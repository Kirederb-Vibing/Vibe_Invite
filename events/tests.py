from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Event, Husstand, Husstandsmedlem, Invitation, Kommentar


def _html(message):
    return message.alternatives[0][0]


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ArrangorMailTests(TestCase):
    def setUp(self):
        self.arrangor = User.objects.create_user(
            username='arrangor', password='hemmelig-kode-1', email='arrangor@example.com',
            first_name='Frederik',
        )
        self.event = Event.objects.create(
            titel='Havefest',
            beskrivelse='Hygge i haven',
            dato=timezone.now() + timedelta(days=14),
            sted='Havnen 1, Aarhus',
            slug='havefest',
            oprettet_af=self.arrangor,
            oenskeliste_url='https://oenskeskyen.dk/havefest',
        )
        Invitation.objects.create(
            event=self.event, navn='Anna', email='anna@example.com',
            status='ja', token='anna',
        )
        Invitation.objects.create(
            event=self.event, navn='Bo', email='bo@example.com',
            status='maaske', token='bo',
        )
        Invitation.objects.create(
            event=self.event, navn='Carla', email='carla@example.com',
            status='nej', token='carla',
        )
        Invitation.objects.create(
            event=self.event, navn='Dan', email='dan@example.com',
            status='pending', token='dan',
        )
        Invitation.objects.create(
            event=self.event, navn='Eva uden mail', email='',
            status='ja', token='eva',
        )
        husstand = Husstand.objects.create(
            event=self.event, navn='Familien Hansen', status='maaske', token='hansen',
        )
        Husstandsmedlem.objects.create(
            husstand=husstand, navn='Far Hansen', email='far@example.com',
        )
        Husstandsmedlem.objects.create(
            husstand=husstand, navn='Mor Hansen', email='mor@example.com',
        )
        individuel = Husstand.objects.create(
            event=self.event, navn='Familien Jensen', status='individuelt', token='jensen',
        )
        Husstandsmedlem.objects.create(
            husstand=individuel, navn='Ole Jensen', email='ole@example.com', status='ja',
        )
        Husstandsmedlem.objects.create(
            husstand=individuel, navn='Ida Jensen', email='ida@example.com', status='nej',
        )
        self.besked_url = reverse('event_send_besked', args=[self.event.slug])
        self.info_url = reverse('event_send_info', args=[self.event.slug])
        self.overblik_url = reverse('event_overblik', args=[self.event.slug])

    def _login(self, user=None):
        self.client.force_login(user or self.arrangor)

    def test_overblik_viser_knapper_for_redaktorer(self):
        self._login()
        response = self.client.get(self.overblik_url)
        self.assertContains(response, 'Send besked')
        self.assertContains(response, 'Send info til deltagere')
        self.assertContains(response, 'id="beskedModal"')
        self.assertContains(response, 'id="infoModal"')
        self.assertContains(response, 'Intet svar')

    def test_besked_kraever_login(self):
        response = self.client.post(self.besked_url, {
            'besked': 'Hej',
            'grupper': ['ja'],
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])
        self.assertEqual(len(mail.outbox), 0)

    def test_besked_forbudt_for_andre(self):
        anden = User.objects.create_user(username='anden', password='hemmelig-kode-1')
        self._login(anden)
        response = self.client.post(self.besked_url, {
            'besked': 'Hej',
            'grupper': ['ja'],
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_besked_tilladt_for_medredaktor(self):
        medredaktor = User.objects.create_user(username='med', password='hemmelig-kode-1')
        self.event.medredaktorer.add(medredaktor)
        self._login(medredaktor)
        response = self.client.post(self.besked_url, {
            'besked': 'Husk solcreme',
            'grupper': ['ja'],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        modtagere = {m.to[0] for m in mail.outbox}
        self.assertIn('anna@example.com', modtagere)
        self.assertIn('ole@example.com', modtagere)

    def test_besked_kraever_tekst(self):
        self._login()
        self.client.post(self.besked_url, {'besked': '   ', 'grupper': ['ja']})
        self.assertEqual(len(mail.outbox), 0)

    def test_besked_kraever_gruppe(self):
        self._login()
        self.client.post(self.besked_url, {'besked': 'Hej alle'})
        self.assertEqual(len(mail.outbox), 0)

    def test_besked_sender_kun_til_valgte_grupper(self):
        self._login()
        self.client.post(self.besked_url, {
            'besked': 'Parkering i gården',
            'grupper': ['nej', 'pending'],
        })
        modtagere = {m.to[0] for m in mail.outbox}
        self.assertEqual(modtagere, {'carla@example.com', 'dan@example.com', 'ida@example.com'})
        for m in mail.outbox:
            html = _html(m)
            self.assertIn('Parkering i gården', html)
            self.assertIn('Besked fra arrangørerne', html)
            self.assertIn('/rsvp/', html)

    def test_besked_mail_har_individuelt_rsvp_link(self):
        self._login()
        self.client.post(self.besked_url, {
            'besked': 'Vi glæder os',
            'grupper': ['ja'],
        })
        efter_email = {m.to[0]: m for m in mail.outbox}
        self.assertIn('/rsvp/anna/', _html(efter_email['anna@example.com']))
        self.assertIn('/rsvp/jensen/', _html(efter_email['ole@example.com']))
        self.assertFalse(any('eva' in m.to[0] for m in mail.outbox))

    def test_besked_sender_ikke_naar_event_er_aflyst(self):
        self.event.aflyst = True
        self.event.save(update_fields=['aflyst'])
        self._login()
        self.client.post(self.besked_url, {
            'besked': 'Hej',
            'grupper': ['ja'],
        })
        self.assertEqual(len(mail.outbox), 0)

    def test_info_sender_kun_til_deltager_og_maaske(self):
        self._login()
        self.client.post(self.info_url, {
            'besked': 'Denne tekst må ikke komme med',
            'grupper': ['nej', 'pending'],
        })
        modtagere = {m.to[0] for m in mail.outbox}
        self.assertEqual(modtagere, {
            'anna@example.com',
            'bo@example.com',
            'far@example.com',
            'mor@example.com',
            'ole@example.com',
        })
        for m in mail.outbox:
            html = _html(m)
            self.assertNotIn('Denne tekst må ikke komme med', html)
            self.assertIn('Praktisk info', html)
            self.assertIn('Havnen 1, Aarhus', html)
            self.assertIn('https://oenskeskyen.dk/havefest', html)
            self.assertIn('google.com/maps', html)
            self.assertIn('/rsvp/', html)
            self.assertIn('kalender.ics', html)

    def test_info_mail_har_husstand_rsvp_link(self):
        self._login()
        self.client.post(self.info_url)
        efter_email = {m.to[0]: m for m in mail.outbox}
        self.assertIn('/rsvp/hansen/', _html(efter_email['far@example.com']))
        self.assertIn('/rsvp/bo/', _html(efter_email['bo@example.com']))

    def test_get_paa_send_endpoints_er_forbudt(self):
        self._login()
        self.assertEqual(self.client.get(self.besked_url).status_code, 403)
        self.assertEqual(self.client.get(self.info_url).status_code, 403)


class RedaktorPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='arr', password='hemmelig-kode-1', email='arr@example.com',
            first_name='Frederik',
        )
        self.event = Event.objects.create(
            titel='Havefest',
            dato=timezone.now() + timedelta(days=7),
            sted='Havnen 1',
            slug='havefest',
            oprettet_af=self.user,
        )
        Invitation.objects.create(
            event=self.event, navn='Anna', email='anna@example.com',
            status='ja', token='anna',
        )
        h = Husstand.objects.create(event=self.event, navn='Hansen', status='maaske', token='hansen')
        Husstandsmedlem.objects.create(husstand=h, navn='Far', email='far@example.com')
        Husstandsmedlem.objects.create(husstand=h, navn='Mor', email='mor@example.com')

    def test_admin_link_kun_for_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, reverse('admin:index'))
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, reverse('admin:index'))
        self.assertContains(response, 'Admin')

    def test_login_respekterer_next(self):
        next_url = reverse('event_opret')
        response = self.client.post(reverse('login'), {
            'username': 'arr',
            'password': 'hemmelig-kode-1',
            'next': next_url,
        })
        self.assertRedirects(response, next_url)

    def test_dashboard_taeller_husstande_med(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '3 inviteret')

    def test_gendan_fra_arkiv(self):
        self.event.arkiveret = True
        self.event.save(update_fields=['arkiveret'])
        self.client.force_login(self.user)
        response = self.client.post(reverse('event_arkiver', args=[self.event.slug]))
        self.assertRedirects(response, reverse('event_overblik', args=[self.event.slug]))
        self.event.refresh_from_db()
        self.assertFalse(self.event.arkiveret)

    def test_gaesteliste_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('event_gaesteliste_csv', args=[self.event.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode('utf-8-sig')
        self.assertIn('Anna', body)
        self.assertIn('Far', body)
        self.assertIn('Hansen', body)

    def test_kommentar_slet(self):
        k = Kommentar.objects.create(
            event=self.event, token='anna', navn='Anna', tekst='Hej alle',
        )
        self.client.force_login(self.user)
        response = self.client.post(reverse('kommentar_slet', args=[self.event.slug, k.pk]))
        self.assertRedirects(response, reverse('event_overblik', args=[self.event.slug]))
        self.assertFalse(Kommentar.objects.filter(pk=k.pk).exists())

    def test_skift_adgangskode_vises_uden_tvang(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('force_password_change'))
        self.assertContains(response, 'Skift adgangskode')
        self.assertNotContains(response, 'Du skal vælge en ny adgangskode før du kan fortsætte.')


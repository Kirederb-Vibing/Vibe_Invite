"""
Django-Q opgaver til automatiske reminders og deadline-håndtering.
Køres dagligt via Django-Q Scheduler.
"""
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_maaske_reminders():
    """
    Daglig opgave der:
    1. Sender reminder-mail til 'måske'-gæster når tidsgrænsen nås.
    2. Sender opfølgende reminders baseret på event.reminder_interval.
    3. Konverterer 'måske' automatisk til 'nej' når sidste_svardag er passeret.
    """
    from .models import Event, Invitation, Husstand

    nu = timezone.now()

    events = Event.objects.filter(
        dato__gt=nu,
        reminder_dage_foer__isnull=False,
    ).select_related()

    total_sendt = 0
    total_auto_nej = 0

    for event in events:
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        første_reminder_dato = event.dato - timedelta(days=event.reminder_dage_foer)

        # --- Solo-invitationer ---
        for inv in event.invitation_set.filter(status='maaske'):
            skal_sende = False

            if inv.reminder_sendt is None:
                # Første reminder
                if nu >= første_reminder_dato:
                    skal_sende = True
            elif event.reminder_interval and event.reminder_interval > 0:
                # Opfølgende reminder
                naeste = inv.reminder_sendt + timedelta(days=event.reminder_interval)
                if nu >= naeste:
                    skal_sende = True

            if skal_sende and inv.email:
                _send_reminder_mail(inv.navn, inv.email, event, inv.token, base_url)
                inv.reminder_sendt = nu
                inv.save(update_fields=['reminder_sendt'])
                total_sendt += 1

        # --- Husstande ---
        for husstand in event.husstande.filter(status='maaske'):
            skal_sende = False

            if husstand.reminder_sendt is None:
                if nu >= første_reminder_dato:
                    skal_sende = True
            elif event.reminder_interval and event.reminder_interval > 0:
                naeste = husstand.reminder_sendt + timedelta(days=event.reminder_interval)
                if nu >= naeste:
                    skal_sende = True

            if skal_sende:
                # Send til alle medlemmer med email
                modtagere = list(
                    husstand.medlemmer.filter(email__isnull=False)
                    .exclude(email='')
                    .values_list('navn', 'email')
                )
                for navn, email in modtagere:
                    _send_reminder_mail(navn, email, event, husstand.token, base_url,
                                        husstand_navn=husstand.navn)
                if modtagere:
                    husstand.reminder_sendt = nu
                    husstand.save(update_fields=['reminder_sendt'])
                    total_sendt += len(modtagere)

    # --- Auto-nej ved udløbet svarfrist ---
    events_med_frist = Event.objects.filter(
        sidste_svardag__lte=nu,
        dato__gt=nu,
    )
    for event in events_med_frist:
        auto_nej_inv = event.invitation_set.filter(status='maaske')
        count = auto_nej_inv.count()
        if count:
            auto_nej_inv.update(status='nej', svar_opdateret=nu)
            total_auto_nej += count

        auto_nej_hus = event.husstande.filter(status='maaske')
        count = auto_nej_hus.count()
        if count:
            auto_nej_hus.update(status='nej', svar_opdateret=nu)
            total_auto_nej += count

    return f"Reminders sendt: {total_sendt}. Auto-nej: {total_auto_nej}."


def _send_reminder_mail(navn, email, event, token, base_url, husstand_navn=None):
    """Sender én reminder-mail til én modtager."""
    rsvp_url = f"{base_url}/rsvp/{token}/"
    context = {
        'navn': navn,
        'event': event,
        'rsvp_url': rsvp_url,
        'husstand_navn': husstand_navn,
        'dage_tilbage': max(0, (event.dato - timezone.now()).days),
    }
    emne = f"Husk at svare: {event.titel}"
    besked_txt = render_to_string('events/email/reminder.txt', context)
    besked_html = render_to_string('events/email/reminder.html', context)
    send_mail(
        subject=emne,
        message=besked_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=besked_html,
        fail_silently=True,
    )


def auto_arkiver_events():
    """
    Daglig opgave der automatisk arkiverer events dagen efter afholdelses-datoen.
    Arkivering sker stille – ingen mail sendes.
    """
    from .models import Event

    nu = timezone.now()
    arkiverede = Event.objects.filter(
        dato__lt=nu,
        arkiveret=False,
    ).update(arkiveret=True)

    return f"Auto-arkiverede events: {arkiverede}."


def notifikation_ny_bruger(username, email, full_name, user_pk):
    """Sender HTML-notifikation til admin når en ny bruger anmoder om oprettelse."""
    from django.core import signing
    from django.template.loader import render_to_string
    from django.core.mail import EmailMultiAlternatives

    admin_emails = [e for _, e in getattr(settings, 'ADMINS', [])]
    if not admin_emails:
        return

    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    accepter_token = signing.dumps({'pk': user_pk}, salt='bruger-accepter')
    afvis_token = signing.dumps({'pk': user_pk}, salt='bruger-afvis')

    context = {
        'full_name': full_name,
        'username': username,
        'email': email,
        'accepter_url': f'{site_url}/bruger/accepter/{accepter_token}/',
        'afvis_url': f'{site_url}/bruger/afvis/{afvis_token}/',
    }

    emne = f'Ny brugeranmodning: {full_name or username}'
    besked_txt = render_to_string('events/email/ny_bruger.txt', context)
    besked_html = render_to_string('events/email/ny_bruger.html', context)

    msg = EmailMultiAlternatives(
        subject=emne,
        body=besked_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=admin_emails,
    )
    msg.attach_alternative(besked_html, 'text/html')
    msg.send(fail_silently=True)

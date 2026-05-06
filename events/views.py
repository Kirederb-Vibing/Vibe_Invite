from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core import signing
from django.conf import settings
from datetime import timezone as dt_timezone
from django.contrib.auth.models import User
from .models import UserProfile, Invitation, Event, Husstand, Husstandsmedlem, Contact, GaestebogHusstand, GaestebogMedlem, Delelink, Kommentar, Afstemning, AfstemningValg, AfstemningsSvar
from .forms import SignupForm, EventForm, InvitationForm, HusstandForm, AfbudEfterFristForm, ContactForm, GaestebogHusstandForm, KommentarForm, AfstemningOpretForm

TEMA_DATA = {
    'standard': {'farve_fra': '#4361ee', 'farve_til': '#3a0ca3', 'ikon': '📋', 'label': 'Standard'},
    'foedselsdag': {'farve_fra': '#f72585', 'farve_til': '#7209b7', 'ikon': '🎂', 'label': 'Fødselsdag'},
    'fest': {'farve_fra': '#f8961e', 'farve_til': '#f3722c', 'ikon': '🎉', 'label': 'Fest / Nytår'},
    'barnedag': {'farve_fra': '#48cae4', 'farve_til': '#023e8a', 'ikon': '🕊️', 'label': 'Barnedåb'},
    'bryllup': {'farve_fra': '#c9a84c', 'farve_til': '#785e25', 'ikon': '💍', 'label': 'Bryllup'},
    'jul': {'farve_fra': '#1b4332', 'farve_til': '#d62828', 'ikon': '🎄', 'label': 'Jul'},
    'paaske': {'farve_fra': '#606c38', 'farve_til': '#dda15e', 'ikon': '🐣', 'label': 'Påske'},
    'sommer': {'farve_fra': '#ff9f1c', 'farve_til': '#ff6b35', 'ikon': '☀️', 'label': 'Sommerfest'},
}


def _send_html_mail(subject, to, template_prefix, context, attachment=None):
    """Sender en HTML+tekst email. attachment = (filename, content, mimetype)."""
    txt = render_to_string(f'events/email/{template_prefix}.txt', context)
    html = render_to_string(f'events/email/{template_prefix}.html', context)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to] if isinstance(to, str) else to,
    )
    msg.attach_alternative(html, 'text/html')
    if attachment:
        msg.attach(*attachment)
    msg.send(fail_silently=True)


def _svg_moenster_css(tema, farve_hex):
    """Returnerer CSS background-image + background-size med SVG-mønster for temaet."""
    from urllib.parse import quote
    c = farve_hex
    monstre = {
        'standard': (
            f'<circle cx="15" cy="15" r="4" fill="{c}"/>'
            f'<circle cx="45" cy="45" r="4" fill="{c}"/>'
            f'<circle cx="45" cy="15" r="2.5" fill="{c}"/>'
            f'<circle cx="15" cy="45" r="2.5" fill="{c}"/>'
        ),
        'foedselsdag': (
            f'<ellipse cx="30" cy="21" rx="10" ry="13" fill="{c}"/>'
            f'<circle cx="30" cy="34" r="2" fill="{c}"/>'
            f'<path d="M30 36 Q27 44 26 52" stroke="{c}" stroke-width="2" fill="none" stroke-linecap="round"/>'
        ),
        'fest': (
            f'<polygon points="30,12 33,23 45,23 36,30 39,42 30,35 21,42 24,30 15,23 27,23" fill="{c}"/>'
        ),
        'barnedag': (
            f'<rect x="27" y="13" width="6" height="34" rx="3" fill="{c}"/>'
            f'<rect x="13" y="23" width="34" height="6" rx="3" fill="{c}"/>'
        ),
        'bryllup': (
            f'<path d="M30 40 C20 31 13 25 13 19 C13 14 17 11 21 11 C25 11 28 14 30 17 C32 14 35 11 39 11 C43 11 47 14 47 19 C47 25 40 31 30 40Z" fill="{c}"/>'
        ),
        'jul': (
            f'<line x1="30" y1="8" x2="30" y2="52" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="10" y1="19" x2="50" y2="41" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="50" y1="19" x2="10" y2="41" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="30" cy="8" r="3" fill="{c}"/>'
            f'<circle cx="30" cy="52" r="3" fill="{c}"/>'
            f'<circle cx="10" cy="19" r="3" fill="{c}"/>'
            f'<circle cx="50" cy="41" r="3" fill="{c}"/>'
            f'<circle cx="50" cy="19" r="3" fill="{c}"/>'
            f'<circle cx="10" cy="41" r="3" fill="{c}"/>'
        ),
        'paaske': (
            f'<ellipse cx="30" cy="30" rx="13" ry="18" fill="none" stroke="{c}" stroke-width="3"/>'
            f'<path d="M17 27 Q30 32 43 27" stroke="{c}" stroke-width="2.5" fill="none"/>'
        ),
        'sommer': (
            f'<circle cx="30" cy="30" r="9" fill="{c}"/>'
            f'<line x1="30" y1="8" x2="30" y2="16" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="30" y1="44" x2="30" y2="52" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="8" y1="30" x2="16" y2="30" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="44" y1="30" x2="52" y2="30" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="14" y1="14" x2="20" y2="20" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>'
            f'<line x1="46" y1="14" x2="40" y2="20" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>'
            f'<line x1="14" y1="46" x2="20" y2="40" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>'
            f'<line x1="46" y1="46" x2="40" y2="40" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>'
        ),
    }
    ikon = monstre.get(tema, monstre['standard'])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" opacity="0.13">'
        f'{ikon}'
        f'</svg>'
    )
    encoded = quote(svg, safe="")
    return f'url(data:image/svg+xml,{encoded})'


def _generer_ics(event):
    """Genererer ICS-filindhold for et event."""
    from datetime import timedelta

    def ics_fmt(dt):
        if timezone.is_aware(dt):
            return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        return dt.strftime('%Y%m%dT%H%M%S')

    def ics_text(s):
        return (s or '').replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')

    now = timezone.now()
    slut = event.dato + timedelta(hours=3)
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Vibe Invite//DA',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:{event.slug}@vibe-invite',
        f'DTSTAMP:{ics_fmt(now)}',
        f'DTSTART:{ics_fmt(event.dato)}',
        f'DTEND:{ics_fmt(slut)}',
        f'SUMMARY:{ics_text(event.titel)}',
    ]
    if event.beskrivelse:
        lines.append(f'DESCRIPTION:{ics_text(event.beskrivelse)}')
    if event.sted:
        lines.append(f'LOCATION:{ics_text(event.sted)}')
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(lines)


def _rsvp_kontekst(event, request):
    """Returnerer tema_data, ics_url, gcal_url og maps_url til RSVP-skabeloner."""
    from urllib.parse import quote
    from datetime import timedelta
    tema_data = TEMA_DATA.get(event.tema, TEMA_DATA['standard'])
    ics_url = request.build_absolute_uri(f'/event/{event.slug}/kalender.ics')
    if timezone.is_aware(event.dato):
        dtstart = event.dato.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        dtend = (event.dato + timedelta(hours=3)).astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    else:
        dtstart = event.dato.strftime('%Y%m%dT%H%M%S')
        dtend = (event.dato + timedelta(hours=3)).strftime('%Y%m%dT%H%M%S')
    gcal_url = (
        'https://calendar.google.com/calendar/render?action=TEMPLATE'
        f'&text={quote(event.titel)}'
        f'&dates={dtstart}/{dtend}'
        f'&details={quote(event.beskrivelse or "")}'
        f'&location={quote(event.sted or "")}'
    )
    maps_url = f'https://www.google.com/maps/search/?api=1&query={quote(event.sted)}' if event.sted else ''
    farve_moenster = event.farve_moenster or tema_data['farve_fra']
    farve_baggrund = event.farve_baggrund or '#ffffff'
    moenster_css = _svg_moenster_css(event.tema, farve_moenster)
    return {
        'tema_data': tema_data,
        'ics_url': ics_url,
        'gcal_url': gcal_url,
        'maps_url': maps_url,
        'farve_baggrund': farve_baggrund,
        'moenster_css': moenster_css,
    }


def _andre_deltagere(event, ekskluder_email=None):
    """Returnerer liste af navne på bekræftede deltagere (max 20)."""
    navne = list(event.invitation_set.filter(status='ja').exclude(
        email=ekskluder_email
    ).values_list('navn', flat=True)) if ekskluder_email else list(
        event.invitation_set.filter(status='ja').values_list('navn', flat=True)
    )
    for h in event.husstande.filter(status='ja'):
        navne.extend(h.medlemmer.values_list('navn', flat=True))
    for h in event.husstande.filter(status='individuelt'):
        navne.extend(h.medlemmer.filter(status='ja').values_list('navn', flat=True))
    return navne[:20]


# ---------- AUTH ----------
def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            from .tasks import notifikation_ny_bruger
            notifikation_ny_bruger(
                username=user.username,
                email=user.email,
                full_name=user.get_full_name(),
                user_pk=user.pk,
            )
            messages.success(
                request,
                _('Tak! Din konto er oprettet og venter på godkendelse fra en administrator. '
                  'Du får besked når den er aktiveret.')
            )
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'events/signup.html', {'form': form})


def bruger_accepter(request, token):
    """Aktiverer en bruger via signeret token fra admin-email."""
    try:
        data = signing.loads(token, salt='bruger-accepter', max_age=7 * 24 * 3600)
        user = get_object_or_404(User, pk=data['pk'])
    except signing.BadSignature:
        return HttpResponseBadRequest(_('Ugyldigt eller udløbet link.'))

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
        _send_html_mail(
            subject=_('Din konto er nu aktiveret'),
            to=user.email,
            template_prefix='bruger_aktiveret',
            context={
                'bruger': user,
                'login_url': f'{settings.SITE_URL}/login/',
            },
        )

    return render(request, 'events/bruger_handling.html', {
        'handling': 'accepteret',
        'bruger': user,
    })


def bruger_afvis(request, token):
    """Sletter en afvist bruger via signeret token fra admin-email."""
    try:
        data = signing.loads(token, salt='bruger-afvis', max_age=7 * 24 * 3600)
        user = get_object_or_404(User, pk=data['pk'])
    except signing.BadSignature:
        return HttpResponseBadRequest(_('Ugyldigt eller udløbet link.'))

    navn = user.get_full_name() or user.username
    email = user.email
    if not user.is_active:
        _send_html_mail(
            subject=_('Din konto er ikke godkendt'),
            to=email,
            template_prefix='bruger_afvist',
            context={'navn': navn},
        )
        user.delete()

    return render(request, 'events/bruger_handling.html', {
        'handling': 'afvist',
        'navn': navn,
    })


# ---------- DASHBOARD + EVENT-ADMIN ----------
@login_required
def dashboard(request):
    if request.user.is_superuser:
        qs = Event.objects.all()
    else:
        qs = Event.objects.filter(
            Q(oprettet_af=request.user) | Q(medredaktorer=request.user)
        ).distinct()
    events = qs.filter(arkiveret=False).order_by('-dato')
    arkiverede = qs.filter(arkiveret=True).order_by('-dato')
    return render(request, 'events/dashboard.html', {
        'events': events,
        'arkiverede': arkiverede,
    })

def _hent_gaestebog_data(user):
    """Returnerer (kontakter, husstande, alle_tags) sorteret alfabetisk for invite-pickeren."""
    kontakter = list(Contact.objects.filter(user=user).order_by('navn'))
    husstande = list(
        GaestebogHusstand.objects.filter(user=user).prefetch_related('medlemmer').order_by('navn')
    )
    alle_tags = set()
    for k in kontakter:
        alle_tags.update(k.tags_liste())
    for h in husstande:
        alle_tags.update(h.tags_liste())
    return kontakter, husstande, sorted(alle_tags)


def _tilfoej_gaestebog_til_event(request, event):
    """Læser kontakt/husstand-valg fra POST og tilføjer dem til eventet. Returnerer antal tilføjede."""
    valgte_kontakter = request.POST.getlist('kontakt')
    valgte_husstande = request.POST.getlist('husstand')
    valgte_medlemmer = request.POST.getlist('husstand_medlem')

    husstand_pks_tilfoejede = set()
    tilfoejede = 0

    eksisterende_emails = set(event.invitation_set.values_list('email', flat=True))

    for pk_str in valgte_husstande:
        try:
            gb = GaestebogHusstand.objects.get(pk=int(pk_str), user=request.user)
            h = Husstand.objects.create(event=event, navn=gb.navn)
            for m in gb.medlemmer.all():
                Husstandsmedlem.objects.create(
                    husstand=h, navn=m.navn, email=m.email, send_invitation=bool(m.email),
                )
            husstand_pks_tilfoejede.add(gb.pk)
            tilfoejede += 1
        except (GaestebogHusstand.DoesNotExist, ValueError):
            pass

    # Grupper valgte enkeltmedlemmer efter husstand (spring over hvis hele husstanden allerede er tilføjet)
    husstand_til_valgte = {}
    for pk_str in valgte_medlemmer:
        try:
            m = GaestebogMedlem.objects.select_related('husstand').get(
                pk=int(pk_str), husstand__user=request.user
            )
            if m.husstand_id in husstand_pks_tilfoejede or not m.email:
                continue
            husstand_til_valgte.setdefault(m.husstand_id, []).append(m)
        except (GaestebogMedlem.DoesNotExist, ValueError):
            pass

    for husstand_id, medlemmer in husstand_til_valgte.items():
        try:
            gb = GaestebogHusstand.objects.get(pk=husstand_id)
        except GaestebogHusstand.DoesNotExist:
            continue
        h = Husstand.objects.create(event=event, navn=gb.navn)
        for m in medlemmer:
            if m.email not in eksisterende_emails:
                Husstandsmedlem.objects.create(
                    husstand=h, navn=m.navn, email=m.email, send_invitation=True,
                )
                eksisterende_emails.add(m.email)
        tilfoejede += 1

    for pk_str in valgte_kontakter:
        try:
            k = Contact.objects.get(pk=int(pk_str), user=request.user)
            if k.email not in eksisterende_emails:
                Invitation.objects.create(event=event, navn=k.navn, email=k.email)
                eksisterende_emails.add(k.email)
                tilfoejede += 1
        except (Contact.DoesNotExist, ValueError):
            pass

    return tilfoejede


@login_required
def event_opret(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.oprettet_af = request.user
            event.save()
            form.save_m2m()
            tilfoejede = _tilfoej_gaestebog_til_event(request, event)
            msg = _('Eventet "%(titel)s" er oprettet.') % {'titel': event.titel}
            if tilfoejede:
                msg += ' ' + _('%(n)d gæst(er) tilføjet.') % {'n': tilfoejede}
            messages.success(request, msg)
            return redirect('event_overblik', slug=event.slug)
    else:
        form = EventForm()

    kontakter, husstande, alle_tags = _hent_gaestebog_data(request.user)
    return render(request, 'events/event_form.html', {
        'form': form,
        'titel': 'Opret event',
        'is_new': True,
        'kontakter': kontakter,
        'husstande': husstande,
        'alle_tags': alle_tags,
        'tema_data': TEMA_DATA,
    })

@login_required
def event_rediger(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, _('Ændringer gemt.'))
            return redirect('event_overblik', slug=event.slug)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {
        'form': form,
        'titel': 'Rediger event',
        'tema_data': TEMA_DATA,
    })

@login_required
def event_slet(request, slug):
    """Slet event (hvis ejer) eller fjern sig selv som medredaktør."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id

    if request.method == 'POST':
        if er_ejer:
            titel = event.titel
            event.delete()
            messages.success(request, _('Eventet "%(titel)s" og alle tilhørende invitationer er slettet.') % {'titel': titel})
            return redirect('dashboard')
        else:
            event.medredaktorer.remove(request.user)
            messages.success(request, _('Du er fjernet som medredaktør på "%(titel)s".') % {'titel': event.titel})
            return redirect('dashboard')

    antal_gaester = event.invitation_set.count() + event.husstande.count()
    return render(request, 'events/event_slet.html', {
        'event': event,
        'er_ejer': er_ejer,
        'antal_gaester': antal_gaester,
    })

@login_required
def medredaktor_tilfoej(request, slug):
    """Tilføj en bruger som medredaktør via email (kun for ejer)."""
    event = get_object_or_404(Event, slug=slug)
    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id
    if not er_ejer:
        return HttpResponseForbidden(_('Kun ejeren kan tilføje medredaktører.'))
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, _('Indtast en email-adresse.'))
        else:
            try:
                bruger = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                messages.error(request, _('Ingen bruger fundet med email "%(email)s". Brugeren skal have en konto.') % {'email': email})
            else:
                if bruger == event.oprettet_af:
                    messages.info(request, _('Den bruger er allerede ejer af eventet.'))
                elif event.medredaktorer.filter(pk=bruger.pk).exists():
                    messages.info(request, _('%(navn)s er allerede medredaktør.') % {'navn': bruger.get_full_name() or bruger.username})
                else:
                    event.medredaktorer.add(bruger)
                    messages.success(request, _('%(navn)s er nu tilføjet som medredaktør.') % {'navn': bruger.get_full_name() or bruger.username})
    return redirect('event_overblik', slug=event.slug)

@login_required
def medredaktor_fjern(request, slug, user_id):
    """Fjern en medredaktør fra et event (kun for ejer)."""
    event = get_object_or_404(Event, slug=slug)
    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id
    if not er_ejer:
        return HttpResponseForbidden(_('Kun ejeren kan fjerne medredaktører.'))
    if request.method == 'POST':
        bruger = get_object_or_404(User, pk=user_id)
        event.medredaktorer.remove(bruger)
        messages.success(request, _('%(navn)s er fjernet som medredaktør.') % {'navn': bruger.get_full_name() or bruger.username})
    return redirect('event_overblik', slug=event.slug)

@login_required
def deltager_opret(request, slug):
    """Tilføj en ny gæst til et event."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            navn = form.cleaned_data['navn'].strip()
            email = (form.cleaned_data.get('email') or '').strip().lower()

            # Tjek: eksisterer allerede som solo-invitation? (match på navn ELLER email)
            q_inv = Q(navn__iexact=navn)
            if email:
                q_inv |= Q(email__iexact=email)
            dup_inv = Invitation.objects.filter(event=event).filter(q_inv).first()
            if dup_inv:
                messages.info(request, _('"%(navn)s" findes allerede som deltager på dette event.') % {'navn': dup_inv.navn})
                return redirect('event_overblik', slug=event.slug)

            # Tjek: eksisterer allerede som husstandsmedlem? (match på navn ELLER email)
            q_medl = Q(navn__iexact=navn)
            if email:
                q_medl |= Q(email__iexact=email)
            dup_medl = Husstandsmedlem.objects.filter(husstand__event=event).filter(q_medl).first()
            if dup_medl:
                messages.info(request, _('"%(navn)s" er allerede med i husstanden "%(husstand)s" på dette event.') % {'navn': dup_medl.navn, 'husstand': dup_medl.husstand.navn})
                return redirect('event_overblik', slug=event.slug)

            invitation = form.save(commit=False)
            invitation.event = event
            invitation.save()
            messages.success(request, _('%(navn)s er tilføjet som deltager.') % {'navn': invitation.navn})

            if 'gem_og_tilfoej_flere' in request.POST:
                return redirect('deltager_opret', slug=event.slug)
            return redirect('event_overblik', slug=event.slug)
    else:
        form = InvitationForm()

    return render(request, 'events/deltager_form.html', {
        'form': form,
        'event': event,
    })

@login_required
def deltager_rediger(request, slug, token):
    """Se og redigér en eksisterende gæst."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    invitation = get_object_or_404(Invitation, token=token, event=event)

    if request.method == 'POST':
        if 'slet' in request.POST:
            navn = invitation.navn
            invitation.delete()
            messages.success(request, _('%(navn)s er fjernet fra gæstelisten.') % {'navn': navn})
            return redirect('event_overblik', slug=event.slug)

        form = InvitationForm(request.POST, instance=invitation)
        if form.is_valid():
            form.save()
            messages.success(request, _('Ændringer til %(navn)s er gemt.') % {'navn': invitation.navn})
            return redirect('event_overblik', slug=event.slug)
    else:
        form = InvitationForm(instance=invitation)

    rsvp_url = request.build_absolute_uri(f'/rsvp/{invitation.token}/')

    return render(request, 'events/deltager_rediger.html', {
        'form': form,
        'event': event,
        'invitation': invitation,
        'rsvp_url': rsvp_url,
    })

# --- HUSSTANDE ---
def _parse_husstand_input(request):
    """
    Henter medlemsdata fra POST.
    Returnerer en liste af tuples: (navn, email, send_invitation).
    """
    medlem_navne = request.POST.getlist('medlem_navn[]')
    medlem_emails = request.POST.getlist('medlem_email[]')

    # Parse send_invitation som en dictionary med indeks
    send_invitation_dict = {}
    for key, value in request.POST.items():
        if key.startswith('medlem_send_invitation[') and key.endswith(']'):
            index = key.split('[')[1].split(']')[0]  # Ekstraher indeks (fx "0", "1", osv.)
            send_invitation_dict[index] = (value == '1')  # Konverter til boolean

    medlemmer = []
    for i, navn in enumerate(medlem_navne):
        if not navn.strip():
            continue
        email = medlem_emails[i].strip() if i < len(medlem_emails) else ""
        send_flag = send_invitation_dict.get(str(i), False)  # Hent send_flag for dette indeks
        medlemmer.append((navn, email, send_flag))

    return medlemmer

@login_required
def husstand_opret(request, slug):
    """Opret ny husstand med medlemmer."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        form = HusstandForm(request.POST)
        medlemmer = _parse_husstand_input(request)

        ekstra_fejl = []
        if not medlemmer:
            ekstra_fejl.append(_('Tilføj mindst ét husstandsmedlem.'))

        if form.is_valid() and not ekstra_fejl:
            husstand_navn = form.cleaned_data['navn'].strip()
            dup_husstand = Husstand.objects.filter(event=event, navn__iexact=husstand_navn).first()
            if dup_husstand:
                messages.info(request, _('Husstanden "%(navn)s" findes allerede på dette event.') % {'navn': husstand_navn})
                return redirect('husstand_rediger', slug=event.slug, token=dup_husstand.token)

            husstand = form.save(commit=False)
            husstand.event = event
            husstand.save()

            for navn, email, send_flag in medlemmer:
                Husstandsmedlem.objects.create(
                    husstand=husstand,
                    navn=navn,
                    email=email if email else None,
                    send_invitation=send_flag
                )

            messages.success(request, _('Husstanden "%(navn)s" er oprettet.') % {'navn': husstand.navn})
            return redirect('event_overblik', slug=event.slug)

        for fejl in ekstra_fejl:
            messages.error(request, fejl)

    return render(request, 'events/husstand_form.html', {
        'form': HusstandForm(),
        'event': event,
        'titel': 'Opret husstand',
        'medlemmer': [],
        'er_redigering': False,
    })

@login_required
def husstand_rediger(request, slug, token):
    """Redigér eksisterende husstand."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    husstand = get_object_or_404(Husstand, token=token, event=event)

    if request.method == 'POST':
        form = HusstandForm(request.POST, instance=husstand)
        medlemmer = _parse_husstand_input(request)

        ekstra_fejl = []
        if not medlemmer:
            ekstra_fejl.append(_('En husstand skal have mindst ét medlem.'))

        if form.is_valid() and not ekstra_fejl:
            form.save()
            husstand.medlemmer.all().delete()
            for navn, email, send_flag in medlemmer:
                q = Q(navn__iexact=navn)
                if email:
                    q |= Q(email__iexact=email)
                dup_inv = Invitation.objects.filter(event=event).filter(q).first()
                if dup_inv:
                    messages.warning(request, _('"%(navn)s" findes allerede som solo deltager og blev ikke tilføjet til husstanden.') % {'navn': dup_inv.navn})
                    continue
                Husstandsmedlem.objects.create(
                    husstand=husstand,
                    navn=navn,
                    email=email if email else None,
                    send_invitation=send_flag
                )
            messages.success(request, _('Husstanden "%(navn)s" er opdateret.') % {'navn': husstand.navn})
            return redirect('event_overblik', slug=event.slug)

        for fejl in ekstra_fejl:
            messages.error(request, fejl)
    else:
        form = HusstandForm(instance=husstand)
        medlemmer = [(m.navn, m.email or '', m.send_invitation) for m in husstand.medlemmer.all()]

    rsvp_url = request.build_absolute_uri(f'/rsvp/{husstand.token}/')

    return render(request, 'events/husstand_form.html', {
        'form': form,
        'event': event,
        'husstand': husstand,
        'titel': f'Redigér {husstand.navn}',
        'medlemmer': medlemmer,
        'er_redigering': True,
        'rsvp_url': rsvp_url,
    })

@login_required
def husstand_slet(request, slug, token):
    """Slet en husstand med alle dens medlemmer."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')
    husstand = get_object_or_404(Husstand, token=token, event=event)

    if request.method == 'POST':
        navn = husstand.navn
        husstand.delete()
        messages.success(request, _('Husstanden "%(navn)s" er slettet.') % {'navn': navn})
        return redirect('event_overblik', slug=event.slug)

    return render(request, 'events/husstand_slet.html', {
        'event': event,
        'husstand': husstand,
    })

# ---------- RSVP (offentlig) ----------
def rsvp(request, token):
    # Prøv først at finde en solo-invitation
    invitation = Invitation.objects.filter(token=token).first()
    husstand = None

    if invitation:
        # Solo-invitation: brug det eksisterende flow
        event = invitation.event
        frist_passeret = event.svarfrist_passeret()

        if invitation.status != 'pending':
            return redirect('rsvp_oversigt', token=token)

        if request.method == 'POST':
            status = request.POST.get('status')
            if status in ['ja', 'nej', 'maaske']:
                invitation.status = status
                invitation.svar_opdateret = timezone.now()
                invitation.save()
                return redirect('rsvp_bekræftet', token=token)

        return render(request, 'events/rsvp.html', {
            'invitation': invitation,
            'frist_passeret': frist_passeret,
            'event': event,
            **_rsvp_kontekst(event, request),
        })
    else:
        # Hvis ingen solo-invitation, prøv at finde en husstand
        husstand = get_object_or_404(Husstand, token=token)
        event = husstand.event
        frist_passeret = event.svarfrist_passeret()

        if husstand.status != 'pending':
            return redirect('rsvp_oversigt', token=token)

        if request.method == 'POST':
            # Håndter de 3 store knapper
            husstand_status = request.POST.get('husstand_status')
            if husstand_status in ['ja', 'nej', 'maaske']:
                if husstand_status == 'ja':
                    husstand.medlemmer.all().update(status='ja')
                    husstand.status = 'ja'
                elif husstand_status == 'nej':
                    husstand.medlemmer.all().update(status='nej')
                    husstand.status = 'nej'
                elif husstand_status == 'maaske':
                    husstand.status = 'maaske'
                husstand.svar_opdateret = timezone.now()
                husstand.save()
                return redirect('rsvp_bekræftet', token=token)

            # Håndter individuelle checkboxes
            if 'bekraeft_individuelt' in request.POST:
                husstand.status = 'individuelt'
                husstand.svar_opdateret = timezone.now()
                husstand.save()
                for medlem in husstand.medlemmer.all():
                    checkbox_name = f'medlem_{medlem.id}'
                    medlem.status = 'ja' if checkbox_name in request.POST else 'nej'
                    medlem.save()
                return redirect('rsvp_bekræftet', token=token)

        # Hvis GET-request: vis formularen
        medlemmer = husstand.medlemmer.all()
        er_solo = husstand.medlemmer.count() == 1
        solo_navn = husstand.medlemmer.first().navn if er_solo else None
        return render(request, 'events/rsvp_husstand.html', {
            'husstand': husstand,
            'medlemmer': medlemmer,
            'frist_passeret': frist_passeret,
            'event': event,
            'er_solo': er_solo,
            'solo_navn': solo_navn,
            **_rsvp_kontekst(event, request),
        })

def rsvp_oversigt(request, token):
    # Prøv først at finde en solo-invitation
    invitation = Invitation.objects.filter(token=token).first()
    husstand = None

    if invitation:
        # Solo-invitation: brug det eksisterende flow
        event = invitation.event
        frist_passeret = event.svarfrist_passeret()

        if frist_passeret:
            kan_aendre_til = ['nej'] if invitation.status == 'ja' else []
        else:
            kan_aendre_til = [s for s in ['ja', 'nej', 'maaske'] if s != invitation.status]

        if request.method == 'POST':
            ny_status = request.POST.get('status')
            if ny_status not in kan_aendre_til:
                messages.error(request, _('Den ændring er ikke tilladt.'))
                return redirect('rsvp_oversigt', token=token)

            if frist_passeret and invitation.status == 'ja' and ny_status == 'nej':
                form = AfbudEfterFristForm(request.POST)
                if form.is_valid():
                    invitation.status = 'nej'
                    invitation.afbud_aarsag = form.cleaned_data['aarsag']
                    invitation.svar_opdateret = timezone.now()
                    invitation.save()
                    _send_afbud_mail_til_arrangør(invitation)
                    return redirect('rsvp_bekræftet', token=token)
                return render(request, 'events/rsvp_oversigt.html', {
                    'invitation': invitation,
                    'frist_passeret': frist_passeret,
                    'kan_aendre_til': kan_aendre_til,
                    'afbud_form': form,
                    'andre_ja': _andre_deltagere(event, ekskluder_email=invitation.email) if event.vis_deltagerliste else [],
                    'event': event,
                    **_rsvp_kontekst(event, request),
                })
            else:
                invitation.status = ny_status
                invitation.svar_opdateret = timezone.now()
                invitation.save()
                return redirect('rsvp_bekræftet', token=token)

        return render(request, 'events/rsvp_oversigt.html', {
            'invitation': invitation,
            'frist_passeret': frist_passeret,
            'kan_aendre_til': kan_aendre_til,
            'afbud_form': AfbudEfterFristForm(),
            'andre_ja': _andre_deltagere(event, ekskluder_email=invitation.email) if event.vis_deltagerliste else [],
            'event': event,
            'kommentarer': event.kommentarer.all(),
            'kommentar_form': KommentarForm(),
            'afstemninger': _afstemning_kontekst(event, token),
            'guest_token': token,
            **_rsvp_kontekst(event, request),
        })

    else:
        # Hvis det er en husstand
        husstand = get_object_or_404(Husstand, token=token)
        event = husstand.event
        frist_passeret = event.svarfrist_passeret()
        medlemmer = husstand.medlemmer.all()

        # Bestem hvilke ændringer der er tilladt
        if frist_passeret:
            kan_aendre_til = ['nej'] if husstand.status == 'ja' else []
            kan_aendre_medlem = ['nej'] if husstand.status in ['ja', 'individuelt'] else []
        else:
            kan_aendre_til = [s for s in ['ja', 'nej', 'maaske'] if s != husstand.status]
            kan_aendre_medlem = ['ja', 'nej']

        if request.method == 'POST':
            # Håndter fælles svar-knapper
            ny_status = request.POST.get('husstand_status')
            if ny_status and ny_status in kan_aendre_til:
                if ny_status == 'ja':
                    husstand.medlemmer.all().update(status='ja')
                    husstand.status = 'ja'
                elif ny_status == 'nej':
                    husstand.medlemmer.all().update(status='nej')
                    husstand.status = 'nej'
                    afbud_aarsag = request.POST.get('afbud_aarsag', '').strip()
                    if afbud_aarsag:
                        husstand.afbud_aarsag = afbud_aarsag
                elif ny_status == 'maaske':
                    husstand.status = 'maaske'
                husstand.svar_opdateret = timezone.now()
                husstand.save()
                _send_afbud_mail_til_arrangør_husstand(husstand)
                return redirect('rsvp_bekræftet', token=token)

            # Håndter individuelle ændringer
            if 'bekraeft_individuelt' in request.POST:
                husstand.status = 'individuelt'
                husstand.svar_opdateret = timezone.now()
                husstand.save()
                for medlem in medlemmer:
                    checkbox_name = f'medlem_{medlem.id}'
                    if checkbox_name in request.POST:
                        medlem.status = 'ja'
                    else:
                        medlem.status = 'nej'
                    medlem.save()
                return redirect('rsvp_bekræftet', token=token)

        er_solo = husstand.medlemmer.count() == 1
        solo_navn = husstand.medlemmer.first().navn if er_solo else None
        return render(request, 'events/rsvp_husstand_oversigt.html', {
            'husstand': husstand,
            'medlemmer': medlemmer,
            'frist_passeret': frist_passeret,
            'kan_aendre_til': kan_aendre_til,
            'kan_aendre_medlem': kan_aendre_medlem,
            'afbud_form': AfbudEfterFristForm() if frist_passeret and husstand.status == 'ja' else None,
            'andre_ja': _andre_deltagere(event) if event.vis_deltagerliste else [],
            'event': event,
            'er_solo': er_solo,
            'solo_navn': solo_navn,
            'kommentarer': event.kommentarer.all(),
            'kommentar_form': KommentarForm(),
            'afstemninger': _afstemning_kontekst(event, token),
            'guest_token': token,
            **_rsvp_kontekst(event, request),
        })

def rsvp_bekræftet(request, token):
    from django.http import HttpResponseNotFound
    invitation = Invitation.objects.filter(token=token).first()
    if invitation:
        event = invitation.event
        andre_ja = _andre_deltagere(event, ekskluder_email=invitation.email) if invitation.status == 'ja' and event.vis_deltagerliste else []
        return render(request, 'events/bekræftet.html', {
            'invitation': invitation,
            'andre_ja': andre_ja,
            'event': event,
            **_rsvp_kontekst(event, request),
        })
    husstand = Husstand.objects.filter(token=token).first()
    if husstand:
        event = husstand.event
        andre_ja = _andre_deltagere(event) if husstand.status == 'ja' and event.vis_deltagerliste else []
        return render(request, 'events/bekræftet.html', {
            'husstand': husstand,
            'andre_ja': andre_ja,
            'event': event,
            **_rsvp_kontekst(event, request),
        })
    return HttpResponseNotFound("Invitation eller husstand ikke fundet.")

def event_ics(request, slug):
    """Download ICS-fil for et event."""
    from django.http import HttpResponse
    event = get_object_or_404(Event, slug=slug)
    ics = _generer_ics(event)
    response = HttpResponse(ics, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
    return response


# ---------- DELELINK (offentlig selvtilmelding) ----------
def del_rsvp(request, token):
    """Offentlig selvtilmeldingsside via delelink."""
    delelink = get_object_or_404(Delelink, token=token)
    event = delelink.event
    fejl = []

    if request.method == 'POST':
        if delelink.type == 'solo':
            navn = request.POST.get('navn', '').strip()
            email = request.POST.get('email', '').strip().lower()

            if not navn:
                fejl.append('Navn er påkrævet.')
            if not email:
                fejl.append('Email er påkrævet.')

            if not fejl:
                # Tjek duplikat solo
                dup_inv = Invitation.objects.filter(event=event, email__iexact=email).first()
                if dup_inv:
                    return redirect('rsvp', token=dup_inv.token)
                # Tjek duplikat husstandsmedlem
                dup_medl = Husstandsmedlem.objects.filter(husstand__event=event, email__iexact=email).first()
                if dup_medl:
                    return redirect('rsvp', token=dup_medl.husstand.token)
                inv = Invitation.objects.create(event=event, navn=navn, email=email)
                return redirect('rsvp', token=inv.token)

        else:  # husstand
            husstand_navn = request.POST.get('husstand_navn', '').strip()
            medlemmer = _parse_husstand_input(request)

            if not husstand_navn:
                fejl.append('Husstandens navn er påkrævet.')
            if not medlemmer:
                fejl.append('Tilføj mindst ét husstandsmedlem.')
            elif not any(email for _, email, _ in medlemmer):
                fejl.append('Mindst ét husstandsmedlem skal have en email-adresse.')

            if not fejl:
                dup_husstand = Husstand.objects.filter(event=event, navn__iexact=husstand_navn).first()
                if dup_husstand:
                    return redirect('rsvp', token=dup_husstand.token)
                husstand = Husstand.objects.create(event=event, navn=husstand_navn)
                for m_navn, m_email, _ in medlemmer:
                    Husstandsmedlem.objects.create(
                        husstand=husstand,
                        navn=m_navn,
                        email=m_email if m_email else None,
                        send_invitation=bool(m_email),
                    )
                return redirect('rsvp', token=husstand.token)

    return render(request, 'events/del_rsvp.html', {
        'event': event,
        'delelink': delelink,
        'fejl': fejl,
        **_rsvp_kontekst(event, request),
    })


# ---------- OVERBLIK + SEND ----------
@login_required
def event_overblik(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    # Solo-invitationer
    invitationer = event.invitation_set.all()
    ja_solo = invitationer.filter(status='ja')
    maaske_solo = invitationer.filter(status='maaske')
    nej_solo = invitationer.filter(status='nej')
    afventer_solo = invitationer.filter(status='pending')

    # Husstande
    husstande = event.husstande.all().prefetch_related('medlemmer')

    # Beregn samlede tællere (solo + husstandsmedlemmer)
    total_ja = ja_solo.count()
    total_maaske = maaske_solo.count()
    total_nej = nej_solo.count()
    total_afventer = afventer_solo.count()

    for h in husstande:
        if h.status == 'ja':
            total_ja += h.antal_medlemmer()
        elif h.status == 'maaske':
            total_maaske += h.antal_medlemmer()
        elif h.status == 'nej':
            total_nej += h.antal_medlemmer()
        elif h.status == 'pending':
            total_afventer += h.antal_medlemmer()
        elif h.status == 'individuelt':
            total_ja += h.antal_ja()
            total_nej += h.antal_nej()

    # Opret kombinerede lister (solo + husstandsmedlemmer)
    alle_ja = list(ja_solo)
    alle_maaske = list(maaske_solo)
    alle_nej = list(nej_solo)
    alle_afventer = list(afventer_solo)

    for h in husstande:
        if h.status == 'ja':
            alle_ja.extend(h.medlemmer.all())
        elif h.status == 'maaske':
            alle_maaske.extend(h.medlemmer.all())
        elif h.status == 'nej':
            alle_nej.extend(h.medlemmer.all())
        elif h.status == 'pending':
            alle_afventer.extend(h.medlemmer.all())
        elif h.status == 'individuelt':
            alle_ja.extend(h.medlemmer.filter(status='ja'))
            alle_nej.extend(h.medlemmer.filter(status='nej'))

    tema_data = TEMA_DATA.get(event.tema, TEMA_DATA['standard'])
    farve_moenster = event.farve_moenster or tema_data['farve_fra']
    farve_baggrund = event.farve_baggrund or '#ffffff'
    moenster_css = _svg_moenster_css(event.tema, farve_moenster)
    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id

    dl_solo, _ = Delelink.objects.get_or_create(event=event, type='solo')
    dl_husstand, _ = Delelink.objects.get_or_create(event=event, type='husstand')
    del_url_solo = request.build_absolute_uri(f'/del/{dl_solo.token}/')
    del_url_husstand = request.build_absolute_uri(f'/del/{dl_husstand.token}/')

    # Afstemninger med stemmetal til admin-overblik
    afstemninger_admin = []
    for a in event.afstemninger.prefetch_related('valg', 'svar'):
        total = a.svar.count()
        valg_data = []
        for v in a.valg.all():
            antal = v.svar.count()
            valg_data.append({
                'id': v.pk,
                'tekst': v.tekst,
                'antal': antal,
                'pct': round(antal / total * 100) if total else 0,
                'stemmer': list(v.svar.values_list('navn', flat=True)),
            })
        afstemninger_admin.append({
            'id': a.pk,
            'spoergsmaal': a.spoergsmaal,
            'valg': valg_data,
            'total': total,
        })

    return render(request, 'events/overblik.html', {
        'event': event,
        'er_ejer': er_ejer,
        'tema_data': tema_data,
        'farve_baggrund': farve_baggrund,
        'moenster_css': moenster_css,
        'total_ja': total_ja,
        'total_maaske': total_maaske,
        'total_nej': total_nej,
        'total_afventer': total_afventer,
        'alle_ja': alle_ja,
        'alle_maaske': alle_maaske,
        'alle_nej': alle_nej,
        'alle_afventer': alle_afventer,
        'husstande': husstande,
        'del_url_solo': del_url_solo,
        'del_url_husstand': del_url_husstand,
        'kommentarer': event.kommentarer.all(),
        'afstemninger_admin': afstemninger_admin,
    })

@login_required
def send_invitationer(request, slug):
    if request.method != 'POST':
        return HttpResponseForbidden()

    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    # Send til solo-invitationer
    invitationer = event.invitation_set.filter(status='pending')
    ics_content = _generer_ics(event)
    for inv in invitationer:
        _send_html_mail(
            subject=f'Du er inviteret til {event.titel}',
            to=inv.email,
            template_prefix='invitation_solo',
            context={
                'navn': inv.navn,
                'event': event,
                'rsvp_url': request.build_absolute_uri(f'/rsvp/{inv.token}/'),
            },
            attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
        )

    # Send til husstandsmedlemmer med send_invitation=True og valid email
    for husstand in event.husstande.filter(status='pending'):
        er_solo = husstand.medlemmer.count() == 1
        for medlem in husstand.medlemmer.filter(send_invitation=True):
            if not (medlem.email and medlem.email.strip()):
                continue
            if er_solo:
                _send_html_mail(
                    subject=f'Du er inviteret til {event.titel}',
                    to=medlem.email,
                    template_prefix='invitation_solo',
                    context={
                        'navn': medlem.navn,
                        'event': event,
                        'rsvp_url': request.build_absolute_uri(f'/rsvp/{husstand.token}/'),
                    },
                    attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
                )
            else:
                _send_html_mail(
                    subject=f'Du er inviteret til {event.titel}',
                    to=medlem.email,
                    template_prefix='invitation_husstand',
                    context={
                        'navn': medlem.navn,
                        'husstand_navn': husstand.navn,
                        'event': event,
                        'rsvp_url': request.build_absolute_uri(f'/rsvp/{husstand.token}/'),
                    },
                    attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
                )

    sendte_invitationer = invitationer.count()
    sendte_husstandsmedlemmer = sum(
        1 for h in event.husstande.filter(status='pending')
        for m in h.medlemmer.filter(send_invitation=True)
        if m.email and m.email.strip()
    )

    messages.success(request, _('Sendte %(inv)d invitationer + %(husstand)d husstandsmedlemmer.') % {'inv': sendte_invitationer, 'husstand': sendte_husstandsmedlemmer})
    return redirect('event_overblik', slug=slug)


@login_required
def gensend_invitation_solo(request, slug, token):
    """Gensend invitation til en enkelt solo-deltager."""
    if request.method != 'POST':
        return HttpResponseForbidden()
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden()
    inv = get_object_or_404(Invitation, token=token, event=event)
    if not inv.email:
        messages.warning(request, _('%(navn)s har ingen email-adresse.') % {'navn': inv.navn})
        return redirect('event_overblik', slug=slug)
    ics_content = _generer_ics(event)
    _send_html_mail(
        subject=f'Du er inviteret til {event.titel}',
        to=inv.email,
        template_prefix='invitation_solo',
        context={
            'navn': inv.navn,
            'event': event,
            'rsvp_url': request.build_absolute_uri(f'/rsvp/{inv.token}/'),
        },
        attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
    )
    messages.success(request, _('Invitation gensendt til %(navn)s.') % {'navn': inv.navn})
    return redirect('event_overblik', slug=slug)


@login_required
def gensend_invitation_husstand(request, slug, token):
    """Gensend invitation til alle medlemmer af en husstand."""
    if request.method != 'POST':
        return HttpResponseForbidden()
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden()
    husstand = get_object_or_404(Husstand, token=token, event=event)
    ics_content = _generer_ics(event)
    sendt = 0
    er_solo = husstand.medlemmer.count() == 1
    for medlem in husstand.medlemmer.all():
        if not (medlem.email and medlem.email.strip()):
            continue
        if er_solo:
            _send_html_mail(
                subject=f'Du er inviteret til {event.titel}',
                to=medlem.email,
                template_prefix='invitation_solo',
                context={
                    'navn': medlem.navn,
                    'event': event,
                    'rsvp_url': request.build_absolute_uri(f'/rsvp/{husstand.token}/'),
                },
                attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
            )
        else:
            _send_html_mail(
                subject=f'Du er inviteret til {event.titel}',
                to=medlem.email,
                template_prefix='invitation_husstand',
                context={
                    'navn': medlem.navn,
                    'husstand_navn': husstand.navn,
                    'event': event,
                    'rsvp_url': request.build_absolute_uri(f'/rsvp/{husstand.token}/'),
                },
                attachment=(f'{event.slug}.ics', ics_content, 'text/calendar'),
            )
        sendt += 1
    if sendt:
        messages.success(request, _('Invitation gensendt til %(navn)s (%(n)d email).') % {'navn': husstand.navn, 'n': sendt})
    else:
        messages.warning(request, _('Ingen medlemmer af %(navn)s har en email-adresse.') % {'navn': husstand.navn})
    return redirect('event_overblik', slug=slug)


# ---------- INTERNE HJÆLPEFUNKTIONER ----------
def _send_afbud_mail_til_arrangør(invitation):
    event = invitation.event
    arrangor = event.oprettet_af
    if not arrangor or not arrangor.email:
        return
    ja_liste = list(event.invitation_set.filter(status='ja').order_by('navn').values_list('navn', flat=True))
    maaske_liste = list(event.invitation_set.filter(status='maaske').order_by('navn').values_list('navn', flat=True))
    _send_html_mail(
        subject=f'Afbud fra {invitation.navn} til {event.titel}',
        to=arrangor.email,
        template_prefix='afbud_arrangor',
        context={
            'arrangor': arrangor,
            'invitation': invitation,
            'event': event,
            'ja_liste': ja_liste,
            'maaske_liste': maaske_liste,
            'overblik_url': f'{settings.SITE_URL}/event/{event.slug}/',
        },
    )

def _send_afbud_mail_til_arrangør_husstand(husstand):
    """Sender afbudsmail til arrangøren for en husstand."""
    event = husstand.event
    arrangor = event.oprettet_af
    if not arrangor or not arrangor.email:
        return
    ja_liste = list(event.invitation_set.filter(status='ja').order_by('navn').values_list('navn', flat=True))
    ja_liste += list(husstand.medlemmer.filter(status='ja').order_by('navn').values_list('navn', flat=True))
    maaske_liste = list(event.invitation_set.filter(status='maaske').order_by('navn').values_list('navn', flat=True))
    if husstand.status == 'maaske':
        maaske_liste += list(husstand.medlemmer.all().order_by('navn').values_list('navn', flat=True))
    _send_html_mail(
        subject=f'Svar fra {husstand.navn} til {event.titel}',
        to=arrangor.email,
        template_prefix='afbud_arrangor_husstand',
        context={
            'arrangor': arrangor,
            'husstand': husstand,
            'event': event,
            'ja_liste': ja_liste,
            'maaske_liste': maaske_liste,
            'overblik_url': f'{settings.SITE_URL}/event/{event.slug}/',
        },
    )


# ---------- GÆSTEBOG ----------

def _parse_gaestebog_husstand_input(request):
    """Henter medlemsdata fra POST (navn, email, telefon)."""
    navne = request.POST.getlist('medlem_navn[]')
    emails = request.POST.getlist('medlem_email[]')
    telefoner = request.POST.getlist('medlem_telefon[]')
    result = []
    for i, navn in enumerate(navne):
        if not navn.strip():
            continue
        email = emails[i].strip() if i < len(emails) else ''
        telefon = telefoner[i].strip() if i < len(telefoner) else ''
        result.append((navn.strip(), email, telefon))
    return result


@login_required
def gaestebog(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            navn = form.cleaned_data['navn'].strip()
            email = (form.cleaned_data.get('email') or '').strip().lower()

            # Tjek: eksisterer allerede som solo kontakt?
            q_c = Q(navn__iexact=navn)
            if email:
                q_c |= Q(email__iexact=email)
            dup_c = Contact.objects.filter(user=request.user).filter(q_c).first()
            if dup_c:
                messages.info(request, _('"%(navn)s" findes allerede som solo kontakt i din gæstebog.') % {'navn': dup_c.navn})
                return redirect('gaestebog')

            # Tjek: eksisterer allerede som husstandsmedlem?
            q_m = Q(navn__iexact=navn)
            if email:
                q_m |= Q(email__iexact=email)
            dup_m = GaestebogMedlem.objects.filter(husstand__user=request.user).filter(q_m).first()
            if dup_m:
                messages.info(request, _('"%(navn)s" er allerede med i husstanden "%(husstand)s" i din gæstebog.') % {'navn': dup_m.navn, 'husstand': dup_m.husstand.navn})
                return redirect('gaestebog')

            kontakt = form.save(commit=False)
            kontakt.user = request.user
            kontakt.save()
            messages.success(request, _('%(navn)s er tilføjet til din gæstebog.') % {'navn': kontakt.navn})
            return redirect('gaestebog')
    else:
        form = ContactForm()

    egne = list(Contact.objects.filter(user=request.user).order_by('navn'))
    delte = list(Contact.objects.filter(shared_with=request.user).exclude(user=request.user).order_by('navn'))
    kontakter = egne + delte

    egne_husstande = GaestebogHusstand.objects.filter(user=request.user).prefetch_related('medlemmer').order_by('navn')
    delte_husstande = GaestebogHusstand.objects.filter(shared_with=request.user).exclude(user=request.user).prefetch_related('medlemmer').order_by('navn')
    husstande = list(egne_husstande) + list(delte_husstande)

    alle_brugere = User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by('first_name', 'last_name', 'username')

    alle_tags = set()
    for k in egne:
        alle_tags.update(k.tags_liste())
    for h in egne_husstande:
        alle_tags.update(h.tags_liste())

    return render(request, 'events/gaestebog.html', {
        'kontakter': kontakter,
        'husstande': husstande,
        'form': form,
        'alle_brugere': alle_brugere,
        'alle_tags': sorted(alle_tags),
    })


@login_required
def gaestebog_del(request):
    """Del en kontakt eller husstand med andre brugere."""
    if request.method != 'POST':
        return redirect('gaestebog')

    del_type = request.POST.get('del_type')
    try:
        pk = int(request.POST.get('pk', ''))
    except (TypeError, ValueError):
        return redirect('gaestebog')

    bruger_ids = [int(uid) for uid in request.POST.getlist('del_med_user_ids') if uid.strip().isdigit()]
    brugere = list(User.objects.filter(pk__in=bruger_ids, is_active=True))

    if not brugere:
        messages.warning(request, _('Vælg mindst én bruger at dele med.'))
        return redirect('gaestebog')

    if del_type == 'contact':
        kontakt = get_object_or_404(Contact, pk=pk, user=request.user)
        kontakt.shared_with.add(*brugere)
        navne = ', '.join(b.get_full_name() or b.username for b in brugere)
        messages.success(request, _('%(navn)s er nu delt med %(brugere)s.') % {'navn': kontakt.navn, 'brugere': navne})
    elif del_type == 'husstand':
        husstand = get_object_or_404(GaestebogHusstand, pk=pk, user=request.user)
        husstand.shared_with.add(*brugere)
        navne = ', '.join(b.get_full_name() or b.username for b in brugere)
        messages.success(request, _('%(navn)s er nu delt med %(brugere)s.') % {'navn': husstand.navn, 'brugere': navne})

    return redirect('gaestebog')


@login_required
def contact_rediger(request, pk):
    kontakt = get_object_or_404(Contact, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ContactForm(request.POST, instance=kontakt)
        if form.is_valid():
            form.save()
            messages.success(request, _('%(navn)s er opdateret.') % {'navn': kontakt.navn})
            return redirect('gaestebog')
    else:
        form = ContactForm(instance=kontakt)

    return render(request, 'events/contact_rediger.html', {
        'form': form,
        'kontakt': kontakt,
    })


@login_required
def contact_slet(request, pk):
    kontakt = get_object_or_404(Contact, pk=pk, user=request.user)

    if request.method == 'POST':
        navn = kontakt.navn
        kontakt.delete()
        messages.success(request, _('%(navn)s er slettet fra din gæstebog.') % {'navn': navn})
        return redirect('gaestebog')

    return render(request, 'events/contact_slet.html', {'kontakt': kontakt})


@login_required
def gaestebog_husstand_opret(request):
    if request.method == 'POST':
        form = GaestebogHusstandForm(request.POST)
        medlemmer = _parse_gaestebog_husstand_input(request)
        if not medlemmer:
            messages.error(request, _('Tilføj mindst ét husstandsmedlem.'))
        elif form.is_valid():
            husstand_navn = form.cleaned_data['navn'].strip()

            # Tjek: husstand med samme navn eksisterer allerede?
            dup_h = GaestebogHusstand.objects.filter(user=request.user, navn__iexact=husstand_navn).first()
            if dup_h:
                messages.info(request, _('Husstanden "%(navn)s" findes allerede i din gæstebog.') % {'navn': husstand_navn})
                return redirect('gaestebog')

            husstand = form.save(commit=False)
            husstand.user = request.user
            husstand.save()

            for navn, email, telefon in medlemmer:
                # Tjek: er dette medlem allerede en solo kontakt?
                q = Q(navn__iexact=navn)
                if email:
                    q |= Q(email__iexact=email)
                dup_c = Contact.objects.filter(user=request.user).filter(q).first()
                if dup_c:
                    messages.warning(request, _('"%(navn)s" findes allerede som solo kontakt og blev ikke tilføjet til husstanden.') % {'navn': dup_c.navn})
                    continue
                GaestebogMedlem.objects.create(
                    husstand=husstand,
                    navn=navn,
                    email=email if email else None,
                    telefon=telefon,
                )

            messages.success(request, _('Husstanden "%(navn)s" er oprettet.') % {'navn': husstand.navn})
            return redirect('gaestebog')
        _, _, alle_tags = _hent_gaestebog_data(request.user)
        return render(request, 'events/gaestebog_husstand_form.html', {
            'form': form,
            'titel': 'Opret husstand',
            'medlemmer': medlemmer,
            'alle_tags': alle_tags,
        })
    return redirect('gaestebog')


@login_required
def gaestebog_husstand_rediger(request, pk):
    husstand = get_object_or_404(GaestebogHusstand, pk=pk, user=request.user)

    if request.method == 'POST':
        form = GaestebogHusstandForm(request.POST, instance=husstand)
        medlemmer = _parse_gaestebog_husstand_input(request)
        if not medlemmer:
            messages.error(request, _('En husstand skal have mindst ét medlem.'))
        elif form.is_valid():
            form.save()
            husstand.medlemmer.all().delete()
            for navn, email, telefon in medlemmer:
                q = Q(navn__iexact=navn)
                if email:
                    q |= Q(email__iexact=email)
                dup_c = Contact.objects.filter(user=request.user).filter(q).first()
                if dup_c:
                    messages.warning(request, _('"%(navn)s" findes allerede som solo kontakt og blev ikke tilføjet til husstanden.') % {'navn': dup_c.navn})
                    continue
                GaestebogMedlem.objects.create(
                    husstand=husstand,
                    navn=navn,
                    email=email if email else None,
                    telefon=telefon,
                )
            messages.success(request, _('Husstanden "%(navn)s" er opdateret.') % {'navn': husstand.navn})
            return redirect('gaestebog')
    else:
        form = GaestebogHusstandForm(instance=husstand)
        medlemmer = [(m.navn, m.email or '', m.telefon) for m in husstand.medlemmer.all()]

    _, _, alle_tags = _hent_gaestebog_data(request.user)
    return render(request, 'events/gaestebog_husstand_form.html', {
        'form': form,
        'husstand': husstand,
        'titel': f'Redigér {husstand.navn}',
        'medlemmer': [(m.navn, m.email or '', m.telefon) for m in husstand.medlemmer.all()],
        'alle_tags': alle_tags,
    })


@login_required
def gaestebog_husstand_slet(request, pk):
    husstand = get_object_or_404(GaestebogHusstand, pk=pk, user=request.user)

    if request.method == 'POST':
        navn = husstand.navn
        husstand.delete()
        messages.success(request, _('Husstanden "%(navn)s" er slettet fra din gæstebog.') % {'navn': navn})
        return redirect('gaestebog')

    return render(request, 'events/gaestebog_husstand_slet.html', {'husstand': husstand})


@login_required
def event_gaestebog_import(request, slug):
    """Vælg kontakter/husstande fra gæstebog og tilføj dem til et event."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        tilfoejede = _tilfoej_gaestebog_til_event(request, event)
        messages.success(request, _('%(n)d gæst(er) tilføjet til eventet.') % {'n': tilfoejede})
        return redirect('event_overblik', slug=event.slug)

    kontakter, husstande, alle_tags = _hent_gaestebog_data(request.user)
    return render(request, 'events/event_gaestebog_import.html', {
        'event': event,
        'kontakter': kontakter,
        'husstande': husstande,
        'alle_tags': alle_tags,
    })

# ---------- KOMMENTARSPOR ----------

def _gaest_navn_fra_token(token):
    """Returnerer gæstens visningsnavn ud fra et invitation- eller husstand-token."""
    inv = Invitation.objects.filter(token=token).first()
    if inv:
        return inv.navn
    husstand = Husstand.objects.filter(token=token).first()
    if husstand:
        if husstand.medlemmer.count() == 1:
            return husstand.medlemmer.first().navn
        return husstand.navn
    return None


def _afstemning_kontekst(event, token):
    """Returnerer afstemninger med stemmetal og gæstens eget svar."""
    result = []
    for a in event.afstemninger.prefetch_related('valg', 'svar'):
        mit_svar = a.svar.filter(token=token).first()
        total = a.svar.count()
        valg_data = []
        for v in a.valg.all():
            antal = v.svar.count()
            valg_data.append({
                'id': v.pk,
                'tekst': v.tekst,
                'antal': antal,
                'pct': round(antal / total * 100) if total else 0,
                'valgt': bool(mit_svar and mit_svar.valg_id == v.pk),
            })
        result.append({
            'id': a.pk,
            'spoergsmaal': a.spoergsmaal,
            'valg': valg_data,
            'total': total,
            'har_stemt': bool(mit_svar),
        })
    return result


def kommentar_opret(request, token):
    """POST: gæst opretter en kommentar via sit RSVP-token."""
    from datetime import timedelta
    inv = Invitation.objects.filter(token=token).first()
    husstand = None if inv else Husstand.objects.filter(token=token).first()
    if not inv and not husstand:
        return HttpResponseBadRequest('Ugyldigt token.')

    event = inv.event if inv else husstand.event

    if request.method == 'POST' and event.kommentarer_aktiveret:
        # Max 10 kommentarer per token per event per time
        en_time_siden = timezone.now() - timedelta(hours=1)
        if Kommentar.objects.filter(token=token, event=event, oprettet__gte=en_time_siden).count() < 10:
            form = KommentarForm(request.POST)
            if form.is_valid():
                navn = _gaest_navn_fra_token(token) or 'Gæst'
                Kommentar.objects.create(
                    event=event,
                    token=token,
                    navn=navn,
                    tekst=form.cleaned_data['tekst'].strip(),
                )
    return redirect('rsvp_oversigt', token=token)


def afstemning_stem(request, token, pk):
    """POST: gæst afgiver en stemme på en afstemning."""
    inv = Invitation.objects.filter(token=token).first()
    husstand = None if inv else Husstand.objects.filter(token=token).first()
    if not inv and not husstand:
        return HttpResponseBadRequest('Ugyldigt token.')

    event = inv.event if inv else husstand.event
    afstemning = get_object_or_404(Afstemning, pk=pk, event=event)

    if request.method == 'POST' and event.afstemning_aktiveret:
        try:
            valg_id = int(request.POST.get('valg', ''))
        except (TypeError, ValueError):
            return redirect('rsvp_oversigt', token=token)
        valg = get_object_or_404(AfstemningValg, pk=valg_id, afstemning=afstemning)
        navn = _gaest_navn_fra_token(token) or 'Gæst'
        AfstemningsSvar.objects.update_or_create(
            afstemning=afstemning,
            token=token,
            defaults={'valg': valg, 'navn': navn},
        )
    return redirect('rsvp_oversigt', token=token)


# ---------- AFLYSNING + ARKIVERING ----------

@login_required
def event_aflys(request, slug):
    """Aflys et event og send forklaringsmail til alle gæster med email."""
    event = get_object_or_404(Event, slug=slug)
    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id
    if not er_ejer:
        return HttpResponseForbidden('Kun ejeren kan aflyse et event.')
    if event.aflyst:
        return redirect('event_overblik', slug=slug)

    if request.method == 'POST':
        besked = request.POST.get('aflysning_besked', '').strip()
        event.aflyst = True
        event.aflysning_besked = besked
        event.save(update_fields=['aflyst', 'aflysning_besked'])

        # Send til alle gæster med email (solo-invitationer)
        for inv in event.invitation_set.exclude(email=''):
            _send_html_mail(
                subject=f'Aflysning: {event.titel}',
                to=inv.email,
                template_prefix='aflysning',
                context={'navn': inv.navn, 'event': event},
            )
        # Send til husstandsmedlemmer med email
        sendte_emails = set(event.invitation_set.values_list('email', flat=True))
        for husstand in event.husstande.all():
            for medlem in husstand.medlemmer.exclude(email='').exclude(email__isnull=True):
                if medlem.email not in sendte_emails:
                    er_solo = husstand.medlemmer.count() == 1
                    navn = medlem.navn if er_solo else husstand.navn
                    _send_html_mail(
                        subject=f'Aflysning: {event.titel}',
                        to=medlem.email,
                        template_prefix='aflysning',
                        context={'navn': navn, 'event': event},
                    )
                    sendte_emails.add(medlem.email)

        messages.success(request, _('"%(titel)s" er markeret som aflyst og gæsterne er notificeret.') % {'titel': event.titel})
        return redirect('event_overblik', slug=slug)

    return render(request, 'events/event_aflys.html', {'event': event})


@login_required
def event_arkiver(request, slug):
    """Arkivér et event så det skjules fra dashboardet."""
    event = get_object_or_404(Event, slug=slug)
    er_ejer = request.user.is_superuser or event.oprettet_af_id == request.user.id
    if not er_ejer:
        return HttpResponseForbidden('Kun ejeren kan arkivere et event.')
    if request.method == 'POST':
        event.arkiveret = True
        event.save(update_fields=['arkiveret'])
        messages.success(request, _('"%(titel)s" er arkiveret.') % {'titel': event.titel})
        return redirect('dashboard')
    return redirect('event_overblik', slug=slug)


# ---------- AFSTEMNINGS-ADMINISTRATION (kun for arrangør) ----------

@login_required
def afstemning_opret(request, slug):
    """POST: arrangør opretter en ny afstemning med svarmuligheder."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        spoergsmaal = request.POST.get('spoergsmaal', '').strip()
        svarmuligheder = [s.strip() for s in request.POST.getlist('svar') if s.strip()]
        if spoergsmaal and len(svarmuligheder) >= 2:
            a = Afstemning.objects.create(event=event, spoergsmaal=spoergsmaal)
            for tekst in svarmuligheder:
                AfstemningValg.objects.create(afstemning=a, tekst=tekst)
            messages.success(request, _('Afstemning oprettet.'))
        else:
            messages.error(request, _('Angiv et spørgsmål og mindst 2 svarmuligheder.'))
    return redirect('event_overblik', slug=slug)


@login_required
def afstemning_slet(request, slug, pk):
    """POST: arrangør sletter en afstemning."""
    event = get_object_or_404(Event, slug=slug)
    if not event.kan_ses_af(request.user):
        return HttpResponseForbidden('Du har ikke adgang til dette event.')

    if request.method == 'POST':
        afstemning = get_object_or_404(Afstemning, pk=pk, event=event)
        afstemning.delete()
        messages.success(request, _('Afstemning slettet.'))
    return redirect('event_overblik', slug=slug)


# ---------- PWA ----------

def manifest_json(request):
    from django.http import JsonResponse
    data = {
        'name': 'Vibe Invite',
        'short_name': 'Vibe Invite',
        'description': 'Invitér og hold styr på dine events',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#f8f9fa',
        'theme_color': '#212529',
        'lang': 'da',
        'icons': [
            {
                'src': request.build_absolute_uri('/static/events/icons/icon-192.svg'),
                'sizes': '192x192',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            },
            {
                'src': request.build_absolute_uri('/static/events/icons/icon-512.svg'),
                'sizes': '512x512',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            },
        ],
    }
    return JsonResponse(data, content_type='application/manifest+json')


def service_worker(request):
    from django.http import HttpResponse
    js = """
const CACHE = 'events-v1';
const STATIC_ASSETS = [
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Cache-first for CDN static assets
  if (url.hostname.includes('cdn.jsdelivr.net')) {
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }))
    );
    return;
  }
  // Network-first for app pages (graceful offline fallback)
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  }
});
""".strip()
    return HttpResponse(js, content_type='application/javascript')


@login_required
def force_password_change(request):
    """Force user to change password when must_change_password is set."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()
            messages.success(request, _('Din adgangskode er ændret.'))
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'events/force_password_change.html', {'form': form})


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)

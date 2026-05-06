from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
import uuid

def _dansk_slugify(tekst):
    """Dansk-venlig slugify: oversætter æøå før Django's slugify."""
    return slugify(
        tekst
        .replace('æ', 'ae').replace('Æ', 'Ae')
        .replace('ø', 'oe').replace('Ø', 'Oe')
        .replace('å', 'aa').replace('Å', 'Aa')
    )

TEMA_VALG = [
    ('standard', _('Standard')),
    ('foedselsdag', _('Fødselsdag')),
    ('fest', _('Fest / Nytår')),
    ('barnedag', _('Barnedåb')),
    ('bryllup', _('Bryllup')),
    ('jul', _('Jul')),
    ('paaske', _('Påske')),
    ('sommer', _('Sommerfest')),
]

class UserProfile(models.Model):
    """Extra user fields — tracks whether a password change is required."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Event(models.Model):
    titel = models.CharField(max_length=200)
    beskrivelse = models.TextField(blank=True)
    dato = models.DateTimeField()
    sted = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sidste_svardag = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Efter denne dato kan gæster kun ændre svar fra "ja" til "nej"'
    )
    oprettet = models.DateTimeField(auto_now_add=True)
    oprettet_af = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mine_events',
        null=True,
        blank=True,
    )
    medredaktorer = models.ManyToManyField(
        User,
        related_name='redaktor_for_events',
        blank=True,
        help_text='Andre brugere der må se og redigere dette event.',
    )
    tema = models.CharField(max_length=20, choices=TEMA_VALG, default='standard', verbose_name=_('Tema'))
    baggrundsbillede = models.ImageField(
        upload_to='event_baggrunde/', blank=True, null=True,
        verbose_name=_('Baggrundsbillede'),
        help_text=_('Vises i headeren på RSVP-siden (anbefalet: 1200×400 px).')
    )
    oenskeliste_url = models.URLField(
        blank=True,
        verbose_name=_('Ønskeliste-link'),
        help_text=_('Link til ønskeliste (fx Ønskeskyen.dk). Vises på RSVP-siden.')
    )
    farve_baggrund = models.CharField(
        max_length=7, default='#ffffff', blank=True,
        verbose_name=_('Baggrundsfarve'),
        help_text=_('Sidens baggrundsfarve (standard: hvid).')
    )
    farve_moenster = models.CharField(
        max_length=7, default='', blank=True,
        verbose_name=_('Mønsterfarve'),
        help_text=_('Farve på illustrationerne i baggrunden. Tom = brug tema-farve.')
    )

    REMINDER_INTERVAL_VALG = [
        (0, _('Ingen yderligere reminders')),
        (1, _('Hver dag')),
        (2, _('Hver 2. dag')),
        (3, _('Hver 3. dag')),
        (7, _('Ugentlig')),
    ]
    reminder_dage_foer = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_('Send første reminder'),
        help_text=_('Antal dage før eventet den første reminder-mail sendes til "måske"-gæster.')
    )
    reminder_interval = models.PositiveIntegerField(
        null=True, blank=True,
        choices=REMINDER_INTERVAL_VALG,
        verbose_name=_('Efterfølgende reminders'),
        help_text=_('Hvor ofte skal der sendes yderligere reminders efter den første?')
    )
    kommentarer_aktiveret = models.BooleanField(
        default=True,
        verbose_name=_('Kommentarspor aktiveret'),
        help_text=_('Gæster kan skrive kommentarer på RSVP-siden.')
    )
    afstemning_aktiveret = models.BooleanField(
        default=True,
        verbose_name=_('Afstemning aktiveret'),
        help_text=_('Gæster kan stemme på afstemninger på RSVP-siden.')
    )
    aflyst = models.BooleanField(default=False, verbose_name=_('Aflyst'))
    aflysning_besked = models.TextField(
        blank=True,
        verbose_name=_('Besked til gæsterne'),
        help_text=_('Vises i aflysningsmailen og på RSVP-siden.')
    )
    arkiveret = models.BooleanField(default=False, verbose_name=_('Arkiveret'))

    def __str__(self):
        return self.titel

    def kan_ses_af(self, user):
        """Må denne bruger se og redigere eventet?"""
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.oprettet_af_id == user.id:
            return True
        return self.medredaktorer.filter(pk=user.pk).exists()

    def svarfrist_passeret(self):
        if not self.sidste_svardag:
            return False
        return timezone.now() > self.sidste_svardag

class Invitation(models.Model):
    """Solo-invitation til en enkelt gæst."""
    STATUS = [
        ('pending', _('Afventer')),
        ('ja', _('Deltager')),
        ('nej', _('Deltager ikke')),
        ('maaske', _('Måske')),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    navn = models.CharField(max_length=100)
    email = models.EmailField()
    token = models.SlugField(unique=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    afbud_aarsag = models.TextField(
        blank=True,
        help_text='Udfyldes hvis gæsten melder afbud efter svarfristen.'
    )
    svar_opdateret = models.DateTimeField(null=True, blank=True)
    reminder_sendt = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            basis = _dansk_slugify(self.navn)
            kandidat = basis
            while Invitation.objects.filter(token=kandidat).exists() or Husstand.objects.filter(token=kandidat).exists():
                kandidat = f"{basis}-{str(uuid.uuid4())[:4]}"
            self.token = kandidat
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.navn} - {self.event.titel}"

class Husstand(models.Model):
    """En gruppe af personer der inviteres samlet og deler ét RSVP-link."""
    STATUS = [
        ('pending', _('Afventer')),
        ('maaske', _('Måske (hele husstanden)')),
        ('individuelt', _('Svar afgivet individuelt')),
        ('nej', _('Hele husstanden kommer ikke')),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='husstande')
    navn = models.CharField(max_length=200, help_text='Fx "Familien Hansen"')
    token = models.SlugField(unique=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default='pending')
    afbud_aarsag = models.TextField(
        blank=True,
        help_text='Udfyldes hvis husstanden melder afbud efter svarfristen.'
    )
    svar_opdateret = models.DateTimeField(null=True, blank=True)
    oprettet = models.DateTimeField(auto_now_add=True)
    reminder_sendt = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            basis = _dansk_slugify(self.navn)
            kandidat = basis
            while Husstand.objects.filter(token=kandidat).exists() or Invitation.objects.filter(token=kandidat).exists():
                kandidat = f"{basis}-{str(uuid.uuid4())[:4]}"
            self.token = kandidat
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.navn} - {self.event.titel}"

    def antal_medlemmer(self):
        return self.medlemmer.count()

    def antal_ja(self):
        return self.medlemmer.filter(status='ja').count()

    def antal_nej(self):
        return self.medlemmer.filter(status='nej').count()

class Husstandsmedlem(models.Model):
    """Et enkelt medlem af en husstand. Kan svare ja/nej og have sin egen email."""
    STATUS = [
        ('pending', _('Afventer')),
        ('ja', _('Deltager')),
        ('nej', _('Deltager ikke')),
    ]
    husstand = models.ForeignKey(Husstand, on_delete=models.CASCADE, related_name='medlemmer')
    navn = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True, help_text='Email til dette medlem (valgfrit).')
    send_invitation = models.BooleanField(
        default=True,
        help_text='Skal invitation sendes til denne email?'
    )
    status = models.CharField(max_length=10, choices=STATUS, default='pending')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.navn} ({self.husstand.navn})"


class Contact(models.Model):
    """En kontakt i brugerens gæstebog."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kontakter')
    navn = models.CharField(max_length=100)
    email = models.EmailField()
    telefon = models.CharField(max_length=20, blank=True)
    noter = models.TextField(blank=True)
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text='Kommaseparerede tags, fx "familie, venner"'
    )
    oprettet = models.DateTimeField(auto_now_add=True)
    sidst_opdateret = models.DateTimeField(auto_now=True)
    shared_with = models.ManyToManyField(
        User,
        related_name='delte_kontakter',
        blank=True,
    )

    class Meta:
        ordering = ['navn']
        constraints = [
            models.UniqueConstraint(fields=['user', 'email'], name='unique_contact_per_user')
        ]

    def __str__(self):
        return f"{self.navn} ({self.email})"

    def tags_liste(self):
        """Returnerer tags som en liste af strenge."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class GaestebogHusstand(models.Model):
    """En husstand i brugerens gæstebog – ikke event-specifik, kan genbruges."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gaestebog_husstande')
    navn = models.CharField(max_length=200, help_text='Fx "Familien Hansen"')
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text='Kommaseparerede tags, fx "familie, venner"'
    )
    shared_with = models.ManyToManyField(
        User,
        related_name='delte_husstande',
        blank=True,
    )
    oprettet = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['navn']

    def __str__(self):
        return self.navn

    def antal_medlemmer(self):
        return self.medlemmer.count()

    def tags_liste(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class Delelink(models.Model):
    """Et delelink der giver modtageren mulighed for at tilmelde sig selv."""
    TYPE_VALG = [
        ('solo', _('Solo')),
        ('husstand', _('Husstand')),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='delelinks')
    token = models.SlugField(max_length=12, unique=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_VALG)
    oprettet = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('event', 'type')]

    def save(self, *args, **kwargs):
        if not self.token:
            kandidat = str(uuid.uuid4())[:8]
            while Delelink.objects.filter(token=kandidat).exists():
                kandidat = str(uuid.uuid4())[:8]
            self.token = kandidat
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.titel} – {self.get_type_display()}"


class GaestebogMedlem(models.Model):
    """Et enkelt medlem af en husstand i gæstebogen."""
    husstand = models.ForeignKey(GaestebogHusstand, on_delete=models.CASCADE, related_name='medlemmer')
    navn = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telefon = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.navn} ({self.husstand.navn})"


class Kommentar(models.Model):
    """En kommentar skrevet af en gæst på RSVP-siden."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='kommentarer')
    token = models.CharField(max_length=50)  # invitation- eller husstand-token
    navn = models.CharField(max_length=100)
    tekst = models.TextField(max_length=1000)
    oprettet = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['oprettet']

    def __str__(self):
        return f"{self.navn}: {self.tekst[:40]}"


class Afstemning(models.Model):
    """En afstemning knyttet til et event."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='afstemninger')
    spoergsmaal = models.CharField(max_length=300, verbose_name=_('Spørgsmål'))
    oprettet = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['oprettet']

    def __str__(self):
        return self.spoergsmaal


class AfstemningValg(models.Model):
    """Et svarmulighed i en afstemning."""
    afstemning = models.ForeignKey(Afstemning, on_delete=models.CASCADE, related_name='valg')
    tekst = models.CharField(max_length=200)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.tekst


class AfstemningsSvar(models.Model):
    """En gæsts svar på en afstemning. Én stemme pr. gæst pr. afstemning."""
    afstemning = models.ForeignKey(Afstemning, on_delete=models.CASCADE, related_name='svar')
    valg = models.ForeignKey(AfstemningValg, on_delete=models.CASCADE, related_name='svar')
    token = models.CharField(max_length=50)  # invitation- eller husstand-token
    navn = models.CharField(max_length=100)

    class Meta:
        unique_together = [('afstemning', 'token')]

    def __str__(self):
        return f"{self.navn} → {self.valg.tekst}"
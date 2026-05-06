from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Invitation, Husstandsmedlem, Contact, GaestebogHusstand, GaestebogMedlem


@receiver(post_save, sender=Invitation)
def opret_kontakt_fra_invitation(sender, instance, created, **kwargs):
    """Opret Contact for event-ejer (og medredaktører) når en solo-invitation oprettes."""
    if not created:
        return
    if not instance.email:
        return

    event = instance.event
    brugere = list(event.medredaktorer.all())
    if event.oprettet_af:
        brugere.append(event.oprettet_af)

    for bruger in brugere:
        try:
            Contact.objects.get_or_create(
                user=bruger,
                email=instance.email,
                defaults={
                    'navn': instance.navn,
                    'noter': f'Inviteret til: {event.titel}',
                }
            )
        except Exception:
            pass


@receiver(post_save, sender=Husstandsmedlem)
def opret_gaestebog_husstand_fra_husstandsmedlem(sender, instance, created, **kwargs):
    """
    Når et husstandsmedlem oprettes på et event, spejles det i ejerens gæstebog
    som en GaestebogHusstand med GaestebogMedlem – uanset om medlemmet har email.
    Matcher på husstandens navn, så samme familie på tværs af events samles ét sted.
    """
    if not created:
        return

    husstand = instance.husstand
    event = husstand.event
    if not event.oprettet_af:
        return

    bruger = event.oprettet_af

    try:
        gb_husstand, _ = GaestebogHusstand.objects.get_or_create(
            user=bruger,
            navn=husstand.navn,
        )
        # Tilføj kun hvis der ikke allerede er et medlem med samme navn
        if not gb_husstand.medlemmer.filter(navn=instance.navn).exists():
            GaestebogMedlem.objects.create(
                husstand=gb_husstand,
                navn=instance.navn,
                email=instance.email or None,
                telefon='',
            )
    except Exception:
        pass

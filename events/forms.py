from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Event, Invitation, Husstand, Contact, GaestebogHusstand, Afstemning, AfstemningValg, _dansk_slugify

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=30, required=True, label='Fornavn')
    last_name = forms.CharField(max_length=30, required=True, label='Efternavn')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = False  # venter på admin-godkendelse
        if commit:
            user.save()
        return user

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('titel', 'beskrivelse', 'dato', 'sted', 'sidste_svardag', 'slug',
                  'tema', 'baggrundsbillede', 'oenskeliste_url',
                  'farve_baggrund', 'farve_moenster',
                  'reminder_dage_foer', 'reminder_interval',
                  'kommentarer_aktiveret', 'afstemning_aktiveret')
        widgets = {
            'dato': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'sidste_svardag': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'beskrivelse': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'id': 'id_slug', 'class': 'form-control'}),
            'titel': forms.TextInput(attrs={'id': 'id_titel', 'class': 'form-control'}),
            'oenskeliste_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'baggrundsbillede': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'farve_baggrund': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'farve_moenster': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'reminder_dage_foer': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '365', 'placeholder': 'Fx 14'}),
            'reminder_interval': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'slug': 'Kort URL-navn til eventet. Udfyldes automatisk ud fra titlen.',
            'oenskeliste_url': 'Link til ønskeliste (fx Ønskeskyen.dk). Vises på RSVP-siden.',
            'baggrundsbillede': 'Vises i headeren på RSVP-siden (anbefalet: 1200×400 px).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['baggrundsbillede'].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        titel = self.cleaned_data.get('titel', '')
        if not slug and titel:
            slug = _dansk_slugify(titel)
            qs = Event.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Det kort-navn er allerede brugt - vælg et andet.')
        return slug

class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ('navn', 'email', 'token')
        widgets = {
            'navn': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_navn'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'token': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_token'}),
        }
        help_texts = {
            'token': 'Genereres automatisk fra navnet. Bruges i gæstens invitationslink.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['token'].required = False

class HusstandForm(forms.ModelForm):
    """Form til at oprette/redigere en husstand."""
    class Meta:
        model = Husstand
        fields = ('navn', 'token')
        widgets = {
            'navn': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_navn',
                'placeholder': 'Fx Familien Hansen'
            }),
            'token': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_token'
            }),
        }
        help_texts = {
            'token': 'Genereres automatisk fra navnet. Bruges i husstandens fælles invitationslink.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['token'].required = False

class AfbudEfterFristForm(forms.Form):
    """Bruges når en gæst vil ændre svar fra 'ja' til 'nej' efter fristen."""
    aarsag = forms.CharField(
        label='Hvorfor kan du ikke komme alligevel?',
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=True,
        min_length=5,
    )


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ('navn', 'email', 'telefon', 'noter', 'tags')
        widgets = {
            'navn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Navn'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefon (valgfrit)'}),
            'noter': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Noter (valgfrit)'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tags, fx "familie, venner"'}),
        }
        labels = {
            'noter': 'Noter',
            'tags': 'Tags',
        }


class GaestebogHusstandForm(forms.ModelForm):
    class Meta:
        model = GaestebogHusstand
        fields = ('navn', 'tags')
        widgets = {
            'navn': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Fx Familien Hansen',
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tags, fx "familie, venner"',
            }),
        }


class KommentarForm(forms.Form):
    tekst = forms.CharField(
        label='',
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Skriv en kommentar…',
        }),
    )


class AfstemningOpretForm(forms.Form):
    spoergsmaal = forms.CharField(
        label='Spørgsmål',
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Fx: Hvad skal vi spise?',
        }),
    )
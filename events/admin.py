from django.contrib import admin
from .models import Event, Invitation, Husstand, Husstandsmedlem, Contact, GaestebogHusstand, GaestebogMedlem

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('titel',)}
    list_display = ('titel', 'dato', 'sidste_svardag', 'oprettet_af')
    list_filter = ('oprettet_af',)
    filter_horizontal = ('medredaktorer',)

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('navn', 'event', 'status', 'svar_opdateret')
    list_filter = ('status', 'event')
    fields = ('event', 'navn', 'email', 'status', 'token', 'afbud_aarsag', 'svar_opdateret')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('token', 'svar_opdateret')
        return ('svar_opdateret',)

    class Media:
        js = ('admin/js/invitation_token.js',)

class HusstandsmedlemInline(admin.TabularInline):
    model = Husstandsmedlem
    extra = 1
    fields = ('navn', 'email', 'send_invitation', 'status')

@admin.register(Husstand)
class HusstandAdmin(admin.ModelAdmin):
    list_display = ('navn', 'event', 'status', 'antal_medlemmer', 'svar_opdateret')
    list_filter = ('status', 'event')
    fields = ('event', 'navn', 'token', 'status', 'afbud_aarsag', 'svar_opdateret')
    inlines = [HusstandsmedlemInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('token', 'svar_opdateret')
        return ('svar_opdateret',)

    def antal_medlemmer(self, obj):
        return obj.antal_medlemmer()
    antal_medlemmer.short_description = 'Medlemmer'


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('navn', 'email', 'telefon', 'user', 'oprettet')
    list_filter = ('user',)
    search_fields = ('navn', 'email', 'tags')
    filter_horizontal = ('shared_with',)
    readonly_fields = ('oprettet', 'sidst_opdateret')


class GaestebogMedlemInline(admin.TabularInline):
    model = GaestebogMedlem
    extra = 1
    fields = ('navn', 'email', 'telefon')


@admin.register(GaestebogHusstand)
class GaestebogHusstandAdmin(admin.ModelAdmin):
    list_display = ('navn', 'user', 'antal_medlemmer', 'oprettet')
    list_filter = ('user',)
    search_fields = ('navn',)
    inlines = [GaestebogMedlemInline]

    def antal_medlemmer(self, obj):
        return obj.antal_medlemmer()
    antal_medlemmer.short_description = 'Medlemmer'
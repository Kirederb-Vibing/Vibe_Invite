from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('signup/', views.signup, name='signup'),
    path('bruger/accepter/<str:token>/', views.bruger_accepter, name='bruger_accepter'),
    path('bruger/afvis/<str:token>/', views.bruger_afvis, name='bruger_afvis'),
    path('login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('skift-adgangskode/', views.force_password_change, name='force_password_change'),

    # Dashboard + event-administration
    path('', views.dashboard, name='dashboard'),
    path('event/ny/', views.event_opret, name='event_opret'),
    path('event/<slug:slug>/rediger/', views.event_rediger, name='event_rediger'),
    path('event/<slug:slug>/slet/', views.event_slet, name='event_slet'),

    # Solo-deltagere
    path('event/<slug:slug>/deltager/ny/', views.deltager_opret, name='deltager_opret'),
    path('event/<slug:slug>/deltager/<slug:token>/', views.deltager_rediger, name='deltager_rediger'),

    # Husstande
    path('event/<slug:slug>/husstand/ny/', views.husstand_opret, name='husstand_opret'),
    path('event/<slug:slug>/husstand/<slug:token>/', views.husstand_rediger, name='husstand_rediger'),
    path('event/<slug:slug>/husstand/<slug:token>/slet/', views.husstand_slet, name='husstand_slet'),

    # Medredaktører
    path('event/<slug:slug>/medredaktorer/tilfoej/', views.medredaktor_tilfoej, name='medredaktor_tilfoej'),
    path('event/<slug:slug>/medredaktorer/<int:user_id>/fjern/', views.medredaktor_fjern, name='medredaktor_fjern'),

    # Event overblik + send
    path('event/<slug:slug>/', views.event_overblik, name='event_overblik'),
    path('event/<slug:slug>/send/', views.send_invitationer, name='send_invitationer'),
    path('event/<slug:slug>/aflys/', views.event_aflys, name='event_aflys'),
    path('event/<slug:slug>/arkiver/', views.event_arkiver, name='event_arkiver'),
    path('event/<slug:slug>/kalender.ics', views.event_ics, name='event_ics'),

    # Delelink (offentlig selvtilmelding)
    path('del/<slug:token>/', views.del_rsvp, name='del_rsvp'),

    # RSVP (offentlig)
    path('rsvp/<slug:token>/', views.rsvp, name='rsvp'),
    path('rsvp/<slug:token>/oversigt/', views.rsvp_oversigt, name='rsvp_oversigt'),
    path('rsvp/<slug:token>/tak/', views.rsvp_bekræftet, name='rsvp_bekræftet'),

    # Gæstebog – solo kontakter
    path('gaestebog/', views.gaestebog, name='gaestebog'),
    path('gaestebog/kontakt/<int:pk>/rediger/', views.contact_rediger, name='contact_rediger'),
    path('gaestebog/kontakt/<int:pk>/slet/', views.contact_slet, name='contact_slet'),

    # Gæstebog – husstande
    path('gaestebog/husstand/ny/', views.gaestebog_husstand_opret, name='gaestebog_husstand_opret'),
    path('gaestebog/husstand/<int:pk>/rediger/', views.gaestebog_husstand_rediger, name='gaestebog_husstand_rediger'),
    path('gaestebog/husstand/<int:pk>/slet/', views.gaestebog_husstand_slet, name='gaestebog_husstand_slet'),

    # Deling
    path('gaestebog/del/', views.gaestebog_del, name='gaestebog_del'),

    # Import fra gæstebog til event
    path('event/<slug:slug>/fra-gaestebog/', views.event_gaestebog_import, name='event_gaestebog_import'),

    # Afstemninger (admin)
    path('event/<slug:slug>/afstemning/ny/', views.afstemning_opret, name='afstemning_opret'),
    path('event/<slug:slug>/afstemning/<int:pk>/slet/', views.afstemning_slet, name='afstemning_slet'),

    # Kommentarer + afstemning-stemmer (gæster via RSVP-token)
    path('rsvp/<slug:token>/kommentar/', views.kommentar_opret, name='kommentar_opret'),
    path('rsvp/<slug:token>/afstemning/<int:pk>/stem/', views.afstemning_stem, name='afstemning_stem'),

    # PWA
    path('manifest.json', views.manifest_json, name='manifest_json'),
    path('sw.js', views.service_worker, name='service_worker'),
]
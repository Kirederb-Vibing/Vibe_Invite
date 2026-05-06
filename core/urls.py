from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.conf.urls.i18n import i18n_patterns
import django.views.i18n


def healthz(request):
    return JsonResponse({'status': 'ok'})


handler404 = 'events.views.error_404'
handler500 = 'events.views.error_500'

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path(settings.ADMIN_URL, admin.site.urls),
    path('healthz/', healthz, name='healthz'),
    path('', include('events.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
BookBridge URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # BookBridge Core Applications
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('ngos/', include('apps.ngos.urls', namespace='ngos')),
    path('donations/', include('apps.donations.urls', namespace='donations')),
    path('', include('apps.inventory.urls', namespace='inventory')),
    path('', include('apps.requests.urls', namespace='requests')),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# proyecto/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def admin_login_redirect(request):
    """Redirect /admin/login/ to the project's login page, preserving ?next="""
    next_param = request.GET.get('next', '/')
    return redirect(f'/iniciar_sesion/?next={next_param}')

urlpatterns = [
    path('admin/login/', admin_login_redirect, name='admin_login_redirect'),
    path('admin/', admin.site.urls),
    path('', include('jugadores.urls')),
]

# IMPORTANTE: Esto es para servir archivos multimedia en modo de desarrollo.
# Esta configuración es necesaria para que las imágenes subidas se muestren.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

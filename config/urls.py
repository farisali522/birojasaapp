from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('xxx/', admin.site.urls),
    path('', include('core.urls')),
]

# --- KONFIGURASI WAJIB UNTUK MEDIA & STATIC ---

# 1. Saat Mode Development (DEBUG = True) -> Laptop Anda
if settings.DEBUG:
    # Sajikan File Media (Upload User)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Sajikan File Static (CSS/JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 2. Saat Mode Production (DEBUG = False) -> Untuk Tes Error Page tadi
# (Opsional: Memaksa serve static di local saat debug false, 
# tapi biasanya tidak disarankan untuk production asli)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import AktivitasLogin, Karyawan

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    # Hanya catat aktivitas jika User adalah Karyawan
    if Karyawan.objects.filter(email=user.email).exists():
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        AktivitasLogin.objects.create(
            user=user,
            ip_address=ip,
            user_agent=user_agent
        )

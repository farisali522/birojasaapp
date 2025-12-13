import json
import uuid
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

# Firebase Imports
import firebase_admin
from firebase_admin import credentials, auth

# Import Models
from ..models import Pelanggan, Karyawan

# Import Email Helper
from ..utils import kirim_notifikasi_email

from django.conf import settings

# --- INISIALISASI FIREBASE ---
# Inisialisasi Firebase (Hanya sekali)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(settings.FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Warning: Firebase Error - {e}")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_role_redirect_url(user):
    """
    Helper untuk menentukan arah redirect berdasarkan Role Karyawan/Pelanggan.
    """
    try:
        karyawan = Karyawan.objects.get(email=user.email)
        if karyawan.role == 'manajer':
            return 'manajer_dashboard'
        elif karyawan.role == 'staff_keuangan':
            return 'keuangan_dashboard'
        elif karyawan.role == 'lapangan':
            return 'lapangan_dashboard'
        else:
            return 'staff_dashboard' # Default Staff Admin
    except Karyawan.DoesNotExist:
        return 'dashboard' # Default Pelanggan

# ==========================================
# PUBLIC & AUTHENTICATION VIEWS
# ==========================================

def landing_page(request):
    from ..models import Layanan
    semua_layanan = Layanan.objects.all()
    return render(request, 'core/auth/home.html', {'layanan_list': semua_layanan})

def login_view(request):
    # Jika sudah login, lempar ke dashboard yang sesuai
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))
        
    # Jika login manual (opsional/fallback)
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(get_role_redirect_url(user))
        else:
            messages.error(request, 'Email atau Password salah.')
            
    context = {
        'firebase_api_key': settings.FIREBASE_API_KEY,
        'firebase_auth_domain': settings.FIREBASE_AUTH_DOMAIN,
        'firebase_project_id': settings.FIREBASE_PROJECT_ID,
        'firebase_storage_bucket': settings.FIREBASE_STORAGE_BUCKET,
        'firebase_messaging_sender_id': settings.FIREBASE_MESSAGING_SENDER_ID,
        'firebase_app_id': settings.FIREBASE_APP_ID,
        'firebase_measurement_id': settings.FIREBASE_MEASUREMENT_ID,
    }
    return render(request, 'core/auth/login_firebase.html', context)

@csrf_exempt
def firebase_auth_api(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_token = data.get('id_token')
            
            # Data input tambahan dari form registrasi (jika ada)
            input_nama = data.get('nama')
            input_wa = data.get('no_wa')
            
            # 1. Verifikasi Token ke Firebase
            decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
            email = decoded_token['email']
            nama_google = decoded_token.get('name', 'User')
            
            # 2. Cek User Django (Search or Create)
            user = None
            is_new_user = False
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Jika User tidak ada, cek dulu apakah dia Karyawan?
                if Karyawan.objects.filter(email=email).exists():
                    # Jika Karyawan, buatkan akun otomatis
                    user = User.objects.create_user(username=email, email=email, password=uuid.uuid4().hex)
                else:
                    # Jika bukan Karyawan, berarti Pelanggan Baru
                    is_new_user = True

            # 3. Proses Registrasi Pelanggan Baru
            if is_new_user:
                if not input_nama:
                    # Minta Frontend tampilkan form data diri
                    return JsonResponse({
                        'status': 'need_register', 
                        'email': email,
                        'google_name': nama_google
                    })
                
                # Buat User & Data Pelanggan
                user = User.objects.create_user(username=email, email=email, password=uuid.uuid4().hex)
                kode = f"PLG-{user.id}"
                Pelanggan.objects.create(
                    kode_pelanggan=kode,
                    nama=input_nama,
                    email=email,
                    no_whatsapp=input_wa
                )
                subjek = "Selamat Datang di BiroJasaApp!"
                pesan = f"""
                <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #2F4F4F; padding: 20px; text-align: center;">
                        <h2 style="color: #ffffff; margin: 0;">BiroJasaApp</h2>
                    </div>
                    <div style="padding: 30px; background-color: #ffffff;">
                        <h3 style="color: #333;">Halo, {input_nama}! 👋</h3>
                        <p style="color: #555; line-height: 1.6;">
                            Selamat datang di keluarga besar BiroJasaApp. Akun Anda telah berhasil dibuat.
                            Sekarang Anda dapat menikmati kemudahan mengurus dokumen kendaraan dari rumah.
                        </p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://127.0.0.1:8000/dashboard/" style="background-color: #2F4F4F; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Masuk ke Dashboard</a>
                        </div>
                        <p style="color: #555; font-size: 12px;">Jika tombol di atas tidak berfungsi, silakan login melalui website kami.</p>
                    </div>
                    <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #888;">
                        &copy; 2025 BiroJasaApp. Bandung, Jawa Barat.
                    </div>
                </div>
                """
                kirim_notifikasi_email(subjek, pesan, email)
                

            # 4. Login Session Django
            if user:
                login(request, user)
                # Gunakan helper untuk redirect yang tepat
                target_url_name = get_role_redirect_url(user)
                final_url = reverse(target_url_name)
                return JsonResponse({'status': 'success', 'redirect_url': final_url})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah keluar.')
    return redirect('login')

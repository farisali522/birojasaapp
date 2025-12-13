import json
import datetime
import uuid
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.urls import reverse

# Firebase Imports
import firebase_admin
from firebase_admin import credentials, auth

# Import Models
from .models import (
    Layanan, Pelanggan, Permohonan, LayananDokumen, 
    Dokumen, Pembayaran, Karyawan, MasterDokumen # <--- TAMBAHKAN MasterDokumen
)

# Import Email Helper
from .utils import kirim_notifikasi_email, render_to_pdf

# --- 0. INISIALISASI & HELPER ---

# Inisialisasi Firebase (Hanya sekali)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Warning: Firebase Error - {e}")

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
# 1. AREA PUBLIK & AUTENTIKASI
# ==========================================

def landing_page(request):
    semua_layanan = Layanan.objects.all()
    return render(request, 'core/home.html', {'layanan_list': semua_layanan})

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
            
    return render(request, 'core/login_firebase.html')

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

# ==========================================
# 2. AREA PELANGGAN
# ==========================================

@login_required(login_url='login')
def dashboard_view(request):
    # Security: Karyawan tidak boleh masuk sini
    if Karyawan.objects.filter(email=request.user.email).exists():
        return redirect(get_role_redirect_url(request.user))

    try:
        pelanggan = Pelanggan.objects.get(email=request.user.email)
    except Pelanggan.DoesNotExist:
        pelanggan = None

    permohonan_list = []
    if pelanggan:
        permohonan_list = Permohonan.objects.filter(pelanggan=pelanggan).order_by('-created_at')

    return render(request, 'core/dashboard.html', {'pelanggan': pelanggan, 'permohonan_list': permohonan_list})

@login_required(login_url='login')
def edit_profil_view(request):
    pelanggan = get_object_or_404(Pelanggan, email=request.user.email)
    if request.method == 'POST':
        pelanggan.nama = request.POST.get('nama')
        pelanggan.no_whatsapp = request.POST.get('no_wa')
        pelanggan.alamat_lengkap = request.POST.get('alamat')
        pelanggan.save()
        messages.success(request, "Profil diperbarui!")
        return redirect('dashboard')
    return render(request, 'core/edit_profil.html', {'pelanggan': pelanggan})

@login_required(login_url='login')
def pilih_layanan_view(request):
    layanan_list = Layanan.objects.all()
    return render(request, 'core/pilih_layanan.html', {'layanan_list': layanan_list})

@login_required(login_url='login')
def form_pengajuan_view(request, layanan_id):
    layanan_terpilih = get_object_or_404(Layanan, id=layanan_id)
    syarat_dokumen = LayananDokumen.objects.filter(layanan=layanan_terpilih)

    if request.method == 'POST':
        try:
            pelanggan = Pelanggan.objects.get(email=request.user.email)
            

            metode_pengiriman = request.POST.get('metode_pengiriman')
            catatan = request.POST.get('catatan')

            # =======================================================
            # 🛡️ VALIDASI ALAMAT (LOGIKA BARU) 🛡️
            # =======================================================
            # Jika pilih Kurir TAPI alamat masih kosong/None
            if metode_pengiriman == 'Kirim Kurir' and not pelanggan.alamat_lengkap:
                messages.error(request, "GAGAL: Anda memilih pengiriman Kurir, tetapi Alamat Anda masih kosong. Mohon lengkapi profil terlebih dahulu.")
                # Lempar user ke halaman Edit Profil untuk isi alamat
                return redirect('edit_profil')
            
            now = datetime.datetime.now()
            kode_unik = f"PMH-{now.strftime('%Y%m%d-%H%M%S')}"

            # Simpan Permohonan
            permohonan_baru = Permohonan.objects.create(
                kode_permohonan=kode_unik,
                pelanggan=pelanggan,
                layanan=layanan_terpilih,
                status_proses='Menunggu Verifikasi',
                # Gunakan variabel yang sudah kita ambil di atas
                metode_pengiriman=metode_pengiriman, 
                catatan_pelanggan=catatan
            )

            # Simpan Dokumen
            for syarat in syarat_dokumen:
                nama_input = f"file_{syarat.master_dokumen.id}"
                file_upload = request.FILES.get(nama_input)
                if file_upload:
                    kode_dok = f"DOK-{permohonan_baru.id}-{syarat.master_dokumen.id}"
                    Dokumen.objects.create(
                        kode_dokumen=kode_dok,
                        permohonan=permohonan_baru,
                        master_dokumen=syarat.master_dokumen,
                        path_file=file_upload
                    )
            
            messages.success(request, 'Permohonan berhasil dikirim!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Gagal: {e}")

    context = { 'layanan': layanan_terpilih, 'syarat_dokumen': syarat_dokumen }
    return render(request, 'core/form_pengajuan.html', context)

@login_required(login_url='login')
def tagihan_view(request, permohonan_id):
    # 1. Ambil Data Permohonan (Hanya milik user yang login)
    permohonan = get_object_or_404(Permohonan, id=permohonan_id, pelanggan__email=request.user.email)
    
    # 2. Cek Tagihan
    try:
        pembayaran = permohonan.tagihan
    except:
        messages.error(request, "Tagihan belum dibuat oleh admin.")
        return redirect('dashboard')

    # 3. Logika POST (Saat Tombol Bayar Diklik)
    if request.method == 'POST':
        metode = request.POST.get('metode')
        
        # --- SKENARIO A: BAYAR ONLINE ---
        if metode == 'online':
            # 1. Update Data Pembayaran
            pembayaran.metode_pembayaran = 'Payment Gateway'
            pembayaran.status_pembayaran = 'paid'
            pembayaran.transaction_id_gateway = f"TRX-{uuid.uuid4().hex[:8].upper()}"
            pembayaran.save()
            
            # 2. Update Status Permohonan
            permohonan.status_proses = 'Diproses'
            permohonan.save()
            
            # 3. Generate PDF Struk
            pdf_context = {
                'permohonan': permohonan,
                'pembayaran': pembayaran
            }
            pdf_file = render_to_pdf('core/struk_lunas_pdf.html', pdf_context)
            
            # 4. Siapkan Email
            subjek = f"LUNAS: Pembayaran {permohonan.kode_permohonan} Berhasil"
            pesan = f"""
            <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #198754; padding: 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0;">Pembayaran Diterima ✅</h2>
                </div>
                <div style="padding: 30px; background-color: #ffffff;">
                    <p style="color: #555;">Terima kasih <strong>{permohonan.pelanggan.nama}</strong>,</p>
                    <p style="color: #555;">Kami telah menerima pembayaran Anda sebesar:</p>
                    <h1 style="text-align: center; color: #2F4F4F; margin: 20px 0;">Rp {pembayaran.total_biaya}</h1>
                    <p style="color: #555; text-align: center;">Status Permohonan: <span style="background-color: #e2e3e5; padding: 5px 10px; border-radius: 4px; font-weight: bold;">DIPROSES</span></p>
                    <p style="color: #555; margin-top: 20px;">
                        Bukti pembayaran (Struk) terlampir dalam email ini.<br>
                        Kami akan segera memproses dokumen Anda ke instansi terkait.
                    </p>
                </div>
            </div>
            """
            
            # 5. Kirim Email (Dengan atau Tanpa PDF)
            if pdf_file:
                filename = f"Struk_Lunas_{permohonan.kode_permohonan}.pdf"
                kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email, pdf_file, filename)
            else:
                kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)

            messages.success(request, "Pembayaran Online Berhasil! Struk dikirim ke email.")
            return redirect('dashboard')
            
        # --- SKENARIO B: BAYAR TUNAI (HYBRID) ---
        elif metode == 'tunai':
            # Hanya catat metodenya, JANGAN ubah jadi 'paid'
            pembayaran.metode_pembayaran = 'Tunai'
            pembayaran.save()
            
            # Kirim notifikasi pengingat (Opsional)
            kirim_notifikasi_email(
                f"Menunggu Pembayaran Tunai: {permohonan.kode_permohonan}",
                f"Halo, Anda memilih pembayaran Tunai. Silakan lakukan pembayaran di kasir kantor kami.",
                permohonan.pelanggan.email
            )
            
            messages.info(request, "Silakan bayar tunai di kantor.")
            return redirect('dashboard')

    # 4. Logika GET (Menampilkan Halaman)
    context = {
        'permohonan': permohonan,
        'pembayaran': pembayaran
    }
    return render(request, 'core/tagihan.html', context)
# ==========================================
# 3. AREA STAFF ADMIN
# ==========================================

@login_required(login_url='login')
def staff_dashboard_view(request):
    # Security Check
    if not Karyawan.objects.filter(email=request.user.email).exists():
        messages.error(request, "⛔ Akses Ditolak.")
        return redirect('dashboard')
    
    # 1. Menunggu Verifikasi (Baru Masuk)
    antrean_verifikasi = Permohonan.objects.filter(status_proses='Menunggu Verifikasi').order_by('created_at')

    # 2. Menunggu Pembayaran (BARU: Sudah diverifikasi, belum bayar)
    menunggu_pembayaran = Permohonan.objects.filter(status_proses='Menunggu Pembayaran').order_by('created_at')
    
    # 3. Siap Ditugaskan (Sudah Bayar)
    antrean_penugasan = Permohonan.objects.filter(status_proses='Diproses', karyawan__isnull=True).order_by('created_at')

    # 4. Siap Finalisasi (Dokumen Kembali)
    siap_finalisasi = Permohonan.objects.filter(
        status_proses__icontains='Kembali' 
    ).exclude(status_proses='Selesai').order_by('updated_at')
    
    # 5. Sedang Berjalan (Di Lapangan)
    sedang_berjalan = Permohonan.objects.filter(
        karyawan__isnull=False
    ).exclude(
        status_proses='Selesai'
    ).exclude(
        status_proses__icontains='Kembali'
    ).exclude(
        status_proses='Diproses'
    ).order_by('-updated_at')

    context = {
        'antrean_verifikasi': antrean_verifikasi,
        'menunggu_pembayaran': menunggu_pembayaran, # <-- Data Baru
        'antrean_penugasan': antrean_penugasan,
        'siap_finalisasi': siap_finalisasi,
        'sedang_berjalan': sedang_berjalan
    }
    return render(request, 'core/staff_dashboard.html', context)

@login_required(login_url='login')
def staff_input_walkin_view(request):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Ambil Data
            nama = request.POST.get('nama')
            email = request.POST.get('email')
            no_wa = request.POST.get('no_wa')
            alamat = request.POST.get('alamat')
            layanan_id = request.POST.get('layanan_id')
            layanan_terpilih = Layanan.objects.get(id=layanan_id)

            # Search-or-Create Pelanggan
            try:
                user = User.objects.get(email=email)
                pelanggan = Pelanggan.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(username=email, email=email, password=uuid.uuid4().hex[:8])
                kode_plg = f"PLG-{user.id}"
                pelanggan = Pelanggan.objects.create(
                    kode_pelanggan=kode_plg, nama=nama, email=email, no_whatsapp=no_wa, alamat_lengkap=alamat
                )

            # Buat Permohonan
            kode_unik = f"PMH-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            permohonan_baru = Permohonan.objects.create(
                kode_permohonan=kode_unik,
                pelanggan=pelanggan,
                layanan=layanan_terpilih,
                status_proses='Menunggu Verifikasi',
                metode_pengiriman='Ambil di Kantor',
                catatan_pelanggan=f"Walk-in via {request.user.username}"
            )
            
            messages.success(request, "Data disimpan. Silakan upload arsip.")
            return redirect('staff_upload_arsip', permohonan_id=permohonan_baru.id)

        except Exception as e:
            messages.error(request, f"Gagal: {e}")

    layanan_list = Layanan.objects.all()
    return render(request, 'core/staff_input_walkin.html', {'layanan_list': layanan_list})

@login_required(login_url='login')
def staff_upload_arsip_view(request, permohonan_id):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')
    
    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    syarat_dokumen = LayananDokumen.objects.filter(layanan=permohonan.layanan)

    if request.method == 'POST':
        for syarat in syarat_dokumen:
            nama_input = f"file_{syarat.master_dokumen.id}"
            file_upload = request.FILES.get(nama_input)
            if file_upload:
                kode_dok = f"DOK-{permohonan.id}-{syarat.master_dokumen.id}"
                Dokumen.objects.create(
                    kode_dokumen=kode_dok,
                    permohonan=permohonan,
                    master_dokumen=syarat.master_dokumen,
                    path_file=file_upload,
                    status_file='Fisik Diterima & Diarsipkan'
                )
        messages.success(request, 'Arsip selesai. Lanjut verifikasi.')
        return redirect('verifikasi_permohonan', permohonan_id=permohonan.id)

    return render(request, 'core/staff_upload_arsip.html', {'permohonan': permohonan, 'syarat_dokumen': syarat_dokumen})

@login_required(login_url='login')
def verifikasi_permohonan_view(request, permohonan_id):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')

    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    
    
    if request.method == 'POST':
        biaya_resmi = int(request.POST.get('biaya_resmi'))
        biaya_pengiriman = int(request.POST.get('biaya_pengiriman') or 0)
        
        permohonan.biaya_resmi = biaya_resmi
        permohonan.status_proses = 'Menunggu Pembayaran'
        permohonan.save()
        
        total_tagihan = permohonan.layanan.harga_jasa + biaya_resmi + biaya_pengiriman
        
        pembayaran_baru = Pembayaran.objects.create(
            nomor_invoice=f"INV-{permohonan.kode_permohonan}",
            permohonan=permohonan,
            biaya_pengiriman=biaya_pengiriman,
            total_biaya=total_tagihan,
            metode_pembayaran=None,
            status_pembayaran='pending'
        )

        # 1. Siapkan Data untuk PDF
        pdf_context = {
            'permohonan': permohonan,
            'pembayaran': pembayaran_baru # Pastikan Anda menangkap objek pembayaran yg baru dicreate
        }

        # 2. Generate PDF
        pdf_file = render_to_pdf('core/invoice_pdf.html', pdf_context)
        
        subjek = f"Tagihan Terbit: {permohonan.kode_permohonan}"
        pesan = f"""
        <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #ffc107; padding: 20px; text-align: center;">
                <h2 style="color: #333; margin: 0;">Menunggu Pembayaran</h2>
            </div>
            <div style="padding: 30px; background-color: #ffffff;">
                <p style="color: #555;">Halo <strong>{permohonan.pelanggan.nama}</strong>,</p>
                <p style="color: #555;">Permohonan Anda telah diverifikasi oleh admin. Berikut rincian tagihan Anda:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #777;">Layanan</td>
                        <td style="padding: 10px; font-weight: bold; text-align: right;">{permohonan.layanan.nama_layanan}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #777;">No. Invoice</td>
                        <td style="padding: 10px; font-weight: bold; text-align: right;">{permohonan.tagihan.nomor_invoice}</td>
                    </tr>
                    <tr style="background-color: #f1f8f5;">
                        <td style="padding: 10px; color: #2F4F4F; font-weight: bold;">TOTAL BAYAR</td>
                        <td style="padding: 10px; color: #2F4F4F; font-weight: bold; text-align: right; font-size: 18px;">Rp {total_tagihan}</td>
                    </tr>
                </table>

                <p style="color: #555;">Detail lengkap tagihan terlampir dalam file PDF (Invoice).</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://127.0.0.1:8000/tagihan/{permohonan.id}/" style="background-color: #ffc107; color: #000; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Bayar Sekarang ➔</a>
                </div>
            </div>
        </div>
        """
        # Pastikan kode PDF generation Anda ada di sini juga
        if pdf_file:
             filename = f"Invoice_{permohonan.kode_permohonan}.pdf"
             kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email, pdf_file, filename)
        else:
             kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)

        messages.success(request, 'Verifikasi berhasil! Invoice PDF telah dikirim ke email.')
        return redirect('staff_dashboard')
        

    return render(request, 'core/verifikasi_form.html', {'item': permohonan, 'dokumen_list': permohonan.berkas_upload.all()})

@login_required(login_url='login')
def tugaskan_staff_view(request, permohonan_id):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')
    
    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    if request.method == 'POST':
        petugas = Karyawan.objects.get(id=request.POST.get('karyawan_id'))
        permohonan.karyawan = petugas
        permohonan.status_proses = 'Proses Lapangan'
        permohonan.save()
        messages.success(request, f"Ditugaskan ke {petugas.nama}")
        return redirect('staff_dashboard')

    return render(request, 'core/tugaskan_form.html', {'item': permohonan, 'staff_list': Karyawan.objects.filter(role='lapangan')})

@login_required(login_url='login')
def finalisasi_permohonan_view(request, permohonan_id):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')
    
    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    permohonan.status_proses = 'Selesai'
    permohonan.save()
    
    kirim_notifikasi_email(
        f"SELESAI: {permohonan.kode_permohonan}",
        f"Dokumen selesai. Metode pengambilan: {permohonan.metode_pengiriman}",
        permohonan.pelanggan.email
    )
    messages.success(request, "Permohonan SELESAI.")
    return redirect('staff_dashboard')

# ==========================================
# 4. AREA STAFF KEUANGAN
# ==========================================

@login_required(login_url='login')
def keuangan_dashboard_view(request):
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
        if karyawan.role != 'staff_keuangan':
            return redirect('dashboard')
    except Karyawan.DoesNotExist:
        return redirect('dashboard')

    list_tagihan = Pembayaran.objects.filter(
        status_pembayaran='pending'
    ).filter(
        Q(metode_pembayaran='Tunai') |  # 1. Yang sudah jelas mau Tunai
        Q(metode_pembayaran__isnull=True) | # 2. Yang BELUM DIPILIH metodenya (ini biasanya Walk-in)
        Q(permohonan__metode_pengiriman='Ambil di Kantor') # 3. Yang Walk-in (ambil sendiri)
    ).order_by('created_at')
    history = Pembayaran.objects.filter(status_pembayaran='paid', updated_at__date=datetime.date.today()).order_by('-updated_at')
    
    context = {
        'list_tagihan': list_tagihan,
        'history': history,
        'karyawan': karyawan
    }
    return render(request, 'core/keuangan_dashboard.html', context)

@login_required(login_url='login')
def konfirmasi_lunas_view(request, pembayaran_id):
    if not Karyawan.objects.filter(email=request.user.email, role='staff_keuangan').exists():
        return redirect('dashboard')
        
    if request.method == 'POST': # Pastikan POST
        pembayaran = get_object_or_404(Pembayaran, id=pembayaran_id)
        
        # 1. TANGKAP METODE DARI TOMBOL YANG DIKLIK
        metode_dipilih = request.POST.get('metode') # 'Tunai' atau 'Transfer/QRIS Manual'
        
        # 2. Simpan Metode & Status
        pembayaran.metode_pembayaran = metode_dipilih
        pembayaran.status_pembayaran = 'paid'
        pembayaran.save()
        
        # 3. Update Status Permohonan
        permohonan = pembayaran.permohonan
        permohonan.status_proses = 'Diproses'
        permohonan.save()
        
# --- MULAI UPDATE (GENERATE STRUK PDF) ---
        pdf_context = {
            'permohonan': permohonan,
            'pembayaran': pembayaran
        }
        pdf_file = render_to_pdf('core/struk_lunas_pdf.html', pdf_context)
        
        # Kirim Email + Lampiran Struk
        subjek = f"LUNAS: Pembayaran {permohonan.kode_permohonan} Berhasil"
        pesan = f"""
            <h3>Terima Kasih, {permohonan.pelanggan.nama}</h3>
            <p>Pembayaran Anda sebesar <b>Rp {pembayaran.total_biaya}</b> via <b>{metode_dipilih}</b> telah kami terima.</p>
            <p>Terlampir adalah <b>Struk Bukti Pembayaran</b> yang sah.</p>
            <p>Status permohonan Anda sekarang: <b>Diproses</b>.</p>
        """
        
        if pdf_file:
            filename = f"Struk_Lunas_{permohonan.kode_permohonan}.pdf"
            kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email, pdf_file, filename)
        else:
            kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)
        # -----------------------------------------
        
        messages.success(request, f"Pembayaran dikonfirmasi & Struk dikirim ke email!")
        return redirect('keuangan_dashboard')
        
    return redirect('keuangan_dashboard')

# ==========================================
# 5. AREA STAFF LAPANGAN
# ==========================================

@login_required(login_url='login')
def lapangan_dashboard_view(request):
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
        if karyawan.role != 'lapangan':
            return redirect('dashboard')
    except:
        return redirect('dashboard')

    daftar_tugas = Permohonan.objects.filter(karyawan=karyawan).exclude(status_proses='Selesai').order_by('-updated_at')
    return render(request, 'core/lapangan_dashboard.html', {'karyawan': karyawan, 'daftar_tugas': daftar_tugas})

@login_required(login_url='login')
def update_status_lapangan_view(request, permohonan_id):
    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    if request.method == 'POST':
        status_baru = request.POST.get('status_baru')
        permohonan.status_proses = status_baru
        permohonan.save()
        
        subjek = f"Update Status: {permohonan.kode_permohonan}"
        pesan = f"""
        <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #0dcaf0; padding: 20px; text-align: center;">
                <h2 style="color: #ffffff; margin: 0;">Update Progres 🚀</h2>
            </div>
            <div style="padding: 30px; background-color: #ffffff;">
                <p style="color: #555;">Halo {permohonan.pelanggan.nama},</p>
                <p style="color: #555;">Ada perkembangan terbaru mengenai dokumen <strong>{permohonan.layanan.nama_layanan}</strong> Anda.</p>
                
                <div style="background-color: #f0f8ff; border-left: 5px solid #0dcaf0; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 12px; color: #777;">STATUS TERKINI:</p>
                    <h3 style="margin: 5px 0 0 0; color: #055160;">{status_baru}</h3>
                </div>

                <p style="color: #555;">Anda dapat memantau detail lengkapnya di dashboard.</p>
                <div style="text-align: center; margin-top: 20px;">
                    <a href="http://127.0.0.1:8000/dashboard/" style="color: #0dcaf0; text-decoration: none; font-weight: bold;">Buka Aplikasi</a>
                </div>
            </div>
        </div>
        """
        kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)
        messages.success(request, "Status diperbarui!")
        return redirect('lapangan_dashboard')

    return render(request, 'core/update_status_form.html', {'item': permohonan})

# ==========================================
# 6. AREA MANAJER
# ==========================================

@login_required(login_url='login')
def manajer_dashboard_view(request):
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
        if karyawan.role != 'manajer':
            return redirect('dashboard')
    except:
        return redirect('dashboard')

# Total Pelanggan
    total_pelanggan = Pelanggan.objects.count()
    
    # Total Transaksi (Semua Permohonan masuk)
    total_permohonan = Permohonan.objects.count()
    
    # Total Pendapatan (Dari Tabel Pembayaran yang sudah LUNAS)
    total_uang_agg = Pembayaran.objects.filter(status_pembayaran='paid').aggregate(Sum('total_biaya'))
    total_uang = total_uang_agg['total_biaya__sum'] or 0

    # Statistik Status Permohonan (untuk tabel di Tab Monitoring)
    status_stats = Permohonan.objects.values('status_proses').annotate(jumlah=Count('id')).order_by('-jumlah')
    
    # Ambil data karyawan untuk ucapan selamat datang
    karyawan = Karyawan.objects.get(email=request.user.email)

    context = {
        'karyawan': karyawan,
        'total_pelanggan': total_pelanggan,
        'total_permohonan': total_permohonan,
        'total_uang': total_uang,
        'status_stats': status_stats
    }
    return render(request, 'core/manajer_dashboard.html', context)

@login_required(login_url='login')
def laporan_keuangan_view(request):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    laporan = Pembayaran.objects.filter(status_pembayaran='paid').order_by('-updated_at')

    if start_date and end_date:
        laporan = laporan.filter(updated_at__date__range=[start_date, end_date])

    total_pemasukan = laporan.aggregate(Sum('total_biaya'))['total_biaya__sum'] or 0

    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="laporan_{datetime.date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(['No Invoice', 'Tanggal', 'Pelanggan', 'Total'])
        for item in laporan:
            writer.writerow([item.nomor_invoice, item.updated_at.strftime("%d-%m-%Y"), item.permohonan.pelanggan.nama, item.total_biaya])
        return response

    return render(request, 'core/laporan.html', {'laporan': laporan, 'total_pemasukan': total_pemasukan, 'start_date': start_date, 'end_date': end_date})

# ==========================================
# 7. FITUR TAMBAHAN (TOLAK & DETAIL)
# ==========================================

# --- VIEW TOLAK PERMOHONAN (STAFF) ---
@login_required(login_url='login')
def tolak_permohonan_view(request, permohonan_id):
    # Security: Hanya Staff
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')

    permohonan = get_object_or_404(Permohonan, id=permohonan_id)

    if request.method == 'POST':
        alasan = request.POST.get('alasan')
        
        # Update Status & Catatan
        permohonan.status_proses = 'Ditolak'
        permohonan.catatan_penolakan = alasan
        permohonan.save()
        
        subjek = f"PENTING: Permohonan Ditolak ({permohonan.kode_permohonan})"
        pesan = f"""
        <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #dc3545; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #dc3545; padding: 20px; text-align: center;">
                <h2 style="color: #ffffff; margin: 0;">Permohonan Ditolak ⛔</h2>
            </div>
            <div style="padding: 30px; background-color: #ffffff;">
                <p style="color: #555;">Halo {permohonan.pelanggan.nama},</p>
                <p style="color: #555;">Mohon maaf, permohonan Anda belum dapat kami proses karena alasan berikut:</p>
                
                <div style="background-color: #fce8e6; padding: 15px; border-radius: 5px; color: #a71d2a; font-weight: bold; margin: 20px 0;">
                    "{alasan}"
                </div>

                <p style="color: #555;">Jangan khawatir, Anda tidak perlu membuat permohonan baru. Silakan klik tombol di bawah untuk melakukan revisi (upload ulang dokumen).</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://127.0.0.1:8000/detail/{permohonan.id}/" style="background-color: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Perbaiki Permohonan</a>
                </div>
            </div>
        </div>
        """
        kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)
        
        messages.warning(request, f"Permohonan {permohonan.kode_permohonan} telah DITOLAK.")
        return redirect('staff_dashboard')

    return render(request, 'core/tolak_form.html', {'item': permohonan})

# --- VIEW DETAIL PERMOHONAN (PELANGGAN) ---
@login_required(login_url='login')
def detail_permohonan_view(request, permohonan_id):
    # Security: Hanya pemilik permohonan
    permohonan = get_object_or_404(Permohonan, id=permohonan_id, pelanggan__email=request.user.email)
    
    # Ambil dokumen yang diupload
    dokumen_list = permohonan.berkas_upload.all()
    
    # Ambil data pembayaran (jika ada)
    try:
        pembayaran = permohonan.tagihan
    except:
        pembayaran = None

    context = {
        'item': permohonan,
        'dokumen_list': dokumen_list,
        'pembayaran': pembayaran
    }
    return render(request, 'core/detail_permohonan.html', context)

# ... (kode sebelumnya di area manajer) ...

# --- 18. MANAJEMEN KARYAWAN (LIST) ---
@login_required(login_url='login')
def manajer_karyawan_list_view(request):
    # Security Check
    try:
        if Karyawan.objects.get(email=request.user.email).role != 'manajer':
            return redirect('dashboard')
    except:
        return redirect('dashboard')

    karyawan_list = Karyawan.objects.all().order_by('role', 'nama')
    return render(request, 'core/manajer_karyawan_list.html', {'karyawan_list': karyawan_list})

# --- 19. TAMBAH KARYAWAN BARU ---
@login_required(login_url='login')
def manajer_karyawan_create_view(request):
    # Security Check (Sama)
    if not Karyawan.objects.filter(email=request.user.email, role='manajer').exists():
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Ambil data
            nama = request.POST.get('nama')
            email = request.POST.get('email')
            no_wa = request.POST.get('no_wa')
            role = request.POST.get('role')
            
            # Generate Kode Unik (KRY-UUID)
            kode = f"KRY-{uuid.uuid4().hex[:6].upper()}"
            
            # Simpan ke Database Karyawan
            Karyawan.objects.create(
                kode_karyawan=kode,
                nama=nama,
                email=email,
                no_whatsapp=no_wa,
                role=role
            )
            
            messages.success(request, f"Karyawan {nama} berhasil ditambahkan!")
            return redirect('manajer_karyawan_list')
            
        except Exception as e:
            messages.error(request, f"Gagal menambah karyawan: {e}")

    return render(request, 'core/manajer_karyawan_form.html')

# --- 20. EDIT KARYAWAN ---
@login_required(login_url='login')
def manajer_karyawan_edit_view(request, karyawan_id):
    # Security Check
    if not Karyawan.objects.filter(email=request.user.email, role='manajer').exists():
        return redirect('dashboard')
        
    karyawan = get_object_or_404(Karyawan, id=karyawan_id)
    
    if request.method == 'POST':
        try:
            karyawan.nama = request.POST.get('nama')
            karyawan.email = request.POST.get('email')
            karyawan.no_whatsapp = request.POST.get('no_wa')
            karyawan.role = request.POST.get('role')
            karyawan.save()
            
            messages.success(request, "Data karyawan diperbarui.")
            return redirect('manajer_karyawan_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'core/manajer_karyawan_form.html', {'item': karyawan})

# --- 21. HAPUS KARYAWAN ---
@login_required(login_url='login')
def manajer_karyawan_delete_view(request, karyawan_id):
    if not Karyawan.objects.filter(email=request.user.email, role='manajer').exists():
        return redirect('dashboard')
        
    karyawan = get_object_or_404(Karyawan, id=karyawan_id)
    
    # Cegah manajer menghapus dirinya sendiri
    if karyawan.email == request.user.email:
        messages.error(request, "Anda tidak bisa menghapus akun sendiri!")
    else:
        karyawan.delete()
        # Opsional: Hapus juga User Django jika ada
        User.objects.filter(email=karyawan.email).delete()
        messages.success(request, "Karyawan dihapus.")
        
    return redirect('manajer_karyawan_list')

# --- 16. VIEW REVISI PENGAJUAN ---
@login_required(login_url='login')
def revisi_pengajuan_view(request, permohonan_id):
    # Security: Hanya pemilik yang boleh revisi
    permohonan = get_object_or_404(Permohonan, id=permohonan_id, pelanggan__email=request.user.email)
    
    # Pastikan hanya yang DITOLAK yang bisa direvisi
    if permohonan.status_proses != 'Ditolak':
        messages.error(request, "Permohonan ini tidak dalam status Ditolak.")
        return redirect('dashboard')

    # Ambil syarat dokumen untuk layanan ini
    syarat_dokumen = LayananDokumen.objects.filter(layanan=permohonan.layanan)

    if request.method == 'POST':
        try:
            # 1. Update Dokumen (Hanya yang diupload ulang)
            for syarat in syarat_dokumen:
                nama_input = f"file_{syarat.master_dokumen.id}"
                file_upload = request.FILES.get(nama_input)
                
                if file_upload:
                    # Cari dokumen lama
                    doc_obj, created = Dokumen.objects.get_or_create(
                        permohonan=permohonan,
                        master_dokumen=syarat.master_dokumen,
                        defaults={
                            'kode_dokumen': f"DOK-{permohonan.id}-{syarat.master_dokumen.id}",
                            'path_file': file_upload
                        }
                    )
                    # Jika sudah ada, update filenya
                    if not created:
                        doc_obj.path_file = file_upload
                        doc_obj.save()

            # 2. Reset Status Permohonan
            permohonan.status_proses = 'Menunggu Verifikasi'
            permohonan.catatan_penolakan = None # Hapus catatan penolakan lama
            
            # Update catatan baru jika ada
            catatan_baru = request.POST.get('catatan')
            if catatan_baru:
                permohonan.catatan_pelanggan = catatan_baru
                
            permohonan.save()

            messages.success(request, 'Revisi berhasil dikirim! Admin akan mengecek ulang.')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f"Gagal revisi: {e}")

    context = {
        'permohonan': permohonan,
        'syarat_dokumen': syarat_dokumen
    }
    return render(request, 'core/form_revisi.html', context)

# --- 16. VIEW DETAIL TUGAS (KHUSUS LAPANGAN) ---
@login_required(login_url='login')
def lapangan_detail_view(request, permohonan_id):
    # Security Check
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
        if karyawan.role != 'lapangan':
            return redirect('dashboard')
    except:
        return redirect('dashboard')

    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    
    # Pastikan ini tugas dia
    if permohonan.karyawan != karyawan:
        messages.error(request, "Ini bukan tugas Anda.")
        return redirect('lapangan_dashboard')

    dokumen_list = permohonan.berkas_upload.all()

    context = {
        'item': permohonan,
        'dokumen_list': dokumen_list
    }
    return render(request, 'core/lapangan_detail.html', context)

# ==========================================
# 7. MANAJEMEN MASTER DATA (P1.6)
# ==========================================

def manajer_check(user):
    try:
        return Karyawan.objects.get(email=user.email).role == 'manajer'
    except Karyawan.DoesNotExist:
        return False

# --- 22. KELOLA LAYANAN (LIST & DELETE) ---
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_list_view(request):
    layanan_list = Layanan.objects.all().order_by('nama_layanan')

    if request.method == 'POST':
        layanan_id = request.POST.get('layanan_id')
        layanan_obj = get_object_or_404(Layanan, id=layanan_id)
        layanan_obj.delete()
        messages.success(request, f"Layanan {layanan_obj.nama_layanan} dihapus.")
        return redirect('master_layanan_list')

    return render(request, 'core/master_layanan_list.html', {'layanan_list': layanan_list})

# --- 23. KELOLA LAYANAN (CREATE & EDIT) ---
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_form_view(request, layanan_id=None):
    layanan_obj = get_object_or_404(Layanan, id=layanan_id) if layanan_id else None

    if request.method == 'POST':
        try:
            # Cek apakah kode sudah ada untuk CREATE
            if not layanan_obj and Layanan.objects.filter(kode_layanan=request.POST.get('kode_layanan')).exists():
                messages.error(request, "Kode Layanan sudah digunakan!")
                return redirect('master_layanan_add')

            # Create atau Update
            Layanan.objects.update_or_create(
                id=layanan_id,
                defaults={
                    'kode_layanan': request.POST.get('kode_layanan'),
                    'nama_layanan': request.POST.get('nama_layanan'),
                    'harga_jasa': request.POST.get('harga_jasa'),
                    'estimasi_waktu': request.POST.get('estimasi_waktu'),
                }
            )
            messages.success(request, "Data layanan berhasil disimpan.")
            return redirect('master_layanan_list')
        except Exception as e:
            messages.error(request, f"Gagal menyimpan: {e}")

    context = {'item': layanan_obj, 'is_edit': layanan_id is not None}
    return render(request, 'core/master_layanan_form.html', context)

# --- 24. KELOLA PERSYARATAN (RELASI N:M) ---
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_requirements_view(request, layanan_id):
    layanan = get_object_or_404(Layanan, id=layanan_id)

    # Ambil semua dokumen yang mungkin (Master Dokumen)
    master_dokumen = MasterDokumen.objects.all()
    # Ambil semua persyaratan yang sudah terpasang
    persyaratan_terpasang = LayananDokumen.objects.filter(layanan=layanan).values_list('master_dokumen__id', flat=True)

    if request.method == 'POST':
        # Hapus semua relasi lama untuk layanan ini
        LayananDokumen.objects.filter(layanan=layanan).delete()

        # Buat relasi baru berdasarkan centangan form
        for doc in master_dokumen:
            if request.POST.get(f'doc_{doc.id}'):
                LayananDokumen.objects.create(
                    layanan=layanan,
                    master_dokumen=doc,
                    is_wajib=True # Default wajib
                )
        messages.success(request, f"Persyaratan untuk {layanan.nama_layanan} berhasil diperbarui.")
        return redirect('master_layanan_list')

    context = {
        'layanan': layanan,
        'master_dokumen': master_dokumen,
        'terpasang_ids': list(persyaratan_terpasang) # IDs yang sudah tercentang
    }
    return render(request, 'core/master_layanan_requirements.html', context)

# --- 25. KELOLA MASTER DOKUMEN (LIST & DELETE) ---
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_list_view(request):
    master_dokumen_list = MasterDokumen.objects.all().order_by('nama_dokumen')
    
    if request.method == 'POST':
        doc_id = request.POST.get('doc_id')
        doc_obj = get_object_or_404(MasterDokumen, id=doc_id)
        
        # Perlu cek apakah dokumen masih dipakai di relasi LayananDokumen atau Dokumen (FK set to RESTRICT)
        # Untuk simpel, kita asumsikan Manajer tahu risikonya, atau nanti kita tambahkan check.
        doc_obj.delete() 
        messages.success(request, f"Master Dokumen {doc_obj.nama_dokumen} dihapus.")
        return redirect('master_dokumen_list')
        
    return render(request, 'core/master_dokumen_list.html', {'master_dokumen_list': master_dokumen_list})

# --- 26. KELOLA MASTER DOKUMEN (CREATE & EDIT) ---
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_form_view(request, doc_id=None):
    doc_obj = get_object_or_404(MasterDokumen, id=doc_id) if doc_id else None
    
    if request.method == 'POST':
        try:
            MasterDokumen.objects.update_or_create(
                id=doc_id,
                defaults={
                    'nama_dokumen': request.POST.get('nama_dokumen'),
                    'deskripsi': request.POST.get('deskripsi'),
                }
            )
            messages.success(request, "Data Master Dokumen berhasil disimpan.")
            return redirect('master_dokumen_list')
        except Exception as e:
            messages.error(request, f"Gagal menyimpan: {e}")

    context = {'item': doc_obj, 'is_edit': doc_id is not None}
    return render(request, 'core/master_dokumen_form.html', context)
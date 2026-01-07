import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
import uuid

# Import Models
from ..models import Layanan, Pelanggan, Permohonan, LayananDokumen, Dokumen, Pembayaran, Karyawan, PermohonanAuditLog

# Import Helpers
from ..utils import kirim_notifikasi_email, render_to_pdf
from .auth_views import get_role_redirect_url

# ==========================================
# PELANGGAN VIEWS
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

    return render(request, 'core/pelanggan/dashboard.html', {'pelanggan': pelanggan, 'permohonan_list': permohonan_list})

@login_required(login_url='login')
def pilih_layanan_view(request):
    layanan_list = Layanan.objects.all()
    return render(request, 'core/pelanggan/pilih_layanan.html', {'layanan_list': layanan_list})

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
            
            # 🔥 AUDIT LOG: Permohonan dibuat
            PermohonanAuditLog.objects.create(
                permohonan=permohonan_baru,
                karyawan=None,  # Dibuat oleh pelanggan (system)
                action='created',
                notes=f'Permohonan dibuat oleh {pelanggan.nama} via {metode_pengiriman}'
            )
            
            messages.success(request, 'Permohonan berhasil dikirim!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Gagal: {e}")

    context = { 'layanan': layanan_terpilih, 'syarat_dokumen': syarat_dokumen }
    return render(request, 'core/pelanggan/form_pengajuan.html', context)

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
            pdf_file = render_to_pdf('core/pdf/struk_lunas_pdf.html', pdf_context)
            
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
            pembayaran.metode_pembayaran = 'Tunai'
            pembayaran.save()
            
            kirim_notifikasi_email(
                f"Menunggu Pembayaran Tunai: {permohonan.kode_permohonan}",
                f"Halo, Anda memilih pembayaran Tunai. Silakan lakukan pembayaran di kasir kantor kami.",
                permohonan.pelanggan.email
            )
            
            messages.info(request, "Silakan bayar tunai di kantor.")
            return redirect('dashboard')

        # --- SKENARIO C: QRIS INSTANT BYPASS (DEMO) ---
        elif metode == 'qris_instant':
            pembayaran.metode_pembayaran = 'QRIS (Instant)'
            pembayaran.status_pembayaran = 'paid'
            pembayaran.transaction_id_gateway = f"QRIS-DEMO-{uuid.uuid4().hex[:6].upper()}"
            pembayaran.save()
            
            permohonan.status_proses = 'Diproses'
            permohonan.save()
            
            # Email Struk
            pdf_context = {'permohonan': permohonan, 'pembayaran': pembayaran}
            pdf_file = render_to_pdf('core/pdf/struk_lunas_pdf.html', pdf_context)
            subjek = f"LUNAS: Pembayaran QRIS {permohonan.kode_permohonan} Berhasil"
            pesan = f"Terima kasih {permohonan.pelanggan.nama}, pembayaran QRIS Anda telah diterima."
            
            if pdf_file:
                kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email, pdf_file, f"Struk_QRIS_{permohonan.kode_permohonan}.pdf")
            else:
                kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)

            messages.success(request, "Pembayaran QRIS Berhasil (Mode Demo)!")
            return redirect('dashboard')

        # --- SKENARIO C: BAYAR MANUAL (TRANSFER/QRIS) ---
        elif metode == 'manual':
            metode_asli = request.POST.get('metode_pilihan')
            bukti = request.FILES.get('bukti_bayar')
            
            if bukti:
                pembayaran.metode_pembayaran = metode_asli
                pembayaran.bukti_pembayaran = bukti
                pembayaran.status_pembayaran = 'pending'
                pembayaran.save()
                
                kirim_notifikasi_email(f"KONFIRMASI BAYAR: {permohonan.kode_permohonan}", f"Bukti bayar diupload.", "admin@birojasa.com")

                messages.success(request, f"Bukti {metode_asli} berhasil diupload. Mohon tunggu verifikasi.")
                return redirect('dashboard')
            else:
                messages.error(request, "Harap upload bukti pembayaran.")
                return redirect('tagihan', permohonan_id=permohonan.id)

    # 4. Logika GET (Menampilkan Halaman)
    context = {
        'permohonan': permohonan,
        'pembayaran': pembayaran
    }
    return render(request, 'core/pelanggan/tagihan.html', context)
@login_required(login_url='login')
def konfirmasi_selesai_view(request, permohonan_id):
    # Hanya permohonan milik yang bersangkutan dan statusnya 'Dikirim'
    permohonan = get_object_or_404(Permohonan, id=permohonan_id, pelanggan__email=request.user.email)
    
    if permohonan.status_proses == 'Dikirim':
        permohonan.status_proses = 'Selesai'
        permohonan.save()
        
        # 🔥 AUDIT LOG
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=None, # Oleh pelanggan
            action='completed',
            notes=f'Pelanggan telah mengonfirmasi penerimaan dokumen. Selesai.'
        )
        
        messages.success(request, "Terima kasih! Permohonan Anda telah dinyatakan Selesai.")
    
    return redirect('dashboard')

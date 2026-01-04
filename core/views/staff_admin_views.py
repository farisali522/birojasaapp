import datetime
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

# Import Models
from ..models import Layanan, Pelanggan, Permohonan, LayananDokumen, Dokumen, Pembayaran, Karyawan, PermohonanAuditLog, PembayaranAuditLog

# Import Helpers
from ..utils import kirim_notifikasi_email, render_to_pdf

# ==========================================
# STAFF ADMIN VIEWS
# ==========================================

@login_required(login_url='login')
def staff_dashboard_view(request):
    # Security Check
    if not Karyawan.objects.filter(email=request.user.email).exists():
        messages.error(request, "Akses Ditolak.")
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
    return render(request, 'core/staff/staff_dashboard.html', context)

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
    return render(request, 'core/staff/staff_input_walkin.html', {'layanan_list': layanan_list})

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

    return render(request, 'core/staff/staff_upload_arsip.html', {'permohonan': permohonan, 'syarat_dokumen': syarat_dokumen})

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
        
        # 🔥 AUDIT LOG: Verifikasi
        staff_admin = Karyawan.objects.get(email=request.user.email)
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=staff_admin,
            action='verified',
            notes=f'Diverifikasi. Biaya resmi: Rp {biaya_resmi:,}'
        )
        
        total_tagihan = permohonan.layanan.harga_jasa + biaya_resmi + biaya_pengiriman
        
        pembayaran_baru = Pembayaran.objects.create(
            nomor_invoice=f"INV-{permohonan.kode_permohonan}",
            permohonan=permohonan,
            biaya_pengiriman=biaya_pengiriman,
            total_biaya=total_tagihan,
            metode_pembayaran=None,
            status_pembayaran='pending'
        )
        
        # 🔥 AUDIT LOG: Invoice created
        PembayaranAuditLog.objects.create(
            pembayaran=pembayaran_baru,
            karyawan=staff_admin,
            action='invoice_created',
            notes=f'Invoice generated. Total: Rp {total_tagihan:,}'
        )

        # 1. Siapkan Data untuk PDF
        pdf_context = {
            'permohonan': permohonan,
            'pembayaran': pembayaran_baru # Pastikan Anda menangkap objek pembayaran yg baru dicreate
        }

        # 2. Generate PDF
        pdf_file = render_to_pdf('core/pdf/invoice_pdf.html', pdf_context)
        
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
        

    return render(request, 'core/staff/verifikasi_form.html', {'item': permohonan, 'dokumen_list': permohonan.berkas_upload.all()})

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
        
        # 🔥 AUDIT LOG: Assignment
        staff_admin = Karyawan.objects.get(email=request.user.email)
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=staff_admin,
            action='assigned',
            notes=f'Ditugaskan ke {petugas.nama} ({petugas.role})'
        )
        
        messages.success(request, f"Ditugaskan ke {petugas.nama}")
        return redirect('staff_dashboard')

    return render(request, 'core/staff/tugaskan_form.html', {'item': permohonan, 'staff_list': Karyawan.objects.filter(role='lapangan')})

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
        
        # 🔥 AUDIT LOG: Rejection
        staff_admin = Karyawan.objects.get(email=request.user.email)
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=staff_admin,
            action='rejected',
            notes=f'Ditolak. Alasan: {alasan}'
        )
        
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

    return render(request, 'core/staff/tolak_form.html', {'item': permohonan})

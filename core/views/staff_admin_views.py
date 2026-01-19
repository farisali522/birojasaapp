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
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
    except Karyawan.DoesNotExist:
        messages.error(request, "Akses Ditolak.")
        return redirect('dashboard')
    
    # 1. Menunggu Verifikasi (Baru Masuk)
    antrean_verifikasi = Permohonan.objects.filter(status_proses='Menunggu Verifikasi').order_by('created_at')

    # 2. Menunggu Pembayaran (BARU: Sudah diverifikasi, belum bayar)
    menunggu_pembayaran = Permohonan.objects.filter(status_proses='Menunggu Pembayaran').order_by('created_at')
    
    # 3. Siap Ditugaskan (Sudah Bayar)
    antrean_penugasan = Permohonan.objects.filter(status_proses='Diproses', karyawan__isnull=True).order_by('created_at')

    # 4. Siap Finalisasi (Dokumen Kembali/Menunggu Finalisasi/Siap Diambil)
    siap_finalisasi = Permohonan.objects.filter(
        status_proses__in=['Menunggu Finalisasi', 'Siap Diambil']
    ).exclude(status_proses='Selesai').order_by('updated_at')
    
    # 5. Sedang Berjalan (Di Lapangan)
    sedang_berjalan = Permohonan.objects.filter(
        karyawan__isnull=False
    ).exclude(
        status_proses='Selesai'
    ).exclude(
        status_proses='Menunggu Finalisasi'
    ).exclude(
        status_proses='Diproses'
    ).order_by('-updated_at')

    # NEW: Sedang di-revisi pelanggan
    antrean_revisi = Permohonan.objects.filter(status_proses='Revisi').order_by('-updated_at')

    # NEW: Riwayat Selesai
    riwayat_selesai = Permohonan.objects.filter(status_proses='Selesai').order_by('-updated_at')[:50] # Limit 50 terakhir

    context = {
        'karyawan': karyawan,
        'nama_asli': karyawan.nama,
        'antrean_verifikasi': antrean_verifikasi,
        'menunggu_pembayaran': menunggu_pembayaran,
        'antrean_penugasan': antrean_penugasan,
        'siap_finalisasi': siap_finalisasi,
        'sedang_berjalan': sedang_berjalan,
        'antrean_revisi': antrean_revisi,
        'riwayat_selesai': riwayat_selesai
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
            # LOGIC BARU: Jika email kosong, generate dummy email
            if not email:
                timestamp_str = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                clean_wa = no_wa.replace('+', '').replace(' ', '')
                email = f"walkin_{clean_wa}_{timestamp_str}@birojasa.local"
            
            try:
                user = User.objects.get(email=email)
                pelanggan = Pelanggan.objects.get(email=email)
            except User.DoesNotExist:
                # Generate random password
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
        action = request.POST.get('action')
        staff_admin = Karyawan.objects.get(email=request.user.email)
        
        if action == 'revision':
            # Handle Partial Rejection
            has_rejection = False
            rejected_docs_names = []
            
            for dok in permohonan.berkas_upload.all():
                if request.POST.get(f'status_dok_{dok.id}') == 'tolak':
                    catatan = request.POST.get(f'catatan_dok_{dok.id}')
                    dok.status_file = 'Perbaikan'
                    dok.catatan_perbaikan = catatan
                    dok.save()
                    rejected_docs_names.append(f"- {dok.master_dokumen.nama_dokumen}: {catatan}")
                    has_rejection = True
            
            if has_rejection:
                permohonan.status_proses = 'Revisi'
                permohonan.save()
                
                # Audit Log
                PermohonanAuditLog.objects.create(
                    permohonan=permohonan,
                    karyawan=staff_admin,
                    action='rejected',
                    notes=f"Dokumen perlu perbaikan: {', '.join([d.master_dokumen.nama_dokumen for d in permohonan.berkas_upload.filter(status_file='Perbaikan')])}"
                )
                
                # Email Notifikasi
                daftar_perbaikan_html = "<br>".join(rejected_docs_names)
                subjek = f"Perbaikan Dokumen: {permohonan.kode_permohonan}"
                pesan = f"""
                <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #ffc107; padding: 20px; text-align: center;">
                        <h2 style="color: #333; margin: 0;">Perlu Perbaikan Dokumen ⚠️</h2>
                    </div>
                    <div style="padding: 30px; background-color: #ffffff;">
                        <p style="color: #555;">Halo <strong>{permohonan.pelanggan.nama}</strong>,</p>
                        <p style="color: #555;">Setelah kami verifikasi, terdapat beberapa dokumen yang perlu Anda perbaiki/upload ulang agar permohonan dapat diproses:</p>
                        
                        <div style="background-color: #fff8e1; border-left: 5px solid #ffc107; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0; color: #856404; font-weight: bold;">DAFTAR PERBAIKAN:</p>
                            <p style="margin: 10px 0 0 0; color: #555;">{daftar_perbaikan_html}</p>
                        </div>

                        <p style="color: #555;">Silakan login ke dashboard Anda untuk melakukan upload ulang pada dokumen yang dimaksud.</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://127.0.0.1:8000/dashboard/" style="background-color: #2F4F4F; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Buka Dashboard ➔</a>
                        </div>
                    </div>
                </div>
                """
                kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)
                messages.warning(request, 'Instruksi perbaikan telah dikirim ke pelanggan.')
                return redirect('staff_dashboard')

        elif action == 'verify':
            biaya_resmi = int(request.POST.get('biaya_resmi'))
            biaya_pengiriman = int(request.POST.get('biaya_pengiriman') or 0)
            
            permohonan.biaya_resmi = biaya_resmi
            permohonan.status_proses = 'Menunggu Pembayaran'
            permohonan.save()
            
            # 🔥 AUDIT LOG: Verifikasi
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
                'pembayaran': pembayaran_baru
            }

            # 2. Generate PDF
            pdf_file = render_to_pdf('core/pdf/invoice_pdf.html', pdf_context)
            
            subjek = f"Tagihan Terbit: {permohonan.kode_permohonan}"
            pesan = f"""
            <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #0dcaf0; padding: 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0;">Menunggu Pembayaran 💸</h2>
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
                            <td style="padding: 10px; font-weight: bold; text-align: right;">{pembayaran_baru.nomor_invoice}</td>
                        </tr>
                        <tr style="background-color: #f1f8f5;">
                            <td style="padding: 10px; color: #2F4F4F; font-weight: bold;">TOTAL BAYAR</td>
                            <td style="padding: 10px; color: #2F4F4F; font-weight: bold; text-align: right; font-size: 18px;">Rp {total_tagihan:,}</td>
                        </tr>
                    </table>

                    <p style="color: #555;">Detail lengkap tagihan terlampir dalam file PDF (Invoice).</p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://127.0.0.1:8000/tagihan/{permohonan.id}/" style="background-color: #0dcaf0; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Bayar Sekarang ➔</a>
                    </div>
                </div>
            </div>
            """
            
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
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if permohonan.metode_pengiriman == 'Kirim Kurir':
            resi = request.POST.get('nomor_resi')
            if not resi:
                messages.error(request, "Nomor Resi harus diisi untuk pengiriman kurir.")
                return redirect('finalisasi_permohonan', permohonan_id=permohonan.id)
            
        if permohonan.metode_pengiriman == 'Kirim Kurir':
            permohonan.nomor_resi = resi
            permohonan.status_proses = 'Dikirim'
            msg_log = f"Dokumen dalam pengiriman dengan Resi: {resi}"
            
            subjek = f"📦 DOKUMEN DIKIRIM: {permohonan.kode_permohonan}"
            pesan = f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;">
                <div style="background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%); padding: 40px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">DOKUMEN DIKIRIM 🚚</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0; font-size: 16px;">Permohonan Anda sedang dalam perjalanan</p>
                </div>
                
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #334155; margin-bottom: 25px;">Halo <strong>{permohonan.pelanggan.nama}</strong>,</p>
                    <p style="font-size: 16px; color: #475569; line-height: 1.6; margin-bottom: 30px;">
                        Kabar baik! Dokumen <strong>{permohonan.layanan.nama_layanan}</strong> Anda telah selesai diproses dan saat ini sudah kami serahkan ke pihak kurir untuk pengantaran ke alamat Anda.
                    </p>
                    
                    <div style="background-color: #fffbeb; border: 2px dashed #f59e0b; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 30px;">
                        <p style="margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #92400e; font-weight: 600;">Nomor Resi Pengiriman</p>
                        <p style="margin: 10px 0 0; font-size: 32px; font-weight: 800; color: #1e293b; letter-spacing: 2px; font-family: monospace;">{resi}</p>
                    </div>

                    <p style="font-size: 14px; color: #64748b; text-align: center;">
                        Silakan pantau status pengiriman secara berkala. Jangan lupa untuk konfirmasi penerimaan di dashboard aplikasi jika paket sudah sampai.
                    </p>
                    
                    <div style="text-align: center; margin-top: 40px;">
                        <a href="http://127.0.0.1:8000/dashboard/" style="background-color: #1e293b; color: #ffffff; padding: 16px 32px; border-radius: 50px; text-decoration: none; font-weight: 700; font-size: 16px; display: inline-block; transition: all 0.3s ease;">Buka Dashboard</a>
                    </div>
                </div>
                
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2024 BiroJasaApp. Solusi Dokumen Terpercaya.</p>
                </div>
            </div>
            """
            
        else:
            permohonan.status_proses = 'Selesai'
            msg_log = "Permohonan telah diselesaikan (Ambil di Kantor)."
            
            subjek = f"✅ SIAP DIAMBIL: {permohonan.kode_permohonan}"
            pesan = f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">DOKUMEN SELESAI 🎉</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0; font-size: 16px;">Siap untuk diambil di kantor kami</p>
                </div>
                
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #334155; margin-bottom: 25px;">Halo <strong>{permohonan.pelanggan.nama}</strong>,</p>
                    <p style="font-size: 16px; color: #475569; line-height: 1.6; margin-bottom: 30px;">
                        Selamat! Proses pengurusan dokumen <strong>{permohonan.layanan.nama_layanan}</strong> Anda telah berhasil diselesaikan. Kami telah memverifikasi kelengkapan dokumen fisik.
                    </p>
                    
                    <div style="background-color: #ecfdf5; border-left: 5px solid #10b981; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h3 style="margin: 0 0 10px; color: #065f46; font-size: 18px;">📍 Ambil di Kantor</h3>
                        <p style="margin: 0; color: #064e3b; font-size: 14px;">Silakan datang ke kantor operasional kami pada jam kerja untuk pengambilan dokumen fisik.</p>
                        <p style="margin: 15px 0 0; font-weight: 600; color: #047857;">⚠️ Harap membawa KTP asli/bukti identitas untuk validasi.</p>
                    </div>

                    <div style="text-align: center; margin-top: 40px;">
                        <a href="http://127.0.0.1:8000/dashboard/" style="background-color: #10b981; color: #ffffff; padding: 16px 32px; border-radius: 50px; text-decoration: none; font-weight: 700; font-size: 16px; display: inline-block; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">Lihat Detail di Aplikasi</a>
                    </div>
                </div>
                
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2024 BiroJasaApp. Solusi Dokumen Terpercaya.</p>
                </div>
            </div>
            """

        permohonan.save()
        
        # 🔥 AUDIT LOG
        staff_admin = Karyawan.objects.get(email=request.user.email)
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=staff_admin,
            action='finalized',
            notes=msg_log
        )
        
        kirim_notifikasi_email(subjek, pesan, permohonan.pelanggan.email)
        
        messages.success(request, msg_log)
        return redirect('staff_dashboard')

    return render(request, 'core/staff/finalisasi_form.html', {'item': permohonan})

@login_required(login_url='login')
def cetak_bast_view(request, permohonan_id):
    # Security: Hanya Staff
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')

    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    pembayaran = permohonan.tagihan

    pdf_context = {
        'permohonan': permohonan,
        'pembayaran': pembayaran,
        'tanggal': datetime.datetime.now()
    }
    
    # --- MODIFIKASI: Render HTML langsung untuk Print Browser ---
    return render(request, 'core/pdf/bast_pdf.html', pdf_context)

    # pdf_data = render_to_pdf('core/pdf/bast_pdf.html', pdf_context)
    
    # if pdf_data:
    #     from django.http import HttpResponse
    #     response = HttpResponse(pdf_data, content_type='application/pdf')
    #     response['Content-Disposition'] = f'attachment; filename="BAST_{permohonan.kode_permohonan}.pdf"'
    #     return response
    
    # messages.error(request, "Gagal membuat PDF BAST.")
    # return redirect('staff_dashboard')

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

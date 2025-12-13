import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

# Import Models
from ..models import Pembayaran, Permohonan, Karyawan, PembayaranAuditLog

# Import Helpers
from ..utils import kirim_notifikasi_email, render_to_pdf

# ==========================================
# STAFF KEUANGAN VIEWS
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
    return render(request, 'core/staff/keuangan_dashboard.html', context)

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
        
        # 🔥 AUDIT LOG: Payment verification & confirmation
        staff_keuangan = Karyawan.objects.get(email=request.user.email)
        PembayaranAuditLog.objects.create(
            pembayaran=pembayaran,
            karyawan=staff_keuangan,
            action='payment_verified',
            notes=f'Terima {metode_dipilih}. Total: Rp {pembayaran.total_biaya:,}'
        )
        PembayaranAuditLog.objects.create(
            pembayaran=pembayaran,
            karyawan=staff_keuangan,
            action='payment_confirmed',
            notes='Pembayaran dikonfirmasi lunas'
        )
        
        # 3. Update Status Permohonan
        permohonan = pembayaran.permohonan
        permohonan.status_proses = 'Diproses'
        permohonan.save()
        
# --- MULAI UPDATE (GENERATE STRUK PDF) ---
        pdf_context = {
            'permohonan': permohonan,
            'pembayaran': pembayaran
        }
        pdf_file = render_to_pdf('core/pdf/struk_lunas_pdf.html', pdf_context)
        
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

from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Import Models
from ..models import Permohonan, Karyawan, PermohonanAuditLog

# Import Helpers
from ..utils import kirim_notifikasi_email

# ==========================================
# STAFF LAPANGAN VIEWS
# ==========================================

@login_required(login_url='login')
def lapangan_dashboard_view(request):
    try:
        karyawan = Karyawan.objects.get(email=request.user.email)
        if karyawan.role != 'lapangan':
            return redirect('dashboard')
    except:
        return redirect('dashboard')

    # Tugas Aktif: Yang statusnya masih progres di lapangan (belum balik kantor/selesai)
    daftar_tugas = Permohonan.objects.filter(karyawan=karyawan).exclude(
        status_proses__icontains='Selesai'
    ).exclude(
        status_proses='Menunggu Finalisasi'
    ).exclude(
        status_proses='Dikirim'
    ).order_by('-updated_at')

    # Riwayat Tugas: Yang sudah diserahkan balik ke kantor atau sudah beres
    riwayat_tugas = Permohonan.objects.filter(karyawan=karyawan).filter(
        models.Q(status_proses__icontains='Selesai') | 
        models.Q(status_proses='Menunggu Finalisasi') |
        models.Q(status_proses='Dikirim')
    ).order_by('-updated_at')
    
    context = {
        'karyawan': karyawan, 
        'daftar_tugas': daftar_tugas,
        'riwayat_tugas': riwayat_tugas
    }
    return render(request, 'core/staff/lapangan_dashboard.html', context)

@login_required(login_url='login')
def update_status_lapangan_view(request, permohonan_id):
    permohonan = get_object_or_404(Permohonan, id=permohonan_id)
    
    # SECURITY: Prevent modification of finalized tasks
    if permohonan.status_proses in ['Menunggu Finalisasi', 'Siap Diambil', 'Selesai', 'Dikirim']:
        messages.error(request, "Tugas ini sudah selesai dan dikunci. Anda tidak bisa mengubahnya lagi.")
        return redirect('lapangan_dashboard')
    if request.method == 'POST':
        status_baru = request.POST.get('status_baru')
        permohonan.status_proses = status_baru
        
        # Tangkap foto dokumen jadi jika diupload
        foto_hasil = request.FILES.get('hasil_lapangan')
        if foto_hasil:
            permohonan.hasil_lapangan = foto_hasil
            
        permohonan.save()
        
        # 🔥 AUDIT LOG: Status update
        staff_lapangan = Karyawan.objects.get(email=request.user.email)
        action_map = {
            'Proses Lapangan': 'in_progress',
            'Kembali dari Lapangan': 'completed',
            'Dikirim ke Pelanggan': 'delivered',
            'Selesai': 'delivered'
        }
        action = action_map.get(status_baru, 'in_progress')
        PermohonanAuditLog.objects.create(
            permohonan=permohonan,
            karyawan=staff_lapangan,
            action=action,
            notes=f'Status diupdate menjadi: {status_baru}'
        )
        
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

    return render(request, 'core/staff/update_status_form.html', {'item': permohonan})

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
    return render(request, 'core/staff/lapangan_detail.html', context)

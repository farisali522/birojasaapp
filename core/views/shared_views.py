from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Import Models
from ..models import Pelanggan, Permohonan, LayananDokumen, Dokumen

# ==========================================
# SHARED VIEWS (USED BY MULTIPLE ROLES)
# ==========================================

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
    return render(request, 'core/shared/edit_profil.html', {'pelanggan': pelanggan})

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
    return render(request, 'core/shared/detail_permohonan.html', context)

@login_required(login_url='login')
def revisi_pengajuan_view(request, permohonan_id):
    # Security: Hanya pemilik yang boleh revisi
    permohonan = get_object_or_404(Permohonan, id=permohonan_id, pelanggan__email=request.user.email)
    
    # Izinkan revisi jika status 'Ditolak' (total) ATAU 'Revisi' (parsial)
    if permohonan.status_proses not in ['Ditolak', 'Revisi']:
        messages.error(request, "Permohonan ini tidak butuh perbaikan saat ini.")
        return redirect('dashboard')

    # Ambil dokumen yang butuh perbaikan
    if permohonan.status_proses == 'Revisi':
        dokumen_revisi = permohonan.berkas_upload.filter(status_file='Perbaikan')
    else:
        # Jika ditolak total, tampilkan semua syarat layanan
        dokumen_revisi = permohonan.berkas_upload.all()

    if request.method == 'POST':
        try:
            files_count = 0
            for dok in dokumen_revisi:
                file_input_name = f"file_dok_{dok.id}"
                file_upload = request.FILES.get(file_input_name)
                
                if file_upload:
                    dok.path_file = file_upload
                    dok.status_file = 'Digital Diupload' # Reset status
                    dok.catatan_perbaikan = None # Hapus catatan lama
                    dok.save()
                    files_count += 1

            # 2. Reset Status Permohonan ke Verifikasi Ulang
            permohonan.status_proses = 'Menunggu Verifikasi'
            
            # Jika sebelumnya ditolak total, hapus catatan penolakan
            if permohonan.status_proses == 'Ditolak':
                permohonan.catatan_penolakan = None
                
            # Update catatan pelanggan jika ada
            catatan_baru = request.POST.get('catatan')
            if catatan_baru:
                permohonan.catatan_pelanggan = catatan_baru
                
            permohonan.save()

            messages.success(request, f'Berhasil mengupdate {files_count} dokumen. Permohonan Anda dikirim ulang ke admin.')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f"Gagal mengirim revisi: {e}")

    context = {
        'permohonan': permohonan,
        'dokumen_revisi': dokumen_revisi
    }
    return render(request, 'core/shared/form_revisi.html', context)

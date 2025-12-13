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
    return render(request, 'core/edit_profil.html', {'pelanggan': pelanggan})

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

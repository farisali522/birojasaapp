import datetime
import csv
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count

# Import Models
from ..models import Pelanggan, Permohonan, Pembayaran, Karyawan, Layanan, MasterDokumen, LayananDokumen

# ==========================================
# HELPER DECORATOR
# ==========================================

def manajer_check(user):
    try:
        return Karyawan.objects.get(email=user.email).role == 'manajer'
    except Karyawan.DoesNotExist:
        return False

# ==========================================
# MANAJER VIEWS - DASHBOARD & REPORTS
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
# MANAJER VIEWS - EMPLOYEE MANAGEMENT
# ==========================================

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

# ==========================================
# MANAJER VIEWS - SERVICE MASTER DATA
# ==========================================

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

# ==========================================
# MANAJER VIEWS - DOCUMENT MASTER DATA
# ==========================================

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

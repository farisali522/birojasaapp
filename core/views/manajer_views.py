import datetime
import csv
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

# Import Models
from ..models import Pelanggan, Permohonan, Pembayaran, Karyawan, Layanan, MasterDokumen, LayananDokumen

# Import Helpers
from ..utils import render_to_pdf

# ==========================================
# HELPER DECORATOR
# ==========================================

def manajer_check(user):
    try:
        return Karyawan.objects.filter(email=user.email, role='manajer').exists()
    except:
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

# 🔥 NEW: LAPORAN GABUNGAN (Operasional + Keuangan)
@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def cetak_laporan_gabungan_view(request):
    """
    Cetak Laporan Operasional & Keuangan Gabungan
    Filter: Harian, Mingguan, Bulanan, Tahunan
    """
    karyawan = Karyawan.objects.get(email=request.user.email)
    
    # Default: Bulan ini
    today = timezone.now().date()
    start_date = today.replace(day=1)
    end_date = today
    
    # Ambil parameter filter
    periode = request.GET.get('periode', 'bulanan')
    custom_start = request.GET.get('start_date')
    custom_end = request.GET.get('end_date')
    
    # Hitung tanggal berdasarkan periode
    if periode == 'harian':
        start_date = today
        end_date = today
        label_periode = today.strftime('%d %B %Y')
    elif periode == 'mingguan':
        start_date = today - timedelta(days=today.weekday())  # Senin minggu ini
        end_date = start_date + timedelta(days=6)  # Minggu
        label_periode = f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}"
    elif periode == 'bulanan':
        start_date = today.replace(day=1)
        # Last day of month
        if today.month == 12:
            end_date = today.replace(day=31)
        else:
            end_date = (today.replace(month=today.month+1, day=1) - timedelta(days=1))
        label_periode = today.strftime('%B %Y')
    elif periode == 'tahunan':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        label_periode = f'Tahun {today.year}'
    elif periode == 'custom' and custom_start and custom_end:
        start_date = datetime.datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(custom_end, '%Y-%m-%d').date()
        label_periode = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
    
    # === LAPORAN OPERASIONAL ===
    permohonan_list = Permohonan.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).order_by('-created_at')
    
    # Statistik operasional
    total_permohonan = permohonan_list.count()
    permohonan_selesai = permohonan_list.filter(status_proses='Selesai').count()
    permohonan_diproses = permohonan_list.exclude(status_proses__in=['Selesai', 'Ditolak']).count()
    permohonan_ditolak = permohonan_list.filter(status_proses='Ditolak').count()
    
    # Breakdown per layanan
    layanan_stats = permohonan_list.values('layanan__nama_layanan').annotate(
        jumlah=Count('id')
    ).order_by('-jumlah')
    
    # === LAPORAN KEUANGAN ===
    pembayaran_list = Pembayaran.objects.filter(
        status_pembayaran='paid',
        updated_at__date__range=[start_date, end_date]
    ).order_by('-updated_at')
    
    # Statistik keuangan
    total_transaksi = pembayaran_list.count()
    total_pemasukan = pembayaran_list.aggregate(Sum('total_biaya'))['total_biaya__sum'] or 0
    
    # Breakdown per metode pembayaran
    metode_stats = pembayaran_list.values('metode_pembayaran').annotate(
        jumlah=Count('id'),
        total=Sum('total_biaya')
    ).order_by('-total')
    
    # Jika request adalah cetak PDF
    if 'print' in request.GET:
        context = {
            'karyawan': karyawan,
            'periode': label_periode,
            'start_date': start_date,
            'end_date': end_date,
            'generated_at': timezone.now(),
            
            # Operasional
            'total_permohonan': total_permohonan,
            'permohonan_selesai': permohonan_selesai,
            'permohonan_diproses': permohonan_diproses,
            'permohonan_ditolak': permohonan_ditolak,
            'layanan_stats': layanan_stats,
            'permohonan_list': permohonan_list[:20],  # Top 20
            
            # Keuangan
            'total_transaksi': total_transaksi,
            'total_pemasukan': total_pemasukan,
            'metode_stats': metode_stats,
            'pembayaran_list': pembayaran_list[:20],  # Top 20
        }
        
        pdf = render_to_pdf('core/laporan_gabungan_pdf.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Laporan_{periode}_{today}.pdf"'
            return response
        else:
            messages.error(request, 'Gagal generate PDF')
            return redirect('cetak_laporan_gabungan')
    
    # Tampilkan form filter
    context = {
        'karyawan': karyawan,
        'periode': periode,
        'label_periode': label_periode,
        'start_date': start_date,
        'end_date': end_date,
        
        # Operasional
        'total_permohonan': total_permohonan,
        'permohonan_selesai': permohonan_selesai,
        'permohonan_diproses': permohonan_diproses,
        'permohonan_ditolak': permohonan_ditolak,
        'layanan_stats': layanan_stats,
        
        # Keuangan
        'total_transaksi': total_transaksi,
        'total_pemasukan': total_pemasukan,
        'metode_stats': metode_stats,
    }
    return render(request, 'core/cetak_laporan_gabungan.html', context)


# ==========================================
# MANAJER VIEWS - EMPLOYEE MANAGEMENT
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def manajer_karyawan_list_view(request):
    if not Karyawan.objects.filter(email=request.user.email).exists():
        return redirect('dashboard')
    
    karyawan_list = Karyawan.objects.all().order_by('nama')
    context = {
        'karyawan_list': karyawan_list
    }
    return render(request, 'core/manajer_karyawan_list.html', context)

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def manajer_karyawan_create_view(request):
    if request.method == 'POST':
        nama = request.POST.get('nama')
        email = request.POST.get('email')
        no_wa = request.POST.get('no_wa')
        role = request.POST.get('role')
        
        # Generate kode
        kode = f"KRY-{Karyawan.objects.count() + 1}"
        
        # Create User
        try:
            user = User.objects.create_user(username=email, email=email, password=uuid.uuid4().hex[:8])
            Karyawan.objects.create(
                kode_karyawan=kode,
                nama=nama,
                email=email,
                no_whatsapp=no_wa,
                role=role
            )
            messages.success(request, f"Kar yawan {nama} berhasil ditam bahkan.")
            return redirect('manajer_karyawan_list')
        except:
            messages.error(request, "Email sudah terdaftar.")
    
    return render(request, 'core/manajer_karyawan_form.html')

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def manajer_karyawan_edit_view(request, karyawan_id):
    karyawan = get_object_or_404(Karyawan, id=karyawan_id)
    
    if request.method == 'POST':
        karyawan.nama = request.POST.get('nama')
        karyawan.no_whatsapp = request.POST.get('no_wa')
        karyawan.role = request.POST.get('role')
        karyawan.save()
        messages.success(request, "Data karyawan diupdate.")
        return redirect('manajer_karyawan_list')
    
    return render(request, 'core/manajer_karyawan_form.html', {'karyawan': karyawan})

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def manajer_karyawan_delete_view(request, karyawan_id):
    karyawan = get_object_or_404(Karyawan, id=karyawan_id)
    try:
        user = User.objects.get(email=karyawan.email)
        user.delete()
    except:
        pass
    karyawan.delete()
    messages.success(request, "Karyawan dihapus.")
    return redirect('manajer_karyawan_list')

# ==========================================
# MANAJER VIEWS - SERVICE MASTER DATA
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_list_view(request):
    layanan_list = Layanan.objects.all().order_by('nama_layanan')
    return render(request, 'core/master_layanan_list.html', {'layanan_list': layanan_list})

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_form_view(request, layanan_id=None):
    layanan = None
    if layanan_id:
        layanan = get_object_or_404(Layanan, id=layanan_id)
    
    if request.method == 'POST':
        nama = request.POST.get('nama_layanan')
        harga = request.POST.get('harga_jasa')
        estimasi = request.POST.get('estimasi_waktu')
        
        if layanan:
            layanan.nama_layanan = nama
            layanan.harga_jasa = harga
            layanan.estimasi_waktu = estimasi
            layanan.save()
            messages.success(request, "Layanan diupdate.")
        else:
            kode = f"LAY-{Layanan.objects.count() + 1}"
            Layanan.objects.create(kode_layanan=kode, nama_layanan=nama, harga_jasa=harga, estimasi_waktu=estimasi)
            messages.success(request, "Layanan ditambahkan.")
        return redirect('master_layanan_list')
    
    return render(request, 'core/master_layanan_form.html', {'layanan': layanan})

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_requirements_view(request, layanan_id):
    layanan = get_object_or_404(Layanan, id=layanan_id)
    all_dokumen = MasterDokumen.objects.all()
    current_syarat = LayananDokumen.objects.filter(layanan=layanan)
    
    if request.method == 'POST':
        # Clear existing
        current_syarat.delete()
        
        # Add new
        for dok in all_dokumen:
            if f'dok_{dok.id}' in request.POST:
                is_wajib = request.POST.get(f'wajib_{dok.id}') == 'on'
                LayananDokumen.objects.create(
                    layanan=layanan,
                    master_dokumen=dok,
                    is_wajib=is_wajib
                )
        messages.success(request, "Syarat dokumen diupdate.")
        return redirect('master_layanan_list')
    
    current_ids = [s.master_dokumen.id for s in current_syarat]
    context = {
        'layanan': layanan,
        'all_dokumen': all_dokumen,
        'current_syarat': current_syarat,
        'current_ids': current_ids
    }
    return render(request, 'core/master_layanan_requirements.html', context)

# ==========================================
# MANAJER VIEWS - DOCUMENT MASTER DATA
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_list_view(request):
    if request.method == 'POST' and 'delete_id' in request.POST:
        doc_id = request.POST.get('delete_id')
        MasterDokumen.objects.filter(id=doc_id).delete()
        messages.success(request, "Dokumen dihapus.")
        return redirect('master_dokumen_list')
    
    dokumen_list = MasterDokumen.objects.all().order_by('nama_dokumen')
    return render(request, 'core/master_dokumen_list.html', {'dokumen_list': dokumen_list})

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_form_view(request, doc_id=None):
    dokumen = None
    if doc_id:
        dokumen = get_object_or_404(MasterDokumen, id=doc_id)
    
    if request.method == 'POST':
        nama = request.POST.get('nama_dokumen')
        desk = request.POST.get('deskripsi')
        
        if dokumen:
            dokumen.nama_dokumen = nama
            dokumen.deskripsi = desk
            dokumen.save()
        else:
            MasterDokumen.objects.create(nama_dokumen=nama, deskripsi=desk)
        messages.success(request, "Data disimpan.")
        return redirect('master_dokumen_list')
    
    return render(request, 'core/master_dokumen_form.html', {'dokumen': dokumen})

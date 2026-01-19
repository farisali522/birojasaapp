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

# Firebase Imports
import firebase_admin
from firebase_admin import credentials, auth

# Import Models
from ..models import Pelanggan, Permohonan, Pembayaran, Karyawan, Layanan, MasterDokumen, LayananDokumen, AktivitasLogin, TahapanLayanan

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
    
    # --- FITUR MONITORING LOGIN (Peningkatan dengan IP) ---
    # 1. Staff Terkini Login
    staff_emails = Karyawan.objects.values_list('email', flat=True)
    recent_staff_logins = AktivitasLogin.objects.filter(user__email__in=staff_emails).order_by('-timestamp')[:10]
    
    # Ambil data karyawan untuk ucapan selamat datang
    karyawan = Karyawan.objects.get(email=request.user.email)

    context = {
        'karyawan': karyawan,
        'total_pelanggan': total_pelanggan,
        'total_permohonan': total_permohonan,
        'total_uang': total_uang,
        'status_stats': status_stats,
        'recent_staff_logins': recent_staff_logins,
    }
    return render(request, 'core/manajer/manajer_dashboard.html', context)

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

    return render(request, 'core/manajer/laporan.html', {'laporan': laporan, 'total_pemasukan': total_pemasukan, 'start_date': start_date, 'end_date': end_date})

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
    # Penting: order_by() kosong di awal me-reset sorting default agar GROUP BY valid
    layanan_stats = permohonan_list.order_by().values('layanan__nama_layanan').annotate(
        jumlah_count=Count('id')
    ).order_by('-jumlah_count')
    
    # === LAPORAN KEUANGAN ===
    pembayaran_list = Pembayaran.objects.filter(
        status_pembayaran='paid',
        updated_at__date__range=[start_date, end_date]
    ).order_by('-updated_at')
    
    # Statistik keuangan
    total_transaksi = pembayaran_list.count()
    total_pemasukan = pembayaran_list.aggregate(Sum('total_biaya'))['total_biaya__sum'] or 0
    
    # Breakdown per metode pembayaran
    # Gunakan QS baru agar tidak terganggu sorting/caching dari pembayaran_list
    stats_payment_qs = Pembayaran.objects.filter(
        status_pembayaran='paid',
        updated_at__date__range=[start_date, end_date]
    )
    
    # values() harus di-chain langsung dengan annotate() tanpa ordering default model
    metode_stats = stats_payment_qs.order_by().values('metode_pembayaran').annotate(
        jumlah_count=Count('id'),
        total_bayar=Sum('total_biaya')
    ).order_by('-total_bayar')
    
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
            'permohonan_list': permohonan_list,
            
            # Keuangan
            'total_transaksi': total_transaksi,
            'total_pemasukan': total_pemasukan,
            'metode_stats': metode_stats,
            'pembayaran_list': pembayaran_list,
        }
        
        pdf = render_to_pdf('core/pdf/laporan_gabungan_pdf.html', context)
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
    return render(request, 'core/manajer/cetak_laporan_gabungan.html', context)


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
    return render(request, 'core/manajer/manajer_karyawan_list.html', context)

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
    
    return render(request, 'core/manajer/manajer_karyawan_form.html')

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
    
    return render(request, 'core/manajer/manajer_karyawan_form.html', {'item': karyawan})

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def manajer_karyawan_delete_view(request, karyawan_id):
    messages.error(request, "Penghapusan karyawan tidak diperbolehkan. Silakan hubungi Administrator Sistem.")
    return redirect('manajer_karyawan_list')

# ==========================================
# MANAJER VIEWS - SERVICE MASTER DATA
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_list_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 1. Handle Layanan Deletion
        if 'layanan_id' in request.POST and action == 'delete_layanan':
            layanan_id = request.POST.get('layanan_id')
            Layanan.objects.filter(id=layanan_id).delete()
            messages.success(request, "Layanan dihapus.")
            return redirect('master_layanan_list')
        
        # 2. Handle MasterDokumen Deletion
        if 'delete_id' in request.POST and action == 'delete_dokumen':
            doc_id = request.POST.get('delete_id')
            MasterDokumen.objects.filter(id=doc_id).delete()
            messages.success(request, "Dokumen dihapus.")
            return redirect('master_layanan_list')

        # 3. Handle Toggle Syarat (Matrix)
        if action == 'toggle_syarat':
            lay_id = request.POST.get('layanan_id')
            dok_id = request.POST.get('dokumen_id')
            layanan = get_object_or_404(Layanan, id=lay_id)
            master_dok = get_object_or_404(MasterDokumen, id=dok_id)
            
            syarat, created = LayananDokumen.objects.get_or_create(layanan=layanan, master_dokumen=master_dok)
            if not created:
                syarat.delete()
                messages.info(request, f"Syarat {master_dok.nama_dokumen} dihapus dari {layanan.nama_layanan}.")
            else:
                messages.success(request, f"Syarat {master_dok.nama_dokumen} ditambahkan ke {layanan.nama_layanan}.")
            return redirect('master_layanan_list')

        # 4. Handle Toggle Wajib (Matrix)
        if action == 'toggle_wajib':
            lay_id = request.POST.get('layanan_id')
            dok_id = request.POST.get('dokumen_id')
            syarat = get_object_or_404(LayananDokumen, layanan_id=lay_id, master_dokumen_id=dok_id)
            syarat.is_wajib = not syarat.is_wajib
            syarat.save()
            status = "WAJIB" if syarat.is_wajib else "OPSIONAL"
            messages.success(request, f"Status {syarat.master_dokumen.nama_dokumen} diubah menjadi {status}.")
            return redirect('master_layanan_list')

    layanan_list = Layanan.objects.all().order_by('nama_layanan')
    master_dokumen_list = MasterDokumen.objects.all().order_by('nama_dokumen')
    
    # Ambil pemetaan untuk matriks
    mapping_qs = LayananDokumen.objects.all()
    matrix_mapping = {(m.layanan_id, m.master_dokumen_id): m for m in mapping_qs}
    
    # Restrukturisasi data agar mudah di-loop di template (Matrix Data)
    matrix_rows = []
    for lay in layanan_list:
        row_cells = []
        for dok in master_dokumen_list:
            syarat = matrix_mapping.get((lay.id, dok.id))
            row_cells.append({
                'dokumen_id': dok.id,
                'syarat': syarat # Berisi objek LayananDokumen jika ada, else None
            })
        matrix_rows.append({
            'layanan': lay,
            'cells': row_cells
        })
    
    context = {
        'layanan_list': layanan_list,
        'master_dokumen_list': master_dokumen_list,
        'matrix_rows': matrix_rows, # Data baru untuk matrix
    }
    return render(request, 'core/manajer/master_layanan_list.html', context)

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_form_view(request, layanan_id=None):
    item = None
    is_edit = False
    if layanan_id:
        item = get_object_or_404(Layanan, id=layanan_id)
        is_edit = True
    
    if request.method == 'POST':
        nama = request.POST.get('nama_layanan')
        deskripsi = request.POST.get('deskripsi', '')
        harga = request.POST.get('harga_jasa')
        estimasi = request.POST.get('estimasi_waktu')
        has_custom_tahapan = request.POST.get('has_custom_tahapan') == 'on'
        
        if item:
            item.nama_layanan = nama
            item.deskripsi = deskripsi
            item.harga_jasa = harga
            item.estimasi_waktu = estimasi
            item.has_custom_tahapan = has_custom_tahapan
            item.save()
            messages.success(request, "Layanan diupdate.")
        else:
            kode = f"LAY-{Layanan.objects.count() + 1}"
            Layanan.objects.create(
                kode_layanan=kode, 
                nama_layanan=nama, 
                deskripsi=deskripsi,
                harga_jasa=harga, 
                estimasi_waktu=estimasi,
                has_custom_tahapan=has_custom_tahapan
            )
            messages.success(request, "Layanan ditambahkan.")
        return redirect('master_layanan_list')
    
    return render(request, 'core/manajer/master_layanan_form.html', {'item': item, 'is_edit': is_edit})

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
    return render(request, 'core/manajer/master_layanan_requirements.html', context)

# ==========================================
# MANAJER VIEWS - DOCUMENT MASTER DATA
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_list_view(request):
    # Sekarang sudah digabung ke Master Control Center
    return redirect('master_layanan_list')

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_dokumen_form_view(request, doc_id=None):
    item = None
    is_edit = False
    if doc_id:
        item = get_object_or_404(MasterDokumen, id=doc_id)
        is_edit = True
    
    if request.method == 'POST':
        nama = request.POST.get('nama_dokumen')
        desk = request.POST.get('deskripsi')
        
        if item:
            # Jika sedang edit, pastikan nama baru tidak dipunyai dokumen lain
            if MasterDokumen.objects.filter(nama_dokumen=nama).exclude(id=doc_id).exists():
                messages.error(request, f"Dokumen dengan nama '{nama}' sudah ada.")
                return render(request, 'core/manajer/master_dokumen_form.html', {'item': item, 'is_edit': is_edit})
            
            item.nama_dokumen = nama
            item.deskripsi = desk
            item.save()
            messages.success(request, "Data diupdate.")
        else:
            # Jika sedang tambah baru, pastikan nama belum ada
            if MasterDokumen.objects.filter(nama_dokumen=nama).exists():
                messages.error(request, f"Dokumen dengan nama '{nama}' sudah ada.")
                return render(request, 'core/manajer/master_dokumen_form.html', {'item': item, 'is_edit': is_edit})
            
            MasterDokumen.objects.create(nama_dokumen=nama, deskripsi=desk)
            messages.success(request, "Data disimpan.")
        return redirect('master_dokumen_list')
    
    return render(request, 'core/manajer/master_dokumen_form.html', {'item': item, 'is_edit': is_edit})

# ==========================================
# MANAJER VIEWS - TAHAPAN LAYANAN (BPKB WORKFLOW)
# ==========================================

@login_required(login_url='login')
@user_passes_test(manajer_check, login_url='dashboard')
def master_layanan_tahapan_view(request, layanan_id):
    """
    Manage tahapan (process stages) for a specific layanan.
    Used for multi-step workflows like BPKB change process.
    """
    layanan = get_object_or_404(Layanan, id=layanan_id)
    tahapan_list = TahapanLayanan.objects.filter(layanan=layanan).order_by('urutan')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Add new tahapan
        if action == 'add':
            nama = request.POST.get('nama_tahapan')
            deskripsi = request.POST.get('deskripsi', '')
            is_payment = request.POST.get('is_payment_required') == 'on'
            biaya = request.POST.get('biaya_tahapan') or 0
            
            # Calculate next urutan
            last_urutan = tahapan_list.last()
            next_urutan = (last_urutan.urutan + 1) if last_urutan else 1
            
            TahapanLayanan.objects.create(
                layanan=layanan,
                urutan=next_urutan,
                nama_tahapan=nama,
                deskripsi=deskripsi,
                is_payment_required=is_payment,
                biaya_tahapan=biaya
            )
            messages.success(request, f"Tahapan '{nama}' ditambahkan.")
            return redirect('master_layanan_tahapan', layanan_id=layanan_id)
        
        # Edit tahapan
        elif action == 'edit':
            tahapan_id = request.POST.get('tahapan_id')
            tahapan = get_object_or_404(TahapanLayanan, id=tahapan_id, layanan=layanan)
            tahapan.nama_tahapan = request.POST.get('nama_tahapan')
            tahapan.deskripsi = request.POST.get('deskripsi', '')
            tahapan.is_payment_required = request.POST.get('is_payment_required') == 'on'
            tahapan.biaya_tahapan = request.POST.get('biaya_tahapan') or 0
            tahapan.save()
            messages.success(request, "Tahapan diupdate.")
            return redirect('master_layanan_tahapan', layanan_id=layanan_id)
        
        # Delete tahapan
        elif action == 'delete':
            tahapan_id = request.POST.get('tahapan_id')
            TahapanLayanan.objects.filter(id=tahapan_id, layanan=layanan).delete()
            
            # Reorder remaining tahapan
            for idx, t in enumerate(TahapanLayanan.objects.filter(layanan=layanan).order_by('urutan'), 1):
                t.urutan = idx
                t.save()
            
            messages.success(request, "Tahapan dihapus.")
            return redirect('master_layanan_tahapan', layanan_id=layanan_id)
        
        # Move up
        elif action == 'move_up':
            tahapan_id = request.POST.get('tahapan_id')
            tahapan = get_object_or_404(TahapanLayanan, id=tahapan_id, layanan=layanan)
            if tahapan.urutan > 1:
                prev_tahapan = TahapanLayanan.objects.filter(layanan=layanan, urutan=tahapan.urutan - 1).first()
                if prev_tahapan:
                    prev_tahapan.urutan = tahapan.urutan
                    prev_tahapan.save()
                    tahapan.urutan -= 1
                    tahapan.save()
            return redirect('master_layanan_tahapan', layanan_id=layanan_id)
        
        # Move down
        elif action == 'move_down':
            tahapan_id = request.POST.get('tahapan_id')
            tahapan = get_object_or_404(TahapanLayanan, id=tahapan_id, layanan=layanan)
            next_tahapan = TahapanLayanan.objects.filter(layanan=layanan, urutan=tahapan.urutan + 1).first()
            if next_tahapan:
                next_tahapan.urutan = tahapan.urutan
                next_tahapan.save()
                tahapan.urutan += 1
                tahapan.save()
            return redirect('master_layanan_tahapan', layanan_id=layanan_id)
    
    context = {
        'layanan': layanan,
        'tahapan_list': tahapan_list,
    }
    return render(request, 'core/manajer/master_layanan_tahapan.html', context)


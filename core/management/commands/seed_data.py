"""
Seeder Command - Membuat data sample untuk testing
Jalankan dengan: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from core.models import Karyawan, Pelanggan, Layanan, MasterDokumen, LayananDokumen, TahapanLayanan


class Command(BaseCommand):
    help = 'Seed database dengan data sample untuk testing'

    def create_groups(self):
        """Create role groups"""
        self.stdout.write('\n📝 Membuat groups...')
        
        groups = ['Manajer', 'Staff Admin', 'Staff Keuangan', 'Staff Lapangan', 'Pelanggan']
        
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"  ✅ Group {group_name} dibuat")
            else:
                self.stdout.write(f"  ⏭️  Group {group_name} sudah ada")
        
        return {
            'manajer': Group.objects.get(name='Manajer'),
            'staff_admin': Group.objects.get(name='Staff Admin'),
            'staff_keuangan': Group.objects.get(name='Staff Keuangan'),
            'lapangan': Group.objects.get(name='Staff Lapangan'),
            'pelanggan': Group.objects.get(name='Pelanggan'),
        }

    def handle(self, *args, **options):
        self.stdout.write('🌱 Memulai seeding database...\n')
        
        # === 0. CREATE GROUPS ===
        groups = self.create_groups()
        
        # === 1. CREATE USERS & KARYAWAN ===
        self.stdout.write('\n📝 Membuat akun users...')
        
        users_data = [
            {
                'username': 'manajer@test.com',
                'email': 'manajer@test.com',
                'password': 'password123',
                'group': groups['manajer'],
                'karyawan': {
                    'kode': 'KRY-001',
                    'nama': 'Ahmad Manajer',
                    'role': 'manajer',
                    'no_wa': '081234567890'
                }
            },
            {
                'username': 'admin@test.com',
                'email': 'admin@test.com',
                'password': 'password123',
                'group': groups['staff_admin'],
                'karyawan': {
                    'kode': 'KRY-002',
                    'nama': 'Budi Staff Admin',
                    'role': 'staff_admin',
                    'no_wa': '081234567891'
                }
            },
            {
                'username': 'keuangan@test.com',
                'email': 'keuangan@test.com',
                'password': 'password123',
                'group': groups['staff_keuangan'],
                'karyawan': {
                    'kode': 'KRY-003',
                    'nama': 'Citra Keuangan',
                    'role': 'staff_keuangan',
                    'no_wa': '081234567892'
                }
            },
            {
                'username': 'lapangan@test.com',
                'email': 'lapangan@test.com',
                'password': 'password123',
                'group': groups['lapangan'],
                'karyawan': {
                    'kode': 'KRY-004',
                    'nama': 'Dedi Lapangan',
                    'role': 'lapangan',
                    'no_wa': '081234567893'
                }
            },
        ]
        
        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={'email': data['email']}
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(f"  ✅ User {data['username']} dibuat")
            else:
                self.stdout.write(f"  ⏭️  User {data['username']} sudah ada")
            
            # Add user to group
            user.groups.add(data['group'])
            
            # Create Karyawan
            kry_data = data['karyawan']
            karyawan, created = Karyawan.objects.get_or_create(
                email=data['email'],
                defaults={
                    'kode_karyawan': kry_data['kode'],
                    'nama': kry_data['nama'],
                    'role': kry_data['role'],
                    'no_whatsapp': kry_data['no_wa']
                }
            )
            if created:
                self.stdout.write(f"  ✅ Karyawan {kry_data['nama']} ({kry_data['role']}) dibuat")
        
        # === 2. CREATE PELANGGAN ===
        self.stdout.write('\n📝 Membuat akun pelanggan...')
        
        pelanggan_data = [
            {
                'username': 'pelanggan@test.com',
                'email': 'pelanggan@test.com',
                'password': 'password123',
                'pelanggan': {
                    'kode': 'PLG-001',
                    'nama': 'Eko Pelanggan',
                    'no_wa': '081234567894',
                    'alamat': 'Jl. Merdeka No. 123, Jakarta'
                }
            },
            {
                'username': 'pelanggan2@test.com',
                'email': 'pelanggan2@test.com',
                'password': 'password123',
                'pelanggan': {
                    'kode': 'PLG-002',
                    'nama': 'Fitri Customer',
                    'no_wa': '081234567895',
                    'alamat': 'Jl. Sudirman No. 456, Bandung'
                }
            },
        ]
        
        for data in pelanggan_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={'email': data['email']}
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(f"  ✅ User {data['username']} dibuat")
            else:
                self.stdout.write(f"  ⏭️  User {data['username']} sudah ada")
            
            # Add user to Pelanggan group
            user.groups.add(groups['pelanggan'])
            
            # Create Pelanggan
            plg_data = data['pelanggan']
            pelanggan, created = Pelanggan.objects.get_or_create(
                email=data['email'],
                defaults={
                    'kode_pelanggan': plg_data['kode'],
                    'nama': plg_data['nama'],
                    'no_whatsapp': plg_data['no_wa'],
                    'alamat_lengkap': plg_data['alamat']
                }
            )
            if created:
                self.stdout.write(f"  ✅ Pelanggan {plg_data['nama']} dibuat")
        
        # === 3. CREATE LAYANAN ===
        self.stdout.write('\n📝 Membuat data layanan...')
        
        layanan_data = [
            {
                'kode': 'LAY-001',
                'nama': 'Perpanjang STNK Tahunan',
                'harga': 150000,
                'estimasi': '1-2 Hari Kerja',
                'has_tahapan': False
            },
            {
                'kode': 'LAY-002',
                'nama': 'Perpanjang STNK 5 Tahunan',
                'harga': 250000,
                'estimasi': '3-5 Hari Kerja',
                'has_tahapan': False
            },
            {
                'kode': 'LAY-003',
                'nama': 'Perubahan BPKB (BBN 2) - Ubah Alamat',
                'harga': 500000,
                'estimasi': '7-14 Hari Kerja',
                'deskripsi': 'Proses perubahan BPKB sesuai ketentuan resmi dengan 8 tahapan.',
                'has_tahapan': True,
                'tahapan': [
                    {'nama': 'Cek Fisik Ranmor', 'deskripsi': 'Pemeriksaan fisik kendaraan', 'biaya': 0},
                    {'nama': 'Pengesahan Cek Fisik', 'deskripsi': 'Verifikasi data di sistem ERI', 'biaya': 0},
                    {'nama': 'Pengisian Formulir & Antrian', 'deskripsi': 'Pengambilan nomor antrian', 'biaya': 0},
                    {'nama': 'Pendaftaran & Pemeriksaan Berkas', 'deskripsi': 'Verifikasi kelengkapan dokumen', 'biaya': 0},
                    {'nama': 'Pembayaran PNBP', 'deskripsi': 'Pembayaran di Bank BRI', 'biaya': 375000, 'is_payment': True},
                    {'nama': 'Verifikasi & Pencetakan BPKB', 'deskripsi': 'Proses cetak BPKB baru', 'biaya': 0},
                    {'nama': 'Pengesahan BPKB', 'deskripsi': 'Pengesahan oleh Pamin 2 & Kasi BPKB', 'biaya': 0},
                    {'nama': 'Penyerahan Dokumen', 'deskripsi': 'Penyerahan ke pemohon', 'biaya': 0},
                ]
            },
        ]
        
        for data in layanan_data:
            layanan, created = Layanan.objects.get_or_create(
                kode_layanan=data['kode'],
                defaults={
                    'nama_layanan': data['nama'],
                    'harga_jasa': data['harga'],
                    'estimasi_waktu': data['estimasi'],
                    'deskripsi': data.get('deskripsi', ''),
                    'has_custom_tahapan': data.get('has_tahapan', False)
                }
            )
            if created:
                self.stdout.write(f"  ✅ Layanan {data['nama']} dibuat")
                
                # Create Tahapan jika ada
                if data.get('tahapan'):
                    for idx, tahap in enumerate(data['tahapan'], 1):
                        TahapanLayanan.objects.create(
                            layanan=layanan,
                            urutan=idx,
                            nama_tahapan=tahap['nama'],
                            deskripsi=tahap.get('deskripsi', ''),
                            biaya_tahapan=tahap.get('biaya', 0),
                            is_payment_required=tahap.get('is_payment', False)
                        )
                    self.stdout.write(f"    📊 {len(data['tahapan'])} tahapan ditambahkan")
            else:
                self.stdout.write(f"  ⏭️  Layanan {data['nama']} sudah ada")
        
        # === 4. CREATE MASTER DOKUMEN ===
        self.stdout.write('\n📝 Membuat master dokumen...')
        
        dokumen_list = [
            ('KTP', 'Kartu Tanda Penduduk'),
            ('STNK', 'Surat Tanda Nomor Kendaraan'),
            ('BPKB', 'Buku Pemilik Kendaraan Bermotor'),
            ('Bukti Bayar Pajak', 'Bukti pembayaran pajak kendaraan'),
            ('Surat Kuasa', 'Surat kuasa bermeterai untuk yang diwakilkan'),
            ('Hasil Cek Fisik', 'Hasil pemeriksaan fisik kendaraan'),
        ]
        
        for nama, desk in dokumen_list:
            doc, created = MasterDokumen.objects.get_or_create(
                nama_dokumen=nama,
                defaults={'deskripsi': desk}
            )
            if created:
                self.stdout.write(f"  ✅ Dokumen {nama} dibuat")
        
        # === SUMMARY ===
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ SEEDING SELESAI!'))
        self.stdout.write('='*50)
        self.stdout.write('\n📋 AKUN LOGIN TESTING:')
        self.stdout.write('─'*50)
        self.stdout.write('👔 Manajer    : manajer@test.com / password123')
        self.stdout.write('📋 Staff Admin: admin@test.com / password123')
        self.stdout.write('💰 Keuangan   : keuangan@test.com / password123')
        self.stdout.write('🛵 Lapangan   : lapangan@test.com / password123')
        self.stdout.write('👤 Pelanggan  : pelanggan@test.com / password123')
        self.stdout.write('👤 Pelanggan 2: pelanggan2@test.com / password123')
        self.stdout.write('─'*50 + '\n')

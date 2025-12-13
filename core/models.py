from django.db import models
import os
import uuid

# --- FUNGSI PEMBANTU (RENAME FILE OTOMATIS) ---
def get_file_path(instance, filename):
    """
    Mengubah nama file asli menjadi UUID agar aman dan tidak bentrok.
    """
    ext = filename.split('.')[-1] # Ambil ekstensi file (jpg, pdf, png)
    filename = f"{uuid.uuid4()}.{ext}" # Buat nama baru acak
    return os.path.join('dokumen_upload/', filename)

# ==========================================
# 1. ENTITAS MASTER (DATA ACUAN)
# ==========================================

class Pelanggan(models.Model):
    kode_pelanggan = models.CharField(max_length=30, unique=True)
    nama = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    no_whatsapp = models.CharField(max_length=20, blank=True, null=True)
    alamat_lengkap = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.kode_pelanggan} - {self.nama}"

class Karyawan(models.Model):
    # --- DEFINISI PILIHAN ROLE (DROPDOWN) ---
    # Format: ('nilai_database', 'Label yang Tampil di Admin')
    # Nilai database (kiri) HARUS SAMA dengan yang kita pakai di views.py
    ROLE_CHOICES = [
        ('manajer', 'Manajer / Pemilik'),
        ('staff_admin', 'Staff Administrasi'),
        ('staff_keuangan', 'Staff Keuangan'),
        ('lapangan', 'Staff Lapangan'),
    ]

    kode_karyawan = models.CharField(max_length=30, unique=True)
    nama = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    no_whatsapp = models.CharField(max_length=20, blank=True, null=True)
    
    # --- UPDATE DI SINI ---
    # Tambahkan parameter choices=ROLE_CHOICES
    role = models.CharField(max_length=30, choices=ROLE_CHOICES) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Ini agar di tampilan admin muncul "Nama (Label Role)" yang rapi
        # Kita gunakan get_role_display() untuk mengambil labelnya
        return f"{self.nama} ({self.get_role_display()})"

class Layanan(models.Model):
    kode_layanan = models.CharField(max_length=30, unique=True)
    nama_layanan = models.CharField(max_length=100)
    harga_jasa = models.PositiveIntegerField(default=0)
    estimasi_waktu = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nama_layanan

class MasterDokumen(models.Model):
    nama_dokumen = models.CharField(max_length=100, unique=True)
    deskripsi = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nama_dokumen

# ==========================================
# 2. ENTITAS PENGHUBUNG (MANY-TO-MANY)
# ==========================================

class LayananDokumen(models.Model):
    layanan = models.ForeignKey(Layanan, on_delete=models.CASCADE, related_name='syarat_dokumen')
    master_dokumen = models.ForeignKey(MasterDokumen, on_delete=models.CASCADE)
    is_wajib = models.BooleanField(default=True)

    class Meta:
        unique_together = ('layanan', 'master_dokumen') 

    def __str__(self):
        return f"{self.layanan.nama_layanan} butuh {self.master_dokumen.nama_dokumen}"

# ==========================================
# 3. ENTITAS TRANSAKSI (DATA AKTIVITAS)
# ==========================================

class Permohonan(models.Model):
    kode_permohonan = models.CharField(max_length=30, unique=True)
    
    pelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE, related_name='permohonan_list')
    layanan = models.ForeignKey(Layanan, on_delete=models.RESTRICT) 
    karyawan = models.ForeignKey(Karyawan, on_delete=models.SET_NULL, null=True, blank=True, related_name='tugas_list')
    
    status_proses = models.CharField(max_length=30, default='Menunggu Verifikasi')
    biaya_resmi = models.PositiveIntegerField(default=0, blank=True, null=True)
    metode_pengiriman = models.CharField(max_length=30, blank=True, null=True)
    catatan_pelanggan = models.TextField(blank=True, null=True)
    catatan_penolakan = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.kode_permohonan

class Dokumen(models.Model):
    kode_dokumen = models.CharField(max_length=30, unique=True)
    permohonan = models.ForeignKey(Permohonan, on_delete=models.CASCADE, related_name='berkas_upload')
    master_dokumen = models.ForeignKey(MasterDokumen, on_delete=models.RESTRICT)
    
    # Menggunakan FileField dengan fungsi rename otomatis
    path_file = models.FileField(upload_to=get_file_path, max_length=255)
    status_file = models.CharField(max_length=30, default='Digital Diupload')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.kode_dokumen

    # --- PROPERTI PINTAR: CEK PDF ---
    # Pastikan indentasi (tab) sejajar dengan def __str__
    @property
    def is_pdf(self):
        if self.path_file and self.path_file.name:
            return self.path_file.name.lower().endswith('.pdf')
        return False

class Pembayaran(models.Model):
    nomor_invoice = models.CharField(max_length=30, unique=True)
    
    permohonan = models.OneToOneField(Permohonan, on_delete=models.CASCADE, related_name='tagihan')
    
    biaya_pengiriman = models.PositiveIntegerField(default=0, blank=True, null=True)
    total_biaya = models.PositiveIntegerField(default=0)
    metode_pembayaran = models.CharField(max_length=30, blank=True, null=True)
    status_pembayaran = models.CharField(max_length=30, default='pending')
    transaction_id_gateway = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nomor_invoice
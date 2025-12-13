from django.contrib import admin
from .models import (
    Pelanggan, Karyawan, Layanan, MasterDokumen, 
    LayananDokumen, Permohonan, Dokumen, Pembayaran
)

@admin.register(Pelanggan)
class PelangganAdmin(admin.ModelAdmin):
    list_display = ('kode_pelanggan', 'nama', 'email', 'no_whatsapp')
    search_fields = ('nama', 'kode_pelanggan')

@admin.register(Karyawan)
class KaryawanAdmin(admin.ModelAdmin):
    list_display = ('kode_karyawan', 'nama', 'role', 'email')
    list_filter = ('role',)

@admin.register(Layanan)
class LayananAdmin(admin.ModelAdmin):
    list_display = ('kode_layanan', 'nama_layanan', 'harga_jasa', 'estimasi_waktu')
    search_fields = ('nama_layanan',)

@admin.register(MasterDokumen)
class MasterDokumenAdmin(admin.ModelAdmin):
    list_display = ('nama_dokumen', 'deskripsi')

@admin.register(LayananDokumen)
class LayananDokumenAdmin(admin.ModelAdmin):
    list_display = ('layanan', 'master_dokumen', 'is_wajib')
    list_filter = ('layanan',)

@admin.register(Permohonan)
class PermohonanAdmin(admin.ModelAdmin):
    list_display = ('kode_permohonan', 'pelanggan', 'layanan', 'status_proses', 'created_at')
    list_filter = ('status_proses', 'layanan')
    search_fields = ('kode_permohonan', 'pelanggan__nama')

@admin.register(Dokumen)
class DokumenAdmin(admin.ModelAdmin):
    list_display = ('kode_dokumen', 'permohonan', 'master_dokumen', 'status_file')

@admin.register(Pembayaran)
class PembayaranAdmin(admin.ModelAdmin):
    list_display = ('nomor_invoice', 'permohonan', 'total_biaya', 'status_pembayaran')
    list_filter = ('status_pembayaran',)

    # Fungsi kecil untuk menampilkan jenis dokumen di list admin (opsional)
    def jenis_dokumen(self, obj):
        return obj.master_dokumen.nama_dokumen
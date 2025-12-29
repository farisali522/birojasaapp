from django.urls import path
from . import views

urlpatterns = [
    # --- AREA PUBLIK ---
    path('', views.landing_page, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API Firebase (Invisible)
    path('api/firebase-auth/', views.firebase_auth_api, name='firebase_auth'),

    # --- AREA PELANGGAN ---
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('ajukan/', views.pilih_layanan_view, name='pilih_layanan'),
    path('ajukan/<int:layanan_id>/', views.form_pengajuan_view, name='form_pengajuan'),
    path('tagihan/<int:permohonan_id>/', views.tagihan_view, name='tagihan'),

    # --- AREA STAFF ADMIN ---
    path('staff/dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
    path('staff/verifikasi/<int:permohonan_id>/', views.verifikasi_permohonan_view, name='verifikasi_permohonan'),
    path('staff/tugaskan/<int:permohonan_id>/', views.tugaskan_staff_view, name='tugaskan_staff'),
    path('staff/finalisasi/<int:permohonan_id>/', views.finalisasi_permohonan_view, name='finalisasi_permohonan'),

    # --- AREA STAFF LAPANGAN ---
    path('lapangan/dashboard/', views.lapangan_dashboard_view, name='lapangan_dashboard'),
    path('lapangan/update/<int:permohonan_id>/', views.update_status_lapangan_view, name='update_status_lapangan'),
    path('lapangan/detail/<int:permohonan_id>/', views.lapangan_detail_view, name='lapangan_detail'),


    path('keuangan/dashboard/', views.keuangan_dashboard_view, name='keuangan_dashboard'),
    path('keuangan/lunas/<int:pembayaran_id>/', views.konfirmasi_lunas_view, name='konfirmasi_lunas'),

    path('profil/edit/', views.edit_profil_view, name='edit_profil'),
    path('staff/input-walkin/', views.staff_input_walkin_view, name='staff_input_walkin'),
    path('staff/upload-arsip/<int:permohonan_id>/', views.staff_upload_arsip_view, name='staff_upload_arsip'),

    path('manajer/', views.manajer_dashboard_view),
    path('manajer/dashboard/', views.manajer_dashboard_view, name='manajer_dashboard'),
    path('manajer/laporan/', views.laporan_keuangan_view, name='laporan_keuangan'),
    path('manajer/cetak-laporan/', views.cetak_laporan_gabungan_view, name='cetak_laporan_gabungan'),  # NEW

    path('staff/tolak/<int:permohonan_id>/', views.tolak_permohonan_view, name='tolak_permohonan'),
    path('detail/<int:permohonan_id>/', views.detail_permohonan_view, name='detail_permohonan'),

    path('manajer/karyawan/', views.manajer_karyawan_list_view, name='manajer_karyawan_list'),
    path('manajer/karyawan/add/', views.manajer_karyawan_create_view, name='manajer_karyawan_add'),
    path('manajer/karyawan/edit/<int:karyawan_id>/', views.manajer_karyawan_edit_view, name='manajer_karyawan_edit'),
    path('manajer/karyawan/delete/<int:karyawan_id>/', views.manajer_karyawan_delete_view, name='manajer_karyawan_delete'),
    path('manajer/master/layanan/', views.master_layanan_list_view, name='master_layanan_list'),
    path('manajer/master/layanan/add/', views.master_layanan_form_view, name='master_layanan_add'),
    path('manajer/master/layanan/edit/<int:layanan_id>/', views.master_layanan_form_view, name='master_layanan_edit'),
    path('manajer/master/layanan/requirements/<int:layanan_id>/', views.master_layanan_requirements_view, name='master_layanan_requirements'),

    path('manajer/master/dokumen/', views.master_dokumen_list_view, name='master_dokumen_list'),
    path('manajer/master/dokumen/add/', views.master_dokumen_form_view, name='master_dokumen_add'),
    path('manajer/master/dokumen/edit/<int:doc_id>/', views.master_dokumen_form_view, name='master_dokumen_edit'),
    path('manajer/master/dokumen/delete/<int:doc_id>/', views.master_dokumen_list_view, name='master_dokumen_delete'), # Delete handled in list view POST

    path('revisi/<int:permohonan_id>/', views.revisi_pengajuan_view, name='revisi_pengajuan'),
]
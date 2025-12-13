# ==========================================
# Views Package - Modular Structure
# ==========================================
# This __init__.py exports all views from modular files
# for backward compatibility with urls.py

# Auth & Public Views
from .auth_views import (
    landing_page,
    login_view,
    firebase_auth_api,
    logout_view,
    get_role_redirect_url
)

# Pelanggan (Customer) Views
from .pelanggan_views import (
    dashboard_view,
    pilih_layanan_view,
    form_pengajuan_view,
    tagihan_view
)

# Staff Admin Views
from .staff_admin_views import (
    staff_dashboard_view,
    staff_input_walkin_view,
    staff_upload_arsip_view,
    verifikasi_permohonan_view,
    tugaskan_staff_view,
    finalisasi_permohonan_view,
    tolak_permohonan_view
)

# Staff Keuangan (Finance) Views
from .staff_keuangan_views import (
    keuangan_dashboard_view,
    konfirmasi_lunas_view
)

# Staff Lapangan (Field) Views
from .staff_lapangan_views import (
    lapangan_dashboard_view,
    update_status_lapangan_view,
    lapangan_detail_view
)

# Manajer (Manager) Views
from .manajer_views import (
    manajer_dashboard_view,
    laporan_keuangan_view,
    cetak_laporan_gabungan_view,  # NEW
    manajer_karyawan_list_view,
    manajer_karyawan_create_view,
    manajer_karyawan_edit_view,
    manajer_karyawan_delete_view,
    master_layanan_list_view,
    master_layanan_form_view,
    master_layanan_requirements_view,
    master_dokumen_list_view,
    master_dokumen_form_view
)

# Shared Views
from .shared_views import (
    edit_profil_view,
    detail_permohonan_view,
    revisi_pengajuan_view
)

# Export all for "from core.views import *"
__all__ = [
    # Auth
    'landing_page',
    'login_view',
    'firebase_auth_api',
    'logout_view',
    'get_role_redirect_url',
    # Pelanggan
    'dashboard_view',
    'pilih_layanan_view',
    'form_pengajuan_view',
    'tagihan_view',
    # Staff Admin
    'staff_dashboard_view',
    'staff_input_walkin_view',
    'staff_upload_arsip_view',
    'verifikasi_permohonan_view',
    'tugaskan_staff_view',
    'finalisasi_permohonan_view',
    'tolak_permohonan_view',
    # Staff Keuangan
    'keuangan_dashboard_view',
    'konfirmasi_lunas_view',
    # Staff Lapangan
    'lapangan_dashboard_view',
    'update_status_lapangan_view',
    'lapangan_detail_view',
    # Manajer
    'manajer_dashboard_view',
    'laporan_keuangan_view',
    'cetak_laporan_gabungan_view',  # NEW
    'manajer_karyawan_list_view',
    'manajer_karyawan_create_view',
    'manajer_karyawan_edit_view',
    'manajer_karyawan_delete_view',
    'master_layanan_list_view',
    'master_layanan_form_view',
    'master_layanan_requirements_view',
    'master_dokumen_list_view',
    'master_dokumen_form_view',
    # Shared
    'edit_profil_view',
    'detail_permohonan_view',
    'revisi_pengajuan_view',
]

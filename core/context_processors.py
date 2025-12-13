from .models import Pelanggan, Karyawan

def global_user_info(request):
    """
    Fungsi ini akan mencari Nama Asli user yang sedang login,
    baik dia Pelanggan maupun Karyawan.
    """
    user_info = {
        'nama_asli': None  # Default kosong
    }

    if request.user.is_authenticated:
        email_login = request.user.email
        
        # 1. Cek apakah dia Pelanggan?
        try:
            pelanggan = Pelanggan.objects.get(email=email_login)
            user_info['nama_asli'] = pelanggan.nama
        except Pelanggan.DoesNotExist:
            # 2. Jika bukan Pelanggan, Cek apakah dia Karyawan?
            try:
                karyawan = Karyawan.objects.get(email=email_login)
                user_info['nama_asli'] = karyawan.nama
            except Karyawan.DoesNotExist:
                # 3. Jika tidak ditemukan di keduanya, pakai username/email saja
                user_info['nama_asli'] = request.user.username

    return user_info
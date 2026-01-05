# BiroJasaApp - Sistem Manajemen Biro Jasa Digital

Aplikasi manajemen biro jasa modern berbasis Django yang dirancang untuk mengintegrasikan alur kerja antara pelanggan, admin, keuangan, dan staff lapangan dalam satu platform yang transparan dan efisien.

---

## 🚀 Fitur Utama

- **Dashboard Multi-Role**: Antarmuka yang disesuaikan untuk 5 peran berbeda.
- **Tracking Real-time**: Pelanggan dapat memantau status dokumen mereka secara langsung.
- **Monitoring Keamanan**: Manajer dapat memantau login staff beserta alamat IP mereka.
- **Input Walk-in**: Memudahkan staff mendaftarkan order pelanggan yang datang langsung secara manual.
- **Notifikasi Terintegrasi**: Update status otomatis di dashboard.

---

## 🛠️ Petunjuk Instalasi & Setup

### 1. Persiapan Lingkungan
Gunakan virtual environment agar library tidak bentrok dengan sistem global.
```bash
git clone https://github.com/farisali522/birojasaapp.git
cd birojasaapp
python -m venv venv

# Aktifkan (Linux/Mac):
source venv/bin/activate
# Aktifkan (Windows):
.\venv\Scripts\activate
```

### 2. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

**Keterangan Library Utama:**
- `Django`: Framework utama aplikasi (Backend).
- `django-jazzmin`: Digunakan untuk mempercantik tampilan Admin Panel (Manager View).
- `firebase-admin`: Library untuk integrasi backend dengan Firebase (SSO & Auth).
- `python-dotenv`: Untuk membaca variabel rahasia dari file `.env`.
- `mysqlclient`: Driver untuk menghubungkan Django ke database MySQL.
- `pillow`: Digunakan untuk pengelolaan file gambar (foto/scan dokumen).

### 3. Konfigurasi Environment (`.env`)
Salin file `.env.example` menjadi `.env` dan lengkapi datanya:
```bash
# Core Django
SECRET_KEY=kunci_rahasia_anda_disini
DEBUG=True

# Database MySQL
DB_NAME=nama_db
DB_USER=root
DB_PASSWORD=password_db
DB_HOST=localhost
DB_PORT=3306

# Konfigurasi Email (SMTP)
EMAIL_HOST_USER=email_anda@gmail.com
EMAIL_HOST_PASSWORD=app_password_gmail_anda

# Konfigurasi Firebase (SSO/Auth)
FIREBASE_KEY_PATH=firebase_key.json
FIREBASE_API_KEY=xxx
FIREBASE_AUTH_DOMAIN=xxx
FIREBASE_PROJECT_ID=xxx
... (lengkapi dari dashboard firebase)
```

---

## ⚙️ Panduan Konfigurasi Lanjutan

### A. Pengaturan Email (SMTP Gmail)
Agar aplikasi bisa mengirimkan notifikasi email:
1.  Gunakan akun Gmail dan aktifkan **2-Step Verification**.
2.  Buka [Google App Passwords](https://myaccount.google.com/apppasswords).
3.  Buat password baru untuk aplikasi "BiroJasaApp".
4.  Salin password 16 digit tersebut ke `.env` pada bagian `EMAIL_HOST_PASSWORD`.

### B. Pengaturan Firebase (SSO & Admin SDK)
Aplikasi menggunakan Firebase untuk sistem login (SSO):
1.  **Private Key (Backend)**:
    - Buka Firebase Console > Project Settings > Service Accounts.
    - Klik **Generate New Private Key**, download filenya.
    - Simpan di folder root proyek dengan nama `firebase_key.json`.
2.  **Frontend Config**:
    - Buka Project Settings > General > Your Apps.
    - Salin konfigurasi API Key, Auth Domain, dll, ke file `.env`.

---

## 👤 Panduan Penggunaan Berdasarkan Aktor

### 1. 💼 Manajer (Pemilik)
- **Dashboard**: Memantau statistik pendapatan dan jumlah permohonan.
- **Monitoring Login**: Cek Alamat IP staff yang login di tab khusus.
- **Akses Admin**: Melalui `/admin` untuk manajemen user dan database master (Jazzmin UI).

### 2. 📝 Staff Administrasi
- **Input Walk-in**: Menu untuk mendaftarkan pelanggan luring.
- **Verifikasi**: Mengecek dokumen yang diupload pelanggan digital.

### 3. 💳 Staff Keuangan
- **Keuangan**: Kelola invoice dan konfirmasi pembayaran (`status=paid`).

### 4. 🛵 Staff Lapangan
- **Progres**: Update status teknis permohonan yang sedang dikerjakan di instansi.

### 5. 🧑‍💻 Pelanggan
- **Order Online**: Pilih layanan dan upload berkas mandiri.
- **Tracking**: Pantau progres dokumen via dashboard pelanggan.

---

## 📚 Teknologi
- **Backend**: Django 4.x
- **Database**: MySQL
- **Identity**: Firebase Auth
- **UI Framework**: Bootstrap 5 + Jazzmin Admin
- **Deployment**: Localhost (Dev Mode)

---
*Dibuat dengan ❤️ untuk efisiensi operasional biro jasa.*

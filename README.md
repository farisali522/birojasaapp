# 🚀 BiroJasaApp - Digital Management System

Aplikasi manajemen biro jasa modern berbasis Django yang mengintegrasikan alur kerja antara **Manajer**, **Staff Administrasi**, **Staff Keuangan**, **Staff Lapangan**, dan **Pelanggan**.

---

## 📋 Daftar Isi
1. [Fitur Utama](#-fitur-utama)
2. [Panduan Instalasi & Setup](#-panduan-instalasi--setup)
3. [Konfigurasi Database (MySQL)](#-konfigurasi-database-mysql)
4. [Konfigurasi Environment (.env)](#-konfigurasi-environment-env)
5. [Konfigurasi SSO (Firebase)](#-konfigurasi-sso-firebase)
6. [Panduan Fitur Berdasarkan Peran](#-panduan-fitur-berdasarkan-peran)
7. [Teknologi](#-teknologi)

---

## 🛠️ Panduan Instalasi & Setup

### 1. Persiapan Environment
Buka terminal/command prompt di dalam folder proyek Anda.
- **Tip (VS Code)**: Tekan `Ctrl + ` ` (backtick) atau buka menu **Terminal > New Terminal**.

```bash
git clone https://github.com/farisali522/birojasaapp.git
cd birojasaapp
python -m venv venv

# Aktivasi
# Linux/Mac: source venv/bin/activate
# Windows: .\venv\Scripts\activate
```

### 2. Instalasi Library
```bash
pip install -r requirements.txt
```

---

## 🗄️ Konfigurasi Database (MySQL)

Sebelum menjalankan aplikasi, Anda harus membuat database di MySQL:

1.  Buka terminal MySQL atau **phpMyAdmin**.
2.  Jalankan perintah SQL berikut:
    ```sql
    CREATE DATABASE db_birojasa;
    ```
3.  Pastikan user MySQL Anda memiliki hak akses penuh ke database tersebut.

---

## ⚙️ Konfigurasi Environment (.env)

Buat file bernama `.env` di folder root proyek. Gunakan referensi di bawah ini untuk mengisinya:

```bash
# === CORE DJANGO ===
SECRET_KEY=isi_bebas_acak_panjang
DEBUG=True
ALLOWED_HOSTS=localhost, 127.0.0.1

# === DATABASE SETTINGS (MySQL) ===
DB_NAME=db_birojasa
DB_USER=root
DB_PASSWORD=isi_password_mysql_anda
DB_HOST=localhost
DB_PORT=3306

# === EMAIL SETTINGS (SMTP GMAIL) ===
# Digunakan untuk kirim notifikasi tagihan/invoice otomatis
EMAIL_HOST_USER=emailanda@gmail.com
EMAIL_HOST_PASSWORD=isi_16_digit_app_password_google

# === FIREBASE CONFIG (SSO/AUTH) ===
# Path ke file json private key yang didownload dari Firebase
FIREBASE_KEY_PATH=firebase_key.json

# Ambil data ini dari Firebase Console (Project Settings > General > Your Apps)
FIREBASE_API_KEY=xxx
FIREBASE_AUTH_DOMAIN=xxx
FIREBASE_PROJECT_ID=xxx
FIREBASE_STORAGE_BUCKET=xxx
FIREBASE_MESSAGING_SENDER_ID=xxx
FIREBASE_APP_ID=xxx
FIREBASE_MEASUREMENT_ID=xxx
```

---

## 🔥 Konfigurasi SSO (Firebase)

Agar sistem login (SSO) berfungsi, ikuti langkah ini:

### A. Mendapatkan Private Key (Backend)
1.  Buka [Firebase Console](https://console.firebase.google.com/).
2.  Pilih proyek Anda > **Project Settings** (icon gerigi).
3.  Pilih tab **Service Accounts**.
4.  Klik tombol **Generate New Private Key**.
5.  Download file `.json` tersebut, ubah namanya menjadi `firebase_key.json`.
6.  Pindahkan ke folder utama proyek Anda.

### B. Mendapatkan Config SDK (Frontend)
1.  Di menu **Project Settings**, pilih tab **General**.
2.  Pada bagian "Your apps", klik icon **Web (</>)**.
3.  Daftarkan aplikasi (beri nama bebas).
4.  Copy semua nilai (API Key, Project ID, dll) ke file `.env` yang Anda buat tadi.

---

## 👥 Panduan Fitur Berdasarkan Peran

### 👑 1. Manajer (Owner)
- **Monitoring**: Omzet, jumlah pelanggan, dan **IP Tracking** login staff.
- **Admin**: Akses penuh ke `/admin` (Jazzmin UI) untuk manajemen data master.

### 📝 2. Staff Administrasi
- **Input Walk-in**: Menu untuk input nasabah yang datang langsung.
- **Verifikasi**: Memeriksa berkas fisik dan digital pelanggan.

### 💳 3. Staff Keuangan
- **Invoice**: Verifikasi bukti transfer dan konfirmasi pembayaran (`Paid`).

### 🛵 4. Staff Lapangan
- **Track Progres**: Update status proses birokrasi di instansi lapangan.

### 🧑‍💻 5. Pelanggan
- **Online Order**: Pesan layanan dan upload berkas mandiri dari rumah.

---

## 🔄 Finalisasi Setup
Setelah semua konfigurasi (.env, database, firebase) selesai, jalankan:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

---
*Dibuat untuk efisiensi dan transparansi operasional biro jasa.*

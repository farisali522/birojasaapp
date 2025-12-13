# BiroJasaApp

Aplikasi manajemen biro jasa berbasis Django.

## Cara Install (Setup) di Laptop Baru

### 1. Clone Repository
```bash
git clone https://github.com/farisali522/birojasaapp.git
cd birojasaapp
```

### 2. Buat Virtual Environment
Agar library tidak bentrok, gunakan virtual environment.
```bash
python -m venv venv
```
**Aktifkan (Windows):**
```bash
.\venv\Scripts\activate
```
**Aktifkan (Linux/Mac):**
```bash
source venv/bin/activate
```

### 3. Install Library
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Kunci Rahasia (.env)
Aplikasi ini butuh password database & API Key yang tidak di-upload demi keamanan.
1.  Copy file `.env.example` dan ubah namanya menjadi `.env`.
2.  Buka file `.env` baru tersebut, lalu isi dengan data asli (Password Database, Email Host, Firebase Config) yang Anda miliki.

### 5. Konfigurasi Firebase Service Account
1.  Copy file `firebase_key.example.json` dan ubah namanya menjadi `firebase_key.json`.
2.  Isi file tersebut dengan JSON Private Key asli yang didapat dari Firebase Console (Project Settings -> Service Accounts -> Generate New Private Key).

### 6. Jalankan Aplikasi
```bash
python manage.py migrate
python manage.py runserver
```
Buka browser di `http://127.0.0.1:8000`

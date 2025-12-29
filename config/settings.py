from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = True

ALLOWED_HOSTS = ['192.168.1.16','*']


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # --- TAMBAHAN KITA ---
                'core.context_processors.global_user_info', 
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Jakarta'

USE_I18N = True

# GANTI DARI True MENJADI False (Agar database menyimpan waktu lokal, bukan UTC)
# Ini mempermudah pemula agar tidak bingung konversi waktu
USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
# 2. LOKASI FISIK UNTUK FILES STATIS (WAJIB DITAMBAH)
# Folder di root proyek tempat Django akan menaruh CSS/JS tema Jazzmin
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 

# 3. Direktori File Statis (Opsional, tapi bantu)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core/static'), # Jika Anda punya static file sendiri
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
# Folder fisik di komputer untuk menyimpan file
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'BiroJasaApp <noreply@birojasaapp.com>'
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Custom Setting for Firebase
FIREBASE_KEY_PATH = os.getenv('FIREBASE_KEY_PATH')

# JAZZMIN SETTINGS (UNTUK TAMPILAN ADMIN PANEL)
JAZZMIN_SETTINGS = {
    # Judul untuk Login Screen
    "site_title": "BiroJasaApp - Manager",

    # Judul di Navbar Atas
    "site_header": "BiroJasaApp",

    # Logo di Sidebar
    "site_brand": "BIROJASA MANAGER",

    # Icon Admin Panel
    "site_icon": "admin/img/logo.png", # Gunakan path logo Anda

    # Tema visual (Pilihan: darkly, cerulean, lux, material, superhero, cosmo)
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # Opsi: Pilih Dark Mode atau Light Mode
    "show_sidebar": True,
    "navigation_expanded": True,
    "theme": "darkly",
}
# Firebase Frontend Config
FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN')
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET')
FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID')
FIREBASE_MEASUREMENT_ID = os.getenv('FIREBASE_MEASUREMENT_ID')

from pathlib import Path
import os
import sys
from dotenv import load_dotenv # Importar librería para leer .env

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Funciones Helper para convertir tipos de datos del .env ---
def env(key, default=None):
    return os.getenv(key, default)

def env_int(key, default=None):
    val = os.getenv(key)
    return int(val) if val is not None and val != "" else default

def env_bool(key, default=False):
    val = os.getenv(key)
    if val is None or val == "":
        return default
    return val.lower() in ("1", "true", "yes", "on")

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
#  SEGURIDAD
# =========================================================
SECRET_KEY = env('SECRET_KEY')

# OJO: En producción, DEBUG debe ser False en el .env
DEBUG = env_bool('DEBUG', False)

# Convertimos la string de hosts separada por comas en una lista
ALLOWED_HOSTS = env('ALLOWED_HOSTS', '*').split(',')

# Duración del enlace de restablecimiento de contraseña (14 horas)
PASSWORD_RESET_TIMEOUT = 50400

# =========================================================
#  CONFIGURACIÓN GETNET (Pagos)
# =========================================================
GETNET_LOGIN = env('GETNET_LOGIN')
GETNET_TRANKEY = env('GETNET_TRANKEY')

# Endpoints base (leídos del env o por defecto test)
GETNET_BASE_URL = env('GETNET_ENV_URL', "https://checkout.test.getnet.cl")

# Construcción de URLs de la API Getnet
GETNET_API_CREATE_REQUEST = f"{GETNET_BASE_URL}/api/session/createRequest"
GETNET_API_QUERY_REQUEST = f"{GETNET_BASE_URL}/api/session/queryRequest"
GETNET_WEBCHECKOUT_URL = f"{GETNET_BASE_URL}/webcheckout/"

# URL Base de TU proyecto (Localhost por defecto, editable en .env)
BASE_URL = env('APP_BASE_URL', 'http://127.0.0.1:8000')

# URLs de Retorno y Notificación (Callback)
GETNET_RETURN_URL = f"{BASE_URL}/studentView/pago-finalizado/"
GETNET_NOTIFICATION_URL = f"{BASE_URL}/studentView/confirmacion-getnet/"


# =========================================================
#  APLICACIONES E INSTALACIÓN
# =========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps propias
    'inicioSesion',
    'studentView',
    'adminView',
    'profesorView',
    'core',
    'finanzas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'inicioSesion.middleware.LoginRequiredMiddleware',    
]

ROOT_URLCONF = 'intranet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates" / "adminView"], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'intranet.wsgi.application'


# =========================================================
#  BASE DE DATOS
# =========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', 'localhost'),
        'PORT': env('DB_PORT', '5432'),
    }
}


# =========================================================
#  VALIDACIÓN DE PASSWORD
# =========================================================
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# =========================================================
#  INTERNACIONALIZACIÓN
# =========================================================
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# =========================================================
#  ARCHIVOS ESTÁTICOS
# =========================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'




# =========================================================
#  AUTENTICACIÓN Y MODELOS
# =========================================================
LOGIN_URL = "inicioSesion:login"
LOGIN_REDIRECT_URL = '/inicioSesion/registro/'
AUTH_USER_MODEL = "core.User"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =========================================================
#  CONFIGURACIÓN DE CORREO (SMTP)
# =========================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("EMAIL_HOST_USER")
EMAIL_TIMEOUT = 15
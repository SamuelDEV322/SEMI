import os
import json
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "semi-local-demonstration-only")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")
CSRF_TRUSTED_ORIGINS = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
# Deployment profile is selected only on server startup, never by a browser.
SEMI_MODE = os.getenv("SEMI_MODE", "operational")
if SEMI_MODE not in {"operational", "demonstration"}:
    raise ImproperlyConfigured("SEMI_MODE must be operational or demonstration")
SEMI_LIDAR_SOURCE = os.getenv(
    "SEMI_LIDAR_SOURCE", "real" if SEMI_MODE == "operational" else "mock"
)
if SEMI_LIDAR_SOURCE not in {"real", "mock", "replay"}:
    raise ImproperlyConfigured("Invalid SEMI_LIDAR_SOURCE")
if SEMI_MODE == "operational" and SEMI_LIDAR_SOURCE != "real":
    raise ImproperlyConfigured(
        "Operational mode requires a real LiDAR source; no mock fallback"
    )
if SEMI_MODE == "demonstration" and SEMI_LIDAR_SOURCE == "real":
    raise ImproperlyConfigured("Demonstration cannot consume a physical LiDAR source")
SEMI_DEV_TOOLS = (
    DEBUG and SEMI_MODE == "demonstration" and os.getenv("SEMI_DEV_TOOLS", "0") == "1"
)
# Diagnostic ingestion and the optional supervised bench are configured independently.
SEMI_DEVICE_INTEGRATION = os.getenv("SEMI_DEVICE_INTEGRATION", "disabled")
if SEMI_DEVICE_INTEGRATION not in {"disabled", "diagnostic"}:
    raise ImproperlyConfigured(
        "Only disabled or diagnostic device integration is supported"
    )
try:
    SEMI_DEVICE_TOKENS = json.loads(os.getenv("SEMI_DEVICE_TOKENS", "{}"))
    if not isinstance(SEMI_DEVICE_TOKENS, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, str)
        or not 32 <= len(value) <= 512
        for key, value in SEMI_DEVICE_TOKENS.items()
    ):
        raise ValueError()
except (ValueError, TypeError):
    raise ImproperlyConfigured(
        "Invalid device credential configuration; contents withheld"
    ) from None
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "apps.agriculture",
    "apps.telemetry",
    "apps.lidar",
    "apps.devices",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.security.DemoCsrfMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.getenv("SEMI_DATABASE", "demo.sqlite3"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "America/Bogota"
USE_TZ = True
LANGUAGE_CODE = "es-co"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.errors.exception_handler",
}
CSRF_FAILURE_VIEW = "config.errors.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True

# Optional supervised bench profile. Secrets are supplied outside the repository.
SEMI_BENCH_DEVICE = os.getenv("SEMI_BENCH_DEVICE", "")
SEMI_OPERATOR_KEY = os.getenv("SEMI_OPERATOR_KEY", "")
SEMI_MOTOR_KEY = os.getenv("SEMI_MOTOR_KEY", "")
SEMI_BENCH_STORE = str(BASE_DIR / os.getenv("SEMI_BENCH_STORE", "bench-runtime.sqlite3"))

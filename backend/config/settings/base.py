from pathlib import Path
from config.private import PROJECT_ROOT, secret

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = secret("DJANGO_SECRET_KEY", "django_secret_key.txt")
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1"]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "allauth", "allauth.account", "allauth.headless", "cuentas", "huerto",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "cuentas.Usuario"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 15}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = False
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = False
ACCOUNT_ADAPTER = "cuentas.adapters.ClosedRegistrationAdapter"
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_SERVE_SPECIFICATION = False
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"django.request": {"handlers": ["null"], "propagate": False}},
}


# Stage 2: one browser origin; no app-token, social, PIN or passkey endpoints.
CSRF_FAILURE_VIEW = "cuentas.api.csrf_failure"
EMAIL_BACKEND = "cuentas.email.AuthorizedSMTPBackend"
DEFAULT_FROM_EMAIL = "El Chilito <no-reply@localhost>"
EMAIL_SUBJECT_PREFIX = "[El Chilito] "
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[El Chilito] "
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT = {"length": 6, "numeric": True, "dashed": False}
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = 5
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_CHANGE = False
ACCOUNT_RATE_LIMITS = {
    "login": "30/m/ip",
    "login_failed": "10/m/ip,5/300s/key",
    "confirm_email": "1/60s/key",
    "reset_password": "10/m/ip,1/60s/key",
    "reset_password_from_key": "20/m/ip",
    "change_password": "5/m/user",
}
PASSWORD_RESET_TIMEOUT = 1800
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 32768
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.db.DatabaseCache",
    "LOCATION": "cuentas_cuotas_acceso",
    "TIMEOUT": 3600,
    "OPTIONS": {"MAX_ENTRIES": 10000},
}}
# Do not write paths, headers, bodies or SMTP exceptions to request logs.
LOGGING["loggers"]["django.server"] = {"handlers": ["null"], "propagate": False}
LOGGING["loggers"]["django.security.csrf"] = {"handlers": ["null"], "propagate": False}

# Disabled outside the explicitly selected local presentation profile.
ELCHILITO_LOCAL_PRESENTATION = False
ELCHILITO_LOCAL_REGISTRATION_ENABLED = False
ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = False

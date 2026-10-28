from .settings import *
PROFILE='testing'
ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
ELCHILITO_REGISTRATION_ENABLED=True
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

"""Común a todos los perfiles, con valores seguros. Sin configuración privada ni secretos."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR=Path(__file__).resolve().parents[2]
PROJECT_ROOT=BASE_DIR.parent
PROFILE=os.environ['CHILITO_ENV']
SECRET_KEY=os.environ.get('CHILITO_DJANGO_KEY','')
if len(SECRET_KEY)<32:raise ImproperlyConfigured('Suministra CHILITO_DJANGO_KEY externo de al menos 32 caracteres')
CHILITO_SUPPORT_KEY=os.environ.get('CHILITO_SUPPORT_KEY','')
if len(CHILITO_SUPPORT_KEY.encode())<32:raise ImproperlyConfigured('Suministra CHILITO_SUPPORT_KEY independiente de al menos 32 bytes')
CHILITO_VINCULACION_SECRETO=os.environ.get('CHILITO_VINCULACION_SECRETO','')
if len(CHILITO_VINCULACION_SECRETO.encode())<32:raise ImproperlyConfigured('Suministra CHILITO_VINCULACION_SECRETO de al menos 32 bytes')
DEBUG=False
# localhost y no 127.0.0.1: WebAuthn no acepta una IP como identificador del sitio.
ORIGIN=os.environ.get('CHILITO_ORIGIN','http://localhost:8780')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions',
    'django.contrib.messages','django.contrib.staticfiles','allauth','allauth.account','allauth.headless',
    'allauth.mfa','cuentas','huerto','datos','web.apps.WebConfig','privacidad']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware',
    'allauth.account.middleware.AccountMiddleware','web.middleware.SecurityHeaders','web.sesion.SesionAcotada','web.middleware.ActorDeBase']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,
 'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
AUTH_USER_MODEL='cuentas.Usuario'
AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend','allauth.account.auth_backends.AuthenticationBackend']
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LANGUAGE_CODE='es-mx';TIME_ZONE='America/Mexico_City';USE_TZ=True;USE_I18N=True
STATIC_URL='/static/'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.environ.get('CHILITO_DB_NAME','chilito_integracion_sinteticos'),
 'USER':os.environ.get('CHILITO_DB_USER','chilito_pkg_runtime'),'PASSWORD':os.environ.get('CHILITO_DB_PASSWORD',''),
 'HOST':os.environ.get('CHILITO_DB_HOST','127.0.0.1'),'PORT':os.environ.get('CHILITO_DB_PORT','5432'),
 'OPTIONS':{'sslmode':os.environ.get('CHILITO_DB_SSLMODE','verify-full')},
 'ATOMIC_REQUESTS':True,
 'TEST':{'NAME':'test_chilito_integracion_sinteticos'}}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':15}},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
ACCOUNT_ADAPTER='cuentas.adapters.ClosedRegistrationAdapter'
ACCOUNT_USER_MODEL_USERNAME_FIELD=None
ACCOUNT_LOGIN_METHODS={'email'}
ACCOUNT_SIGNUP_FIELDS=['email*','password1*','password2*']
ACCOUNT_EMAIL_VERIFICATION='mandatory'
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED=True
# Segundo paso tras la contraseña. Sin ENABLED no existe el acceso solo por código.
ACCOUNT_LOGIN_BY_CODE_ENABLED=False
ACCOUNT_LOGIN_BY_CODE_REQUIRED={'password'}
ACCOUNT_LOGIN_BY_CODE_TIMEOUT=300
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS=3
ACCOUNT_LOGIN_BY_CODE_FORMAT={'length':6,'numeric':True,'dashed':False}
MFA_ADAPTER='cuentas.adapters.AdaptadorMFA'
MFA_SUPPORTED_TYPES=['totp','recovery_codes','webauthn']
MFA_TOTP_ISSUER='El Chilito'
MFA_RECOVERY_CODE_COUNT=10
MFA_RECOVERY_CODES_SHOW_ONCE=True
MFA_PASSKEY_LOGIN_ENABLED=False
MFA_PASSKEY_SIGNUP_ENABLED=False
MFA_TRUST_ENABLED=False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN=False
CHILITO_MFA_KEY=os.environ.get('CHILITO_MFA_KEY','')
# Se muestra a quien perdió todos sus métodos. Sin valor, la pantalla no inventa un contacto.
CHILITO_CONTACTO_SOPORTE=os.environ.get('CHILITO_CONTACTO_SOPORTE','')
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED=False
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT=600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS=3
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT={'length':6,'numeric':True,'dashed':False}
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND=5
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_CHANGE=False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION=True
ACCOUNT_LOGIN_ON_PASSWORD_RESET=False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE=False
ACCOUNT_RATE_LIMITS={'signup':'10/m/ip','login':'30/m/ip','login_failed':'10/m/ip,5/300s/key',
 'confirm_email':'1/60s/key','reset_password':'10/m/ip,1/60s/key','reset_password_from_key':'20/m/ip','change_password':'5/m/user',
 'request_login_code':'20/m/ip,3/m/key','reauthenticate':'10/m/user',
 'privacidad_cookies':'20/m/ip','estadistica_seccion':'60/m/ip','contacto_producto':'5/h/ip','vincular_dispositivo':'20/m/ip,5/m/key'}
PASSWORD_RESET_TIMEOUT=600
SESSION_ENGINE='django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE=28800
CHILITO_SESION_ABSOLUTA=28800
CHILITO_INACTIVIDAD_USUARIO=1800
CHILITO_INACTIVIDAD_ADMIN=900
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_COOKIE_SAMESITE='Lax'
CSRF_FAILURE_VIEW='cuentas.api.csrf_failure'
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='same-origin'
X_FRAME_OPTIONS='DENY'
HEADLESS_ONLY=True
HEADLESS_CLIENTS=('browser',)
HEADLESS_SERVE_SPECIFICATION=False
HEADLESS_FRONTEND_URLS={'account_confirm_email':ORIGIN+'/index.html#verificar?key={key}',
 'account_reset_password':ORIGIN+'/index.html#recuperar',
 'account_reset_password_from_key':ORIGIN+'/index.html#restablecer?key={key}',
 'account_signup':ORIGIN+'/index.html#registro'}
ELCHILITO_SMTP_ENABLED=os.environ.get('CHILITO_SMTP_ENABLED','0')=='1'
ELCHILITO_SMTP_RECIPIENT_MODE=os.environ.get('CHILITO_SMTP_RECIPIENT_MODE','restricted')
ELCHILITO_SMTP_ALLOWED_RECIPIENTS=[s.strip() for s in os.environ.get('CHILITO_SMTP_ALLOWED_RECIPIENTS','').split(',') if s.strip()]
EMAIL_BACKEND='cuentas.email.AuthorizedSMTPBackend' if ELCHILITO_SMTP_ENABLED else 'cuentas.email.ProtectedFileEmailBackend'
EMAIL_FILE_PATH=os.environ.get('CHILITO_MAILBOX','/tmp/el-chilito-integracion-correo-pruebas')
EMAIL_HOST=os.environ.get('CHILITO_SMTP_HOST','')
EMAIL_PORT=int(os.environ.get('CHILITO_SMTP_PORT','587'))
EMAIL_HOST_USER=os.environ.get('CHILITO_SMTP_USER','')
EMAIL_HOST_PASSWORD=os.environ.get('CHILITO_SMTP_PASSWORD','')
EMAIL_USE_TLS=True;EMAIL_USE_SSL=False;EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL=os.environ.get('CHILITO_FROM_EMAIL','El Chilito <no-reply@example.test>')
ACCOUNT_EMAIL_SUBJECT_PREFIX='[El Chilito] '
DATA_UPLOAD_MAX_MEMORY_SIZE=32768
CACHES={'default':{'BACKEND':'django.core.cache.backends.db.DatabaseCache','LOCATION':'cuentas_cuotas_acceso','TIMEOUT':3600,'OPTIONS':{'MAX_ENTRIES':10000}}}
LOGGING={'version':1,'disable_existing_loggers':False,
 'formatters':{'seguro':{'()':'config.registro.FormatoSeguro','format':'%(asctime)s %(levelname)s %(name)s %(message)s'}},
 'handlers':{'consola':{'class':'logging.StreamHandler','formatter':'seguro'},'null':{'class':'logging.NullHandler'}},
 # django.server repetiría cada URL; el resto deja rastro de errores sin cuerpos ni credenciales.
 'loggers':{'django.server':{'handlers':['null'],'propagate':False},
  **{n:{'handlers':['consola'],'level':'WARNING','propagate':False} for n in ['django.request','django.security','cuentas','datos','web','privacidad']}}}

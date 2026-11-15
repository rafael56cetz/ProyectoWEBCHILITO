from django.urls import path,re_path
from allauth.headless.account import views as auth
from allauth.headless.mfa import views as mfa
from cuentas.api import bootstrap,profile,registration,browser_endpoint,totp_qr,verification_context
from privacidad import api as privacidad
from web import api
from web.static_views import frontend,resource
PREFIX='_allauth/browser/v1/'
urlpatterns=[path('',frontend),path('index.html',frontend),
 path('api/acceso/configuracion',bootstrap),path('api/cuenta',profile),path('api/acceso/verificacion',verification_context),
 path(PREFIX+'auth/session',browser_endpoint(auth.SessionView,['GET','DELETE'])),
 path(PREFIX+'auth/login',browser_endpoint(auth.LoginView,['POST'])),path(PREFIX+'auth/signup',registration),
 path(PREFIX+'auth/email/verify',browser_endpoint(auth.VerifyEmailView,['POST'])),
 path(PREFIX+'auth/email/verify/resend',browser_endpoint(auth.ResendEmailVerificationCodeView,['POST'])),
 path(PREFIX+'auth/password/request',browser_endpoint(auth.RequestPasswordResetView,['POST'],reset_mail=True)),
 path(PREFIX+'auth/password/reset',browser_endpoint(auth.ResetPasswordView,['GET','POST'])),
 path(PREFIX+'account/password/change',browser_endpoint(auth.ChangePasswordView,['POST'],verified_only=True)),
 # Segundo paso del acceso. auth/code/request no se publica: el código nunca sustituye a la contraseña.
 path(PREFIX+'auth/code/confirm',browser_endpoint(auth.ConfirmLoginCodeView,['POST'])),
 path(PREFIX+'auth/2fa/authenticate',browser_endpoint(mfa.AuthenticateView,['POST'])),
 path(PREFIX+'auth/webauthn/authenticate',browser_endpoint(mfa.AuthenticateWebAuthnView,['GET','POST'])),
 path(PREFIX+'auth/reauthenticate',browser_endpoint(auth.ReauthenticateView,['POST'],verified_only=True)),
 path(PREFIX+'auth/2fa/reauthenticate',browser_endpoint(mfa.ReauthenticateView,['POST'],verified_only=True)),
 path(PREFIX+'auth/webauthn/reauthenticate',browser_endpoint(mfa.ReauthenticateWebAuthnView,['GET','POST'],verified_only=True)),
 path(PREFIX+'account/authenticators',browser_endpoint(mfa.AuthenticatorsView,['GET'],verified_only=True)),
 path(PREFIX+'account/authenticators/totp',browser_endpoint(mfa.ManageTOTPView,['GET','POST','DELETE'],verified_only=True)),
 path(PREFIX+'account/authenticators/recovery-codes',browser_endpoint(mfa.ManageRecoveryCodesView,['GET','POST'],verified_only=True)),
 path(PREFIX+'account/authenticators/webauthn',browser_endpoint(mfa.ManageWebAuthnView,['GET','POST','PUT','DELETE'],verified_only=True)),
 path('api/cuenta/seguridad/totp-qr',totp_qr),
 path('api/contacto',api.contact),
 path('api/guias',api.care_guides),path('api/admin/guias',api.admin_guides),
 path('api/admin/guias/<uuid:guide_id>/editar',api.admin_guide_edit),
 path('api/admin/guias/<uuid:guide_id>/publicar',api.admin_guide_publish),
 path('api/admin/guias/<uuid:guide_id>/retirar',api.admin_guide_withdraw),
 path('api/huertos/actual',api.garden),path('api/huertos/actual/avisos',api.notices),
 path('api/huertos/actual/avisos/<str:notice_id>',api.notice),path('api/huertos/actual/avisos/<str:notice_id>/lectura',api.read_notice),
 path('api/huertos/actual/mantenimiento',api.maintenance),path('api/huertos/actual/solicitudes',api.requests),
 path('api/soporte',api.support),path('api/soporte/<uuid:case_id>/revocar',api.revoke),
 path('api/admin/flota',api.fleet),
 path('api/admin/soporte',api.reports),path('api/admin/soporte/<uuid:case_id>/solicitar-token',api.ask_token),path('api/admin/soporte/<uuid:case_id>/resolver',api.resolve_case),path('api/vinculacion',api.bind_garden),path('api/admin/vinculacion',api.binding_panel),path('api/admin/vinculacion/emitir',api.binding_issue),path('api/admin/vinculacion/<uuid:code_id>/revocar',api.binding_revoke),path('api/admin/consultas',api.inquiries),path('api/admin/consultas/<uuid:inquiry_id>/estado',api.inquiry_state),
 path('api/admin/soporte/<uuid:case_id>/abrir',api.open_session),
 path('api/admin/sesiones/<uuid:session_id>/accion',api.technical),path('api/admin/sesiones/<uuid:session_id>/cerrar',api.close_session),
 path('api/admin/mantenimientos',api.admin_maintenance),path('api/admin/mantenimientos/<uuid:record_id>',api.admin_maintenance_detail),
 path('api/admin/mantenimientos/<uuid:record_id>/corregir',api.admin_maintenance_correct),
 path('api/admin/mantenimientos/<uuid:record_id>/anular',api.admin_maintenance_void),
 path('api/cuenta/perfil',privacidad.profile),path('api/cuenta/bienvenida',privacidad.welcome),
 path('api/privacidad/mis-datos',privacidad.my_data),path('api/privacidad/documentos/<str:kind>',privacidad.document),
 path('api/privacidad/cookies',privacidad.cookies),path('api/estadisticas/seccion',privacidad.section),
 re_path(r'^(?P<path>(?:vistas|modelos|controladores)/.+|favicon\.svg)$',resource)]
handler404='web.static_views.not_found'
handler500='web.static_views.server_error'

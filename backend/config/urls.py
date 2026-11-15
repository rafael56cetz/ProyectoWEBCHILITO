from django.urls import path,re_path
from allauth.headless.account import views as auth
from allauth.headless.mfa import views as mfa
from cuentas.api import bootstrap,profile,registration,browser_endpoint,totp_qr,verification_context
from datos import api as datos
from huerto import api as huerto
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
 path('api/legales/aceptar',datos.accept_legal),path('api/dispositivos/vincular',datos.link_device),
 path('api/comandos/<uuid:comando_id>',datos.command_state),
 path('api/huertos',huerto.gardens),path('api/huertos/<int:huerto_id>',huerto.garden),
 path('api/huertos/<int:huerto_id>/renombrar',huerto.garden_rename),path('api/huertos/<int:huerto_id>/archivar',huerto.garden_archive),
 path('api/huertos/<int:huerto_id>/ia',huerto.garden_summaries),path('api/huertos/<int:huerto_id>/codigo',huerto.link_code),
 path('api/huertos/<int:huerto_id>/vinculacion',huerto.link_state),path('api/huertos/<int:huerto_id>/desvincular',huerto.unlink),
 path('api/huertos/<int:huerto_id>/plantas/<int:numero>',huerto.plant),
 path('api/huertos/<int:huerto_id>/comandos',huerto.commands),path('api/huertos/<int:huerto_id>/cuidados',huerto.cares),
 path('api/huertos/<int:huerto_id>/telemetria',huerto.telemetry),path('api/huertos/<int:huerto_id>/bitacora',huerto.log),
 path('api/huertos/<int:huerto_id>/soporte',datos.support),
 path('api/soporte/<uuid:caso_id>/revocar',datos.support_revoke),path('api/soporte/<uuid:caso_id>/cancelar',datos.support_cancel),
 path('api/autodiagnosticos/<uuid:diagnostico_id>',datos.diagnostic),
 path('api/avisos',datos.notices),path('api/avisos/leer-todos',datos.notices_read_all),path('api/avisos/contador',datos.notice_count),
 path('api/avisos/<int:aviso_id>',datos.notice),path('api/avisos/<int:aviso_id>/leido',datos.notice_read),
 path('api/avisos/<int:aviso_id>/resuelto',datos.notice_resolved),
 path('api/cuenta/aceptaciones',privacidad.acceptances),path('api/cuenta/eliminar',privacidad.delete_account),
 path('api/cuenta/eliminar/cancelar',privacidad.cancel_deletion),
 # Rediseñadas en fases posteriores: responden 503 en-actualizacion.
 path('api/admin/vinculacion',api.en_actualizacion),
 path('api/admin/vinculacion/emitir',api.en_actualizacion),path('api/admin/vinculacion/<uuid:code_id>/revocar',api.en_actualizacion),
 path('api/admin/flota',api.en_actualizacion),
 path('api/admin/soporte',api.en_actualizacion),path('api/admin/soporte/<uuid:case_id>/solicitar-token',api.en_actualizacion),
 path('api/admin/soporte/<uuid:case_id>/resolver',api.en_actualizacion),path('api/admin/soporte/<uuid:case_id>/abrir',api.en_actualizacion),
 path('api/admin/sesiones/<uuid:session_id>/accion',api.en_actualizacion),path('api/admin/sesiones/<uuid:session_id>/cerrar',api.en_actualizacion),
 path('api/admin/mantenimientos',api.en_actualizacion),path('api/admin/mantenimientos/<uuid:record_id>',api.en_actualizacion),
 path('api/admin/mantenimientos/<uuid:record_id>/corregir',api.en_actualizacion),path('api/admin/mantenimientos/<uuid:record_id>/anular',api.en_actualizacion),
 path('api/admin/consultas',api.inquiries),path('api/admin/consultas/<uuid:inquiry_id>/estado',api.inquiry_state),
 path('api/cuenta/perfil',privacidad.profile),path('api/cuenta/bienvenida',privacidad.welcome),
 path('api/privacidad/mis-datos',privacidad.my_data),path('api/privacidad/documentos/<str:kind>',privacidad.document),
 path('api/privacidad/cookies',privacidad.cookies),path('api/estadisticas/seccion',privacidad.section),
 re_path(r'^(?P<path>(?:vistas|modelos|controladores)/.+|favicon\.svg)$',resource)]
handler404='web.static_views.not_found'
handler500='web.static_views.server_error'

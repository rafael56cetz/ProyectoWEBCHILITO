from django.urls import path,re_path
from allauth.headless.account import views as auth
from cuentas.api import bootstrap,profile,registration,browser_endpoint,verification_context
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
 path('api/huertos/actual',api.garden),path('api/huertos/actual/avisos',api.notices),
 path('api/huertos/actual/avisos/<str:notice_id>',api.notice),path('api/huertos/actual/avisos/<str:notice_id>/lectura',api.read_notice),
 path('api/huertos/actual/mantenimiento',api.maintenance),path('api/huertos/actual/solicitudes',api.requests),
 path('api/soporte',api.support),path('api/soporte/<uuid:case_id>/revocar',api.revoke),
 path('api/admin/flota',api.fleet),path('api/admin/gobernanza',api.governance),path('api/admin/cambios',api.changes),
 path('api/admin/soporte',api.reports),path('api/admin/soporte/<uuid:case_id>/solicitar-token',api.ask_token),
 path('api/admin/soporte/<uuid:case_id>/abrir',api.open_session),
 path('api/admin/sesiones/<uuid:session_id>/accion',api.technical),path('api/admin/sesiones/<uuid:session_id>/cerrar',api.close_session),
 path('api/admin/validaciones',api.validate),path('api/admin/despliegues',api.deploy),
 path('api/admin/conocimiento',api.knowledge),path('api/admin/reinicio',api.restart),
 re_path(r'^(?P<path>(?:vista|modelo|controlador)/.+|vista-trabajo\.js|favicon\.svg)$',resource)]
handler404='web.static_views.not_found'
handler500='web.static_views.server_error'

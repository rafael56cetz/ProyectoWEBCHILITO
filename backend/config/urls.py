from django.urls import path, re_path
from allauth.headless.account import views as auth
from config.views import frontend, resource
from huerto import api as garden
from cuentas.api import bootstrap, profile, registration, browser_endpoint, verification_context

PREFIX = "_allauth/browser/v1/"
urlpatterns = [
    path("", frontend), path("index.html", frontend),
    path("api/acceso/configuracion", bootstrap),
    path("api/cuenta", profile),
    path("api/huertos/actual", garden.garden),
    path("api/huertos/actual/avisos", garden.notices),
    path("api/huertos/actual/avisos/<str:notice_id>", garden.notice),
    path("api/huertos/actual/avisos/<str:notice_id>/lectura", garden.read_notice),
    path("api/acceso/verificacion", verification_context),
    path(PREFIX + "auth/session", browser_endpoint(auth.SessionView, ["GET", "DELETE"])),
    path(PREFIX + "auth/login", browser_endpoint(auth.LoginView, ["POST"])),
    path(PREFIX + "auth/signup", registration),
    path(PREFIX + "auth/email/verify", browser_endpoint(auth.VerifyEmailView, ["POST"])),
    path(PREFIX + "auth/email/verify/resend", browser_endpoint(auth.ResendEmailVerificationCodeView, ["POST"])),
    path(PREFIX + "auth/password/request", browser_endpoint(auth.RequestPasswordResetView, ["POST"], reset_mail=True)),
    path(PREFIX + "auth/password/reset", browser_endpoint(auth.ResetPasswordView, ["GET", "POST"])),
    path(PREFIX + "account/password/change", browser_endpoint(auth.ChangePasswordView, ["POST"], verified_only=True)),
    re_path(r"^(?P<path>(?:vista|modelo|controlador)/.+|favicon\.svg)$", resource),
]

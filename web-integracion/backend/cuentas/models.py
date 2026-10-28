from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.db import models
from django.db.models.functions import Lower

class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email.strip())

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Se requiere correo electronico.")
        user = self.model(email=self.normalize_email(email.strip()).lower(), **extra_fields)
        user.full_clean(exclude=["password"])
        if password is not None:
            validate_password(password, user)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("El superusuario requiere ambos permisos.")
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="usuario_email_ci_unico"),
        ]


class CuotaAcceso(models.Model):
    """Storage schema for Django DatabaseCache/allauth rate limits, not a second auth system."""
    cache_key = models.CharField(max_length=255, primary_key=True)
    value = models.TextField()
    expires = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "cuentas_cuotas_acceso"


class ConfirmacionRegistroLocal(models.Model):
    """Technical checkbox confirmation; never an approved legal consent."""
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="confirmacion_registro_local")
    confirmado_en = models.DateTimeField(auto_now_add=True)
    casilla_marcada = models.BooleanField(default=True, editable=False)
    documentos_pendientes = models.BooleanField(default=True, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(casilla_marcada=True, documentos_pendientes=True),
                                   name="registro_local_solo_confirmacion_tecnica"),
        ]

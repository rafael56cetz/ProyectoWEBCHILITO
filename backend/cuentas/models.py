from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.db import models
from web.models import AHORA

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
    alias = models.CharField(max_length=64, blank=True, default="", db_default="")
    bienvenida_atendida_en = models.DateTimeField(null=True, blank=True)
    anonimizacion_solicitada_en = models.DateTimeField(null=True, blank=True)
    anonimizada_en = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
        if isinstance(self.alias, str):
            self.alias = self.alias.strip()

    @property
    def nombre_presentacion(self):
        """Texto para la bienvenida, sin consultar datos ni completar el perfil."""
        return self.alias.strip() or self.first_name.strip() or "Bienvenido"

    class Meta:
        permissions = [
            ("ver_flota", "Ver telemetría de flota"),
            ("atender_soporte", "Atender soporte remoto (consola remota)"),
            ("gestionar_mantenimientos", "Corregir y anular cuidados registrados"),
            ("atender_consultas", "Atender consultas del producto (Consíguelo)"),
            ("gestionar_dispositivos", "Gestionar inventario y desvinculación de equipos"),
            ("gestionar_ventas", "Registrar y gestionar ventas"),
            ("gestionar_guias", "Crear, editar, publicar y retirar guías de cuidado"),
            ("gestionar_legales", "Subir y publicar versiones de textos legales"),
            ("ver_consentimientos", "Ver la bitácora de consentimientos"),
            ("gestionar_administradores", "Super administrador: dar y quitar capacidades"),
        ]


class CapacidadHistorial(models.Model):
    """Lo llena un trigger de la base; la aplicación solo lo lee."""
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    capacidad = models.CharField(max_length=64)
    accion = models.CharField(max_length=10)
    realizada_por = models.ForeignKey(Usuario, null=True, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    motivo = models.CharField(max_length=300, db_default="")
    realizada_en = models.DateTimeField(db_default=AHORA)

    class Meta:
        db_table = "capacidad_historial"
        default_permissions = ()

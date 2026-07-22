from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROLE_SUPERADMIN = 'superadmin'
    ROLE_ADMIN_LIGA = 'adminliga'
    ROLE_ENTRENADOR = 'entrenador'

    ROLE_CHOICES = [
        (ROLE_SUPERADMIN, 'Administrador General'),
        (ROLE_ADMIN_LIGA, 'Administrador de Liga'),
        (ROLE_ENTRENADOR, 'Entrenador'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ENTRENADOR,
        help_text='Rol principal dentro del sistema deportivo.',
    )
    phone = models.CharField('Teléfono', max_length=30, blank=True)
    organization = models.CharField('Organización', max_length=128, blank=True)
    limite_ligas = models.PositiveIntegerField(
        'Límite de ligas',
        default=1,
        help_text='Cuántas ligas puede crear este Administrador de Liga.',
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def es_super_admin(self):
        return self.role == self.ROLE_SUPERADMIN or self.is_superuser

    def es_admin_liga(self):
        return self.role == self.ROLE_ADMIN_LIGA

    def es_entrenador(self):
        return self.role == self.ROLE_ENTRENADOR

    def save(self, *args, **kwargs):
        if not self.is_superuser:
            self.is_staff = self.role == self.ROLE_SUPERADMIN
        super().save(*args, **kwargs)

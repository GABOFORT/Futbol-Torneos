from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models


class UsuarioManager(UserManager):
    def entrenadores(self, para=None):
        """Los entrenadores que se pueden elegir y administrar.

        Excluye siempre a los superusuarios: una cuenta puede tener cargado
        role='entrenador' y ser superadmin a la vez, y en ese caso no debe
        figurar en las listas ni en los desplegables que ve un admin de liga.

        Con `para` se acota a quien puede verlos:
          - superadmin        -> todos
          - admin de liga     -> solo los que dio de alta el mismo
        Sin `para` devuelve todos, para usos internos que no dependen de quien mira.
        """
        base = self.filter(role=Usuario.ROLE_ENTRENADOR, is_superuser=False)
        if para is None or para.es_super_admin():
            return base
        return base.filter(creado_por=para)


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
    phone = models.CharField(
        'Teléfono',
        max_length=10,
        blank=True,
        validators=[RegexValidator(
            r'^\d{10}$',
            'El teléfono debe tener exactamente 10 dígitos, sin letras ni signos.',
        )],
    )
    organization = models.CharField('Organización', max_length=128, blank=True)
    limite_ligas = models.PositiveIntegerField(
        'Límite de ligas',
        default=1,
        help_text='Cuántas ligas puede crear este Administrador de Liga.',
    )
    limite_torneos = models.PositiveIntegerField(
        'Límite de torneos',
        default=1,
        help_text='Cuántos torneos relámpago puede tener en curso a la vez. '
                  'Los que ya terminaron no ocupan lugar.',
    )

    creado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_creados',
        verbose_name='Dado de alta por',
        help_text='Qué administrador creó esta cuenta. Define quién puede verla y editarla.',
    )

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def es_super_admin(self):
        return self.role == self.ROLE_SUPERADMIN or self.is_superuser

    @property
    def nombre_visible(self):
        return self.get_full_name() or self.username

    @property
    def iniciales(self):
        nombre = (self.first_name or '').strip()
        apellido = (self.last_name or '').strip()
        if nombre or apellido:
            return f'{nombre[:1]}{apellido[:1]}'.upper()
        return self.username[:2].upper()

    @property
    def equipos_del_usuario(self):
        """Los equipos que dirige. Solo un entrenador tiene."""
        return sorted(self.equipos.all(), key=lambda e: e.nombre)

    @property
    def ligas_del_usuario(self):
        """Las ligas a las que esta vinculado.

        Se llega de forma distinta segun el rol: el admin de liga las
        administra directamente, y el entrenador llega a ellas a traves de los
        equipos que dirige.
        """
        if self.es_super_admin():
            return []
        if self.role == self.ROLE_ADMIN_LIGA:
            return sorted(self.ligas_administradas.all(), key=lambda l: l.nombre)
        vistas, ligas = set(), []
        for equipo in self.equipos.all():
            if equipo.liga_id not in vistas:
                vistas.add(equipo.liga_id)
                ligas.append(equipo.liga)
        return sorted(ligas, key=lambda l: l.nombre)

    @property
    def rol_visible(self):
        """El rol tal como se muestra en pantalla.

        is_superuser manda sobre el campo role: hay cuentas marcadas como
        superusuario que tienen cargado 'entrenador', y mostrar ese seria
        enganoso porque en la practica pueden hacer todo.
        """
        if self.es_super_admin():
            return dict(self.ROLE_CHOICES)[self.ROLE_SUPERADMIN]
        return self.get_role_display()

    def es_admin_liga(self):
        return self.role == self.ROLE_ADMIN_LIGA

    def es_entrenador(self):
        return self.role == self.ROLE_ENTRENADOR

    def save(self, *args, **kwargs):
        """Mantiene sincronizados el rol de negocio y los flags de Django.

        El rol manda: un Administrador General **es** superusuario. Antes se
        podia crear uno con `is_superuser=False` y quedaba a medias — la interfaz
        lo trataba como administrador general, pero los decoradores de permisos
        miraban el flag y lo dejaban afuera de ligas, categorias y partidos.

        Va en el modelo y no en el formulario para que valga por todos los
        caminos: el alta desde la pantalla, el admin de Django y el shell.

        No se toca a quien tiene el flag activo con otro rol cargado: hay cuentas
        marcadas como superusuario con role='entrenador' y bajarles el flag les
        sacaria acceso que hoy usan.
        """
        if self.role == self.ROLE_SUPERADMIN:
            self.is_superuser = True
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test


def _role_test(*roles):
    """Deja pasar a cualquier Administrador General y a los roles que se pidan.

    Se pregunta por `es_super_admin()` y no por `is_superuser`: el rol de negocio
    tiene que alcanzar por si solo. Mirando el flag, un usuario con
    role='superadmin' e is_superuser=False quedaba bloqueado en ligas, categorias
    y partidos —`admin_liga_required` solo pasa ('adminliga',)— aunque toda la
    interfaz lo mostrara como administrador general.
    """
    def test(user):
        return user.is_authenticated and (user.es_super_admin() or user.role in roles)
    return test


def role_required(*roles):
    """Decorator factory: allows superuser plus any of the given business roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        @user_passes_test(_role_test(*roles))
        def wrapped(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def superadmin_required(view_func):
    from .models import Usuario
    return role_required(Usuario.ROLE_SUPERADMIN)(view_func)


def admin_liga_required(view_func):
    from .models import Usuario
    return role_required(Usuario.ROLE_ADMIN_LIGA)(view_func)


def entrenador_required(view_func):
    from .models import Usuario
    return role_required(Usuario.ROLE_ENTRENADOR)(view_func)


def ligas_visibles(user):
    """Las ligas que este usuario debe ver en las pantallas publicas.

    Es **lo publico mas lo propio**: las ligas activas, que son la vitrina del
    sistema y las ve cualquiera, mas las que uno administra aunque las tenga
    desactivadas —el admin no deja de ver su liga por esconderla del publico—.

    No confundirla con `ligas_administradas`, que es sobre que se puede
    ESCRIBIR. Esta responde que se puede MIRAR, y son dos preguntas distintas:
    el tablero, el alta de equipos y la carga de resultados se acotan con la
    otra.

    Antes devolvia `ligas_administradas(user)` para el admin de liga, con el
    razonamiento de que cada liga es un negocio aparte. Pero eso solo vale para
    la gestion: aplicado a la vitrina dejaba al admin viendo MENOS que un
    visitante sin cuenta. En la practica, entrar a Inicio -> Torneos en juego,
    abrir una liga ajena y pulsar un equipo daba 404 —`equipo_perfil` filtra por
    esta funcion— cuando cerrando sesion ese mismo enlace funcionaba. La portada
    ofrece las seis ligas activas a todo el mundo, asi que el sistema invitaba a
    un recorrido que despues cortaba.
    """
    from apps.torneos.models import Liga

    publicas = Liga.objects.filter(activa=True, torneo__isnull=True)

    if user.is_authenticated and (user.es_super_admin() or user.role == user.ROLE_ADMIN_LIGA):
        return (publicas | ligas_administradas(user)).distinct()
    return publicas


def ligas_administradas(user):
    """Las ligas que este usuario administra. Los torneos relámpago quedan fuera.

    Un torneo se apoya en una Liga, pero vive en su propio apartado: si entrara
    por aca aparecería en el listado de ligas, contaría contra la cuota de
    `limite_ligas` y ofrecería sus categorias en los filtros de todo el sistema.
    Se piden con `torneos_administrados()`.
    """
    from apps.torneos.models import Liga

    if user.es_super_admin():
        return Liga.objects.filter(torneo__isnull=True)
    if user.role == user.ROLE_ADMIN_LIGA:
        return user.ligas_administradas.filter(torneo__isnull=True)
    return Liga.objects.none()


def torneos_administrados(user):
    """Los torneos relámpago que este usuario puede administrar.

    Se pregunta primero por `is_authenticated`: el listado y la ficha de un
    torneo son publicos, y un `AnonymousUser` no tiene `es_super_admin()`. Sin
    esta guarda, un visitante sin cuenta reventaba las dos pantallas.
    """
    from apps.torneos.models import Torneo

    if not user.is_authenticated:
        return Torneo.objects.none()
    if user.es_super_admin():
        return Torneo.objects.all()
    if user.role == user.ROLE_ADMIN_LIGA:
        return Torneo.objects.filter(liga__administradores=user)
    return Torneo.objects.none()


def torneos_visibles(user):
    """Los torneos que se pueden mirar: los de las ligas activas, mas los propios."""
    from apps.torneos.models import Torneo

    publicos = Torneo.objects.filter(liga__activa=True)
    if user.is_authenticated and (user.es_super_admin() or user.role == user.ROLE_ADMIN_LIGA):
        return (publicos | torneos_administrados(user)).distinct()
    return publicos


def ligas_y_torneos_visibles(user):
    """Todo lo que este usuario puede MIRAR, ligas y torneos juntos.

    Las funciones de arriba parten el mundo en dos porque cada apartado lista lo
    suyo. Pero las pantallas que trabajan sobre UN objeto concreto —la ficha de
    un partido, el perfil de un equipo— no listan nada: solo tienen que decidir
    si quien pide puede verlo. Ahi el corte por apartado no sirve, y sin esto un
    partido de torneo daba 404.
    """
    from apps.torneos.models import Liga

    de_torneos = Liga.objects.filter(torneo__in=torneos_visibles(user))
    return Liga.objects.filter(
        pk__in=set(ligas_visibles(user).values_list('pk', flat=True))
        | set(de_torneos.values_list('pk', flat=True)))


def ligas_y_torneos_administrados(user):
    """Todo lo que este usuario puede ADMINISTRAR, ligas y torneos juntos.

    Lo piden las pantallas que cambian un partido concreto: programar la fecha,
    cargar el resultado, dar de alta una cancha.
    """
    from apps.torneos.models import Liga

    if not user.is_authenticated:
        return Liga.objects.none()
    de_torneos = Liga.objects.filter(torneo__in=torneos_administrados(user))
    return Liga.objects.filter(
        pk__in=set(ligas_administradas(user).values_list('pk', flat=True))
        | set(de_torneos.values_list('pk', flat=True)))


def cascada_equipos(user, parametros):
    """Resuelve la seleccion Liga -> Categoria -> Equipo acotando cada nivel.

    Si un nivel no pertenece al que lo contiene se descarta: asi cambiar de liga
    limpia sola la categoria vieja, y nadie llega a datos de otra liga pasando
    ids a mano en la URL.

    Devuelve (seleccion, disponibles) para armar los filtros y las consultas.
    """
    from apps.equipos.models import Equipo
    from apps.torneos.models import Categoria

    ligas = ligas_visibles(user).order_by('nombre')
    categorias = Categoria.objects.filter(liga__in=ligas).order_by('liga__nombre', 'nombre')
    equipos = Equipo.objects.filter(liga__in=ligas).order_by('nombre')

    def elegido(nombre, disponibles):
        valor = parametros.get(nombre, '')
        if valor.isdigit() and disponibles.filter(pk=int(valor)).exists():
            return int(valor)
        return None

    liga = elegido('liga', ligas)
    if liga:
        categorias = categorias.filter(liga_id=liga)
        equipos = equipos.filter(liga_id=liga)

    categoria = elegido('categoria', categorias)
    if categoria:
        equipos = equipos.filter(categoria_id=categoria)

    equipo = elegido('equipo', equipos)

    return (
        {'liga': liga, 'categoria': categoria, 'equipo': equipo},
        {'ligas': ligas, 'categorias': categorias, 'equipos': equipos},
    )

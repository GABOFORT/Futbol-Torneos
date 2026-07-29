from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test


def _role_test(*roles):
    def test(user):
        return user.is_authenticated and (user.is_superuser or user.role in roles)
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
    """Las ligas que este usuario debe ver en los listados generales.

    Un admin de liga ve solo las suyas: cada liga es un negocio aparte y no
    tiene por que ver los equipos ni las tablas de las demas. El superadmin ve
    todas, y el publico sin cuenta ve las activas, porque esas pantallas son la
    vitrina del sistema.
    """
    from apps.torneos.models import Liga

    if user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA):
        return ligas_administradas(user)
    return Liga.objects.filter(activa=True)


def ligas_administradas(user):
    """Queryset of Liga this user may manage: all for superuser, own for admin liga, none otherwise."""
    from apps.torneos.models import Liga

    if user.is_superuser or user.role == user.ROLE_SUPERADMIN:
        return Liga.objects.all()
    if user.role == user.ROLE_ADMIN_LIGA:
        return user.ligas_administradas.all()
    return Liga.objects.none()

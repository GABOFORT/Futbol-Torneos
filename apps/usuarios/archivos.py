"""Borrado de las imagenes que dejan de usarse.

Django solo actualiza la base cuando se elimina un registro o se reemplaza una
imagen: el archivo viejo queda en el disco para siempre. Estas senales lo borran,
pero solo despues de confirmar que ningun otro registro lo este usando.
"""
import logging

from django.db.models import FileField
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _campos_de_archivo(modelo):
    return [c for c in modelo._meta.get_fields() if isinstance(c, FileField)]


def _lo_usa_alguien_mas(instancia, campo, nombre):
    """Si otro registro apunta al mismo archivo.

    Puede pasar si dos equipos se subieron la misma imagen y Django reuso el
    nombre, o si alguien copio el valor a mano. Borrar sin mirar dejaria al otro
    con la imagen rota.
    """
    otros = type(instancia)._default_manager.filter(**{campo.name: nombre})
    if instancia.pk:
        otros = otros.exclude(pk=instancia.pk)
    return otros.exists()


def _borrar(archivo):
    """Saca el archivo del disco, sin dejar que un fallo rompa la operacion.

    En Windows es habitual que el archivo siga tomado por el proceso y el
    borrado falle. Si eso pasa, el registro igual se tiene que borrar o
    guardar: quedaria un archivo suelto, que es mucho menos grave que dejar al
    usuario sin poder eliminar un equipo.
    """
    if not archivo:
        return
    try:
        # save=False: no hay que volver a guardar el registro, solo sacar el
        # archivo del disco.
        archivo.delete(save=False)
    except OSError as error:
        logger.warning('No se pudo borrar %s: %s', archivo.name, error)


def conectar(modelo):
    """Deja el modelo limpiando sus archivos al borrarse o al reemplazarlos."""
    campos = _campos_de_archivo(modelo)
    if not campos:
        return

    @receiver(post_delete, sender=modelo, weak=False)
    def al_borrar(sender, instance, **kwargs):
        for campo in campos:
            archivo = getattr(instance, campo.name, None)
            if archivo and not _lo_usa_alguien_mas(instance, campo, archivo.name):
                _borrar(archivo)

    @receiver(pre_save, sender=modelo, weak=False)
    def al_reemplazar(sender, instance, **kwargs):
        if not instance.pk:
            return  # es nuevo, no hay nada anterior que borrar
        anterior = sender._default_manager.filter(pk=instance.pk).first()
        if not anterior:
            return
        for campo in campos:
            viejo = getattr(anterior, campo.name, None)
            nuevo = getattr(instance, campo.name, None)
            # Solo si de verdad cambio: guardar el registro sin tocar la imagen
            # no tiene que borrar nada.
            if viejo and viejo.name != (nuevo.name if nuevo else None):
                if not _lo_usa_alguien_mas(instance, campo, viejo.name):
                    _borrar(viejo)

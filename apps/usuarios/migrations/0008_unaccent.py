from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Activa la extension unaccent de PostgreSQL.

    Sin ella, buscar 'Garduno' no encuentra a 'Garduño' ni 'Lopez' a 'López':
    Postgres ignora mayusculas pero no acentos. Queda como migracion para que
    al montar el proyecto en otro servidor no haya que acordarse de activarla.

    Necesita permisos para CREATE EXTENSION. Si el usuario de la base no los
    tiene, hay que correr una vez, como superusuario de PostgreSQL:
        CREATE EXTENSION IF NOT EXISTS unaccent;
    """

    dependencies = [
        ('usuarios', '0007_usuario_creado_por'),
    ]

    operations = [
        UnaccentExtension(),
    ]


import apps.usuarios.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_alter_usuario_phone'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='usuario',
            managers=[
                ('objects', apps.usuarios.models.UsuarioManager()),
            ],
        ),
    ]


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_alter_usuario_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='limite_ligas',
            field=models.PositiveIntegerField(default=1, help_text='Cuántas ligas puede crear este Administrador de Liga.', verbose_name='Límite de ligas'),
        ),
    ]

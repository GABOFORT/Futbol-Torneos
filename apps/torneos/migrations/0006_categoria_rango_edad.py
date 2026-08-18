from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0005_remove_categoria_equipos_por_jornada_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='categoria',
            old_name='fecha_inicio',
            new_name='fecha_nacimiento_desde',
        ),
        migrations.RenameField(
            model_name='categoria',
            old_name='fecha_final',
            new_name='fecha_nacimiento_hasta',
        ),
        migrations.AlterField(
            model_name='categoria',
            name='fecha_nacimiento_desde',
            field=models.DateField(blank=True, help_text='Fecha de nacimiento del jugador de mayor edad que puede entrar.', null=True, verbose_name='Nacidos desde'),
        ),
        migrations.AlterField(
            model_name='categoria',
            name='fecha_nacimiento_hasta',
            field=models.DateField(blank=True, help_text='Fecha de nacimiento del jugador de menor edad que puede entrar.', null=True, verbose_name='Nacidos hasta'),
        ),
    ]

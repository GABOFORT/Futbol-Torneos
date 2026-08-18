from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0005_jugador_dorsal_unico_por_equipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='jugador',
            name='sexo',
            field=models.CharField(choices=[('masculino', 'Masculino'), ('femenino', 'Femenino')], default='masculino', help_text='Define el límite de edad: las mujeres entran con un año más que la categoría.', max_length=10, verbose_name='Sexo'),
        ),
    ]

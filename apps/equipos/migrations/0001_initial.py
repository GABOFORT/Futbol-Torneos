
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Equipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=140, verbose_name='Nombre del equipo')),
                ('fecha_creacion', models.DateField(auto_now_add=True, verbose_name='Fecha de registro')),
                ('estado', models.CharField(choices=[('borrador', 'Borrador'), ('pendiente', 'Pendiente de aprobación'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')], default='borrador', max_length=20, verbose_name='Estado')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
            ],
            options={
                'verbose_name': 'Equipo',
                'verbose_name_plural': 'Equipos',
            },
        ),
    ]


import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0008_liga_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sede',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre de la cancha')),
                ('direccion', models.CharField(blank=True, max_length=255, verbose_name='Dirección')),
                ('latitud', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Latitud')),
                ('longitud', models.DecimalField(decimal_places=6, max_digits=9, verbose_name='Longitud')),
                ('liga', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sedes', to='torneos.liga')),
            ],
            options={
                'verbose_name': 'Sede',
                'verbose_name_plural': 'Sedes',
                'ordering': ['nombre'],
                'unique_together': {('liga', 'nombre')},
            },
        ),
    ]

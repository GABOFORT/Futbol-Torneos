
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0009_sede'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='cerrada',
            field=models.BooleanField(default=False, verbose_name='Categoría concluida'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='fecha_cierre',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Concluida el'),
        ),
        migrations.AddField(
            model_name='liga',
            name='cerrada',
            field=models.BooleanField(default=False, verbose_name='Liga concluida'),
        ),
        migrations.AddField(
            model_name='liga',
            name='fecha_cierre',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Concluida el'),
        ),
        migrations.CreateModel(
            name='Palmares',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('liga_nombre', models.CharField(max_length=150, verbose_name='Liga')),
                ('categoria_nombre', models.CharField(max_length=120, verbose_name='Categoría')),
                ('fecha_cierre', models.DateTimeField(auto_now_add=True, verbose_name='Concluida el')),
                ('campeon', models.CharField(blank=True, max_length=140, verbose_name='Campeón')),
                ('subcampeon', models.CharField(blank=True, max_length=140, verbose_name='Subcampeón')),
                ('tercero', models.CharField(blank=True, max_length=140, verbose_name='Tercer lugar')),
                ('goleadores', models.CharField(blank=True, max_length=400, verbose_name='Bota de oro')),
                ('goles_del_goleador', models.PositiveIntegerField(default=0, verbose_name='Goles')),
                ('asistidores', models.CharField(blank=True, max_length=400, verbose_name='Trofeo de asistencias')),
                ('asistencias_del_asistidor', models.PositiveIntegerField(default=0, verbose_name='Asistencias')),
                ('vallas', models.CharField(blank=True, max_length=400, verbose_name='Guante de oro')),
                ('goles_recibidos', models.PositiveIntegerField(default=0, verbose_name='Goles recibidos')),
                ('tabla_final', models.JSONField(blank=True, default=list, verbose_name='Tabla final')),
                ('categoria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='palmares', to='torneos.categoria')),
            ],
            options={
                'verbose_name': 'Palmarés',
                'verbose_name_plural': 'Palmarés',
                'ordering': ['-fecha_cierre'],
            },
        ),
    ]

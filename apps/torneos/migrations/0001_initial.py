
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, verbose_name='Categoría')),
                ('cupo_equipos', models.PositiveIntegerField(default=8, verbose_name='Cupo de equipos')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
            },
        ),
        migrations.CreateModel(
            name='Liga',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre de la liga')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_inicio', models.DateField(blank=True, null=True, verbose_name='Fecha de inicio')),
                ('fecha_final', models.DateField(blank=True, null=True, verbose_name='Fecha de finalización')),
                ('activa', models.BooleanField(default=True, verbose_name='Liga activa')),
            ],
            options={
                'verbose_name': 'Liga',
                'verbose_name_plural': 'Ligas',
            },
        ),
        migrations.CreateModel(
            name='Torneo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre del torneo')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_inicio', models.DateField(blank=True, null=True, verbose_name='Fecha de inicio')),
                ('fecha_final', models.DateField(blank=True, null=True, verbose_name='Fecha de finalización')),
                ('activo', models.BooleanField(default=True, verbose_name='Torneo activo')),
            ],
            options={
                'verbose_name': 'Torneo',
                'verbose_name_plural': 'Torneos',
            },
        ),
    ]

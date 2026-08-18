
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0016_alter_categoria_peso_minimo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Torneo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(help_text='Se juega entero en esta fecha.', verbose_name='Día del torneo')),
                ('equipos', models.PositiveSmallIntegerField(choices=[(8, '8 equipos · cuartos, semifinal y final'), (16, '16 equipos · octavos, cuartos, semifinal y final')], default=8, verbose_name='Equipos que participan')),
                ('creado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='torneos_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('liga', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='torneo', to='torneos.liga')),
            ],
            options={
                'verbose_name': 'Torneo',
                'verbose_name_plural': 'Torneos',
                'ordering': ['-fecha'],
            },
        ),
    ]

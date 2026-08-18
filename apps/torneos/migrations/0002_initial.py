
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipos', '0003_initial'),
        ('torneos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='liga',
            name='administradores',
            field=models.ManyToManyField(blank=True, limit_choices_to={'role': 'adminliga'}, related_name='ligas_administradas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='categoria',
            name='liga',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias', to='torneos.liga'),
        ),
        migrations.AddField(
            model_name='torneo',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='torneos', to='torneos.categoria'),
        ),
        migrations.AddField(
            model_name='torneo',
            name='equipos',
            field=models.ManyToManyField(blank=True, related_name='torneos', to='equipos.equipo'),
        ),
        migrations.AddField(
            model_name='torneo',
            name='liga',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='torneos', to='torneos.liga'),
        ),
        migrations.AlterUniqueTogether(
            name='categoria',
            unique_together={('liga', 'nombre')},
        ),
    ]

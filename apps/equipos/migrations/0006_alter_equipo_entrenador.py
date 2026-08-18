
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0005_equipo_escudo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipo',
            name='entrenador',
            field=models.ForeignKey(limit_choices_to={'is_superuser': False, 'role': 'entrenador'}, on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to=settings.AUTH_USER_MODEL),
        ),
    ]

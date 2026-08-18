
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0004_remove_equipo_estado_equipo_formacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='escudo',
            field=models.ImageField(blank=True, help_text='Opcional. Si lo dejas vacío se muestra un escudo neutro.', null=True, upload_to='escudos/', verbose_name='Escudo del equipo'),
        ),
    ]

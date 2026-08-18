
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0007_remove_categoria_fecha_nacimiento_desde_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='liga',
            name='logo',
            field=models.ImageField(blank=True, help_text='Opcional. Si lo dejas vacío se muestran las iniciales de la liga.', null=True, upload_to='logos-ligas/', verbose_name='Logo de la liga'),
        ),
    ]

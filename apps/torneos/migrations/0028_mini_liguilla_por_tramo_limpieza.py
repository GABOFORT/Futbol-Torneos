from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0027_mini_liguilla_por_tramo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='categoria',
            name='mini_liguilla',
        ),
        migrations.RenameField(
            model_name='categoria',
            old_name='mini_liguilla_equipos',
            new_name='mini_liguilla',
        ),
        migrations.AlterField(
            model_name='categoria',
            name='mini_liguilla',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'Sin mini-liguilla'),
                    (4, 'Puestos 9 a 12 · necesita 12 equipos o más'),
                    (8, 'Puestos 9 a 16 · necesita 16 equipos o más'),
                ],
                default=0,
                help_text='Los equipos que siguen a los 8 de la liguilla juegan su propio cuadro.',
                verbose_name='Mini-liguilla de consolación',
            ),
        ),
    ]

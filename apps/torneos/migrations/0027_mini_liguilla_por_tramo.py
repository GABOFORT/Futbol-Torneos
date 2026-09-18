from django.db import migrations, models

SIN_MINI_LIGUILLA = 0
MINI_LIGUILLA_DE_CUATRO = 4


def a_tramo(apps, schema_editor):
    Categoria = apps.get_model('torneos', 'Categoria')
    Categoria.objects.filter(mini_liguilla=True).update(
        mini_liguilla_equipos=MINI_LIGUILLA_DE_CUATRO)


def a_casilla(apps, schema_editor):
    Categoria = apps.get_model('torneos', 'Categoria')
    Categoria.objects.exclude(mini_liguilla_equipos=SIN_MINI_LIGUILLA).update(
        mini_liguilla=True)


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0026_redes_sociales_liga'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='mini_liguilla_equipos',
            field=models.PositiveSmallIntegerField(default=SIN_MINI_LIGUILLA),
        ),
        migrations.RunPython(a_tramo, a_casilla),
    ]

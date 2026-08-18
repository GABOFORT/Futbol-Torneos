
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0015_alter_categoria_edad_minima_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoria',
            name='peso_minimo',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(50, '50 kg'), (51, '51 kg'), (52, '52 kg'), (53, '53 kg'), (54, '54 kg'), (55, '55 kg'), (56, '56 kg'), (57, '57 kg'), (58, '58 kg'), (59, '59 kg'), (60, '60 kg'), (61, '61 kg'), (62, '62 kg'), (63, '63 kg'), (64, '64 kg'), (65, '65 kg'), (66, '66 kg'), (67, '67 kg'), (68, '68 kg'), (69, '69 kg'), (70, '70 kg'), (71, '71 kg'), (72, '72 kg'), (73, '73 kg'), (74, '74 kg'), (75, '75 kg'), (76, '76 kg'), (77, '77 kg'), (78, '78 kg'), (79, '79 kg'), (80, '80 kg'), (81, '81 kg'), (82, '82 kg'), (83, '83 kg'), (84, '84 kg'), (85, '85 kg'), (86, '86 kg'), (87, '87 kg'), (88, '88 kg'), (89, '89 kg'), (90, '90 kg'), (91, '91 kg'), (92, '92 kg'), (93, '93 kg'), (94, '94 kg'), (95, '95 kg'), (96, '96 kg'), (97, '97 kg'), (98, '98 kg'), (99, '99 kg'), (100, '100 kg')], help_text='Requisito para poder inscribirse. Se verifica en báscula: el sistema no registra el peso de cada jugador.', null=True, verbose_name='Categoría con peso mínimo'),
        ),
    ]

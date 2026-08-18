
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0012_categoria_edad_minima_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoria',
            name='edad_minima',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(5, '5 años'), (6, '6 años'), (7, '7 años'), (8, '8 años'), (9, '9 años'), (10, '10 años'), (11, '11 años'), (12, '12 años'), (13, '13 años'), (14, '14 años'), (15, '15 años'), (16, '16 años'), (17, '17 años'), (18, '18 años'), (19, '19 años'), (20, '20 años'), (21, '21 años'), (22, '22 años'), (23, '23 años'), (24, '24 años'), (25, '25 años'), (26, '26 años'), (27, '27 años'), (28, '28 años'), (29, '29 años'), (30, '30 años'), (31, '31 años'), (32, '32 años'), (33, '33 años'), (34, '34 años'), (35, '35 años'), (36, '36 años'), (37, '37 años'), (38, '38 años'), (39, '39 años'), (40, '40 años'), (41, '41 años'), (42, '42 años'), (43, '43 años'), (44, '44 años'), (45, '45 años'), (46, '46 años'), (47, '47 años'), (48, '48 años'), (49, '49 años'), (50, '50 años'), (51, '51 años'), (52, '52 años'), (53, '53 años'), (54, '54 años'), (55, '55 años'), (56, '56 años'), (57, '57 años'), (58, '58 años'), (59, '59 años'), (60, '60 años'), (61, '61 años'), (62, '62 años'), (63, '63 años'), (64, '64 años'), (65, '65 años'), (66, '66 años'), (67, '67 años'), (68, '68 años'), (69, '69 años'), (70, '70 años'), (71, '71 años'), (72, '72 años'), (73, '73 años'), (74, '74 años'), (75, '75 años'), (76, '76 años'), (77, '77 años'), (78, '78 años'), (79, '79 años'), (80, '80 años')], help_text='Vacío es sin edad mínima.', null=True, verbose_name='Edad mínima'),
        ),
        migrations.AlterField(
            model_name='categoria',
            name='peso_minimo',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(50, '50 kg'), (51, '51 kg'), (52, '52 kg'), (53, '53 kg'), (54, '54 kg'), (55, '55 kg'), (56, '56 kg'), (57, '57 kg'), (58, '58 kg'), (59, '59 kg'), (60, '60 kg'), (61, '61 kg'), (62, '62 kg'), (63, '63 kg'), (64, '64 kg'), (65, '65 kg'), (66, '66 kg'), (67, '67 kg'), (68, '68 kg'), (69, '69 kg'), (70, '70 kg'), (71, '71 kg'), (72, '72 kg'), (73, '73 kg'), (74, '74 kg'), (75, '75 kg'), (76, '76 kg'), (77, '77 kg'), (78, '78 kg'), (79, '79 kg'), (80, '80 kg'), (81, '81 kg'), (82, '82 kg'), (83, '83 kg'), (84, '84 kg'), (85, '85 kg'), (86, '86 kg'), (87, '87 kg'), (88, '88 kg'), (89, '89 kg'), (90, '90 kg'), (91, '91 kg'), (92, '92 kg'), (93, '93 kg'), (94, '94 kg'), (95, '95 kg'), (96, '96 kg'), (97, '97 kg'), (98, '98 kg'), (99, '99 kg'), (100, '100 kg')], help_text='Vacío es sin peso mínimo. Al ponerlo, cargar el peso pasa a ser obligatorio.', null=True, verbose_name='Peso mínimo'),
        ),
    ]

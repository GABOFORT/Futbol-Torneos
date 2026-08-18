
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0013_alter_categoria_edad_minima_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoria',
            name='edad_minima',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(30, '30 años'), (31, '31 años'), (32, '32 años'), (33, '33 años'), (34, '34 años'), (35, '35 años'), (36, '36 años'), (37, '37 años'), (38, '38 años'), (39, '39 años'), (40, '40 años'), (41, '41 años'), (42, '42 años'), (43, '43 años'), (44, '44 años'), (45, '45 años'), (46, '46 años'), (47, '47 años'), (48, '48 años'), (49, '49 años'), (50, '50 años'), (51, '51 años'), (52, '52 años'), (53, '53 años'), (54, '54 años'), (55, '55 años'), (56, '56 años'), (57, '57 años'), (58, '58 años'), (59, '59 años'), (60, '60 años'), (61, '61 años'), (62, '62 años'), (63, '63 años'), (64, '64 años'), (65, '65 años'), (66, '66 años'), (67, '67 años'), (68, '68 años'), (69, '69 años'), (70, '70 años'), (71, '71 años'), (72, '72 años'), (73, '73 años'), (74, '74 años'), (75, '75 años'), (76, '76 años'), (77, '77 años'), (78, '78 años'), (79, '79 años'), (80, '80 años')], help_text='Vacío es sin edad mínima.', null=True, verbose_name='Edad mínima'),
        ),
    ]

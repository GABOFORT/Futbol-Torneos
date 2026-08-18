
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0011_liga_portada'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='edad_minima',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(30, '30 años o más'), (31, '31 años o más'), (32, '32 años o más'), (33, '33 años o más'), (34, '34 años o más'), (35, '35 años o más'), (36, '36 años o más'), (37, '37 años o más'), (38, '38 años o más'), (39, '39 años o más'), (40, '40 años o más'), (41, '41 años o más'), (42, '42 años o más'), (43, '43 años o más'), (44, '44 años o más'), (45, '45 años o más'), (46, '46 años o más'), (47, '47 años o más'), (48, '48 años o más'), (49, '49 años o más'), (50, '50 años o más'), (51, '51 años o más'), (52, '52 años o más'), (53, '53 años o más'), (54, '54 años o más'), (55, '55 años o más'), (56, '56 años o más'), (57, '57 años o más'), (58, '58 años o más'), (59, '59 años o más'), (60, '60 años o más'), (61, '61 años o más'), (62, '62 años o más'), (63, '63 años o más'), (64, '64 años o más'), (65, '65 años o más'), (66, '66 años o más'), (67, '67 años o más'), (68, '68 años o más'), (69, '69 años o más'), (70, '70 años o más'), (71, '71 años o más'), (72, '72 años o más'), (73, '73 años o más'), (74, '74 años o más'), (75, '75 años o más'), (76, '76 años o más'), (77, '77 años o más'), (78, '78 años o más'), (79, '79 años o más'), (80, '80 años o más')], help_text='Solo para categorías de veteranos. Vacío es sin edad mínima.', null=True, verbose_name='Edad mínima'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='empate_define_penales',
            field=models.BooleanField(default=True, help_text='Si lo desmarcas, un empate en jornada vale 1 punto para cada uno y no habra ganador.', verbose_name='El empate se define en penales'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='libre',
            field=models.BooleanField(default=False, help_text='Sin restricción: entra cualquier jugador, de cualquier edad, peso y sexo.', verbose_name='Categoría libre'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='mini_liguilla',
            field=models.BooleanField(default=False, help_text='Los puestos 9 a 12 juegan su propio cuadro. Necesita 12 equipos o más.', verbose_name='Mini-liguilla de consolación'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='peso_minimo',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(50, '50 kg o más'), (55, '55 kg o más'), (60, '60 kg o más'), (65, '65 kg o más'), (70, '70 kg o más'), (75, '75 kg o más'), (80, '80 kg o más'), (85, '85 kg o más'), (90, '90 kg o más'), (95, '95 kg o más'), (100, '100 kg o más')], help_text='Vacío es sin peso mínimo. Al prenderlo, cargar el peso pasa a ser obligatorio.', null=True, verbose_name='Peso mínimo'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='vueltas',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Una vuelta · todos se enfrentan una vez'), (2, 'Ida y vuelta · todos se enfrentan dos veces')], default=1, help_text='Con ida y vuelta se duplican las jornadas y se invierte la localía en la segunda.', verbose_name='Vueltas del torneo regular'),
        ),
    ]

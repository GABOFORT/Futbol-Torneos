"""Los datos con los que se arman las ligas de demostracion.

Va aparte del comando para que el comando se lea como el procedimiento y esto
como la tabla de datos. Todo lo de aca es publico y verificable:

  - Los clubes son los reales de cada liga.
  - Las canchas son sus estadios, con coordenadas verificadas contra Wikipedia,
    latitude.to y mapcarta en agosto de 2026. El pin cae adentro del estadio.
  - Los nombres de personas son veros�miles del pais de cada liga, pero NO son
    personas reales: son menores de edad y no corresponde cargar identidades
    ajenas en una base de produccion. El sistema publica su propio aviso de
    privacidad.

Las categorias usan la nomenclatura real del futbol formativo (Sub-9, Sub-13),
que es lo que significan de verdad: 'Primera / Segunda Division' no es una
categoria de edad.

**Cada categoria tiene su propio cupo, de 3 a 20 equipos.** No es un capricho:
el tamaño cambia el torneo entero. Con cupo impar hay un equipo que descansa
cada jornada, y el cuadro de la liguilla depende de cuantos entren:

    20, 18, 15, 14, 13, 11, 10, 9, 8  ->  cuartos de final (entran 8)
    6, 5, 4                           ->  semifinales      (entran 4)
    3                                 ->  final directa    (entran 2)

Con un solo cupo para todas, dos tercios de `liguilla.py` no se ejecutaban nunca.
"""

BUNDESLIGA = [
    ('Bayern Munchen', 'Allianz Arena', 48.218967, 11.624700),
    ('Borussia Dortmund', 'Signal Iduna Park', 51.492500, 7.451669),
    ('RB Leipzig', 'Red Bull Arena', 51.340808, 12.342264),
    ('Bayer Leverkusen', 'BayArena', 51.036286, 7.001322),
    ('Eintracht Frankfurt', 'Deutsche Bank Park', 50.068056, 8.645806),
    ('VfB Stuttgart', 'MHPArena', 48.792220, 9.231940),
    ('Werder Bremen', 'Weserstadion', 53.066389, 8.837500),
    ('Borussia Monchengladbach', 'Borussia-Park', 51.171417, 6.384611),
    ('VfL Wolfsburg', 'Volkswagen Arena', 52.431944, 10.803889),
    ('FC Schalke 04', 'Veltins-Arena', 51.554503, 7.067589),
    ('1. FC Koln', 'RheinEnergieStadion', 50.933497, 6.874997),
    ('Hertha BSC', 'Olympiastadion Berlin', 52.514722, 13.239444),
    ('TSG Hoffenheim', 'PreZero Arena', 49.239008, 8.888281),
    ('1. FSV Mainz 05', 'Mewa Arena', 49.984167, 8.224167),
    ('FC Augsburg', 'WWK Arena', 48.322500, 10.882222),
    ('Hamburger SV', 'Volksparkstadion', 53.587158, 9.898617),
    ('FC St. Pauli', 'Millerntor-Stadion', 53.554444, 9.967778),
    ('Hannover 96', 'HDI-Arena', 52.360067, 9.731197),
    ('1. FC Nurnberg', 'Max-Morlock-Stadion', 49.426111, 11.125833),
    ('Fortuna Dusseldorf', 'Merkur Spiel-Arena', 51.261667, 6.733056),
]

LIGA_MX = [
    ('Club America', 'Estadio Azteca', 19.302806, -99.150556),
    ('Guadalajara', 'Estadio Akron', 20.681670, -103.462780),
    ('Cruz Azul', 'Estadio Ciudad de los Deportes', 19.383330, -99.178330),
    ('Pumas UNAM', 'Estadio Olimpico Universitario', 19.331940, -99.192220),
    ('Tigres UANL', 'Estadio Universitario', 25.723000, -100.312000),
    ('Monterrey', 'Estadio BBVA', 25.669170, -100.244440),
    ('Toluca', 'Estadio Nemesio Diez', 19.287220, -99.666670),
    ('Santos Laguna', 'Estadio Corona', 25.629000, -103.379000),
    ('Leon', 'Estadio Leon', 21.109325, -101.654644),
    ('Pachuca', 'Estadio Hidalgo', 20.103780, -98.752330),
    ('Atlas', 'Estadio Jalisco', 20.705086, -103.328181),
    ('Necaxa', 'Estadio Victoria', 21.880690, -102.275430),
    ('Puebla', 'Estadio Cuauhtemoc', 19.078060, -98.164440),
    ('Queretaro', 'Estadio Corregidora', 20.577730, -100.366320),
    ('Tijuana', 'Estadio Caliente', 32.506110, -116.993060),
]

PREMIER_LEAGUE = [
    ('Arsenal', 'Emirates Stadium', 51.554867, -0.109112),
    ('Liverpool', 'Anfield', 53.430819, -2.960828),
    ('Manchester City', 'Etihad Stadium', 53.482989, -2.200292),
    ('Manchester United', 'Old Trafford', 53.463056, -2.291389),
    ('Chelsea', 'Stamford Bridge', 51.481667, -0.191111),
    ('Tottenham Hotspur', 'Tottenham Hotspur Stadium', 51.604252, -0.067007),
    ('Newcastle United', "St James' Park", 54.975170, -1.622539),
    ('Aston Villa', 'Villa Park', 52.509167, -1.884722),
    ('Everton', 'Goodison Park', 53.438889, -2.966389),
    ('Fulham', 'Craven Cottage', 51.475000, -0.221667),
    ('Wolverhampton Wanderers', 'Molineux Stadium', 52.590278, -2.130278),
    ('Norwich City', 'Carrow Road', 52.622128, 1.308653),
    ('Stoke City', 'bet365 Stadium', 52.988333, -2.175556),
    ('Sunderland', 'Stadium of Light', 54.914400, -1.388200),
    ('Swansea City', 'Swansea.com Stadium', 51.642200, -3.935100),
    ('West Bromwich Albion', 'The Hawthorns', 52.509167, -1.963889),
    ('Blackburn Rovers', 'Ewood Park', 53.728611, -2.489167),
    ('Queens Park Rangers', 'Loftus Road', 51.509167, -0.232222),
    ('Wigan Athletic', 'DW Stadium', 53.547778, -2.653889),
    ('Bolton Wanderers', 'Toughsheet Community Stadium', 53.580556, -2.535556),
]

SERIE_A = [
    ('Inter', 'San Siro', 45.478489, 9.122150),
    ('Milan', 'San Siro', 45.478489, 9.122150),
    ('Juventus', 'Allianz Stadium', 45.109440, 7.641110),
    ('Napoli', 'Stadio Diego Armando Maradona', 40.828000, 14.193000),
    ('Roma', 'Stadio Olimpico', 41.933964, 12.454297),
    ('Lazio', 'Stadio Olimpico', 41.933964, 12.454297),
    ('Atalanta', 'Gewiss Stadium', 45.708890, 9.680830),
    ('Fiorentina', 'Stadio Artemio Franchi', 43.775156, 11.276019),
    ('Bologna', "Stadio Renato Dall'Ara", 44.492194, 11.309806),
    ('Torino', 'Stadio Olimpico Grande Torino', 45.041670, 7.650000),
    ('Udinese', 'Bluenergy Stadium', 46.081600, 13.200100),
    ('Genoa', 'Stadio Luigi Ferraris', 44.416390, 8.952500),
    ('Cagliari', 'Unipol Domus', 39.199440, 9.137220),
    ('Hellas Verona', 'Stadio Marcantonio Bentegodi', 45.435280, 10.968610),
]

LA_LIGA = [
    ('Real Madrid', 'Santiago Bernabeu', 40.453053, -3.688344),
    ('Barcelona', 'Camp Nou', 41.380898, 2.122820),
    ('Atletico de Madrid', 'Civitas Metropolitano', 40.436139, -3.599472),
    ('Sevilla', 'Ramon Sanchez-Pizjuan', 37.384000, -5.970500),
    ('Real Sociedad', 'Reale Arena', 43.301390, -1.973610),
    ('Athletic Club', 'San Mames', 43.264300, -2.950400),
    ('Valencia', 'Mestalla', 39.474720, -0.358330),
    ('Villarreal', 'Estadio de la Ceramica', 39.944180, -0.103430),
    ('Real Betis', 'Benito Villamarin', 37.356389, -5.981389),
    ('Celta de Vigo', 'Balaidos', 42.211842, -8.739711),
    ('Osasuna', 'El Sadar', 42.796667, -1.636944),
    ('Getafe', 'Coliseum', 40.325556, -3.714722),
    ('Rayo Vallecano', 'Campo de Vallecas', 40.391944, -3.658961),
    ('Mallorca', 'Son Moix', 39.590000, 2.630000),
    ('Espanyol', 'RCDE Stadium', 41.347861, 2.075667),
    ('Real Valladolid', 'Jose Zorrilla', 41.644444, -4.761111),
    ('Granada', 'Nuevo Los Carmenes', 37.152967, -3.595736),
    ('Levante', 'Ciutat de Valencia', 39.494722, -0.364167),
    ('Deportivo La Coruna', 'Riazor', 43.368714, -8.417516),
    ('Almeria', 'Power Horse Stadium', 36.840000, -2.435278),
]


NOMBRES = {
    'de': {
        'varon': ['Lukas', 'Jonas', 'Leon', 'Finn', 'Noah', 'Elias', 'Paul', 'Ben',
                  'Felix', 'Maximilian', 'Moritz', 'Emil', 'Anton', 'Theo', 'Jakob',
                  'Niklas', 'Tim', 'Julian', 'Fabian', 'Simon'],
        'mujer': ['Mia', 'Emma', 'Hannah', 'Lina', 'Marie', 'Lena', 'Clara', 'Frieda',
                  'Johanna', 'Greta'],
        'apellidos': ['Muller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer',
                      'Wagner', 'Becker', 'Hoffmann', 'Schafer', 'Koch', 'Bauer',
                      'Richter', 'Klein', 'Wolf', 'Neumann', 'Braun', 'Zimmermann'],
        'compuesto': False,
    },
    'mx': {
        'varon': ['Santiago', 'Mateo', 'Diego', 'Emiliano', 'Sebastian', 'Leonardo',
                  'Angel', 'Iker', 'Alexander', 'Daniel', 'Bruno', 'Ian', 'Rodrigo',
                  'Emmanuel', 'Fernando', 'Ximeno', 'Julian', 'Maximiliano', 'Axel', 'Gael'],
        'mujer': ['Sofia', 'Valentina', 'Regina', 'Camila', 'Ximena', 'Renata',
                  'Victoria', 'Danna', 'Romina', 'Ivanna'],
        'apellidos': ['Hernandez', 'Garcia', 'Martinez', 'Lopez', 'Gonzalez', 'Perez',
                      'Rodriguez', 'Sanchez', 'Ramirez', 'Cruz', 'Flores', 'Gomez',
                      'Diaz', 'Reyes', 'Morales', 'Jimenez', 'Vazquez', 'Castillo'],
        'compuesto': True,
    },
    'en': {
        'varon': ['Oliver', 'Harry', 'Jack', 'George', 'Noah', 'Charlie', 'Jacob',
                  'Thomas', 'Oscar', 'William', 'James', 'Henry', 'Leo', 'Alfie',
                  'Freddie', 'Archie', 'Theo', 'Arthur', 'Joshua', 'Ethan'],
        'mujer': ['Olivia', 'Amelia', 'Isla', 'Ava', 'Ella', 'Grace', 'Poppy',
                  'Freya', 'Willow', 'Ivy'],
        'apellidos': ['Smith', 'Jones', 'Taylor', 'Brown', 'Williams', 'Wilson',
                      'Johnson', 'Davies', 'Robinson', 'Wright', 'Thompson', 'Evans',
                      'Walker', 'White', 'Roberts', 'Green', 'Hall', 'Clarke'],
        'compuesto': False,
    },
    'it': {
        'varon': ['Lorenzo', 'Francesco', 'Alessandro', 'Matteo', 'Leonardo',
                  'Riccardo', 'Tommaso', 'Gabriele', 'Andrea', 'Marco', 'Giuseppe',
                  'Antonio', 'Davide', 'Simone', 'Federico', 'Luca', 'Pietro',
                  'Nicolo', 'Filippo', 'Edoardo'],
        'mujer': ['Giulia', 'Sofia', 'Aurora', 'Alice', 'Ginevra', 'Emma',
                  'Beatrice', 'Chiara', 'Martina', 'Vittoria'],
        'apellidos': ['Rossi', 'Russo', 'Ferrari', 'Esposito', 'Bianchi', 'Romano',
                      'Colombo', 'Ricci', 'Marino', 'Greco', 'Bruno', 'Gallo',
                      'Conti', 'De Luca', 'Costa', 'Giordano', 'Mancini', 'Rizzo'],
        'compuesto': False,
    },
    'es': {
        'varon': ['Hugo', 'Martin', 'Pablo', 'Alejandro', 'Alvaro', 'Adrian',
                  'Daniel', 'David', 'Mario', 'Diego', 'Marcos', 'Javier', 'Iker',
                  'Gonzalo', 'Ruben', 'Sergio', 'Nicolas', 'Enzo', 'Bruno', 'Izan'],
        'mujer': ['Lucia', 'Martina', 'Maria', 'Paula', 'Daniela', 'Carla', 'Sara',
                  'Alba', 'Julia', 'Vega'],
        'apellidos': ['Garcia', 'Fernandez', 'Gonzalez', 'Rodriguez', 'Lopez',
                      'Martinez', 'Sanchez', 'Perez', 'Gomez', 'Martin', 'Jimenez',
                      'Ruiz', 'Hernandez', 'Diaz', 'Moreno', 'Alvarez', 'Romero', 'Navarro'],
        'compuesto': True,
    },
}


LIGAS = [
    {
        'nombre': 'Bundesliga',
        'pais': 'de',
        'inicio': (2026, 2, 7),
        'final': (2026, 11, 28),
        'clubes': BUNDESLIGA,
        'categorias': [
            ('Sub-11', 'U11', 20, 'terminada'),
            ('Sub-13', 'U13', 12, 'liguilla'),
            ('Sub-15', 'U15', 9, 'mitad'),
            ('Sub-17', 'U17', 6, 'arranque'),
        ],
    },
    {
        'nombre': 'Liga MX',
        'pais': 'mx',
        'inicio': (2026, 1, 31),
        'final': (2026, 11, 21),
        'clubes': LIGA_MX,
        'categorias': [
            ('Sub-13', 'U13', 15, 'terminada'),
            ('Sub-15', 'U15', 10, 'mitad'),
            ('Sub-17', 'U17', 6, 'sin_calendario'),
        ],
    },
    {
        'nombre': 'Premier League',
        'pais': 'en',
        'inicio': (2026, 1, 17),
        'final': (2026, 12, 12),
        'clubes': PREMIER_LEAGUE,
        'categorias': [
            ('Sub-9', 'U9', 20, 'terminada'),
            ('Sub-11', 'U11', 16, 'liguilla'),
            ('Sub-13', 'U13', 11, 'mitad'),
            ('Sub-15', 'U15', 8, 'arranque'),
            ('Sub-17', 'U17', 4, 'sin_calendario'),
        ],
    },
    {
        'nombre': 'Serie A',
        'pais': 'it',
        'inicio': (2026, 1, 24),
        'final': (2026, 12, 5),
        'clubes': SERIE_A,
        'categorias': [
            ('Sub-15', 'U15', 14, 'terminada'),
            ('Sub-17', 'U17', 3, 'terminada'),
        ],
    },
    {
        'nombre': 'La Liga',
        'pais': 'es',
        'inicio': (2026, 1, 10),
        'final': (2026, 12, 19),
        'clubes': LA_LIGA,
        'categorias': [
            ('Sub-7', 'U7', 18, 'terminada'),
            ('Sub-9', 'U9', 13, 'terminada'),
            ('Sub-11', 'U11', 10, 'liguilla'),
            ('Sub-13', 'U13', 8, 'mitad'),
            ('Sub-15', 'U15', 5, 'terminada'),
            ('Sub-17', 'U17', 3, 'arranque'),
        ],
    },
]

JUGADORES_MINIMO = 13
JUGADORES_MAXIMO = 20

FORMACIONES = ['4-4-2', '4-3-3', '3-5-2', '5-3-2', '4-2-3-1']


def posiciones_para(cantidad):
    """Las posiciones de un plantel de `cantidad` jugadores.

    Siempre arranca con dos arqueros —un equipo sin suplente de arquero no
    existe— y el resto se reparte entre defensa, medio y delantero en la
    proporcion de un plantel de verdad. Sin esto salian equipos de once
    delanteros y ningun portero.
    """
    posiciones = ['portero'] * min(2, cantidad)
    resto = cantidad - len(posiciones)
    defensas = round(resto * 5 / 14)
    medios = round(resto * 5 / 14)
    delanteros = resto - defensas - medios
    return posiciones + ['defensa'] * defensas + ['medio'] * medios + ['delantero'] * delanteros

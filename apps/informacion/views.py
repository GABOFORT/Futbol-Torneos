from django.shortcuts import render

from . import privacidad


def quienes_somos(request):
    return render(request, 'informacion/quienes_somos.html')


def donde_estamos(request):
    return render(request, 'informacion/donde_estamos.html')


def aviso_privacidad(request):
    return render(request, 'informacion/aviso_privacidad.html', {
        'secciones': privacidad.SECCIONES,
        'actualizado': privacidad.ACTUALIZADO,
        'domicilio': privacidad.DOMICILIO,
        'telefono': privacidad.TELEFONO,
        'correo': privacidad.CORREO,
        'responsable': privacidad.RESPONSABLE,
    })


def reglamento(request):
    articulos = [
        {
            'titulo': 'Uso de la plataforma',
            'texto': 'BUHO SPORT es una plataforma destinada a la gestión, difusión y seguimiento de ligas, torneos y eventos deportivos. Todos los usuarios deberán utilizar el sistema de manera responsable y conforme a este reglamento.',
            'lista': None,
        },
        {
            'titulo': 'Registro de usuarios',
            'texto': None,
            'lista': [
                {'texto': 'La información proporcionada durante el registro debe ser verídica y estar actualizada.', 'prohibido': False},
                {'texto': 'Cada usuario es responsable de la seguridad de su cuenta y contraseña.', 'prohibido': False},
                {'texto': 'No se permite compartir cuentas con terceros.', 'prohibido': True},
            ],
        },
        {
            'titulo': 'Conducta',
            'texto': None,
            'lista': [
                {'texto': 'Mantener un trato respetuoso hacia todos los usuarios.', 'prohibido': False},
                {'texto': 'Queda prohibido publicar contenido ofensivo, discriminatorio o que incite al odio.', 'prohibido': True},
                {'texto': 'No se permite suplantar la identidad de otras personas u organizaciones.', 'prohibido': True},
            ],
        },
        {
            'titulo': 'Información deportiva',
            'texto': 'Los organizadores son responsables de la veracidad de los datos registrados, incluyendo equipos, jugadores, resultados, estadísticas y calendarios. BUHO SPORT podrá corregir o eliminar información que incumpla las políticas de la plataforma.',
            'lista': None,
        },
        {
            'titulo': 'Equipos y torneos',
            'texto': 'Cada liga u organizador es responsable de sus reglamentos internos, convocatorias, sanciones y decisiones deportivas. BUHO SPORT actúa como plataforma de administración y difusión, no interviene en decisiones arbitrales o conflictos deportivos.',
            'lista': None,
        },
        {
            'titulo': 'Uso adecuado',
            'texto': None,
            'lista': [
                {'texto': 'Utilizar la plataforma para fines ilícitos.', 'prohibido': True},
                {'texto': 'Manipular resultados o estadísticas de forma fraudulenta.', 'prohibido': True},
                {'texto': 'Intentar vulnerar la seguridad del sistema.', 'prohibido': True},
                {'texto': 'Distribuir software malicioso o afectar el funcionamiento de la plataforma.', 'prohibido': True},
            ],
        },
        {
            'titulo': 'Disponibilidad del servicio',
            'texto': 'BUHO SPORT trabajará para mantener la plataforma disponible y segura; sin embargo, podrán realizarse mantenimientos, actualizaciones o interrupciones temporales cuando sea necesario.',
            'lista': None,
        },
        {
            'titulo': 'Privacidad',
            'texto': 'La información personal será tratada conforme a las políticas de privacidad de BUHO SPORT y utilizada únicamente para el funcionamiento de la plataforma y los servicios ofrecidos.',
            'lista': None,
        },
        {
            'titulo': 'Propiedad intelectual',
            'texto': 'El nombre, logotipo, diseño, contenido y software de BUHO SPORT son propiedad de la plataforma y no podrán ser utilizados, modificados o distribuidos sin autorización.',
            'lista': None,
        },
        {
            'titulo': 'Modificaciones',
            'texto': 'BUHO SPORT podrá actualizar este reglamento cuando sea necesario para mejorar el servicio o cumplir con disposiciones legales. Las modificaciones entrarán en vigor una vez publicadas en la plataforma.',
            'lista': None,
        },
        {
            'titulo': 'Aceptación',
            'texto': 'Al registrarse o utilizar BUHO SPORT, el usuario acepta este reglamento y se compromete a cumplir con todas las normas establecidas para garantizar una comunidad deportiva organizada, segura y respetuosa.',
            'lista': None,
        },
    ]
    return render(request, 'informacion/reglamento.html', {'articulos': articulos})



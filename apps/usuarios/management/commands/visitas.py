import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone as utc
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CARPETA_IIS = Path(r'C:\inetpub\logs\LogFiles\W3SVC1')

CAMPOS = {
    'fecha': 'date',
    'hora': 'time',
    'metodo': 'cs-method',
    'ruta': 'cs-uri-stem',
    'puerto': 's-port',
    'ip': 'c-ip',
    'agente': 'cs(User-Agent)',
    'origen': 'cs(Referer)',
    'estado': 'sc-status',
    'subestado': 'sc-substatus',
}

BOTS = re.compile(
    r'bot|crawl|spider|slurp|curl|wget|python|aiohttp|okhttp|scrapy|httpclient'
    r'|go-http|java/|libwww|headless|phantom|selenium|semrush|ahrefs|mj12'
    r'|dotbot|petal|bytespider|yandex|baidu|facebookexternalhit|whatsapp'
    r'|telegram|discord|zgrab|masscan|nmap|censys|expanse|scan|probe|nuclei'
)

SONDEOS = re.compile(
    r'\.php|\.cgi|\.asp|\.jsp|\.env|\.git|\.bak|\.sql|/wp-|/phpmyadmin'
    r'|/cgi-bin|/vendor/|/shell|/solr|/actuator|/manager/|/boaform|/pandora'
    r'|/jenkins|/hudson|/\.well-known/openid|^/admin'
)

MOVILES = re.compile(r'iphone|android|mobile|windows phone')

TABLETS = re.compile(r'ipad|tablet|kindle')

ESTATICOS = ('/static/', '/media/')

SUELTOS = ('/favicon.ico', '/robots.txt', '/apple-touch-icon.png')

PAGINAS_VALIDAS = {'200', '304'}

ANCHO_BARRA = 36


class Command(BaseCommand):
    help = 'Resume las visitas reales del sitio leyendo las bitacoras de IIS.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=1,
                            help='Cuantos dias hacia atras resumir, contando hoy. Por defecto 1.')
        parser.add_argument('--fecha',
                            help='Un solo dia, en formato AAAA-MM-DD.')
        parser.add_argument('--top', type=int, default=10,
                            help='Cuantas filas mostrar en cada tabla. Por defecto 10.')
        parser.add_argument('--sondeos', action='store_true',
                            help='Detalla los sondeos automatizados y de donde vienen.')
        parser.add_argument('--carpeta',
                            help='Carpeta de bitacoras de IIS, si no es la habitual.')

    def handle(self, *args, **opciones):
        self.zona = ZoneInfo(settings.TIME_ZONE)
        self.top = max(1, opciones['top'])

        carpeta = Path(opciones['carpeta']) if opciones['carpeta'] else CARPETA_IIS
        if not carpeta.is_dir():
            raise CommandError(
                f'No existe la carpeta de bitacoras: {carpeta}\n'
                f'Este comando lee las bitacoras de IIS, asi que solo da datos '
                f'en el servidor. Con --carpeta se le puede indicar otra ruta.')

        fechas = self._fechas(opciones)
        datos = self._acumular(self._lineas(carpeta, fechas))

        if not datos['peticiones']:
            self.stdout.write(self.style.WARNING(
                f'No hay ninguna peticion registrada en {self._titulo(fechas)}.'))
            return

        self._encabezado(fechas)
        self._resumen(datos)
        self._tabla('PAGINAS MAS VISTAS', datos['paginas'])
        self._tabla('DE DONDE LLEGAN', datos['origenes'])
        self._tabla('DISPOSITIVOS', datos['dispositivos'], total=len(datos['personas']))
        if len(fechas) > 1:
            self._barras('VISITANTES POR DIA', datos['por_dia'])
        else:
            self._barras('HORA DEL DIA', datos['por_hora'], etiqueta='{:02d}h')
        self._errores(datos)
        if opciones['sondeos']:
            self._detalle_sondeos(datos)

    def _fechas(self, opciones):
        if opciones['fecha']:
            try:
                return [date.fromisoformat(opciones['fecha'])]
            except ValueError:
                raise CommandError('La fecha va en formato AAAA-MM-DD, por ejemplo 2026-09-12.')
        dias = max(1, opciones['dias'])
        hoy = datetime.now(self.zona).date()
        return [hoy - timedelta(days=n) for n in reversed(range(dias))]

    def _lineas(self, carpeta, fechas):
        buscadas = set(fechas)
        for archivo in self._archivos(carpeta, fechas):
            indices = {}
            with archivo.open(encoding='utf-8', errors='replace') as bitacora:
                for linea in bitacora:
                    if linea.startswith('#'):
                        if linea.startswith('#Fields:'):
                            columnas = linea.split(':', 1)[1].split()
                            indices = {
                                clave: columnas.index(columna)
                                for clave, columna in CAMPOS.items()
                                if columna in columnas
                            }
                        continue
                    if len(indices) < len(CAMPOS):
                        continue
                    partes = linea.split()
                    if len(partes) <= max(indices.values()):
                        continue
                    momento = self._momento(partes[indices['fecha']], partes[indices['hora']])
                    if momento is None or momento.date() not in buscadas:
                        continue
                    yield momento, {
                        clave: partes[indice]
                        for clave, indice in indices.items()
                        if clave not in ('fecha', 'hora')
                    }

    def _archivos(self, carpeta, fechas):
        nombres = sorted({
            f'u_ex{dia:%y%m%d}.log'
            for fecha in fechas
            for dia in (fecha, fecha + timedelta(days=1))
        })
        return [ruta for ruta in (carpeta / nombre for nombre in nombres) if ruta.is_file()]

    def _momento(self, dia, hora):
        try:
            crudo = datetime.strptime(f'{dia} {hora}', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
        return crudo.replace(tzinfo=utc.utc).astimezone(self.zona)

    def _acumular(self, lineas):
        propios = {host.lower() for host in settings.ALLOWED_HOSTS}
        agentes = {}
        datos = {
            'peticiones': 0,
            'vistas': 0,
            'personas': set(),
            'navegadores': set(),
            'bots': Counter(),
            'paginas': Counter(),
            'origenes': Counter(),
            'dispositivos': Counter(),
            'por_hora': Counter(),
            'por_dia': defaultdict(set),
            'errores': Counter(),
            'sondeos': Counter(),
            'sondeos_ip': Counter(),
            'fallas': Counter(),
        }

        for momento, fila in lineas:
            datos['peticiones'] += 1
            ruta = fila['ruta']
            estado = fila['estado']
            agente = fila['agente'].replace('+', ' ')
            ip = fila['ip']
            es_bot = agente == '-' or bool(BOTS.search(agente.lower()))

            if estado == '404' and SONDEOS.search(ruta.lower()):
                datos['sondeos'][ruta] += 1
                datos['sondeos_ip'][ip] += 1
                continue

            if estado.startswith('5'):
                datos['fallas'][ruta] += 1
            elif estado == '404':
                datos['errores'][f'{estado}.{fila["subestado"]} {ruta}'] += 1

            if es_bot:
                datos['bots'][agente[:60]] += 1
                continue

            if ruta.startswith(ESTATICOS):
                if ip in datos['personas']:
                    datos['navegadores'].add(ip)
                continue

            if (fila['metodo'] != 'GET' or fila['puerto'] != '443'
                    or estado not in PAGINAS_VALIDAS or ruta in SUELTOS):
                continue

            datos['vistas'] += 1
            datos['personas'].add(ip)
            datos['por_dia'][momento.date()].add(ip)
            datos['por_hora'][momento.hour] += 1
            datos['paginas'][ruta] += 1
            agentes.setdefault(ip, agente)

            host = urlsplit(fila['origen']).hostname if fila['origen'] != '-' else None
            if host is None:
                datos['origenes']['directo'] += 1
            elif host.lower() not in propios:
                datos['origenes'][host.lower()] += 1

        for agente in agentes.values():
            datos['dispositivos'][self._dispositivo(agente.lower())] += 1

        return datos

    def _dispositivo(self, agente):
        if TABLETS.search(agente):
            return 'tablet'
        if MOVILES.search(agente):
            return 'movil'
        return 'escritorio'

    def _titulo(self, fechas):
        if len(fechas) == 1:
            return fechas[0].strftime('%d/%m/%Y')
        return f'{fechas[0]:%d/%m/%Y} al {fechas[-1]:%d/%m/%Y}'

    def _encabezado(self, fechas):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'VISITAS  {self._titulo(fechas)}'))

    def _resumen(self, datos):
        personas = len(datos['personas'])
        vistas = datos['vistas']
        filas = [
            ('Personas', f'{personas}'),
            ('Paginas vistas', f'{vistas}'),
            ('Paginas por persona', f'{vistas / personas:.1f}' if personas else '0'),
            ('Navegadores confirmados', f'{len(datos["navegadores"])} (cargaron los estilos)'),
            ('Bots', f'{sum(datos["bots"].values())} peticiones de {len(datos["bots"])} origenes'),
            ('Sondeos', f'{sum(datos["sondeos"].values())} intentos '
                        f'de {len(datos["sondeos_ip"])} direcciones'),
            ('Peticiones totales', f'{datos["peticiones"]}'),
        ]
        ancho = max(len(etiqueta) for etiqueta, _ in filas)
        self.stdout.write('')
        for etiqueta, valor in filas:
            self.stdout.write(f'  {etiqueta:<{ancho}}   {valor}')

    def _tabla(self, titulo, conteo, total=None):
        if not conteo:
            return
        filas = conteo.most_common(self.top)
        ancho = len(str(filas[0][1]))
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL(titulo))
        for clave, veces in filas:
            porcentaje = f'  {veces / total:.0%}' if total else ''
            self.stdout.write(f'  {veces:>{ancho}}  {self._corto(clave)}{porcentaje}')
        restantes = len(conteo) - len(filas)
        if restantes:
            self.stdout.write(f'  {"":>{ancho}}  y {restantes} mas')

    def _barras(self, titulo, conteo, etiqueta='{}'):
        if not conteo:
            return
        if isinstance(conteo, defaultdict):
            conteo = {clave: len(valor) for clave, valor in conteo.items()}
        tope = max(conteo.values())
        ancho = len(str(tope))
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL(titulo))
        for clave in sorted(conteo):
            valor = conteo[clave]
            barra = '#' * max(1, round(valor / tope * ANCHO_BARRA))
            nombre = etiqueta.format(clave) if etiqueta != '{}' else f'{clave:%d/%m}'
            self.stdout.write(f'  {nombre}  {barra:<{ANCHO_BARRA}} {valor:>{ancho}}')

    def _errores(self, datos):
        if not datos['fallas'] and not datos['errores']:
            return
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL('ERRORES'))
        for ruta, veces in datos['fallas'].most_common(self.top):
            self.stdout.write(self.style.ERROR(f'  {veces:>5}  500  {self._corto(ruta)}'))
        for etiqueta, veces in datos['errores'].most_common(self.top):
            self.stdout.write(self.style.WARNING(f'  {veces:>5}  {self._corto(etiqueta, 70)}'))

    def _detalle_sondeos(self, datos):
        self._tabla('SONDEOS MAS REPETIDOS', datos['sondeos'])
        self._tabla('DIRECCIONES QUE MAS SONDEAN', datos['sondeos_ip'])
        self._tabla('BOTS', datos['bots'])

    def _corto(self, texto, tope=64):
        return texto if len(texto) <= tope else f'{texto[:tope - 3]}...'

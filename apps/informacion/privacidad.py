"""Contenido del aviso de privacidad.

Vive aparte de la vista porque es un texto legal largo que se revisa y se
actualiza por su cuenta: mezclarlo con las paginas informativas obligaria a
leer codigo para corregir una linea.

`ACTUALIZADO` debe moverse cada vez que cambie el texto: es la fecha que ve el
usuario y la que vale si algun dia se discute que decia el aviso.
"""

RESPONSABLE = 'BUHO SPORT'

DOMICILIO = ('Carr. Villahermosa la Isla 157, Miguel Hidalgo III Etapa, '
             '86127 Villahermosa, Tabasco, México')

TELEFONO = '+52 993 289 3328'

CORREO = 'buhosportsleague@gmail.com'

ACTUALIZADO = '28 de agosto de 2026'

SECCIONES = [
    {
        'titulo': 'Qué es esta plataforma y quién responde por los datos',
        'parrafos': [
            f'{RESPONSABLE}, ofrece un servicio: una plataforma '
            f'para que ligas, torneos, clubes y entrenadores administren y difundan sus '
            f'competencias deportivas.',
            f'{RESPONSABLE} no organiza competencias, no inscribe jugadores, no recaba datos por '
            f'su cuenta y no decide qué información se carga ni con qué finalidad. Únicamente '
            f'pone la herramienta a disposición de quien la contrata y la opera.',
        ],
        'lista': [
            'Cada liga, torneo, club, organizador o entrenador que registra información es el '
            'responsable de esos datos personales: él decide qué captura, para qué, de quién lo '
            'obtiene y cuánto lo conserva, y es quien debe contar con el consentimiento de las '
            'personas involucradas y de los padres o tutores cuando se trate de menores.',
            f'Respecto de esa información, {RESPONSABLE} actúa exclusivamente como encargado del '
            f'tratamiento: la almacena y la muestra siguiendo lo que decide quien la cargó, sin '
            f'usarla para fines propios, sin venderla y sin disponer de ella.',
            f'{RESPONSABLE} responde únicamente por los datos de las cuentas creadas para entrar '
            f'al sistema usuario, correo y teléfono y por las bitácoras técnicas de seguridad, '
            f'que son lo indispensable para operar y proteger la plataforma.',
            'Cualquier solicitud sobre los datos de un jugador, un equipo o una liga debe '
            'dirigirse a la liga o al entrenador que los registró, por ser quien los administra '
            'y quien responde por ellos.',
        ],
        'cierre': f'En pocas palabras: {RESPONSABLE} presta el servicio; las ligas y los '
                  f'entrenadores son los dueños y responsables de la información que suben.',
    },
    {
        'titulo': 'Qué información tratamos',
        'parrafos': [
            'Tratamos únicamente la información necesaria para operar la plataforma:',
        ],
        'lista': [
            'Datos de cuenta de administradores y entrenadores: nombre, usuario, correo '
            'electrónico, teléfono y organización.',
            'Datos de jugadores cargados por las ligas y los entrenadores: nombre, apellido, '
            'fecha de nacimiento, sexo, posición, número, estado deportivo y, cuando se '
            'proporciona, fotografía y documento de identificación.',
            'Datos deportivos: equipos, categorías, calendarios, sedes, resultados, goles, '
            'asistencias, sanciones y estadísticas derivadas.',
            'Datos técnicos de seguridad: dirección IP, fecha y hora de acceso e intentos de '
            'inicio de sesión, que se conservan en bitácoras para proteger las cuentas.',
        ],
        'cierre': 'No solicitamos ni almacenamos datos bancarios, tarjetas de pago, datos '
                  'biométricos ni información de salud.',
    },
    {
        'titulo': 'Para qué usamos esta información',
        'lista': [
            'Registrar y administrar ligas, torneos, categorías, equipos y planteles.',
            'Generar calendarios, tablas de posiciones, estadísticas y palmarés.',
            'Publicar la información deportiva de las competencias, que es de consulta abierta.',
            'Dar acceso a las cuentas de administradores y entrenadores, y protegerlas.',
            'Atender solicitudes, aclaraciones y reportes relacionados con la plataforma.',
        ],
        'cierre': 'No utilizamos los datos con fines publicitarios, de perfilamiento ni de '
                  'venta a terceros.',
    },
    {
        'titulo': 'Información que se publica de forma abierta',
        'parrafos': [
            'Esta plataforma es, por su naturaleza, una vitrina deportiva pública. Los nombres '
            'de equipos y jugadores, sus fotografías cuando se cargan, posiciones, números, '
            'resultados, estadísticas, calendarios y sedes pueden ser consultados por cualquier '
            'persona, sin necesidad de registrarse, y pueden ser indexados por buscadores.',
            'Quien carga esa información la liga, el organizador o el entrenador acepta que '
            'será visible públicamente y manifiesta contar con las autorizaciones necesarias '
            'para difundirla. No se publican domicilios, correos, teléfonos ni documentos de '
            'identificación de los jugadores.',
        ],
    },
    {
        'titulo': 'Obligaciones de quien carga la información',
        'parrafos': [
            'Los datos de equipos, jugadores, edades, fotografías y resultados son ingresados, '
            'modificados y actualizados por los administradores de liga, los organizadores y '
            'los entrenadores. Al hacerlo, cada uno se obliga a:',
        ],
        'lista': [
            'Contar con el consentimiento de las personas cuyos datos registra y, tratándose de '
            'menores, con el de su padre, madre o tutor.',
            'Responder por la veracidad, exactitud, licitud y actualización de lo que publica.',
            'Cargar únicamente información y fotografías sobre las que tenga derecho a disponer.',
            'Atender las solicitudes de acceso, corrección o eliminación que le presenten los '
            'titulares de esos datos.',
            'Mantener la confidencialidad de su cuenta y no compartirla con terceros.',
        ],
        'cierre': f'Quien incumpla lo anterior responde frente a los titulares y frente a '
                  f'terceros, y se obliga a sacar en paz y a salvo a {RESPONSABLE} de cualquier '
                  f'reclamación, sanción o gasto que se derive de la información que cargó.',
    },
    {
        'titulo': 'Menores de edad',
        'parrafos': [
            'La plataforma difunde competencias de categorías infantiles y juveniles, por lo '
            'que trata datos de personas menores de edad.',
            'El registro de un menor únicamente puede realizarlo su liga, club o entrenador, '
            'quien manifiesta contar con el consentimiento expreso del padre, madre o tutor '
            'para registrar y difundir públicamente esa información en los términos de este '
            'aviso.',
            'El padre, madre o tutor puede solicitar en cualquier momento la corrección, '
            'ocultamiento o eliminación de los datos y fotografías del menor, dirigiéndose a la '
            'liga que lo registró o directamente a los medios de contacto de este aviso.',
            'Corresponde también al padre, madre o tutor supervisar el uso que el menor haga de '
            'internet, incluidos los enlaces a sitios externos que puedan aparecer en la '
            'plataforma.',
        ],
    },
    {
        'titulo': 'Patrocinadores, anuncios y enlaces a sitios de terceros',
        'parrafos': [
            f'Los logotipos, patrocinios, anuncios y enlaces que se muestran corresponden a '
            f'personas, negocios y organizaciones ajenas a {RESPONSABLE}. Su presencia responde '
            f'a un acuerdo celebrado con la liga o el torneo correspondiente y no implica '
            f'recomendación, aval, verificación, supervisión ni vínculo comercial con '
            f'{RESPONSABLE}.',
            f'{RESPONSABLE} no controla, no revisa de forma continua y no responde por el '
            f'contenido, los productos, los servicios, la publicidad, las prácticas de '
            f'privacidad ni la disponibilidad de los sitios de terceros a los que esos enlaces '
            f'dirigen.',
            'Al seguir un enlace hacia un sitio externo, la persona abandona esta plataforma y '
            'deja de estar amparada por este aviso: desde ese momento aplican los términos y el '
            'aviso de privacidad del sitio de destino, y la navegación corre por cuenta y '
            'riesgo de quien decide seguirlo.',
            f'Considerando que esta plataforma difunde competencias de categorías infantiles y '
            f'juveniles, {RESPONSABLE} se reserva el derecho de rechazar, condicionar, '
            f'suspender o retirar en cualquier momento, sin previo aviso y sin necesidad de '
            f'justificación, cualquier patrocinio, logotipo, anuncio o enlace cuyo contenido, '
            f'giro, imagen o presentación no resulte apropiado para una audiencia que incluye '
            f'personas menores de edad, o que a su juicio pueda afectar la imagen de la '
            f'plataforma. El ejercicio de este derecho no genera reclamación, reembolso ni '
            f'indemnización alguna, y se entiende que la relación económica del patrocinio fue '
            f'celebrada con la liga u organizador, no con {RESPONSABLE}.',
        ],
    },
    {
        'titulo': 'Limitación de responsabilidad',
        'parrafos': [
            f'{RESPONSABLE} es una plataforma de administración y difusión deportiva. El '
            f'servicio se ofrece tal como está y según disponibilidad.',
        ],
        'lista': [
            'No garantizamos ni respondemos por la exactitud, veracidad, vigencia, legalidad o '
            'integridad de la información publicada por las ligas, los organizadores o los '
            'entrenadores, ni por el uso que terceros hagan de ella.',
            'No intervenimos ni respondemos por decisiones arbitrales, deportivas o '
            'disciplinarias, elegibilidad de jugadores, ni por conflictos entre ligas, equipos, '
            'entrenadores, padres o jugadores.',
            'No participamos ni respondemos por cobros, inscripciones, cuotas, patrocinios ni '
            'acuerdos económicos pactados entre las partes.',
            'No respondemos por lesiones, accidentes o incidentes ocurridos antes, durante o '
            'después de los encuentros, ni por lo que suceda en las canchas y sedes, que no son '
            'operadas por nosotros.',
            'No garantizamos que la plataforma funcione de forma ininterrumpida o libre de '
            'errores. Puede haber suspensiones por mantenimiento, fallas de energía, de red, de '
            'proveedores externos o causas de fuerza mayor.',
        ],
        'cierre': f'Hasta el máximo que permita la legislación aplicable, {RESPONSABLE} no será '
                  f'responsable por daños o perjuicios directos, indirectos, incidentales, '
                  f'especiales o consecuenciales incluida la pérdida de datos, de oportunidad '
                  f'o de ingresos derivados del uso o de la imposibilidad de uso de la '
                  f'plataforma o de la información contenida en ella. Quien publique '
                  f'información se obliga a sacar en paz y a salvo a {RESPONSABLE} frente a '
                  f'cualquier reclamación de terceros derivada de esa publicación.',
    },
    {
        'titulo': 'Con quién se comparte',
        'parrafos': [
            'No vendemos, alquilamos ni comercializamos datos personales.',
            'La información deportiva de consulta abierta es visible para cualquier visitante, '
            'según se explica en este aviso. Fuera de eso, solo compartimos datos cuando exista '
            'requerimiento fundado y motivado de una autoridad competente, o cuando sea '
            'necesario para proteger derechos, la seguridad de las personas o la del propio '
            'sistema.',
        ],
    },
    {
        'titulo': 'Tus derechos y cómo ejercerlos',
        'parrafos': [
            'Puedes solicitar el acceso, la rectificación, la cancelación o la oposición al '
            'tratamiento de tus datos personales, así como revocar el consentimiento otorgado.',
            'Si tu solicitud es sobre datos de un jugador, un equipo o una liga, dirígela a la '
            'liga, club o entrenador que los registró: es quien decide sobre esa información y '
            'quien puede corregirla o eliminarla desde la plataforma. Si se trata de un menor, '
            'la solicitud debe presentarla su padre, madre o tutor.',
            f'Si tu solicitud es sobre la cuenta con la que entras al sistema, comunícate por '
            f'los medios señalados al final de este aviso: eso sí lo administra {RESPONSABLE}.',
            f'Cuando una liga deje de operar o no sea localizable, {RESPONSABLE} atenderá la '
            f'solicitud en lo que esté dentro de sus posibilidades técnicas.',
        ],
    },
    {
        'titulo': 'Conservación de la información',
        'parrafos': [
            'Los datos se conservan mientras la liga, el torneo o la cuenta permanezcan activos '
            'y durante el tiempo necesario para cumplir las finalidades descritas.',
            'Los resultados históricos y el palmarés pueden conservarse de forma indefinida como '
            'registro deportivo de las competencias. Las bitácoras de seguridad se conservan por '
            'periodos limitados y se depuran de forma automática.',
        ],
    },
    {
        'titulo': 'Seguridad',
        'parrafos': [
            'Aplicamos medidas técnicas y organizativas razonables para proteger la información: '
            'conexión cifrada, contraseñas almacenadas de forma irreversible, control de acceso '
            'por rol, bloqueo tras intentos fallidos, expiración de sesión por inactividad y '
            'bitácoras de los movimientos relevantes.',
            'Ningún sistema conectado a internet es completamente invulnerable. Cada usuario es '
            'responsable de resguardar su contraseña y de no compartir su cuenta.',
        ],
    },
    {
        'titulo': 'Cookies y almacenamiento en tu dispositivo',
        'parrafos': [
            'Utilizamos únicamente lo indispensable para que la plataforma funcione: una cookie '
            'de sesión para mantener la sesión iniciada y una cookie de seguridad para proteger '
            'los formularios. No usamos cookies de publicidad, de rastreo ni de terceros.',
            'Si eliges seguir equipos desde la portada, esa preferencia se guarda en tu propio '
            'dispositivo y no se envía ni se almacena en nuestros servidores.',
            'Los mapas incrustados provienen de un proveedor externo y pueden aplicar sus '
            'propias tecnologías al cargarse; su uso se rige por las políticas de ese proveedor.',
        ],
    },
    {
        'titulo': 'Cambios a este aviso',
        'parrafos': [
            'Este aviso puede actualizarse para reflejar cambios en la plataforma o en la '
            'legislación aplicable. La versión vigente será siempre la publicada en esta página, '
            'con su fecha de actualización.',
            'El uso de la plataforma después de publicada una modificación implica la aceptación '
            'de la versión vigente.',
        ],
    },
    {
        'titulo': 'Aceptación',
        'parrafos': [
            'Al registrarse, cargar información o utilizar esta plataforma, el usuario declara '
            'haber leído y aceptado este aviso de privacidad y las limitaciones de '
            'responsabilidad aquí descritas.',
        ],
    },
]

"""Carga inicial de la guía de cuidado. Sin cuentas: creado_por y actualizado_por quedan nulos.

ON CONFLICT (clave) DO NOTHING: si la ficha ya existe no se duplica ni se sobrescribe lo editado después.
Estas constantes son historial de la migración; el contenido vigente vive en PostgreSQL.
"""
import uuid

from django.db import migrations

UMD = ('University of Maryland Extension', 'https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables')
UMN = ('University of Minnesota Extension', 'https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers')
OSU = ('Oregon State University Extension', 'https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers')
SIN_FUENTE = ('', '')

GUIAS = [
    ('germinacion-inicio', 10, '¿Cómo comienzo a germinar mis semillas de habanero?',
     'Etapa de germinación. Se hace fuera del sistema, en un semillero aparte con mezcla limpia para semillas. Cubre las semillas con una capa ligera y mantén la mezcla húmeda, sin encharcarla.\n\n'
     'Las semillas de chile germinan mejor en un lugar cálido y estable que en uno frío. Cuando asomen los brotes, dales luz abundante: con poca luz, el tallo se alarga y se inclina.\n\n'
     'Registrar la germinación solo deja constancia de lo que ya hiciste. El sistema no la realiza ni la comprueba.', UMN),
    ('brotacion-tiempo', 20, '¿Cuánto puede tardar en brotar y qué debo observar?',
     'No hay un plazo fijo. Depende de la edad de la semilla, la variedad, la temperatura y la humedad. El habanero puede tardar varias semanas, así que una espera larga no significa por sí sola que la siembra haya fallado.\n\n'
     'Mientras tanto, observa que la mezcla siga húmeda y sin charcos, y que no aparezca moho ni mal olor. Si la mezcla se seca por completo o se mantiene empapada, la germinación puede fallar.\n\n'
     'Cuando broten, vigila que el tallo no se alargue ni se doble hacia la luz.', UMN),
    ('trasplante-plantula', 30, '¿Cómo reconozco que la plántula está lista para trasplantar?',
     'Etapa de trasplante. Guíate por la plántula y no por el calendario: tallo firme, hojas verdaderas además de las dos primeras, buen color y raíces que ya sostienen la mezcla al sacarla.\n\n'
     'Si creció en otro lugar, acostúmbrala poco a poco a la luz y a las condiciones del huerto. Al trasplantar, no entierres el tallo más de lo que estaba y riega después. Si ya tiene flores, puedes retirarlas para que se concentre en crecer.\n\n'
     'Las fechas de las guías para exteriores dependen de las heladas y de cada clima. No se aplican tal cual a un huerto interior.', OSU),
    ('sustrato-perlita', 40, '¿Para qué sirve la perlita y cómo reviso el sustrato?',
     'La perlita ayuda a conservar la aireación: mantiene espacios en la mezcla para que entren aire y agua y para que las raíces respiren.\n\n'
     'Revisa si el agua drena con facilidad. Si notas compactación, malos olores o acumulación de sales, revisa la mezcla antes de volver a regar. Con el tiempo la mezcla se degrada y pierde esos espacios, así que conviene renovarla cuando deje de drenar bien.\n\n'
     'Marcar la revisión hecha declara que ya la realizaste. El sistema no inspecciona el sustrato.', UMD),
    ('riego-revision', 50, '¿Cuándo debo revisar el riego de mis plantas?',
     'Etapa de crecimiento. Revisa antes de regar, no por un horario fijo: toca el sustrato un poco por debajo de la superficie. La velocidad con que se seca cambia con el tamaño de la planta, la luz, la temperatura y el recipiente.\n\n'
     'Que una planta se marchite no prueba que le falte agua: el exceso de riego también la marchita. Un sustrato siempre empapado deja a las raíces sin aire y puede dañarlas. Evita que quede agua estancada.\n\n'
     'La lectura de humedad, cuando existe, es un dato más. Confírmala revisando la planta y el sustrato.', UMD),
    ('deposito-recarga', 60, '¿Qué significa rellenar el depósito y registrar la recarga?',
     'Rellenar es añadir agua limpia al depósito con tus propias manos. Después, «Ya rellené el depósito» guarda la fecha de ese cuidado.\n\n'
     'Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.\n\n'
     'El flotador detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo.', SIN_FUENTE),
    ('mangueras-goteros', 70, '¿Cómo reviso las mangueras y los goteros?',
     'Mira que las mangueras no estén dobladas, aplastadas ni sueltas, y que no haya fugas en las uniones. Comprueba que los cables y las conexiones estén secos.\n\n'
     'Observa si cada gotero entrega agua de forma parecida a los demás. Un gotero que no gotea puede estar obstruido o tener la manguera doblada.\n\n'
     'Si encuentras una fuga o algo no parece seguro, usa el paro físico del equipo y solicita soporte técnico. «Registrar inspección» declara que hiciste la revisión; el sistema no la comprueba.', SIN_FUENTE),
    ('cosecha-registro', 80, '¿Cómo identifico y registro una cosecha?',
     'Etapa de cosecha. Fíjate en el fruto y no en una fecha: firme, de tamaño completo y con el color final de su variedad. El tiempo y la cantidad de frutos varían de una planta a otra.\n\n'
     'Corta con utensilios limpios y deja un poco de tallo unido al fruto, sin tirar para no romper las ramas. Usa guantes: el habanero irrita la piel y los ojos. Retirar los frutos maduros con regularidad favorece que la planta siga produciendo.\n\n'
     'Después, «Registrar cosecha» guarda la fecha de lo que ya hiciste. El sistema no detecta la cosecha ni la comprueba.', OSU),
    ('sin-lecturas', 90, '¿Qué hago si no hay lecturas o el dispositivo está desconectado?',
     'Sin lecturas válidas no puede deducirse el estado de la planta: «sin datos» no significa que esté bien ni que le falte agua. Una lectura antigua tampoco describe lo que ocurre ahora.\n\n'
     'Mientras tanto, revisa directamente las plantas, el sustrato y el depósito. Comprueba que el equipo tenga corriente y que tu red Wi-Fi funcione.\n\n'
     'Si el problema continúa, repórtalo en Soporte técnico.', SIN_FUENTE),
]

INSERTAR = """INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES (%s::uuid,%s,%s,%s,%s,'publicada',%s,%s,1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING"""


def sentencias():
    filas = []
    for clave, orden, pregunta, respuesta, (fuente, enlace) in GUIAS:
        identificador = str(uuid.uuid5(uuid.NAMESPACE_URL, f'el-chilito/guia/{clave}'))
        filas.append((INSERTAR, [identificador, clave, pregunta, respuesta, orden, fuente, enlace]))
    return filas


class Migration(migrations.Migration):
    dependencies = [('datos', '0011_guias_cuidado')]
    operations = [migrations.RunSQL(sentencias(), migrations.RunSQL.noop)]

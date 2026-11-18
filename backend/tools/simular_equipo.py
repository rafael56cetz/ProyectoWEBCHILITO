"""Simulador de equipo para probar la interfaz sin un ESP32. SOLO DESARROLLO.

Se conecta como chilito_pkg_iot (el mismo rol del servicio IoT real) y usa sus propias variables de entorno, nunca las de la
aplicación: CHILITO_SIM_DB, CHILITO_SIM_HOST, CHILITO_SIM_PUERTO y CHILITO_SIM_CLAVE_IOT. Se niega a correr fuera de desarrollo
(CHILITO_ENV=local o testing y CHILITO_DEBUG=1) y solo escribe en las bases de desarrollo o de pruebas.

«vincular» no toca la base: hace lo mismo que el ESP32 y llama al servicio de vinculación (CHILITO_SIM_URL o, si no está,
http://localhost:8780/api/dispositivos/vincular) con la credencial del equipo y el código que muestra «Vincular equipo».

Cada ejecución deja un evento «reinicio» con detalle «simulador» en la bitácora del equipo: así lo simulado no se confunde con
la operación real. Los eventos «conectado» y «desconectado» los escribe la propia base al cambiar la conexión.

Uso (salvo «vincular», el equipo debe estar vinculado a un huerto):
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 vincular
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 conectar
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 medir --n 12 --intervalo 300
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 atender --falla bomba_2
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 correr --cada 10
  python backend/tools/simular_equipo.py CHI-PRUEBA-0001 desconectar

Ciclo del depósito (el flotador lo interpreta la base: aviso, eventos y recarga «Detectada por tu equipo»):
  medir --sin-agua                     el flotador marca nivel bajo: evento deposito_bajo y aviso «Tu depósito necesita agua»
  medir                                vuelve a detectar agua: evento deposito_recargado y una recarga del equipo
Cargas completas con duración (en orden cronológico; --hace desplaza la medición N horas hacia atrás, hasta 7 días):
  medir --hace 120 --sin-agua  →  medir --hace 119  →  medir --hace 48 --sin-agua  →  medir
  (deja una carga de ~71 h y otra abierta con su estimación; las mediciones atrasadas respecto a otra más nueva no cuentan)
"""
import argparse
import getpass
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import psycopg

ROL = 'chilito_pkg_iot'
BASES_DE_DESARROLLO = {'chilito_integracion_sinteticos', 'test_chilito_integracion_sinteticos'}
FIRMWARE = '0.0.0-simulador'
COMPONENTES = ('conexion', 'sensor_ambiente', 'sensor_luz', 'sensor_sustrato_1', 'sensor_sustrato_2', 'sensor_sustrato_3',
               'flotador', 'bomba_1', 'bomba_2', 'bomba_3', 'lampara', 'ventilador')
SIN_INSTALAR = ('ventilador',)
URL_VINCULAR = 'http://localhost:8780/api/dispositivos/vincular'
FORMATO_CODIGO = re.compile(r'[0-9A-Za-z]{4}-?[0-9A-Za-z]{4}')
EQUIPO_LOCAL = {'localhost', '127.0.0.1'}
ACTUADOR_POR_ORDEN = {'lampara_apagar': ('lampara', 'apagado'), 'lampara_automatico': ('lampara', 'encendido'),
                      'ventilador_encender': ('ventilador', 'encendido'), 'ventilador_apagar': ('ventilador', 'apagado')}


def exigir_desarrollo(entorno):
    if entorno.get('CHILITO_ENV') not in ('local', 'testing') or entorno.get('CHILITO_DEBUG') != '1':
        sys.exit('El simulador solo corre con CHILITO_ENV=local o testing y CHILITO_DEBUG=1.')


def exigir_entorno(entorno=None):
    """Devuelve los datos de conexión o termina el programa si el entorno no es de desarrollo."""
    entorno = os.environ if entorno is None else entorno
    exigir_desarrollo(entorno)
    base = entorno.get('CHILITO_SIM_DB', '')
    if base not in BASES_DE_DESARROLLO and 'prueba' not in base and 'test' not in base:
        sys.exit(f'El simulador no escribe en «{base}»: solo en bases de desarrollo o de pruebas.')
    if not entorno.get('CHILITO_SIM_CLAVE_IOT'):
        sys.exit('Falta CHILITO_SIM_CLAVE_IOT (la contraseña de chilito_pkg_iot).')
    return {'host': entorno.get('CHILITO_SIM_HOST', 'localhost'), 'port': int(entorno.get('CHILITO_SIM_PUERTO', '5432')),
            'dbname': base, 'user': ROL, 'password': entorno['CHILITO_SIM_CLAVE_IOT'], 'autocommit': True}


def url_vinculacion(entorno):
    """La credencial solo viaja cifrada, salvo hacia este mismo equipo."""
    url = entorno.get('CHILITO_SIM_URL') or URL_VINCULAR
    partes = urlsplit(url)
    if partes.scheme != 'https' and not (partes.scheme == 'http' and partes.hostname in EQUIPO_LOCAL):
        sys.exit('CHILITO_SIM_URL debe usar https, o http solo hacia localhost.')
    return url


def vincular(identificador, entorno=None):
    """Pide la credencial y el código, los envía como el ESP32 y devuelve el resultado del servidor."""
    entorno = os.environ if entorno is None else entorno
    exigir_desarrollo(entorno)
    url = url_vinculacion(entorno)
    credencial = getpass.getpass('Credencial del equipo: ')
    codigo = input('Código de vinculación (XXXX-XXXX): ').strip()
    if not credencial or not FORMATO_CODIGO.fullmatch(codigo):
        sys.exit('Escribe la credencial del equipo y el código de 8 caracteres, por ejemplo 7K3M-Q9TX.')
    cuerpo = json.dumps({'identifier': identificador, 'credential': credencial, 'code': codigo}).encode()
    peticion = urllib.request.Request(url, data=cuerpo, method='POST', headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            return json.load(respuesta)['result']
    except urllib.error.HTTPError as fallo:
        sys.exit(f'El servidor rechazó la vinculación (HTTP {fallo.code}).')
    except urllib.error.URLError:
        sys.exit(f'No se pudo conectar con {url}. ¿Está encendido el servidor?')


def equipo(con, identificador):
    fila = con.execute('SELECT id, huerto_id, conexion, firmware_version FROM dispositivo WHERE identificador = %s', [identificador]).fetchone()
    if fila is None or fila[1] is None:
        sys.exit(f'El equipo {identificador} no existe o no está vinculado a un huerto.')
    return {'id': fila[0], 'huerto': fila[1], 'conexion': fila[2], 'firmware': fila[3]}


def marcar_simulado(con, dispositivo):
    con.execute("INSERT INTO dispositivo_evento (dispositivo_id, huerto_id, tipo, detalle) VALUES (%s, %s, 'reinicio', 'simulador')",
                [dispositivo['id'], dispositivo['huerto']])


def conexion(con, dispositivo, estado):
    """La base escribe sola los eventos «conectado» y «desconectado» y avisa al dueño."""
    con.execute('UPDATE dispositivo SET conexion = %s, ultima_conexion_en = now() WHERE id = %s', [estado, dispositivo['id']])
    if estado == 'en_linea' and not dispositivo['firmware']:
        con.execute('UPDATE dispositivo SET firmware_version = %s WHERE id = %s', [FIRMWARE, dispositivo['id']])


def medir(con, dispositivo, cuantas=1, intervalo=60, luz=False, sin_agua=False, azar=None, hace=0.0):
    """Inserta `cuantas` mediciones con sus 3 plantas; la última es de hace `hace` horas (0: ahora) y las anteriores,
    hacia atrás cada `intervalo` s."""
    azar = azar or random.Random()
    for indice in range(cuantas):
        atras = round(hace * 3600) + (cuantas - 1 - indice) * intervalo
        medicion = con.execute(
            'INSERT INTO medicion (dispositivo_id, huerto_id, medida_en, temperatura_c, humedad_aire_pct, luz_lux, deposito_con_agua) '
            "VALUES (%s, %s, now() - make_interval(secs => %s), %s, %s, %s, %s) RETURNING id",
            [dispositivo['id'], dispositivo['huerto'], atras, round(azar.uniform(24, 31), 1), round(azar.uniform(50, 72), 1),
             round(azar.uniform(800, 1500), 1) if luz else None, not sin_agua]).fetchone()[0]
        for planta in (1, 2, 3):
            humedad = round(azar.uniform(32, 68), 1)
            con.execute('INSERT INTO medicion_planta (medicion_id, planta_numero, humedad_sustrato_pct, adc_crudo) VALUES (%s, %s, %s, %s)',
                        [medicion, planta, humedad, int(4095 - humedad * 30)])
    con.execute("SELECT chilito_resumir_mediciones(now() - interval '48 hours', now() + interval '1 hour')")


def _revisiones(falla):
    return [(componente, 'falla' if componente == falla else 'no_instalado' if componente in SIN_INSTALAR else 'correcto',
             'Simulado' if componente == falla else '') for componente in COMPONENTES]


def _completar_autodiagnostico(con, comando, falla):
    diagnostico = con.execute('SELECT id FROM autodiagnostico WHERE comando_id = %s', [comando]).fetchone()[0]
    for componente, resultado, detalle in _revisiones(falla):
        con.execute('INSERT INTO autodiagnostico_revision (autodiagnostico_id, componente, resultado, detalle) VALUES (%s, %s, %s, %s)',
                    [diagnostico, componente, resultado, detalle])
    con.execute("UPDATE autodiagnostico SET estado = 'completado' WHERE id = %s", [diagnostico])


def _actuar(con, dispositivo, orden):
    comando, tipo, planta, duracion, origen = orden
    if tipo in ('regar', 'probar_bomba'):
        actuador, accion = 'bomba', 'encendido'
    elif tipo in ACTUADOR_POR_ORDEN:
        actuador, accion = ACTUADOR_POR_ORDEN[tipo]
    else:
        return
    con.execute('INSERT INTO actuacion (dispositivo_id, huerto_id, actuador, planta_numero, accion, duracion_s, origen, comando_id, ocurrido_en) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())',
                [dispositivo['id'], dispositivo['huerto'], actuador, planta if actuador == 'bomba' else None, accion,
                 duracion, origen, comando])


def atender(con, dispositivo, pausa=2.0, falla=None, fallar=()):
    """Responde las órdenes pendientes: enviada, una pausa visible y luego confirmada o fallida. Devuelve cuántas atendió."""
    ordenes = con.execute("SELECT id, tipo, planta_numero, duracion_s, origen FROM comando WHERE dispositivo_id = %s AND estado = 'pendiente' "
                          'ORDER BY creado_en', [dispositivo['id']]).fetchall()
    for orden in ordenes:
        comando, tipo = orden[0], orden[1]
        con.execute("UPDATE comando SET estado = 'enviado' WHERE id = %s", [comando])
        time.sleep(pausa)
        if tipo in fallar:
            con.execute("UPDATE comando SET estado = 'fallido', detalle_error = 'Falla simulada' WHERE id = %s", [comando])
            continue
        if tipo == 'autodiagnostico':
            _completar_autodiagnostico(con, comando, falla)
        _actuar(con, dispositivo, orden)
        con.execute("UPDATE comando SET estado = 'confirmado' WHERE id = %s", [comando])
    return len(ordenes)


def correr(con, dispositivo, cada=10.0, ciclos=None, **opciones):
    """Mantiene el equipo en línea: una medición y las órdenes pendientes en cada ciclo, hasta Ctrl+C o `ciclos`."""
    conexion(con, dispositivo, 'en_linea')
    hechos = 0
    while ciclos is None or hechos < ciclos:
        medir(con, dispositivo, luz=opciones.get('luz', False), sin_agua=opciones.get('sin_agua', False))
        atender(con, dispositivo, pausa=opciones.get('pausa', 2.0), falla=opciones.get('falla'), fallar=opciones.get('fallar', ()))
        hechos += 1
        if ciclos is None or hechos < ciclos:
            time.sleep(cada)


def leer_argumentos(argv=None):
    analizador = argparse.ArgumentParser(description='Simula un equipo El Chilito (solo desarrollo).')
    analizador.add_argument('identificador')
    analizador.add_argument('accion', choices=('vincular', 'conectar', 'desconectar', 'medir', 'atender', 'correr'))
    analizador.add_argument('--n', type=int, default=1, help='mediciones a insertar (medir)')
    analizador.add_argument('--intervalo', type=int, default=60, help='segundos entre mediciones hacia atrás (medir)')
    analizador.add_argument('--luz', action='store_true', help='incluye lecturas del sensor de luz')
    analizador.add_argument('--sin-agua', action='store_true', help='el flotador marca nivel bajo (medir y correr)')
    analizador.add_argument('--hace', type=float, default=0.0, help='horas hacia atrás de la última medición (medir; máximo 168)')
    analizador.add_argument('--pausa', type=float, default=2.0, help='segundos en «enviada» antes de responder')
    analizador.add_argument('--falla', choices=COMPONENTES, help='componente que falla en el autodiagnóstico')
    analizador.add_argument('--fallar', action='append', default=[], help='tipo de orden que se responde como fallida')
    analizador.add_argument('--cada', type=float, default=10.0, help='segundos entre ciclos (correr)')
    analizador.add_argument('--ciclos', type=int, help='ciclos a ejecutar (correr); sin valor, hasta Ctrl+C')
    return analizador.parse_args(argv)


def main(argv=None):
    argumentos = leer_argumentos(argv)
    if argumentos.accion == 'vincular':
        print(f'Resultado: {vincular(argumentos.identificador)}')
        return
    with psycopg.connect(**exigir_entorno()) as con:
        dispositivo = equipo(con, argumentos.identificador)
        marcar_simulado(con, dispositivo)
        if argumentos.accion in ('conectar', 'desconectar'):
            conexion(con, dispositivo, 'en_linea' if argumentos.accion == 'conectar' else 'desconectado')
        elif argumentos.accion == 'medir':
            if not 0 <= argumentos.hace <= 168:
                sys.exit('--hace va de 0 a 168 horas (7 días).')
            medir(con, dispositivo, argumentos.n, argumentos.intervalo, argumentos.luz, argumentos.sin_agua, hace=argumentos.hace)
        elif argumentos.accion == 'atender':
            print(f'Órdenes atendidas: {atender(con, dispositivo, argumentos.pausa, argumentos.falla, tuple(argumentos.fallar))}')
        else:
            try:
                correr(con, dispositivo, argumentos.cada, argumentos.ciclos, luz=argumentos.luz, sin_agua=argumentos.sin_agua, pausa=argumentos.pausa,
                       falla=argumentos.falla, fallar=tuple(argumentos.fallar))
            except KeyboardInterrupt:
                print('Simulación detenida.')


if __name__ == '__main__':
    main()

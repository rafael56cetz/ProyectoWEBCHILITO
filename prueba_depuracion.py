"""Pruebas de la base El Chilito v2: flujos completos y reglas, con los tres roles.
Se ejecuta sobre una base recién instalada. Cada caso es una transacción: los que deben fallar se deshacen."""
import sys, hashlib, psycopg

# Base de PRUEBAS recién instalada (nunca la de trabajo: las pruebas escriben datos).
# Variables: CHILITO_PRUEBAS_DB, CHILITO_PRUEBAS_HOST, CHILITO_PRUEBAS_PUERTO y, si tu servidor pide contraseña,
# CHILITO_PRUEBAS_CLAVE_OWNER, CHILITO_PRUEBAS_CLAVE_RUNTIME y CHILITO_PRUEBAS_CLAVE_IOT.
import os
DB = os.environ.get("CHILITO_PRUEBAS_DB", "chilito_pruebas")
HOST = os.environ.get("CHILITO_PRUEBAS_HOST", "localhost")
PUERTO = int(os.environ.get("CHILITO_PRUEBAS_PUERTO", "5432"))
if "prueba" not in DB and "test" not in DB:
    sys.exit(f"Por seguridad, el nombre de la base debe contener «prueba» o «test» (recibido: {DB}).")
OK, FALLOS = [], []

def con(rol):
    clave = os.environ.get("CHILITO_PRUEBAS_CLAVE_" + rol.rsplit("_", 1)[1].upper())
    return psycopg.connect(host=HOST, port=PUERTO, dbname=DB, user=rol, password=clave)

def _run(rol, sqls, actor):
    c = con(rol)
    try:
        with c.transaction():
            cur = c.cursor()
            if actor is not None:
                cur.execute("SELECT set_config('chilito.actor_id', %s, true)", (str(actor),))
            res = None
            for s in sqls:
                if isinstance(s, tuple):
                    cur.execute(s[0], s[1])
                else:
                    cur.execute(s)
                if cur.description:
                    res = cur.fetchall()
            return res
    finally:
        c.close()

def bien(desc, rol, sqls, actor=None, espera=None):
    try:
        r = _run(rol, sqls if isinstance(sqls, list) else [sqls], actor)
        if espera is not None and r != espera:
            FALLOS.append(f"{desc}: esperaba {espera}, obtuvo {r}"); return r
        OK.append(desc); return r
    except Exception as e:
        FALLOS.append(f"{desc}: error inesperado → {str(e).splitlines()[0]}")

def mal(desc, rol, sqls, actor=None, contiene=None):
    try:
        _run(rol, sqls if isinstance(sqls, list) else [sqls], actor)
        FALLOS.append(f"{desc}: debía fallar y se aceptó")
    except Exception as e:
        msg = str(e)
        if contiene and contiene.lower() not in msg.lower():
            FALLOS.append(f"{desc}: falló por otro motivo → {msg.splitlines()[0]}")
        else:
            OK.append(desc)

def uno(rol, sql, actor=None):
    return _run(rol, [sql], actor)[0][0]

h = lambda t: hashlib.sha256(t.encode()).hexdigest()

def registrar(correo, aceptar=True, verificado=True):
    sqls = [f"INSERT INTO cuentas_usuario(password,email) VALUES ('pbkdf2_sha256$x','{correo}')",
            f"INSERT INTO account_emailaddress(email,verified,\"primary\",user_id) SELECT '{correo}',{str(verificado).lower()},true,id FROM cuentas_usuario WHERE email='{correo}'",
            f"INSERT INTO privacidad_sujeto(ambito,usuario_id) SELECT 'cuenta',id FROM cuentas_usuario WHERE email='{correo}'"]
    if aceptar:
        for acto, tipo in [("aceptacion_terminos", "terminos"), ("lectura_aviso", "aviso_privacidad")]:
            sqls.append(f"""INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,usuario_id,ip_recortada,navegador)
              SELECT s.id,'{acto}',true,chilito_documento_vigente('{tipo}'),s.usuario_id,'189.203.45.0','Chrome 130 · Android'
              FROM privacidad_sujeto s JOIN cuentas_usuario u ON u.id=s.usuario_id WHERE u.email='{correo}'""")
    sqls.append(f"SELECT id FROM cuentas_usuario WHERE email='{correo}'")
    return sqls

BEA = bien("Registro Bea", "chilito_pkg_runtime", registrar("bea@example.com"))[0][0]
HB = bien("Huerto Bea", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id) VALUES ({BEA}) RETURNING id", actor=BEA)[0][0]
bien("Vincula ESP32-0004", "chilito_pkg_runtime", [f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({HB},{BEA},'{h('B1')}')",
     f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0004','{h('B1')}')"], actor=BEA, espera=[("vinculado",)])
D4 = uno("chilito_pkg_owner", "SELECT id FROM dispositivo WHERE identificador='ESP32-0004'")
bien("Medición de hace 100 días", "chilito_pkg_iot", [f"INSERT INTO medicion(dispositivo_id,huerto_id,medida_en,temperatura_c) VALUES ({D4},{HB},now()-interval '100 days',30) RETURNING id"])
M = uno("chilito_pkg_owner", "SELECT max(id) FROM medicion")
bien("Su planta", "chilito_pkg_iot", f"INSERT INTO medicion_planta VALUES ({M},1,40)")
r = bien("Tarea periódica", "chilito_pkg_owner", "SELECT chilito_mantenimiento_periodico()")
print(r)
bien("Detalle borrado y resumen conservado", "chilito_pkg_owner",
     f"SELECT (SELECT count(*) FROM medicion WHERE huerto_id={HB}), (SELECT count(*) FROM resumen_hora_huerto WHERE huerto_id={HB}), (SELECT count(*) FROM resumen_hora_planta WHERE huerto_id={HB})", espera=[(0,1,1)])
print(len(OK), FALLOS)

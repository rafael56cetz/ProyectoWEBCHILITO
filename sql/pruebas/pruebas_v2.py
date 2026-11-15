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

# ------------------------------------------------------------------------------------------------ LEGAL
mal("Registro imposible sin textos legales publicados", "chilito_pkg_runtime", [
    "INSERT INTO cuentas_usuario(password,email) VALUES ('x','sinlegal@example.com')"], contiene="publícalos")
for tipo, tit in [("terminos", "Términos"), ("aviso_privacidad", "Aviso de privacidad"), ("politica_cookies", "Política de cookies")]:
    bien(f"Owner publica {tipo} 1.0", "chilito_pkg_owner",
         f"SELECT chilito_publicar_documento_legal('{tipo}','1.0','{tit}','Texto de prueba de {tit}.')")
mal("Runtime no puede usar la función de publicar de pgAdmin", "chilito_pkg_runtime",
    "SELECT chilito_publicar_documento_legal('terminos','9.0','x','x')", contiene="permission denied")

# --------------------------------------------------------------------------------------------- REGISTRO
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

mal("Registro sin aceptar términos ni aviso se rechaza al confirmar", "chilito_pkg_runtime", registrar("nadie@example.com", aceptar=False), contiene="aceptar los términos")
SUPER = bien("Registro completo (super admin)", "chilito_pkg_runtime", registrar("rafael.admin@gmail.com"))[0][0]
ANA = bien("Registro completo (Ana)", "chilito_pkg_runtime", registrar("ana@example.com"))[0][0]
LUIS = bien("Registro completo (Luis, admin de soporte)", "chilito_pkg_runtime", registrar("luis@example.com"))[0][0]
PEPE = bien("Registro completo (Pepe, sin verificar)", "chilito_pkg_runtime", registrar("pepe@example.com", verificado=False))[0][0]
mal("Cuenta duplicada por variante de Gmail", "chilito_pkg_runtime", registrar("Rafael.Admin+huerto@googlemail.com"), contiene="usuario_identidad_correo_unica")
mal("Runtime no crea cuentas staff/superusuario", "chilito_pkg_runtime",
    "INSERT INTO cuentas_usuario(password,email,is_staff) VALUES ('x','staff@example.com',true)", contiene="usuario_sin_privilegios_django")
mal("Runtime no puede desactivar cuentas (privilegio de columna)", "chilito_pkg_runtime",
    f"UPDATE cuentas_usuario SET is_active=false WHERE id={ANA}", contiene="permission denied")
mal("Las cuentas no se borran", "chilito_pkg_owner", f"DELETE FROM cuentas_usuario WHERE id={PEPE}", contiene="anonimizan")

# ------------------------------------------------------------------------------------------- CAPACIDADES
bien("Owner nombra super admin con la función", "chilito_pkg_owner", "SELECT chilito_designar_super_admin('rafael.admin@gmail.com')")
bien("Historial registra las 10 concesiones desde pgAdmin", "chilito_pkg_owner",
     f"SELECT count(*) FROM capacidad_historial WHERE usuario_id={SUPER} AND realizada_por_id IS NULL AND accion='concedida'", espera=[(10,)])
mal("No se dan capacidades a cuentas sin correo verificado", "chilito_pkg_owner",
    "SELECT chilito_conceder_capacidad('pepe@example.com','ver_flota')", contiene="verificado")
bien("Super admin da atender_soporte a Luis desde el panel", "chilito_pkg_runtime", [
    "SELECT set_config('chilito.motivo','Encargado de soporte',true)",
    f"INSERT INTO cuentas_usuario_user_permissions(usuario_id,permission_id) SELECT {LUIS},id FROM auth_permission WHERE codename='atender_soporte'"], actor=SUPER)
bien("Historial guarda quién lo dio y el motivo", "chilito_pkg_owner",
     f"SELECT realizada_por_id, motivo FROM capacidad_historial WHERE usuario_id={LUIS}", espera=[(SUPER, "Encargado de soporte")])
mal("Desde el panel no se da la capacidad de super admin", "chilito_pkg_runtime",
    f"INSERT INTO cuentas_usuario_user_permissions(usuario_id,permission_id) SELECT {LUIS},id FROM auth_permission WHERE codename='gestionar_administradores'", actor=SUPER, contiene="pgAdmin")
mal("Nadie cambia sus propias capacidades", "chilito_pkg_runtime",
    f"DELETE FROM cuentas_usuario_user_permissions WHERE usuario_id={SUPER}", actor=SUPER, contiene="propias")
mal("Sin actor no se dan capacidades", "chilito_pkg_runtime",
    f"INSERT INTO cuentas_usuario_user_permissions(usuario_id,permission_id) SELECT {ANA},id FROM auth_permission WHERE codename='ver_flota'", contiene="super administrador")
mal("Un admin que no es super admin no da capacidades", "chilito_pkg_runtime",
    f"INSERT INTO cuentas_usuario_user_permissions(usuario_id,permission_id) SELECT {ANA},id FROM auth_permission WHERE codename='ver_flota'", actor=LUIS, contiene="super administrador")
mal("No se puede quitar el último super admin", "chilito_pkg_owner", "SELECT chilito_retirar_super_admin('rafael.admin@gmail.com')", contiene="al menos un super")
bien("Vista de administradores", "chilito_pkg_runtime", "SELECT email, es_super_admin FROM v_administradores ORDER BY email",
     espera=[("luis@example.com", False), ("rafael.admin@gmail.com", True)])

# ------------------------------------------------------------------------------------------------ HUERTOS
H1 = bien("Ana crea su huerto (nombre por defecto)", "chilito_pkg_runtime",
          f"INSERT INTO huerto(propietario_id) VALUES ({ANA}) RETURNING id", actor=ANA)[0][0]
bien("El huerto nace con 3 plantas y zona America/Merida", "chilito_pkg_runtime",
     f"SELECT count(*), min(h.zona_horaria) FROM huerto_planta p JOIN huerto h ON h.id=p.huerto_id WHERE h.id={H1}", espera=[(3, "America/Merida")])
mal("Solo un huerto sin equipo a la vez", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id) VALUES ({ANA})", actor=ANA, contiene="sin equipo")
mal("Nadie crea huertos para otra cuenta", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id) VALUES ({ANA})", actor=LUIS, contiene="propios")
mal("Zona horaria fuera de Yucatán", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id,zona_horaria) VALUES ({LUIS},'America/Mexico_City')", actor=LUIS, contiene="huerto_solo_yucatan")
bien("Ana renombra planta y cambia su etapa", "chilito_pkg_runtime",
     f"UPDATE huerto_planta SET nombre='Chilito feliz', fecha_siembra=current_date-10, etapa='germinacion' WHERE huerto_id={H1} AND numero=1", actor=ANA)
bien("El cambio de etapa queda en el historial", "chilito_pkg_runtime",
     f"SELECT e.etapa FROM huerto_planta_etapa e JOIN huerto_planta p ON p.id=e.planta_id WHERE p.huerto_id={H1}", espera=[("germinacion",)])
mal("Fecha de siembra futura", "chilito_pkg_runtime",
    f"UPDATE huerto_planta SET fecha_siembra=current_date+5 WHERE huerto_id={H1} AND numero=2", actor=ANA, contiene="futura")
mal("Otra cuenta no cambia las plantas de Ana", "chilito_pkg_runtime",
    f"UPDATE huerto_planta SET nombre='Mía' WHERE huerto_id={H1} AND numero=2", actor=LUIS, contiene="propia cuenta")

# ------------------------------------------------------------------------------------------ DISPOSITIVOS
mal("Sin «gestionar_dispositivos» no se dan de alta equipos", "chilito_pkg_runtime",
    f"INSERT INTO dispositivo(identificador,mac,credencial_hash,registrado_por_id) VALUES ('ESP32-0001','AA:BB:CC:00:00:01','{h('c1')}',{LUIS})", actor=LUIS, contiene="gestionar_dispositivos")
for i in range(1, 5):
    bien(f"Admin da de alta ESP32-000{i}", "chilito_pkg_runtime",
         f"INSERT INTO dispositivo(identificador,mac,credencial_hash,registrado_por_id) VALUES ('ESP32-000{i}','AA:BB:CC:00:00:0{i}','pbkdf2_sha512${h('cred'+str(i))}',{SUPER})", actor=SUPER)
D1 = uno("chilito_pkg_owner", "SELECT id FROM dispositivo WHERE identificador='ESP32-0001'")
bien("El alta queda en el historial del equipo", "chilito_pkg_owner", f"SELECT tipo FROM dispositivo_evento WHERE dispositivo_id={D1}", espera=[("alta",)])
mal("Vincular a mano sin código", "chilito_pkg_runtime", f"UPDATE dispositivo SET estado='vinculado', huerto_id={H1}, vinculado_en=now() WHERE id={D1}", actor=ANA, contiene="código")

# ------------------------------------------------------------------------------------------- VINCULACIÓN
COD = "AC-729184"
bien("Ana genera su código de vinculación", "chilito_pkg_runtime",
     f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({H1},{ANA},'{h(COD)}')", actor=ANA)
mal("Un solo código pendiente por huerto", "chilito_pkg_runtime",
    f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({H1},{ANA},'{h('otro')}')", actor=ANA, contiene="codigo_pendiente_por_huerto")
mal("Solo el dueño genera códigos de su huerto", "chilito_pkg_runtime",
    f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({H1},{LUIS},'{h('x')}')", actor=LUIS, contiene="dueño")
bien("ESP32 presenta un código incorrecto", "chilito_pkg_runtime", f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0001','{h('malo')}')", espera=[("codigo_invalido",)])
bien("ESP32 desconocido con código válido", "chilito_pkg_runtime", f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-9999','{h(COD)}')", espera=[("dispositivo_desconocido",)])
bien("ESP32 presenta el código correcto → vinculado", "chilito_pkg_runtime", f"SELECT resultado, huerto_id FROM chilito_vincular_dispositivo('ESP32-0001','{h(COD)}')", espera=[("vinculado", H1)])
bien("Equipo vinculado, evento y aviso a Ana", "chilito_pkg_owner",
     f"""SELECT d.estado, (SELECT count(*) FROM dispositivo_evento WHERE dispositivo_id={D1} AND tipo='vinculado'),
         (SELECT count(*) FROM notificacion WHERE destinatario_id={ANA} AND origen='vinculacion') FROM dispositivo d WHERE id={D1}""", espera=[("vinculado", 1, 1)])
bien("Reutilizar el código", "chilito_pkg_runtime", f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0001','{h(COD)}')", espera=[("codigo_usado",)])
mal("El servicio IoT no puede vincular", "chilito_pkg_iot", f"SELECT chilito_vincular_dispositivo('ESP32-0002','{h(COD)}')", contiene="permission denied")

H2 = bien("Con el primero vinculado, Ana crea un 2.º huerto", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id,nombre) VALUES ({ANA},'Huerto de la terraza') RETURNING id", actor=ANA)[0][0]
bien("Código para el 2.º huerto", "chilito_pkg_runtime", f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({H2},{ANA},'{h('C2')}')", actor=ANA)
bien("Equipo ocupado: ESP32-0001 ya es de otro huerto", "chilito_pkg_runtime", f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0001','{h('C2')}')", espera=[("dispositivo_ocupado",)])
bien("ESP32-0002 al 2.º huerto", "chilito_pkg_runtime", f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0002','{h('C2')}')", espera=[("vinculado",)])
H3 = bien("3.er huerto", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id) VALUES ({ANA}) RETURNING id", actor=ANA)[0][0]
bien("Código y equipo para el 3.er huerto", "chilito_pkg_runtime", [
    f"INSERT INTO codigo_vinculacion(huerto_id,generado_por_id,codigo_hash) VALUES ({H3},{ANA},'{h('C3')}')",
    f"SELECT resultado FROM chilito_vincular_dispositivo('ESP32-0003','{h('C3')}')"], actor=ANA, espera=[("vinculado",)])
mal("Máximo 3 huertos activos", "chilito_pkg_runtime", f"INSERT INTO huerto(propietario_id) VALUES ({ANA})", actor=ANA, contiene="Máximo 3")

# --------------------------------------------------------------------------------------------- TELEMETRÍA
bien("IoT guarda una medición con las 3 plantas", "chilito_pkg_iot", [
    f"INSERT INTO medicion(dispositivo_id,huerto_id,medida_en,temperatura_c,humedad_aire_pct,luz_lux,deposito_con_agua) VALUES ({D1},{H1},now()-interval '2 minutes',29.5,71.2,18000,true) RETURNING id"])
MED = uno("chilito_pkg_owner", "SELECT max(id) FROM medicion")
bien("IoT guarda la humedad de cada planta", "chilito_pkg_iot",
     f"INSERT INTO medicion_planta(medicion_id,planta_numero,humedad_sustrato_pct,adc_crudo) VALUES ({MED},1,41.0,2710),({MED},2,38.5,2802),({MED},3,55.0,2190)")
mal("Medición de un equipo en un huerto ajeno", "chilito_pkg_iot",
    f"INSERT INTO medicion(dispositivo_id,huerto_id,medida_en) VALUES ({D1},{H2},now())", contiene="no está vinculado")
mal("Medición con valor imposible", "chilito_pkg_iot",
    f"INSERT INTO medicion(dispositivo_id,huerto_id,medida_en,humedad_aire_pct) VALUES ({D1},{H1},now(),140)", contiene="medicion_humedad_rango")
bien("IoT marca el equipo en línea → evento «conectado»", "chilito_pkg_iot", [
    f"UPDATE dispositivo SET conexion='en_linea', ultima_conexion_en=now(), firmware_version='1.0.3' WHERE id={D1}",
    f"SELECT count(*) FROM dispositivo_evento WHERE dispositivo_id={D1} AND tipo IN ('conectado','firmware_actualizado')"], espera=[(2,)])
mal("IoT no puede desvincular equipos", "chilito_pkg_iot", f"UPDATE dispositivo SET estado='disponible' WHERE id={D1}", contiene="permission denied")
mal("IoT no ve cuentas", "chilito_pkg_iot", "SELECT email FROM cuentas_usuario", contiene="permission denied")
mal("Las mediciones no se modifican", "chilito_pkg_owner", f"UPDATE medicion SET temperatura_c=10 WHERE id={MED}", contiene="inmutable")
mal("Ni el propietario borra mediciones recientes", "chilito_pkg_owner", f"DELETE FROM medicion WHERE id={MED}", contiene="inmutable")
bien("IoT reporta un riego automático de la planta 2 (8 s)", "chilito_pkg_iot",
     f"INSERT INTO actuacion(dispositivo_id,huerto_id,actuador,planta_numero,accion,duracion_s,origen,ocurrido_en) VALUES ({D1},{H1},'bomba',2,'encendido',8,'automatico',now())")
mal("Riego sin planta", "chilito_pkg_iot",
    f"INSERT INTO actuacion(dispositivo_id,huerto_id,actuador,accion,origen,ocurrido_en) VALUES ({D1},{H1},'bomba','encendido','automatico',now())", contiene="actuacion_planta_si_bomba")
bien("IoT avisa a Ana: depósito sin agua", "chilito_pkg_iot",
     f"INSERT INTO notificacion(destinatario_id,origen,severidad,titulo,huerto_id,enlace) VALUES ({ANA},'dispositivo','critico','Depósito sin agua',{H1},'#avisos')")
mal("IoT no avisa a quien no es dueño", "chilito_pkg_iot",
    f"INSERT INTO notificacion(destinatario_id,origen,titulo,huerto_id) VALUES ({LUIS},'dispositivo','x',{H1})", contiene="dueño")
bien("IA escribe un resumen del huerto", "chilito_pkg_iot",
     f"INSERT INTO ia_resumen(huerto_id,contenido,modelo,datos_hasta) VALUES ({H1},'Tus plantas se regaron bien; el depósito necesita agua.','gemini-prueba',now())")
bien("Resumen por hora (IoT puede ejecutarlo)", "chilito_pkg_iot", "SELECT chilito_resumir_mediciones(now()-interval '1 day', now()+interval '1 hour')", espera=[(4,)])

# ------------------------------------------------------------------------------------------------ COMANDOS
C1 = bien("Ana pide regar la planta 2 por 8 s", "chilito_pkg_runtime",
          f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,planta_numero,duracion_s,origen,solicitado_por_id) VALUES ({H1},{D1},'regar',2,8,'usuario',{ANA}) RETURNING id", actor=ANA)[0][0]
mal("No se repite una orden igual sin resolver", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,planta_numero,duracion_s,origen,solicitado_por_id) VALUES ({H1},{D1},'regar',2,8,'usuario',{ANA})", actor=ANA, contiene="comando_uno_en_curso")
mal("Regar sin indicar planta", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id) VALUES ({H1},{D1},'regar','usuario',{ANA})".replace("tipo,origen","tipo,duracion_s,origen").replace("'regar','usuario'","'regar',8,'usuario'"), actor=ANA, contiene="comando_planta_por_tipo")
mal("El usuario no puede reiniciar el equipo", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id) VALUES ({H1},{D1},'reiniciar','usuario',{ANA})", actor=ANA, contiene="comando_tipo_por_origen")
mal("Otra cuenta no da órdenes al huerto de Ana", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id) VALUES ({H1},{D1},'lampara_apagar','usuario',{LUIS})", actor=LUIS, contiene="dueño")
bien("IoT marca la orden enviada y luego confirmada", "chilito_pkg_iot", [
    f"UPDATE comando SET estado='enviado' WHERE id='{C1}'", f"UPDATE comando SET estado='confirmado' WHERE id='{C1}'",
    f"SELECT estado, enviado_en IS NOT NULL, resuelto_en IS NOT NULL FROM comando WHERE id='{C1}'"], espera=[("confirmado", True, True)])
mal("Una orden confirmada no vuelve atrás", "chilito_pkg_iot", f"UPDATE comando SET estado='enviado' WHERE id='{C1}'", contiene="Transición")
bien("Ana apaga la lámpara", "chilito_pkg_runtime",
     f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id) VALUES ({H1},{D1},'lampara_apagar','usuario',{ANA})", actor=ANA)

# ----------------------------------------------------------------------------------------- AUTODIAGNÓSTICO
CA = bien("Ana pulsa «Revisar mi equipo»", "chilito_pkg_runtime",
          f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id) VALUES ({H1},{D1},'autodiagnostico','usuario',{ANA}) RETURNING id", actor=ANA)[0][0]
AD = uno("chilito_pkg_owner", f"SELECT id FROM autodiagnostico WHERE comando_id='{CA}'")
mal("No se crean autodiagnósticos sueltos", "chilito_pkg_owner",
    f"INSERT INTO autodiagnostico(huerto_id,dispositivo_id,comando_id,solicitado_por_id) VALUES ({H1},{D1},'{C1}',{ANA})", contiene="comando")
bien("IoT reporta revisiones (bomba 3 falla)", "chilito_pkg_iot",
     f"""INSERT INTO autodiagnostico_revision(autodiagnostico_id,componente,resultado) VALUES
       ('{AD}','conexion','correcto'),('{AD}','sensor_ambiente','correcto'),('{AD}','flotador','correcto'),('{AD}','bomba_3','falla')""")
bien("Al completar, la base calcula «con_fallas»", "chilito_pkg_iot", [
    f"UPDATE autodiagnostico SET estado='completado' WHERE id='{AD}'",
    f"SELECT resultado_general FROM autodiagnostico WHERE id='{AD}'"], espera=[("con_fallas",)])
mal("No se añaden revisiones a un autodiagnóstico cerrado", "chilito_pkg_iot",
    f"INSERT INTO autodiagnostico_revision(autodiagnostico_id,componente,resultado) VALUES ('{AD}','lampara','correcto')", contiene="cerrado")

# --------------------------------------------------------------------------------------------- SOPORTE
CASO = bien("Ana solicita revisión técnica con autorización 24 h", "chilito_pkg_runtime",
            f"INSERT INTO soporte_caso(huerto_id,dispositivo_id,solicitante_id,incidente,nota,autodiagnostico_id,consentimiento) VALUES ({H1},{D1},{ANA},'bomba','La bomba 3 no riega','{AD}',true) RETURNING id", actor=ANA)[0][0]
bien("Folio CS-…, correo al buzón y aviso a Luis", "chilito_pkg_owner",
     f"""SELECT folio LIKE 'CS-%', (SELECT count(*) FROM correo_pendiente WHERE caso_id='{CASO}'),
         (SELECT count(*) FROM notificacion WHERE destinatario_id={LUIS} AND origen='soporte') FROM soporte_caso WHERE id='{CASO}'""", espera=[(True, 1, 1)])
mal("Un solo caso activo por huerto", "chilito_pkg_runtime",
    f"INSERT INTO soporte_caso(huerto_id,dispositivo_id,solicitante_id,incidente,consentimiento) VALUES ({H1},{D1},{ANA},'otro',true)", actor=ANA, contiene="caso_uno_activo_por_huerto")
mal("Sin consentimiento no hay caso", "chilito_pkg_runtime",
    f"INSERT INTO soporte_caso(huerto_id,dispositivo_id,solicitante_id,incidente,consentimiento) VALUES ({H2},(SELECT id FROM dispositivo WHERE identificador='ESP32-0002'),{ANA},'otro',false)", actor=ANA, contiene="caso_consentimiento_explicito")
mal("Conectar sin haber tomado el caso", "chilito_pkg_runtime",
    f"INSERT INTO soporte_sesion(caso_id,administrador_id) VALUES ('{CASO}',{LUIS})", actor=LUIS, contiene="autorización vigente")
mal("Una cuenta sin «atender_soporte» no atiende", "chilito_pkg_runtime",
    f"UPDATE soporte_caso SET estado='en_atencion', atendido_por_id={ANA} WHERE id='{CASO}'", actor=ANA, contiene="atender_soporte")
bien("Luis pulsa «Atender»", "chilito_pkg_runtime", f"UPDATE soporte_caso SET estado='en_atencion', atendido_por_id={LUIS} WHERE id='{CASO}'", actor=LUIS)
SES = bien("Luis pulsa «Conectar»", "chilito_pkg_runtime", f"INSERT INTO soporte_sesion(caso_id,administrador_id) VALUES ('{CASO}',{LUIS}) RETURNING id", actor=LUIS)[0][0]
bien("Luis prueba la bomba 3 dentro de la sesión", "chilito_pkg_runtime",
     f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,planta_numero,duracion_s,origen,solicitado_por_id,sesion_id) VALUES ({H1},{D1},'probar_bomba',3,3,'soporte',{LUIS},'{SES}')", actor=LUIS)
mal("Orden de soporte en otro huerto", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id,sesion_id) VALUES ({H2},(SELECT id FROM dispositivo WHERE identificador='ESP32-0002'),'reiniciar','soporte',{LUIS},'{SES}')", actor=LUIS, contiene="sesión técnica")
bien("Ana revoca el acceso → la sesión se cierra sola", "chilito_pkg_runtime", [
    f"UPDATE soporte_caso SET autorizacion_revocada_en=now() WHERE id='{CASO}'",
    f"SELECT motivo_cierre FROM soporte_sesion WHERE id='{SES}'"], actor=ANA, espera=[("revocada",)])
mal("Tras revocar, Luis ya no da órdenes", "chilito_pkg_runtime",
    f"INSERT INTO comando(huerto_id,dispositivo_id,tipo,origen,solicitado_por_id,sesion_id) VALUES ({H1},{D1},'reiniciar','soporte',{LUIS},'{SES}')", actor=LUIS, contiene="sesión técnica")
mal("Tras revocar, Luis no puede reconectar", "chilito_pkg_runtime",
    f"INSERT INTO soporte_sesion(caso_id,administrador_id) VALUES ('{CASO}',{LUIS})", actor=LUIS, contiene="autorización vigente")
mal("La revocación no se deshace", "chilito_pkg_owner", f"UPDATE soporte_caso SET autorizacion_revocada_en=NULL WHERE id='{CASO}'", contiene="vuelta atrás")
bien("Luis resuelve el caso", "chilito_pkg_runtime", [
    f"UPDATE soporte_caso SET estado='resuelto', resultado='sin_respuesta' WHERE id='{CASO}'",
    f"SELECT estado, cerrado_en IS NOT NULL FROM soporte_caso WHERE id='{CASO}'"], actor=LUIS, espera=[("resuelto", True)])
mal("Un caso resuelto no cambia", "chilito_pkg_runtime", f"UPDATE soporte_caso SET estado='cancelado' WHERE id='{CASO}'", actor=ANA, contiene="cerrado")

# --------------------------------------------------------------------------------------------- CUIDADOS
mal("Rellenar depósito es del huerto, no de una planta", "chilito_pkg_runtime",
    f"INSERT INTO cuidado(huerto_id,planta_numero,tipo,registrado_por_id) VALUES ({H1},1,'rellenar_deposito',{ANA})", actor=ANA, contiene="cuidado_planta_por_tipo")
bien("Rellenar depósito (huerto)", "chilito_pkg_runtime", f"INSERT INTO cuidado(huerto_id,tipo,registrado_por_id) VALUES ({H1},'rellenar_deposito',{ANA})", actor=ANA)
CU = bien("Cosecha de la planta 1 con 12 chiles, hecha ayer", "chilito_pkg_runtime",
          f"INSERT INTO cuidado(huerto_id,planta_numero,tipo,chiles_cosechados,realizado_en,registrado_por_id) VALUES ({H1},1,'cosecha',12,now()-interval '1 day',{ANA}) RETURNING id", actor=ANA)[0][0]
mal("Cosecha sin planta", "chilito_pkg_runtime", f"INSERT INTO cuidado(huerto_id,tipo,registrado_por_id) VALUES ({H1},'cosecha',{ANA})", actor=ANA, contiene="cuidado_planta_por_tipo")
mal("Cuidado de hace 8 días", "chilito_pkg_runtime",
    f"INSERT INTO cuidado(huerto_id,tipo,realizado_en,registrado_por_id) VALUES ({H1},'inspeccion',now()-interval '8 days',{ANA})", actor=ANA, contiene="cuidado_fecha_realista")
mal("Un cuidado no se modifica", "chilito_pkg_owner", f"UPDATE cuidado SET chiles_cosechados=99 WHERE id='{CU}'", contiene="inmutable")
mal("Corregir sin «gestionar_mantenimientos»", "chilito_pkg_runtime",
    f"INSERT INTO cuidado_revision(cuidado_id,numero,tipo,tipo_corregido,planta_corregida,chiles_corregidos,motivo,editor_id) VALUES ('{CU}',1,'correccion','cosecha',1,10,'Conteo',{LUIS})", actor=LUIS, contiene="gestionar_mantenimientos")
bien("Super admin corrige la cosecha (10 chiles)", "chilito_pkg_runtime",
     f"INSERT INTO cuidado_revision(cuidado_id,numero,tipo,tipo_corregido,planta_corregida,chiles_corregidos,motivo,editor_id) VALUES ('{CU}',1,'correccion','cosecha',1,10,'Conteo corregido',{SUPER})", actor=SUPER)
mal("Revisión fuera de orden", "chilito_pkg_runtime",
    f"INSERT INTO cuidado_revision(cuidado_id,numero,tipo,motivo,editor_id) VALUES ('{CU}',3,'anulacion','x',{SUPER})", actor=SUPER, contiene="fuera de orden")
bien("Anulación", "chilito_pkg_runtime", f"INSERT INTO cuidado_revision(cuidado_id,numero,tipo,motivo,editor_id) VALUES ('{CU}',2,'anulacion','Duplicado',{SUPER})", actor=SUPER)
mal("Un cuidado anulado no admite más revisiones", "chilito_pkg_runtime",
    f"INSERT INTO cuidado_revision(cuidado_id,numero,tipo,tipo_corregido,motivo,editor_id) VALUES ('{CU}',3,'correccion','inspeccion','x',{SUPER})", actor=SUPER, contiene="anulado")

# ------------------------------------------------------------------------------------------------- GUÍAS
mal("Las guías no se borran", "chilito_pkg_owner", "DELETE FROM guia_cuidado WHERE clave='riego-revision'", contiene="retiran")
bien("Super admin retira una guía (versión +1)", "chilito_pkg_runtime",
     f"UPDATE guia_cuidado SET estado='retirada', version=version+1, actualizado_por_id={SUPER} WHERE clave='riego-revision'", actor=SUPER)
mal("Editar sin subir la versión", "chilito_pkg_runtime",
    f"UPDATE guia_cuidado SET orden=55, actualizado_por_id={SUPER} WHERE clave='riego-revision'", actor=SUPER, contiene="versión")

# ------------------------------------------------------------------------------------------------- LEGAL (panel)
DOC = bien("Super admin crea borrador de términos 1.1", "chilito_pkg_runtime",
           f"INSERT INTO documento_legal(tipo,version,titulo,contenido,contenido_sha256,creado_por_id) VALUES ('terminos','1.1','Términos','Texto nuevo','{'0'*64}',{SUPER}) RETURNING id", actor=SUPER)[0][0]
bien("La base calcula la huella SHA-256", "chilito_pkg_runtime", f"SELECT contenido_sha256 FROM documento_legal WHERE id='{DOC}'", espera=[(h('Texto nuevo'),)])
mal("Sin «gestionar_legales» no se editan textos", "chilito_pkg_runtime", f"UPDATE documento_legal SET titulo='x' WHERE id='{DOC}'", actor=LUIS, contiene="gestionar_legales")
bien("Publica términos 1.1 → aviso a todas las cuentas", "chilito_pkg_runtime", [
    f"UPDATE documento_legal SET estado='publicada' WHERE id='{DOC}'",
    "SELECT count(*) FROM notificacion WHERE origen='legal'"], actor=SUPER, espera=[(4,)])
mal("Una versión publicada no cambia", "chilito_pkg_runtime", f"UPDATE documento_legal SET contenido='otro' WHERE id='{DOC}'", actor=SUPER, contiene="publicada")
mal("No se publica una versión menor que la vigente", "chilito_pkg_runtime", [
    f"INSERT INTO documento_legal(tipo,version,titulo,contenido,contenido_sha256,creado_por_id) VALUES ('terminos','1.0.5','T','x','{'0'*64}',{SUPER})",
    "UPDATE documento_legal SET estado='publicada' WHERE version='1.0.5'"], actor=SUPER, contiene="mayor")
bien("Ana tiene pendiente aceptar términos 1.1", "chilito_pkg_runtime", f"SELECT tipo, version FROM chilito_aceptaciones_pendientes({ANA})", espera=[("terminos", "1.1")])
mal("Aceptar una versión que ya no es vigente", "chilito_pkg_runtime",
    f"""INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,usuario_id)
       SELECT s.id,'aceptacion_terminos',true,(SELECT id FROM documento_legal WHERE tipo='terminos' AND version='1.0'),{ANA} FROM privacidad_sujeto s WHERE s.usuario_id={ANA}""", contiene="vigente")
bien("Ana acepta la 1.1 al entrar → nada pendiente", "chilito_pkg_runtime", [
    f"""INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,usuario_id,ip_recortada,navegador)
       SELECT s.id,'aceptacion_terminos',true,chilito_documento_vigente('terminos'),{ANA},'189.203.45.0','Firefox 132 · Windows' FROM privacidad_sujeto s WHERE s.usuario_id={ANA} AND s.ambito='cuenta'""",
    f"SELECT count(*) FROM chilito_aceptaciones_pendientes({ANA})"], espera=[(0,)])

# ------------------------------------------------------------------------------------------------ COOKIES
bien("Visitante anónimo rechaza cookies", "chilito_pkg_runtime", [
    "INSERT INTO privacidad_sujeto(id,ambito) VALUES ('11111111-1111-1111-1111-111111111111','navegador')",
    """INSERT INTO privacidad_decision(id,sujeto_id,acto,decision,documento_id,finalidad_id,ip_recortada,navegador)
       VALUES ('22222222-2222-2222-2222-222222222222','11111111-1111-1111-1111-111111111111','cookies',false,chilito_documento_vigente('politica_cookies'),
       (SELECT id FROM privacidad_finalidad),'201.141.12.0','Safari 18 · iPhone')""",
    """INSERT INTO privacidad_preferencia(sujeto_id,finalidad_id,decision_id) VALUES ('11111111-1111-1111-1111-111111111111',
       (SELECT id FROM privacidad_finalidad),'22222222-2222-2222-2222-222222222222')"""])
bien("Ana (con sesión) acepta cookies en su navegador", "chilito_pkg_runtime", [
    f"INSERT INTO privacidad_sujeto(id,ambito,usuario_id) VALUES ('33333333-3333-3333-3333-333333333333','navegador',{ANA})",
    f"""INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,finalidad_id,usuario_id,ip_recortada,navegador)
       VALUES ('33333333-3333-3333-3333-333333333333','cookies',true,chilito_documento_vigente('politica_cookies'),(SELECT id FROM privacidad_finalidad),{ANA},'189.203.45.0','Chrome 130 · Android')"""])
mal("IP sin recortar", "chilito_pkg_runtime",
    """INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,finalidad_id,ip_recortada)
       VALUES ('11111111-1111-1111-1111-111111111111','cookies',true,chilito_documento_vigente('politica_cookies'),(SELECT id FROM privacidad_finalidad),'201.141.12.77')""", contiene="priv_decision_ip_recortada")
mal("Cookies decididas sobre el sujeto de cuenta", "chilito_pkg_runtime",
    f"""INSERT INTO privacidad_decision(sujeto_id,acto,decision,documento_id,finalidad_id)
       SELECT s.id,'cookies',true,chilito_documento_vigente('politica_cookies'),(SELECT id FROM privacidad_finalidad) FROM privacidad_sujeto s WHERE s.usuario_id={ANA} AND s.ambito='cuenta'""", contiene="navegador")
bien("Bitácora: correo, qué, versión y decisión", "chilito_pkg_runtime",
     "SELECT cuenta, que, version_documento, decision FROM v_bitacora_consentimientos WHERE que='Cookies' ORDER BY registrada_en",
     espera=[("Visitante anónimo", "Cookies", "1.0", "Rechazó"), ("ana@example.com", "Cookies", "1.0", "Aceptó")])
mal("La bitácora no se modifica", "chilito_pkg_owner", "UPDATE privacidad_decision SET decision=true", contiene="inmutable")

# --------------------------------------------------------------------------------------------- VENTAS
mal("Vender sin «gestionar_ventas»", "chilito_pkg_runtime",
    f"INSERT INTO venta(dispositivo_id,comprador_nombre,comprador_correo,municipio,precio_mxn,modalidad_entrega,vendida_en,registrada_por_id) VALUES ({D1},'Ana','ana@example.com','Mérida',3500,'domicilio',current_date,{LUIS})", actor=LUIS, contiene="gestionar_ventas")
bien("Super admin registra la venta del ESP32-0001", "chilito_pkg_runtime",
     f"INSERT INTO venta(dispositivo_id,comprador_nombre,comprador_correo,comprador_usuario_id,municipio,precio_mxn,importe_recibido_mxn,referencia_pago,modalidad_entrega,vendida_en,registrada_por_id) VALUES ({D1},'Ana','ana@example.com',{ANA},'Mérida',3500,1000,'Transferencia 0042','domicilio',current_date,{SUPER})", actor=SUPER)
bien("El estado de pago lo calcula la base (parcial)", "chilito_pkg_runtime", f"SELECT estado_pago FROM venta WHERE dispositivo_id={D1}", espera=[("parcial",)])
bien("Registrar el resto del pago y la entrega", "chilito_pkg_runtime", [f"UPDATE venta SET importe_recibido_mxn=3500, entregada_en=current_date WHERE dispositivo_id={D1}", f"SELECT estado_pago FROM venta WHERE dispositivo_id={D1}"], actor=SUPER, espera=[("completo",)])
mal("Importe recibido mayor que el precio", "chilito_pkg_runtime", f"UPDATE venta SET importe_recibido_mxn=4000 WHERE dispositivo_id={D1}", actor=SUPER, contiene="venta_importe_valido")
mal("Venta con fecha futura", "chilito_pkg_runtime", f"INSERT INTO venta(dispositivo_id,comprador_nombre,comprador_correo,municipio,precio_mxn,modalidad_entrega,vendida_en,registrada_por_id) VALUES ((SELECT id FROM dispositivo WHERE identificador='ESP32-0004'),'X','x@example.com','Mérida',3500,'recogida',current_date+3,{SUPER})", actor=SUPER, contiene="futura")
mal("Una sola venta vigente por equipo", "chilito_pkg_runtime",
    f"INSERT INTO venta(dispositivo_id,comprador_nombre,comprador_correo,municipio,precio_mxn,modalidad_entrega,vendida_en,registrada_por_id) VALUES ({D1},'Otro','o@example.com','Progreso',3500,'recogida',current_date,{SUPER})", actor=SUPER, contiene="venta_vigente_por_equipo")

# ----------------------------------------------------------------------------------------- DESVINCULAR
D3 = uno("chilito_pkg_owner", "SELECT id FROM dispositivo WHERE identificador='ESP32-0003'")
mal("Archivar un huerto con equipo", "chilito_pkg_runtime", f"UPDATE huerto SET estado='archivado' WHERE id={H3}", actor=ANA, contiene="Desvincula")
mal("Otra cuenta no desvincula el equipo de Ana", "chilito_pkg_runtime", f"SELECT chilito_desvincular_dispositivo({D3})", actor=LUIS, contiene="dueño")
bien("Ana desvincula su equipo y archiva el huerto", "chilito_pkg_runtime", [
    f"SELECT chilito_desvincular_dispositivo({D3})", f"UPDATE huerto SET estado='archivado' WHERE id={H3}",
    f"SELECT d.estado, h.estado FROM dispositivo d, huerto h WHERE d.id={D3} AND h.id={H3}"], actor=ANA, espera=[("disponible", "archivado")])
bien("Historial del equipo: alta → vinculado → desvinculado", "chilito_pkg_owner",
     f"SELECT string_agg(tipo, ' → ' ORDER BY id) FROM dispositivo_evento WHERE dispositivo_id={D3}", espera=[("alta → vinculado → desvinculado",)])

# ------------------------------------------------------------------------------------------- ANONIMIZAR
bien("Ana pide anonimizar su cuenta", "chilito_pkg_runtime", f"UPDATE cuentas_usuario SET anonimizacion_solicitada_en=now() WHERE id={ANA}", actor=ANA)
mal("La tarea periódica no la ejecuta la página", "chilito_pkg_runtime", "SELECT chilito_mantenimiento_periodico()", contiene="permission denied")
bien("Tarea periódica (antes de 15 días no anonimiza)", "chilito_pkg_owner", "SELECT (chilito_mantenimiento_periodico()->>'cuentas_anonimizadas')::int", espera=[(0,)])
bien("Owner anonimiza (simula los 15 días)", "chilito_pkg_owner", [
    f"SELECT chilito_anonimizar_cuenta({ANA})",
    f"""SELECT u.email, u.is_active, (SELECT count(*) FROM huerto WHERE propietario_id={ANA} AND estado='activo'),
        (SELECT count(*) FROM dispositivo WHERE estado='vinculado'), (SELECT count(*) FROM notificacion WHERE destinatario_id={ANA})
        FROM cuentas_usuario u WHERE u.id={ANA}"""], espera=[(f"anonimo-{ANA}@anonimo.invalid", False, 0, 0, 0)])
bien("La bitácora conserva la prueba como «Cuenta eliminada»", "chilito_pkg_runtime",
     "SELECT count(*) FROM v_bitacora_consentimientos WHERE cuenta='Cuenta eliminada'", espera=[(4,)])
mal("La anonimización no se deshace", "chilito_pkg_owner", f"UPDATE cuentas_usuario SET anonimizada_en=NULL, is_active=true WHERE id={ANA}", contiene="vuelta atrás")

# ----------------------------------------------------------------------------------------- AUDITORÍA
mal("La auditoría no se modifica", "chilito_pkg_owner", "UPDATE auditoria SET resultado='rechazado'", contiene="inmutable")
mal("El historial de capacidades no se borra", "chilito_pkg_owner", "DELETE FROM capacidad_historial", contiene="inmutable")

print(f"\nCORRECTAS: {len(OK)}   FALLOS: {len(FALLOS)}")
for f in FALLOS:
    print("  ✖", f)
sys.exit(1 if FALLOS else 0)

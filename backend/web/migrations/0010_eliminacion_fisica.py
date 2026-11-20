"""Eliminación física e inmediata de una cuenta (sustituye a la anonimización a los 15 días).

· chilito_eliminar_cuenta(usuario): borra en la misma transacción la cuenta y todo lo suyo. Eso incluye sus huertos con
  todo su contenido (plantas, ciclos, telemetría, cuidados, comandos, casos de soporte…), notificaciones, auditoría,
  bitácora de consentimientos (sujetos, decisiones y preferencias), historial de capacidades, recibos de idempotencia,
  correos de allauth y segundo factor. Antes desvincula los equipos de sus huertos por la ruta normal, así que quedan
  «disponible». En registros ajenos pone en NULL las referencias opcionales (por ejemplo, la venta de la que fue
  compradora se conserva con su dato fiscal, pero ya sin vínculo a la cuenta). Al final deja en auditoría una sola
  fila sin identificar: «eliminar_cuenta», sin actor ni id.
  · La aplicación (chilito_pkg_runtime) solo puede borrar la cuenta de la sesión (chilito.actor_id).
  · Se rechaza una cuenta con capacidades («cuenta-administrativa»), lo que incluye al último superadministrador. También
    se rechaza la que dejó referencias obligatorias en registros ajenos («cuenta-con-historial-administrativo»).
· Los historiales siguen siendo inmutables. La excepción la autoriza una fila en cuenta_en_borrado con el id de la
  transacción en curso. La tabla es solo del propietario, la escribe únicamente chilito_eliminar_cuenta (SECURITY
  DEFINER) y la vacía antes de terminar. Una bandera de sesión (set_config) no serviría, porque la aplicación también
  puede fijarla.
· Los triggers que impiden borrar reciben al inicio la guarda chilito_borrado_permitido. La guarda deja pasar un DELETE y
  un UPDATE que solo pone en NULL referencias a la cuenta que se borra, y únicamente mientras exista esa marca. La guarda
  se inyecta en la definición vigente de cada función (incluidas las que reemplazaron 0004–0007). El inverso la quita.
· Índices en las columnas que apuntan a la cuenta, para que los DELETE y las comprobaciones de FK al confirmar no recorran
  tablas completas.
· La aplicación ya no escribe anonimizacion_solicitada_en (se retira el UPDATE de esa columna). Las columnas heredadas y
  chilito_anonimizar_cuenta se conservan para las solicitudes antiguas que sigan pendientes.
"""
from django.db import migrations

INICIO, FIN = '-- chilito:borrado-de-cuenta', '-- /chilito:borrado-de-cuenta'
GUARDA = (f"\n {INICIO}\n IF public.chilito_borrado_permitido(TG_OP, TG_RELID, to_jsonb(OLD), to_jsonb(NEW)) THEN\n"
          f"  IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;\n END IF;\n {FIN}")
# La cuenta solo se borra si es justo la marcada; nunca se modifica por esta vía.
GUARDA_CUENTA = (f"\n {INICIO}\n IF TG_OP='DELETE' AND OLD.id = public.chilito_borrado_de_cuenta() THEN RETURN OLD; END IF;\n {FIN}")

# Funciones de trigger que impiden borrar o desvincular filas a las que llega el borrado de una cuenta.
FUNCIONES = ('chilito_inmutable', 'chilito_huerto_reglas', 'chilito_planta_reglas', 'chilito_dispositivo_reglas',
             'chilito_codigo_reglas', 'chilito_comando_reglas', 'chilito_autodiagnostico_reglas', 'chilito_guia_reglas',
             'chilito_caso_reglas', 'chilito_sesion_reglas', 'chilito_notificacion_reglas', 'chilito_consulta_reglas',
             'chilito_correo_reglas', 'chilito_venta_reglas', 'chilito_legal_reglas', 'chilito_sujeto_reglas',
             'chilito_preferencia_reglas', 'chilito_ciclo_reglas', 'chilito_deteccion_reglas')

# Columnas que apuntan a cuentas_usuario y no tenían índice (parciales: casi todas son NULL).
INDICES = (('capacidad_historial', 'realizada_por_id'), ('huerto_planta_etapa', 'registrada_por_id'),
           ('autodiagnostico', 'solicitado_por_id'), ('comando', 'solicitado_por_id'), ('consulta_producto', 'atendida_por_id'),
           ('cuidado', 'registrado_por_id'), ('dispositivo', 'registrado_por_id'), ('codigo_vinculacion', 'generado_por_id'),
           ('dispositivo_evento', 'actor_id'), ('guia_cuidado', 'creado_por_id'), ('guia_cuidado', 'actualizado_por_id'),
           ('soporte_caso', 'atendido_por_id'), ('venta', 'comprador_usuario_id'), ('venta', 'registrada_por_id'),
           ('cuidado_revision', 'editor_id'), ('planta_ciclo', 'cerrado_por_id'), ('documento_legal', 'creado_por_id'),
           ('documento_legal', 'publicado_por_id'), ('deposito_deteccion', 'decidida_por_id'), ('notificacion', 'huerto_id'))


def _inyectar(nombre, guarda):
    """Bloque DO que añade la guarda tras el primer BEGIN del cuerpo vigente; falla si no la pudo poner o ya estaba."""
    return f"""
DO $do$
DECLARE antes text := pg_get_functiondef('public.{nombre}()'::regprocedure); despues text;
BEGIN
 IF position('{INICIO}' IN antes) > 0 THEN RAISE EXCEPTION '{nombre} ya tiene la guarda de borrado'; END IF;
 despues := regexp_replace(antes, '(AS \\$function\\$.*?\\mBEGIN\\M)', '\\1' || $g${guarda}$g$);
 IF despues = antes THEN RAISE EXCEPTION 'No se pudo poner la guarda de borrado en {nombre}'; END IF;
 EXECUTE despues;
END $do$;"""


def _retirar(nombre):
    return f"""
DO $do$
DECLARE antes text := pg_get_functiondef('public.{nombre}()'::regprocedure); despues text;
BEGIN
 despues := regexp_replace(antes, '\\n {INICIO}.*?{FIN}', '');
 IF despues <> antes THEN EXECUTE despues; END IF;
END $do$;"""


BASE = r"""
-- Marca de la transacción que está borrando una cuenta. Solo el propietario la toca.
CREATE TABLE public.cuenta_en_borrado (
 transaccion xid8 PRIMARY KEY DEFAULT pg_current_xact_id(),
 usuario_id bigint NOT NULL
);
REVOKE ALL ON public.cuenta_en_borrado FROM PUBLIC, chilito_pkg_runtime, chilito_pkg_iot;

-- Cuenta que esta transacción está borrando, o NULL. SECURITY DEFINER: lee la marca sin dar acceso a la tabla.
CREATE FUNCTION public.chilito_borrado_de_cuenta() RETURNS bigint
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT usuario_id FROM public.cuenta_en_borrado WHERE transaccion = pg_current_xact_id_if_assigned()
$$;

-- Durante el borrado de una cuenta: un DELETE, o un UPDATE que solo pone en NULL referencias a esa cuenta.
-- Las columnas generadas no cuentan: en un trigger BEFORE todavía valen NULL en la fila nueva.
CREATE FUNCTION public.chilito_borrado_permitido(op text, tabla oid, viejo jsonb, nuevo jsonb) RETURNS boolean
LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, public AS $$
DECLARE u bigint;
BEGIN
 IF op NOT IN ('DELETE','UPDATE') THEN RETURN false; END IF;
 u := public.chilito_borrado_de_cuenta();
 IF u IS NULL THEN RETURN false; END IF;
 IF op='DELETE' THEN RETURN true; END IF;
 RETURN NOT EXISTS (SELECT 1 FROM jsonb_each(nuevo) n JOIN jsonb_each(viejo) o USING (key)
                    WHERE n.value IS DISTINCT FROM o.value AND NOT (n.value='null'::jsonb AND o.value=to_jsonb(u))
                      AND NOT EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=tabla AND a.attname=key AND a.attgenerated<>''));
END $$;

REVOKE ALL ON FUNCTION public.chilito_borrado_de_cuenta(), public.chilito_borrado_permitido(text,oid,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.chilito_borrado_de_cuenta(), public.chilito_borrado_permitido(text,oid,jsonb,jsonb)
 TO chilito_pkg_runtime, chilito_pkg_iot;
"""

ELIMINAR = r"""
-- Borra la cuenta y todo lo suyo en esta transacción. Devuelve conteos, sin datos personales.
CREATE FUNCTION public.chilito_eliminar_cuenta(p_usuario bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
 r jsonb := '{}'::jsonb; n integer; d bigint;
 h bigint[]; p bigint[]; c uuid[]; s uuid[]; dec uuid[];
BEGIN
 IF public.chilito_es_aplicacion() AND p_usuario IS DISTINCT FROM public.chilito_actor() THEN
  RAISE EXCEPTION 'Solo la cuenta de la sesión puede eliminarse' USING ERRCODE='42501';
 END IF;
 IF session_user NOT IN ('chilito_pkg_runtime','chilito_pkg_owner') THEN
  RAISE EXCEPTION 'Rol no autorizado para eliminar cuentas' USING ERRCODE='42501';
 END IF;
 PERFORM 1 FROM public.cuentas_usuario WHERE id=p_usuario FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'La cuenta no existe' USING ERRCODE='P0002'; END IF;
 IF EXISTS (SELECT 1 FROM public.cuentas_usuario_user_permissions WHERE usuario_id=p_usuario) THEN
  RAISE EXCEPTION 'Una cuenta con capacidades no se elimina' USING ERRCODE='23514';
 END IF;

 SELECT coalesce(array_agg(id), '{}') INTO h FROM public.huerto WHERE propietario_id=p_usuario;
 -- Referencias obligatorias en registros ajenos: borrarlas dañaría el historial de otra persona.
 IF EXISTS (SELECT 1 FROM public.soporte_sesion x JOIN public.soporte_caso k ON k.id=x.caso_id
            WHERE x.administrador_id=p_usuario AND NOT k.huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.soporte_caso WHERE (solicitante_id=p_usuario OR (atendido_por_id=p_usuario AND estado<>'cancelado'))
            AND NOT huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.venta WHERE registrada_por_id=p_usuario)
 OR EXISTS (SELECT 1 FROM public.consulta_producto WHERE atendida_por_id=p_usuario)
 OR EXISTS (SELECT 1 FROM public.cuidado_revision x JOIN public.cuidado k ON k.id=x.cuidado_id
            WHERE x.editor_id=p_usuario AND NOT k.huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.cuidado WHERE registrado_por_id=p_usuario AND origen<>'equipo' AND NOT huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.deposito_deteccion WHERE decidida_por_id=p_usuario AND estado IN ('confirmada','descartada')
            AND NOT huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.codigo_vinculacion WHERE generado_por_id=p_usuario AND NOT huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.comando WHERE solicitado_por_id=p_usuario AND NOT huerto_id = ANY(h))
 OR EXISTS (SELECT 1 FROM public.autodiagnostico WHERE solicitado_por_id=p_usuario AND NOT huerto_id = ANY(h)) THEN
  RAISE EXCEPTION 'La cuenta tiene historial administrativo en registros de otras personas' USING ERRCODE='23514';
 END IF;

 -- Los equipos se desvinculan por la ruta normal, antes de la marca: quedan «disponible» con sus reglas.
 FOR d IN SELECT id FROM public.dispositivo WHERE huerto_id = ANY(h) AND estado='vinculado' LOOP
  PERFORM public.chilito_desvincular_dispositivo(d);
 END LOOP;

 INSERT INTO public.cuenta_en_borrado(usuario_id) VALUES (p_usuario);

 -- Huertos y todo su contenido.
 SELECT coalesce(array_agg(id), '{}') INTO p FROM public.huerto_planta WHERE huerto_id = ANY(h);
 SELECT coalesce(array_agg(id), '{}') INTO c FROM public.soporte_caso WHERE huerto_id = ANY(h) OR solicitante_id=p_usuario;
 DELETE FROM public.medicion WHERE huerto_id = ANY(h);                      -- medicion_planta cae en cascada
 GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('mediciones', n);
 DELETE FROM public.resumen_hora_huerto WHERE huerto_id = ANY(h);
 DELETE FROM public.resumen_hora_planta WHERE huerto_id = ANY(h);
 DELETE FROM public.actuacion WHERE huerto_id = ANY(h);
 DELETE FROM public.autodiagnostico_revision WHERE autodiagnostico_id IN (SELECT id FROM public.autodiagnostico WHERE huerto_id = ANY(h));
 DELETE FROM public.correo_pendiente WHERE caso_id = ANY(c);
 DELETE FROM public.comando WHERE huerto_id = ANY(h) OR sesion_id IN (SELECT id FROM public.soporte_sesion WHERE caso_id = ANY(c));
 DELETE FROM public.soporte_sesion WHERE caso_id = ANY(c);
 DELETE FROM public.soporte_caso WHERE id = ANY(c);
 DELETE FROM public.autodiagnostico WHERE huerto_id = ANY(h);
 DELETE FROM public.ia_resumen WHERE huerto_id = ANY(h);
 DELETE FROM public.deposito_deteccion WHERE huerto_id = ANY(h);
 DELETE FROM public.cuidado_revision WHERE cuidado_id IN (SELECT id FROM public.cuidado WHERE huerto_id = ANY(h));
 DELETE FROM public.cuidado WHERE huerto_id = ANY(h);
 GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('cuidados', n);
 DELETE FROM public.codigo_vinculacion WHERE huerto_id = ANY(h);
 DELETE FROM public.planta_recomendacion WHERE ciclo_id IN (SELECT id FROM public.planta_ciclo WHERE planta_id = ANY(p));
 DELETE FROM public.huerto_planta_etapa WHERE planta_id = ANY(p);
 DELETE FROM public.planta_ciclo WHERE planta_id = ANY(p);
 DELETE FROM public.huerto_planta WHERE id = ANY(p);
 DELETE FROM public.dispositivo_evento WHERE huerto_id = ANY(h);
 DELETE FROM public.notificacion WHERE huerto_id = ANY(h) OR destinatario_id=p_usuario;
 DELETE FROM public.auditoria WHERE huerto_id = ANY(h) OR actor_id=p_usuario OR (entidad='cuenta' AND entidad_id=p_usuario::text);
 GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('auditoria', n);
 DELETE FROM public.huerto WHERE id = ANY(h);
 r := r || jsonb_build_object('huertos', cardinality(h));

 -- Bitácora de consentimientos: sujetos de la cuenta (también los de navegador vinculados), sus decisiones y preferencias.
 SELECT coalesce(array_agg(id), '{}') INTO s FROM public.privacidad_sujeto WHERE usuario_id=p_usuario;
 SELECT coalesce(array_agg(id), '{}') INTO dec FROM public.privacidad_decision WHERE usuario_id=p_usuario OR sujeto_id = ANY(s);
 DELETE FROM public.privacidad_preferencia WHERE sujeto_id = ANY(s) OR decision_id = ANY(dec);
 DELETE FROM public.privacidad_decision WHERE id = ANY(dec);
 r := r || jsonb_build_object('decisiones', cardinality(dec));
 DELETE FROM public.privacidad_sujeto WHERE id = ANY(s);

 -- Lo demás de la cuenta.
 DELETE FROM public.capacidad_historial WHERE usuario_id=p_usuario;
 DELETE FROM public.web_idempotencia WHERE actor_id=p_usuario;
 DELETE FROM public.account_emailconfirmation WHERE email_address_id IN (SELECT id FROM public.account_emailaddress WHERE user_id=p_usuario);
 DELETE FROM public.account_emailaddress WHERE user_id=p_usuario;
 DELETE FROM public.mfa_authenticator WHERE user_id=p_usuario;
 DELETE FROM public.cuentas_usuario_groups WHERE usuario_id=p_usuario;

 -- Referencias opcionales en registros ajenos: el registro se conserva sin vínculo a la cuenta.
 UPDATE public.venta SET comprador_usuario_id=NULL WHERE comprador_usuario_id=p_usuario;
 UPDATE public.capacidad_historial SET realizada_por_id=NULL WHERE realizada_por_id=p_usuario;
 UPDATE public.dispositivo_evento SET actor_id=NULL WHERE actor_id=p_usuario;
 UPDATE public.dispositivo SET registrado_por_id=NULL WHERE registrado_por_id=p_usuario;
 UPDATE public.cuidado SET registrado_por_id=NULL WHERE registrado_por_id=p_usuario;
 UPDATE public.huerto_planta_etapa SET registrada_por_id=NULL WHERE registrada_por_id=p_usuario;
 UPDATE public.planta_ciclo SET cerrado_por_id=NULL WHERE cerrado_por_id=p_usuario;
 UPDATE public.soporte_caso SET atendido_por_id=NULL WHERE atendido_por_id=p_usuario;
 UPDATE public.guia_cuidado SET creado_por_id=NULL WHERE creado_por_id=p_usuario;
 UPDATE public.guia_cuidado SET actualizado_por_id=NULL WHERE actualizado_por_id=p_usuario;
 UPDATE public.documento_legal SET creado_por_id=NULL WHERE creado_por_id=p_usuario;
 UPDATE public.documento_legal SET publicado_por_id=NULL WHERE publicado_por_id=p_usuario;

 DELETE FROM public.cuentas_usuario WHERE id=p_usuario;

 -- Sin actor: nada nuevo puede apuntar a la cuenta borrada. Una fila sin datos que la identifiquen.
 PERFORM set_config('chilito.actor_id', '', true);
 INSERT INTO public.auditoria(actor_id, accion, entidad, entidad_id) VALUES (NULL, 'eliminar_cuenta', 'cuenta', '');
 DELETE FROM public.cuenta_en_borrado WHERE transaccion = pg_current_xact_id();
 RETURN r;
END $$;
REVOKE ALL ON FUNCTION public.chilito_eliminar_cuenta(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.chilito_eliminar_cuenta(bigint) TO chilito_pkg_runtime;

-- La aplicación ya no pide la anonimización diferida.
REVOKE UPDATE (anonimizacion_solicitada_en) ON public.cuentas_usuario FROM chilito_pkg_runtime;
"""

BASE_INVERSA = r"""
DROP FUNCTION public.chilito_borrado_permitido(text,oid,jsonb,jsonb);
DROP FUNCTION public.chilito_borrado_de_cuenta();
DROP TABLE public.cuenta_en_borrado;
"""

ELIMINAR_INVERSA = r"""
GRANT UPDATE (anonimizacion_solicitada_en) ON public.cuentas_usuario TO chilito_pkg_runtime;
DROP FUNCTION public.chilito_eliminar_cuenta(bigint);
"""

GUARDAS = ''.join(_inyectar(nombre, GUARDA) for nombre in FUNCIONES) + _inyectar('chilito_cuenta_reglas', GUARDA_CUENTA)
GUARDAS_INVERSAS = ''.join(_retirar(nombre) for nombre in (*FUNCIONES, 'chilito_cuenta_reglas'))
CREAR_INDICES = ''.join(f'CREATE INDEX IF NOT EXISTS {tabla}_{columna}_borrado ON public.{tabla}({columna}) '
                        f'WHERE {columna} IS NOT NULL;\n' for tabla, columna in INDICES)
BORRAR_INDICES = ''.join(f'DROP INDEX IF EXISTS public.{tabla}_{columna}_borrado;\n' for tabla, columna in INDICES)


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0009_nombre_yougarden'),
        ('huerto', '0002_planta_ciclo'),
        ('datos', '0003_deposito_deteccion'),
        ('privacidad', '0001_initial'),
        ('cuentas', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(BASE, BASE_INVERSA),
        migrations.RunSQL(GUARDAS, GUARDAS_INVERSAS),
        migrations.RunSQL(CREAR_INDICES, BORRAR_INDICES),
        migrations.RunSQL(ELIMINAR, ELIMINAR_INVERSA),
    ]

from django.db import migrations
FORWARD=r'''
CREATE FUNCTION public.chilito_historial_inmutable() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Historial inmutable; no se permite alterar ni borrar' USING ERRCODE='23514';
END $$;
CREATE FUNCTION public.chilito_permiso_revocar() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'El permiso se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'revocado_en') IS DISTINCT FROM (to_jsonb(OLD)-'revocado_en')
 OR OLD.revocado_en IS NOT NULL AND NEW.revocado_en IS DISTINCT FROM OLD.revocado_en
 OR NEW.revocado_en IS NULL THEN
  RAISE EXCEPTION 'Solo se admite revocacion irreversible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.chilito_tecnica_cerrar() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'La sesion tecnica se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'cerrada_en'-'motivo_cierre') IS DISTINCT FROM (to_jsonb(OLD)-'cerrada_en'-'motivo_cierre')
 OR OLD.cerrada_en IS NOT NULL AND (NEW.cerrada_en IS DISTINCT FROM OLD.cerrada_en OR NEW.motivo_cierre IS DISTINCT FROM OLD.motivo_cierre)
 OR NEW.cerrada_en IS NULL THEN
  RAISE EXCEPTION 'Solo se admite cierre irreversible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.chilito_datos_relaciones() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE c public.datos_casosoporte%ROWTYPE; p public.datos_permisosoporte%ROWTYPE;
        t public.datos_sesiontecnica%ROWTYPE; v public.datos_validacionversion%ROWTYPE;
        s public.datos_solicitud%ROWTYPE; g bigint; a bigint;
BEGIN
 IF TG_TABLE_NAME='datos_casosoporte' THEN
  IF NOT EXISTS(SELECT 1 FROM public.datos_dispositivo WHERE id=NEW.dispositivo_id AND huerto_id=NEW.huerto_id) THEN
   RAISE EXCEPTION 'Dispositivo de otro huerto' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_permisosoporte' THEN
  SELECT * INTO c FROM public.datos_casosoporte WHERE id=NEW.caso_id;
  IF NEW.otorgante_id IS DISTINCT FROM c.solicitante_id THEN
   RAISE EXCEPTION 'Permiso de otro solicitante' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_sesiontecnica' THEN
  SELECT * INTO p FROM public.datos_permisosoporte WHERE id=NEW.permiso_id FOR UPDATE;
  IF p.revocado_en IS NOT NULL OR p.vence_en<=statement_timestamp()
   OR NEW.iniciada_en<p.emitido_en OR NEW.iniciada_en>=p.vence_en THEN
   RAISE EXCEPTION 'Permiso no vigente' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_solicitud' THEN
  IF NEW.dispositivo_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_dispositivo WHERE id=NEW.dispositivo_id AND huerto_id=NEW.huerto_id) THEN
   RAISE EXCEPTION 'Dispositivo de otro huerto' USING ERRCODE='23514';
  END IF;
  IF NEW.validacion_id IS NOT NULL THEN
   SELECT * INTO v FROM public.datos_validacionversion WHERE id=NEW.validacion_id;
   IF v.actor_id IS DISTINCT FROM NEW.actor_id OR v.tipo IS DISTINCT FROM NEW.tipo THEN
    RAISE EXCEPTION 'Validacion de otro actor o tipo' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.sesion_tecnica_id IS NOT NULL THEN
   SELECT * INTO t FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id;
   SELECT * INTO p FROM public.datos_permisosoporte WHERE id=t.permiso_id FOR UPDATE;
   SELECT * INTO t FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id FOR UPDATE;
   SELECT * INTO c FROM public.datos_casosoporte WHERE id=p.caso_id;
   IF t.administrador_id IS DISTINCT FROM NEW.actor_id OR t.cerrada_en IS NOT NULL
    OR p.revocado_en IS NOT NULL OR p.vence_en<=statement_timestamp()
    OR NEW.huerto_id IS DISTINCT FROM c.huerto_id OR NEW.dispositivo_id IS DISTINCT FROM c.dispositivo_id THEN
    RAISE EXCEPTION 'Solicitud fuera de la autorizacion tecnica' USING ERRCODE='23514';
   END IF;
  END IF;
 ELSIF TG_TABLE_NAME='datos_auditoria' THEN
  IF NEW.caso_id IS NOT NULL THEN
   SELECT * INTO c FROM public.datos_casosoporte WHERE id=NEW.caso_id;
   IF NEW.huerto_id IS DISTINCT FROM c.huerto_id THEN
    RAISE EXCEPTION 'Auditoria de otro huerto' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.permiso_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_permisosoporte WHERE id=NEW.permiso_id AND caso_id=NEW.caso_id) THEN
   RAISE EXCEPTION 'Auditoria de otro permiso' USING ERRCODE='23514';
  END IF;
  IF NEW.solicitud_id IS NOT NULL THEN
   SELECT * INTO s FROM public.datos_solicitud WHERE id=NEW.solicitud_id;
   IF s.actor_id IS DISTINCT FROM NEW.actor_id OR s.huerto_id IS DISTINCT FROM NEW.huerto_id THEN
    RAISE EXCEPTION 'Auditoria de otra solicitud' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.mantenimiento_id IS NOT NULL THEN
   SELECT huerto_id,actor_id INTO g,a FROM public.datos_mantenimiento WHERE id=NEW.mantenimiento_id;
   IF g IS DISTINCT FROM NEW.huerto_id OR a IS DISTINCT FROM NEW.actor_id THEN
    RAISE EXCEPTION 'Auditoria de otro mantenimiento' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.validacion_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_validacionversion WHERE id=NEW.validacion_id AND actor_id=NEW.actor_id) THEN
   RAISE EXCEPTION 'Auditoria de otra validacion' USING ERRCODE='23514';
  END IF;
  IF NEW.conocimiento_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_revisionconocimiento WHERE id=NEW.conocimiento_id AND autor_id=NEW.actor_id) THEN
   RAISE EXCEPTION 'Auditoria de otra revision' USING ERRCODE='23514';
  END IF;
  IF NEW.sesion_tecnica_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id AND administrador_id=NEW.actor_id AND permiso_id=NEW.permiso_id) THEN
   RAISE EXCEPTION 'Auditoria de otra sesion' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
'''
# Fixed identifiers, never untrusted input.
IMMUTABLE=['dispositivo','mantenimiento','casosoporte','validacionversion','revisionconocimiento','solicitud','auditoria']
for name in IMMUTABLE:
    FORWARD+=f'CREATE TRIGGER historial_{name} BEFORE UPDATE OR DELETE ON public.datos_{name} FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();\n'
FORWARD+='''
CREATE TRIGGER permiso_solo_revocar BEFORE UPDATE OR DELETE ON public.datos_permisosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_permiso_revocar();
CREATE TRIGGER tecnica_solo_cerrar BEFORE UPDATE OR DELETE ON public.datos_sesiontecnica FOR EACH ROW EXECUTE FUNCTION public.chilito_tecnica_cerrar();
'''
for name in ['casosoporte','permisosoporte','sesiontecnica','solicitud','auditoria']:
    FORWARD+=f'CREATE TRIGGER relacion_{name} BEFORE INSERT ON public.datos_{name} FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();\n'
FORWARD+='''
REVOKE ALL ON FUNCTION public.chilito_historial_inmutable(),public.chilito_permiso_revocar(),
 public.chilito_tecnica_cerrar(),public.chilito_datos_relaciones() FROM PUBLIC;
'''
FORWARD+='''
CREATE FUNCTION public.chilito_usuario_sin_privilegios() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF current_user='chilito_pkg_runtime' AND (NEW.is_staff OR NEW.is_superuser OR NOT NEW.is_active) THEN
  RAISE EXCEPTION 'El runtime no provisiona privilegios' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_usuario_sin_privilegios BEFORE INSERT ON public.cuentas_usuario
 FOR EACH ROW EXECUTE FUNCTION public.chilito_usuario_sin_privilegios();
REVOKE ALL ON FUNCTION public.chilito_usuario_sin_privilegios() FROM PUBLIC;
'''
REVERSE='DROP TRIGGER chilito_usuario_sin_privilegios ON public.cuentas_usuario; DROP FUNCTION public.chilito_usuario_sin_privilegios();\n'
for name in ['casosoporte','permisosoporte','sesiontecnica','solicitud','auditoria']:
    REVERSE+=f'DROP TRIGGER relacion_{name} ON public.datos_{name};\n'
for name in IMMUTABLE:
    REVERSE+=f'DROP TRIGGER historial_{name} ON public.datos_{name};\n'
REVERSE+='''
DROP TRIGGER permiso_solo_revocar ON public.datos_permisosoporte;
DROP TRIGGER tecnica_solo_cerrar ON public.datos_sesiontecnica;
DROP FUNCTION public.chilito_historial_inmutable();
DROP FUNCTION public.chilito_permiso_revocar();
DROP FUNCTION public.chilito_tecnica_cerrar();
DROP FUNCTION public.chilito_datos_relaciones();
'''
class Migration(migrations.Migration):
    dependencies=[('datos','0001_initial'),('huerto','0006_tres_zonas_y_lecturas')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]

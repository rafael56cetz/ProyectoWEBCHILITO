-- Apply after ALL migrations, in the target isolated database as administrative owner.
-- psql "$OWNER_DSN" -v ON_ERROR_STOP=1 -v db_name=chilito_integracion_sinteticos -f privilegios.sql
-- db_name local: chilito_integracion_sinteticos. Repetir solo en su base de pruebas.
-- Archivo único de privilegios: 03_esquema_completo.sql se genera desde aquí.
BEGIN;
REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db_name" TO chilito_pkg_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO chilito_pkg_runtime;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM chilito_pkg_runtime;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM chilito_pkg_runtime;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
GRANT SELECT ON public.cuentas_usuario,public.account_emailaddress,public.account_emailconfirmation,
 public.cuentas_confirmacionregistrolocal,public.huerto_huerto,public.huerto_zona,public.huerto_membresia,
 public.huerto_aviso,public.huerto_avisoleido,public.auth_permission,public.auth_group,
 public.auth_group_permissions,public.cuentas_usuario_groups,public.cuentas_usuario_user_permissions,
 public.django_content_type TO chilito_pkg_runtime;
GRANT INSERT ON public.cuentas_usuario,public.cuentas_confirmacionregistrolocal,public.huerto_avisoleido TO chilito_pkg_runtime;
GRANT UPDATE(email,password,last_login,first_name,last_name,alias,bienvenida_atendida_en) ON public.cuentas_usuario TO chilito_pkg_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.django_session,public.cuentas_cuotas_acceso,
 public.account_emailaddress,public.account_emailconfirmation TO chilito_pkg_runtime;
GRANT SELECT ON public.datos_dispositivo TO chilito_pkg_runtime;
GRANT SELECT,INSERT ON public.datos_mantenimiento,public.datos_casosoporte,public.datos_permisosoporte,
 public.datos_sesiontecnica,public.datos_validacionversion,public.datos_revisionconocimiento,
 public.datos_solicitud,public.datos_auditoria TO chilito_pkg_runtime;
GRANT UPDATE(revocado_en) ON public.datos_permisosoporte TO chilito_pkg_runtime;
GRANT UPDATE(cerrada_en,motivo_cierre) ON public.datos_sesiontecnica TO chilito_pkg_runtime;
-- Soporte resuelto y buzón: resoluciones solo se insertan; consultas y avisos solo avanzan su estado.
GRANT SELECT,INSERT ON public.datos_resolucionsoporte,public.datos_consultaproducto,public.datos_avisocorreo TO chilito_pkg_runtime;
GRANT UPDATE(estado,atendida_por_id,atendida_en) ON public.datos_consultaproducto TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,ultimo_intento_en,aceptado_en) ON public.datos_avisocorreo TO chilito_pkg_runtime;
-- Vinculación de huertos: los códigos se insertan y solo cierran su estado; la membresía solo se crea
-- y el trigger membresia_exige_codigo exige, al confirmar, un código consumido coherente.
GRANT SELECT,INSERT ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,cerrado_en,membresia_id,envio) ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT INSERT ON public.huerto_membresia TO chilito_pkg_runtime;
-- Guías de cuidado: sin DELETE (baja lógica) y sin UPDATE de identidad, autoría ni fecha de creación.
GRANT SELECT,INSERT ON public.datos_guiacuidado TO chilito_pkg_runtime;
GRANT UPDATE(pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,actualizado_en,actualizado_por_id) ON public.datos_guiacuidado TO chilito_pkg_runtime;
-- Row locking needs UPDATE privilege; immutable columns remain trigger-protected.
GRANT UPDATE(usuario_id) ON public.huerto_membresia TO chilito_pkg_runtime;
GRANT UPDATE(id) ON public.datos_casosoporte,public.datos_validacionversion TO chilito_pkg_runtime;
-- Sequence names come from catalog identities, not guessed naming conventions.
DO $$ DECLARE tab text; seq text; BEGIN
 FOREACH tab IN ARRAY ARRAY['cuentas_usuario','cuentas_confirmacionregistrolocal','account_emailaddress',
 'account_emailconfirmation','huerto_avisoleido','datos_revisionconocimiento','huerto_membresia'] LOOP
  seq:=pg_get_serial_sequence('public.'||tab,'id');
  IF seq IS NOT NULL THEN EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO chilito_pkg_runtime',seq); END IF;
 END LOOP;
END $$;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- Integration-only request ledger. No raw password/support token stored here.
GRANT SELECT,INSERT ON public.web_idempotencia TO chilito_pkg_runtime;
GRANT USAGE,SELECT ON SEQUENCE public.web_idempotencia_id_seq TO chilito_pkg_runtime;
-- Read-only migration history for Django's local startup consistency check.
GRANT SELECT ON public.django_migrations TO chilito_pkg_runtime;
-- Identidad de correo: necesaria al insertar o actualizar el índice de usuario.
GRANT EXECUTE ON FUNCTION public.chilito_identidad_correo(text) TO chilito_pkg_runtime;
-- Mantenimientos: revisiones de solo inserción. Asignaciones las administra el propietario.
GRANT SELECT,INSERT ON public.datos_revisionmantenimiento TO chilito_pkg_runtime;
GRANT SELECT ON public.datos_asignacionmantenimiento TO chilito_pkg_runtime;
GRANT UPDATE(id) ON public.datos_mantenimiento TO chilito_pkg_runtime;
-- Privacidad: catálogos de solo lectura; decisiones e historial sin UPDATE ni DELETE.
GRANT SELECT ON public.privacidad_documentoversion,public.privacidad_finalidadopcional TO chilito_pkg_runtime;
GRANT SELECT,INSERT ON public.privacidad_sujetoprivacidad,public.privacidad_decisionprivacidad,
 public.privacidad_preferenciafinalidad TO chilito_pkg_runtime;
GRANT UPDATE(usuario_id) ON public.privacidad_sujetoprivacidad TO chilito_pkg_runtime;
GRANT UPDATE(decision_id,actualizada_en) ON public.privacidad_preferenciafinalidad TO chilito_pkg_runtime;
GRANT INSERT ON public.privacidad_eventoprivacidad TO chilito_pkg_runtime;
GRANT SELECT(id,creado_en) ON public.privacidad_eventoprivacidad TO chilito_pkg_runtime;
-- Contador: solo totales diarios, sin identidad ni recorrido individual.
GRANT SELECT,INSERT ON public.privacidad_conteonavegacion TO chilito_pkg_runtime;
GRANT UPDATE(visitas) ON public.privacidad_conteonavegacion TO chilito_pkg_runtime;
GRANT USAGE,SELECT ON SEQUENCE public.privacidad_conteonavegacion_id_seq TO chilito_pkg_runtime;
-- Segundo factor: allauth usa save() completo. chilito_mfa_estable impide cambiar dueño o tipo.
GRANT SELECT,INSERT,DELETE ON public.mfa_authenticator TO chilito_pkg_runtime;
GRANT UPDATE(user_id,type,data,created_at,last_used_at) ON public.mfa_authenticator TO chilito_pkg_runtime;
GRANT USAGE,SELECT ON SEQUENCE public.mfa_authenticator_id_seq TO chilito_pkg_runtime;
COMMIT;

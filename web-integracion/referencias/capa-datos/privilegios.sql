-- Apply after ALL migrations, in the target isolated database as administrative owner.
-- psql "$OWNER_DSN" -v ON_ERROR_STOP=1 -v db_name=chilito_datos_sinteticos -f privilegios.sql
-- Repeat for test_chilito_datos_sinteticos only for the role test suite.
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
GRANT UPDATE(email,password,last_login,first_name,last_name) ON public.cuentas_usuario TO chilito_pkg_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.django_session,public.cuentas_cuotas_acceso,
 public.account_emailaddress,public.account_emailconfirmation TO chilito_pkg_runtime;
GRANT SELECT ON public.datos_dispositivo TO chilito_pkg_runtime;
GRANT SELECT,INSERT ON public.datos_mantenimiento,public.datos_casosoporte,public.datos_permisosoporte,
 public.datos_sesiontecnica,public.datos_validacionversion,public.datos_revisionconocimiento,
 public.datos_solicitud,public.datos_auditoria TO chilito_pkg_runtime;
GRANT UPDATE(revocado_en) ON public.datos_permisosoporte TO chilito_pkg_runtime;
GRANT UPDATE(cerrada_en,motivo_cierre) ON public.datos_sesiontecnica TO chilito_pkg_runtime;
-- Row locking needs UPDATE privilege; immutable columns remain trigger-protected.
GRANT UPDATE(usuario_id) ON public.huerto_membresia TO chilito_pkg_runtime;
GRANT UPDATE(id) ON public.datos_casosoporte,public.datos_validacionversion TO chilito_pkg_runtime;
-- Sequence names come from catalog identities, not guessed naming conventions.
DO $$ DECLARE tab text; seq text; BEGIN
 FOREACH tab IN ARRAY ARRAY['cuentas_usuario','cuentas_confirmacionregistrolocal','account_emailaddress',
 'account_emailconfirmation','huerto_avisoleido','datos_revisionconocimiento'] LOOP
  seq:=pg_get_serial_sequence('public.'||tab,'id');
  IF seq IS NOT NULL THEN EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO chilito_pkg_runtime',seq); END IF;
 END LOOP;
END $$;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
COMMIT;

-- Solo para una base creada antes de privacidad.0006. Query Tool, como chilito_pkg_owner.
-- Registra la versión 0.2 de aviso y términos: el texto que muestra la página legal.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='privacidad' AND name='0006_documentos_con_texto_publicado')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

INSERT INTO public.privacidad_documentoversion(id,tipo,version,contenido_ref,contenido_sha256,registrado_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e05','aviso_privacidad','0.2-borrador',
 'privacidad/documentos/aviso_privacidad-0.2-borrador.md',
 'c1b1a3e626e43344b685e9c671d48c223126abd330985642702f6f48549e1c02',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e06','terminos','0.2-borrador',
 'privacidad/documentos/terminos-0.2-borrador.md',
 '565e817bab5f7fa8f65127db1d7c00033b6ce100757ac8a63c6b72d188ee5ce5',now());

INSERT INTO public.django_migrations(app,name,applied) VALUES('privacidad','0006_documentos_con_texto_publicado',now());

COMMIT;

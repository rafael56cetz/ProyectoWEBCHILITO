-- Solo para una base que ya tiene datos.0010 (parche 06). Query Tool, como chilito_pkg_owner.
-- Guías de cuidado: tabla de fichas, referencia en la auditoría, trigger de protección, las nueve preguntas
-- iniciales (publicadas, sin cuenta asociada) y la capacidad gestionar_guias, creada SIN asignar a nadie.
-- Privilegios nuevos del rol de la aplicación: leer, crear y actualizar el contenido. Sin DELETE.
-- Una sola transacción: si algo falla, no se aplica nada (ejecuta ROLLBACK; para limpiar el error).
-- Después de aplicarlo, reinicia el servidor. Para asignar la capacidad: usa asignar_capacidad.sql con gestionar_guias.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0010_vinculacion_huerto')
 THEN RAISE EXCEPTION 'Falta el parche 06_vinculacion_huerto.sql'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0011_guias_cuidado')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

-- Esquema de datos.0011 (generado con sqlmigrate; incluye el trigger).
--
-- Create model GuiaCuidado
--
CREATE TABLE "datos_guiacuidado" ("id" uuid NOT NULL PRIMARY KEY, "clave" varchar(64) NOT NULL UNIQUE, "pregunta" varchar(200) NOT NULL, "respuesta" text NOT NULL, "orden" integer NOT NULL CHECK ("orden" >= 0), "estado" varchar(10) NOT NULL, "fuente_nombre" varchar(120) NOT NULL, "fuente_url" varchar(500) NOT NULL, "version" integer NOT NULL CHECK ("version" >= 0), "creado_en" timestamp with time zone NOT NULL, "actualizado_en" timestamp with time zone NOT NULL);
--
-- Change Meta options on dispositivo
--
-- (no-op)
--
-- Remove constraint auditoria_accion_valida from model auditoria
--
ALTER TABLE "datos_auditoria" DROP CONSTRAINT "auditoria_accion_valida";
--
-- Add field actualizado_por to guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD COLUMN "actualizado_por_id" bigint NULL CONSTRAINT "datos_guiacuidado_actualizado_por_id_2e6317a5_fk_cuentas_u" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_guiacuidado_actualizado_por_id_2e6317a5_fk_cuentas_u" IMMEDIATE;
--
-- Add field creado_por to guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD COLUMN "creado_por_id" bigint NULL CONSTRAINT "datos_guiacuidado_creado_por_id_2337ac27_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_guiacuidado_creado_por_id_2337ac27_fk_cuentas_usuario_id" IMMEDIATE;
--
-- Add field guia to auditoria
--
ALTER TABLE "datos_auditoria" ADD COLUMN "guia_id" uuid NULL CONSTRAINT "datos_auditoria_guia_id_06c2da4a_fk_datos_guiacuidado_id" REFERENCES "datos_guiacuidado"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_auditoria_guia_id_06c2da4a_fk_datos_guiacuidado_id" IMMEDIATE;
--
-- Create constraint auditoria_accion_valida on model auditoria
--
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved', 'maintenance-corrected', 'maintenance-voided', 'case-resolved', 'mfa-reset', 'binding-issued', 'binding-revoked', 'binding-replaced', 'binding-consumed', 'binding-rejected', 'binding-locked', 'binding-limited', 'guide-created', 'guide-updated', 'guide-published', 'guide-withdrawn'));
--
-- Create constraint auditoria_guia_coherente on model auditoria
--
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_guia_coherente" CHECK ((("accion"::text LIKE 'guide-%' AND "guia_id" IS NOT NULL) OR (NOT ("accion"::text LIKE 'guide-%') AND "guia_id" IS NULL)));
--
-- Create index guia_estado_orden_idx on field(s) estado, orden of model guiacuidado
--
CREATE INDEX "guia_estado_orden_idx" ON "datos_guiacuidado" ("estado", "orden");
--
-- Create constraint guia_pregunta_significativa on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_pregunta_significativa" CHECK ("pregunta"::text ~  E'\\S');
--
-- Create constraint guia_respuesta_significativa on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_respuesta_significativa" CHECK ("respuesta"::text ~  E'\\S');
--
-- Create constraint guia_respuesta_limite on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_respuesta_limite" CHECK (LENGTH("respuesta") <= 4000);
--
-- Create constraint guia_clave_valida on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_clave_valida" CHECK ("clave"::text ~ '^[a-z0-9]+(-[a-z0-9]+)*$');
--
-- Create constraint guia_orden_valido on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_orden_valido" CHECK (("orden" >= 1 AND "orden" <= 9999));
--
-- Create constraint guia_estado_valido on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_estado_valido" CHECK ("estado" IN ('borrador', 'publicada', 'retirada'));
--
-- Create constraint guia_version_valida on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_version_valida" CHECK ("version" >= 1);
--
-- Create constraint guia_fuente_valida on model guiacuidado
--
ALTER TABLE "datos_guiacuidado" ADD CONSTRAINT "guia_fuente_valida" CHECK (("fuente_url" = '' OR ("fuente_url"::text ~ '^https?://[^[:space:]]+$' AND NOT ("fuente_nombre" = ''))));
--
-- Raw SQL operation
--

CREATE FUNCTION public.chilito_guia_cuidado() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Las guias no se borran: se retiran' USING ERRCODE='23514';
 END IF;
 IF NEW.id<>OLD.id OR NEW.clave<>OLD.clave OR NEW.creado_en<>OLD.creado_en
    OR NEW.creado_por_id IS DISTINCT FROM OLD.creado_por_id THEN
  RAISE EXCEPTION 'La identidad y autoria de una guia no cambian' USING ERRCODE='23514';
 END IF;
 IF NEW.version<>OLD.version+1 OR NEW.actualizado_por_id IS NULL THEN
  RAISE EXCEPTION 'Cada cambio avanza la version e indica su responsable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER historial_guiacuidado BEFORE UPDATE OR DELETE ON public.datos_guiacuidado
 FOR EACH ROW EXECUTE FUNCTION public.chilito_guia_cuidado();

CREATE INDEX "datos_guiacuidado_clave_d54710c6_like" ON "datos_guiacuidado" ("clave" varchar_pattern_ops);
CREATE INDEX "datos_guiacuidado_actualizado_por_id_2e6317a5" ON "datos_guiacuidado" ("actualizado_por_id");
CREATE INDEX "datos_guiacuidado_creado_por_id_2337ac27" ON "datos_guiacuidado" ("creado_por_id");
CREATE INDEX "datos_auditoria_guia_id_06c2da4a" ON "datos_auditoria" ("guia_id");

-- Carga inicial de datos.0012: no duplica ni sobrescribe.
--
-- Raw SQL operation
--
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('799107f9-96d5-5536-86dc-9bc276475df2'::uuid,'germinacion-inicio','¿Cómo comienzo a germinar mis semillas de habanero?','Etapa de germinación. Se hace fuera del sistema, en un semillero aparte con mezcla limpia para semillas. Cubre las semillas con una capa ligera y mantén la mezcla húmeda, sin encharcarla.

Las semillas de chile germinan mejor en un lugar cálido y estable que en uno frío. Cuando asomen los brotes, dales luz abundante: con poca luz, el tallo se alarga y se inclina.

Registrar la germinación solo deja constancia de lo que ya hiciste. El sistema no la realiza ni la comprueba.',10,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('f849ea28-3a9e-5eae-9d67-ee7dca35aa0a'::uuid,'brotacion-tiempo','¿Cuánto puede tardar en brotar y qué debo observar?','No hay un plazo fijo. Depende de la edad de la semilla, la variedad, la temperatura y la humedad. El habanero puede tardar varias semanas, así que una espera larga no significa por sí sola que la siembra haya fallado.

Mientras tanto, observa que la mezcla siga húmeda y sin charcos, y que no aparezca moho ni mal olor. Si la mezcla se seca por completo o se mantiene empapada, la germinación puede fallar.

Cuando broten, vigila que el tallo no se alargue ni se doble hacia la luz.',20,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('82e02837-ab58-5847-b9c9-873dad3def6e'::uuid,'trasplante-plantula','¿Cómo reconozco que la plántula está lista para trasplantar?','Etapa de trasplante. Guíate por la plántula y no por el calendario: tallo firme, hojas verdaderas además de las dos primeras, buen color y raíces que ya sostienen la mezcla al sacarla.

Si creció en otro lugar, acostúmbrala poco a poco a la luz y a las condiciones del huerto. Al trasplantar, no entierres el tallo más de lo que estaba y riega después. Si ya tiene flores, puedes retirarlas para que se concentre en crecer.

Las fechas de las guías para exteriores dependen de las heladas y de cada clima. No se aplican tal cual a un huerto interior.',30,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('26fb7ca5-cd6e-5e36-8687-790308a24f8b'::uuid,'sustrato-perlita','¿Para qué sirve la perlita y cómo reviso el sustrato?','La perlita ayuda a conservar la aireación: mantiene espacios en la mezcla para que entren aire y agua y para que las raíces respiren.

Revisa si el agua drena con facilidad. Si notas compactación, malos olores o acumulación de sales, revisa la mezcla antes de volver a regar. Con el tiempo la mezcla se degrada y pierde esos espacios, así que conviene renovarla cuando deje de drenar bien.

Marcar la revisión hecha declara que ya la realizaste. El sistema no inspecciona el sustrato.',40,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('4a0a2210-b48d-52a8-9058-a6c23d3f2cbc'::uuid,'riego-revision','¿Cuándo debo revisar el riego de mis plantas?','Etapa de crecimiento. Revisa antes de regar, no por un horario fijo: toca el sustrato un poco por debajo de la superficie. La velocidad con que se seca cambia con el tamaño de la planta, la luz, la temperatura y el recipiente.

Que una planta se marchite no prueba que le falte agua: el exceso de riego también la marchita. Un sustrato siempre empapado deja a las raíces sin aire y puede dañarlas. Evita que quede agua estancada.

La lectura de humedad, cuando existe, es un dato más. Confírmala revisando la planta y el sustrato.',50,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('0cb10161-67a5-5b32-b6e7-2858e80f0e6e'::uuid,'deposito-recarga','¿Qué significa rellenar el depósito y registrar la recarga?','Rellenar es añadir agua limpia al depósito con tus propias manos. Después, «Ya rellené el depósito» guarda la fecha de ese cuidado.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo.',60,'publicada','','',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('492a0e27-a4ad-5bff-bc1a-d693e5a6cb6a'::uuid,'mangueras-goteros','¿Cómo reviso las mangueras y los goteros?','Mira que las mangueras no estén dobladas, aplastadas ni sueltas, y que no haya fugas en las uniones. Comprueba que los cables y las conexiones estén secos.

Observa si cada gotero entrega agua de forma parecida a los demás. Un gotero que no gotea puede estar obstruido o tener la manguera doblada.

Si encuentras una fuga o algo no parece seguro, usa el paro físico del equipo y solicita soporte técnico. «Registrar inspección» declara que hiciste la revisión; el sistema no la comprueba.',70,'publicada','','',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('75729f99-13f0-5f6d-95e8-acd12f6d7268'::uuid,'cosecha-registro','¿Cómo identifico y registro una cosecha?','Etapa de cosecha. Fíjate en el fruto y no en una fecha: firme, de tamaño completo y con el color final de su variedad. El tiempo y la cantidad de frutos varían de una planta a otra.

Corta con utensilios limpios y deja un poco de tallo unido al fruto, sin tirar para no romper las ramas. Usa guantes: el habanero irrita la piel y los ojos. Retirar los frutos maduros con regularidad favorece que la planta siga produciendo.

Después, «Registrar cosecha» guarda la fecha de lo que ya hiciste. El sistema no detecta la cosecha ni la comprueba.',80,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('e4848719-fa76-5bbe-8267-8c140f0db5ac'::uuid,'sin-lecturas','¿Qué hago si no hay lecturas o el dispositivo está desconectado?','Sin lecturas válidas no puede deducirse el estado de la planta: «sin datos» no significa que esté bien ni que le falte agua. Una lectura antigua tampoco describe lo que ocurre ahora.

Mientras tanto, revisa directamente las plantas, el sustrato y el depósito. Comprueba que el equipo tenga corriente y que tu red Wi-Fi funcione.

Si el problema continúa, repórtalo en Soporte técnico.',90,'publicada','','',1,now(),now(),NULL,NULL)
 ON CONFLICT (clave) DO NOTHING;

-- Privilegios mínimos del rol de la aplicación (igual que sql/privilegios.sql).
GRANT SELECT,INSERT ON public.datos_guiacuidado TO chilito_pkg_runtime;
GRANT UPDATE(pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,actualizado_en,actualizado_por_id) ON public.datos_guiacuidado TO chilito_pkg_runtime;

-- Capacidad nueva (Django la crearía al migrar). Sin asignarla a ninguna cuenta.
INSERT INTO public.auth_permission(name,content_type_id,codename)
 SELECT 'Crear, editar, publicar y retirar guías de cuidado',c.id,'gestionar_guias' FROM public.django_content_type c
 WHERE c.app_label='datos' AND c.model='dispositivo'
 ON CONFLICT (content_type_id,codename) DO NOTHING;

INSERT INTO public.django_migrations(app,name,applied) VALUES
 ('datos','0011_guias_cuidado',now()),
 ('datos','0012_guias_iniciales',now());

COMMIT;

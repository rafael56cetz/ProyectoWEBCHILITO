"""Arranque en la nube sin textos legales publicados (bug funcional: el superadministrador quedaba bloqueado).

Sin términos ni aviso de privacidad publicados, el trigger diferido `registro_exige_aceptacion` impedía crear cualquier
cuenta. Por eso nunca existía la cuenta que se designa superadministradora (`chilito_designar_super_admin`) y nadie
podía publicar los textos desde el panel.

La regla nueva admite una sola excepción y conserva todo lo demás:
· no hay términos o no hay aviso de privacidad publicados, **y**
· la transacción del alta fijó `chilito.arranque_legal = 'on'` (la aplicación solo lo hace con CHILITO_BYPASS_LEGAL_CHECK=1), **y**
· no existe ninguna otra cuenta: es la primera de una base vacía.

En cuanto hay textos publicados u otra cuenta, la excepción no tiene efecto, aunque la variable siga activa. La cuenta
creada así queda con los textos pendientes de aceptar (`chilito_aceptaciones_pendientes`) y los acepta al publicarlos.

Al revertir se restaura la función original de web.0002.
"""
from django.db import migrations

CON_ARRANQUE = r"""
CREATE OR REPLACE FUNCTION public.chilito_registro_exige_aceptacion() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE t uuid := public.chilito_documento_vigente('terminos');
        a uuid := public.chilito_documento_vigente('aviso_privacidad');
BEGIN
 IF t IS NULL OR a IS NULL THEN
  -- Arranque inicial: solo la primera cuenta de una base vacía y solo si la aplicación lo pidió en esta transacción.
  IF coalesce(current_setting('chilito.arranque_legal', true), '') = 'on'
     AND NOT EXISTS(SELECT 1 FROM public.cuentas_usuario u WHERE u.id <> NEW.id) THEN
   RETURN NULL;
  END IF;
  RAISE EXCEPTION 'No hay términos y aviso de privacidad publicados: publícalos antes de abrir el registro' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='aceptacion_terminos' AND d.documento_id=t)
 OR NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='lectura_aviso' AND d.documento_id=a) THEN
  RAISE EXCEPTION 'Para crear la cuenta hay que aceptar los términos y el aviso de privacidad vigentes' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
"""

ORIGINAL = r"""
CREATE OR REPLACE FUNCTION public.chilito_registro_exige_aceptacion() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE t uuid := public.chilito_documento_vigente('terminos');
        a uuid := public.chilito_documento_vigente('aviso_privacidad');
BEGIN
 IF t IS NULL OR a IS NULL THEN
  RAISE EXCEPTION 'No hay términos y aviso de privacidad publicados: publícalos antes de abrir el registro' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='aceptacion_terminos' AND d.documento_id=t)
 OR NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='lectura_aviso' AND d.documento_id=a) THEN
  RAISE EXCEPTION 'Para crear la cuenta hay que aceptar los términos y el aviso de privacidad vigentes' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0007_ciclos_planta'),
    ]

    operations = [
        migrations.RunSQL(sql=CON_ARRANQUE, reverse_sql=ORIGINAL),
    ]

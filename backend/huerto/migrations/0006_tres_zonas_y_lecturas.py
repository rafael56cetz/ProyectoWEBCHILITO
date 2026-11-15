from django.db import migrations
FORWARD=r'''
-- Serialize provisioning and reject invalid legacy rows before adding cardinality rules.
LOCK TABLE public.huerto_huerto, public.huerto_zona IN SHARE ROW EXCLUSIVE MODE;
INSERT INTO public.huerto_zona(huerto_id,numero,nombre,cultivo)
 SELECT h.id,n,'Planta '||n,'Chile habanero' FROM public.huerto_huerto h
 CROSS JOIN generate_series(1,3) n
 ON CONFLICT(huerto_id,numero) DO NOTHING;
CREATE FUNCTION public.chilito_crear_tres_zonas() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 INSERT INTO public.huerto_zona(huerto_id,numero,nombre,cultivo)
 SELECT NEW.id,n,'Planta '||n,'Chile habanero' FROM generate_series(1,3) n;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_crear_tres_zonas AFTER INSERT ON public.huerto_huerto
 FOR EACH ROW EXECUTE FUNCTION public.chilito_crear_tres_zonas();
CREATE FUNCTION public.chilito_conservar_zona() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Las tres zonas se conservan; no se permite borrarlas' USING ERRCODE='23514';
END $$;
CREATE TRIGGER chilito_conservar_zona BEFORE DELETE ON public.huerto_zona
 FOR EACH ROW EXECUTE FUNCTION public.chilito_conservar_zona();
CREATE FUNCTION public.chilito_lectura_exige_membresia() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE garden bigint;
BEGIN
 SELECT huerto_id INTO garden FROM public.huerto_aviso WHERE id=NEW.aviso_id;
 PERFORM 1 FROM public.huerto_membresia
 WHERE usuario_id=NEW.usuario_id AND huerto_id=garden AND activa FOR UPDATE;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'Membresia activa requerida' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_lectura_exige_membresia BEFORE INSERT OR UPDATE ON public.huerto_avisoleido
 FOR EACH ROW EXECUTE FUNCTION public.chilito_lectura_exige_membresia();
REVOKE ALL ON FUNCTION public.chilito_crear_tres_zonas(), public.chilito_conservar_zona(),
 public.chilito_lectura_exige_membresia() FROM PUBLIC;
'''
REVERSE='''
DROP TRIGGER chilito_lectura_exige_membresia ON public.huerto_avisoleido;
DROP FUNCTION public.chilito_lectura_exige_membresia();
DROP TRIGGER chilito_conservar_zona ON public.huerto_zona;
DROP FUNCTION public.chilito_conservar_zona();
DROP TRIGGER chilito_crear_tres_zonas ON public.huerto_huerto;
DROP FUNCTION public.chilito_crear_tres_zonas();
'''
class Migration(migrations.Migration):
    dependencies=[('huerto','0005_aviso_aviso_titulo_significativo_and_more')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]

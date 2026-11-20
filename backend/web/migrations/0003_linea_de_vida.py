"""Línea de vida: cada planta nace con su etapa inicial en huerto_planta_etapa.

Hasta ahora el historial solo lo llenaba planta_historial (al cambiar la etapa), y las plantas creadas por
crear_plantas no tenían fila. Esta migración añade el trigger de la etapa inicial y rellena las plantas que
no tienen ninguna fila. Al revertirla se quitan el trigger y la función; el relleno se queda."""
from django.db import migrations

ETAPA_INICIAL = r"""
-- Al nacer una planta (crear_plantas) queda registrada su etapa inicial, normalmente «sin_sembrar».
CREATE FUNCTION public.chilito_planta_etapa_inicial() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO huerto_planta_etapa(planta_id, etapa, desde, registrada_por_id)
 VALUES (NEW.id, NEW.etapa, chilito_hoy(), chilito_actor());
 RETURN NULL;
END $$;
CREATE TRIGGER planta_etapa_inicial AFTER INSERT ON huerto_planta FOR EACH ROW
 EXECUTE FUNCTION chilito_planta_etapa_inicial();
-- Igual que las demás funciones de apoyo (0002): la usan los triggers con los permisos de quien escribe.
GRANT EXECUTE ON FUNCTION public.chilito_planta_etapa_inicial() TO chilito_pkg_runtime, chilito_pkg_iot;
"""

# Plantas que aún no tienen ninguna fila: su etapa actual desde que empezó o, si no tiene fecha
# (sin_sembrar), desde el día en que se creó su huerto en Mérida.
RELLENO = r"""
INSERT INTO huerto_planta_etapa(planta_id, etapa, desde, registrada_por_id)
SELECT p.id, p.etapa, coalesce(p.etapa_desde, (h.creado_en AT TIME ZONE 'America/Merida')::date), NULL
FROM huerto_planta p JOIN huerto h ON h.id = p.huerto_id
WHERE NOT EXISTS (SELECT 1 FROM huerto_planta_etapa e WHERE e.planta_id = p.id)
ORDER BY p.id;
"""

QUITAR_ETAPA_INICIAL = r"""
DROP TRIGGER planta_etapa_inicial ON huerto_planta;
DROP FUNCTION public.chilito_planta_etapa_inicial();
"""


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0002_reglas_v2'),
    ]

    operations = [
        migrations.RunSQL(sql=ETAPA_INICIAL, reverse_sql=QUITAR_ETAPA_INICIAL),
        migrations.RunSQL(sql=RELLENO, reverse_sql=migrations.RunSQL.noop),
    ]

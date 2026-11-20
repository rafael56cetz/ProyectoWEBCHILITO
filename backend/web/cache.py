"""Caché de cuotas en PostgreSQL que nunca desaloja entradas vigentes (auditoría M-3).

La caché `default` guarda los contadores de intentos de allauth (`login_failed`, `vincular_dispositivo`, …) y los de la web
(`web-rate`). allauth no permite elegir otro alias, así que la protección va en el propio backend.

`DatabaseCache` de Django, al pasar de `MAX_ENTRIES`, borra los expirados y después un tercio de las claves aunque sigan
vigentes. Quien generara muchas claves distintas (correos o identificadores inventados) podía así reiniciar el contador de
fallos de una cuenta concreta. Aquí la purga solo quita lo expirado: un contador vigente vive hasta su caducidad (como mucho
`TIMEOUT`). La tabla la limpia también `chilito_mantenimiento_periodico()`.
"""
from django.core.cache.backends.db import DatabaseCache
from django.db import connections


class CacheSinDesalojo(DatabaseCache):
    def _cull(self, db, cursor, now, num):
        connection = connections[db]
        cursor.execute(
            'DELETE FROM %s WHERE %s < %%s' % (connection.ops.quote_name(self._table), connection.ops.quote_name('expires')),
            [connection.ops.adapt_datetimefield_value(now)],
        )

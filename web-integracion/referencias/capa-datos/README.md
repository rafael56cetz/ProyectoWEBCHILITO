# Capa de datos de El Chilito

Paquete separado para la entrega web del **28 de octubre de 2026**, preparado y validado el 27 de octubre. Incluye persistencia y servicios Django de datos, **verificados en PostgreSQL 17.11 aislado con datos sintéticos**. No conecta el frontend ni añade una API HTTP. Los originales permanecen intactos.

## Qué contiene y qué se comprobó

- Nueve entidades nuevas: recurso/dispositivo, mantenimiento, caso, permiso de soporte, sesión técnica, validación de versión, revisión de conocimientos, solicitud y auditoría.
- Modelos y cinco migraciones nuevas; se conservan las siete migraciones históricas propias de cuentas/huerto sin reescribirlas.
- Funciones de persistencia y consulta en `backend/datos/services.py`, con cuenta activa/verificada, membresía o capacidades explícitas según operación.
- `el_chilito.sql` **actualiza una línea base Django existente** al esquema completo de este alcance. Es SQL generado de las migraciones nuevas, no un instalador autónomo de las tablas de autenticación. La instalación vacía se explica abajo.
- `roles.sql` y `privilegios.sql` requieren contextos administrativos distintos del runtime.
- **42 pruebas PostgreSQL y nueve sin base aprobadas (51 en total)**. También aprobaron instalación vacía, actualización SQL, comparación de restricciones, privilegios del runtime y respaldo/restauración sintéticos. Docker ya está accesible. Véase [resultado-pruebas.md](resultado-pruebas.md) para correcciones, evidencia y límites.

No existen tablas de lecturas, credenciales de sensores ni modelos de IA. Las solicitudes web se conservan como `pending`; nunca se convierten en actuación, despliegue o reinicio confirmado. WebAuthn, ARCO y políticas legales están fuera de esta entrega. La confirmación técnica del registro no representa documentos legales aprobados.

## Versiones y dependencias

Se comprobaron Python 3.13.17, Django 5.2.18, django-allauth 65.20.0 y psycopg 3.3.6 en el entorno local existente. Las dependencias fijadas están en `backend/requirements-lock.txt`. El SQL se ejecutó en PostgreSQL **17.11**, imagen oficial `postgres:17`, dentro de un contenedor efímero.

Se puede reutilizar el entorno ya disponible:

```sh
cd '<paquete-historico>'
PY='<entorno-python>/bin/python'
"$PY" backend/manage.py check
```

En otro equipo, crear un entorno propio e instalar `backend/requirements-lock.txt`. No copiar entornos, `.env`, contraseñas, dumps ni archivos privados del proyecto original.

## Prueba automática de principio a fin

Con Docker autorizado para la cuenta del operador y la imagen oficial `postgres:17` disponible:

```sh
"$PY" backend/tools/verificar_postgres.py
```

El programa crea un contenedor con nombre único y etiqueta `elchilito.synthetic-data-test=true`, almacenamiento efímero `tmpfs` y puerto aleatorio publicado **solo en 127.0.0.1**. Genera credenciales transitorias en memoria y un archivo temporal de modo 0600; no las imprime. No monta datos existentes ni accede a otras bases. Al terminar detiene únicamente ese contenedor; no borra volúmenes ajenos.

Dentro de ese servidor verifica: baseline histórica → datos sintéticos → SQL de actualización → comprobación Django; instalación vacía por `migrate` en otra base; catálogo de restricciones equivalente; suite Django; operaciones con runtime limitado y denegaciones; respaldo/restauración en una tercera base sintética. **La ejecución final aprobó**; el resultado efectivo queda en `evidencias/ejecucion-postgres.json` y las 51 pruebas en `evidencias/pruebas-postgres-stdout.txt`.

Si el programa falla, no interpretar un archivo parcial como aprobación. Conservar el estado y diagnosticar antes de repetir. El script usa una instancia nueva en cada ejecución y aborta al encontrar nombres de roles inesperados en ella.

## Instalación manual vacía

Solo en un PostgreSQL aislado administrado para estas pruebas:

1. Como administrador PostgreSQL, ejecutar `roles.sql`. Crea `chilito_pkg_owner` y `chilito_pkg_runtime` sin secretos incrustados, y las bases `chilito_datos_sinteticos` y `test_chilito_datos_sinteticos`. Falla si los roles/bases ya existen; no los altera ni elimina automáticamente.
2. Establecer autenticación externa para ambos roles, por ejemplo `\password` interactivo y `PGPASSFILE` protegido. No poner contraseñas en SQL, historial de terminal ni documentación. Preferir SCRAM-SHA-256 en `pg_hba.conf`; revisar verificación de transporte según la conexión.
3. Configurar las variables no secretas `CHILITO_DB_HOST`, `CHILITO_DB_PORT`, `CHILITO_DB_USER=chilito_pkg_owner`, `CHILITO_DB_NAME=chilito_datos_sinteticos`. El perfil del paquete rechaza otros nombres. La contraseña puede proceder de libpq/PGPASSFILE o `CHILITO_DB_PASSWORD` suministrado externamente.
4. Elegir **una** ruta:

**Ruta Django recomendada para incorporar el paquete:**

```sh
"$PY" backend/manage.py migrate --noinput
"$PY" backend/tools/validar_instalacion.py
```

**Ruta para comprobar el SQL entregado en una base inicialmente vacía:**

```sh
"$PY" backend/tools/preparar_base.py
psql --dbname=chilito_datos_sinteticos --username=chilito_pkg_owner --host=127.0.0.1 --port=55432 -v ON_ERROR_STOP=1 -f el_chilito.sql
"$PY" backend/tools/validar_instalacion.py
```

Usar el puerto real del servidor. `preparar_base.py` instala las 31 migraciones de dependencias y baseline que aparecen en `evidencias/plan-migraciones.json`. No es correcto ejecutar `el_chilito.sql` antes de ellas: las FK necesitan `cuentas_usuario`, y las modificaciones necesitan el huerto anterior.

El SQL ejecuta DDL y los registros **correspondientes a esas operaciones reales** en `django_migrations`, dentro de una transacción. `validar_instalacion.py` comprueba el plan y dispara `post_migrate` normal para content types/permisos. No se usa `--fake`. No ejecutar el SQL dos veces; rechaza una integración ya registrada. Una base instalada mediante `migrate` tampoco necesita aplicar después ese SQL.

5. Como propietario de la base, ejecutar `privilegios.sql`, suministrando `-v db_name=chilito_datos_sinteticos` y `ON_ERROR_STOP=1`. Los cambios de configuración de rol están en `roles.sql`, contexto administrador. El runtime no recibe DDL, TRUNCATE, gestión de membresías ni escritura sobre asignación de permisos.
6. Las capacidades web se asignan únicamente por un operador fuera del runtime mediante `backend/tools/asignar_capacidades.py USER_ID CAPACIDADES...`. No crea cuentas ni membresías. No hay concesiones implícitas por `is_staff`/`is_superuser`. Los grupos, si se usan, requieren revisión separada.

## Actualización del esquema anterior

No se ejecutó sobre el backend ni una base real originales. Para ensayar la actualización:

1. Partir de una **copia sintética aislada** que tenga las migraciones históricas del paquete aplicadas: cuentas 0001–0003, huerto 0001–0004 y dependencias allauth/auth/sesiones fijadas. Conservar respaldo y comprobar su restauración por separado.
2. Verificar que los siete archivos históricos coincidan por hash con `evidencias/huellas-fuentes.json`. No editar ni regenerar esas migraciones.
3. Inspeccionar conflictos de reglas agregadas manualmente por scripts previos. Si el SQL del PDF ya se aplicó a mano, no asumir equivalencia ni borrar sus reglas automáticamente: resolver la diferencia de historial y esquema bajo revisión antes de continuar. Este paquete no adopta reglas mediante `--fake`.
4. Ejecutar `migrate --plan`; elegir `migrate` o `el_chilito.sql`, conforme a las rutas anteriores. El SQL comprueba baseline y ausencia de las migraciones nuevas. Datos existentes sin texto significativo hacen fallar la transacción; no se inventan correcciones.
5. La actualización conserva nombres/cultivos/avisos/membresías. Completa únicamente números de zona faltantes con nombres iniciales; los huertos nuevos reciben las tres zonas mediante trigger. El script no crea huertos ni concede membresías a cuentas nuevas.
6. Validar catálogo, datos y pruebas antes de cambiar a runtime. No interpretar `CREATE TABLE IF NOT EXISTS` como una actualización: este paquete usa migraciones/ALTER y reglas explícitas.

El archivo SQL exige esquema `public`, base dedicada y ejecución como propietario. No modifica roles de máquina ni incorpora secretos. Sus funciones usan privilegios del invocador; no hay `SECURITY DEFINER` ni RLS decorativa.

## Validación y lectura de evidencias

```sh
"$PY" backend/manage.py check
"$PY" backend/manage.py makemigrations --check --dry-run
"$PY" backend/tools/generar_sql.py
"$PY" backend/manage.py test datos.tests.test_integridad.PoliticaPasswordSinBaseTests datos.tests.test_servicios.TokenContractWithoutDatabaseTests datos.tests.test_contrato --verbosity 2
```

Para PostgreSQL, usar el harness anterior. Las pruebas `TransactionTestCase` usan **test_chilito_datos_sinteticos** precreada para no conceder CREATEDB al propietario. El teardown hace TRUNCATE como propietario, capacidad que no posee el runtime; no confundirlo con un borrado permitido al usuario de la web.

El compilador SQL funciona sin conexión y falla si una operación intenta conectarse. `makemigrations --check` verificó el estado de modelos sin diferencias, pero emitió aviso porque no pudo consultar el historial vivo. Eso no demuestra consistencia de una base activa.

## Recuperación y límites operativos

El harness ejecutó `pg_dump -Fc` y `pg_restore --exit-on-error` solo de los datos sintéticos, sin imprimir ni conservar el dump como entregable. Coincidieron las restricciones y su estado de validación, y las cantidades de registros de `cuentas_usuario`, `huerto_zona`, `datos_mantenimiento` y `datos_auditoria`. La comparación normaliza únicamente dos conversiones equivalentes de arrays literales de texto que PostgreSQL reescribe al restaurar; conserva valores, orden y operadores. No acredita equivalencia completa de todos los objetos ni del contenido fila por fila. Para producción, usar un rol de respaldo protegido, cifrar/restringir copias y probar restauración en otra instancia; conservar roles y secretos externos mediante su procedimiento independiente.

La reversión de una integración con historia no debe consistir en eliminar tablas: restaurar una copia comprobada en una base separada y verificar antes de intercambiar conexiones. No hay plazo automático de eliminación de historia; se conserva y se protege con FK y reglas inmutables. El propietario sigue siendo una identidad de confianza capaz de alterar el esquema; la defensa frente a compromiso de ese operador requiere controles de operación y copias externas.

## Incorporación futura al backend

Tras aprobar PostgreSQL, incorporar a una rama de integración los cambios de `huerto/models.py`, migraciones 0005/0006, la app `datos` y configuración pertinente. Conservar las migraciones históricas. Añadir `datos` a INSTALLED_APPS, suministrar claves y rol runtime externos y aplicar privilegios revisados. No sustituir el proyecto original completo por `integration_config`: ese perfil solo sirve a este paquete y no publica rutas.

Después implementar adaptadores HTTP con `request.user`, sesión/CSRF y respuestas neutrales, invocando los servicios. El SMTP original debe revisarse/configurarse por separado; el paquete solo usa correo en memoria. El frontend necesita los ajustes enumerados en [diccionario-y-contrato.md](diccionario-y-contrato.md). La autenticación real, fuerza bruta, WebAuthn, correo, URL y acceso de navegador no quedan funcionando por disponer de este SQL.

Quien prepare el diseño de seguridad de la etapa 3 debe recibir: roles/capacidades explícitos, frontera de autorización Django, token y revocación atómicos, historia protegida y sus límites, contrato JSON, privilegios PostgreSQL y **resultados de las pruebas del motor y pendientes de integración web**. El [documento de seguridad](seguridad-base-de-datos.md) es trazabilidad de este componente, no reemplaza ese diseño general.

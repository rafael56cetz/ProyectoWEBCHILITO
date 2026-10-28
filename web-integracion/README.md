# El Chilito — integración web, etapa 4

27 de octubre de 2026. Copia integrada local con HTML/CSS/JavaScript, API Django y PostgreSQL. Conserva las pantallas y el flujo actual. Los originales y el paquete de datos validado no se modifican. No es un despliegue ni una certificación de seguridad.

## Qué revisar

1. [Contrato de API](docs/contrato-api.md).
2. [Implementación de seguridad](docs/implementacion-seguridad.md).
3. [Resultados de integración](docs/resultados.md) y [evidencia PostgreSQL/HTTP](evidencias/validacion-integracion.json).
4. [Cuentas y correo](docs/auth.md).
5. [Configuración de correo real](docs/correo-real.md) y [estado del cierre](docs/cierre-entrega.md).

## Requisitos y versiones comprobadas

Python 3.13.17, Django 5.2.18, django-allauth 65.20.0, psycopg 3.3.6, PostgreSQL 17.11. Dependencias fijadas en [requirements-lock.txt](backend/requirements-lock.txt). La imagen oficial está fijada por digest en `backend/tools/entorno.py`. Docker debe estar accesible; no se alteran permisos de sistema automáticamente.

## Arranque local en este equipo

Desde esta carpeta:

```sh
python backend/tools/local.py start
```

Abrir **http://127.0.0.1:8780/index.html**. El comando crea una instancia PostgreSQL sintética propia, con nombre/etiqueta únicos, volumen nuevo y puerto aleatorio solo en loopback. Aplica todas las migraciones por la ruta Django, después los privilegios del runtime. El servidor utiliza `chilito_pkg_runtime`, no el propietario. Los datos permanecen en ese volumen al detenerlo.

En otro equipo, preparar un entorno externo a la entrega e instalar `backend/requirements-lock.txt`; usar el Python de ese entorno. No copiar el entorno virtual de este equipo.

La configuración secreta de desarrollo permanece fuera del proyecto, en archivos protegidos de modo 0600. En el entorno local recuperado se conserva bajo almacenamiento privado persistente del operador; las pruebas efímeras usan `/tmp`. `evidencias/entorno-local.json` solo contiene metadatos y referencias a esos archivos. No incluye credenciales. Si se pierde `/tmp`, **no eliminar el volumen ni crear otra instancia silenciosamente**: restaurar su configuración mediante el operador o preparar deliberadamente otro entorno sintético, conservando el anterior. La pérdida de claves invalida sesiones/permisos anteriores.

Para detener ambos servicios, desde otra terminal:

```sh
python backend/tools/local.py stop
```

El apagado valida identidad/etiqueta de los recursos propios, termina su servidor y detiene su contenedor. No elimina el volumen ni bases ajenas. Un segundo `start` utiliza el entorno propio registrado, consulta el puerto actual publicado en loopback y espera que PostgreSQL esté disponible. La herramienta de operador consulta el mismo puerto para evitar reutilizar el anterior si Docker lo cambió. No ejecutar dos servidores sobre 8780 al mismo tiempo.

## Cuentas, correo y asignación de recursos

El registro crea una cuenta normal y envía el código a un **buzón de pruebas local protegido**, cuya ruta imprime el arranque. No envía SMTP. Abrir los archivos de ese buzón local para obtener el código de la cuenta creada; no compartirlos ni adjuntarlos como evidencia. El código no se muestra en respuestas HTTP.

Verificar el correo no asigna huerto. Después de registrar/verificar una cuenta, un operador puede asignar el huerto de demostración:

```sh
python backend/tools/operador.py persona@example.test --huerto
```

Para asignar las capacidades existentes a otra cuenta, únicamente desde la herramienta de operador:

```sh
python backend/tools/operador.py administracion@example.test --capacidades ver_flota atender_soporte ver_gobernanza gestionar_cambios
```

Los correos son parámetros ilustrativos: usar cuentas existentes del entorno. La herramienta no crea ni verifica cuentas, no cambia contraseñas y no expone una API de administración de roles. Las cuentas `ui-user@example.test` y `ui-admin@example.test` usadas en la revisión de navegador son fixtures sintéticas de comprobación, no cuentas de producción ni un método de acceso publicado. Al cerrar la revisión se les retiró el acceso de prueba. El registro normal y la herramienta de operador permiten preparar las cuentas autorizadas.

## Instalación y actualización

La aplicación integrada elige **una ruta: migraciones Django**. En un PostgreSQL nuevo aislado, crear los roles propietario/runtime, configurar externamente la conexión como propietario y ejecutar:

```sh
python backend/manage.py migrate --noinput
python backend/manage.py makemigrations --check --dry-run
```

Después aplicar [sql/privilegios.sql](sql/privilegios.sql) como propietario, con `psql -v ON_ERROR_STOP=1 -v db_name=NOMBRE` y conexión explícita a esa base. Cambiar luego la conexión del servidor a `chilito_pkg_runtime`. El script del entorno local realiza esa secuencia automáticamente para sus nombres sintéticos; no es un instalador de producción.

Para actualizar una copia histórica, comprobar respaldo, historial y migraciones de cuentas/huerto; conservar las siete históricas sin reescribirlas. Revisar diferencias de reglas aplicadas manualmente. Con código y baseline reconciliados, ejecutar `migrate --plan`, después `migrate`, comprobar ausencia de cambios pendientes y aplicar los privilegios revisados. No usar `--fake` como reparación automática.

`referencias/capa-datos/el_chilito.sql` se conserva **como antecedente validado**: requiere la baseline histórica, solo aplica las cinco migraciones del paquete de datos y no incluye la migración `web.0001` de idempotencia. **No ejecutarlo encima de `migrate` ni tratarlo como instalador autónomo de la aplicación integrada.** Los documentos de referencia son una selección histórica con rutas relativas; las instrucciones operativas de esta entrega son este README y `docs/`.

## Configuración externa y despliegue posterior

[.env.example](.env.example) enumera variables sin secretos reales. No se carga automáticamente: un operador suministra variables al proceso. `config.settings` separa `local`, `testing` y `deployment`. Local admite exclusivamente nombres sintéticos y hosts loopback. Deployment requiere origen HTTPS, hosts explícitos, rol runtime y `sslmode=verify-full`; cookies Secure, redirección HTTPS y HSTS. No configura proxy/VM ni se ha probado un despliegue.

El SMTP permanece apagado hasta suministrar la configuración externa. El propietario confirmó registro público a direcciones válidas: se admite el modo explícito `any-valid`, conservando cuotas de servidor; el modo `restricted` sigue disponible para limitar pruebas. Véase `docs/correo-real.md`. No se leyeron credenciales antiguas ni se ha comprobado entrega externa. La dockerización corresponde al compañero; esta revisión no prepara ni verifica una VM.

## Pruebas reproducibles

```sh
python backend/tools/verificar_integracion.py
node frontend/pruebas-contrato.cjs
```

El primer comando usa un contenedor separado y efímero; corre regresiones de datos, HTTP y operaciones reales con el rol limitado. No sustituye PostgreSQL por SQLite. El segundo verifica adaptadores JavaScript; no es una prueba de navegador. Véanse resultados y límites en `docs/resultados.md`.

No hay sensores, MQTT, IA, WebAuthn, ARCO operativo, ejecución remota ni publicación real. Solicitudes relacionadas quedan `pending`/sin confirmación. TLS, SMTP real, despliegue, respaldo de producción y revisión humana del diseño siguen siendo verificaciones posteriores.

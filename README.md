# El Chilito

Aplicación de un huerto de habanero: página pública, acceso a cuentas y paneles de usuario y administración. El servidor usa Django y PostgreSQL; la interfaz usa HTML, CSS y JavaScript sin un proceso de compilación.

## Dónde encontrar cada cosa

| Carpeta o archivo | Para qué sirve |
|---|---|
| `frontend/index.html` | Entrada de la página y orden de carga de los estilos y scripts (el orden importa). |
| `frontend/modelos/` | Modelo: peticiones al servidor, validaciones y adaptación de sus respuestas. |
| `frontend/vistas/` | Vista: plantillas y funciones que dibujan la interfaz. |
| `frontend/controladores/` | Controlador: eventos de botones y formularios, navegación y coordinación de pantallas. |
| `frontend/vistas/estilos/` | Apariencia de la página. |
| `frontend/vistas/imagenes/`, `frontend/vistas/fuentes/` | Fotografías, ilustraciones y tipografía local. |
| `frontend/pruebas/pruebas.cjs` | Todas las pruebas de JavaScript y de la separación Modelo-Vista-Controlador, en un solo archivo. |
| `backend/config/` | Configuración de Django, rutas y perfiles local, pruebas y producción. |
| `backend/cuentas/` | Registro, inicio de sesión, verificación de correo y segundo factor. |
| `backend/huerto/` | Huertos, plantas, membresías y avisos. |
| `backend/datos/` | Operación del huerto: mantenimiento, soporte, vinculación, consultas y guías. |
| `backend/privacidad/` | Documentos versionados, decisiones de cookies y registro de aceptaciones. |
| `backend/web/` | Entrega de la interfaz, API compartida y controles de sesión. |
| `backend/tools/` | Comandos de arranque, comprobación, pruebas y preparación de entrega. |
| `sql/` | Instalación y permisos de PostgreSQL. Ver `sql/instalacion/LEEME.md`. |

El frontend sigue el patrón Modelo-Vista-Controlador. Cada capa tiene un archivo por área (`cuenta`, `publico`, `huerto`, `equipos`, `administracion` y `comun`), así que el área que buscas está en el mismo nombre en las tres carpetas: `modelos/huerto.js` pide y valida los datos, `vistas/huerto.js` los dibuja y `controladores/huerto.js` atiende los botones. Dentro de cada archivo, cada parte empieza con una línea `// ── Nombre ──`. Esta separación evita mezclar peticiones al servidor con el código que dibuja la página.

Los nombres de las aplicaciones Django se conservan porque también identifican tablas, permisos y dependencias de migraciones. Las carpetas `migrations/` guardan el historial de la base; sus archivos no son copias sobrantes.

## Textos legales

El aviso de privacidad, los términos y la política de cookies viven en la base de datos. Se redactan, publican y retiran desde Administración → Textos legales (capacidad correspondiente, con segundo factor); el servidor los sanea con una lista blanca antes de mostrarlos. No hay archivos HTML que editar.

## Cambiar otras partes de la interfaz

- Textos de la portada: `frontend/vistas/publico.js` (parte «Pagina publica»).
- Formularios de acceso: `frontend/vistas/cuenta.js` (parte «Acceso»).
- Navegación entre pantallas y comprobación de sesión: `frontend/controladores/enrutador.js`.
- Iconos y piezas comunes: `frontend/vistas/comun.js` (parte «Componentes»).

La interfaz contiene 19 archivos JavaScript (6 modelos, 7 vistas y 6 controladores, de los cuales `vistas/navegacion.js` y `controladores/enrutador.js` van aparte) y 7 hojas de estilo. Los estilos están agrupados en `base.css`, `acceso.css`, `panel.css`, `navegacion.css`, `apariencia.css`, `cookies.css` y `comercial.css`. Conservan el orden de las reglas anteriores; agruparlos reduce archivos, pero no significa que se haya cambiado el diseño ni eliminado todas las sobrescrituras. Mantener el orden de carga de `index.html`: los modelos, luego las vistas, luego los controladores, y al final `vistas/navegacion.js` y `controladores/enrutador.js`. Un archivo que se ejecuta al cargar solo puede usar lo que ya se cargó antes.

## Arranque local

Desde la raíz del proyecto, usando un entorno Python con las dependencias de `backend/requirements-lock.txt` instaladas. Se necesitan PostgreSQL preparado y el archivo `.env` en la raíz. Es el único archivo de entorno: lo usan la página y las pruebas. En la copia para la nube, `armar_entrega.py` genera `.env.example` con las mismas claves y sin valores.

```sh
python3 backend/tools/servir_local.py
```

Abrir `http://localhost:8780`. La herramienta carga `.env` y la configuración SMTP externa si está indicada; no muestra sus valores. La aplicación usa `chilito_pkg_runtime`. Los cambios de esquema usan el rol propietario según la guía SQL.

## Comprobaciones y pruebas

Las pruebas del frontend se ejecutan con Node.js desde la raíz. Usan respuestas simuladas; no requieren iniciar el servidor ni acceder a PostgreSQL o al correo:

```sh
node frontend/pruebas/pruebas.cjs
```

Cubren contratos de datos, validaciones y límites entre datos, pantallas y acciones. No sustituyen la comparación visual ni una prueba completa en navegador.

Para comprobar que el servidor local entrega los archivos de esta carpeta:

```sh
python3 backend/tools/comprobar_frontend_local.py
```

La cantidad de archivos se calcula desde `index.html`. Un resultado `coincide` acredita la raíz y sus scripts/estilos; no comprueba la cuenta iniciada, los textos legales obtenidos por API ni el funcionamiento de cada pantalla. Ver las explicaciones de resultados en `backend/tools/README.md`.

Las pruebas del servidor requieren PostgreSQL y, en el `.env`, `CHILITO_TEST_DB_USER=chilito_pkg_owner` y `CHILITO_TEST_DB_PASSWORD`:

```sh
python3 backend/tools/pruebas_local.py suite
python3 backend/tools/pruebas_local.py flujos
```

`suite` usa el corredor de pruebas de Django. `flujos` comprueba operaciones con el rol limitado. Crean y eliminan la base temporal fija `test_chilito_integracion_sinteticos`; no debe contener datos que quieras conservar. Los flujos también usan el rol de la aplicación (`CHILITO_DB_USER`) del mismo `.env`. El correo de pruebas se simula o queda en el entorno de pruebas; `probar_correo.py` es una herramienta distinta que sí envía un mensaje real.

## Base de datos y entrega

La guía `sql/instalacion/LEEME.md` explica la instalación nueva y las actualizaciones de una base existente. `03_esquema_completo.sql` se genera desde las migraciones y los permisos; no se edita a mano ni se vuelve a ejecutar sobre una base con datos. Mantener los parches e históricos permite actualizar instalaciones anteriores.

En la copia original, `python3 backend/tools/armar_entrega.py [destino]` prepara una carpeta externa con los archivos permitidos. Incluye las rutas nuevas de la interfaz; excluye los archivos de entorno reales y las cachés. Si el destino ya tiene la marca de una entrega anterior, reemplaza su contenido conservando `.git`. Preparar la copia no publica ni despliega la aplicación.

## Decisiones pendientes del propietario

- Si se guardará IP o navegador (hoy no).
- Si las cuentas existentes deben aceptar la versión nueva al iniciar sesión.
- Si el correo debe verse completo en la pantalla o solo parcialmente (por ejemplo, `ra***@gmail.com`).

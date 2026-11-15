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
| `frontend/legales/` | Los tres textos legales editables en HTML. |
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

## Cambiar el aviso de privacidad y los otros textos

Editar directamente el archivo que corresponda:

| Documento visible | Archivo editable | Ruta de la página |
|---|---|---|
| Aviso de privacidad | `frontend/legales/aviso-privacidad.html` | `#privacidad` |
| Términos y condiciones | `frontend/legales/terminos.html` | `#terminos` |
| Política de cookies | `frontend/legales/politica-cookies.html` | `#cookies` |

Son fragmentos HTML: contienen solo el cuerpo del documento, sin repetir `<html>`, `<head>` o `<body>`. El encabezado, el pie y el diseño los añade la página. Por ejemplo:

```html
<h3>Nombre de la sección</h3>
<p>Aquí puedes escribir el texto del documento.</p>
```

Se admiten párrafos, títulos `h2`/`h3`, `strong`, `em`, listas `ul`/`ol`/`li`, saltos `br` y enlaces `a`. Los títulos `h2` se muestran como `h3` para conservar la jerarquía visual actual. El servidor filtra el HTML: no incluir scripts, estilos, clases ni eventos. Para enlaces, usar anclas `#`, rutas locales que empiecen con `/`, o direcciones `https:`, `http:` y `mailto:`.

Guardar cambia el cuerpo servido en la siguiente consulta del documento. Después, recargar su página para revisarlo. Si el cuerpo está vacío, se muestra que está en redacción; no se recupera automáticamente un borrador antiguo.

**Editar el texto y registrar una versión publicada son operaciones distintas.** El sistema compara la huella SHA-256 de los bytes del archivo con la versión registrada. Si no coincide, el texto se presenta como borrador sin registrar. Cambiar el HTML no reescribe aceptaciones anteriores ni registra una versión nueva. Esta reorganización no añade un comando de publicación: esa operación debe seguir la política de versiones existente y revisarse por separado.

Los textos legales se editan solo en `frontend/legales/*.html`.

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

En la copia original, `python3 backend/tools/armar_entrega.py [destino]` prepara una carpeta externa con los archivos permitidos. Incluye las rutas nuevas de la interfaz y los HTML legales; excluye los archivos de entorno reales y las cachés. Si el destino ya tiene la marca de una entrega anterior, reemplaza su contenido conservando `.git`. Preparar la copia no publica ni despliega la aplicación.

## Propuesta: ver quién aceptó, cuándo y qué versión (cookies, términos y aviso)

Esta sección es una **propuesta**: describe lo que falta y cómo resolverlo. Nada de lo que sigue está implementado todavía.

### El problema

El proyecto exige que se pueda **ver** quién aceptó o rechazó, a qué hora, qué decidió y con qué texto. Hoy los datos se guardan correctamente, pero **solo se pueden leer entrando a PostgreSQL con SQL**. La página no tiene ninguna pantalla para consultarlos. Además, la versión «0.2-borrador» que se registra al crear una cuenta corresponde a los `.md` antiguos, no al HTML que se muestra ahora.

### Dónde se guarda hoy

Todo vive en la base de datos, en tablas que PostgreSQL protege contra modificaciones y borrados (migración `0002`):

| Qué | Dónde | Qué queda registrado |
|---|---|---|
| Aceptó o rechazó las cookies de estadísticas | `privacidad_decisionprivacidad`, con `acto = 'cookies'` | Fecha y hora, aceptó o rechazó, versión del aviso y de la política vigentes, y un identificador seudónimo del navegador. Se vincula a la cuenta si la persona tenía sesión. |
| Aceptó los términos y leyó el aviso al crear la cuenta | La misma tabla, con `acto = 'aceptacion_terminos'` y `'lectura_aviso'` | Fecha y hora, cuenta, y la versión del documento. |
| Historial de cada acto | `privacidad_eventoprivacidad` | Quién actuó, qué acción y su resultado. |
| Versiones de los textos | `privacidad_documentoversion` | Tipo, versión, huella SHA-256 y fecha de registro. |

Cómo se consulta hoy:
- **Cookies:** el script `sql/instalacion/07_consultar_cookies.sql`, como `chilito_pkg_owner`. No muestra correos a propósito.
- **Términos y aviso del registro:** no existe una consulta lista.
- **Registros de texto (logs):** el único registro de la aplicación en esta parte es el de un error (`privacidad-no-disponible`). No registran decisiones, y un archivo de texto tampoco serviría como evidencia: se puede editar y rotar.
- **No se guarda** IP, navegador ni ubicación. Es una decisión de privacidad; si el proyecto exige «desde dónde», debe decidirlo el propietario.

### Propuesta A: publicar la versión definitiva

La aplicación no puede publicar documentos (el rol de la aplicación no tiene permiso). Lo hace el propietario:

1. Dejar el texto final en `frontend/legales/*.html`.
2. Una herramienta nueva, `backend/tools/publicar_documento.py <tipo> <versión>`, calcula la huella SHA-256 de ese archivo y **imprime el `INSERT`** para `privacidad_documentoversion`. No escribe en la base: el propietario lo revisa y lo ejecuta con su rol. Las tablas no permiten corregir una fila, así que primero se prueba en la base temporal.
3. Guardar también el **texto completo** en la fila (columna nueva `contenido_texto`, migración nueva). Así la prueba de qué leyó la gente no depende de un archivo que alguien pueda editar o borrar.
4. No editar el HTML ya publicado. Si se edita, la página lo vuelve a mostrar como borrador. Un cambio es una versión nueva (por ejemplo, 1.1).

Qué pasa al publicar:
- **Cookies:** a todas las personas se les vuelve a pedir la decisión, porque cambió el documento vigente.
- **Cuentas existentes:** conservan su aceptación de la versión anterior. Hoy nadie vuelve a aceptar los términos nuevos. Propuesta, a decidir: un aviso único tras iniciar sesión que pida aceptar la versión nueva.

### Propuesta B: pantalla «Registro de privacidad» (solo lectura)

Una pantalla nueva en el panel de administración, con el mismo patrón que las guías y la vinculación:

- **Permiso:** capacidad nueva `ver_privacidad` (parche SQL 08, igual que los parches 06 y 07), con segundo factor obligatorio.
- **Servicio y ruta:** una consulta de solo lectura en `backend/privacidad/services.py`, con paginación (`datos/paginacion.py`), y la ruta `GET /api/admin/privacidad`. Filtros: fechas, acto y usuario.
- **Pantalla:** una parte nueva «Privacidad» en `vistas/administracion.js`, con su modelo y su controlador, enlazada desde el panel.
- **Columnas:** fecha y hora, usuario (correo, o «Visitante sin cuenta» con el identificador corto del navegador), acto en español («Aceptó cookies de estadísticas», «Rechazó cookies de estadísticas», «Aceptó los términos», «Leyó el aviso»), versión del documento y si esa decisión es la vigente.
- **Exportar** el resultado a CSV.
- **Auditoría:** cada consulta de esta pantalla se anota en la auditoría existente, porque muestra correos.
- **Pruebas:** servicio y permisos en la suite de Django (base temporal), y los textos de la pantalla en `frontend/pruebas/pruebas.cjs`.

### Orden de trabajo

1. Publicar la versión definitiva (propuesta A) y probarla en la base temporal.
2. Capacidad `ver_privacidad`, servicio y ruta.
3. Pantalla y exportación.
4. Pruebas, y capturas de la pantalla con datos sintéticos para la entrega.

### Decisiones pendientes del propietario

- Si se guardará IP o navegador (hoy no).
- Si las cuentas existentes deben aceptar la versión nueva al iniciar sesión.
- Si el correo debe verse completo en la pantalla o solo parcialmente (por ejemplo, `ra***@gmail.com`).

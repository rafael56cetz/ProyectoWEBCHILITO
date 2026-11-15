# El Chilito · Ejecución v2: base de datos nueva e interfaces

Guía para ejecutar el plan con **Claude Code (Sonnet 5.5)**, fase por fase. Contiene:

- la preparación;
- la instalación de la base en pgAdmin y del servidor;
- los cambios que hay que anotar en el diseño de seguridad;
- los **7 prompts**, uno por fase;
- las pruebas manuales de cada fase;
- el formato del informe que entrega Claude Code al terminar cada una.

---

## 0. Cómo se usa

1. **Una fase = una sesión nueva de Claude Code = una rama de Git.** No mezcles fases.
2. Abre Claude Code en la **raíz del proyecto** con el modelo **Sonnet 5.5** y el **modo plan** activado (Shift+Tab hasta ver «plan mode»). Pega el prompt de la fase.
3. Claude Code te presenta su plan (archivos y motivo). Revísalo: si crea archivos que la fase no nombra, dile que no. Aprueba y deja que trabaje.
4. Al terminar, te da el **informe de fase** (sección 6). Haz tú las **pruebas manuales** de la fase en el navegador.
5. **Mándame el informe y el resultado de tus pruebas** antes de pasar a la siguiente. Reviso que no haya código de más ni nada fuera del plan.
6. Si todo está bien: commit, fusionas la rama y pasas a la fase siguiente.

| Fase | Contenido | Rama |
|---|---|---|
| 1 | Base v2 en Django: modelos, migraciones, actor y flujos que se conservan | `fase-1-base-v2` |
| 2 | Sistema visual unificado (Liquid Glass) | `fase-2-sistema-visual` |
| 3 | Flujo principal del usuario: legales, huerto, vinculación, plantas, Mis huertos | `fase-3-flujo-usuario` |
| 4 | Operación del usuario: panel técnico, mantenimiento, soporte, avisos | `fase-4-operacion-usuario` |
| 5 | Administración nueva: equipos, administradores, legales, consentimientos, ventas | `fase-5-admin-nueva` |
| 6 | Administración adaptada: flota, consola remota, mantenimientos, solicitudes, guías | `fase-6-admin-adaptada` |
| 7 | Limpieza, verificación completa y documentación | `fase-7-cierre` |

---

## 1. Preparación (la haces tú, una sola vez)

### 1.1 Git
Si el proyecto no usa Git todavía:
```
cd <carpeta del proyecto>
git init
git add .
git commit -m "Estado antes de la v2"
```
Si ya lo usa, asegúrate de tener todo guardado (`git status` limpio).

### 1.2 Coloca los archivos

| Archivo | Destino en el proyecto |
|---|---|
| `CLAUDE.md` | raíz del proyecto |
| `el_chilito_base_v2.sql` | `sql/` |
| `FUNCIONAMIENTO-BASE-DE-DATOS-v2.md` | `sql/` |
| `pruebas_v2.py`, `prueba_depuracion.py` | `sql/pruebas/` |
| `PLAN-INTERFACES-v2.md`, `INVENTARIO-INTERFAZ-ACTUAL.md`, `EJECUCION-v2.md` (este) | `docs/` |
| Tus documentos de seguridad (Etapa 3 y Marcos de seguridad) | `docs/seguridad/` |
| Scripts antiguos (`el_chilito_base_completa.sql`, `designar_administrador.sql`, `instalacion/`, parches) | **muévelos** a `sql/historico/` |

```
git add . && git commit -m "Documentación y script de la base v2"
```

### 1.3 Variables nuevas del `.env`
Agrégalas (con valores reales generados por ti; nunca las subas a Git):
```
# Clave para el HMAC de los códigos de vinculación (64 caracteres aleatorios)
CHILITO_VINCULACION_SECRETO=<genera con: python -c "import secrets;print(secrets.token_hex(32))">
# Base nueva (de momento no la uses: ver 2.2)
CHILITO_DB_NAME_V2=chilito_v2
```

---

## 2. Instalación de la base y del servidor

### 2.1 Ahora (opcional): ver la base nueva en pgAdmin sin tocar la actual
Sirve para revisar las tablas antes de programar. **Tu base y tu página actuales siguen igual.**

1. En pgAdmin, conéctate como **postgres** a la base `postgres` y abre **Query Tool**. Crea el rol nuevo (los otros dos ya existen):
   ```sql
   CREATE ROLE chilito_pkg_iot LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
   ALTER ROLE chilito_pkg_iot SET search_path = pg_catalog, public;
   ```
   Ponle contraseña: **Login/Group Roles › chilito_pkg_iot › Properties › Definition**.
2. En la misma consola, esta línea sola:
   ```sql
   CREATE DATABASE chilito_v2_revision OWNER chilito_pkg_owner;
   ```
3. En el árbol de pgAdmin: clic derecho en **Servers › tu servidor › Databases › Refresh**. Clic derecho en `chilito_v2_revision` → **Query Tool**. Esa consola debe estar conectada como `chilito_pkg_owner`. Si tu conexión de pgAdmin es como `postgres`, crea otra conexión al servidor con el usuario `chilito_pkg_owner`.
4. **File › Open** → `sql/el_chilito_base_v2.sql` → **Execute (F5)**. Debe terminar sin errores.
5. Comprueba:
   ```sql
   SELECT count(*) FILTER (WHERE table_type='BASE TABLE') AS tablas,
          count(*) FILTER (WHERE table_type='VIEW') AS vistas
   FROM information_schema.tables WHERE table_schema='public';   -- 46 y 5
   ```
Esta base es solo para mirar. La oficial se crea en 2.2.

### 2.2 Después de la fase 1: la base oficial v2
Tu diseño de seguridad (sección 11) dice que **las migraciones de Django son la fuente de verdad**. Por eso, la base oficial la crea Django con `migrate`. El script SQL queda como referencia equivalente y comprobada.

1. **Respaldo** de tu base actual: en pgAdmin, clic derecho en `chilito_integracion_sinteticos` → **Backup…** → formato *Custom* → guárdalo fuera del proyecto.
2. Como **postgres**, crea la base nueva vacía (línea sola):
   ```sql
   CREATE DATABASE chilito_v2 OWNER chilito_pkg_owner;
   ```
3. En la terminal, en `backend/`, con tu entorno virtual activo, crea la estructura **como propietario**, solo para este comando:
   ```
   CHILITO_DB_NAME=chilito_v2 CHILITO_DB_USER=chilito_pkg_owner CHILITO_DB_PASSWORD=<contraseña del owner> python manage.py migrate
   ```
   En Windows (PowerShell), define antes las tres variables con `$env:CHILITO_DB_NAME="chilito_v2"`, etc.
4. **Publica los textos legales.** Sin ellos nadie puede registrarse. En pgAdmin, Query Tool sobre `chilito_v2` como `chilito_pkg_owner`:
   ```sql
   SELECT chilito_publicar_documento_legal('terminos', '1.0', 'Términos y condiciones', $texto$
   …pega aquí el texto completo…
   $texto$);
   SELECT chilito_publicar_documento_legal('aviso_privacidad', '1.0', 'Aviso de privacidad', $texto$ … $texto$);
   SELECT chilito_publicar_documento_legal('politica_cookies', '1.0', 'Política de cookies', $texto$ … $texto$);
   ```
   Si todavía no tienes los textos definitivos, publica una versión `0.1` con un texto provisional. Después podrás publicar la `1.0` desde el panel.
5. Cambia el `.env` para que la página use la base nueva **con el rol de la aplicación**:
   ```
   CHILITO_DB_NAME=chilito_v2
   CHILITO_DB_USER=chilito_pkg_runtime
   CHILITO_DB_PASSWORD=<contraseña de chilito_pkg_runtime>
   ```
6. Levanta el servidor como siempre (por ejemplo `python manage.py runserver 8780`) y abre `http://localhost:8780`.
7. **Regístrate** con tu correo (casillas de términos y aviso), verifica el código y activa tu app autenticadora en **Mi cuenta › Seguridad**.
8. Nómbrate super administrador. En pgAdmin, sobre `chilito_v2` como `chilito_pkg_owner`:
   ```sql
   SELECT chilito_designar_super_admin('tu-correo@dominio.com');
   ```
   Cierra sesión y vuelve a entrar: verás el panel de administración.
9. Crea también una **cuenta de usuario de prueba** con otro correo para las pruebas del lado del usuario.
10. Para tener un equipo de prueba (hasta que exista el ESP32), en pgAdmin:
    ```sql
    INSERT INTO dispositivo(identificador, mac, credencial_hash)
    VALUES ('ESP32-PRUEBA1', 'AA:BB:CC:00:00:01', repeat('x', 40));
    ```
    En la fase 5 ya podrás darlos de alta desde el panel.

**Volver atrás** si algo falla: regresa el `.env` a `chilito_integracion_sinteticos` y reinicia el servidor. Tu base anterior no se tocó.

### 2.3 Tarea periódica (cuando despliegues)
Cada hora, como `chilito_pkg_owner`: `SELECT chilito_mantenimiento_periodico();`. En local no hace falta. En Cloud SQL se programa con `pg_cron` o con Cloud Scheduler.

---

## 3. Cambios al diseño de seguridad (Etapa 3) que debes registrar

Tu documento dice que los cambios de permisos, datos o flujos deben mantener la relación requisito → amenaza → decisión → prueba (SSDF PW.1 y PW.2). Estos cambios de la v2 **contradicen o amplían** el documento actual. Actualízalo antes de entregar (o en una adenda):

| Sección | Antes | Ahora (v2) | Motivo |
|---|---|---|---|
| 7 | Acceso al huerto por **membresía activa** | El huerto tiene **dueño** (`huerto.propietario_id`); hasta 3 por cuenta | Flujo IoT nuevo: la persona crea su huerto |
| 7 | Capacidades «flota, soporte, gobernanza, cambios» | **10 capacidades**, incluida la de super admin, que solo se da desde la base; historial automático e inmutable | Petición del responsable |
| 8 | Soporte con **token de 43 caracteres** y verificador HMAC | **Sin token**: la autorización explícita (24 h, revocable) es el permiso; solo el dueño autenticado la crea; el admin «atiende» y «conecta»; revocar cierra la sesión técnica al instante | Elimina el secreto que viajaba por correo (menos superficie de ataque) |
| 2 y 11 | Solicitudes de actuadores siempre «pendientes» | Comandos con estados reales (pendiente → enviado → confirmado, fallido o expirado) | Preparación IoT |
| 2 | Documentos legales en otra entrega | Textos legales **versionados en la base**, reaceptación obligatoria y bitácora con IP recortada y navegador | Petición del responsable |
| 11 | — | Tercer rol `chilito_pkg_iot` con privilegios mínimos para MQTT e IA | Mínimo privilegio (ASVS V8, V13) |
| 11 | — | La base exige el **actor** de cada cambio y lo valida con triggers | Defensa en profundidad |
| 12 | — | Anonimización de cuentas a los 15 días (derecho de cancelación) | LFPDPPP |
| 13 | Clave de tokens de soporte | Clave `CHILITO_VINCULACION_SECRETO` para el HMAC de los códigos de vinculación | Nuevo secreto |

---

## 4. Prompts por fase

> Copia el bloque completo de la fase. No cambies el orden de las fases.

### FASE 1 · Base v2 en Django

````text
FASE 1 de docs/EJECUCION-v2.md · Rama: fase-1-base-v2

Lee completos, en este orden: CLAUDE.md, docs/seguridad/ (diseño Etapa 3), sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md,
sql/el_chilito_base_v2.sql y docs/INVENTARIO-INTERFAZ-ACTUAL.md (secciones 0, 4 y 6).

OBJETIVO
Que Django use la base v2. Las migraciones deben CREAR una base equivalente al script sql/el_chilito_base_v2.sql
(el diseño de seguridad, sección 11, dice que las migraciones son la fuente de verdad; prohibido migrate --fake).
Al terminar, los flujos que se conservan funcionan sobre la base v2; las pantallas que se rediseñan en fases
posteriores quedan desactivadas de forma limpia.

TAREAS
1. Comprueba la versión de Django. Si es menor que 5.2, detente y pregúntame (se necesitan CompositePrimaryKey,
   GeneratedField y db_default).
2. Modelos (reescribe los models.py existentes; no crees apps nuevas). Reparto de tablas:
   - cuentas: Usuario (cuentas_usuario, añade anonimizacion_solicitada_en y anonimizada_en), CapacidadHistorial.
     Usuario.Meta.permissions = las 10 capacidades con el mismo codename y nombre que la sección 15 del script.
   - huerto: Huerto, Planta (huerto_planta), PlantaEtapa (huerto_planta_etapa).
   - datos: Dispositivo, CodigoVinculacion, DispositivoEvento, Medicion, MedicionPlanta, ResumenHoraHuerto,
     ResumenHoraPlanta, Actuacion, Comando, Autodiagnostico, AutodiagnosticoRevision, Cuidado, CuidadoRevision,
     GuiaCuidado, SoporteCaso, SoporteSesion, Notificacion, IaResumen, ConsultaProducto, CorreoPendiente, Venta, Auditoria.
   - privacidad: DocumentoLegal, Finalidad, Sujeto, Decision, Preferencia, ConteoNavegacion.
   - web: Idempotencia.
   Cada modelo con db_table exacto, mismas columnas, tipos, nulos, longitudes, FK, UNIQUE e índices simples.
   Usa db_default para los DEFAULT de la base, GeneratedField para folio y estado_pago, y CompositePrimaryKey
   donde la tabla la tiene. default_permissions = () en todos los modelos menos Usuario.
3. Migraciones: borra las migraciones antiguas de cuentas, huerto, datos, privacidad y web y genera 0001_initial
   por app. Crea UNA migración web/0002_reglas_v2.py con RunSQL que aplique, copiado del script sin reescribirlo:
   las funciones (secciones 1 y 12–13), los CHECK, índices parciales y únicos por expresión que los modelos no
   declaran, los triggers, las vistas (14), los datos iniciales (15), los privilegios (16) y la tabla de caché
   cuentas_cuotas_acceso. Debe depender de las últimas migraciones de todas las apps (incluidas auth, account,
   mfa, sessions y contenttypes). Ajusta la FK medicion_planta→medicion a ON DELETE CASCADE, como en el script.
   NO incluyas la sección 0 ni BEGIN/COMMIT.
4. Equivalencia (obligatoria):
   a) Crea dos bases vacías (owner chilito_pkg_owner): una con el script y otra con `migrate`.
   b) Ejecuta sql/pruebas/pruebas_v2.py y prueba_depuracion.py contra la base creada con migrate (se configuran
      con las variables CHILITO_PRUEBAS_*, documentadas al inicio del archivo; no cambies las pruebas). Deben pasar todas.
   c) Compara ambas bases (columnas, tipos, nulos, defaults, CHECK por nombre, UNIQUE, triggers, funciones,
      vistas y privilegios por tabla y columna). Diferencias aceptables: nombres automáticos de FK e índices
      generados por Django y que las FK de Django sean DEFERRABLE. Cualquier otra diferencia se corrige en el
      modelo o en la migración, NUNCA en el script.
5. Middleware de actor en web/: en cada petición con sesión y ATOMIC_REQUESTS=True, ejecuta
   SELECT set_config('chilito.actor_id', <id del usuario>, true). Si la petición no tiene sesión, no fija nada.
6. Servicios que se CONSERVAN (adáptalos a las tablas nuevas, sin cambiar sus contratos JSON salvo lo indicado):
   - Registro (cuentas/api.py): en la misma transacción crea privacidad_sujeto (ámbito cuenta) y las dos
     privacidad_decision (aceptacion_terminos, lectura_aviso) con chilito_documento_vigente(), la IP recortada
     (IPv4 con el último bloque en 0; IPv6 a /48) y el navegador resumido («Chrome 130 · Android», sin user-agent completo).
     Quita lo de cuentas_confirmacionregistrolocal.
   - GET /api/cuenta: añade «pendingLegal»: lista de chilito_aceptaciones_pendientes(id) ([] si no hay).
     Calcula role y capabilities con los 10 codenames nuevos (cuentas.<codename>).
   - Textos legales públicos (/api/privacidad/documentos/<kind>): leen la versión vigente de documento_legal y la
     sanean con la lista blanca actual. Deja de leer frontend/legales/*.html.
   - Cookies (/api/privacidad/cookies): privacidad_decision con IP recortada, navegador y usuario si hay sesión;
     privacidad_preferencia.
   - Mis datos, perfil y bienvenida: los «eventos de privacidad» ahora van a auditoria (accion consultar_mis_datos /
     rectificar_perfil con detalle {"campo": "..."}; nunca el valor). «Huertos» = huertos activos del propietario.
   - Contacto «Consíguelo»: inserta solo consulta_producto (el aviso al correo y las notificaciones a admins las
     crea la base). El comando enviar_avisos_pendientes pasa a leer correo_pendiente.
   - Guías (/api/guias y /api/admin/guias): tabla guia_cuidado; el actor lo fija el middleware.
   - Buzón (/api/admin/consultas): consulta_producto.
   - Comando retirar_factores: audita en auditoria con accion retirar_segundo_factor.
   - Capacidades en Django: reemplaza la lista CAPS (datos/services.py) por las 10 nuevas y el mapa
     capacidad→destino de frontend/modelos/comun.js SOLO para los destinos que ya existen
     (ver_flota→admin/flota, atender_soporte→admin/soporte, gestionar_mantenimientos→admin/mantenimientos,
     atender_consultas→admin/solicitudes, gestionar_guias→admin/guias). Los demás destinos llegan en la fase 5.
7. Servicios que se REDISEÑAN después (huerto actual, avisos, mantenimiento del usuario, solicitudes, soporte,
   vinculación, admin flota, admin soporte, admin mantenimientos, admin vinculación): elimina su código que usa
   tablas que ya no existen y deja sus endpoints respondiendo 503 {"status":"error","code":"en-actualizacion"}.
   En el frontend, esas pantallas muestran el estado existente de error con «Esta sección se está actualizando.».
   No construyas nada nuevo de esas pantallas en esta fase.
8. Traduce el error 23514 de PostgreSQL en web/ a una respuesta 409 {"code":"regla-de-datos"} con un mensaje
   genérico; registra el detalle solo en el log del servidor (sin datos personales).
9. Si algo de lo que hiciste cambia lo descrito en sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md (secciones 3 y 15),
   actualízalo; si no, no lo toques.

ARCHIVOS PERMITIDOS: models.py, api.py, services.py, migrations/ de las apps citadas, web/middleware.py,
config/settings*.py, comandos de gestión existentes, frontend/modelos/comun.js y las vistas o controladores de las
pantallas desactivadas (solo para mostrar el estado). Archivo nuevo permitido: web/migrations/0002_reglas_v2.py.
Si necesitas otro, pregunta.

SEGURIDAD (cita en tu informe cómo se cumple): ASVS V8 (autorización en servidor; actor), V2 (validación),
V16 (errores sin detalles internos; auditoría sin secretos), V14 (IP recortada; sin user-agent completo);
SSDF PW.4 (reutilizar), PW.5 (codificación segura), PW.8 (pruebas).

COMPROBACIONES: python manage.py check; makemigrations --check sin cambios; migrate en base vacía; pruebas_v2.py
y prueba_depuracion.py en verde contra esa base; comparación del punto 4c; pruebas de Django existentes de los
flujos conservados (las de pantallas desactivadas se quitan, no se maquillan).

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales (después de 2.2):** registro con y sin casillas · verificación por código · inicio de sesión con segundo paso · recuperar contraseña · Mi cuenta (Perfil, Seguridad, Privacidad y Mis datos) · cookies (aceptar, rechazar, configurar) · textos legales visibles con su versión · «Consíguelo» llega a Solicitudes del producto · guías visibles en Mantenimiento · te nombras super admin y ves el panel · las pantallas desactivadas dicen «Esta sección se está actualizando».

---

### FASE 2 · Sistema visual unificado

````text
FASE 2 de docs/EJECUCION-v2.md · Rama: fase-2-sistema-visual

Lee: CLAUDE.md, docs/PLAN-INTERFACES-v2.md secciones 0, 1 y 3, y docs/INVENTARIO-INTERFAZ-ACTUAL.md sección 1.

OBJETIVO
Unificar el sistema visual SIN cambiar el aspecto general: mismo fondo crema del panel, menú lateral verde, vidrio
claro en tarjetas, portada y acceso en vidrio oscuro. Solo se corrigen C1–C9 y se crean los componentes 3.5 y 3.6.

TAREAS
1. Crea frontend/vistas/estilos/tokens.css con TODAS las variables que hoy viven en los :root y ámbitos
   (base.css, acceso.css, panel.css, apariencia.css, cookies.css), agrupadas por zona: pública, acceso y panel.
   Cárgalo primero en index.html. Las demás hojas consumen variables; mueve allí los valores sueltos repetidos
   (radios, sombras, blur, z-index, duraciones). No cambies valores visibles. Define también las variables que
   hoy se usan sin definir (--liquid-surface, --liquid-hover-*, --header-surface).
2. C1: deja tres variantes de botón de vidrio (Primaria, Secundaria, Peligro) más la compacta. Reasigna las clases
   existentes (.btn-liquid-brand → Primaria, .btn-liquid-light → Secundaria, data-danger → Peligro) sin renombrar
   los usos en las vistas. Elimina el estilo pastel duplicado de peligro.
3. C2: deshabilitado = misma variante al 45 % de opacidad, cursor not-allowed, sin perder el vidrio.
4. C3: campos, selectores y textarea del panel en vidrio claro (texto oscuro, borde suave, foco verde de 3 px).
   No toques los campos del acceso (vidrio oscuro). Quita las reglas contradictorias de [data-maint-revise].
5. C4: insignias en cápsula de vidrio con cuatro tonos (verde, ámbar, rojo y gris), siempre con texto.
6. C5: componente de aviso flotante en vistas/comun.js + modelos/comun.js (una sola función mostrarAviso(tipo,
   texto)). Reemplaza el aviso de cookies por este componente. No reemplaces aún los mensajes de cada pantalla
   (se hará pantalla por pantalla en las fases 3 a 6).
7. 3.6: diálogo de confirmación estándar reutilizable (una función confirmar({titulo, texto, accion, peligro})
   que devuelve una promesa). Úsalo ya en: cerrar sesión, «Desactivar» app, «Quitar» llave y «Generar códigos
   nuevos» (Mi cuenta › Seguridad).
8. C7: backdrop-filter solo en tarjetas de primer nivel, menú lateral, encabezados y diálogos; quítalo de
   elementos internos.
9. C9: la campana de la barra flotante aparece también para administradores (todavía sin contador: llega en
   la fase 4).
10. Mientras tocas una regla, elimina las reglas muertas que la pisaban (por ejemplo, la piel oscura del panel en
    apariencia.css). No hagas la limpieza completa de !important: es de la fase 7.

ARCHIVOS: frontend/index.html, frontend/vistas/estilos/*.css, frontend/vistas/comun.js, frontend/modelos/comun.js,
frontend/controladores/cuenta.js y administracion.js (solo para usar confirmar). Nuevo: frontend/vistas/estilos/tokens.css.

SEGURIDAD: ASVS V3 (sin estilos ni scripts en línea nuevos; la CSP actual no se relaja). El aviso flotante
inserta texto con textContent.

COMPROBACIONES: recorre en escritorio (1366×768) y móvil (375×812) la portada, el acceso, todas las pantallas del
panel de usuario y de administración que funcionan; anota en el informe cualquier diferencia visual que no sea
C1–C9. Cuenta las reglas !important antes y después.

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales:** la página se ve **igual que antes** salvo botones uniformes de vidrio, deshabilitados legibles, campos claros en el panel, insignias en cápsula y campana para el admin · cerrar sesión, desactivar la app y quitar una llave piden confirmación · en móvil todo sigue igual · las cookies muestran el nuevo aviso flotante.

---

### FASE 3 · Flujo principal del usuario

````text
FASE 3 de docs/EJECUCION-v2.md · Rama: fase-3-flujo-usuario

Lee: CLAUDE.md, docs/PLAN-INTERFACES-v2.md (secciones 2.1, 3.1, 3.2, 3.8, 4.0, 4.1, 4.2, 4.3, 4.4, 4.9 «Mis huertos»
y 7), sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md (5.2 a 5.5 y 6).

OBJETIVO
Que una persona pueda: aceptar textos legales nuevos, crear su huerto, vincular su equipo, ver «Mi huerto»
(versiones A, B y C), editar sus plantas y gestionar sus huertos desde Mi cuenta.

BACKEND (endpoints nuevos en huerto/api.py y datos/api.py, lógica en services.py; formato de respuesta de web/respuestas.py):
- POST /api/legales/aceptar {documentos:[id,...]} → inserta las decisiones de la cuenta; solo acepta ids que estén
  en chilito_aceptaciones_pendientes().
- GET /api/huertos → huertos activos del usuario (id como texto, nombre, estado del equipo para 3.2).
- POST /api/huertos {nombre?} · POST /api/huertos/<id>/renombrar · POST /api/huertos/<id>/archivar.
- GET /api/huertos/<id> → huerto, 3 plantas (con su última medicion_planta), métricas (última medicion), lámpara
  (última actuacion de la lámpara + último comando de lámpara), último ia_resumen y estado del equipo.
- GET /api/huertos/<id>/ia?pagina= → resúmenes de los últimos 30 días.
- POST /api/huertos/<id>/codigo → genera el código de 8 caracteres XXXX-XXXX (alfabeto Crockford, secrets),
  guarda HMAC-SHA256(CHILITO_VINCULACION_SECRETO, código normalizado) y lo devuelve UNA vez con su vencimiento.
  Si había uno pendiente, lo cancela antes.
- GET /api/huertos/<id>/vinculacion → estado del último código y si el huerto ya tiene equipo (para la espera).
- POST /api/dispositivos/vincular {identificador, credencial, codigo} → endpoint del ESP32 (sin sesión de usuario,
  con CSRF exento SOLO aquí): verifica la credencial contra credencial_hash con el hasher de Django, normaliza el
  código, calcula el HMAC y llama a chilito_vincular_dispositivo(); responde solo el resultado. Cuota estricta por
  identificador e IP. Documenta en el informe por qué este endpoint no usa sesión ni CSRF (cliente sin navegador).
- POST /api/huertos/<id>/desvincular → chilito_desvincular_dispositivo().
- GET /api/huertos/<id>/plantas/<n> y POST …/plantas/<n> {nombre?, fecha_siembra?, etapa?} (save con update_fields).
- POST /api/huertos/<id>/comandos {tipo, planta?, duracion?} → crea comandos de usuario (regar, lampara_apagar,
  lampara_automatico, autodiagnostico). GET /api/comandos/<id> → estado (para 3.3).
- POST /api/huertos/<id>/cuidados → registrar cuidado (usado por «Registrar recarga»).
Todos verifican en el servidor que el huerto es del usuario (aunque la base también lo exige).

FRONTEND (dominio huerto: modelos/huerto.js, vistas/huerto.js, controladores/huerto.js; enrutador; cuenta):
- 4.0 #aceptar-legales (el enrutador bloquea las rutas privadas si /api/cuenta trae pendingLegal).
- 4.1 Mi huerto en sus 3 versiones, 3.1 selector (solo con 2 o más huertos), 3.2 línea de estado, 3.3 tarjeta de orden.
- 4.2 #huerto/nuevo, 4.3 #huerto/vincular (asistente; espera cada 5 s, máximo 10 min, con X-Chilito-Sondeo),
  4.4 #huerto/plantas/<n>, 4.9 pestaña «Mis huertos».
- Elimina «Vincular mi huerto» con código de 26 caracteres y la ayuda de mailto (vistas/equipos.js en su parte de
  usuario). Elimina las frases y textos fijos que el plan quita.
- Usa mostrarAviso (C5) y confirmar (3.6) de la fase 2. Ningún dato inventado: sin lectura = «Sin lectura».

ARCHIVOS: los de huerto y cuentas citados, enrutador.js, vistas/comun.js, modelos/comun.js, equipos.js (para quitar
la parte de usuario), urls. Sin archivos nuevos, salvo que justifiques uno y yo lo apruebe.

SEGURIDAD: ASVS V8 (propiedad del huerto en cada endpoint; ids ajenos → 404 sin revelar existencia), V2
(validación de nombre, fecha, etapa, duración y planta), V6/V11 (código con secrets; solo HMAC guardado; credencial
del equipo con hasher de Django), V4 (endpoint del ESP32 con cuota y respuesta mínima), V16 (auditoría:
crear_huerto, archivar_huerto, generar_codigo, desvincular_dispositivo, crear_comando).

COMPROBACIONES: pruebas de Django para cada endpoint, incluyendo los casos de otra cuenta (debe recibir 404), código
vencido, código reutilizado, equipo ocupado, cuarto huerto y segundo huerto sin equipo. Simula el ESP32 con una
petición de prueba a /api/dispositivos/vincular.

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales:** con la cuenta de usuario: Mi huerto sin huertos → «Crear mi huerto» · crear huerto con y sin nombre · generar código (8 caracteres, contador) · simular el ESP32 (te dirán cómo en el informe) → pasa solo al paso «Listo» · Mi huerto completo · editar planta (nombre, siembra y etapa) y ver su línea de vida · crear 2.º huerto y ver el selector · intentar un 2.º huerto sin equipo (debe impedirlo) · Mis huertos: renombrar, desvincular (pide confirmación) y archivar · publicar desde pgAdmin un término 1.1 → al entrar te pide aceptarlo.

---

### FASE 4 · Operación del usuario

````text
FASE 4 de docs/EJECUCION-v2.md · Rama: fase-4-operacion-usuario

Lee: CLAUDE.md, docs/PLAN-INTERFACES-v2.md (3.3, 3.4, 3.7, 4.5, 4.6, 4.7, 4.8, 4.9 Privacidad), sql/FUNCIONAMIENTO-
BASE-DE-DATOS-v2.md (5.6 a 5.11 y 5.13).

OBJETIVO
Panel técnico, Mantenimiento, Soporte (sin token, con autodiagnóstico), Avisos y, en Mi cuenta › Privacidad,
«Documentos que aceptaste» y «Eliminar mi cuenta».

BACKEND:
- GET /api/huertos/<id>/telemetria?rango=1h|24h|7d|30d → 1h y 24h desde medicion/medicion_planta (incluye adc_crudo);
  7d y 30d desde resumen_hora_*. Lecturas por planta. Paginado: GET /api/huertos/<id>/bitacora?tipo=ordenes|
  actuaciones|eventos&pagina=.
- Cuidados: GET /api/huertos/<id>/cuidados?planta&tipo&desde&hasta&pagina= (aplicando la última revisión vigente)
  y POST (ya existe desde la fase 3; amplíalo con planta, realizado_en y chiles).
- Soporte: GET /api/huertos/<id>/soporte (caso activo + historial + órdenes de soporte del caso),
  POST /api/huertos/<id>/soporte {incidente, nota?, autodiagnostico?, consentimiento:true},
  POST /api/soporte/<caso>/revocar, POST /api/soporte/<caso>/cancelar. Elimina por completo el token de soporte
  (emisión, copia, verificador y textos).
- Autodiagnóstico: GET /api/autodiagnosticos/<id> (con sus revisiones).
- Avisos: GET /api/avisos?filtro=&pagina=, GET /api/avisos/<id>, POST /api/avisos/<id>/leido,
  POST /api/avisos/<id>/resuelto, POST /api/avisos/leer-todos, GET /api/avisos/contador.
- Cuenta: GET /api/cuenta/aceptaciones; POST /api/cuenta/eliminar {password} (reautentica con la contraseña y fija
  anonimizacion_solicitada_en); POST /api/cuenta/eliminar/cancelar.
- Quita los 503 «en-actualizacion» de estas pantallas.
- Simulador de equipo para probar sin ESP32: backend/tools/simular_equipo.py (archivo nuevo permitido). Se conecta
  con el rol chilito_pkg_iot (variables de entorno propias, nunca las de la app) y, para un identificador dado,
  inserta mediciones con sus 3 plantas, responde comandos pendientes (enviado → confirmado o fallido), completa
  autodiagnósticos y puede marcar el equipo conectado o desconectado. Debe marcar sus datos como simulados en
  dispositivo_evento.detalle='simulador' y negarse a correr si DEBUG es False.

FRONTEND: 4.5, 4.6, 4.7, 4.8, contador de la campana (3.4) en todas las pantallas privadas, aviso fijo de
eliminación pendiente (4.9). Usa mostrarAviso y confirmar. Elimina el código y los textos del token de soporte, del
selector de periodo que no hacía nada y de los estados que el backend nunca enviaba.

ARCHIVOS: dominio huerto, comun y cuenta (frontend y backend), urls. Nuevo permitido: backend/tools/simular_equipo.py.

SEGURIDAD: ASVS V8 (caso y avisos solo del dueño; revocar y cancelar solo el solicitante), V6 (eliminar la cuenta pide
contraseña), V2 (validación de filtros y paginación con límites), V16 (auditoría: abrir_caso, revocar_soporte,
cancelar_caso, solicitar_eliminacion, cancelar_eliminacion), WSTG (pruebas con dos cuentas). El simulador NUNCA
se ejecuta en producción (SSDF PO/PS: separar demostración de operación real).

COMPROBACIONES: pruebas de Django por endpoint con dos cuentas (la ajena recibe 404); prueba de que el contador baja
al marcar leído; prueba del simulador contra una base de pruebas.

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales** (con el simulador encendido): panel técnico con gráficas de 1 h a 30 días y ADC · regar una planta → la orden pasa a «Confirmada» · registrar cuidados por planta y del depósito · revisar mi equipo → resultados por componente · solicitar revisión con autorización · revocar y cancelar (piden confirmación) · avisos con contador en la campana · Documentos que aceptaste · eliminar cuenta (pide contraseña) y cancelar.

---

### FASE 5 · Administración nueva

````text
FASE 5 de docs/EJECUCION-v2.md · Rama: fase-5-admin-nueva

Lee: CLAUDE.md, docs/PLAN-INTERFACES-v2.md (2.2, 5.5, 5.6, 5.8, 5.9, 5.10, 7), sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md
(5.12, 7 y 10).

OBJETIVO
Pantallas nuevas de administración: Inventario de equipos, Administradores (super admin), Textos legales,
Bitácora de consentimientos y Ventas. Elimina «Vinculación de huertos» y la maqueta «Equipos y ventas».

BACKEND (todo bajo /api/admin/…, exigiendo la capacidad y el segundo factor como las pantallas actuales):
- Equipos (gestionar_dispositivos): listar con filtros y paginación (v_estado_equipos), alta (genera la credencial
  MQTT con secrets, guarda solo su hash con el hasher de Django, la devuelve una vez), detalle con historial de
  eventos, desvincular (chilito_desvincular_dispositivo), rotar credencial (misma regla) y retirar.
- Administradores (gestionar_administradores): listar (v_administradores), historial (v_capacidad_historial con
  filtros), actividad (auditoria filtrada por actor), y cambiar capacidades de una cuenta: recibe la lista final de
  capacidades y un motivo; fija chilito.motivo y aplica altas y bajas en una transacción. Rechaza
  gestionar_administradores y la propia cuenta antes de llegar a la base.
- Legales (gestionar_legales): por tipo: vigente, borradores e historial; crear, editar y borrar borrador; publicar.
- Consentimientos (ver_consentimientos): v_bitacora_consentimientos con filtros y paginación, resumen (aceptaciones
  de la versión vigente / cuentas activas; % de navegadores con estadísticas) y exportación CSV del filtro (con
  auditoria exportar_consentimientos; CSV con escape contra inyección de fórmulas).
- Ventas (gestionar_ventas): listar con filtros, registrar, registrar pago, marcar entregada, editar nota, cancelar,
  y resumen por periodo y municipio. Municipios: lista cerrada en el backend (constante en el módulo de ventas).
- Elimina el servicio y los endpoints de vinculación del admin.

FRONTEND: dominio administracion (+ equipos.js para el inventario: reutiliza ese archivo en lugar de crear otro).
Menú con los grupos de 2.2 y el mapa capacidad→destino completo. Pantallas 5.5, 5.6, 5.8, 5.9 y 5.10 con
paginación visible, mostrarAviso, confirmar y el componente 3.8 para la credencial. Editor de textos legales
con vista previa (el HTML de la vista previa lo devuelve el servidor ya saneado; el navegador no lo genera).
Elimina por completo CommerceViews/CommerceController/CommerceModel y comercial.css, y las vistas
de vinculación del admin.

ARCHIVOS: dominio administracion y equipos (frontend y backend), privacidad (legales y bitácora), urls y estilos de
estas pantallas dentro de las hojas existentes. Sin archivos nuevos salvo aprobación.

SEGURIDAD: ASVS V8 (capacidad por endpoint, nunca solo por menú), V11/V13 (credencial generada con secrets, mostrada
una vez, solo hash), V1/V3 (contenido legal saneado en servidor; CSV sin inyección de fórmulas), V14 (la bitácora
muestra IP recortada; la exportación solo para ver_consentimientos), V16 (auditoría de cada acción).

COMPROBACIONES: pruebas por endpoint con una cuenta con la capacidad y otra sin ella (403); prueba de que el panel no
deja dar gestionar_administradores ni cambiar las propias capacidades; prueba de publicación (versión menor rechazada;
notificación a cuentas); prueba de CSV.

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales** (como super admin): dar de alta `ESP32-PRUEBA2` y ver la credencial una sola vez · darle a tu cuenta de prueba solo «Ventas» con motivo → aparece en el historial · entrar con esa cuenta: solo ve Ventas · intentar cambiar tus propias capacidades (no debe dejar) · crear borrador de términos 1.1, vista previa y publicar → tu usuario de prueba debe aceptarlo al entrar · bitácora con tu aceptación (correo, versión, IP recortada y navegador) y exportar CSV · registrar una venta con pago parcial → completar pago → marcar entregada.

---

### FASE 6 · Administración adaptada

````text
FASE 6 de docs/EJECUCION-v2.md · Rama: fase-6-admin-adaptada

Lee: CLAUDE.md, docs/PLAN-INTERFACES-v2.md (5.1, 5.2, 5.3, 5.4, 5.7), sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md (5.10, 5.11).

OBJETIVO
Telemetría de flota con datos reales, Consola remota sin token (Atender, Conectar, acciones y resolución),
Mantenimientos de todos los huertos y confirmaciones en Solicitudes y Guías.

BACKEND:
- Flota (ver_flota): totales (vinculados, en línea, desconectados, problemas en 24 h), tendencias de 7 días desde
  resumen_hora_*, tabla paginada desde v_estado_equipos y problemas recientes (autodiagnósticos con fallas,
  comandos fallidos, equipos desconectados más de 24 h). Elimina las métricas sin fuente.
- Consola (atender_soporte): bandeja por estado con paginación; detalle (persona, huerto, equipo, nota, autorización,
  autodiagnóstico); atender; conectar (crea soporte_sesion); estado de la sesión (lecturas actuales, eventos 24 h,
  órdenes de la sesión); acciones (comandos de origen soporte con sesion_id); cerrar sesión técnica; resolver. Al
  cerrar la sesión de la cuenta, cierra su sesión técnica (motivo cierre_sesion). Elimina por completo el token.
- Mantenimientos (gestionar_mantenimientos): todos los huertos, búsqueda por correo o huerto, filtros, paginación;
  corregir (tipo, planta y chiles con motivo y número de revisión) y anular.
- Quita los 503 «en-actualizacion» que queden.

FRONTEND: 5.1, 5.2 (en vivo: comprobación cada 10 s de revocación; al salir de la pantalla cierra la sesión técnica),
5.3 con paginación, confirmaciones en 5.4 (Archivar) y 5.7 (Publicar y Retirar). Elimina los textos y campos del token,
los «pines GPIO» y los registros simulados del diagnóstico.

ARCHIVOS: dominio administracion y huerto (mantenimientos), datos (servicios), urls. Sin archivos nuevos.

SEGURIDAD: ASVS V8 (solo quien atiende conecta y opera; cada acción vuelve a comprobar la autorización vigente),
V7 (cierre de sesión técnica al cerrar sesión), V16 (auditoría: atender_caso, conectar_sesion, crear_comando,
cerrar_sesion_tecnica, resolver_caso, corregir_cuidado, anular_cuidado).

COMPROBACIONES: pruebas con dos admins (el segundo no puede conectar al caso del primero), revocación durante una
sesión (la siguiente acción falla), vencimiento de 24 h, paginación de mantenimientos.

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales** (con el simulador y dos ventanas: admin y usuario): el usuario solicita revisión → al admin le llega aviso y aparece en «Nuevos» · Atender → Conectar → lecturas actuales · «Reiniciar equipo» y «Probar bomba» (confirmaciones) → órdenes confirmadas · el usuario ve lo que hizo soporte · el usuario revoca → la sesión del admin se cierra sola · resolver otro caso · flota con totales y equipos reales · corregir y anular un cuidado (el usuario lo ve como «Corregido» o «Anulado»).

---

### FASE 7 · Limpieza, verificación y documentación

````text
FASE 7 de docs/EJECUCION-v2.md · Rama: fase-7-cierre

Lee: CLAUDE.md y el informe de cada fase anterior (si los guardaste en docs/informes/).

OBJETIVO
Dejar el código limpio y verificado, sin cambiar comportamiento.

TAREAS
1. CSS: elimina reglas muertas y reduce !important al mínimo necesario (informa el antes y el después por archivo).
   Ningún cambio visual: compáralo pantalla por pantalla en escritorio y móvil.
2. Busca y elimina: funciones, clases CSS, textos, rutas y endpoints sin uso; archivos frontend/legales/*.html;
   referencias a tablas o modelos v1; restos del token de soporte, de «Vinculación de huertos» y de la maqueta comercial.
3. Comprueba que ningún archivo del frontend usa innerHTML con datos del servidor sin sanear.
4. Revisa dependencias (pip): lista versiones en el informe y ejecuta pip-audit si está disponible (no lo instales
   sin preguntar).
5. Ejecuta todas las pruebas: Django completas, sql/pruebas/pruebas_v2.py y prueba_depuracion.py contra una base
   creada con migrate, y makemigrations --check.
6. Documentación: actualiza docs/INVENTARIO-INTERFAZ-ACTUAL.md para que describa el estado nuevo (rutas, pantallas y
   endpoints) y añade a docs/ una matriz breve requisito ASVS/SSDF → dónde se implementa → qué prueba lo verifica
   (solo de lo hecho en las fases 1–6; nada declarado sin prueba).

ARCHIVOS: cualquiera, solo para eliminar o simplificar. Nuevo permitido: docs/MATRIZ-SEGURIDAD-v2.md.

SEGURIDAD: SSDF PW.7 (revisión de código), PW.8 (pruebas), PS.3 (registro de versión) y RV.1 (registro de pendientes).

Empieza presentando tu plan y espera mi aprobación.
````

**Tus pruebas manuales:** repite todas las pruebas de las fases 1 a 6 · la página se ve igual que al final de la fase 6 · en móvil todo funciona.

---

## 5. Recordatorios para cada sesión

- Si Claude Code propone **crear archivos** que la fase no nombra, **agregar librerías**, o «mejorar» algo fuera de la fase: dile que no y que se ciña al prompt.
- Si dice que la base «rechaza» algo y propone cambiar la base: **no**. Pídele que te muestre el error. Casi siempre falta el actor o el código no cumple una regla.
- Si una sesión se alarga mucho o se pierde, ciérrala y empieza otra con el mismo prompt, indicando qué quedó hecho.

---

## 6. Formato del informe de fase (Claude Code lo entrega al terminar)

```
INFORME FASE N
1. Resumen (3–5 líneas)
2. Archivos: creados / modificados / eliminados (con 1 línea de motivo cada uno)
3. Líneas: añadidas / eliminadas (git diff --stat)
4. Endpoints nuevos, cambiados y eliminados
5. Seguridad: requisito (ASVS/SSDF) → cómo se cumple → prueba que lo verifica
6. Comprobaciones ejecutadas y resultado (comando y salida resumida)
7. Pendientes o dudas (nada se oculta)
8. Cómo probarlo a mano (pasos)
```
Guarda cada informe en `docs/informes/FASE-N.md` y mándamelo para revisarlo antes de la fase siguiente.

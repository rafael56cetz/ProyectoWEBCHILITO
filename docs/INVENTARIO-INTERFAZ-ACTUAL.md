# Inventario de la interfaz actual de El Chilito

> **Alcance y método.** Documento de solo lectura. Todo sale de leer el código de `frontend/` (14 archivos JS, 7 CSS, `index.html`) y de las partes del backend que entregan datos a la interfaz (`backend/config/urls.py`, `backend/web/`, `backend/cuentas/api.py`, `backend/privacidad/`, `backend/datos/`, `backend/huerto/`).
> **No se levantó el servidor ni se abrió la página**: el backend usa PostgreSQL y no se debe tocar una base real; por tanto **nada visual fue comprobado en un navegador**. Las descripciones de aspecto se deducen de las reglas CSS y pueden diferir de lo pintado cuando varias reglas con `!important` compiten (se señala donde ocurre).
> Convención de citas: `ruta/archivo:línea`. Las rutas de frontend son relativas a la raíz del proyecto (`frontend/...`). «NO DETERMINABLE» = no se puede saber leyendo el código.
> Sin secretos: solo se nombran variables (`CHILITO_CONTACTO_SOPORTE`), nunca valores.
> Fecha del inventario: 2026-11-14.

---

## 0. Resumen

### 0.1 Organización del frontend

| Elemento | Detalle | Fuente |
|---|---|---|
| Tipo de aplicación | SPA sin framework ni empaquetador: un único `index.html` que carga scripts clásicos (no módulos) con `?v=mvc.3`. Todo se pinta con `innerHTML`/DOM dentro de `<div id="app">`. | `frontend/index.html:19,22-40` |
| Carpetas | `modelos/` (datos, validación, llamadas HTTP), `vistas/` (plantillas HTML en JS + `estilos/`, `fuentes/`, `imagenes/`), `controladores/` (eventos y coordinación), `legales/` (HTML editable de los 3 documentos legales), `pruebas/` (pruebas Node), `favicon.svg`. | listado de `frontend/` |
| Patrón | MVC por dominio. Cada dominio tiene un archivo en cada capa: `comun`, `publico`, `cuenta`, `huerto`, `equipos`, `administracion` (en `modelos/` no existe `vistas/navegacion.js`; en `vistas/` sí). Los objetos son IIFE globales (`const X = (() => {...})()`). | cabeceras de cada archivo |
| Orden de carga | modelos (`cuenta`, `comun`, `publico`, `huerto`, `equipos`, `administracion`) → vistas (`comun`, `publico`, `cuenta`, `huerto`, `equipos`, `administracion`) → controladores (mismo orden) → `vistas/navegacion.js` → `controladores/enrutador.js` (arranca la página). | `frontend/index.html:22-40` |
| Enrutador | Hash (`location.hash`). `SiteController.start` escucha `hashchange`, resuelve la ruta con `routeFromHash()` y llama `render()`. No hay `history.pushState`; sí `history.replaceState` para normalizar el hash. | `frontend/controladores/enrutador.js:5-195` |
| Comprobación de sesión | Para rutas privadas, `render()` pregunta al servidor (`AuthService.restore`: `GET /_allauth/browser/v1/auth/session` + `GET /api/cuenta`) antes de pintar. Mientras tanto muestra «Comprobando sesión». | `enrutador.js:66-103`, `modelos/cuenta.js:157-175` |
| Reutilización del marco | Si cambias entre pantallas privadas del mismo rol, el marco (menú lateral + barra) no se reconstruye: `controller.update(route)`. | `enrutador.js:120-122,160`, `controladores/administracion.js:344-351` |
| Servido por Django | `GET /` y `/index.html` → `index.html` (`Cache-Control: no-cache`); `/vistas/…`, `/modelos/…`, `/controladores/…`, `/favicon.svg` → archivos con extensión `.js .css .svg .webp .jpg .png .ttf .woff2`. `legales/` **no** se sirve: lo lee el backend. | `backend/config/urls.py:9,49`, `backend/web/static_views.py:1-19` |
| Cabeceras de seguridad | CSP `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; …`, `X-Frame-Options: DENY`, `Permissions-Policy` sin cámara/micrófono/geolocalización. Las respuestas `/api/` y `/_allauth/` llevan `Cache-Control: no-store`. | `backend/web/middleware.py:1-11` |
| Datos de pantalla | `document.body.dataset.screen / .private / .role` (`inicio`, `huerto`, …; `true|false`; `admin|user`). El CSS depende de estos atributos. | `frontend/vistas/publico.js:247-251` |
| Título de pestaña | `SiteViews.title(x)` → `x + ' · El Chilito'`; título inicial: «El Chilito · Tu huerto de habanero, dentro de casa». | `publico.js:246`, `index.html:6` |
| Sin JavaScript | `<noscript>`: «El Chilito» / «Activa JavaScript para navegar por El Chilito.» | `index.html:21` |
| Almacenamiento local | **Ninguno**: no hay `localStorage` ni `sessionStorage` (solo comentarios que lo prohíben). Cookies del servidor: `sessionid`, `csrftoken`, `chilito_preferencia`, `chilito_estadistica`. | búsqueda en `frontend/` |

### 0.2 Tabla de rutas (`#…`)

Leyenda de acceso: **V** = visitante (sin sesión), **U** = persona usuaria con sesión, **A** = administración (sesión con al menos una capacidad). Una cuenta es «admin» si tiene alguna capacidad de `datos` (`backend/datos/services.py:55-58`).

| Ruta | Pantalla | Quién puede verla | Archivos (vista · controlador · modelo) |
|---|---|---|---|
| `#` (vacío) o ruta desconocida | Portada (Inicio) | V, U, A (se muestra igual; «Iniciar sesión» cambia a «Ir a mi panel» si hay sesión) | `vistas/publico.js:102-239` · `enrutador.js:41,162-172` · — |
| `#inicio` | Portada · Inicio (hero) | V/U/A | ídem |
| `#el-proyecto` | Portada · El proyecto | V/U/A | `publico.js:109-140` |
| `#prototipo` | Portada · Prototipo | V/U/A | `publico.js:142-187` |
| `#consiguelo` | Portada · Consíguelo (+ ventana «Cuéntanos qué quieres saber») | V/U/A | `publico.js:189-199,271-330` · `controladores/publico.js:105-128` · `modelos/publico.js` |
| `#como-funciona` | Portada · Cómo funciona | V/U/A | `publico.js:201-237` |
| `#terminos` | Términos y condiciones | V/U/A | `publico.js:333-405` · `enrutador.js:147-153` · `modelos/comun.js:7-11` |
| `#privacidad` | Aviso de privacidad | V/U/A | ídem |
| `#cookies` | Política de cookies | V/U/A | ídem |
| `#derechos-arco` | (retirada) redirige a `#privacidad` | V/U/A | `enrutador.js:19` |
| `#acceso` | Inicia sesión | V (si ya hay sesión redirige al panel) | `vistas/cuenta.js:5-210` · `controladores/cuenta.js:251-556` · `modelos/cuenta.js` |
| `#registro` | Crea tu cuenta | V (si hay sesión redirige al panel); solo funciona si el servidor permite el registro | ídem |
| `#verificar` | Verifica tu correo | V con verificación pendiente en el servidor; si no, → `#acceso` | ídem |
| `#recuperar` | Recupera el acceso | V | ídem |
| `#restablecer` | Elige una contraseña nueva (enlace con `key`/`token` en el hash) | V con enlace válido | ídem |
| `#segundo-paso` | Confirma tu acceso (código por correo / app / llave) | V con segundo paso pendiente; si no, → `#acceso` | `cuenta.js:214-282` · `cuenta.js(ctl):18-50` |
| `#sin-acceso` | Sin acceso a tu segundo paso | V | `publico.js:252-255`, `cuenta.js:371-379` |
| `#huerto` | Mi huerto | **U** (admin → redirige a su panel) | `vistas/huerto.js:32-201` · `controladores/huerto.js:5-125` · `modelos/huerto.js:73-166` |
| `#telemetria` | Panel técnico | U | ídem |
| `#mantenimiento` | Mantenimiento (+ guías de cuidado) | U | ídem + `huerto.js(vista):205-402` |
| `#mantenimiento/sustrato`, `/germinacion`, `/guias`, `/historial` | Mantenimiento con foco en una guía o en el historial | U | `controladores/huerto.js:129-185,34-55` |
| `#soporte` | Soporte técnico | U | ídem |
| `#avisos` | Avisos (lista) | U (no aparece para admin) | `vistas/comun.js:62-79` · `controladores/administracion.js:209-434` |
| `#avisos/<id>` | Detalle del aviso | U | ídem |
| `#huerto/avisos` | (alias) redirige a `#avisos` | U | `enrutador.js:26-29` |
| `#asistente` | (retirada) redirige a `#huerto` | U | `enrutador.js:25` |
| `#cuenta` | Mi cuenta · Perfil | U y A | `vistas/comun.js:82-87` · `controladores/cuenta.js:138-177` |
| `#cuenta/seguridad` | Mi cuenta · Seguridad | U y A (los A con `mfaRequired` son enviados aquí) | `vistas/cuenta.js:214-322` · `controladores/cuenta.js:52-135` |
| `#cuenta/seguridad/<algo>` | «Página no disponible» | U y A | `enrutador.js:20`, `vistas/comun.js:112` |
| `#cuenta/privacidad` | Mi cuenta · Privacidad | U y A | `vistas/cuenta.js:325-447` · `controladores/cuenta.js:201-248` |
| `#cuenta/contrasena` | Cambiar contraseña | U y A | `vistas/cuenta.js:93`, `controladores/administracion.js:284-287` |
| `#admin` o `#admin/<desconocido>` | → `#admin/flota` (o el primer destino permitido) | A | `enrutador.js:17,99-102` |
| `#admin/flota` | Telemetría de flota | A con `ver_flota` | `vistas/administracion.js:5-103` · `controladores/administracion.js:5-70` · `modelos/administracion.js:6-85` |
| `#admin/soporte` | Consola remota | A con `atender_soporte` | ídem |
| `#admin/mantenimientos` | Mantenimientos | A con `gestionar_mantenimientos` | `vistas/huerto.js:406-558` · `controladores/huerto.js:303-353` · `modelos/huerto.js:240-266` |
| `#admin/solicitudes` | Solicitudes del producto | A con `atender_consultas` | `vistas/administracion.js:107-177` · `controladores/administracion.js:74-117` · `modelos/administracion.js:89-135` |
| `#admin/comercial` | Equipos y ventas | A con `vincular_huertos` (visibilidad provisional) | `vistas/administracion.js:181-317` · `controladores/administracion.js:121-206` · `modelos/administracion.js:140-220` |
| `#admin/vinculacion` | Vinculación de huertos | A con `vincular_huertos` | `vistas/equipos.js:6-250` · `controladores/equipos.js:36-126` · `modelos/equipos.js:7-58` |
| `#admin/guias` | Guías de cuidado | A con `gestionar_guias` | `vistas/huerto.js:205-402` · `controladores/huerto.js:187-300` · `modelos/huerto.js:171-236` |

Reglas del enrutador (todas en `enrutador.js:60-103`):
- Ruta privada sin sesión → `#acceso` con aviso «Inicia sesión para continuar.»; con servidor sin respuesta → «No podemos comprobar tu sesión. Inténtalo de nuevo.»; con verificación de correo pendiente → `#verificar`; con segundo paso pendiente → `#segundo-paso`.
- Admin en ruta de usuario (salvo `#cuenta…`) → su primer destino admin; usuario en `#admin/…` → `#huerto`.
- Admin con `mfaRequired===true` en `#admin/…` → `#cuenta/seguridad`.
- Admin pidiendo un destino sin capacidad → primer destino permitido (`AppModel.adminHome`; si no hay ninguno devuelve `'huerto'`, `modelos/comun.js:72`).

### 0.3 Cómo se decide el menú de cada tipo de cuenta

| Quién | Menú | Fuente |
|---|---|---|
| **Visitante / portada y legales** | Encabezado público: Inicio · El proyecto · Ver prototipo · Consíguelo · Cómo funciona (+ «Iniciar sesión» a la derecha; en móvil, dentro del menú desplegable). | `vistas/publico.js:101` |
| **Persona usuaria** | Menú lateral con 5 destinos: Mi huerto · Panel técnico · Mantenimiento · Soporte técnico · Mi cuenta (Avisos se excluye del lateral y va como **campana** en la barra flotante). Pie: «Cerrar sesión». | `controladores/administracion.js:211-216`, `vistas/comun.js:34-57`, `modelos/comun.js:49-56` |
| **Administración** | Menú lateral con rótulo «Administración». Primero los destinos permitidos que no son de «Gestión» (Telemetría de flota, Consola remota, Mantenimientos); luego grupo «Gestión» (enlace «Abrir correo de soporte» si hay correo configurado, Solicitudes del producto, Equipos y ventas, Vinculación de huertos, Guías de cuidado); al final «Mi cuenta». No hay Avisos. | `vistas/comun.js:41-53`, `modelos/comun.js:57-68` |
| **Capacidad → destino** | `ver_flota`→`admin/flota`; `atender_soporte`→`admin/soporte`; `gestionar_mantenimientos`→`admin/mantenimientos`; `atender_consultas`→`admin/solicitudes`; `vincular_huertos`→`admin/comercial` **y** `admin/vinculacion`; `gestionar_guias`→`admin/guias`. Un destino sin capacidad no se pinta (y el servidor lo niega aparte). | `modelos/comun.js:67-68` |
| **Rol** | `role` = `'admin'` si la cuenta tiene alguna capacidad, si no `'user'`; lo calcula el servidor. | `backend/datos/services.py:55-58` |

---

## 1. Sistema de diseño (Liquid Glass)

> **Hallazgo central:** no existe un único archivo de tokens. Las variables viven en 4 bloques `:root` y 5 bloques con ámbito (`.auth-flow`, `.cookies`, `body[data-private=true]…`). Además el sitio tiene **tres pieles** distintas (portada oscura de vidrio, acceso claro, panel crema con menú verde) más el aviso de cookies oscuro. Las pieles se logran con muchas reglas `!important` (conteo: `base.css` 422, `apariencia.css` 327, `panel.css` 149, `navegacion.css` 108, `acceso.css` 25, `comercial.css` 13, `cookies.css` 2).

### 1.1 Tokens (variables CSS), literales y archivo

**`frontend/vistas/estilos/base.css:3-17` — `:root` principal**

| Variable | Valor |
|---|---|
| `--ivory` | `#f2efe9` |
| `--warm-white` | `#fffdf6` |
| `--ink` | `#1f1915` |
| `--vegetable` | `#355a44` |
| `--coral` | `#fa725a` |
| `--stone` | `#ccc5b9` |
| `--ink-muted` | `#655d54` |
| `--bg` | `var(--ivory)` |
| `--surface` | `var(--warm-white)` |
| `--raised` | `#e9e5dc` |
| `--text` | `var(--ink)` |
| `--muted` | `var(--ink-muted)` |
| `--sage` | `var(--vegetable)` |
| `--line` | `var(--stone)` |
| `--accent` | `var(--coral)` |
| `--error` | `#9c3027` |
| `--warning` | `#77500e` |
| `--focus` | `var(--vegetable)` |
| `--body` | `Geist,Arial,sans-serif` |
| `--display` | `var(--body)` |
| `--text-small` | `.875rem` |
| `--text-body` | `1rem` |
| `--weight-body` | `400` |
| `--weight-label` | `500` |
| `--weight-emphasis` | `600` |
| `--space-1` … `--space-6` | `.25rem`, `.5rem`, `.75rem`, `1rem`, `1.5rem`, `2rem` |
| `--radius-control` | `.5rem` |
| `--radius-panel` | `1rem` |
| `--radius-button` | `999px` |
| `--border-control` | `#80776a` |
| `--control-height` | `3rem` |
| `--control-compact` | `2.75rem` |
| `--motion-control` | `160ms` |
| (propiedades sueltas del mismo bloque) | `color-scheme:light; font-family:var(--body); background:var(--bg); color:var(--text); font-synthesis:none` |

**`base.css:844-847` — segundo `:root`**: `--header-height:72px` (JS lo reescribe en píxeles reales, `vistas/navegacion.js:43,54`), `--disabled-fill:#e6e3dd`, `--disabled-ink:#655d54`, `--disabled-edge:#a39a8d`.

**`apariencia.css:3-9` — `:root` de vidrio líquido** (sombras compuestas):
- `--lg-dark`: `0 2px 6px rgba(0,0,0,.14),inset 3px 3px .5px -3.5px rgba(255,255,255,.09),inset -3px -3px .5px -3.5px rgba(255,255,255,.85),inset 1px 1px 1px -.5px rgba(255,255,255,.6),inset -1px -1px 1px -.5px rgba(255,255,255,.6),inset 0 0 6px 6px rgba(255,255,255,.12),inset 0 0 2px 2px rgba(255,255,255,.06),0 0 12px rgba(0,0,0,.15)` (botones sobre superficies oscuras).
- `--lg-solid`: `inset 0 1px 0 rgba(255,255,255,.5),inset 0 -1px 0 rgba(0,0,0,.28),inset 1px 0 0 rgba(255,255,255,.14),inset -1px 0 0 rgba(255,255,255,.14),0 8px 18px -8px rgba(8,24,15,.55)` (rellenos sólidos).
- `--lg-light`: `inset 0 0 0 1px rgba(28,49,34,.17),inset 0 1px 0 #fff,0 1px 2px rgba(20,42,27,.08),0 6px 14px -8px rgba(20,42,27,.22)` (botones claros).
- `--display-weight`: `800`.

**`panel.css:2`**: `--private-nav-height:0px`, `--review-height:0px`, `scrollbar-color:#526d59 #edf3ee`, `scrollbar-width:auto`. **`panel.css:505`** (dentro de `body[data-private=true]`): `--dashboard-forest:#173c2f`.

**`acceso.css:3-4` — ámbito `.auth-flow`** (pantallas de acceso): `--text:#142419`, `--muted:#4a5d4e`, `--sage:#264d32`, `--focus:#264d32`, `--disabled-fill:#e6eee7`, `--disabled-ink:#526658`, `--disabled-edge:#91aa98`. **`acceso.css:62-64`**: `--liquid-filter:blur(14px) saturate(175%)` (en `.auth-flow .button`), `--liquid-shadow:inset 0 1.5px 0 rgba(255,255,255,.85),inset 0 -1px 0 rgba(16,35,22,.45),0 10px 24px -6px rgba(31,64,41,.38)` (en `.btn-liquid-brand`), `--liquid-fill:#f6f9f6`, `--liquid-ink:#264d32` (en `.btn-liquid-light`; igual en `panel.css:95`).

**`panel.css` (ámbito `body[data-private=true]`, línea ~7)**: `--text:#142419`, `--muted:#4a5d4e`, `--focus:#264d32` (sobrescritos después por apariencia.css).

**`apariencia.css:116-122` — piel oscura del panel (ya sustituida por la clara)**, en `body[data-private=true]:is([data-role=user],[data-role=admin])`: `--text:#fff`, `--muted:rgba(255,255,255,.8)`, `--focus:#fff`, `--sage:#fff`, `--garden-ink:#fff`, `--garden-muted:rgba(255,255,255,.8)`, `--garden-line:rgba(255,255,255,.16)`, `--garden-green:#fff`, `--garden-surface:rgba(255,255,255,.08)`, `--garden-tint:rgba(255,255,255,.1)`, `--glass-card:linear-gradient(180deg,rgba(255,255,255,.13) 0%,rgba(255,255,255,.06) 100%)`, `--glass-edge:inset 0 1px 0 rgba(255,255,255,.22),0 14px 30px -20px rgba(4,16,13,.7)`; fondo `#17393a`.

**`apariencia.css:297-301` — piel clara del panel (la que gana)**, mismo selector: `--claro-fondo:#fdf3e8`, `--claro-tinta:#1b231d`, `--claro-titulo:#13261b`, `--claro-suave:#4b423a`, `--claro-linea:rgba(70,40,20,.12)`, `--claro-tarjeta:rgba(255,250,244,.52)`, `--claro-tarjeta-solida:rgba(255,250,244,.94)`, `--claro-verde:#2f6a48`, `--claro-peligro:#a3321f`, `--claro-borde:rgba(255,255,255,.72)`, `--claro-filo:inset 0 1px 0 rgba(255,255,255,.85),0 18px 40px -26px rgba(150,70,20,.42),0 2px 6px -2px rgba(150,70,20,.08)`, `--claro-desenfoque:blur(22px) saturate(150%)`; reasigna `--text:var(--claro-tinta)`, `--muted:var(--claro-suave)`, `--focus:var(--claro-verde)`, `--sage:var(--claro-verde)`.

**`cookies.css:3-6` — ámbito `.cookies`**: `--cookies-solido:#142b24`, `--cookies-vidrio:rgba(16,36,29,.78)`, `--cookies-vidrio-panel:rgba(16,36,29,.86)`, `--cookies-texto:#fff`, `--cookies-suave:rgba(255,255,255,.84)`, `--cookies-linea:rgba(255,255,255,.16)`, `--cookies-activo:#d6e8a7`, `--cookies-error:#ffc4ba`, `--cookies-filo:inset 0 1px 0 rgba(255,255,255,.34),inset 0 0 0 1px rgba(255,255,255,.14)`.

**Variables usadas pero NUNCA definidas** (el valor cae al valor inicial del navegador): `--liquid-surface` (`base.css:1258`), `--liquid-hover-shadow` y `--liquid-hover-edge` (`base.css:1164`), `--header-surface` (`base.css:1260`). Solo existen como override de ámbito `--liquid-fill/-filter/-ink/-shadow` (`base.css:1639` usa `--liquid-fill` sin definirla globalmente).

**Tokens que NO existen como variables** (están como valores sueltos en las reglas): z-index, duraciones/curvas (salvo `--motion-control`), alturas de línea, sombras de tarjeta, blur de tarjeta. Se listan abajo tal como aparecen.

**Valores sueltos relevantes**

| Categoría | Valores literales | Dónde |
|---|---|---|
| **Radios** | botones `9999px !important`; tarjetas `.bento-panel` `22px` (`panel.css:49`, `apariencia.css:364`); campos del panel `14px` (`apariencia.css:424`); sidebar flotante `26px` (`apariencia.css:324`); menú móvil `24px` (`navegacion.css:99,…`); aviso de cookies `20px` (`cookies.css:18`); `.get-panel` `28px` (`base.css:1694`); badges `6px` (`base.css:19`); `.plant-card`/`.metric` `12px` (`base.css:844` bloque «Monitoring»). | varios |
| **Desenfoque (`backdrop-filter`)** | `blur(12px)` (sidebar botón, topbar), `blur(14px)` (btn brand/light), `blur(16px)` (btn nav/primary, `.auth-bento`), `blur(18px) saturate(160%)` (sidebar base), `blur(20px) saturate(180%)` (encabezado), `blur(22px) saturate(150%)` (`--claro-desenfoque`, tarjetas), `blur(24px)` (calendario), `blur(26px)` (panel de cookies); `url(#container-glass)` (refracción SVG, solo Chromium con hover, `apariencia.css:26-31`); `none` en `prefers-reduced-transparency`. | `base.css`, `apariencia.css`, `acceso.css`, `cookies.css` |
| **Bordes** | `1px solid rgba(255,255,255,.22)` (nav oscuro), `rgba(28,49,34,.16)` (light), `rgba(255,255,255,.32)` (brand), `#d4dfd6` (bento base), `var(--claro-borde)=rgba(255,255,255,.72)` (tarjeta del panel), `rgba(255,255,255,.2)` (campos del panel). | varios |
| **z-index** | `-3,-2,-1` (capas de fondo), `1` (main/section), `2`, `10`, `30`, `40`, `50` (skip-link original), `100` (skip-link final, `base.css:852`), `1200` (`apariencia.css:664` calendario), `9997`–`9999` (encabezados, topbar, menús), `10000` (aviso y panel de cookies), `10001` (confirmación de cookies). | varios |
| **Transiciones** | `transform .22s cubic-bezier(.22,1,.36,1)` + `background/box-shadow/border-color .22s ease` (botones, `base.css:1043-1047`); `150ms ease` en enlaces (`base.css:19`); `160ms` token `--motion-control`; `.nav-lamp` `.42s cubic-bezier(.34,1.3,.64,1)` (`apariencia.css:42`); interruptor de cookies `.15s ease`. | varios |
| **Animaciones (`@keyframes`)** | `button-spin` 900ms lineal (`base.css:1177`); `letter-rise` `.8s cubic-bezier(.125,.92,.69,.975)` con retardo `calc(var(--letter)*24ms + 120ms)` (`apariencia.css:57-59`); `contact-open` `.42s` / `contact-close` `.24s ease-in` (`base.css:1698-1702`); `cookies-entrada` `.25s`/`.2s ease-out` (`cookies.css:105`); `skeleton-pulse` 1.4s (`panel.css:486`). |
| **Altura de línea** | `body 1.6`; `h1,h2,h3 1.16`; `.page-heading h1 1.18`; `.garden-welcome h1 1.12`; `.legal-prose 1.78`; `.cookies 1.5`. | `base.css:19`, `panel.css` |
| **Tamaños de texto** | `body 16px`; botones `.95rem` (`.9rem` en nav/compact); `.badge 12px`; `.page-heading h1` `clamp(32px,3.2vw,42px)` peso 800 (`apariencia.css` «Jerarquía tipográfica»); hero `clamp(50px,5.5vw,78px)`; `.home h2 48px`; `.garden-welcome h1 clamp(34px,4vw,48px)`. | varios |
| **Pesos** | 400 cuerpo, 500 etiquetas/botones, 600 énfasis/botón brand, 700 `.home h2`, 800 `--display-weight` en títulos. | varios |
| **Alturas táctiles** | controles `min-height:44px` (botones, nav, enlaces de acceso), `.compact 38px`. | `base.css:1033,1157` |

### 1.2 Modo claro / oscuro

- **No hay conmutador ni `prefers-color-scheme`.** `color-scheme:light` en `:root` (`base.css:16`). Los campos del panel fuerzan `color-scheme:dark` dentro de `#app-page` y `dialog` (`apariencia.css:424`).
- El aspecto lo decide **la pantalla**, no la preferencia de la persona: portada y legales (oscuro/vidrio sobre fotos), acceso (claro, `.auth-flow`), panel usuaria/admin (crema con menú verde), cookies (oscuro). Preferencias de accesibilidad respetadas: `prefers-reduced-motion` (desactiva animaciones y transiciones, p. ej. `base.css:32`, `navegacion.css:90`), `prefers-reduced-transparency` (sólidos sin blur, p. ej. `base.css:1638`, `cookies.css:111`, `apariencia.css:532`), `forced-colors` (colores del sistema, p. ej. `base.css:1655`, `cookies.css:114`).
- `<meta name="theme-color" content="#f2efe9">` fijo (`index.html:6`).

### 1.3 Puntos de corte (breakpoints) y cambios de layout

Valores usados (de `grep @media`): `1500`, `1300`, `1150`, `1120`, `1100`, `1050`, `1025`, `1024`, `1000`, `900`, `850/701`, `820`, `769`, `768`, `720`, `700`, `640`, `600`, `520`, `480`, `360` px. Los que gobiernan el layout:

| Ancho | Qué cambia | Fuente |
|---|---|---|
| **≥1500** | Hero más alto (865/930px), título 82px. | `base.css:27,836` |
| **≤1120** | `.container` `calc(100% - 72px)`; hero en una columna; `.page-heading h1` 32px; auth más angosto. | `base.css:28,837` |
| **≤1100 / ≥1100** | Métricas del panel: 4 columnas desde 1100px. | `apariencia.css:386` |
| **≤1024** | `.notices-grid` y `.security-grid` a 1 columna; auth 40%/resto entre 901–1024. | `panel.css:105,184`, `acceso.css:68` |
| **≤900** | Auth una columna (`max-width:520px`); `.admin-management` 1 columna. | `acceso.css:73`, `apariencia.css:393` |
| **≥769 / ≤768** | **Corte principal.** ≥769: menú lateral fijo flotante (268px, `left/top/bottom:16px`), contenido con `margin-left:300px`, menú público en cápsula con indicador `.nav-lamp`. ≤768: el lateral se oculta (`display:none`) y se abre con botón «Menú» como panel flotante desde arriba (`top:calc(var(--header-height)+10px)`, `z-index:9998`); menú público igual (desplegable con fondo `.public-menu-shade`); botón «Iniciar sesión» del encabezado se oculta (queda dentro del menú). JS usa el mismo corte: `matchMedia('(max-width: 768px)')`. | `apariencia.css:322-336`, `navegacion.css:4-145`, `vistas/navegacion.js:6`, `controladores/administracion.js:388` |
| **≤700** | Hero en bloque; secciones apiladas; tarjetas de plantas a 1 columna; `.metric` en rejilla horizontal. | `base.css:30` |
| **≤600** | Botones de cuenta/privacidad a ancho completo; pestañas de Equipos y ventas en 2 columnas. | `panel.css:192,268`, `comercial.css:46` |
| **≤480** | `.account-tabs` ocupan todo el ancho; paddings menores; auth `padding:20px 16px 32px`. | `panel.css:125-132`, `acceso.css:77` |
| **≤360** | Se oculta el nombre «El Chilito» junto al isotipo en encabezados y topbar; el aviso de cookies reduce relleno de botones. | `navegacion.css:89`, `apariencia.css:253`, `cookies.css:100` |
| Tableta intermedia | `850–701`: rejilla de plantas con tarjetas más pequeñas; `769–900` ajustes de menú público. | `base.css:29`, `navegacion.css:68` |

### 1.4 Fuentes e íconos

| Recurso | Origen | Detalle | Fuente |
|---|---|---|---|
| **Geist** (variable, 100–900) | **Local** | `vistas/fuentes/Geist-Variable.ttf`, licencia OFL en `Geist-OFL.txt`; `font-display:swap`; precarga `<link rel="preload" … crossorigin>`; respaldo `Arial,sans-serif`. | `base.css:2`, `index.html:9` |
| CDN de fuentes / íconos | **Ninguno** (la CSP solo permite `'self'`). | `middleware.py:1-11` |
| **Íconos de trazo** | SVG propios en `icons` (33): `leaf drop sun temp bell user grid play arrow wifi off info clock tank check plus sparkle shield key mail external list inbox refresh calendar panel home menu close logout activity tool support`. Función `icon(name)` → `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">`; tamaño CSS `.icon{width:22px;height:22px}` (`base.css:19`), 20px en `.private-nav .icon`, 15px en `.badge .icon`, 30px en `.user-metric-icon`. Nombre desconocido → ícono `leaf`. | `vistas/comun.js:5-17` |
| Ojo / ojo tachado | SVG 20×20, trazo 1.8, para mostrar/ocultar contraseña. | `vistas/comun.js:18-19` |
| **Isotipo (hoja + habanero)** | SVG propio 64×64 con degradados (`#9BE3B1→#3E7B52`, `#FF9436→#F25C19→#C83506`); envoltorio 44×44, SVG 40×40. | `vistas/publico.js:6`, `base.css:895-904` |
| Dibujo de planta | SVG `.plant-drawing` 90×110 (`currentColor`, maceta `#a68e68`, `#756040`, fruto `#da9564`), tres variantes por transformación CSS. | `vistas/publico.js:240` |
| Favicon | `favicon.svg` (45 líneas). | `index.html:7` |
| **Imágenes** | `habanero-fondo.webp` (hero y panel visual de acceso, 1896×830), `prototipo-estacion.jpg` (1024×1024), `el-chilito-convivir.jpg`. Todas locales. | `publico.js:106,153,211`, `cuenta.js:59` |
| Filtro SVG | `<filter id="container-glass">` (feTurbulence + feDisplacementMap `scale=70`) para refracción del vidrio. | `index.html:20` |

### 1.5 Catálogo de componentes reutilizables

> Selectores completos con prefijo `html body[data-private=true]:is([data-role=admin],[data-role=user]) #app-page …` se abrevian a «(panel)». Todos son sobrescritos con `!important`; el orden de carga es `base → acceso → panel → navegacion → apariencia → cookies → comercial` (`index.html:8-15`), por lo que **`apariencia.css` gana** casi siempre.

#### Botones

Base común: `button:not(.password-eye-btn)`, `.button` → cápsula `border-radius:9999px`, `min-height:44px`, `padding:.65rem 1.4rem`, `font-size:.95rem`, `font-weight:500`, `gap:.55rem`, `overflow:hidden` (`base.css:1020-1048`).

| Variante / clase | Aspecto | Hover | Active | Focus | Disabled | Cargando | Dónde se usa |
|---|---|---|---|---|---|---|---|
| **Primario verde** `.btn-liquid-brand` | Degradado `180deg #3f7a55→#285a3c`, texto blanco, borde `rgba(255,255,255,.2)`, sombra `--lg-solid` (`apariencia.css:18-21`; versión previa `135deg rgba(47,89,60,.88)→rgba(31,64,41,.94)` + `blur(14px)` en `base.css:1051-1070`). Peso 600. Con `.full` 100% de ancho (`base.css:1159`). | `translateY(-1.5px)`, degradado `#478860→#2d6444` | `translateY(0) scale(.97)` y sombra interior | `outline:3px solid var(--focus); offset 4px` (`base.css:848`); en panel `#fff` en sidebar o `var(--claro-verde)` | fondo `--disabled-fill`, texto `--disabled-ink`, sin sombra/blur, `cursor:not-allowed` (`base.css:1171`) | `aria-busy=true`: `cursor:progress`, sin transform; el texto se reemplaza por `<span class="button-spinner">` + etiqueta «…» (`cuenta.js:172`) | «Iniciar sesión», «Crear cuenta», «Guardar contraseña», «Confirmar», «Registrar», «Publicar», «Emitir código»… |
| **Claro / secundario** `.btn-liquid-light` | Fondo `rgba(255,255,255,.72)`, texto `#142419`, borde transparente + `--lg-light` (`apariencia.css:23`); `min-height:40px`, `padding .55rem 1.35rem`. | fondo `.88`, `translateY(-1.5px)` | idem | idem | idem | idem | «Cancelar», «Ver detalle», filtros inactivos, «Reintentar», «Editar», «Archivar». |
| **Navegación sobre oscuro** `.btn-liquid-nav` | Texto blanco, degradado `rgba(255,255,255,.10)→rgba(15,28,19,.38)`, `blur(16px) saturate(180%)`, borde `rgba(255,255,255,.22)` (`base.css:942-982`); en apariencia fondo `rgba(255,255,255,.05)` + `--lg-dark`. | `translateY(-1.5px)`, borde `.38` | `scale(.97)` | idem | idem | — | Encabezado público, botón «Menú», topbar privada (ícono usuario/campana), cerrar ventana de contacto. |
| **Primario sobre oscuro** `.btn-liquid-primary` | Igual que `.btn-liquid-nav` (comparten regla). | idem | idem | idem | idem | — | «Iniciar sesión» del encabezado, «Quiero más información», «Enviar mensaje», «Iniciar sesión en el panel». |
| **Sidebar** `.btn-liquid-sidebar` / `.private-nav a` | Ancho 100%, `justify-content:flex-start`, `padding .75rem 1.15rem`; reposo `rgba(255,255,255,.07)` borde `rgba(255,255,255,.16)`, texto blanco 600; **activo** (`aria-current`) `linear-gradient(180deg,rgba(255,255,255,.34),rgba(255,255,255,.2))` borde `.4`. | fondo `.14` | — | outline blanco 3px | — | — | Menú lateral. |
| **Peligro** `.button[data-danger=true]` | Degradado rojo (base `#cf6146→#a83826` en hover, `apariencia.css:474-477`). En «Consola remota» el estilo pastel `color:#8c392f;background:#fff4f2` (`panel.css:559`) **compite**. | más oscuro | — | — | — | — | «Revocar autorización», «Anular registro». |
| **Pequeño** `.button.compact` | `min-height:38px`, `padding:.45rem 1.15rem` (`base.css:1155`). | | | | | | Encabezado, filtros, «Revocar», «Copiar dirección…». |
| **Icono** `.account-icon-link` | Botón compacto circular de solo ícono (`aria-label`, `title`). Variantes: `.password-eye-btn.no-glass` (sin vidrio, 44px), `.contact-close` (fijo arriba-derecha), `.cookies-cerrar` (44×44 círculo, transparente), `.maint-dialog-close`. | | | | | | Perfil, Avisos, cerrar. |
| **Menú (hamburguesa)** `.public-menu-toggle`, `.private-menu-toggle` | Compact nav con íconos `menu`/`close` alternos y texto «Menú»; solo ≤768px. | | | | | | Encabezados. |
| **Cookies** `.cookies-boton` | Cápsula `min-height:44px`, `rgba(255,255,255,.1)`, texto blanco 600 14px, borde 0, `--cookies-filo`. Los tres tienen el **mismo peso visual a propósito** (`cookies.css:24`). | `rgba(255,255,255,.2)` | — | outline blanco | `opacity:.6`, `cursor:progress` | `aria-busy` en raíz + `disabled` en todos los botones/inputs | Aviso y panel de cookies. |
| **Pie** `.site-footer__link` (enlace y botón «Configurar cookies») | Texto en enlace, sin cápsula (`base.css:591`). | `base.css:615` | | | | | Pie de página. |
| **Enlace de texto** `.auth-text-link`, `.legal-link` (botón) | Subrayado, `min-height:44px` (`acceso.css`). | | | | | | «¿Olvidaste tu contraseña?». |

#### Superficies

| Componente | Clases | Aspecto (según las reglas que ganan) | Dónde |
|---|---|---|---|
| **Tarjeta de vidrio del panel** | `.bento-panel` (+ `.user-metric`, `.user-chart`, `.user-log-panel`, `.admin-table-panel`, `.admin-ticket-detail`, `.admin-diagnostics`, `.admin-governance-list`, `.admin-management`; `.plant-card`, `.user-care`, `.notice-card` en la regla previa) | Fondo `var(--claro-tarjeta)=rgba(255,250,244,.52)`, `backdrop-filter:blur(22px) saturate(150%)`, borde `1px solid rgba(255,255,255,.72)`, radio **22px**, sombra `--claro-filo`; relleno 28px (22px ≤768, 20px ≤480). Sin soporte de blur: fondo sólido `rgba(255,250,244,.94)`. Base antigua: blanco opaco `#fff` + borde `#d4dfd6` (`panel.css:49`). | Todo el panel. `apariencia.css:363-369` |
| **Tarjeta de acceso** | `.auth-bento` | `#fff` (`rgba(255,255,255,.84)` + `blur(16px)` con soporte), borde `rgba(28,49,34,.12)`, radio 22px, relleno 32px, ancho máx. 480px. | Pantallas de acceso. `acceso.css:17-20,65-67` |
| **Tarjetas de portada** | `.bento-stat-card`, `.anatomy-glass-card`, `.prototype-visual-wrap`, `.get-panel`, `.lifestyle-bento-banner`, `.dark-glass-feature-card` | Vidrio oscuro con texto blanco; sólido `#1c3327` sin blur (`prefers-reduced-transparency`). `.get-panel` radio 28px, centrado, ancho máx. 760px. | Portada. `base.css:1673-1696` |
| **Encabezado de vidrio** | `.site-header`, `.header-glass-dark`, `.public-header` | `position:fixed` arriba, degradado `rgba(12,24,16,.72)→.48`, `blur(20px) saturate(180%)`, borde inferior `rgba(255,255,255,.14)`, `z-index:9999`; `.is-scrolled` más opaco (`rgba(10,22,14,.94→.88)`). En panel privado: `#f6f9f6`. | `base.css:1178-1216`, `panel.css:7-12` |
| **Menú lateral** | `.sidebar` | Escritorio: flotante 268px, radio 26px, degradado verde `rgba(40,98,62,.9)→rgba(22,62,42,.94)` + reflejos, `blur(18px) saturate(140%)`, borde `rgba(255,255,255,.2)`. Móvil: `#173c2f` (`navegacion.css`) o degradado `#28623e→#1b4a30` (`apariencia.css:338`). | `apariencia.css:322-340` |
| **Barra flotante privada** | `.private-topbar` | Sin fondo propio; contiene logotipo (solo móvil), botones de perfil, campana (usuarias) y «Menú». Botones verdes `#28623e` (`apariencia.css:356`). `position:fixed`, `left:300px` en ≥769. | `apariencia.css:232-243,356-360` |

#### Formularios

| Componente | Clases | Aspecto | Dónde |
|---|---|---|---|
| **Campo de texto (acceso)** | `.field` + `input` | Etiqueta 15px/600; input `min-height:48px`, borde `#819486`, radio 8px, `aria-invalid=true` → borde `#a32d22`; foco outline 3px `#264d32`; error `.field-error` 13px `#8b291f`. | `acceso.css`, `base.css:19` |
| **Campo de contraseña** | `.password-input-group` + `.password-eye-btn.no-glass` | Grupo con borde compartido; botón de ojo 44px que alterna `type` y `aria-label` («Mostrar/Ocultar …»), `aria-pressed`. | `cuenta.js:15,192-200` |
| **Campo del panel** | `input`, `select`, `textarea` dentro de `#app-page` y `dialog` | **Vidrio verde oscuro con texto blanco** `rgba(26,64,44,.95)`, borde `rgba(255,255,255,.2)`, radio 14px, `blur(14px)`, placeholder `rgba(255,255,255,.62)`, foco outline 3px `#f08a4b` (naranja), `accent-color:var(--claro-verde)` en radio/casilla. | `apariencia.css:424-440` |
| **Select** | `select` | Con `appearance:base-select` (Chrome/Edge recientes): lista desplegable de vidrio verde `rgba(24,58,40,.9)`, `blur(20px)`, radio 16px, flecha que gira 180°. Si no, lista nativa en modo oscuro. | `apariencia.css:441-455` |
| **Casilla / radio** | `input[type=checkbox|radio]` | Nativos con `accent-color`. En acceso, casilla 22×22 con `accent-color:#264d32`. | `acceso.css`, `apariencia.css` |
| **Interruptor** | `.cookies-interruptor` | Casilla real `role="switch"` oculta; pista 52×28 radio 999 borde `rgba(255,255,255,.62)`, activo `#d6e8a7` con círculo `#10241d`; transición .15s. **Solo existe en el panel de cookies**. | `cookies.css:62-68` |
| **Pestañas** | `.account-tabs` (enlaces/botones), `.commerce-tabs` (`role="tablist"`) | Cápsula `inline-flex`, `padding .35rem`, fondo `rgba(255,255,255,.55)`, radio 9999; cada pestaña `.button` 38px; activa `.btn-liquid-brand.active`; `aria-current="page"` o `aria-selected`. Filtros de avisos (`.notice-filters`) y buzón (`.inquiry-filters`) reutilizan el estilo. | `panel.css:56-77` |
| **Campo de fecha + calendario** | `.maint-date-control`, `.maint-date-field`, `.maint-calendar` (popover `manual`, `role="dialog"`) | Campo de texto `aaaa-mm-dd` con botón de calendario; calendario flotante con rejilla `role="grid"`, `z-index:1200`, fondo `rgba(255,250,244,.95)` `blur(24px)`; teclado completo (flechas, Inicio/Fin, RePág/AvPág, Esc). | `vistas/huerto.js:419-422,470-522`, `vistas/comun.js:157-310` |

#### Diálogos, avisos y estados

| Componente | Clases | Aspecto | Dónde |
|---|---|---|---|
| **Modal estándar** | `<dialog class="bento-panel app-dialog …">` | `showModal()`; ancho `min(440px,100% - 32px)`, `max-height:100svh-32px`, `::backdrop rgba(7,13,9,.46)`; título `h2`, acciones `.app-dialog-actions` (flex, botones `flex:1 1 150px`). | `panel.css:147-152` |
| **Modal de contacto** | `.contact-screen` | **Pantalla completa** con degradado `#16362b/#0f241c/#1b3d33`, animación `clip-path` desde el botón que lo abre (variable `--from`), botón cerrar fijo. | `base.css:1697-1722` |
| **Modal de cookies** | `.cookies-panel` | 560px, radio 20px, vidrio `rgba(16,36,29,.86)` `blur(26px)`; `::backdrop rgba(4,12,9,.62)`. | `cookies.css:38-44` |
| **Aviso de cookies (barra)** | `.cookies-aviso` | Fijo abajo (`z-index:10000`), máx. 920px, radio 20px, `#142b24` (vidrio con soporte); en ≤720px pegado al borde con radio superior 20px. | `cookies.css:13-20,89-96` |
| **Confirmación flotante («toast»)** | `.cookies-confirmacion` | Píldora fija abajo centrada `#142b24`; `role="status"`; se oculta a los 4500 ms. **Es el único toast del sitio.** | `cookies.css:77-86`, `publico.js:492-499` |
| **Mensaje en línea** | `#app-feedback`, `.user-feedback`, `.auth-feedback`, `.binding-status`, `.care-guides-notice` | Caja `role="status"` (éxito: verde `rgba(47,106,72,.1)`, borde `.28`) o `role="alert"` (error: `rgba(163,50,31,.08)`, texto `#a3321f`); toma foco al aparecer. | `panel.css:90,418`, `apariencia.css` «Mensajes» |
| **Insignia** | `.badge`, `.badge.neutral`, `.badge.error`; `.notice-condition.active|resolved`; `.read-state`; `.care-admin-state.is-…`; `.inquiry-state.is-…`; `.admin-connection.online|offline`; `.feature-planned` («Previsto») | Pastilla 12px, borde `var(--line)`, radio 6px (**no** es cápsula de vidrio). | `base.css:19,51-52`, `panel.css:78-79` |
| **Tabla** | `.user-table-scroll` (contenedor con `tabindex=0`, `role="region"`, `aria-label`) + `.user-table` / `.admin-table` | Colapso de bordes, 14px, `min-width:650px` (680px en comercial), cabecera gris-cálida 600, filas con borde `var(--claro-linea)`; fila seleccionada `rgba(250,114,74,.1)`. | `panel.css:384-385`, `apariencia.css` |
| **Lista** | `.user-history-list` (ol), `.security-keys`/`.key-item`, `.access-help-steps` (ol), `.user-token-steps` | Listas con ícono `check`/`key`/`support`. | `huerto.js:147,161`, `cuenta.js:253-262` |
| **Datos clave–valor** | `dl.profile-facts`, `.user-facts`, `.notice-facts`, `.commerce-facts` | Filas `div > dt + dd`. | varios |
| **Gráfica** | `.user-chart` + `<svg class="user-history-chart" viewBox="0 0 620 228">` | Polilínea + punto final, 3 líneas de cuadrícula, etiquetas de eje según rango; sin datos: marco con «—» y nota. `role="img"` con `<title>`/`<desc>`. | `vistas/huerto.js:102-111` |
| **Esqueleto de carga** | `.skeleton-line` (`.short .value .heading`) | Barra `#e1e9e2` radio 6px con `skeleton-pulse 1.4s`; `aria-hidden`. | `panel.css:486-492` |
| **Estado vacío / error** | `.app-state.bento-panel` (con `.icon-medallion`), `.user-empty`, `.user-empty-inline`, `.binding-empty`, `.care-guides-state` | Tarjeta con ícono (clock si carga, info si no), `h2`, `p`, y «Reintentar» si hay reintento. | `vistas/comun.js:28` |
| **Medallón de ícono** | `.icon-medallion` | Ícono 20px; en panel sin caja de fondo, color `var(--claro-titulo)`. | `base.css:646-653`, `apariencia.css:371` |
| **Acordeón** | `details.care-guide`, `.cookies-detalle`, `.binding-support` | `<details>/<summary>` con chevrón CSS que gira. | `huerto.js:216-223`, `cookies.css`, `apariencia.css:817` |
| **Indicador de menú** | `.nav-lamp` | Píldora que se desliza bajo el enlace de sección visible (solo ≥769px, con `IntersectionObserver`). | `apariencia.css:39-47`, `vistas/navegacion.js:9-39` |
| **Spinner de botón** | `.button-spinner` | 1em, borde 2px `currentColor`, giro 900ms. | `base.css:1176` |
| **Enlace «Saltar al contenido»** | `.skip-link` | `position:fixed`, aparece al enfocar (`translateY(-180%)`→`none`), fondo `--accent`. | `base.css:19,852`, `index.html:18` |

### 1.6 Inconsistencias (lo que NO sigue Liquid Glass o está duplicado)

| # | Hallazgo | Cita |
|---|---|---|
| 1 | **Tres pieles + cookies sin tokens comunes.** Portada oscura (`--ivory…` casi sin uso), acceso claro (`.auth-flow` redefine `--text/--muted/--sage/--focus`), panel crema (`--claro-*`) y cookies (`--cookies-*`). No hay una paleta única. | `base.css:3-17`, `acceso.css:3-4`, `apariencia.css:297-301`, `cookies.css:3-6` |
| 2 | **Piel oscura del panel muerta pero presente**: define `--garden-*`, `--glass-card`, fondo `#17393a`, y luego la clara la reemplaza con `!important`. El comentario cita `dashboard-glass.css`, **archivo que no existe**. | `apariencia.css:116-135`, `:295` |
| 3 | **Variables sin definir**: `--liquid-surface`, `--liquid-hover-shadow`, `--liquid-hover-edge`, `--header-surface` (el vidrio de botones base y hover depende de ellas). | `base.css:1164,1258,1260` |
| 4 | **Dos `:root` en `base.css`** y bloques duplicados: `@media(prefers-reduced-motion)` en 32 y 838; `.hero*` definidos en 21-25 y 836-837; `@media(max-width:700px)` repetido (30,31). | `base.css:3,844,32,838` |
| 5 | **Anchuras de menú lateral contradictorias**: grid `226px` (`base.css:1234`), `top:0;padding:20px 16px` (`apariencia.css:221`), flotante `268px` (`apariencia.css:324`), topbar `left:260px` (`:243`) vs `left:300px` (`:329`). | citas |
| 6 | **Tarjetas base opacas**: `.bento-panel` es blanco `#fff` sin blur y solo se convierte en vidrio por override dentro de `#app-page` y `@supports`; fuera de `#app-page` (p. ej. el diálogo de cierre de sesión, `dialog`) conserva el fondo opaco (`:not(dialog)` lo excluye expresamente). | `panel.css:49`, `apariencia.css:363` |
| 7 | **Campos del panel oscuros sobre tarjeta clara**: texto blanco sobre `rgba(26,64,44,.95)` dentro de tarjeta crema; los campos de acceso, de contacto y de «Revisar» usan otros estilos. `[data-maint-revise] select,textarea` fuerza borde `rgba(20,36,25,.2)` y fondo por defecto, **en conflicto** con la regla de campos oscuros. | `apariencia.css:424-440`, `panel.css:246-248` |
| 8 | **Colores de la era oscura en tarjetas**: `.plant-card`, `.metric`, `.reading-note`, `.absent`, `.card-top>span` usan `#b7c5a8`, `#c4d1b7`, `#b8c6ac`, `#a4b498` (verde claro sobre fondo oscuro). Si no los pisa una regla posterior quedan de bajo contraste sobre crema. | `base.css:844` (bloque «Monitoring…») |
| 9 | **Estilo en línea único**: `style="width:${plant.reading.value}%"` (barra de humedad). Es dinámico por naturaleza. | `vistas/huerto.js:79` |
| 10 | **Colores sueltos en JS**: degradados `#9BE3B1/#3E7B52/#FF9436/#F25C19/#C83506/#FFF3B0/#B6E8A7` del isotipo. | `vistas/publico.js:6` |
| 11 | **Insignias planas** (`.badge`, 6px, sin vidrio ni sombra) y `.skeleton-line` plano (`#e1e9e2`). Tablas planas. | `base.css:19`, `panel.css:486` |
| 12 | **Pie de página sólido** `linear-gradient(180deg,#0b140e,#070d09)`, sin blur (aunque su comentario dice «LIQUID GLASS»). | `base.css:508-515` |
| 13 | **Cookies con su propio sistema** (botones `.cookies-boton`, interruptor propio, `#142b24`); la ventana de contacto con otro degradado `#16362b…`; ninguna comparte componente con `.app-dialog`. | `cookies.css`, `base.css:1698` |
| 14 | **«Peligro» duplicado**: degradado rojo (`apariencia.css:474`) vs pastel (`panel.css:559`). | citas |
| 15 | **Sidebar móvil con 3 fondos**: `#173c2f` (`navegacion.css`), degradado `#28623e→#1b4a30` (`apariencia.css:338`), `#173c2f` por `--dashboard-forest` (`panel.css:505`). | citas |
| 16 | **Dependencia de `!important`** (1 046 apariciones en total) y de selectores de alta especificidad (`html body[data-private=true]:is(...) #app-page …`): cualquier rediseño choca con ellos. | conteo por archivo (arriba) |
| 17 | Refracción SVG (`url(#container-glass)`) solo con `@supports` + hover y **no en Safari** (`-webkit-touch-callout`); el resto usa `blur`. | `apariencia.css:26-31` |
| 18 | El «Avisos» de usuaria sale del menú lateral y vive en la barra flotante como campana; en `.account-icon-link` el estado activo es distinto al de la barra lateral. | `vistas/comun.js:39-42` |

---

## 2. Elementos globales

### 2.1 Enlace «Saltar al contenido» y marcador de pantalla
- `<a class="skip-link" href="#contenido">Saltar al contenido</a>` (`index.html:18`). Al hacer clic se evita la navegación y se enfoca `#contenido` (`enrutador.js:180-182`, `SiteViews.focusMain`). Todo contenedor principal lleva `id="contenido" tabindex="-1"`.

### 2.2 Encabezado público (portada y legales)
- **Archivos:** `vistas/publico.js:96-101` (`menuToggle`, `siteHeader`, `publicHeader`), `vistas/navegacion.js` (comportamiento), CSS `base.css:1178-1220`, `apariencia.css:39-47`, `navegacion.css:84-145`.
- **Aparece en:** portada, los tres textos legales. (Acceso, segundo paso y «sin acceso» usan el `auth-layout`, sin este encabezado: solo logotipo `.auth-brand`.)
- **Disposición (escritorio):**
```
┌ site-header (fijo, vidrio oscuro) ───────────────────────────────────────────────┐
│ [isotipo] El Chilito   ( Inicio | El proyecto | Ver prototipo | Consíguelo |       │ [Iniciar sesión]
│                         Cómo funciona )   ← cápsula con .nav-lamp deslizante       │
└────────────────────────────────────────────────────────────────────────────────────┘
```
- **Elementos:**
  - Logotipo/marca: enlace `#inicio`, `aria-label="El Chilito, inicio"`, isotipo 44px + texto «El Chilito» (1.18rem/600).
  - Navegación `<nav id="public-navigation" aria-label="Navegación principal">`: «Inicio» (`#inicio`, ícono home, `data-section=".hero"`), «El proyecto» (`#el-proyecto`, leaf), «Ver prototipo» (`#prototipo`, grid), «Consíguelo» (`#consiguelo`, sparkle), «Cómo funciona» (`#como-funciona`, info), «Iniciar sesión» (`#acceso`, user; solo visible en móvil). Cada uno `.button.compact.btn-liquid-nav`.
  - Acción derecha: «Iniciar sesión» `.btn-liquid-primary.public-header-login` (se oculta ≤768px).
  - Indicador `.nav-lamp` (solo ≥769px): ancho y `translateX` siguen al enlace activo; se actualiza con `IntersectionObserver` (`rootMargin:-45% 0px -54% 0px`), con clic y con `ResizeObserver`; en páginas legales (sin secciones) se oculta (`navegacion.js:15`).
  - `aria-current="location"` en el enlace activo (`navegacion.js:23`).
- **Disposición (móvil ≤768):** solo logotipo (nombre oculto ≤360px) y botón «Menú» (`aria-controls="public-navigation"`, `aria-expanded`, `aria-label` «Abrir menú de navegación»/«Cerrar menú de navegación», íconos menu/close). El menú se abre como panel (`position:absolute`, `top:calc(100% + 10px)`, fondo `#173c2f`, radio 24px) con capa `.public-menu-shade`. Se cierra con Escape, clic fuera, foco fuera, clic en un enlace o al volver a escritorio (`navegacion.js:83-137`). Se añade `body.public-menu-open`.
- **Con sesión:** `showAccountAccess` reemplaza «Iniciar sesión» por el destino del panel: en el encabezado se vuelve un botón de solo ícono usuario con `aria-label="Ir a mi panel"`/`title`; en el menú y demás enlaces `#acceso` el texto pasa a «Ir a mi panel» (`publico.js:9-18`). `AppModel.panelHome`: admin → `#admin/<primer destino>` o `#cuenta/seguridad` si `mfaRequired`; usuaria → `#huerto`.
- **Comportamiento de scroll:** `is-scrolled` se activa cuando el `.hero` sale del encabezado (`navegacion.js:48-50`); el hash del `focusin` evita que el encabezado tape el foco (`navegacion.js:62-68`).

### 2.3 Marco privado: barra flotante + menú lateral + cierre de sesión
- **Archivos:** `vistas/comun.js:34-57` (`shell`), `:89-146` (`frame`), `controladores/administracion.js:209-434` (`AppController`), CSS `apariencia.css:219-260,322-360`, `navegacion.css:1-83`.
- **Disposición (escritorio ≥769):**
```
┌ sidebar flotante (268px, verde) ┐ ┌ private-content ──────────────────────────────────────┐
│ [isotipo] El Chilito            │ │                                 [👤 perfil] [🔔 avisos]* │ ← topbar flotante (*solo usuaria)
│ ⌂ Ver página principal          │ │ #app-feedback (mensajes)                               │
│ (Administración)**              │ │ #app-page  ← aquí se monta la pantalla                 │
│  botones de navegación          │ │                                                        │
│  (Gestión)** …  Mi cuenta       │ └────────────────────────────────────────────────────────┘
│ [↪ Cerrar sesión]               │
└─────────────────────────────────┘   (**solo administración)
```
- **Elementos del lateral** (`<aside class="sidebar" id="garden-navigation">`):
  - Logotipo `sidebar-brand` → `#inicio` (`aria-label="El Chilito, inicio"`).
  - «Ver página principal» (`.sidebar-home`, ícono home) → `#inicio`.
  - Solo admin: rótulo `<p class="private-role-label">Administración</p>`.
  - `<nav class="private-nav" aria-label="Navegación de la aplicación">`: enlaces `.button.btn-liquid-sidebar` con ícono + texto; el actual lleva `aria-current="page"`.
  - Solo admin: rótulo «Gestión» y `.private-pending` con «Abrir correo de soporte» (`target="_blank" rel="noopener noreferrer"`, íconos mail+external, texto sr-only «(se abre en otra pestaña)»; **solo si** `supportContact` es un correo válido → URL `https://mail.google.com/mail/?authuser=…`, `modelos/comun.js:70-71`) y los destinos de gestión.
  - Pie: botón «Cerrar sesión» (`.private-menu-logout`, ícono logout) → abre el diálogo de confirmación.
- **Barra flotante** `.private-topbar` (`vistas/comun.js:42`): logotipo `topbar-brand` (oculto en escritorio), botón perfil `aria-label="Mi cuenta"`/`title="Mi cuenta"` → `#cuenta`, campana `aria-label="Avisos"`/`title="Avisos"` → `#avisos` (solo usuaria) y botón «Menú» (solo ≤768px).
- **Menú móvil:** botón «Menú» (`data-app-action="toggle-menu"`, `aria-controls="garden-navigation"`, `aria-expanded`); el lateral recibe `inert` + `aria-hidden` cuando está cerrado en móvil; se cierra con Escape, clic/foco fuera, clic en un enlace; `.private-menu-shade` oscurece el fondo. Cambiar de ancho reconfigura el estado (`administracion.js:392-419`).
- **Diálogo «¿Cerrar sesión?»** (`logoutConfirmation`, `comun.js:29`): título «¿Cerrar sesión?», texto «Tendrás que iniciar sesión de nuevo para entrar a tu cuenta.», error `.logout-error` `role="alert"` oculto («No se pudo cerrar la sesión. Inténtalo de nuevo.»), botones «Cancelar» (`btn-liquid-light`, `autofocus`) y «Cerrar sesión» (`btn-liquid-brand`; mientras trabaja: «Cerrando sesión…» y todos los botones `disabled`, `aria-busy`). Acción: `AuthService.logout` → `DELETE /_allauth/browser/v1/auth/session` (antes cierra la sesión técnica remota si existe), limpia estado, `CookieController.refresh()` y lleva a `#acceso`. Escape cierra si no está ocupado.
- **Bienvenida:** si `profile.welcomePending === true`, `WelcomeController.offer` abre el diálogo «Te damos la bienvenida» (ver ficha 3.B).
- **Accesibilidad:** `main#contenido tabindex=-1`, `#app-feedback role="status"`, `keepVisible` evita que el teclado móvil tape un campo (`comun.js:141-144`).

### 2.4 Pie de página público
- **Archivos:** `vistas/publico.js:47-95` (`publicFooter`), CSS `base.css:508-640` y `:1592` (móvil). Aparece en portada y legales.
- **Estructura (escritorio):** rejilla de 3 columnas `1.4fr 1fr 1fr`, gap 3rem; barra inferior.
```
 ┌ Marca ─────────────────────┐ ┌ Navegación ──────────┐ ┌ Plataforma y Legal ──────────┐
 │ [isotipo] El Chilito       │ │ Inicio               │ │ Iniciar sesión en el panel   │
 │ Estación doméstica …       │ │ El proyecto          │ │ Términos y condiciones       │
 │ [Control local ESP32 · 5…] │ │ Conoce el prototipo  │ │ Aviso de privacidad          │
 └────────────────────────────┘ │ El cuidado del huerto│ │ Política de cookies          │
                                └──────────────────────┘ │ [Configurar cookies]         │
 ── © 2026 El Chilito. Todos los derechos reservados.   Yucatán, México · Términos y condiciones · Privacidad
```
- **Textos literales:** «Estación doméstica inteligente para el cultivo interior de chile habanero (Capsicum chinense), con riego automatizado por tiempos, iluminación LED programada y monitoreo IoT.»; pastilla «Control local ESP32 · 5 sensores · Asistente IA previsto»; encabezados «Navegación» y «Plataforma y Legal»; enlaces `#inicio` «Inicio», `#el-proyecto` «El proyecto», `#prototipo` «Conoce el prototipo», `#como-funciona` «El cuidado del huerto»; `#acceso` «Iniciar sesión en el panel», `#terminos` «Términos y condiciones», `#privacidad` «Aviso de privacidad», `#cookies` «Política de cookies», botón «Configurar cookies» (`data-cookie-settings`) que abre las preferencias; barra inferior «© 2026 El Chilito. Todos los derechos reservados.», «Yucatán, México», «Términos y condiciones», «Privacidad».
- **Observaciones:** el enlace «Iniciar sesión en el panel» no cambia a «Ir a mi panel» por sí solo salvo que `showAccountAccess` lo encuentre (selecciona `a[href="#acceso"]`, por lo que **sí** cambia: `publico.js:9`). El pie no existe en el panel privado ni en acceso.

### 2.5 Aviso de cookies («Tu privacidad y las cookies»)
- **Archivos:** `vistas/publico.js:407-503` (`CookieViews`), `controladores/publico.js:7-101` (`CookieController`), `modelos/comun.js:23-44` (`PrivacyData`), CSS `cookies.css`. Se monta una sola vez al cargar (`CookieController.start()`, `enrutador.js:207`) en `document.body`, **encima de todas las pantallas** (incluido el panel).
- **Cuándo aparece:** cuando el servidor dice que la decisión no existe (`decided:false`) **o** cuando falló consultar el estado (`failed`: «sin respuesta del servidor la decisión es desconocida: se vuelve a preguntar», `controladores/publico.js:13-15`). Se vuelve a consultar tras iniciar o cerrar sesión (`CookieController.refresh()`).
- **Barra inferior** `div.cookies-aviso[role="region"][aria-labelledby="cookies-aviso-titulo"]`:
  - `h2` «Tu privacidad y las cookies».
  - Texto: «Usamos cookies necesarias para mantener tu sesión, proteger tus acciones y recordar tus preferencias. Si lo autorizas, también utilizaremos cookies para obtener estadísticas internas de navegación y mejorar la web. Puedes rechazar estas estadísticas y seguir utilizando el sitio.»
  - Enlace «Leer la política de cookies» → `#cookies`.
  - Botones (3 columnas iguales): «Aceptar» → `choose(true)`; «Rechazar» → `choose(false)`; «Configurar» → abre el panel.
  - Error (`role="alert"`): «No pudimos guardar tu elección. Inténtalo de nuevo».
- **Ventana «Configurar cookies»** (`<dialog class="cookies-panel">` con `aria-labelledby/describedby`): `h2` «Configurar cookies»; texto «Elige si quieres permitir las estadísticas opcionales. Puedes cambiar tu decisión cuando quieras desde «Configurar cookies», al pie de la página.»; botón cerrar (ícono close, `aria-label="Cerrar sin guardar"`); categoría «Cookies necesarias» («Permiten mantener tu sesión, proteger las solicitudes que haces a la web y recordar tu elección de cookies.») con etiqueta fija «Siempre activas» y `<details>` «Ver detalles» (`sessionid`: mantiene la sesión iniciada; `csrftoken`: ayuda a proteger tus acciones frente a solicitudes enviadas desde otros sitios; `chilito_preferencia`: recuerda tu elección de cookies durante un máximo de 180 días); categoría «Estadísticas opcionales» («Nos ayudan a conocer cuántas visitas reciben las secciones para mejorar la web. Puedes desactivarlas sin perder acceso a tu cuenta ni a tu huerto.») con **interruptor** `name="statistics"` (`role="switch"`) y detalles («Utilizan la cookie `chilito_estadistica`, con una duración máxima de 30 minutos. Los totales de visitas no incluyen tu nombre ni tu correo electrónico.»); botones «Guardar preferencias» (submit) y «Rechazar estadísticas».
- **Confirmación:** píldora «Preferencias guardadas» (`role="status"`, foco si el foco estaba en el aviso), se oculta a 4,5 s.
- **Backend:** `GET/POST /api/privacidad/cookies` (`privacidad/api.py:62-77`). Solo un botón guarda decisión: cerrar la ventana o ignorar el aviso **no** consiente (`controladores/publico.js:4-5`). Mientras se guarda, todos los botones/inputs quedan `disabled` y la raíz `aria-busy`.
- **Estadísticas:** si la decisión es «sí», cada cambio de sección (`PrivacyModel.sectionOf`) envía `POST /api/estadisticas/seccion` `{section}` (`controladores/publico.js:47-50,91-94`).
- **Responsive:** ≤720px la barra pasa a una columna pegada al borde inferior con `padding-bottom` + `safe-area-inset-bottom`; ≤360px botones con menos relleno. Reserva de espacio: `scroll-padding-bottom` = altura del aviso + 32px (`publico.js:474`).
- **Accesibilidad:** `role="region"` con título; diálogo modal nativo; foco visible blanco 3px; Escape cierra el panel sin guardar; interruptor es una casilla real.

### 2.6 Pantalla de carga / comprobación de sesión
- **Texto literal** (`AuthViews.sessionChecking`, `cuenta.js:103`): usa el `auth-layout` con título «Comprobando sesión», introducción «Espera un momento.», y `div.auth-feedback[role="status"]` «Comprobando tu acceso…». Se muestra solo si se llega a una ruta privada sin marco previo (`enrutador.js:69-72`). Además `#app` recibe `aria-busy="true"` durante la comprobación (`SiteViews.busy`).
- **Dentro de las pantallas:** esqueletos `.skeleton-line` (Mi huerto, Panel técnico) y tarjetas `app-state` «Cargando …» (Avisos, Cuenta, Administración). Ver cada ficha.

### 2.7 Sesión vencida y avisos de sesión
- **Disparador:** cualquier petición que reciba HTTP 401 llama `ChilitoHTTP.sessionExpired()` (en `UserGardenService.read/write`, `CareGuideService`, `BindingService`, `AdminService`, `InquiryService`, `MaintenanceService`, `AppService`).
- **Reacción** (`enrutador.js:185-191`): invalida peticiones en curso, olvida la sesión, refresca cookies, y fija `authContext.feedback = 'Tu sesión ha vencido. Inicia sesión de nuevo.'`; lleva a `#acceso` (o re-renderiza si ya está ahí). La pantalla de acceso muestra el mensaje en `#auth-feedback` (`role="status"`, clase `.is-error`, sin tomar foco).
- **Reglas de caducidad del servidor** (`backend/web/sesion.py`): `CHILITO_SESION_ABSOLUTA`, `CHILITO_INACTIVIDAD_USUARIO`, `CHILITO_INACTIVIDAD_ADMIN` (variables de configuración; los valores propuestos en `privacidad/politicas.py` son 8 h absoluta, 30 min usuaria, 15 min admin). Las peticiones de fondo con cabecera `X-Chilito-Sondeo` **no** alargan la sesión (`sesion.py:es_sondeo`).
- **Otros avisos de sesión:** «Inicia sesión para continuar.» (ruta privada sin sesión), «No podemos comprobar tu sesión. Inténtalo de nuevo.» (servidor no responde), «Inicia sesión para continuar la verificación de tu correo.» (verificación vencida), «Inicia sesión de nuevo» / «Tu sesión ya no está disponible.» (pantalla resultado), «Vuelve a iniciar sesión» (verificación vencida).

### 2.8 Manejo global de errores
- **No hay captura global** (`window.onerror`/`unhandledrejection`). Cada servicio devuelve `{status:'…'}` y cada pantalla traduce el estado a texto.
- **Transporte:** `ChilitoHTTP.request` solo admite rutas `/api/…` y `/_allauth/browser/v1/…` (lanza `Error('Unsupported endpoint')` si no); añade `X-CSRFToken`, `Idempotency-Key` (UUID por huella de POST `/api/…` que se **conserva** tras errores 5xx/429 para reintentar sin duplicar) y `redirect:'error'`, `cache:'no-store'`; una respuesta no-JSON se trata como `{}` y nunca como éxito (`modelos/cuenta.js:104-135`).
- **Backend:** errores JSON `{status, code}` (`web/respuestas.py:17-18`): `invalid-input` 400, `unauthenticated` 401, `access-denied`/`garden-unassigned`/`mfa-required`/`reauthentication-required` 403, `stale-record`/`idempotency-conflict`/`operation-conflict` 409, `request-too-large` 413, `rate-limited` 429, `service-unavailable` 503 (`web/api.py:50-78`); 404 y 500 globales devuelven JSON (`static_views.py`), **no HTML**.
- **Error de arranque:** si `GET /api/acceso/configuracion` falla, el frontend arranca con `AuthConfig` por defecto (registro no permitido, política de contraseña vacía) y «cada acción sigue fallando por el lado seguro» (`enrutador.js:200-208`).
- **Mensajes genéricos más comunes (literales):** «No se pudo completar la solicitud. Inténtalo de nuevo.» (panel), «El servicio no está disponible en este momento. Inténtalo de nuevo más tarde.» (acceso), «No se pudo completar la operación. Inténtalo de nuevo.» (admin/mantenimientos), «No pudimos confirmar el resultado. Vuelve a intentarlo sin cambiar nada: no se duplicará.» (guías).

### 2.9 Otros elementos globales
- **Ventana de contacto** y **fondo de la portada**: ver 3.A.
- **Calendario de fechas** (`DateFilterViews`): se inserta en `document.body` como popover y se destruye al salir de la pantalla (`vistas/comun.js:165-166,306`).
- **Teclado móvil:** `keepVisible` en acceso y panel (`visualViewport`).
- **Foco tras navegar:** `SiteViews.focusMain` + `toTop` solo si cambió la ruta (`enrutador.js:176`).

---

## 3. Pantallas (una ficha por pantalla)

> Convenciones de las fichas: «Archivos» abrevia `V`=vista, `C`=controlador, `M`=modelo, `CSS`. «Datos» indica `endpoint → campo JSON`. Las líneas de CSS son aproximadas al bloque que define la regla.
> Todas las pantallas se montan dentro de `<div id="app">`. Las privadas se montan dentro de `#app-page` (ver 2.3).

### 3.A Portada pública

La portada es **una sola pantalla larga** (`landing()`, `vistas/publico.js:102-239`) con secciones ancladas. Navegar entre `#inicio`, `#el-proyecto`, `#prototipo`, `#consiguelo`, `#como-funciona` **no reconstruye** la página: solo hace scroll y enfoca la sección (`enrutador.js:118,166-177`, `SiteViews.focusAnchor`). Estructura vertical común:

```
┌ encabezado público fijo ──────────────────────────────┐   (2.2)
│ HERO (foto a pantalla, h1 grande abajo-izquierda)      │  #inicio
├────────────────────────────────────────────────────────┤
│ EL PROYECTO: título | texto  + 3 tarjetas de cifras    │  #el-proyecto
├────────────────────────────────────────────────────────┤
│ PROTOTIPO: título + foto | 4 tarjetas de anatomía      │  #prototipo
├────────────────────────────────────────────────────────┤
│ CONSÍGUELO: tarjeta centrada + botón (abre ventana)    │  #consiguelo
├────────────────────────────────────────────────────────┤
│ CÓMO FUNCIONA: banner con texto+foto + 4 tarjetas      │  #como-funciona
├────────────────────────────────────────────────────────┤
│ pie de página (2.4)                                    │
└────────────────────────────────────────────────────────┘
```

#### Inicio (hero) — `#inicio`
- **Archivos:** V `vistas/publico.js:105-108`; C `enrutador.js:162-172`, `revealTitle` (`publico.js:20-46`); CSS `base.css:20-25,836-837`, `apariencia.css:56-59`.
- **Acceso:** pública. Con sesión, el encabezado muestra «Ir a mi panel» (`offerAccount`, `enrutador.js:44-52`).
- **Propósito:** presentar el producto con foto de fondo y titular.
- **Disposición (escritorio):** `<section class="hero">` a alto mínimo 790px (865 ≥1500px): foto absoluta de fondo (`habanero-fondo.webp`, `object-position:center 40%`) con sombra degradada oscura (`.hero-shade`), contenido `.hero-content.container` anclado abajo, rejilla `1fr 230px` (la columna derecha está vacía).
- **Disposición (móvil ≤700):** altura 755px, foto al 74% alto, texto en bloque con `padding-top:143–175px`, título `clamp(41px,10.5vw,62px)`.
- **Elementos:**
  - Imagen decorativa con `alt="Ambientación ilustrativa: hojas de habanero y frutos anaranjados junto a una luz suave de interior."`, `width=1896 height=830`, `fetchpriority="high"`.
  - `h1#hero-title` en tres líneas: «Tu huerto de» / «habanero,» / «dentro de casa.» (blanco, peso 800, `clamp(50px,5.5vw,78px)`). Animación de entrada letra por letra (`.reveal-letter`, `letter-rise`) **solo la primera vez** y si no hay `prefers-reduced-motion`; durante la animación el título tiene `aria-label` con el texto completo y las líneas `aria-hidden` (`publico.js:20-46`).
  - Párrafo `.hero-description`: «Un huerto urbano para interiores que reúne tres plantas de habanero y una forma más cercana de cuidar lo que cultivas.» (18px, `#dde4d3`, máx. 495px).
- **Botones/acciones:** ninguno propio (el encabezado y el pie son globales).
- **Estados:** sin carga ni vacío (contenido fijo).
- **Actualización automática:** no.
- **Accesibilidad:** `section aria-labelledby="hero-title"`; `main#contenido tabindex=-1` envuelve el contenido del hero.
- **Observaciones:** no hay botón de llamada a la acción en el hero; el único acceso es el encabezado.

#### El proyecto — `#el-proyecto`
- **Archivos:** V `publico.js:109-140`; CSS `base.css` (`.project-section`, `.bento-stat-card`) + `base.css:1673-1696` (vidrio oscuro).
- **Acceso:** pública.
- **Disposición (escritorio):** rejilla 2 columnas (`gap:35px 85px`, `padding:86px 0 69px`): izquierda título, derecha subtítulo y párrafos; debajo, 3 tarjetas `bento-stat-card` en fila.
```
[ h2: Un pequeño huerto.   ]  [ h3 Cultivar habanero en casa, … ]
[       Una nueva conexión.]  [ p  Falta de espacio exterior … ]
                              [ p  El sistema automatiza …     ]
[ 03 Plantas ] [ 05 Sensores ] [ 100% Riego y luz ]
```
- **Disposición (móvil):** columna única apilada (`flex-direction:column`).
- **Elementos (literales):**
  - `h2#project-title`: «Un pequeño huerto.» (salto) «Una nueva conexión.».
  - `h3`: «Cultivar habanero en casa, sin depender de un patio ni de tu agenda.»
  - `p`: «Falta de espacio exterior, lluvias intensas o poco tiempo libre suelen impedir tener un cultivo propio. El Chilito reúne tres plantas de chile habanero (*Capsicum chinense*) en una estación interior de madera con drenaje seguro y bandeja recolectora que protege la oxigenación de las raíces.»
  - `p`: «El sistema automatiza el riego por tiempos programados y los ciclos de iluminación LED, mientras sus sensores monitorean el cultivo y te informan desde tu celular o computadora.»
  - Tarjeta «03» / «Plantas en producción» / «Cultivo en sustrato y composta con drenaje independiente y bandeja recolectora para evitar saturación en las raíces.»
  - Tarjeta «05» / «Sensores en tiempo real» / «Tres sensores de humedad en sustrato, un sensor de clima ambiental y un detector de nivel de agua conectados vía ESP32.»
  - Tarjeta «100%» / «Riego y luz por tiempos» / «Ciclos automáticos programados con bloqueo inteligente de la bomba cuando el depósito requiere recarga de agua.»
- **Aspecto:** tarjetas de vidrio oscuro con texto blanco (`.bento-stat-card`).
- **Estados / acciones / formularios:** ninguno.
- **Observaciones:** cifras («03», «05», «100%») son texto fijo, no datos.

#### Prototipo — `#prototipo`
- **Archivos:** V `publico.js:142-187`.
- **Disposición (escritorio):** encabezado en dos partes (título a la izquierda, subtítulo a la derecha); debajo rejilla: foto cuadrada a la izquierda (`prototipo-estacion.jpg`, 1024×1024, `loading="lazy"`, `alt="Prototipo del huerto urbano inteligente El Chilito en el hogar"`) y columna de 4 tarjetas `anatomy-glass-card` a la derecha.
- **Elementos (literales):** `h2#prototype-title` «Conoce el prototipo»; `.prototype-subtitle` «Tres plantas. Un mismo espacio autónomo.»; tarjetas con insignia numérica y `h4`:
  - `01` «Iluminación LED programada» — «Cobertura superior con ciclos automáticos de encendido y apagado y altura ajustable manualmente según el crecimiento.»
  - `02` «Distribución triangular con drenaje» — «Tres compartimentos con sustrato y composta que evitan el estancamiento de agua y cuidan la salud de la raíz.»
  - `03` «Controlador IoT ESP32» — «Módulo lateral con conectividad Wi-Fi que ejecuta las reglas locales de riego y envía lecturas cifradas a la plataforma web.»
  - `04` «Depósito frontal con protección» — «Reserva inferior accesible de frente con sensor de nivel bajo que detiene la bomba automáticamente para proteger el equipo.»
- **Móvil:** apilado (foto arriba, tarjetas debajo).
- **Observaciones:** el enlace de menú dice «Ver prototipo», el pie «Conoce el prototipo» y el título «Conoce el prototipo» (tres nombres para la misma sección).

#### Consíguelo — `#consiguelo` (y ventana «Cuéntanos qué quieres saber»)
- **Archivos:** V `publico.js:189-199` (sección), `:271-330` (`ContactViews`); C `controladores/publico.js:105-128` (`ContactController`); M `modelos/publico.js:6-15` (`ProductContact`); CSS `base.css:1694-1722`.
- **Acceso:** pública. Con la sesión de cualquier rol funciona igual.
- **Propósito:** captar consultas de personas interesadas (precio, disponibilidad, aviso de lanzamiento).
- **Disposición (escritorio):** sección con una tarjeta `.get-panel` centrada (máx. 760px, radio 28px, texto centrado).
- **Elementos de la sección:** `h2#get-title` «Sé de los primeros en tener tu Chilito.»; `p` «Será un equipo completo, sin planes ni suscripciones. Pregúntanos por el precio y la disponibilidad, o pide que te avisemos cuando salga la primera versión.»; botón «Quiero más información» (`.btn-liquid-primary.get-open`, `data-contact-open`).
- **Botones y acciones:**

| Texto | Posición | Variante | Qué hace | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|---|---|---|
| «Quiero más información» | Centro de la tarjeta | Primario sobre oscuro | Abre el diálogo con animación `clip-path` desde el botón; limpia el estado | — | no | — | — |
| ícono ✕ («Cerrar», `aria-label="Cerrar"`) | Arriba-derecha, fijo | Icono | Cierra con animación de 240 ms (o directo si `prefers-reduced-motion`); también Esc | — | no | — | — |
| «Enviar mensaje» (→ «Enviando…») | Fin del formulario | Primario sobre oscuro | Valida y envía | `POST /api/contacto` | no | «Recibimos tu mensaje. Te responderemos a tu correo.» y se limpia el formulario | ver abajo |
| Enlace «Aviso de privacidad» | Nota bajo el formulario | Texto | Va a `#privacidad` y cierra el diálogo | — | no | — | — |

- **Ventana modal «Cuéntanos qué quieres saber»** (`<dialog class="contact-screen" aria-labelledby="contact-title">`): **pantalla completa**, fondo degradado verde oscuro, rejilla de 2 columnas (≤820px una columna con `padding-top:44px`):
```
┌ [✕] ─────────────────────────────────────────────────────────┐
│ Cuéntanos qué quieres saber   │ Nombre (opcional)             │
│ Escríbenos sobre El Chilito … │ Correo electrónico            │
│ ✓ Pregunta por el precio…     │ Tu mensaje (textarea)         │
│ ✓ Pide que te avisemos…       │ nota de privacidad            │
│ También puedes escribirnos a  │ [estado]  [Enviar mensaje]    │
└───────────────────────────────────────────────────────────────┘
```
  - Texto izquierdo: `h2#contact-title` «Cuéntanos qué quieres saber»; «Escríbenos sobre El Chilito y te responderemos a tu correo.»; lista con ícono check: «Pregunta por el precio y la disponibilidad.» y «Pide que te avisemos cuando salga la primera versión.»; si `supportContact` es válido: «También puedes escribirnos a <enlace mailto>.» (`CHILITO_CONTACTO_SOPORTE`).
- **Formulario** (`novalidate`):

| Campo | Etiqueta | Placeholder | Tipo | Obligatorio | Validación cliente | Validación servidor | Mensaje |
|---|---|---|---|---|---|---|---|
| `name` | «Nombre (opcional)» | — | texto, `maxlength=100`, `autocomplete=name` | no | — | texto imprimible ≤100 (`web/services.py:71-80`) | — |
| `email` | «Correo electrónico» | — | `email`, `maxlength=254`, `autocomplete=email` | sí | `/^[^\s@]+@[^\s@]+\.[^\s@]+$/` tras `trim` (`publico.js:118`) | `validate_email`, ≤254 | «Revisa tu correo y tu mensaje.» |
| `message` | «Tu mensaje» | — | `textarea rows=5 maxlength=2000` | sí | no vacío tras `trim` | no vacío, ≤2000, imprimible (permite saltos) | idem |
| `website` | «Sitio web» | — | texto, `tabindex=-1`, `aria-hidden`, clase `contact-trap` | — (campo trampa) | — | si viene relleno, el servidor responde `accepted` **sin guardar nada** (`api.py:220`) | — |

  - Nota fija: «Usaremos tu correo solo para responderte. Consulta el Aviso de privacidad.»
  - Mensajes de estado (`<p data-contact-status role="status">`): `accepted` «Recibimos tu mensaje. Te responderemos a tu correo.»; `invalid` (400 o validación local) «Revisa tu correo y tu mensaje.»; `limited` (429) «Enviaste varios mensajes seguidos. Inténtalo más tarde.»; `unavailable` (resto/red) «No se pudo enviar. Inténtalo más tarde o escríbenos por correo.»
- **Estados:** enviando (`submit disabled`, texto «Enviando…»), éxito (formulario limpio, mensaje), error. Cierre con Escape también ejecuta la animación (`cancel` → `view.close`).
- **Datos / backend:** `POST /api/contacto {name,email,message,website}` → `{status:'accepted'}` (`web/api.py:213-226`); cuota `ratelimit.consume(action='contacto_producto')`; guarda en `datos_consultaproducto` y encola `datos_avisocorreo` (`datos/services.py:436-445`); el mismo correo+mensaje en 10 min **no se duplica** (devuelve la anterior).
- **Actualización automática:** no.
- **Accesibilidad:** `<dialog>` nativo con `aria-labelledby`; foco al botón de apertura al cerrar (`closed()`); estado `role="status"`; la ventana cierra al seguir un enlace `#…`.
- **Observaciones:** la consulta llega al buzón «Solicitudes del producto» de administración (3.D). Precio y disponibilidad están «sin definir» (comentario `publico.js:189`). El campo «Nombre» no tiene placeholder; no hay texto de ayuda de longitud.

#### Cómo funciona — `#como-funciona`
- **Archivos:** V `publico.js:201-237`; CSS `base.css` (`.functions-section` fondo `#223520`).
- **Disposición (escritorio):** banner `lifestyle-bento-banner` (texto a la izquierda, foto a la derecha) y debajo rejilla de 4 tarjetas oscuras `dark-glass-feature-card`.
- **Elementos (literales):** `h2#functions-title` «El cuidado del huerto, pensado para convivir contigo.»; `p` «Diseñado para integrarse de forma limpia en interiores. Supervisa la humedad del sustrato, la temperatura ambiental y el nivel del depósito desde tu celular o computadora. Más adelante, un asistente de IA generativa ayudará a interpretar las lecturas.»; botón/enlace «Iniciar sesión en el panel» (`#acceso`, `btn-liquid-primary`); foto `el-chilito-convivir.jpg` con `alt="Huerto urbano inteligente El Chilito conviviendo en el hogar"` (lazy). Tarjetas (ícono + `h4` + texto):
  - ícono clock — «Riego automatizado por tiempos» — «Ciclos de riego programados desde el depósito inferior con límites seguros de operación y bloqueo automático ante nivel bajo de agua.»
  - ícono leaf — «Monitoreo con 5 sensores» — «Tres sensores de humedad en sustrato, un sensor de temperatura y humedad ambiental, y un detector de nivel en el depósito.»
  - ícono sparkle — «Asistente de IA generativa» + etiqueta «Previsto» (`.feature-planned`) — «La arquitectura prevista procesa las lecturas en Google Cloud y muestra los resultados en tu dashboard. Aún no está conectado y no controla el dispositivo.»
  - ícono shield — «Iluminación LED y control local» — «Fotoperiodos LED programados y operación local continua mediante ESP32 con acceso web protegido y comunicación cifrada.»
- **Móvil:** apilado.
- **Observaciones:** este es el único lugar que avisa que la IA «aún no está conectada»; el pie y el panel también lo mencionan («Asistente IA previsto»). Con sesión el enlace cambia a «Ir a mi panel».

#### Textos legales — `#terminos`, `#privacidad`, `#cookies`
- **Archivos:** V `LegalViews.render/fill` `publico.js:333-405`; C `enrutador.js:147-153`; M `PrivacyModel.documents` `modelos/comun.js:7-11`, `PrivacyData.document` `:39`; CSS `panel.css:270-290`; datos `frontend/legales/*.html`.
- **Acceso:** pública (V/U/A). El encabezado es el público (no cambia de navegación).
- **Propósito:** mostrar el texto vigente de cada documento legal.
- **Disposición (escritorio):**
```
┌ encabezado público ───────────────────────────────────────────┐
│ Documentos legales · El Chilito  (eyebrow)                     │
│ <Título>  (h1 grande)                                          │
│ <Entradilla>                                                   │
├────────────────────────────────────────────────────────────────┤
│ [ artículo de lectura a todo lo ancho (legal-prose) ]          │
│ Documentos relacionados: • otro doc • otro doc (• Configurar cookies)  │
└ pie de página ─────────────────────────────────────────────────┘
```
- **Elementos (literales):** eyebrow «Documentos legales · El Chilito»; `h1` y entradilla por documento:
  - `#terminos`: «Términos y condiciones» / «Condiciones de uso de la plataforma El Chilito y de sus servicios.»
  - `#privacidad`: «Aviso de privacidad» / «Qué datos personales tratamos, para qué los usamos y cómo puedes ejercer tus derechos.»
  - `#cookies`: «Política de cookies» / «Qué cookies usamos, para qué sirven y cómo cambiar tu elección.»
  - `<article class="legal-prose" aria-label="<título>">` con `<div data-legal-text role="status">`; mientras carga: «Cargando documento…».
  - `nav.legal-related` (`h2` «Documentos relacionados»): lista de los **otros dos** documentos; en `#cookies` se añade el botón «Configurar cookies» (`.legal-link`, abre preferencias).
- **Datos:** `GET /api/privacidad/documentos/<kind>` (con cabecera `X-Chilito-Sondeo`) → `{status:'ready', version, registered, text, html, draft}` (`privacidad/api.py:54-59`, `privacidad/services.py:42-58`). El backend lee **`frontend/legales/<archivo>.html`** en cada petición, lo sanea (solo `p,h2→h3,h3,strong,em,ul,ol,li,br,a` con enlaces `#`, `/`, `http(s)`, `mailto`) y lo compara con la huella de `privacidad_documentoversion`.
- **Estados:**
  - Cargando: «Cargando documento…».
  - Error: «No se pudo cargar el documento. Inténtalo de nuevo.»
  - **Hoy, los tres archivos `legales/*.html` solo contienen un comentario de instrucciones** (`aviso-privacidad.html`, `politica-cookies.html`, `terminos.html`, 7 líneas cada uno), por lo que el texto visible es: **«[PENDIENTE: documento en redacción]»** (clase `.legal-pending`). Si hubiera texto sin versión registrada: «[PENDIENTE: borrador en edición, sin versión registrada]».
  - Sin permiso: no aplica.
- **Actualización automática:** no (una lectura por visita).
- **Accesibilidad:** el contenedor pierde `role="status"` al cargar; `article` con `aria-label`.
- **Observaciones:** **los tres documentos legales están vacíos**; el registro exige aceptarlos (3.B) y apunta a ellos. «Aviso de privacidad» se cita como texto de derechos (la antigua pantalla `#derechos-arco` se retiró: `enrutador.js:18-19`). Registrar una versión (`privacidad_documentoversion`) no se hace desde la interfaz.

---

### 3.B Acceso (se conserva; fichas breves)

**Marco común** (`AuthViews.layout`, `vistas/cuenta.js:58-60`; CSS `acceso.css`, `base.css:1248-1255`): `div.auth-layout.auth-flow` con logotipo `.auth-brand` (arriba-izquierda sobre la foto, `→ #inicio`), columna izquierda `<aside class="auth-visual">` con foto `habanero-fondo.webp` (`alt="Hojas y frutos de habanero en una ambientación conceptual de interior."`) y cita «Tu huerto, / más cerca de ti.» + «Tres plantas de habanero para cultivar en interiores.» (en escritorio 46%; ≥1025px 42%; 901–1024px 40%), y columna derecha `<main id="contenido">` con tarjeta `.auth-bento` (máx. 480px): `h1#auth-title`, `p.auth-intro`, `#auth-content`. ≤900px una columna con la tarjeta limitada a 520px (la foto se reordena; altura exacta NO DETERMINABLE sin renderizar: `base.css:1310-1355`). La cita se anima letra por letra al **llegar** desde fuera del flujo de acceso (`enrutador.js:140`). Campos y mensajes: `AuthModel.validate` (`modelos/cuenta.js:58-87`). El formulario es `<form id="access-form" class="login-form" novalidate data-auth-screen="…">`; mensajes en `#auth-feedback` (`role="status"`, `aria-live="polite"`, `.is-error`), resumen oculto `#access-errors` (`role="alert"`) «Revisa los campos indicados para continuar.», espera `#auth-wait`. Mientras envía: campos `readOnly`, casillas `disabled`, botón `aria-busy` con spinner y texto «…» (`pendingLabels`: «Iniciando sesión…», «Enviando solicitud…», «Verificando…», «Guardando contraseña…», «Solicitando reenvío…»). Tiempo máximo de petición 20 s (`requestTimeoutMs`); se vacían los campos de contraseña tras cada envío (`clearPasswords`).

#### Inicia sesión — `#acceso`
- **Archivos:** V `cuenta.js:5-60`; C `controladores/cuenta.js:251-556`; M `AuthService.request('login')` `modelos/cuenta.js:180-190`.
- **Acceso:** visitante. Si ya hay sesión confirmada, `leaveAccessScreen` redirige al panel (`enrutador.js:53-59,141`).
- **Campos:** «Correo electrónico» (placeholder «tu@correo.com», `type=email`, `maxlength=254`, requerido, `autocomplete=email`); «Contraseña» (`autocomplete=current-password`, botón ojo `aria-label="Mostrar contraseña"`/`Ocultar …`). Validación cliente: «Escribe un correo válido, como nombre@dominio.com.», «Escribe tu contraseña.». No valida longitud (solo en pantallas de alta/cambio).
- **Botones:** «Iniciar sesión» (brand, ancho completo) → `POST /_allauth/browser/v1/auth/login {email,password}`; luego `GET …/auth/session` y `GET /api/cuenta`. Enlaces: «¿Olvidaste tu contraseña?» → `#recuperar`; «Crear cuenta» (en «¿Aún no tienes cuenta? Crear cuenta») → `#registro`.
- **Resultados:** `authenticated` → «Inicio de sesión confirmado.» y redirige (`#huerto` o panel admin); `second-step` → `#segundo-paso`; `verification-required` → `#verificar`; `invalid-credentials` → «El correo o la contraseña no son correctos. Revisa tus datos e inténtalo de nuevo.»; `limited` → «Has realizado demasiados intentos. Espera un momento antes de volver a intentarlo.» (botón deshabilitado, «Inténtalo de nuevo en m:ss.»); `csrf-failed` → «La sesión del formulario ha cambiado. Recarga la página e inténtalo de nuevo.»; `unavailable` → «El servicio no está disponible en este momento. Inténtalo de nuevo más tarde.»
- **Estados / auto-actualización:** contador de 1 s solo para esperas. Si llega con `context.feedback` (sesión vencida, etc.) lo muestra como error.
- **Observaciones:** no tiene «Recordarme». Para el administrador, tras el inicio el servidor puede exigir segundo paso.

#### Crea tu cuenta — `#registro`
- **Campos:** «Correo electrónico» (placeholder «tu@correo.com»); «Contraseña» (política **servidor**: mínimo 15, máximo 256 caracteres, `GET /api/acceso/configuracion → password.minLength/maxLength`; ayuda visual: medidor, contador «N caracteres», «Mínimo 15 caracteres», «Para que sea más segura»: «Mayúsculas y minúsculas», «Números», «Un símbolo, como ! # $ %», «No incluye tu correo»/«Incluye tu correo: elige otra»; nota «Son recomendaciones. Al guardar se rechazan contraseñas comunes, solo numéricas o parecidas a tu correo.»); «Confirmar contraseña» («Las contraseñas coinciden»); casilla «Acepto los Términos y condiciones de El Chilito» (etiqueta «Obligatorio», enlace «Leer Términos y condiciones» → `#terminos` en pestaña nueva) y casilla «He leído el Aviso de privacidad» («Obligatorio», enlace «Leer Aviso de privacidad» → `#privacidad` nueva pestaña).
- **Validación cliente:** mín./máx. (`Usa al menos N caracteres.`, `Usa como máximo N caracteres.`), «Confirma tu contraseña.», «Las contraseñas no coinciden.», «Debes aceptar los Términos y condiciones para continuar», «Debes confirmar que leíste el Aviso de privacidad para continuar». **Servidor** (`cuentas/api.py:162-182`): 403 `registration-disabled`; 400 `terms-required`/`privacy-required`; 503 `mail-unavailable`; validación de allauth (contraseña común/parecida/numérica).
- **Botón:** «Crear cuenta» → `POST …/auth/signup {email,password,termsAccepted:true,privacyRead:true}`. Si el servidor acepta, `GET /api/acceso/verificacion` y se va a `#verificar` con correo, caducidad y espera de reenvío (60 s).
- **Mensajes:** «El registro no está disponible en este momento.» (también si `registrationAllowed!==true`, sin llamar al servidor); campo correo: «Este correo no está autorizado para la prueba local. Revisa que coincida con la dirección que indicaste.» (`email-not-authorized`), «Revisa el correo y los datos del registro.»; «No fue posible completar el envío a este correo. Inténtalo más tarde o inicia sesión para solicitar otro código.»; rechazos de contraseña: «Esa contraseña es demasiado común. Prueba con una frase larga que solo tú recuerdes.», «Se parece demasiado a tu correo o a los datos de tu cuenta. Elige una distinta.», «No puede tener solo números. Añade palabras o letras.», «Es demasiado corta. Revisa el mínimo de caracteres.», «El servidor no aceptó esta contraseña. Elige otra distinta.»
- **Link:** «Iniciar sesión» → `#acceso`.
- **Observaciones:** el texto «prueba local» sale de entorno de pruebas y se muestra a quien se registre con un correo no autorizado (`registration.local_registration_allowed`).

#### Verifica tu correo — `#verificar`
- **Campos:** «Correo electrónico» (solo lectura); «Código de verificación» (`autocomplete=one-time-code`, `inputmode` del servidor = numérico, `maxlength=6`, estilo tabular con `letter-spacing:.16em`); ayuda «El código vence en m:ss.» y «Ingresa el código de verificación de 6 dígitos enviado a tu correo.». Cliente: «Escribe el código de verificación.», «El código debe tener 6 caracteres.», «Revisa el formato del código.».
- **Botones:** «Verificar correo» → `POST …/auth/email/verify {key}`; «Reenviar código» (claro, ancho completo; deshabilitado durante la espera de 60 s con «Podrás solicitar otro código en m:ss.») → `POST …/auth/email/verify/resend {}`; enlace «Iniciar sesión».
- **Resultados:** verificado → «Correo verificado» / «Tu correo está verificado. Puedes continuar a tu cuenta.» + botón «Mi huerto» (`#huerto`); si no hay sesión confirmada: «La verificación de tu correo se completó.» + «Iniciar sesión»; incorrecto → campo «El código no es correcto. Revísalo e inténtalo de nuevo.» + «No pudimos verificar ese código.»; vencido → «El código ha vencido. Solicita uno nuevo.» + «Solicita un código nuevo para continuar.»; reenvío → «Si la solicitud puede completarse, recibirás un nuevo código por correo.»; contexto perdido → «Vuelve a iniciar sesión» / «La verificación ha vencido o ya no está disponible. Inicia sesión para solicitar un nuevo código.»
- **Datos:** `GET /api/acceso/verificacion → {status,email,expiresAt}` (`cuentas/api.py:185-196`, `ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT=600`, 3 intentos, hasta 5 reenvíos).
- **Auto-actualización:** contador cada 1 s; al vencer, el botón principal se deshabilita.
- **Observaciones:** la longitud «6 dígitos» del texto de ayuda está escrita a mano, no sale de la configuración.

#### Recupera el acceso — `#recuperar`
- Campo «Correo electrónico». Botón «Enviar enlace de recuperación» → `POST …/auth/password/request {email}`. Resultado (siempre igual): «Revisa tu correo» / «Si existe una cuenta asociada a ese correo, recibirás instrucciones para recuperar el acceso.» + «Iniciar sesión». Introducción: «Ingresa tu correo electrónico para enviarte las instrucciones de recuperación.» (el texto de `titles.recuperar[1]` «Te enviaremos un enlace para elegir una contraseña nueva.» no se muestra). Backend: 503 `mail-unavailable` si no hay envío configurado (`cuentas/api.py:143`).

#### Elige una contraseña nueva — `#restablecer`
- El enlace del correo trae el secreto en el hash (`#restablecer?key=…`); `consumeResetLink` lo retira de la URL y lo guarda en memoria (`modelos/cuenta.js:26-33`). Primero `GET …/auth/password/reset` con cabecera `X-Password-Reset-Key` («Comprobando el enlace…»). Inválido → «Este enlace ya no está disponible» + «El enlace no es válido o ha vencido. Solicita uno nuevo para recuperar el acceso.» + botón «Solicitar otro enlace» (`#recuperar`). Servidor caído → «No podemos comprobar el enlace en este momento. Inténtalo de nuevo.» + «Reintentar» + enlace «Solicitar otro enlace». Válido → campos «Nueva contraseña» y «Confirmar contraseña» (misma ayuda que registro); botón «Guardar contraseña» → `POST …/auth/password/reset {key,password}`; éxito «Contraseña actualizada» / «Ya puedes iniciar sesión con tu nueva contraseña.» + «Iniciar sesión».

#### Confirma tu acceso — `#segundo-paso`
- Pantalla: `AuthViews.layout('Confirma tu acceso','Falta un paso para entrar.')`. Primero «Comprobando…» (`GET …/auth/session`). Si no hay paso pendiente → vuelve a `#acceso`.
- Según el factor pendiente (`login_by_code` o `mfa_authenticate`): etiqueta y ayuda distintas: «Código de 6 dígitos» + «Te lo enviamos por correo. Vence en 5 minutos.» (numérico, `maxlength=6`) **o** «Código de tu app o de recuperación» + «Si perdiste tu app, usa uno de tus códigos de recuperación.» + enlace «No tengo mi app ni mis códigos» → `#sin-acceso` (`maxlength=64`).
- Botones: «Continuar» (brand; «Comprobando…») → `POST …/auth/code/confirm {code}` o `POST …/auth/2fa/authenticate {code}`; «Cancelar» (claro) → cierra sesión (`DELETE …/auth/session`) y `#acceso`; «Usar llave de acceso» (claro, oculto salvo que el flujo admita `webauthn` y el navegador soporte `PublicKeyCredential.parseCreationOptionsFromJSON`) → `GET/POST …/auth/webauthn/authenticate`.
- Errores: «El código no es válido.», «Demasiados intentos. Espera un momento.», «El proceso venció. Inicia sesión de nuevo.» (+ vuelve a `#acceso`), «No se pudo comprobar. Inténtalo de nuevo.»
- Al terminar: `restore` y redirige a `#huerto`, o a `#<primer destino admin>`, o a `#cuenta/seguridad` si el admin aún no tiene método fuerte.

#### Sin acceso a tu segundo paso — `#sin-acceso`
- Título «Sin acceso a tu segundo paso»; intro «Si no tienes tu app, tus llaves ni tus códigos, el equipo puede ayudarte. Cambiar la contraseña no quita este paso.»; lista ordenada de 4 pasos («Escribe a soporte desde el correo de tu cuenta. Así podemos saber que el mensaje viene de ti.», «Dinos qué perdiste y la fecha aproximada en que te registraste. Nunca envíes tu contraseña ni códigos.», «Comprobaremos tu identidad. Si coincide, retiraremos los métodos de tu cuenta y te avisaremos.», «Entra con tu correo y tu contraseña: recibirás un código por correo. Después vuelve a activar tu método en Seguridad.»); contacto «Escribir a soporte: <correo>» (enlace `mailto:` con asunto «Recuperar acceso a El Chilito» y cuerpo prellenado) o «Contacto: <texto>» si no es un correo; solo si hay `CHILITO_CONTACTO_SOPORTE`. Botón «Volver al inicio de sesión» (`#segundo-paso`).
- **Observación:** no hace ninguna llamada al backend salvo la configuración inicial.

#### Bienvenida (diálogo) — se abre sobre cualquier pantalla privada
- **Archivos:** V `ProfileViews.welcome` `cuenta.js:347-351`; C `WelcomeController` `controladores/cuenta.js:179-199`.
- **Cuándo:** primera vez que la cuenta entra al panel (`profile.welcomePending===true`, `bienvenida_atendida_en` nulo).
- **Contenido:** `<dialog class="bento-panel app-dialog">` «Te damos la bienvenida» / «¿Cómo quieres que te llamemos? Usaremos tu alias para dirigirnos a ti. Todos los datos son opcionales.»; campos «Nombre» (`maxlength=150`), «Apellido» (150), «Alias» (64; ayuda «Lo usaremos para dirigirnos a ti.»); botones «Ahora no» (claro; envía `{}`) y «Guardar» (brand). Error: «No se pudo guardar. Inténtalo de nuevo.»
- **Backend:** `POST /api/cuenta/bienvenida {firstName,lastName,alias}` (`privacidad/api.py:43-46`); «Ahora no» también cierra el paso (no es un consentimiento).
- **Tras guardar:** se cierra, `restore` y se repinta el saludo (`personalize`).

---

### 3.C Persona usuaria

**Marco común de todas las pantallas privadas** (2.3): `#app-page` dentro de `main.dashboard.container` (`width:calc(100% - 72px)`, `max-width:1232px`, `padding-top:76px` por la barra flotante). Cada pantalla empieza con `div.page-heading > h1` (+ `p` de introducción). Las pantallas de huerto (`#huerto`, `#telemetria`, `#mantenimiento`, `#soporte`) las monta `UserGardenController` (`controladores/huerto.js:5-125`) y comparten **una sola carga** `UserGardenService.load` (`modelos/huerto.js:112-132`):

| Llamada | Endpoint | Uso |
|---|---|---|
| 1 | `GET /api/huertos/actual` → `{status:'ready', garden:{status,name,updatedAt,plants[3],temperature,humidity,tank}, diagnosis}` | Huerto y resumen |
| 2 (paralelo) | `GET /api/huertos/actual/mantenimiento?page=n` → `{items:[{id,type,task,at,actor}],page,total}` | Historial |
| 3 | `GET /api/huertos/actual/solicitudes?page=n` → `{items:[{id,type,status,at}]}` | Bitácora de actuadores |
| 4 | `GET /api/soporte?page=n` → `{items:[caso]}` | Autorización de soporte e historial |

Las páginas se piden en bucle hasta 100 (25 por página, `datos/paginacion.py:6`). Si la llamada 1 devuelve 403 `garden-unassigned` → estado «sin huerto asignado» (estructura vacía, controles bloqueados). Cualquier otro fallo → estado `error`. Tiempo máximo de carga 20 s (`LOAD_TIMEOUT_MS`). Sin refresco automático salvo lo indicado.

**Estados comunes** (`AppModel.states`, `modelos/comun.js:81-90`): `loading` «Consultando el huerto» / «Espera un momento.»; `waiting` «Huerto vinculado · Sin lecturas recibidas» / «Las mediciones aparecerán cuando el equipo empiece a enviarlas.»; `ready` «Datos disponibles»; `stale` «Datos desactualizados»; `offline` «Dispositivo sin conexión»; `error` «No se pudo consultar el huerto» / «Inténtalo de nuevo para consultar su estado.»; `invalid` «Hay una lectura inválida»; `unassigned` «Sin huerto asignado» / «Tu cuenta todavía no tiene un huerto asignado.». **El backend solo devuelve `waiting`** (`datos/services.py:376-384`): `ready/stale/offline/invalid` no se producen hoy.

**Error de carga (común)** (`UserGardenViews.failed`, `huerto.js:48`): tarjeta `role="alert"` `h2` «No se pudo consultar el huerto» + «Inténtalo de nuevo para consultar sus lecturas y acciones.» + botón «Reintentar» (brand → `data-user-action="refresh"`).

**Diálogo estándar de huerto** `<dialog class="bento-panel app-dialog user-dialog">`: foco inicial en «Cancelar»; Escape cierra si no hay operación en curso (`controladores/huerto.js:30`); durante la operación todos los botones quedan `disabled`.

**Mensajes de retorno** `#user-feedback` (`role="status"` o `alert`, toma foco) — ver cada ficha.

#### Mi huerto — `#huerto`
- **Archivos:** V `UserGardenViews.summary` `vistas/huerto.js:82-100`, `metricCards 64-74`, `plantCards 75-81`, `GardenDiagnosisViews 6-29`; C `controladores/huerto.js:5-125`; M `modelos/huerto.js:7-166`, `AppModel` `comun.js:81-146`; CSS `panel.css:290-500`, `apariencia.css:363-395`.
- **Acceso:** usuaria (rol `user`). Admin → redirige a su panel. Sin sesión → `#acceso`. Sin huerto → versión bloqueada con «Vincular mi huerto» (ver ficha final de 3.C).
- **Propósito:** resumen del huerto: estado, depósito, humedad, ambiente, tres plantas, resumen por reglas y cuidados rápidos.
- **Disposición (escritorio):**
```
 Hola, <alias>                       ← h1 (garden-welcome)
 Te damos la bienvenida a tu huerto. ← lead
 <frase aleatoria de la visita>
 Huerto vinculado · Sin lecturas recibidas        Última lectura: Sin registros
 ┌Depósito┐┌Humedad ┐┌Ambiente┐┌Circuito y actuadores┐   ← 4 métricas (4 columnas ≥1100px)
 Tus tres plantas              Humedad del sustrato por planta
 ┌Planta 1┐ ┌Planta 2┐ ┌Planta 3┐                        ← 3 tarjetas
 ┌ Resumen de tu huerto ───────────────────────────────┐
 Acciones a tu alcance
 ┌Rellenar depósito┐┌Revisar sustrato┐┌Germinación y cosecha┐
 ┌ Control de lámpara ────────────────[Apagar lámpara]─┐
 El control remoto depende de Wi-Fi y MQTT. …
 ┌ ¿Algo no responde como debería? ──[Solicitar soporte técnico]┐
```
- **Disposición (móvil):** métricas y plantas a 1 columna (≤700px); la métrica pasa a fila `ícono | título | valor`; botones de tarjeta al ancho de la tarjeta.
- **Elementos en orden:**
  1. **Saludo** (`h1`): `Hola, <nombre>` si hay alias/nombre (`nombre_presentacion`: alias → nombre → «Bienvenido»); si no hay nombre: «Te damos la bienvenida a tu huerto»; con nombre se añade lead «Te damos la bienvenida a tu huerto.»; y una **frase aleatoria** (una por visita; no viene del servidor): «Cada pequeño cuidado cuenta.», «Cultivar es aprender un poco cada día.», «Lo bueno de un huerto es que se cuida poco a poco.», «Aquí tienes lo de tu huerto en un mismo lugar.», «Un rato con tus plantas también es tiempo bien empleado.» (`modelos/comun.js:78-80`).
  2. **Línea de estado** `.user-status-line`: «Huerto vinculado · Sin lecturas recibidas» y «Última lectura: Sin registros». Si estado `offline/stale/invalid`, aviso adicional `role="status"` (no ocurre hoy).
  3. **4 tarjetas de métrica** `.bento-panel.user-metric` (ícono + `h2` + valor `strong` + nota): «Depósito de agua» → «Nivel bajo» / «Nivel adecuado» / «Sin lectura» (de `garden.tank.state`: `low|not-low|unknown`) con nota «Capacidad del depósito: 19 L» (**texto fijo**); «Humedad del sustrato» → `—` y «Aún no hay lecturas disponibles.» (el dato `soil.moisture` **siempre vacío** en el modelo); «Ambiente» → temperatura `—°C` y «Humedad relativa: —» (`garden.temperature/humidity`); «Circuito y actuadores» → «Sin información» / «Sin conexión» / «En línea» / «Apagado solicitado» / «Control solicitado» (según `connection.wifi/mqtt`, siempre `null` → «Sin información») con nota «Bombas y lámpara» o «Esperando confirmación del equipo.».
  4. **«Tus tres plantas»** (`h2#plants-title`) + «Humedad del sustrato por planta»: tres `article.plant-card`: nombre (`zona.nombre`, o «Planta N»), cultivo (`zona.cultivo`, o «Cultivo sin registrar»), dibujo SVG de planta sobre un pedestal, «Humedad del sustrato», valor grande (`—` si no hay lectura), barra `.sensor-track` (único `style` en línea: ancho %). Con lectura válida/ inválida aparece insignia «Lectura registrada» / «Lectura inválida» y la nota «Última lectura: <fecha>» o «Lectura inválida. Revisa este sensor.».
  5. **Tarjeta «Resumen de tu huerto»** (`#diagnosis-title`, ícono sparkle): `h3` «Sin diagnóstico disponible» + «Las recomendaciones aparecerán aquí cuando estén disponibles las lecturas de tu huerto.» por defecto. Con datos reales (hoy el backend manda `diagnosis:null`) mostraría título/mensaje de reglas, «Próxima acción estimada», «Lecturas del <fecha>» / «Lecturas antiguas, la última es del …: pueden no describir el estado actual.» / «Sin lecturas disponibles: no se puede valorar el estado de las plantas.», origen «Resumen por reglas · <fecha>» y, si existe, la explicación de IA («Explicación generada con IA · <fecha> · Complementa el resumen, no lo sustituye.», o «La explicación adicional caducó y ya no se muestra.», o «Explicación adicional no disponible.»); caduca con temporizador.
  6. **«Acciones a tu alcance»** + «Registra los cuidados que realizas en tu huerto.»: 3 tarjetas `.user-care` — «Rellenar depósito» («Añade agua limpia cuando el nivel sea bajo y registra la recarga al terminar.», botón «Registrar recarga»); «Revisar sustrato» («Comprueba el drenaje y el estado de la mezcla con perlita.», enlace «Ver guía de cuidado» → `#mantenimiento/sustrato`); «Germinación y cosecha» («Germina fuera del sistema y cosecha los frutos maduros con utensilios limpios.», botón «Registrar cosecha»).
  7. **Tarjeta «Control de lámpara»**: texto «Solicita el apagado de la lámpara cuando necesites intervenir en el huerto.» (o «Hay una solicitud de apagado. Puedes restablecer el control habitual de la lámpara.») + botón «Apagar lámpara» / «Restaurar control».
  8. Aviso fijo `.user-safety-copy`: «El control remoto depende de Wi-Fi y MQTT. Ante una emergencia, utiliza el paro físico del equipo.»
  9. **Llamada** «¿Algo no responde como debería?» / «Reporta un problema y autoriza el diagnóstico técnico de tu huerto.» + botón «Solicitar soporte técnico» (brand, `#soporte`).
- **Botones y acciones:**

| Texto | Posición | Variante | Acción | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|---|---|---|
| «Registrar recarga» | Tarjeta «Rellenar depósito» | claro | `recordTask('refill')` y recarga | `POST /api/huertos/actual/mantenimiento {type:'refill'}` | no | «Recarga del depósito registrada.» | «No se pudo registrar la tarea.» |
| «Registrar cosecha» | Tarjeta «Germinación y cosecha» | claro | `recordTask('harvest')` | ídem `{type:'harvest'}` | no | «Cosecha registrada.» | idem |
| «Ver guía de cuidado» | Tarjeta «Revisar sustrato» | claro (enlace) | navega | — | no | — | — |
| «Apagar lámpara» / «Restaurar control» | Tarjeta de lámpara | claro | abre diálogo | — | **sí**: «¿Solicitar el apagado de la lámpara?» / «¿Restaurar el control habitual de la lámpara?» con «Se registrará una solicitud para tu huerto. La ejecución depende del servicio del equipo. El estado permanecerá sin confirmar hasta recibir la respuesta del equipo.» Botones «Cancelar» / «Solicitar apagado» (o «Restaurar control») | «Solicitud registrada. Esperando confirmación del dispositivo.» | «No se pudo completar la solicitud. Inténtalo de nuevo.» (también textos para `offline` «No se envió la solicitud. Revisa la conexión Wi-Fi y MQTT del huerto.» y `low-water` «No se solicitó el riego. Revisa el nivel del depósito antes de continuar.» — **el backend nunca devuelve esos estados**) |
| «Solicitar soporte técnico» | Franja final | brand | navega | — | no | — | — |
| «Reintentar» | Tarjeta de error | brand | recarga | los 4 GET | no | — | — |

   Endpoint de la solicitud de lámpara: `POST /api/huertos/actual/solicitudes {type:'lamp-off'|'lamp-auto'}`.
- **Formularios:** ninguno (el diálogo no tiene campos).
- **Estados:** *cargando* = esqueleto (`.skeleton-line`, `aria-hidden`) + «Cargando la información de tu huerto.» (sr-only); *error* = tarjeta de error; *sin huerto* = «Vincular mi huerto» + resto en `<fieldset disabled>` con leyenda sr-only «Acciones no disponibles: tu cuenta no tiene un huerto asignado»; *sin datos de sensores* = guiones y «Aún no hay lecturas disponibles.» (**estado permanente hoy**); *sin permiso* = 401 → sesión vencida (`#acceso`); 403 distinto → error genérico.
- **Actualización automática:** no (solo al montar, al registrar una acción o al pulsar «Reintentar»/«Actualizar»). Temporizador de 1 s activo solo en `#soporte`; temporizador de caducidad de la explicación de IA.
- **Accesibilidad:** `h1` único; tarjetas con `h2/h3`; los mensajes `#user-feedback` reciben foco; el diálogo devuelve el foco al botón de origen; barra de humedad `aria-hidden`.
- **Observaciones:** ninguna lectura de sensores llega (todo `missing`); «Capacidad del depósito: 19 L», «Sensor capacitivo v1.2», «SHT31» son textos fijos; el estado «ready» nunca se alcanza; `canControl` está fijo en `true`, así que el texto «Control remoto no disponible. Esperando conexión del equipo.» (`huerto.js:98`) **no puede mostrarse**; los botones de lámpara y riego registran una solicitud pero nada la confirma («Sin confirmación» eterno).

#### Panel técnico — `#telemetria`
- **Archivos:** V `UserGardenViews.technical` `huerto.js:112-130`, `chart 102-111`, `commandLog 131-134`; C mismo `UserGardenController`; CSS `panel.css:300-480`.
- **Acceso:** usuaria. Sin huerto: la línea de estado se sustituye por «Vincular mi huerto» y el resto queda bloqueado.
- **Propósito:** lecturas técnicas, histórico, conectividad, bitácora de actuadores y riego puntual.
- **Disposición (escritorio):** cabecera «Panel técnico» + «Lecturas, conectividad e historial de tu huerto.» (con saludo si hay alias: `AppModel.addressed`); línea de estado; fila de 3 métricas; barra «Histórico de lecturas» con selector de periodo; rejilla de 3 gráficas + tarjeta de conectividad; «Lecturas por planta» (3 columnas); «Bitácora de actuadores» (tabla) + botón; tarjeta «Solicitar riego puntual».
- **Elementos:**
  - Métricas: «Sensor capacitivo v1.2» → `— ADC` / «Lectura analógica bruta · escala 0–4095»; «Humedad calibrada» → `—` / «Humedad del sustrato»; «Ambiente · SHT31» → `—°C` / «Humedad relativa: —».
  - `h2` «Histórico de lecturas» + grupo `role="group" aria-label="Periodo del histórico"` con botones «1 h», «24 h», «7 días» (`aria-pressed`, el activo `brand`).
  - Gráficas (`user-chart`): «Humedad del sustrato · ADC», «Temperatura ambiental», «Humedad relativa». Sin datos (siempre hoy): encabezado `—`, marco con ejes `—` y etiquetas «Hace 1 h / Hace 30 min / Ahora» (o 24 h: «Hace 24 h / Hace 12 h / Ahora»; 7 d: «Hace 7 días / Hace 3 días / Ahora») y nota «Aún no hay registros para este periodo.». Con datos: polilínea, último punto y `<desc>` accesible.
  - Tarjeta «Depósito y conectividad»: «Flotador» (Nivel bajo/adecuado/Sin lectura), «Capacidad del depósito» «19 L», «Wi-Fi» («Conectado»/«Sin conexión»/«Sin información»), «Mosquitto / MQTT» («Disponible»/«No disponible»/«Sin información») + «El flotador detecta nivel bajo; no mide el volumen de agua.».
  - «Lecturas por planta» + «Humedad del sustrato en cada uno de los tres compartimentos.»: por planta nombre, valor, fecha o «Sin lecturas».
  - «Bitácora de actuadores» + «Órdenes, resultados y origen de cada acción.» y botón «Actualizar bitácora»; tabla (`role="region" aria-label="Historial de órdenes"`, `tabindex=0`): columnas «Fecha y hora», «Actuador», «Orden / resultado», «Origen», «Estado»; filas con «Bomba de riego»/«Lámpara», «Solicitud de riego puntual»/«Solicitud de apagado de lámpara»/«Restaurar control de lámpara», origen «Usuario», estado «Sin confirmación». Vacío: «No hay órdenes registradas.» + «Las solicitudes y la respuesta del equipo aparecerán aquí.».
  - Tarjeta «Solicitar riego puntual»: «Registra la solicitud y consulta su estado en la bitácora. El equipo debe confirmar la operación antes de considerarla realizada.» + botón «Solicitar riego» (brand) y aviso «Una solicitud no confirma que la bomba se haya activado. Ante una emergencia, utiliza el paro físico del equipo.»
- **Botones:**

| Texto | Acción | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|---|
| «1 h» / «24 h» / «7 días» | Cambia `range` y recarga (foco se conserva) | los mismos GET (el servidor **ignora** el rango) | no | — | error genérico de carga |
| «Actualizar bitácora» | Recarga todo | los 4 GET | no | «Información actualizada.» | tarjeta de error |
| «Solicitar riego» | Abre diálogo «¿Solicitar riego puntual?» (mismo texto de confirmación) → «Cancelar» / «Solicitar riego» | `POST /api/huertos/actual/solicitudes {type:'water'}` | **sí** | «Solicitud registrada. Esperando confirmación del dispositivo.» | «No se pudo completar la solicitud. Inténtalo de nuevo.» |

   «Solicitar riego» queda `disabled` si el estado es `error/unassigned/loading`.
- **Estados:** como Mi huerto; *sin datos de sensores* permanente: ADC `—`, gráficas vacías, Wi-Fi/MQTT «Sin información».
- **Actualización automática:** no.
- **Accesibilidad:** gráficas con `role="img"` y `<title>/<desc>` (solo con datos); vacías `aria-hidden`; tabla con `th scope=col`; rango con `aria-pressed`.
- **Observaciones:** pantalla **sin datos reales**: `soil.adc`, `connection.*` e `history.*` se fijan a nulo/vacío en el modelo (`modelos/huerto.js:106,131`); el selector de periodo no cambia nada porque el servidor no entrega histórico. Los modelos de sensor («capacitivo v1.2», «SHT31») están en el texto.

#### Mantenimiento — `#mantenimiento` (y guías de cuidado)
- **Archivos:** V `UserGardenViews.maintenance` `huerto.js:135-148`, `CareGuideViews` `205-271`; C `UserGardenController` + `CareGuideUserController` `controladores/huerto.js:129-185`; M `CareGuideService.published` `modelos/huerto.js:225-229`; CSS `panel.css`, `apariencia.css:780-817`.
- **Acceso:** usuaria. Sin huerto: la tarjeta «Vincular mi huerto» aparece **y las guías siguen disponibles** (quedan fuera del bloque deshabilitado).
- **Subrutas:** `#mantenimiento/sustrato` abre la ficha `sustrato-perlita`; `#mantenimiento/germinacion` abre `germinacion-inicio`; `#mantenimiento/guias` enfoca la sección; `#mantenimiento/historial` desplaza y enfoca el historial. Si la ficha no está publicada: aviso `role="status"` «Esa ficha ya no está publicada. Aquí tienes las guías disponibles.» (los enlaces `data-care-guide-link` se abren **sin navegar** porque ya está en la pantalla).
- **Disposición:** cabecera «Mantenimiento del huerto» + «Registra los cuidados que realizas y consulta tu historial.» → rejilla de 6 tarjetas → «Historial de mantenimiento» → sección de guías.
- **Elementos:**
  - Tarjetas `.user-care` (ícono en medallón + `h3` + `p` + acción): «Nivel de agua» («Estado del depósito: nivel adecuado/nivel bajo/sin lectura. Rellena con agua limpia y registra la recarga al terminar.», botón brand «Ya rellené el depósito»); «Sustrato y perlita» («Comprueba el drenaje y evita que la mezcla quede compactada.», enlace «Ver guía de cuidado» + botón «Marcar revisión hecha»); «Germinación externa» («Germina las semillas fuera del sistema. Trasplanta cuando las plántulas sean resistentes.», enlace «Ver guía de germinación» + botón «Registrar germinación»); «Cosecha» («Usa guantes, revisa el grado de madurez y evita tocar ojos o piel sensible después de manipular los frutos.», botón «Registrar cosecha»); «Inspección visual» («Verifica que cables y conexiones estén secos, que el depósito no tenga fugas y que la lámpara esté estable.», botón «Registrar inspección»); «Registro reciente» («<tarea> · <fecha>» o «Aún no has registrado tareas de mantenimiento.», enlace «Ver historial» → `#mantenimiento/historial`).
  - «Historial de mantenimiento»: lista `ol.user-history-list` (ícono check, `h3` tarea, fecha) o «No hay tareas registradas. Al completar un cuidado, regístralo para conservar su fecha.».
  - Guías: `h2#care-guides-title` «Guía de cuidado y preguntas frecuentes» + «Consulta cada etapa: germinación, trasplante, crecimiento y cosecha.»; `details.bento-panel.care-guide` por ficha (`summary` = pregunta; respuesta en párrafos separados por línea en blanco; «Fuente: <nombre>» con enlace `http(s)` en pestaña nueva y texto sr-only «(se abre en otra pestaña)»).
- **Botones:** `record-refill`/`record-substrate`/`record-germination`/`record-harvest`/`record-inspection` → `POST /api/huertos/actual/mantenimiento {type:'refill'|'substrate'|'germination'|'harvest'|'inspection'}`; éxito «<etiqueta> registrada.» (etiquetas: «Recarga del depósito», «Revisión de sustrato y perlita», «Germinación externa», «Cosecha», «Inspección visual de conexiones»); error «No se pudo registrar la tarea.». No piden confirmación.
- **Datos:** historial de `GET /api/huertos/actual/mantenimiento`; guías de `GET /api/guias → {status:'ready',guides:[{key,question,answer,source:{name,url}|null}]}` (solo `publicada`, ordenadas por `orden`, `datos/guias.py:106-108`).
- **Estados de guías:** cargando «Consultando las guías…» (`aria-busy`); error `role="alert"` «No se pudieron consultar las guías. El resto de la página sigue disponible.» + «Reintentar»; vacío «Todavía no hay guías publicadas.»; las fichas abiertas se recuerdan en memoria mientras la pantalla sigue montada.
- **Actualización automática:** no.
- **Observaciones:** los 5 tipos de tarea son los de `datos_mantenimiento.tipo` (`refill, substrate, germination, harvest, inspection`). Los avisos de «Registrar…» no distinguen quién (no hay nombre) y se guardan con el actor autenticado.

#### Soporte técnico — `#soporte`
- **Archivos:** V `UserGardenViews.support` `huerto.js:149-162`, `confirmation 163-167`; C `controladores/huerto.js:56-117`; M `UserGardenService.issuePermission/revokePermission/supportMail` `modelos/huerto.js:142-163`; CSS `panel.css`.
- **Acceso:** usuaria; sin huerto → «Vincular mi huerto» y formulario bloqueado.
- **Propósito:** reportar un incidente de hardware y emitir un **token temporal** (24 h) que la persona comparte con soporte; revocarlo.
- **Disposición (escritorio):** cabecera «Soporte técnico» + «Reporta un problema y controla el acceso técnico a tu huerto.»; rejilla de 2 columnas `.user-support-layout`: izquierda tarjeta «Reportar un incidente» (y debajo la tarjeta del token si existe), derecha tarjeta «Estado de la autorización»; debajo «Historial de reportes».
- **Elementos:**
  - **«Reportar un incidente»** / «Selecciona el problema que presenta tu huerto.»; `select#user-incident` etiqueta «Tipo de problema» con las 5 opciones: «La bomba no responde», «Lectura de humedad inconsistente», «La lámpara no enciende», «Conexión inestable», «Otro problema de hardware» (valores `pump, humidity, lamp, connection, other`); texto «La autorización permite al equipo de soporte abrir una sesión de diagnóstico de este caso durante un máximo de 24 horas, sin renovarse al usarla. El diagnóstico remoto del equipo todavía no está conectado: hoy sirve para revisar tu caso con tu permiso.»; botón «Reportar y generar token temporal» (brand; `disabled` si `supportAvailable` fuera falso; mensaje «Emisión de tokens no disponible.» — hoy `supportAvailable` es siempre `true`).
  - **«Tu token de soporte»** (solo con autorización activa): `p.user-token-code` con el token (solo si se acaba de emitir en esta visita) o «El token solo se mostró al emitir esta autorización. No se recupera desde el historial. Si no lo conservas, revoca y genera una autorización nueva.»; `dl`: «Folio» (formato `CS-XXXXXXXX`), «Incidente», «Vence»; botones «Copiar token» (brand, solo si hay token) y «Escribir a soporte» (enlace `mailto:` con asunto «[El Chilito] Caso de soporte <folio>», solo si hay contacto configurado); pasos: «Copia el token.» / «Escribe a <correo|soporte> con el folio en el asunto.» / «Pega el token en el mensaje. Nunca envíes tu contraseña ni tus códigos.»; nota «El token solo se muestra al emitirlo y no se puede recuperar. Si lo pierdes, revoca esta autorización y genera una nueva.».
  - **«Estado de la autorización»** (ícono shield): `h3` «Autorización activa» / «Autorización revocada» / «Autorización vencida» / «Sin autorización activa»; texto «La autorización está vigente para este reporte. Puedes revocarlo cuando quieras.» o «El acceso técnico permanece cerrado hasta que lo autorices expresamente.»; `dl`: «Duración del permiso» «24 horas», «Alcance» «Diagnóstico del incidente», «Datos personales y ubicación» «Fuera del alcance»; botón «Revocar autorización» (peligro, `disabled` sin autorización activa).
  - **«Historial de reportes»**: lista con ícono `support`, título del incidente, «Folio X · Caso resuelto|Caso abierto», «<fecha> · Autorización activa|revocada|vencida|Sin autorización», y si aplica «Soporte pidió tu token el <fecha>.»; vacío «No hay reportes registrados.».
- **Diálogo «Autorizar soporte técnico»** (se abre al enviar el formulario): texto con las 24 h y la nota de diagnóstico remoto no conectado, «Puedes revocarla antes de su vencimiento.»; casilla `#user-support-consent` «Autorizo expresamente el diagnóstico remoto de este incidente con el alcance indicado.»; botones «Cancelar» y «Confirmar y generar token» (**deshabilitado hasta marcar la casilla**).
- **Botones y acciones:**

| Texto | Acción | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|---|
| «Reportar y generar token temporal» | valida (`reportValidity`) y abre el diálogo | — | sí (diálogo con casilla) | — | «La emisión de tokens de soporte no está disponible en este momento.» |
| «Confirmar y generar token» | emite | `POST /api/soporte {incident, consent:true}` → `{permission:{token,ticket,folio,supportEmail,device,user,createdAt,expiresAt}}` (reemplaza la autorización anterior de la misma persona) | la propia casilla | «Tu token de soporte está disponible. Puedes copiarlo o revocar la autorización.» (o «La autorización está registrada. El token solo se entrega una vez; si no lo conservas, revoca y genera otra autorización.») | «No se pudo completar la solicitud. Inténtalo de nuevo.» |
| «Copiar token» | `navigator.clipboard.writeText` | — | no | «Token copiado. Compártelo únicamente con el personal de soporte.» | «No se pudo copiar automáticamente. Selecciona y copia el código que aparece en pantalla.» |
| «Revocar autorización» | revoca | `POST /api/soporte/<id>/revocar` | **no** (sin diálogo) | «Autorización revocada. El acceso técnico permanece cerrado.» | «No se pudo confirmar la revocación. Inténtalo de nuevo.» |

- **Actualización automática:** cada 1 s (y al volver a la pestaña) se comprueba si venció la autorización; al vencer recarga con «La autorización ha vencido. El acceso técnico permanece cerrado.».
- **Estados:** cargando, error, sin huerto, vacío (sin reportes), sin permiso (401).
- **Accesibilidad:** diálogo con `aria-labelledby/describedby`; consentimiento con casilla real; token en `<p>` seleccionable.
- **Observaciones:** el token **solo existe en memoria de esa visita**; al recargar se pierde (`active.token` solo se conserva si el mismo ticket sigue). La «sesión de diagnóstico remoto» no está conectada a ningún dispositivo (lo dice el propio texto). El backend envía además `supportEmail`, que el frontend ignora (usa `GET /api/acceso/configuracion → supportContact`).

#### Avisos (lista) — `#avisos`
- **Archivos:** V `AppViews.notices/noticeCard` `vistas/comun.js:58-79`; C `AppController.load` `controladores/administracion.js:288-299`; M `AppService.request('notices')` `modelos/comun.js:159-201`, `AppModel.notices/notice` `:129-146`; CSS `panel.css:78-105`.
- **Acceso:** usuaria (en el menú es la campana de la barra flotante). Admin → redirige. Sin huerto → «Sin huerto asignado» **sin** formulario de vinculación.
- **Disposición (escritorio):** cabecera «Avisos» + «Revisa lo que necesita atención en tu huerto.»; fila de filtros; `.notices-grid` con tarjetas (1 columna ≤1024px).
- **Elementos:** filtros `role="group" aria-label="Filtrar avisos"`: «Todos» / «Activos» / «Resueltos» (`aria-pressed`, activo = brand); línea sr-only `role="status"`: «N avisos en este filtro.»; cada `article.notice-card`: `Activo|Resuelto` (`.notice-condition`), `Leído|No leído`, `h2` título, descripción, `dl` «Zona» / «Importancia» (`Alta`, `Media`, `Informativa`) / «Fecha», enlace «Ver detalle» (sr-only «: <título>») → `#avisos/<id>`.
- **Estados:** cargando «Cargando avisos» / «Consultando los avisos del huerto.»; error `role="alert"` «No se pudieron consultar los avisos» / «Inténtalo de nuevo para revisar los avisos.» + «Reintentar»; vacío «No hay avisos para mostrar» (o «No hay avisos en este filtro») + «Los avisos de cultivo y comunicación aparecerán aquí cuando estén disponibles.»; sin huerto «Sin huerto asignado» / «Tu cuenta todavía no tiene un huerto asignado.».
- **Datos:** `GET /api/huertos/actual/avisos?page=n → {status:'ready', items:[{id,title,description,recommendation,zone,createdAt,resolvedAt,importance:'high|medium|info',condition:'active|resolved',read}], page, total}` (25 por página, el frontend las reúne todas hasta 100 páginas). `importance` viene de `severidad` (`critico→high`, `advertencia→medium`, `informacion→info`); `zone` = nombre de zona o «Huerto».
- **Actualización automática:** no. Filtrar es local (sin llamada).
- **Observaciones:** el modelo `huerto_aviso` es «solo avisos registrados; sin generador automático» (`huerto/models.py`): **no hay nada que cree avisos** desde la interfaz, así que normalmente verá el vacío. El `status` del servidor es `ready` incluso sin elementos (el frontend lo normaliza a `empty`).

#### Aviso (detalle) — `#avisos/<id>`
- Cabecera «Detalle del aviso». `article.notice-detail`: estado, leído, `h2` título, descripción, `dl` (Zona, Importancia, Fecha y, si está resuelto, «Resolución»), `div.notice-recommendation` con `h3` «Recomendación» + texto; acciones: «Marcar como leído» (brand; solo si no leído) y «Todos los avisos» (claro, `#avisos`).
- **Acciones:** «Marcar como leído» → `POST /api/huertos/actual/avisos/<id>/lectura {}` → `{status:'accepted', id, read:true, item}`; éxito: «Aviso marcado como leído. Su condición no ha cambiado.»; error «No se pudo completar la solicitud. Inténtalo de nuevo.». Escribe en `huerto_avisoleido`.
- **Estados:** «Cargando aviso» / «Consultando su información.»; error «No se pudo consultar el aviso» / «Inténtalo de nuevo.»; no encontrado «Aviso no disponible» + «Este aviso no está disponible.» + «Todos los avisos»; sin huerto igual que la lista.
- **Datos:** `GET /api/huertos/actual/avisos/<id> → {status:'ready', notice:{…}}` (403 si el aviso no es del huerto de la persona).

#### Mi cuenta · Perfil — `#cuenta`
- **Archivos:** V `AppViews.account` `comun.js:82-87`, `ProfileViews.form/profileScreen` `cuenta.js:325-386`; C `ProfileController` `controladores/cuenta.js:138-177`; M `PrivacyData.saveProfile` `comun.js:41`; CSS `panel.css:150-200`.
- **Acceso:** usuaria y admin (para admin es el último destino del menú). Sin sesión → `#acceso`.
- **Disposición:** cabecera «Mi cuenta» + saludo (`Hola, <nombre>`, «Bienvenido» o «Tu información de acceso.»); pestañas «Perfil» (activa) · «Seguridad» · «Privacidad» (`nav.account-tabs aria-label="Apartados de mi cuenta"`); tarjeta «Datos de la cuenta»; tarjeta «Datos personales»; tarjeta «Tu sesión».
- **Elementos:**
  - «Datos de la cuenta» (ícono user): `dl` «Correo electrónico» (valor o «Esperando información de la cuenta») y «Verificación del correo» («Correo verificado» / «Correo sin verificar» / «Sin información disponible»); botón «Cambiar contraseña» (brand → `#cuenta/contrasena`).
  - «Datos personales» / «Son opcionales y puedes cambiarlos cuando quieras.»: vista con `dl` «Nombre», «Apellido», «Alias» (valor o «Sin dato») y botón «Cambiar datos» (claro); al pulsar se oculta la vista y aparece el formulario.
  - «Tu sesión» / «Saldrás de tu cuenta en este navegador.» + botón «Cerrar sesión» (claro, ícono logout) → diálogo de 2.3.
- **Formulario (edición):**

| Campo | Etiqueta | Placeholder | Tipo | Obligatorio | Validación cliente | Servidor | Mensaje |
|---|---|---|---|---|---|---|---|
| `firstName` | «Nombre» | — | texto `maxlength=150`, `autocomplete=given-name` | no | — | ≤150, imprimible (`privacidad/services.py:199-208`) | «No se pudieron guardar los cambios. Revisa los datos e inténtalo de nuevo.» |
| `lastName` | «Apellido» | — | `maxlength=150`, `family-name` | no | — | ≤150 | idem |
| `alias` | «Alias» (ayuda «Lo usaremos para dirigirnos a ti.») | — | `maxlength=64`, `nickname` | no | — | ≤64 | idem |

  Botones «Guardar cambios» (brand → «Guardando…», formulario `aria-busy`, campos `disabled`) y «Cancelar» (claro). `POST /api/cuenta/perfil {firstName,lastName,alias}` → luego `restore()` para refrescar. Estados: «Guardando tus cambios…», «Cambios guardados.», «Demasiados intentos. Espera un momento.».
- **Estados de carga:** «Cargando cuenta» / «Consultando la información de tu cuenta.»; error «No se pudo consultar tu cuenta» / «Inténtalo de nuevo.» + «Reintentar» (siempre con la tarjeta «Tu sesión» para poder salir). Datos de `GET /api/cuenta → {email,verified,profile:{firstName,lastName,alias,greeting,welcomePending,id,email,verified,status},session,role,capabilities,mfaRequired,gardenAssigned}`.
- **Actualización automática:** no. **Accesibilidad:** `aria-labelledby` en cada tarjeta; foco al primer campo al editar y de vuelta al botón al cancelar.
- **Observaciones:** guardar el alias actualiza el saludo en la pantalla actual sin recargar (`showGreeting`). Admin ve la misma pantalla.

#### Mi cuenta · Seguridad — `#cuenta/seguridad`
- **Archivos:** V `MfaViews.account/accountScreen/methodItem` `cuenta.js:226-262,284-321`; C `MfaController` `controladores/cuenta.js:52-135`; M `MfaService` `modelos/cuenta.js:277-332`.
- **Acceso:** usuaria y admin. Los admin sin método fuerte (`mfaRequired`) son enviados aquí desde cualquier `#admin/…`.
- **Disposición:** cabecera «Seguridad» + «Elige cómo confirmas tu identidad al entrar.»; pestañas (Seguridad activa); `#mfa-feedback` (`role="status"`); cuadro de alerta «Activa un método para usar el panel» / «Los administradores necesitan una app autenticadora o una llave de acceso.» (solo si `mfaRequired` y no hay método fuerte); tarjeta «Confirma tu contraseña» (oculta; aparece cuando el servidor pide reautenticación); rejilla `.security-grid` de 4 tarjetas (1 columna ≤1024px).
- **Tarjetas:**
  - «Código por correo»: «Activo: te enviamos un código cada vez que entras con tu contraseña.» o «Inactivo: ya confirmas tu acceso con un método más fuerte.»
  - «App autenticadora»: «Activa.»/«Sin activar.»; botones «Activar» (brand) y «Desactivar» (claro); al activar aparece el formulario con QR (`img alt="Código QR para tu app autenticadora"` 200×200), «Clave manual: <código>», campo «Código de la app» (numérico, `maxlength=6`, `autocomplete=one-time-code`, requerido) y «Confirmar».
  - «Llaves de acceso»: «Usa la huella, el rostro o el PIN de tu dispositivo. Tu PIN y tu biometría nunca salen de él.»; lista `aria-label="Llaves registradas"` (por llave: ícono, nombre o «Llave de acceso», botón «Quitar» con `aria-label="Quitar <nombre>"`); formulario con «Nombre de la llave» (placeholder «Ej. Teléfono personal», `maxlength=100`, requerido) y botón «Agregar llave» (ícono +).
  - «Códigos de recuperación»: «Te quedan X de Y.» o «Se generan al activar tu primer método.»; botón «Generar códigos nuevos» (visible solo si ya existen); tras generar: «Guárdalos ahora: no se volverán a mostrar. Cada uno sirve una sola vez.» + lista `ol`.
  - «Confirma tu contraseña»: campo «Contraseña» + botón «Confirmar».
- **Botones y endpoints:**

| Texto | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|
| «Activar» | `GET /_allauth/browser/v1/account/authenticators/totp` + `GET /api/cuenta/seguridad/totp-qr` | no | muestra QR y clave | «No se pudo completar la operación.» |
| «Confirmar» (app) | `POST …/authenticators/totp {code}` | no | «App autenticadora activada.» y, si procede, muestra códigos de recuperación | «Revisa el dato e inténtalo de nuevo.» (400) / «Demasiados intentos. Espera un momento.» |
| «Desactivar» | `DELETE …/authenticators/totp` | **no** | «App autenticadora desactivada.» | idem |
| «Agregar llave» | `GET …/authenticators/webauthn` → WebAuthn del navegador → `POST …/authenticators/webauthn {name,credential}` | no | «Llave agregada.» | «Este navegador no admite llaves de acceso.», «No se creó la llave.», «No se pudo guardar la llave.» |
| «Quitar» | `DELETE …/authenticators/webauthn {authenticators:[id]}` | **no** | «Llave quitada.» | genérico |
| «Generar códigos nuevos» | `POST …/authenticators/recovery-codes` | **no** | muestra los códigos | genérico |
| «Confirmar» (contraseña) | `POST …/auth/reauthenticate {password}` y repite la operación pendiente | — | continúa | «Contraseña incorrecta.» |

  Al cargar: `GET …/account/authenticators` (error «No se pudieron consultar tus métodos.»).
- **Estados:** `401` → sesión vencida; `403 reauthentication` → pide contraseña y reintenta (`guarded`).
- **Actualización automática:** no. **Accesibilidad:** `#mfa-feedback` toma foco, cambia `role` entre `status` y `alert`.
- **Observaciones:** **«Desactivar» y «Quitar» no piden confirmación**; al quitar el último método fuerte a un admin, el siguiente cambio de ruta lo devuelve a esta pantalla. Si la ruta lleva sufijo (`#cuenta/seguridad/x`) se muestra «Página no disponible» + enlace «Seguridad de mi cuenta».

#### Mi cuenta · Privacidad — `#cuenta/privacidad`
- **Archivos:** V `PrivacyViews` `cuenta.js:436-447`, `ProfileViews.myPrivacy/privacyScreen` `352-432`; C `MyPrivacyController` `controladores/cuenta.js:201-248`.
- **Acceso:** usuaria y admin.
- **Elementos:** cabecera «Privacidad» + «Consulta tus datos y decide sobre las estadísticas de este navegador.»; pestañas; tarjeta **«Mis datos»** («Consulta los datos de tu cuenta. Para corregirlos, usa el apartado Perfil.», botón «Consultar mis datos» → `POST /api/privacidad/mis-datos {}`); resultado `dl`: «Correo electrónico», «Nombre», «Apellido», «Alias», «Cuenta creada» (fecha `es-MX`), «Huertos» (nombres separados por coma) con «Sin dato» si faltan; error «No se pudieron consultar tus datos. Inténtalo de nuevo.». Tarjeta **«Estadísticas de este navegador»**: «Son voluntarias y solo cuentan secciones visitadas. Los totales ya acumulados no permiten localizar una aportación individual.»; «Decisión guardada: <Consultando… | No se pudo consultar. Puedes guardar una decisión nueva. | Sin decisión guardada | Estadísticas permitidas | Estadísticas no permitidas>»; `fieldset` «Tu selección» con radios «Permitir estadísticas en este navegador» / «No permitir estadísticas»; «Tienes un cambio sin guardar.»; botón «Guardar preferencias» (deshabilitado hasta que cambia la selección; «Guardando…»); resultado «Preferencia guardada.» / «No se pudo guardar tu preferencia. Sigue vigente la decisión anterior.». Pie `nav[aria-label="Documentos legales"]`: «Documentos legales» · «Aviso de privacidad» (`#privacidad`) · «Política de cookies» (`#cookies`) · «Términos y condiciones» (`#terminos`).
- **Endpoints:** `POST /api/privacidad/mis-datos` (`{status:'accepted',data:{email,firstName,lastName,alias,createdAt,gardens[]}}`; registra un evento de acceso en `privacidad_eventoprivacidad`); guardar preferencia = `POST /api/privacidad/cookies {statistics}` (misma lógica que el aviso de cookies; se mantiene sincronizado con `CookieController.onChange`).
- **Observaciones:** no hay exportación ni borrado de datos ni de cuenta (los derechos ARCO se remiten al Aviso de privacidad, que está vacío).

#### Cambiar contraseña — `#cuenta/contrasena`
- **Archivos:** V `AuthViews.render(embedded)` `cuenta.js:92-93`, `form('cambiar')` `:53-54`; C `AuthController.mount('cambiar',{embedded:true})` `administracion.js:284-287`.
- **Acceso:** usuaria y admin autenticados. Se muestra **dentro** del marco privado como tarjeta `.auth-flow.account-password.bento-panel`.
- **Elementos:** `h1#auth-title` «Cambiar contraseña»; «Confirma tu contraseña actual y elige una nueva.»; «Contraseña actual» (`current-password`), «Nueva contraseña» (con medidor y consejos, mínimo 15 / máximo 256), «Confirmar contraseña»; botón «Guardar contraseña» (brand); enlace «Cancelar y regresar a Mi cuenta» (`#cuenta`).
- **Validación:** «Escribe tu contraseña actual.», `Usa al menos N caracteres.`, «Las contraseñas no coinciden.»; servidor: «La contraseña actual no es correcta. Inténtalo de nuevo.» (campo actual), rechazos de contraseña (ver registro).
- **Endpoint:** `POST /_allauth/browser/v1/account/password/change {current_password,new_password}`; éxito → «Contraseña actualizada» / «El cambio se completó correctamente.» + botón «Mi cuenta».

#### Sin huerto asignado — «Vincular mi huerto»
- **Dónde aparece:** `#huerto`, `#telemetria`, `#mantenimiento`, `#soporte` cuando `GET /api/huertos/actual` responde 403 `garden-unassigned`. En `#avisos` solo aparece el estado «Sin huerto asignado» (sin formulario).
- **Archivos:** V `BindingViews.userPanel/userStatus/helpPanel` `vistas/equipos.js:10-109`; C `BindingUserController` `controladores/equipos.js:6-34`, `BindingHelpController 129-201`; M `BindingService.consume/normalize` `modelos/equipos.js:7-58`, `BindingHelp` `62-107`; CSS `apariencia.css:663-770`.
- **Disposición:** una tarjeta `.garden-link.binding-panel` (ícono leaf + contenido) en lugar de la línea de estado; el resto de la pantalla queda dentro de `fieldset.user-locked disabled`.
- **Elementos (literales):** `h2#binding-title` «Vincular mi huerto»; «Tu cuenta todavía no tiene un huerto. Escribe o pega el código que te dio el equipo al entregarte el huerto, o el que llegó al correo de tu cuenta. Cada código vence a los 10 minutos y solo sirve una vez.»; etiqueta «Código de vinculación»; campo (`#binding-code`, `maxlength=40`, `autocapitalize=characters`, `autocomplete=one-time-code`, requerido); botón «Vincular huerto» (brand); ayuda «26 caracteres. Puedes pegarlo con o sin guiones.»; estado `#binding-status`.
- **Validación cliente:** normaliza (quita espacios y guiones, mayúsculas, `O→0`, `I,L→1`) y exige 26 caracteres del alfabeto Crockford (`^[0-9A-HJKMNP-TV-Z]{26}$`) → «Revisa el código: son 26 letras y números. Puedes pegarlo con o sin guiones.».
- **Acción:** `POST /api/vinculacion {code}` → `{status:'linked'|'already-linked'|'rejected'|'limited', membership, garden:{name}}`. Éxito: recarga y «Huerto vinculado. Todavía no se reciben lecturas del equipo.». Mensajes: «Validando el código…», `rejected` «El código no es válido o ya venció. Pide uno nuevo al equipo.», `limited` «Demasiados intentos. Pide un código nuevo al equipo; si lo intentaste muchas veces, espera una hora.», HTTP 429 «Demasiadas solicitudes seguidas. Espera un momento y vuelve a intentarlo.», red «No pudimos comunicarnos con el servidor. Vuelve a intentarlo: si ya se vinculó, lo reconoceremos.», otro «No se pudo completar la vinculación. Inténtalo de nuevo.». El servidor bloquea tras 5 intentos fallidos (`CodigoVinculacion.MAX_INTENTOS`).
- **Ayuda** `<details class="binding-support">`: resumen «Solicitar ayuda para vincular mi huerto»; al abrir comprueba el contacto (`CHILITO_CONTACTO_SOPORTE`): si no hay → «El contacto de soporte no está disponible por ahora. Inténtalo más tarde.»; si hay: `fieldset` «¿Qué ocurrió?» con radios «El código venció.», «Perdí o no encuentro el código.», «El código no funciona.», «Otro motivo» (este último exige «Explica el motivo (obligatorio)», máx. 300 caracteres); textos «No escribas el código, contraseñas, códigos de verificación, tu domicilio ni otros secretos. No necesitamos más datos personales.» y ««Preparar correo» abre tu aplicación de correo con el mensaje listo: tendrás que revisarlo y enviarlo tú. «Copiar mensaje preparado» solo lo copia, para que lo pegues donde prefieras.»; botones «Preparar correo» (abre `mailto:` con asunto «[El Chilito] Ayuda con la vinculación»; aviso «Pedimos a tu navegador que abra tu aplicación de correo con el mensaje listo. Revísalo y envíalo desde ahí: todavía no se ha enviado nada.»), «Copiar mensaje preparado» (éxito «Mensaje copiado»; si el portapapeles falla muestra un `textarea` de solo lectura «Mensaje preparado para copiar a mano»), «Copiar dirección de soporte» («Dirección de soporte copiada.»); avisos: «Elige un motivo para preparar el correo.», «Explica el motivo para preparar el correo.», «Acorta tu explicación: puedes añadir más detalles en el correo.», «Quita cualquier código de tu explicación. No hace falta para ayudarte.»; cierre «Esta solicitud no genera un código nuevo ni acredita que el huerto sea tuyo. El equipo debe verificar tu caso antes de emitir otro.».
- **Observaciones:** el código **nunca** se guarda en el navegador. La ayuda no envía nada al servidor: solo redacta un correo.

---

### 3.D Administración

**Menú de administración:** ver 0.3 y 2.3. Orden y etiquetas literales: «Telemetría de flota» (ícono grid), «Consola remota» (support), «Mantenimientos» (tool); grupo «Gestión»: «Abrir correo de soporte» (si hay `CHILITO_CONTACTO_SOPORTE` con formato de correo), «Solicitudes del producto» (inbox), «Equipos y ventas» (grid), «Vinculación de huertos» (leaf), «Guías de cuidado» (list); al pie «Mi cuenta». Todas las operaciones de administración exigen en el **servidor** la capacidad **y** un segundo factor fuerte (TOTP o llave): `require_cap` → 403 `mfa-required` si falta (`datos/services.py:49-53`, `web/api.py:71`).

**Marco común de las pantallas admin:** `#admin-feedback` (`role="status"`, toma foco) encima del contenido; las pantallas de `AdminController` (flota y soporte) muestran, mientras no hay datos: `h1` «Administración» + tarjeta «Consultando la plataforma» / «Espera un momento.» (carga) o «No se pudo consultar la plataforma» / «Comprueba tu acceso e inténtalo de nuevo.» (error) + botón «Reintentar» (`data-admin-action="refresh"`) (`vistas/administracion.js:98-101`). Textos de error comunes: «Tu cuenta no tiene acceso a esta operación.» (403), «El caso ya está resuelto o cambió. Actualiza la consola.» (409 `stale-record`), «No se pudo completar la operación. Inténtalo de nuevo.» (resto).

#### Telemetría de flota — `#admin/flota`
- **Archivos:** V `AdminViews.fleet/management` `vistas/administracion.js:18-51`; C `AdminController` `controladores/administracion.js:5-70`; M `AdminService.snapshot` `modelos/administracion.js:37-59`; CSS `apariencia.css:360-395`, `panel.css:500-587`.
- **Acceso:** admin con capacidad `ver_flota`. Sin ella el enrutador lo reemplaza por el primer destino permitido; el servidor responde 403.
- **Propósito:** vista agregada de la flota de dispositivos y evaluación de IA.
- **Disposición (escritorio):** cabecera; línea de estado; 4 métricas (4 columnas ≥1100px); sección de tendencias (2 gráficas); tabla de dispositivos; 3 métricas de evaluación; tabla de correlaciones; tarjeta «Gestión administrativa».
- **Elementos (literales):**
  - `h1` «Telemetría de flota» / «Indicadores agregados y estado operativo de los dispositivos vinculados.»; línea «Vista agregada de la plataforma» · «Última consulta: <fecha>» o «Sin lecturas disponibles».
  - Métricas: «Nodos reportando» (`—` o `n / total`; nota «Sin información de disponibilidad»), «Humedad media» (`—%`; «Sin lecturas disponibles»), «Evaporación estimada» (`mm/día`; «Sin estimación disponible»), «Alertas de hardware» («Sin información disponible»).
  - «Tendencias ambientales agregadas» / «Últimos 7 días. Sin series de un hogar individual.»: gráficas «Humedad media del sustrato» y «Humedad relativa media» (vacías: `—`, «Aún no hay registros para este periodo.»).
  - «Identidades y dispositivos vinculados» / «Identificadores operativos y conexión al broker Mosquitto.» + botón «Actualizar dispositivos» (ícono refresh); tabla `aria-label="Dispositivos vinculados"` con columnas «Device_ID», «User_ID», «Mosquitto» (insignia «En línea» / «Sin conexión» / «Sin información»), «Último heartbeat» (valores ausentes: «Sin vínculo de usuario en esta proyección», «Sin registro»); sin filas: «Sin registros disponibles.»; pie «Se muestra el vínculo operativo mínimo. No se incluyen contraseñas ni ubicación.».
  - «Telemetría para evaluación de IA» / «Patrones agregados para evaluar el riego predictivo y el desgaste del hardware.»: métricas «Evaporación · mezcla con perlita» (mm/día), «Vida mediana del sensor capacitivo v1.2» (meses), «Órdenes de mini bombas» (/ huerto / día).
  - «Correlaciones por temperatura» / «Ventanas ambientales utilizadas para evaluar el modelo.»: tabla «Temperatura media», «Evaporación estimada», «Órdenes de bomba», «Uso en el modelo»; pie «La evaluación utiliza agregados. Las correlaciones lumínicas requieren una medición verificable de luz.».
  - Tarjeta «Gestión administrativa» / «Acceso a los registros de mantenimiento y a las solicitudes del producto.»: enlaces «Gestión de registros» (`#admin/mantenimientos`, si tiene `gestionar_mantenimientos`), «Abrir correo de soporte» (si configurado) y «Solicitudes del producto» (`#admin/solicitudes`, si tiene `atender_consultas`); nota «Las consultas de «Consíguelo» se guardan en el buzón y generan un aviso al correo de soporte. Responde desde tu correo.».
- **Botones:** «Actualizar dispositivos» → recarga `GET /api/admin/flota` → éxito «Consulta actualizada.»; error genérico.
- **Datos:** `GET /api/admin/flota → {status:'ready', nodes:[{device,gardenId,connected,heartbeat}], metrics, trends:{soil,humidity}}` (`datos/services.py:371-374`): **`connected` y `heartbeat` son `null`, `metrics` es `null` y `trends` vacíos**; hasta 100 dispositivos de `datos_dispositivo`. El frontend espera además `n.user`, `metrics.reporting/total/soilHumidity/…`, `correlations` que el backend **no envía**.
- **Estados:** cargando, error, sin permiso (403 «Tu cuenta no tiene acceso…»), **sin datos de sensores (permanente)**.
- **Actualización automática:** no.
- **Accesibilidad:** tablas en contenedores `role="region"` con `tabindex=0`; insignia de conexión con texto además de color.
- **Observaciones:** pantalla completa **sin datos reales**; las métricas de «evaluación de IA» y las correlaciones no tienen fuente en el backend.

#### Consola remota — `#admin/soporte`
- **Archivos:** V `AdminViews.remote/diagnostics` `administracion.js:52-78`; C `AdminController` `administracion.js:5-70`; M `AdminService` (`modelos/administracion.js:6-85`) con `request`, `act`, `closeRemote`, `validateToken`, `requestToken`, `resolveCase`.
- **Acceso:** admin con `atender_soporte`.
- **Propósito:** atender reportes de soporte de personas usuarias: pedir el token, validarlo, abrir una sesión técnica de diagnóstico y resolver el caso.
- **Disposición (escritorio):** cabecera; «Buzón de reportes» (tabla); «Detalle y autorización» (tarjeta del caso); «Sesión de diagnóstico» (solo con sesión abierta); «Alcance del acceso remoto».
- **Elementos (literales):**
  - `h1` «Consola remota» / «Atiende cada reporte con la autorización temporal de la persona usuaria.»
  - «Buzón de reportes» / «Los registros técnicos se abren únicamente con el token del caso seleccionado.» + botón «Actualizar reportes». Tabla `aria-label="Reportes de soporte"`: «Folio», «Device_ID», «Incidente», «Atención» (Abierto/Resuelto), «Autorización» («Espera validación», «Autorización vencida», «Autorización revocada», «Sin autorización», «Diagnóstico autorizado»), «Acción» (botón «Abrir», `aria-label="Abrir caso <folio>"`). Sin reportes: «No hay reportes registrados.». La fila seleccionada se resalta.
  - «Detalle y autorización» (tarjeta `#admin-ticket-detail`, `tabindex=-1`): sin selección «Selecciona un reporte» / «Abre un caso del buzón para consultar su detalle y validar el token correspondiente.»; con caso: `h2` «Caso <folio>»; `dl` «Device_ID», «User_ID», «Incidente», «Creado», «Atención», «Autorización», «Aviso de caso nuevo» (estado del correo: «Pendiente de envío» / «Aceptado por el servidor de correo» / «Envío fallido; se reintentará» / «Sin aviso registrado»), «Token solicitado» («No» o fecha · estado del aviso); texto «El diagnóstico queda limitado a este caso. El token de otro caso no concede acceso. Vencer o revocar la autorización no resuelve el caso.»
  - Si el caso **no** está resuelto: botón «Solicitar token a la persona usuaria»; formulario con etiqueta «Token compartido por la persona usuaria», campo `#admin-token` (texto, exactamente 43 caracteres `[A-Za-z0-9_-]`, requerido, sin autocompletado) y botón «Validar token»; estado «Acceso autorizado hasta el <fecha>.» / «Acceso técnico bloqueado. Valida una autorización vigente para continuar.»; formulario «Resolver caso»: «Resultado de la atención» (select: «Problema solucionado», «Sin falla detectada», «Sin respuesta de la persona usuaria», «Otro (explicado en la nota)»), «Nota (obligatoria si eliges «Otro»)» (textarea, 500), aviso «Resolver es definitivo: revoca la autorización vigente y cierra el acceso técnico de este caso.» y botón «Resolver caso».
  - Si está resuelto: «Resuelto el <fecha> · <resultado>[ · <nota>]. El permiso está revocado y el token ya no abre acceso.»
  - Con sesión técnica abierta: «Sesión de diagnóstico» (subtítulo `<Device_ID> · <folio>`) y tarjeta «Diagnóstico del dispositivo»: «Servicio de diagnóstico remoto no conectado. La sesión está abierta con la autorización del caso, pero todavía no hay lecturas del dispositivo.» (o cuadrícula de pines GPIO + bloque `<pre>` de registros con `aria-label="Registros técnicos del caso"`), botones «Consultar de nuevo» y «Cerrar sesión técnica».
  - «Alcance del acceso remoto»: «Sesión de diagnóstico» — «Se abre con el token vigente del caso. El diagnóstico remoto del dispositivo todavía no está conectado.»; «Duración» — «Máximo 24 horas desde que se emite; usar el token no la renueva.»; «Cierre del acceso» — «Revocación de la persona usuaria, vencimiento o resolución del caso.»; «Fuera del alcance» — «Acceso permanente, contraseñas, ubicación e historial de cultivo.»
- **Botones y acciones:**

| Texto | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|
| «Actualizar reportes» | `GET /api/admin/soporte?page=n` (junta todas las páginas) | no | «Consulta actualizada.» | error genérico |
| «Abrir» | cierra una sesión técnica previa (`POST /api/admin/sesiones/<id>/cerrar`) y carga el caso | no | resalta el caso, foco en detalle | «Tu cuenta no tiene acceso a esta operación.» etc. |
| «Solicitar token a la persona usuaria» | `POST /api/admin/soporte/<caso>/solicitar-token` → `{status:'accepted',notice,repeated}` | no | «Solicitud registrada. Se avisará a la persona usuaria por correo, sin el token; el estado del aviso aparece en el detalle.» (o «Ya se pidió el token de este caso hace menos de 10 minutos. No se envió otro aviso.») | «El caso ya está resuelto o cambió. Actualiza la consola.» |
| «Validar token» | `POST /api/admin/soporte/<caso>/abrir {token}` → `{session:{id,ticket,expiresAt,openedAt}}` | no | «Token válido para este reporte. El diagnóstico autorizado está disponible.» (carga el diagnóstico con `POST /api/admin/sesiones/<id>/accion {action:'diagnostic'}`) | «El token es incorrecto. Comprueba el código compartido por la persona usuaria.» (formato) / «Tu cuenta no tiene acceso a esta operación.» (token no válido/vencido: el servidor responde 403) |
| «Consultar de nuevo» | `POST /api/admin/sesiones/<id>/accion {action:'diagnostic'}` | no | «Consulta de diagnóstico registrada.» | «No hay una autorización vigente para este reporte. Solicita un token nuevo a la persona usuaria.» |
| «Cerrar sesión técnica» | `POST /api/admin/sesiones/<id>/cerrar` | no | «Sesión técnica cerrada. Los registros vuelven a estar bloqueados.» | genérico |
| «Resolver caso» | `POST /api/admin/soporte/<caso>/resolver {result,note}` | **no** (aunque el texto avisa que es definitivo) | «Caso resuelto. El permiso quedó revocado y el acceso técnico cerrado.» | «El caso ya está resuelto o cambió. Actualiza la consola.» |

- **Estados:** cargando/error (ver marco admin); vacío «No hay reportes registrados.»; «Selecciona un reporte»; sin sesión técnica (bloqueado); autorización vencida: el temporizador de 1 s (y al volver a la pestaña) cierra la sesión técnica y avisa «La autorización ha vencido. El acceso técnico se cerró.».
- **Actualización automática:** comprobación de vencimiento cada 1 s; **al salir de la pantalla se cierra la sesión técnica** (`dispose` → `closeRemote`); al cerrar sesión de la cuenta también.
- **Accesibilidad:** botones «Abrir» con `aria-label`; foco al detalle del caso; avisos `role="alert"/"status"`.
- **Observaciones:** el «diagnóstico remoto» **no está conectado a ningún dispositivo** (lo dice la propia pantalla; `diagnostico`/`technical_action` no entrega pines ni registros). El mensaje de error `wrong-report` está definido en la vista pero ningún servicio lo produce. Una cuota de 15 operaciones/minuto aplica a `/soporte/` y `/sesiones/` (60 en el resto), `web/services.py:31-39`.

#### Mantenimientos — `#admin/mantenimientos`
- **Archivos:** V `MaintenanceViews` `vistas/huerto.js:406-558`; C `MaintenanceController` `controladores/huerto.js:303-353`; M `MaintenanceService/MaintenanceDates` `modelos/huerto.js:240-305`; calendario `DateFilterViews` `vistas/comun.js:157-310`.
- **Acceso:** admin con `gestionar_mantenimientos`; el alcance real es **por huerto asignado** (`datos_asignacionmantenimiento`); sin huertos asignados «Tu cuenta no tiene huertos asignados.» y «Registrar» deshabilitado.
- **Propósito:** registrar, corregir y anular intervenciones de mantenimiento de huertos asignados.
- **Disposición (escritorio):** cabecera «Mantenimientos» / «Registra, corrige y anula intervenciones de los huertos asignados.»; tarjeta «Registrar intervención» (formulario en línea); tarjeta «Registros» (filtros + tabla); diálogo de detalle.
- **Formularios:**

| Formulario | Campo | Etiqueta | Tipo | Obligatorio | Validación |
|---|---|---|---|---|---|
| Registrar intervención | `garden` | «Huerto» | select (huertos asignados) | sí | servidor: `identifier` y alcance |
| | `task` | «Tipo» | select (5 tipos, etiquetas de 3.C) | sí | servidor: tipos válidos |
| Filtros | `garden` | «Huerto» | select, «Todos» | no | — |
| | `state` | «Estado» | select «Todos» / «Vigentes» (`active`) / «Anulados» (`voided`) | no | lista blanca |
| | `task` | «Tipo» | select «Todos» + 5 | no | — |
| | `since`, `until` | «Desde», «Hasta» | texto `aaaa-mm-dd` (`maxlength=10`) + botón calendario | no | fecha real; «Escribe una fecha válida con el formato AAAA-MM-DD.»; «Hasta debe ser igual o posterior a Desde.» |
| Diálogo | `task` | «Tipo correcto» | select | en corrección | — |
| | `reason` | «Motivo» | textarea `rows=3 maxlength=500` | sí | «Escribe el motivo.»; servidor ≤500 y no vacío |

- **Elementos:** tabla `aria-label="Registros de mantenimiento"`: «Fecha», «Huerto», «Tipo», «Estado» (Vigente/Anulado), «Acción» («Ver»); estado `role="status"`: «Cargando registros…», «N registros.»; botones de calendario `aria-label="Abrir calendario: Desde|Hasta"` (popover con rejilla; Hoy / Limpiar / cerrar).
- **Diálogo «Registro»** (`dialog.app-dialog`, botón ✕ `aria-label="Cerrar registro"`): historial `ol` («Original: <tipo>», «<fecha> · Anulación: <motivo>» / «<fecha> · Corrección a <tipo>: <motivo>»); si el registro está anulado el formulario se oculta; botones «Guardar corrección» (brand), «Cerrar», «Anular registro» (peligro, a la izquierda).
- **Botones y endpoints:**

| Texto | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|
| «Registrar» | `POST /api/admin/mantenimientos {gardenId, task}` | no | «Intervención registrada.» | «Tu cuenta no tiene acceso a este huerto.» (403), «Revisa los datos e inténtalo de nuevo.» (400), «Demasiadas operaciones. Espera un momento.» (429), «No se pudo completar la operación. Inténtalo de nuevo.» |
| «Ver» | `GET /api/admin/mantenimientos/<id> → {record, revisions[{number,kind,correctedType,editor,reason,at}]}` | — | abre el diálogo | idem |
| «Guardar corrección» | `POST …/<id>/corregir {task,reason,revision}` | no | «Corrección guardada.» | «Otra persona cambió este registro. Revísalo de nuevo antes de continuar.» (cierra el diálogo y recarga) |
| «Anular registro» | `POST …/<id>/anular {reason,revision}` | **no** (solo exige motivo) | «Registro anulado.» | idem |
| Filtros (cambio de cualquier campo / Enter) | `GET /api/admin/mantenimientos?garden=&state=&task=&since=&until=` | — | actualiza tabla | «No se pudo completar la operación…» en `data-maint-status` |

- **Estados:** cargando, vacío (`0 registros.`), error, sin huertos asignados.
- **Actualización automática:** no. Solo se pide **la primera página (25 filas)**: `service.list(filters)` no envía `page`; el contador muestra el total real pero **no hay paginador**.
- **Accesibilidad:** ayuda sr-only «Escribe la fecha en formato año-mes-día, por ejemplo 2026-11-07. Usa flecha abajo para abrir el calendario.»; calendario completo con teclado (ver 1.5).
- **Observaciones:** edición ajena se audita en `datos_revisionmantenimiento` y `datos_auditoria`; las revisiones son de solo inserción; control de concurrencia por `revision`. El registro original nunca se modifica.

#### Solicitudes del producto — `#admin/solicitudes`
- **Archivos:** V `InquiryViews` `vistas/administracion.js:107-177`; C `InquiryController` `controladores/administracion.js:74-117`; M `InquiryService` `modelos/administracion.js:89-135`.
- **Acceso:** admin con `atender_consultas`.
- **Propósito:** buzón de consultas llegadas desde «Consíguelo»; registrar quién las atendió.
- **Disposición:** cabecera «Solicitudes del producto» / «Consultas recibidas desde «Consíguelo». Responde desde tu correo y registra aquí su atención.»; pestañas-filtro; línea de estado; lista de tarjetas; paginador.
- **Elementos:** `nav.account-tabs.inquiry-filters aria-label="Filtrar consultas"` con botones «Todas», «Nuevas», «Atendidas», «Archivadas» (`aria-pressed`); estado `role="status"`: «Consultando el buzón…», «N consulta(s)», «No hay consultas en este filtro.»; cada tarjeta `article.bento-panel.inquiry-item`: folio (`strong`), estado («Nueva», «Atendida», «Archivada»), hora (`<time datetime>`), «<nombre o «Sin nombre»> · <correo>», mensaje, y una línea «<Sin atender | Atendida por <correo> el <fecha> | Último registro: <correo>, <fecha>> · <Aviso pendiente de envío | Aviso aceptado por el servidor de correo | El aviso por correo falló; se reintentará | Sin aviso registrado>»; acciones; paginador `nav aria-label="Páginas del buzón"`: «Anterior», «Página X de Y», «Siguiente» (solo si hay más de 25).
- **Botones:**

| Texto | Visible si | Acción | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|---|---|
| «Responder en Gmail» | el correo es válido | abre `https://mail.google.com/mail/?view=cm&fs=1&to=<correo>&su=Re: [El Chilito] Pregunta sobre el producto (<folio>)` (+`authuser=<soporte>`) en pestaña nueva; `aria-label="Responder a <correo> en Gmail (abre una pestaña nueva)"` | — (no envía nada) | no | — | — |
| «Marcar como atendida» (brand) | estado ≠ atendida | `advance(id,'atendida')` | `POST /api/admin/consultas/<id>/estado {state:'atendida'}` | no | «Consulta marcada como atendida.» | «No se guardó el cambio: ese paso no está permitido o la consulta ya había cambiado. Se actualizó la lista.» (409), «Tu cuenta no tiene la capacidad para atender consultas.» (403), «Demasiadas operaciones seguidas. Espera un momento.» (429), «No se pudo actualizar la consulta.» |
| «Archivar» | estado ≠ archivada | `advance(id,'archivada')` | ídem `{state:'archivada'}` | no | «Consulta archivada.» | idem |
| «Anterior» / «Siguiente» | >1 página | cambia `page` | `GET /api/admin/consultas?page=n[&state=…]` | — | — | «No se pudo consultar el buzón. Inténtalo de nuevo.» |

- **Datos:** `GET /api/admin/consultas?page&state → {items:[{id,folio,receivedAt,name,email,message,state,attendedBy,attendedAt,notice}],page,total}` de `datos_consultaproducto` + `datos_avisocorreo`. Transiciones: nueva→atendida|archivada, atendida→archivada, archivada→atendida (nunca vuelve a «nueva»).
- **Actualización automática:** cada **30 s** y al volver a la pestaña, en segundo plano (`X-Chilito-Sondeo`, no alarga la sesión) y solo repinta si cambió la firma (`total`, ids, estados, avisos).
- **Observaciones:** responder se hace **fuera** de la aplicación; nada registra que se respondió salvo el botón «Marcar como atendida». Sin búsqueda ni exportación.

#### Vinculación de huertos — `#admin/vinculacion`
- **Archivos:** V `BindingViews.adminShell/mountAdmin/reveal/table` `vistas/equipos.js:112-249`; C `BindingAdminController` `controladores/equipos.js:36-126`; M `BindingService.panel/issue/revoke` `modelos/equipos.js:46-48`.
- **Acceso:** admin con `vincular_huertos`; emitir/revocar exige **segundo factor reciente (5 minutos)**: si no, el servidor responde 403 `reauthentication-required` y se abre el diálogo de confirmación.
- **Propósito:** emitir códigos de un solo uso (vigencia 10 minutos) que enlazan un huerto entregado con la cuenta de su dueño; revocarlos.
- **Disposición:** cabecera «Vinculación de huertos» / «Emite un código para asociar un huerto entregado a la cuenta de su dueño. El código vence a los 10 minutos y solo sirve una vez.»; tarjeta «Emitir código»; tarjeta «Códigos pendientes»; tarjeta «Últimos códigos cerrados»; diálogo de reautenticación.
- **Formulario «Emitir código»** (`novalidate`):

| Campo | Etiqueta | Tipo | Obligatorio | Validación |
|---|---|---|---|---|
| `garden` | «Huerto entregado» | select: «Elige un huerto» / «No hay huertos libres con equipo registrado»; opciones `<nombre> · <clave> · <dispositivo>` | sí | cliente: no vacío; servidor: huerto con dispositivo |
| `email` | «Correo de la cuenta» | `email`, `maxlength=254`, `autocomplete=off` | sí | cliente: no vacío; servidor: cuenta activa y verificada |
| `delivery` | «Entrega del código» | radios «En persona: se muestra aquí una sola vez» (por defecto) / «Por correo verificado de la cuenta: tú no lo verás» | sí | servidor: `presencial|correo` |

  Texto: «Emítelo cuando la persona ya haya iniciado sesión y esté lista para escribirlo.» y «El envío por correo solo está disponible si antes se emitió un código en persona para este huerto y esta cuenta.»; botón «Emitir código» (brand).
- **Resultado:** si es presencial, `div.binding-reveal`: «Código para dictar o copiar» + código agrupado (`.binding-code`, **única aparición**) + «Vence a las HH:MM. Solo se muestra ahora; si se pierde, emite otro.» + botón «Copiar código»; si es por correo: «Código <folio> enviado a <cuenta>» + estado («Entrega presencial», «Envío en curso», «El servidor de correo aceptó el mensaje. Esto no confirma que haya llegado al buzón.», «No se envió. El código quedó anulado.», «No pudimos confirmar el envío. El código quedó anulado: si el correo llega después, ya no servirá.»).
- **Tablas:** «Códigos pendientes» (`Solo datos de control: el código nunca se vuelve a mostrar.`) con columnas «Folio», «Huerto», «Cuenta», «Entrega» (Presencial/Correo), «Emitido», «Vence», «Intentos», «Estado» («Pendiente», «Vencido», «Usado», «Revocado», «Reemplazado», «Bloqueado por intentos»), «Acción» (botón «Revocar», `aria-label="Revocar el código <folio>"`); «Últimos códigos cerrados» sin «Acción»; vacío «No hay códigos en esta lista.».
- **Diálogo «Confirma tu segundo factor»** (`aria-labelledby/describedby`): «Para emitir o revocar códigos necesitas haber confirmado tu app autenticadora o tu llave de acceso en los últimos 5 minutos.»; campo «Código de tu app autenticadora» (6 dígitos, `pattern=[0-9]{6}`); botones «Usar llave de acceso», «Cancelar», «Confirmar». Errores: «Escribe los 6 dígitos de tu app autenticadora.», «Demasiados intentos. Espera un momento.», «No se pudo confirmar. Revisa el código o inténtalo con tu llave.». Cancelar: «Operación cancelada: no se emitió ni revocó nada.».
- **Botones y endpoints:**

| Texto | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|
| «Emitir código» | `POST /api/admin/vinculacion/emitir {garden,email,delivery}` → `{status:'issued',binding,code?}` o `{status:'refused',reason}` | segundo factor reciente | «Código emitido. Díctalo o cópialo ahora: no se volverá a mostrar.» / «Código emitido para envío por correo.» | «Elige un huerto y escribe el correo de la cuenta.»; rechazos: «Elige cómo se entregará el código.», «Ese huerto no existe o no tiene un equipo registrado.», «No hay una cuenta activa y verificada con ese correo.», «Esa cuenta ya tiene un huerto vinculado.», «Ese huerto ya está vinculado a otra cuenta.», «Esa cuenta ya tuvo este huerto. Reactivarlo no se hace desde aquí.», «El envío por correo solo se permite después de una emisión presencial de ese huerto para esa cuenta.» |
| «Revocar» | `POST /api/admin/vinculacion/<id>/revocar {}` | segundo factor reciente | «Código revocado.» | «Ese código ya estaba cerrado. Se actualizó la lista.» (409) |
| «Copiar código» | portapapeles | — | «Código copiado.» | «No se pudo copiar. Selecciona el código y cópialo a mano.» |
| «Confirmar» (diálogo) | `POST /_allauth/browser/v1/auth/2fa/reauthenticate {code}` | — | repite la operación | ver arriba |
| «Usar llave de acceso» | `GET/POST /_allauth/browser/v1/auth/webauthn/reauthenticate` | — | repite la operación | idem |

  Carga: `GET /api/admin/vinculacion → {status,gardens:[{id,name,key,device}],pending[≤50],recent[≤20]}` (cada fila `{id,folio,garden,gardenKey,account,issuedBy,delivery,issuedAt,expiresAt,attempts,state,mail,closedAt}`). Errores de carga: «Tu cuenta no tiene la capacidad para vincular huertos.», «Demasiadas operaciones seguidas. Espera un momento.», «Revisa los datos del formulario.», «No se pudo comunicar con el servidor. Inténtalo de nuevo.», «No se pudo consultar la vinculación.».
- **Tablas BD:** `datos_codigovinculacion`, `huerto_membresia`, `huerto_huerto`, `datos_dispositivo`, `cuentas_usuario`, `account_emailaddress`, `datos_auditoria`, `datos_avisocorreo`.
- **Actualización automática:** no (se recarga tras cada operación). **Accesibilidad:** el código tiene foco y desplaza a la vista tras emitirse; tablas con `scope` y `aria-label`.
- **Observaciones:** el código **desaparece al salir de la pantalla**; el servidor solo guarda su resumen (`make_password`).

#### Equipos y ventas — `#admin/comercial`
- **Archivos:** V `CommerceViews` `vistas/administracion.js:181-317`; C `CommerceController` `controladores/administracion.js:121-206`; M `CommerceModel` `modelos/administracion.js:140-220`; CSS `comercial.css` (47 líneas).
- **Acceso:** admin cuya sesión incluya `vincular_huertos` (**«visibilidad provisional; no concede permisos comerciales»**, `modelos/comun.js:66`). Sin ella: `h1` «Equipos y ventas» + tarjeta «Apartado no disponible» / «Tu sesión no tiene habilitado este destino administrativo.».
- **Propósito (según el texto):** inventario, venta presencial y preparación de entregas. **En la práctica es un conjunto de borradores locales: no tiene endpoints ni guarda nada.**
- **Disposición:** cabecera «Equipos y ventas» / «Inventario, venta presencial y preparación de entregas.»; pestañas `role="tablist"` («Equipos», «Ventas y entregas», «Vinculación», «Resumen económico», navegables con ← → Inicio Fin) y 4 paneles `role="tabpanel"`.
- **Panel «Equipos»:** tarjeta «Equipos registrados» (ícono grid) con filtro «Buscar equipo o huerto» (`type=search`, 120) + «Disponibilidad» («Todos», «Disponible», «Reservado», «No disponible») + botón «Aplicar filtros»; estado «La consulta del inventario todavía no está disponible.»; tabla (columnas «Equipo», «Huerto», «Disponibilidad», «Vinculación», «Conexión», «Detalle») con la única fila «Listado pendiente de servicio. Los borradores no son equipos registrados.»; tarjeta «Preparar alta de equipo» («El identificador es visible; no es una contraseña ni acredita conexión.») con campos «Identificador del equipo» (3–80 car., `[A-Za-z0-9][A-Za-z0-9._:-]`), «Nombre del huerto» (1–120), «Disponibilidad propuesta» («Selecciona una opción»); botón «Revisar borrador de equipo» y nota «El registro definitivo todavía no está disponible. No se creará ningún dispositivo.»; al revisar aparece «Detalle del equipo · borrador» (Equipo, Huerto, Disponibilidad propuesta, Registro «Sin registrar», Vinculación «Sin consultar», Conexión «Sin datos de conexión») y botones «Seguir editando» y «Usar identificador en borrador de venta».
- **Panel «Ventas y entregas»:** filtro (Equipo o correo, Desde, Hasta, Venta «Registrada», Pago «Pendiente/Completo», Entrega «Por acordar/Programada/Entregada», Vinculación «Sin vincular/Vinculado») + «Aplicar filtros» (estado «La consulta de ventas todavía no está disponible.»); tabla vacía («Venta / equipo», «Destinatario», «Fecha», «Precio total», «Venta», «Pago», «Entrega», «Vinculación»: «Listado pendiente de servicio. No se incluyen borradores en ventas ni cobros.»); formulario «Preparar registro de venta»: «Identificador del equipo», «Correo de la cuenta destinataria», «Fecha de venta» (AAAA-MM-DD, calendario, no posterior a hoy), «Precio total del equipo» (>0, ≤ 999999999.99, hasta 2 decimales, punto o coma), «Importe recibido declarado» (0…total), «Referencia textual del pago (opcional)» (≤120), «Modalidad de entrega» («Entrega a domicilio»/«Recogida acordada»), «Fecha prevista de entrega (opcional)» (no anterior a la venta); botón «Revisar borrador de venta»; resultado «Revisión de venta · borrador» con saldo aritmético, estados «Sin confirmar» y «Sin consultar».
- **Panel «Vinculación»:** cadena de 5 pasos (Equipo, Venta, Pago, Entrega, Vinculación) con textos «Registro y disponibilidad por consultar.», «Registro comercial por integrar.», «Pago completo: condición futura por validar en Django.», «Modalidad y fecha no acreditan recepción física.», «Cuenta verificada, un huerto activo y controles actuales del servidor.»; bloque «Relación preparada en esta visita»; enlace «Abrir Vinculación de huertos» (`#admin/vinculacion`) y nota «Abre el apartado existente. No transfiere el borrador ni emite un código. La comprobación comercial del pago sigue pendiente de integración.».
- **Panel «Resumen económico»:** formulario «Resumen por periodo» («Periodo»: «Todo el periodo», «Mes actual hasta hoy», «Mes anterior», «Personalizado»; «Desde»; «Hasta»), botón «Consultar periodo» («La consulta económica todavía no está disponible.»); 4 tarjetas «Cantidad de ventas», «Importe vendido», «Cobros», «Saldo» con `—` y notas «Requiere …»; tarjeta «Ganancias»: «Pendientes de definir costos y gastos. El precio de venta por sí solo no permite calcularlas.».
- **Mensajes de error de validación (literales):** «Usa de 3 a 80 caracteres: letras, números, punto, guion, dos puntos o guion bajo; empieza por letra o número.», «Escribe un nombre de huerto de 1 a 120 caracteres, sin saltos de línea ni controles.», «Elige la disponibilidad propuesta.», «Escribe el identificador del equipo (3 a 80 caracteres, sin espacios).», «Escribe un correo válido. Su cuenta y verificación se comprobarán en el servidor.», «Escribe una fecha de venta válida con formato AAAA-MM-DD.», «La fecha de venta no puede ser posterior a hoy.», «El precio debe ser mayor que cero, sin miles y con hasta dos decimales (máximo 999999999.99).», «Escribe un importe desde cero, sin miles y con hasta dos decimales (máximo 999999999.99).», «El importe recibido declarado no puede superar el precio total.», «Usa hasta 120 caracteres, sin saltos de línea ni controles.», «Elige entrega a domicilio o recogida acordada.», «Escribe una fecha de entrega válida con formato AAAA-MM-DD o déjala por acordar.», «La fecha de entrega prevista no puede ser anterior a la venta.»; resumen «Revisa los campos señalados antes de continuar.».
- **Estados:** sin carga ni error de red (sin red). Sin permiso: «Apartado no disponible».
- **Actualización automática:** no. Los borradores **se pierden al recargar o al salir** (`model.dispose()`); «El borrador dura solo esta visita y se pierde al recargar.».
- **Accesibilidad:** pestañas ARIA con navegación por flechas; errores por campo `aria-invalid` + `aria-describedby`; `commerce-date-help` sr-only.
- **Observaciones:** **pantalla maqueta**: no hay endpoints, tablas ni modelos de equipos/ventas/pagos en el backend, y no escribe ningún dato. Es la pieza más alejada de «funcionar».

#### Guías de cuidado — `#admin/guias`
- **Archivos:** V `CareGuideViews.adminShell…` `vistas/huerto.js:271-401`; C `CareGuideAdminController` `controladores/huerto.js:187-300`; M `CareGuideService` `modelos/huerto.js:171-236`; backend `datos/guias.py`.
- **Acceso:** admin con `gestionar_guias` (+ segundo factor: «Activa tu app autenticadora o una llave de acceso para gestionar guías.»).
- **Propósito:** crear, editar, publicar y retirar las fichas que ven las personas usuarias en «Mantenimiento».
- **Disposición:** cabecera «Guías de cuidado» / «Crea, edita y publica las preguntas que ven las personas en Mantenimiento. Las fichas son compartidas: no dependen de quién las creó.»; barra con filtros y «Nueva ficha»; editor (oculto hasta abrirlo); resumen; lista de tarjetas.
- **Elementos:** filtros `role="group" aria-label="Filtrar por estado"`: «Todas», «Publicadas», «Borradores», «Retiradas» (`aria-pressed`); botón «Nueva ficha» (brand); `p` resumen `role="status"`: «Consultando las fichas…», «N ficha(s)», «No hay fichas en este filtro.», «Todavía no hay fichas.», «Aplicando el cambio…»; tarjeta por ficha: estado («Borrador», «Publicada», «Retirada»), `h3` pregunta, «Orden N · Última edición: <correo o «Carga inicial»>, <fecha>», botones: «Editar»; «Publicar» (si borrador) / «Volver a publicar» (si retirada) / «Retirar» (si publicada) — todos con `aria-label="<acción>: <pregunta>"`.
- **Editor** (`section.bento-panel`): título y pista según el estado — nueva «Nueva ficha» / «Se guardará como borrador. Nadie la verá hasta que pulses «Publicar» en la lista.»; borrador «Editar borrador» / «Sigue siendo un borrador. …»; publicada «Editar ficha publicada» / «Esta ficha está publicada: al guardar, los cambios serán visibles de inmediato para las personas usuarias.»; retirada «Editar ficha retirada» / «Guardar no la publica. Para mostrarla de nuevo, usa «Volver a publicar» en la lista.»; etiqueta del botón guardar: «Guardar como borrador» / «Guardar y actualizar lo publicado» / «Guardar (sigue retirada)».
- **Formulario:**

| Campo | Etiqueta | Tipo | Obligatorio | Validación cliente | Servidor |
|---|---|---|---|---|---|
| `question` | «Pregunta» | texto `maxlength=200` | sí | «Escribe la pregunta.» | texto no vacío ≤200 |
| `answer` | «Respuesta» (ayuda «Solo texto. Deja una línea en blanco para separar párrafos.») | textarea `rows=9 maxlength=4000` | sí | «Escribe la respuesta.» | ≤4000 |
| `order` | «Orden» (ayuda «Número de 1 a 9999. Se muestra de menor a mayor.») | texto numérico `maxlength=4` | sí | «El orden debe ser un número entero de 1 a 9999.» | entero 1…9999 |
| `sourceName` | «Nombre de la fuente (opcional)» | texto ≤120 | no (sí si hay enlace) | «Indica el nombre de la fuente del enlace.» | ≤120 |
| `sourceUrl` | «Enlace de la fuente (opcional)» (ayuda «Solo http:// o https://.») | `type=url` ≤500 | no | «El enlace debe empezar por http:// o https://.», «Revisa el enlace de la fuente.» | http/https |

  Botones: guardar (etiqueta según estado), «Cancelar», y «Cargar la versión actual (descarta lo escrito)» (solo tras un conflicto).
- **Botones y endpoints:**

| Texto | Endpoint | Confirmación | Éxito | Error |
|---|---|---|---|---|
| «Nueva ficha» / «Editar» | — (abre el editor; si hay texto sin guardar: «Tienes cambios sin guardar en el formulario. Guárdalos o pulsa Cancelar antes de continuar.») | no | — | — |
| guardar (nueva) | `POST /api/admin/guias {question,answer,order,sourceName,sourceUrl}` | no | «Borrador guardado. Todavía no es visible para las personas usuarias.» | «Revisa los datos: alguna longitud, número o enlace no es válido.» |
| guardar (existente) | `POST /api/admin/guias/<id>/editar {…, version}` | no | «Cambios guardados y visibles para las personas usuarias.» (publicada) / «Cambios guardados. La ficha sigue retirada.» / borrador | «Otra persona cambió esta ficha mientras la editabas. No se guardó nada y tu texto sigue aquí. Cópialo si lo necesitas y carga la versión actual.» (409) |
| «Publicar» / «Volver a publicar» | `POST /api/admin/guias/<id>/publicar {version}` | **no** | «Ficha publicada. Ya es visible para las personas usuarias.» | «No se pudo publicar la ficha.»; conflicto «Otra persona cambió esa ficha. Se actualizó la lista: revísala antes de repetir la acción.» |
| «Retirar» | `POST /api/admin/guias/<id>/retirar {version}` | **no** | «Ficha retirada. Ya no es visible; puedes consultarla en Retiradas.» | «No se pudo retirar la ficha.» |
| «Cancelar» | — | no | cierra el editor | — |

  Otros errores: «Tu cuenta no tiene la capacidad para gestionar guías.», «Demasiadas operaciones seguidas. Espera un momento.», «No se pudo guardar por un conflicto. Inténtalo de nuevo.», «No pudimos confirmar el resultado. Vuelve a intentarlo sin cambiar nada: no se duplicará.» (red/5xx), «No se pudieron consultar las fichas.» (con «Reintentar»).
- **Datos:** `GET /api/admin/guias → {status:'ready', guides:[{id,key,question,answer,order,state,sourceName,sourceUrl,version,createdAt,updatedAt,createdBy,updatedBy}]}` de `datos_guiacuidado` (máx. `MAX_LISTA`), auditoría en `datos_auditoria`. La `key` se genera al crear (no editable).
- **Actualización automática:** no (recarga tras cada acción). Control de concurrencia por `version`.
- **Observaciones:** «Retirar» y «Publicar» **no piden confirmación** aunque son visibles de inmediato. Las claves `sustrato-perlita` y `germinacion-inicio` están enlazadas desde Mantenimiento: si se retiran, el enlace muestra «Esa ficha ya no está publicada…».

---

## 4. Mapa pantalla → API → datos

> Convenciones: todas las respuestas son JSON. Los POST de `/api/…` llevan `X-CSRFToken` y `Idempotency-Key` (UUID) y el cuerpo es un objeto JSON con solo los campos permitidos, sin claves repetidas ni NaN (`web/respuestas.py:20-50`). Las llamadas `/_allauth/browser/v1/…` las atiende **django-allauth headless** a través de `browser_endpoint` (`cuentas/api.py:114-159`) con CSRF y longitudes máximas (256 para contraseñas, 320 para el resto de textos). Tablas: nombres tal como están en `sql/el_chilito_base_completa.sql` (todas con prefijo del app: `datos_`, `huerto_`, `cuentas_`, `privacidad_`, `web_`, más las de allauth y Django). «Vista» = función Django que la atiende.

### 4.1 Arranque, sesión y acceso

| Método · URL | Pantalla(s) | Envía | Recibe | Vista Django | Tablas |
|---|---|---|---|---|---|
| `GET /` , `/index.html` | todas | — | `index.html` | `web/static_views.py:7-12` (`frontend`) | — |
| `GET /vistas/…`, `/modelos/…`, `/controladores/…`, `/favicon.svg` | todas | — | archivo estático | `static_views.py:14-19` (`resource`) | — |
| `GET /api/acceso/configuracion` | arranque (todas) | — | `{registrationAllowed, supportContact, legal:{termsVersion,privacyVersion,approved}, password:{minLength:15,maxLength:256,requirements[]}, code:{length:6,pattern,inputMode,expiresAfterSeconds:600,resendAfterSeconds:60,maxAttempts:3,maxResends:5}}`; fija cookie `csrftoken` | `cuentas/api.py:35-49` (`bootstrap`) | — (usa `CHILITO_CONTACTO_SOPORTE` y `local_registration_allowed`) |
| `GET /api/cuenta` | enrutador (`restore`), Mi cuenta, todas las privadas | cabecera opcional `X-Chilito-Sondeo` | `{status:'ready', session:{status,role,capabilities[],mfaRequired,profile{id,email,verified,status,firstName,lastName,alias,greeting,welcomePending}}, email, verified:true, gardenAssigned, …}`; 401 `unauthenticated`; 403 `verification-required` | `cuentas/api.py:52-67` (`profile`) → `datos/services.py:55-58,69` | `cuentas_usuario`, `account_emailaddress`, `auth_permission`/`cuentas_usuario_user_permissions`/`auth_group`, `mfa_authenticator`, `huerto_membresia` |
| `GET /api/acceso/verificacion` | `#verificar`, enrutador | — | `{status:'verification-required', email, expiresAt}` o 409 `verification-expired` | `cuentas/api.py:185-196` | `django_session` (estado de verificación en sesión) |
| `GET /_allauth/browser/v1/auth/session` | enrutador, segundo paso | — | estado de sesión allauth (`meta.is_authenticated`, `data.flows[]`) | allauth `SessionView` vía `browser_endpoint` (`config/urls.py:11`) | `django_session`, `cuentas_usuario` |
| `DELETE /_allauth/browser/v1/auth/session` | «Cerrar sesión», «Cancelar» del segundo paso | — | 401 con `is_authenticated:false` (éxito) | ídem (antes cierra sesiones técnicas: `cuentas/api.py:108-111`) | `django_session`, `datos_sesiontecnica` |
| `POST …/auth/login` | `#acceso` | `{email,password}` | 200 autenticado / 401 con flujos pendientes / 400 credenciales | allauth `LoginView` (`urls.py:12`) | `cuentas_usuario`, `account_emailaddress`, `cuentas_cuotas_acceso`, `django_session` |
| `POST …/auth/signup` | `#registro` | `{email,password,termsAccepted:true,privacyRead:true}` | 401 con flujo `verify_email` pendiente, o `{code:'registration-disabled'|'terms-required'|'privacy-required'|'mail-unavailable'}` | `cuentas/api.py:162-182` (`registration`) + allauth `SignupView` | `cuentas_usuario`, `account_emailaddress`, `account_emailconfirmation`/`cuentas_confirmacionregistrolocal`, `django_session` |
| `POST …/auth/email/verify` | `#verificar` | `{key}` | 200/401 con `meta.is_authenticated` | allauth `VerifyEmailView` | `account_emailaddress`, `django_session` |
| `POST …/auth/email/verify/resend` | `#verificar` | `{}` | 200 | allauth `ResendEmailVerificationCodeView` | `django_session` |
| `POST …/auth/password/request` | `#recuperar` | `{email}` | 200 / 503 `mail-unavailable` | allauth `RequestPasswordResetView` (`reset_mail=True`) | `cuentas_usuario` |
| `GET/POST …/auth/password/reset` | `#restablecer` | GET con cabecera `X-Password-Reset-Key`; POST `{key,password}` | 200 con `data.user.email` / 400 | allauth `ResetPasswordView` | `cuentas_usuario` |
| `POST …/account/password/change` | `#cuenta/contrasena` | `{current_password,new_password}` | 200 / 400 (`current_password`, `new_password`) | allauth `ChangePasswordView` (`verified_only`) | `cuentas_usuario` |
| `POST …/auth/code/confirm` | `#segundo-paso` | `{code}` | 200 / 401 | allauth `ConfirmLoginCodeView` | `django_session` |
| `POST …/auth/2fa/authenticate` | `#segundo-paso` | `{code}` | 200 / 400 | allauth mfa `AuthenticateView` | `mfa_authenticator` |
| `GET/POST …/auth/webauthn/authenticate` | `#segundo-paso` | GET; POST `{credential}` | opciones / resultado | allauth mfa `AuthenticateWebAuthnView` | `mfa_authenticator` |

### 4.2 Cookies, privacidad y perfil

| Método · URL | Pantalla(s) | Envía | Recibe | Vista | Tablas |
|---|---|---|---|---|---|
| `GET /api/privacidad/cookies` | aviso de cookies (global), Privacidad | cabecera `X-Chilito-Sondeo` | `{status:'ready', decided, statistics, privacyVersion, cookiesVersion}` | `privacidad/api.py:62-77` (`cookies`) → `privacidad/services.py:117` | `privacidad_sujetoprivacidad`, `privacidad_preferenciafinalidad`, `privacidad_decisionprivacidad`, `privacidad_documentoversion` |
| `POST /api/privacidad/cookies` | aviso de cookies, Privacidad | `{statistics:boolean}` | `{status:'accepted', statistics}` + cookie `chilito_preferencia` (180 días); borra `chilito_estadistica` si es «no»; 429 `rate-limited` | ídem → `services.py:126` | ídem + `privacidad_eventoprivacidad`, `privacidad_finalidadopcional` |
| `POST /api/estadisticas/seccion` | cada cambio de sección si hay consentimiento | `{section}` (`inicio`, `proyecto`, `prototipo`, `funcionamiento`, `huerto`, `panel_tecnico`, `mantenimiento`, `soporte`, `avisos`, `cuenta`, `privacidad`) | `{status:'accepted', counted}` + cookie `chilito_estadistica` (30 min) | `privacidad/api.py:80-95` (`section`) → `services.py:162` | `privacidad_conteonavegacion`, `privacidad_preferenciafinalidad` |
| `GET /api/privacidad/documentos/<kind>` (`privacidad`, `terminos`, `cookies`) | textos legales | cabecera `X-Chilito-Sondeo` | `{status:'ready', version, registered, text, html, draft}` o 404 | `privacidad/api.py:54-59` → `services.py:42` | lee `frontend/legales/*.html`; `privacidad_documentoversion` |
| `POST /api/privacidad/mis-datos` | Privacidad | `{}` | `{status:'accepted', data:{email,firstName,lastName,alias,createdAt,gardens[]}}` | `privacidad/api.py:49-52` → `services.py:247` | `cuentas_usuario`, `huerto_membresia`, `huerto_huerto`, `privacidad_eventoprivacidad`, `privacidad_sujetoprivacidad` |
| `POST /api/cuenta/perfil` | Perfil | `{firstName,lastName,alias}` | `{status:'accepted'}` | `privacidad/api.py:37-40` → `services.py:229` | `cuentas_usuario`, `privacidad_eventoprivacidad` |
| `POST /api/cuenta/bienvenida` | diálogo de bienvenida | `{firstName?,lastName?,alias?}` | `{status:'accepted'}` | `privacidad/api.py:43-46` → `services.py:236` | `cuentas_usuario` (`bienvenida_atendida_en`) |

### 4.3 Seguridad de la cuenta (segundo factor)

| Método · URL | Pantalla(s) | Envía | Recibe | Vista | Tablas |
|---|---|---|---|---|---|
| `GET …/account/authenticators` | Seguridad | — | lista `[{type:'totp'|'webauthn'|'recovery_codes', id, name, unused_code_count, total_code_count}]` | allauth `AuthenticatorsView` (`verified_only`) | `mfa_authenticator` |
| `GET/POST/DELETE …/account/authenticators/totp` | Seguridad | POST `{code}` | GET: `meta.secret`; POST: 200 y `meta.recovery_codes_generated`; DELETE | allauth `ManageTOTPView` | `mfa_authenticator` |
| `GET /api/cuenta/seguridad/totp-qr` | Seguridad | — | `{status:'ready', image:'data:image/svg+xml;base64,…'}` o 409 `no-pending-setup` | `cuentas/api.py:199-210` (`totp_qr`) | `django_session` (secreto pendiente) |
| `GET/POST …/account/authenticators/recovery-codes` | Seguridad | POST `{}` | `data.unused_codes[]` | allauth `ManageRecoveryCodesView` | `mfa_authenticator` |
| `GET/POST/DELETE …/account/authenticators/webauthn` (también `PUT`, sin uso) | Seguridad | POST `{name,credential}`; DELETE `{authenticators:[id]}` | `data.creation_options` / 200 | allauth `ManageWebAuthnView` | `mfa_authenticator` |
| `POST …/auth/reauthenticate` | Seguridad | `{password}` | 200 / 400 | allauth `ReauthenticateView` (`verified_only`) | `django_session` |
| `POST …/auth/2fa/reauthenticate` | Vinculación (diálogo) | `{code}` | 200 / 400 | allauth mfa `ReauthenticateView` | `mfa_authenticator`, `django_session` |
| `GET/POST …/auth/webauthn/reauthenticate` | Vinculación (diálogo) | POST `{credential}` | opciones / 200 | allauth mfa `ReauthenticateWebAuthnView` | `mfa_authenticator` |

### 4.4 Contacto, huerto de la persona usuaria y soporte

| Método · URL | Pantalla(s) | Envía | Recibe | Vista | Tablas |
|---|---|---|---|---|---|
| `POST /api/contacto` | ventana «Cuéntanos qué quieres saber» | `{name,email,message,website}` (**sin sesión**; CSRF y cuota) | `{status:'accepted'}`; 400 `invalid-input`; 429 `rate-limited`; 413; 503 | `web/api.py:213-226` (`contact`) → `web/services.py:81-90` → `datos/services.py:436-445` | `datos_consultaproducto`, `datos_avisocorreo` |
| `GET /api/huertos/actual` | Mi huerto, Panel técnico, Mantenimiento, Soporte | — | `{status:'ready', garden:{status:'waiting',name,updatedAt:null,plants[3]{id,zoneId,name,crop,reading},temperature,humidity,tank}, diagnosis:null}`; 403 `garden-unassigned` | `web/api.py:80-83` → `datos/services.py:62,376`, `diagnostico.py:104` | `huerto_membresia`, `huerto_huerto`, `huerto_zona` |
| `GET /api/huertos/actual/avisos?page=` | Avisos | `page` (1…10000) | `{status:'ready', items[], page, total}` | `web/api.py:84-87` → `services.py:386,348` | `huerto_aviso`, `huerto_zona`, `huerto_avisoleido` |
| `GET /api/huertos/actual/avisos/<id>` | Aviso (detalle) | — | `{status:'ready', notice}` | `web/api.py:88-92` | ídem |
| `POST /api/huertos/actual/avisos/<id>/lectura` | Aviso (detalle) | `{}` | `{status:'accepted', id, read:true, item, notice}` | `web/api.py:93-99` → `services.py:172` | `huerto_avisoleido` |
| `GET /api/huertos/actual/mantenimiento?page=` | Mi huerto, Panel técnico, Mantenimiento, Soporte | — | `{status:'ready', items:[{id,type,task,at,actor}], page,total}` | `web/api.py:100-104` → `services.py:110` | `datos_mantenimiento` (+ `datos_revisionmantenimiento` para el tipo vigente) |
| `POST /api/huertos/actual/mantenimiento` | Mi huerto, Mantenimiento | `{type}` (`refill, substrate, germination, harvest, inspection`) | `{status:'accepted', record}` | `web/api.py:100-104` → `services.py:96` | `datos_mantenimiento`, `datos_auditoria` |
| `GET /api/huertos/actual/solicitudes?page=` | Panel técnico (bitácora) | — | `{items:[{id,type,status,at}],page,total}` | `web/api.py:105-109` → `services.py:424` | `datos_solicitud` |
| `POST /api/huertos/actual/solicitudes` | Mi huerto, Panel técnico | `{type}` (`water, lamp-off, lamp-auto`) | `{status:'accepted', request}` | `web/api.py:105-109` → `services.py:180` | `datos_solicitud`, `datos_dispositivo`, `datos_auditoria` |
| `GET /api/soporte?page=` | Mi huerto (carga), Soporte | — | `{status:'ready', items:[caso]}` (caso = `{id,folio,device,user,incident,createdAt,permissionState,expiresAt,caseState,resolution,tokenRequestedAt,notices}`) | `web/api.py:110-115` → `services.py:415,400` | `datos_casosoporte`, `datos_permisosoporte`, `datos_resolucionsoporte`, `datos_dispositivo`, `datos_avisocorreo`, `datos_auditoria` |
| `POST /api/soporte` | Soporte | `{incident, consent:true}` | `{status:'accepted', permission:{token,ticket,folio,supportEmail,device,user,createdAt,expiresAt}}` (token solo una vez) | `web/api.py:110-115` → `services.py:214` | `datos_casosoporte`, `datos_permisosoporte`, `datos_auditoria`, `datos_avisocorreo` |
| `POST /api/soporte/<uuid>/revocar` | Soporte | `{}` | `{status:'accepted'}` | `web/api.py:116-117` → `services.py:238` | `datos_permisosoporte`, `datos_sesiontecnica`, `datos_auditoria` |
| `POST /api/vinculacion` | Vincular mi huerto | `{code}` | `{status:'linked'|'already-linked'|'rejected'|'limited', membership, garden:{name}}` | `web/api.py:134-136` → `datos/vinculacion.py:285` | `datos_codigovinculacion`, `huerto_membresia`, `huerto_huerto`, `datos_auditoria` |
| `GET /api/guias` | Mantenimiento | — | `{status:'ready', guides:[{key,question,answer,source}]}` | `web/api.py:152-155` → `datos/guias.py:106` | `datos_guiacuidado` |

### 4.5 Administración

| Método · URL | Pantalla(s) | Envía | Recibe | Vista | Tablas |
|---|---|---|---|---|---|
| `GET /api/admin/flota` | Telemetría de flota | — | `{status:'ready', nodes[≤100]{device,gardenId,connected:null,heartbeat:null}, metrics:null, trends:{soil:[],humidity:[]}}` | `web/api.py:118-119` → `services.py:371` | `datos_dispositivo` |
| `GET /api/admin/soporte?page=` | Consola remota | — | `{status:'ready', items:[caso], page,total}` | `web/api.py:120-121` → `services.py:419` | `datos_casosoporte`, `datos_dispositivo`, `datos_permisosoporte`, `datos_resolucionsoporte`, `datos_avisocorreo`, `datos_auditoria` |
| `POST /api/admin/soporte/<uuid>/solicitar-token` | Consola remota | `{}` | `{status:'accepted', notice, repeated}` | `web/api.py:170-171` → `services.py:255` | `datos_auditoria`, `datos_avisocorreo` |
| `POST /api/admin/soporte/<uuid>/resolver` | Consola remota | `{result,note}` | `{status:'accepted', case}` | `web/api.py:122-125` → `services.py:266` | `datos_resolucionsoporte`, `datos_permisosoporte`, `datos_sesiontecnica`, `datos_auditoria` |
| `POST /api/admin/soporte/<uuid>/abrir` | Consola remota | `{token}` (43 car.) | `{status:'accepted', session:{id,ticket,expiresAt,openedAt}}` | `web/api.py:172-176` → `services.py:285` | `datos_permisosoporte`, `datos_sesiontecnica`, `datos_auditoria` |
| `POST /api/admin/sesiones/<uuid>/accion` | Consola remota | `{action:'diagnostic'}` | `{status:'accepted', pins?, logs?, at?}` | `web/api.py:177-181` → `services.py:299` | `datos_sesiontecnica`, `datos_auditoria` |
| `POST /api/admin/sesiones/<uuid>/cerrar` | Consola remota, cerrar sesión | `{}` | `{status:'accepted'}` | `web/api.py:182-185` → `services.py:317` | `datos_sesiontecnica`, `datos_auditoria` |
| `GET /api/admin/mantenimientos?garden&state&task&since&until&page` | Mantenimientos | filtros | `{status:'ready', items[{id,type,task,at,actor,originalType,gardenId,garden,state,revision}],page,total,gardens[{id,name}]}` | `web/api.py:195-201` → `services.py:124,120` | `datos_mantenimiento`, `datos_revisionmantenimiento`, `datos_asignacionmantenimiento`, `huerto_huerto` |
| `POST /api/admin/mantenimientos` | Mantenimientos | `{gardenId,task}` | `{status:'accepted', record}` | `web/api.py:195-201` → `services.py:140` | `datos_mantenimiento`, `datos_auditoria` |
| `GET /api/admin/mantenimientos/<uuid>` | Mantenimientos (diálogo) | — | `{status:'ready', record, revisions[{number,kind,correctedType,editor,reason,at}]}` | `web/api.py:202-205` → `services.py:134` | `datos_mantenimiento`, `datos_revisionmantenimiento` |
| `POST /api/admin/mantenimientos/<uuid>/corregir` | Mantenimientos | `{task,reason,revision}` | `{status:'accepted', record}` | `web/api.py:206-208` → `services.py:163` | `datos_revisionmantenimiento`, `datos_auditoria` |
| `POST /api/admin/mantenimientos/<uuid>/anular` | Mantenimientos | `{reason,revision}` | ídem | `web/api.py:209-211` → `services.py:168` | ídem |
| `GET /api/admin/consultas?page&state` | Solicitudes del producto | `page`, `state` | `{status:'ready', items[],page,total}` | `web/api.py:126-129` → `services.py:446,470` | `datos_consultaproducto`, `datos_avisocorreo`, `cuentas_usuario` |
| `POST /api/admin/consultas/<uuid>/estado` | Solicitudes del producto | `{state}` | `{status:'accepted', inquiry}` | `web/api.py:130-132` → `services.py:455` | `datos_consultaproducto` |
| `GET /api/admin/vinculacion` | Vinculación | — (sin parámetros) | `{status:'ready', gardens[], pending[], recent[]}` | `web/api.py:137-140` → `vinculacion.py:199` | `huerto_huerto`, `datos_dispositivo`, `huerto_membresia`, `datos_codigovinculacion` |
| `POST /api/admin/vinculacion/emitir` | Vinculación | `{garden,email,delivery}` | `{status:'issued',binding,code?}` o `{status:'refused',reason}`; 403 `reauthentication-required` | `web/api.py:141-143` → `vinculacion.py:136` | `datos_codigovinculacion`, `huerto_membresia`, `cuentas_usuario`, `account_emailaddress`, `datos_auditoria`, `datos_avisocorreo` |
| `POST /api/admin/vinculacion/<uuid>/revocar` | Vinculación | `{}` | `{status:'revoked', binding}` | `web/api.py:144-146` → `vinculacion.py:187` | `datos_codigovinculacion`, `datos_auditoria` |
| `GET /api/admin/guias` | Guías de cuidado | — | `{status:'ready', guides[]}` | `web/api.py:156-160` → `guias.py:122` | `datos_guiacuidado`, `cuentas_usuario` |
| `POST /api/admin/guias` | Guías de cuidado | `{question,answer,order,sourceName,sourceUrl}` | `{status:'accepted', guide:{id,key,state,version}}` | ídem → `guias.py:130` | `datos_guiacuidado`, `datos_auditoria` |
| `POST /api/admin/guias/<uuid>/editar` | Guías de cuidado | `{…,version}` | ídem | `web/api.py:161-163` → `guias.py:139` | ídem |
| `POST /api/admin/guias/<uuid>/publicar` | Guías de cuidado | `{version}` | ídem | `web/api.py:164-166` → `guias.py:163` | ídem |
| `POST /api/admin/guias/<uuid>/retirar` | Guías de cuidado | `{version}` | ídem | `web/api.py:167-169` → `guias.py:168` | ídem |

**Idempotencia y cuotas (todas las `POST /api/…` con sesión):** `Idempotency-Key` obligatorio (UUID); recibos en `web_idempotencia` (`web/models.py`); cuota de 60 escrituras/minuto por persona (15 en `/soporte/` y `/sesiones/`); respuestas 429 `rate-limited`, 409 `idempotency-conflict`.
**Sin cambio detectado en la sección 4:** `/api/admin/…` exige capacidad y segundo factor en cada llamada; los endpoints `/api/huertos/actual/*` y `/api/soporte*` operan siempre sobre el huerto de la membresía activa (`principal` si existe) de la sesión, nunca sobre un id enviado por el cliente.

---

## 5. Flujos de navegación

### 5.1 Visitante

1. **Entra a `/`** (hash vacío) → portada con hero; el aviso «Tu privacidad y las cookies» aparece si no hay decisión → «Aceptar» / «Rechazar» / «Configurar».
2. **Explora:** menú o pie → `#el-proyecto`, `#prototipo`, `#consiguelo`, `#como-funciona` (scroll, sin recargar); `#terminos` / `#privacidad` / `#cookies` (documentos; hoy «[PENDIENTE: documento en redacción]»).
3. **Pide información:** `#consiguelo` → «Quiero más información» → ventana → «Enviar mensaje» → «Recibimos tu mensaje. Te responderemos a tu correo.».
4. **Crea cuenta:** «Iniciar sesión» → `#acceso` → «Crear cuenta» → `#registro` (acepta términos y aviso) → `#verificar` (código de 6 dígitos por correo, 10 min, reenvío cada 60 s) → «Correo verificado» → botón «Mi huerto» → `#huerto`.
5. **Inicia sesión:** `#acceso`:
   - credenciales incorrectas → mensaje en la misma pantalla;
   - correo sin verificar → `#verificar`;
   - segundo paso pendiente → `#segundo-paso` (código por correo, app/recuperación, o llave) → éxito → `#huerto` o panel admin; «No tengo mi app ni mis códigos» → `#sin-acceso` → «Volver al inicio de sesión»;
   - éxito → bienvenida (primera vez) y `#huerto`.
6. **Recupera contraseña:** `#acceso` → «¿Olvidaste tu contraseña?» → `#recuperar` → «Revisa tu correo» → enlace del correo `#restablecer?key=…` → nueva contraseña → «Contraseña actualizada» → `#acceso`.
7. **Intenta abrir una ruta privada sin sesión** (`#huerto`, `#admin/…`, etc.) → `#acceso` con «Inicia sesión para continuar.».
8. **Con sesión activa:** en la portada «Iniciar sesión» pasa a «Ir a mi panel»; `#acceso`/`#registro` redirigen al panel.

### 5.2 Persona usuaria

```
#acceso ──ok──► [bienvenida (1ª vez)] ──► #huerto
                                           │ 403 garden-unassigned
                                           ▼
                              «Vincular mi huerto» (código de 26 caracteres) ──ok──► recarga #huerto
menú: Mi huerto │ Panel técnico │ Mantenimiento │ Soporte técnico │ Mi cuenta     (campana → Avisos)
```
- **Mi huerto** → «Registrar recarga/cosecha» (mensaje), «Apagar lámpara» (diálogo → solicitud), «Ver guía de cuidado» → `#mantenimiento/sustrato` (abre la ficha), «Solicitar soporte técnico» → `#soporte`.
- **Panel técnico** → rango 1 h/24 h/7 días; «Actualizar bitácora»; «Solicitar riego» (diálogo).
- **Mantenimiento** → registrar tareas, ver historial (`#mantenimiento/historial`), guías.
- **Soporte técnico** → elegir incidente → «Reportar y generar token temporal» → diálogo con casilla de consentimiento → token visible una vez → «Copiar token» / «Escribir a soporte» → «Revocar autorización».
- **Avisos** → filtrar → «Ver detalle» → «Marcar como leído» → «Todos los avisos».
- **Mi cuenta** → Perfil («Cambiar datos», «Cambiar contraseña» → `#cuenta/contrasena` → «Mi cuenta»), Seguridad (activar app/llave/códigos), Privacidad (consultar datos, estadísticas). «Cerrar sesión» → confirmación → `#acceso`.
- **Redirecciones automáticas:** sesión vencida (401 en cualquier llamada) → `#acceso` con «Tu sesión ha vencido. Inicia sesión de nuevo.»; usuaria que abre `#admin/…` → `#huerto`; segundo paso pendiente en medio de la sesión → `#segundo-paso`; sin huerto → versión bloqueada con «Vincular mi huerto» (no redirige); `#asistente` → `#huerto`; `#huerto/avisos` → `#avisos`; `#derechos-arco` → `#privacidad`.

### 5.3 Administración

```
#acceso ─► [segundo paso obligatorio para operar] ─► primer destino permitido (#admin/flota | soporte | mantenimientos | solicitudes | comercial | vinculacion | guias)
  mfaRequired (sin app ni llave) ─► #cuenta/seguridad  (alerta «Activa un método para usar el panel»)
```
- **Entrada:** `AppModel.panelHome` / `adminHome`: primer destino con capacidad (orden: flota, soporte, mantenimientos, solicitudes, comercial, vinculación, guías); si no tiene ninguno, `#huerto` (que luego la redirige de vuelta: ver 6).
- **Telemetría de flota** → «Actualizar dispositivos»; accesos a «Gestión de registros», correo y «Solicitudes del producto».
- **Consola remota** → «Abrir» caso → «Solicitar token a la persona usuaria» → (la persona pega el token en un correo a soporte) → «Validar token» → diagnóstico (sin dispositivo conectado) → «Cerrar sesión técnica» o «Resolver caso» (definitivo). Salir de la pantalla cierra la sesión técnica.
- **Mantenimientos** → «Registrar» → filtros → «Ver» → «Guardar corrección» / «Anular registro».
- **Solicitudes del producto** → filtro → «Responder en Gmail» (pestaña nueva) → volver → «Marcar como atendida» / «Archivar».
- **Vinculación de huertos** → «Emitir código» (si el 2.º factor tiene más de 5 min: diálogo de reautenticación → se repite) → dictar/copiar código → «Revocar» si hace falta.
- **Equipos y ventas** → borradores locales (nada se guarda); «Abrir Vinculación de huertos».
- **Guías de cuidado** → «Nueva ficha» → guardar borrador → «Publicar».
- **Redirecciones automáticas:** admin en ruta de usuaria (salvo `#cuenta…`) → su primer destino; destino sin capacidad → primer destino permitido; sesión vencida (15 min de inactividad en admin según `politicas.py`) → `#acceso`; admin sin factor fuerte → `#cuenta/seguridad`; «Mi cuenta» es el único destino de usuaria permitido a un admin.

---

## 6. Pendientes y huecos

### 6.1 Solo existe en la interfaz (no se guarda en ninguna parte)

| Qué | Dónde | Efecto |
|---|---|---|
| Borradores de **equipo** y de **venta**, filtros de inventario/ventas/periodo, «Relación preparada en esta visita» | `CommerceModel.create` (`modelos/administracion.js:197-218`) | Se pierden al recargar o salir (`dispose`). No hay endpoint. |
| **Frase de bienvenida** aleatoria de «Mi huerto» | `modelos/comun.js:78-80` | Una por visita, calculada en el navegador. |
| Token de soporte emitido | `UserGardenService.active` (`modelos/huerto.js:77,127,148`) | Solo en memoria; tras recargar no se recupera. |
| Código de vinculación emitido (admin) | `BindingViews.reveal` | Solo en el DOM; desaparece al salir. |
| Fichas de guías abiertas, filtro de avisos, rango del histórico, edición de perfil sin guardar, selección de estadísticas sin guardar | controladores | Estado en memoria de la pantalla. |
| Lo escrito en la ventana de contacto | formulario | Se conserva mientras la página no se recargue (solo se limpia al enviar con éxito). |
| Preferencia del menú | — | «Preferencia de esta visita: no se guarda» (`administracion.js:217`). |

### 6.2 Pantallas o partes sin datos reales

| Hallazgo | Evidencia |
|---|---|
| **Ninguna lectura de sensores llega a la interfaz**: humedad del sustrato, ADC, temperatura, humedad relativa, nivel del depósito, Wi-Fi/MQTT, histórico. | `garden_projection` devuelve `status:'waiting'`, todas las lecturas `missing`, `tank unknown`, `updatedAt:null` (`datos/services.py:376-384`); el modelo fija `soil`, `connection`, `history` a vacío (`modelos/huerto.js:106,131`). |
| **Resumen de tu huerto (diagnóstico)** siempre en su texto de relleno. | `_productor()` devuelve `None` (`datos/diagnostico.py:99-101`). |
| **Telemetría de flota** sin métricas, sin series, sin conexión/heartbeat; tabla de correlaciones vacía; métricas de «evaluación de IA» sin fuente. | `fleet_projection` (`services.py:371-374`). |
| **Diagnóstico remoto** sin dispositivo. | Texto de la propia pantalla y `technical_action`. |
| **Solicitudes de riego/lámpara** nunca se confirman: estado permanente «Sin confirmación». | `modelos/huerto.js:129`, `datos_solicitud.estado` default `pending`. |
| **Equipos y ventas** entero es maqueta. | Sin endpoints en `config/urls.py`. |
| **Avisos** sin generador. | `huerto/models.py` docstring de `Aviso`. |
| **Textos legales** vacíos. | `frontend/legales/*.html` (solo comentario). |
| **Asistente de IA**: «Previsto». | `publico.js:227`, pie, `AppViews.assistant()` sin uso (`comun.js:148`, ruta `#asistente` redirige). |

### 6.3 Botones o textos sin función efectiva, relleno o inalcanzables

- «Control remoto no disponible. Esperando conexión del equipo.» (`huerto.js:98`): **inalcanzable** (`canControl` siempre `true`).
- Estados `ready`, `stale`, `offline`, `invalid` del huerto y mensajes `offline`/`low-water` de las solicitudes: el backend nunca los produce.
- Selector de periodo (1 h / 24 h / 7 días): cambia el estado del botón y recarga, pero el servidor no entrega histórico.
- «Capacidad del depósito: 19 L», «Sensor capacitivo v1.2», «SHT31»: texto fijo, no dato.
- `wrong-report` (consola remota): mensaje definido, sin productor.
- `PUT` de `webauthn` y `GET/POST /auth/reauthenticate` por contraseña: el segundo existe y se usa en Seguridad; el primero no se usa.
- `AuthConfig.password.requirements`: recibido del servidor pero la UI usa sus propios textos de ayuda.
- Texto de ayuda «código de 6 dígitos» escrito a mano en `#verificar` en lugar de usar `config.code.length`.
- «Gestión administrativa» en Telemetría de flota duplica lo que ya está en el grupo «Gestión» del menú.
- `AppModel.adminHome` devuelve `'huerto'` si no hubiera destino permitido, pero no puede ocurrir: las 6 capacidades de `CAPS` (`datos/services.py:20`) tienen todas destino en el menú, y el rol `admin` solo existe con al menos una.
- Mensaje de registro: «Este correo no está autorizado para la prueba local…» menciona un entorno de pruebas al usuario final.

### 6.4 Diferencias entre lo que muestra la interfaz y lo que devuelve el backend

| Interfaz espera | Backend entrega |
|---|---|
| `GET /api/admin/flota`: `nodes[].user`, `metrics.{reporting,total,soilHumidity,evaporation,hardwareAlerts,perliteEvaporation,sensorLife,pumpOrders}`, `correlations[]`, `at` | `nodes[].{device,gardenId,connected:null,heartbeat:null}`, `metrics:null`, sin `correlations` ni `at`. |
| `GET /api/huertos/actual`: estados variados de `garden.status`, lecturas válidas, `diagnosis` con reglas | Solo `status:'waiting'` y lecturas `missing`; `diagnosis:null`. |
| `permission.supportEmail` ignorado | Backend lo envía; el frontend usa `supportContact` de `/api/acceso/configuracion`. |
| `POST /api/admin/soporte/<id>/abrir` con token no válido/vencido → mensaje específico | El servidor responde 403 `access-denied`, que la UI traduce a «Tu cuenta no tiene acceso a esta operación.» (engañoso). |
| Lista de mantenimientos admin con paginador | El servidor pagina (25); la UI solo pide la página 1 y no muestra paginador. |
| Retirada de la «Revocar autorización» con confirmación | No hay diálogo; el servidor revoca inmediatamente. |
| Filtro `task` de mantenimiento admin | Aceptado por `maintenance_filters` (`web/api.py:186-194`). Coincide. |
| Secciones de estadísticas | Coinciden: `PrivacyModel.sectionOf` (`modelos/comun.js:14-18`) produce `inicio, proyecto, prototipo, funcionamiento, huerto, panel_tecnico, mantenimiento, soporte, avisos, cuenta, privacidad`, igual que la lista cerrada `ConteoNavegacion.SECCIONES` (`privacidad/models.py:189-191`). El fragmento «Aviso de privacidad» no cuenta como `privacidad` salvo `#cuenta/privacidad`. |
| Tablas con `datos_asignacionmantenimiento` administradas «por el propietario» | No hay pantalla para asignar huertos a administradores de mantenimiento (se hace por SQL: `sql/designar_administrador.sql`). |

### 6.5 Observaciones de calidad para el rediseño

1. Las acciones destructivas o de efecto inmediato sin confirmación: «Desactivar» app, «Quitar» llave, «Generar códigos nuevos», «Revocar autorización», «Resolver caso», «Anular registro», «Publicar»/«Retirar» guía, «Archivar» consulta.
2. No hay paginación visible en Mantenimientos (admin), ni búsqueda en ninguna lista.
3. Los selectores y campos del panel son oscuros sobre tarjetas crema (ver 1.6 #7).
4. Los avisos de éxito/fracaso son cajas en línea arriba del contenido (no «toasts»); solo las cookies tienen un toast.
5. La portada no tiene llamada a la acción en el hero; «Consíguelo» es el único formulario público.
6. El aviso de cookies y el pie existen solo en público; el panel no ofrece «Configurar cookies» salvo en Mi cuenta → Privacidad.
7. Las tres pieles (oscura/clara/crema) conviven; cualquier rediseño debe partir de un único archivo de tokens (ver 1.1) y eliminar las capas `!important`.

---

## Anexo A. Comprobación de cobertura

- **Rutas de 0.2 → fichas:** Inicio, El proyecto, Prototipo, Consíguelo (+ ventana), Cómo funciona, Términos, Privacidad, Cookies (3.A); Acceso, Registro, Verificar, Recuperar, Restablecer, Segundo paso, Sin acceso, Bienvenida (3.B); Mi huerto, Panel técnico, Mantenimiento (+guías), Soporte técnico, Avisos (lista y detalle), Mi cuenta (Perfil, Seguridad, Privacidad), Cambiar contraseña, Sin huerto/Vincular (3.C); Flota, Consola remota, Mantenimientos, Solicitudes, Vinculación, Equipos y ventas, Guías (3.D). Los alias/retiradas (`#derechos-arco`, `#asistente`, `#huerto/avisos`, `#admin` desconocido) se explican en 0.2 y 5.
- **Elementos globales (sección 2):** encabezado público, marco privado, pie, aviso de cookies, sesión vencida, carga, errores.
- **Endpoints de la sección 4:** cada uno aparece en alguna ficha (ver «Datos»/«Botones» de la ficha de su pantalla).

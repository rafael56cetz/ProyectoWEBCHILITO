# Informe · Diseño final de los dashboards

Rama: `diseno-final` (sobre `main`, commit `7bc0853`). Alcance: panel de la persona usuaria y de administración. Sin cambios de backend, endpoints, textos funcionales ni comportamiento.

## 1. Sistema visual (todo en `tokens.css`)

- **Paleta:** tinta `#1b231d` (15,2:1 sobre la tarjeta), texto suave `#4b423a` (9,2:1), acento verde `#2f6a48` (6,0:1; blanco sobre él, 6,4:1). Estados verde, ámbar, rojo y gris desaturados, texto ≥ 7:1, siempre con punto y texto.
- **Vidrio en tres niveles:** base (listas y tablas), tarjeta (KPI, fichas, avisos) y flotante (barra superior, diálogos, calendario, listas desplegables). **`backdrop-filter` solo en la capa flotante** (barra superior, menú lateral, desplegable, diálogos, calendario, aviso de cookies). Las tarjetas del contenido son vidrio sin desenfoque (fondo translúcido, borde de 1 px, brillo superior y sombra difusa).
- **Escalas únicas:** espacios 4/8/12/16/24/32 (`--esp-1…6`), radios (`--radio-sm`, `--radio-campo`, `--radio-tarjeta`, `--radio-menu`, `--radio-boton`), medidas (`--kpi-alto`, `--campo-alto`, `--barra-alto`, `--filtro-ancho-min`).
- **Fondo:** de 8 a 4 degradados, más suaves.

## 2. Componentes (`panel.css`, capa «Componentes del panel»)

Barra superior de vidrio · KPI (ícono + etiqueta, valor en una línea de tamaño fluido, dato secundario a 2 líneas; 4 columnas en escritorio, 2 en tablet y móvil) · tabla (en tarjetas bajo 1024 px, con `data-label`) · barra de filtros en rejilla (Buscar a 2 columnas, acciones al final) · campo de fecha de una pieza · paginación (oculta sin resultados) · insignias · aviso único con tono (también en acceso) · estado vacío `AppViews.empty` · control segmentado único (pestañas de cuenta, filtros de avisos, rangos; se desplaza con difuminado al borde) · pestañas con acción principal (`tabs-bar`) · fila de aviso de una sola estructura · fichas de planta · bandeja de la consola.

## 3. JavaScript tocado (presentación)

- `comun.js`: `AdminTableViews.table` (`data-label`, `title`), `pager` (nada si `total` es 0), `tabs` (acción opcional), `AppViews.empty`, fila de avisos, se quitó el ícono de «Datos de la cuenta».
- `huerto.js`: agregación de lecturas por intervalo antes de dibujar (1 min en 1 h, 10 min en 24 h, 1 h en 7 d, 6 h en 30 d), rangos con botón de ícono «Actualizar» aparte, un solo «Solicitar revisión técnica».
- `administracion.js`, `equipos.js`: estados vacíos y pestañas con acción.
- `controladores/administracion.js`: el desplegable del menú pasa de 768 a 1024 px (única línea de comportamiento).
- `pruebas.cjs`: prueba de la agregación (5 000 lecturas → ≤ 145 puntos).

## 4. `!important` antes → después (apariencias)

| Archivo | Antes | Después |
|---|---|---|
| `apariencia.css` | 233 | 192 |
| `base.css` | 414 | 405 |
| `panel.css` | 145 | 113 |
| `navegacion.css` | 108 | 107 |
| `acceso.css` / `cookies.css` | 25 / 2 | 25 / 2 |
| **Total** | **927** | **844** |

Los nuevos son pocos e intencionales: relleno superior del contenedor (`base.css` lo fuerza), radio de la bandeja de la consola y botones de los controles segmentados (la regla global de botones usa `!important`).

## 5. Defectos previos corregidos

- Declaración suelta en `apariencia.css` (sin selector) que anulaba `.care-guides`.
- Reglas de `[data-maint-filter]` y `[data-maint-create]` que nunca se aplicaban (el JS no genera esos atributos).
- Una regla de color con `!important` impedía ver los tonos de las insignias.
- `border-radius:… !important` en todos los `<button>` deformaba el botón del calendario.

## 6. Verificación

- `node frontend/pruebas/pruebas.cjs`: 7 suites en verde.
- Capturas con Chrome headless de páginas armadas con los CSS y las vistas reales a 375, 768, 1024 y 1366 px: usuario (Mi huerto, tarjetas, avisos, cuenta, panel técnico) y administración (Flota, Consola, Mantenimientos, Ventas, Resumen, Administradores, Consentimientos, Inventario).
- break-ui (nombres de 130 caracteres sin espacios, emoji, árabe y japonés, correos de 180 caracteres, cifras enormes, 123 456 filas, tablas vacías): sin desborde horizontal de la página en ningún ancho; solo se desplazan los controles segmentados y el contenedor de tabla, por diseño.

## 7. Pendiente / no comprobado

- **No se comprobó en un navegador con sesión real.** El fallo de composición (zona blanca al desplazar) se atacó quitando todo `backdrop-filter` del contenido; falta confirmarlo con desplazamiento real.
- No se renderizaron con datos: Soporte, Mantenimiento del usuario, las 4 pestañas de Mi cuenta, ficha de planta, Mis huertos, aceptar textos legales, Solicitudes, Guías, Textos legales y Equipos (lista y ficha). Usan los mismos componentes y se revisaron por CSS, pero no por captura.
- Consola en móvil: el detalle sigue bajo la bandeja (recibe el foco y se desplaza hasta él); no abre una pantalla aparte.
- Etiquetas de KPI y valores largos se cortan con elipsis sin tooltip.
- Siguen ~844 `!important`, sobre todo en `base.css` y `apariencia.css`.

## 8. Ronda de ajustes del usuario (mvc.11)

- KPI: etiqueta hasta 2 líneas sin elipsis; valor fluido (hasta 28 px en escritorio, 24 px en móvil) en una línea.
- Panel técnico: el botón de actualizar va junto al título «Histórico de lecturas»; los 4 rangos caben solos.
- Mi huerto: «Solicitar revisión técnica» ocupa la fila completa; «Resumen de tu huerto» lleva ícono y título en la misma línea.
- Formularios: una sola regla de etiqueta (13 px, 600) para los formularios del panel; accesos rápidos del mismo alto.
- Folio de caso (`CS-XXXXXXXX`) sin partir: `AppViews.conFolio` en avisos y `<span class="folio">` en los encabezados de caso (usuario y consola).
- Ficha de planta: el título no repite el nombre de fábrica; las tarjetas apiladas tienen 24 px entre sí en ambos roles.
- Se quitó la propiedad estándar `line-clamp` (Chrome la convierte en `flow-root` y rompe el recorte a 2 líneas); queda `-webkit-line-clamp`.
- Pruebas nuevas: folio escapado y sin partir; título de planta con y sin nombre propio.

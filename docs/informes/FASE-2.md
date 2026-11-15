# INFORME FASE 2 · Sistema visual unificado

## 1. Resumen
Todas las variables de diseño viven ahora en `frontend/vistas/estilos/tokens.css` (zonas pública, acceso y panel), que se carga
primero. El panel conserva su aspecto (fondo crema, menú verde, tarjetas de vidrio claro; portada y acceso en vidrio oscuro) y
se corrigen C1–C9: botones de vidrio en tres variantes más la compacta, deshabilitado al 45 %, campos claros, insignias en
cápsula con cuatro tonos, aviso flotante y confirmación estándar (`mostrarAviso`, `confirmar`), menos `backdrop-filter`
interno y campana también para administradores. `!important`: **1046 → 967**.

## 2. Archivos
**Creado**
- `frontend/vistas/estilos/tokens.css`: único lugar con variables (pública, acceso, panel).

**Modificados**
- `frontend/index.html`: carga `tokens.css` primero; versión de recursos `mvc.3` → `mvc.4`.
- `estilos/base.css`: `:root` sin variables; deshabilitado = misma variante al 45 %; quita blur interno; estilos del aviso flotante; usa tokens de z-index, radios, duraciones y blur.
- `estilos/apariencia.css`: quita la piel oscura muerta del panel; reescribe campos (C3), botones (C1/C2) e insignias (C4).
- `estilos/panel.css`, `acceso.css`, `navegacion.css`, `cookies.css`: variables movidas a tokens; reglas contradictorias o duplicadas eliminadas (`[data-maint-revise]`, pastel de «Peligro» en consola, opacidades de deshabilitado, `.logout-dialog`, `.cookies-confirmacion`).
- `modelos/comun.js`: `AvisoModel` (tipos, ícono y permanencia del aviso).
- `vistas/comun.js`: `mostrarAviso`, `confirmar`, ícono `alert`, textos de la confirmación de cerrar sesión, campana para administradores; se borra el diálogo propio de cerrar sesión.
- `vistas/publico.js`: el aviso de cookies «Preferencias guardadas» usa `mostrarAviso`.
- `vistas/cuenta.js`, `controladores/cuenta.js`: confirmación al desactivar la app, quitar una llave y generar códigos nuevos.
- `controladores/administracion.js`: cerrar sesión usa `confirmar` (se borran `openLogout`, `closeLogout`, `confirmLogout` y su estado).

**Eliminados**: solo código reemplazado (ver arriba). Ningún archivo borrado.

## 3. Líneas
`git diff --shortstat -- frontend`: 13 archivos, +322 / −429 (más `tokens.css` nuevo, sin contar en el diff).

## 4. Endpoints
Ninguno nuevo, cambiado ni eliminado.

## 5. Seguridad
| Requisito | Cómo se cumple | Verificación |
|---|---|---|
| ASVS V3 (sin estilos ni scripts en línea nuevos; CSP intacta) | Aviso y confirmación se estilan con clases; no se tocó `middleware.py` ni la CSP | Revisión del diff (`grep` de `style=` y `<script` nuevos: ninguno). Las capturas usan un servidor estático sin CSP, así que **no prueban** la CSP; el responsable la comprobó en `localhost:8780` con sesión real: consola sin errores de CSP |
| ASVS V1/V3 (salida segura) | `mostrarAviso` y `confirmar` rellenan con `textContent`; el nombre de la llave llega al texto por `textContent`. Los únicos `innerHTML` son SVG propios y una plantilla fija | Revisión del diff |
| MVC del proyecto | Los controladores no escriben el DOM; los textos están en las vistas | `node frontend/pruebas/pruebas.cjs`: suite MVC en verde |

## 6. Comprobaciones
- `node frontend/pruebas/pruebas.cjs`: 6 de 7 suites en verde. Falla `comercial` (`allowedAdmin(['vincular_huertos'])` ya no devuelve `admin/comercial`). **Falla igual antes de empezar la fase**: la suite comercial de `pruebas.cjs` falla por la desactivación de la fase 1 (la capacidad cambió) y se rehace en la fase 5. No se tocó.
- `!important` (apariencias): antes → después: `base` 422 → 416, `apariencia` 327 → 254, `panel` 149 → 149, `navegacion` 108 → 108, `acceso` 25 → 25, `comercial` 13 → 13, `cookies` 2 → 2, `tokens` 0. **Total 1046 → 967.** (Los conteos del plan, 758, eran líneas; aquí son apariciones, como en el inventario.)
- Comparación visual antes/después en escritorio (1366 px) y móvil (375 px): portada (con y sin aviso de cookies), acceso, registro, Mi cuenta (perfil, seguridad, privacidad, contraseña), Mi huerto (estado «se está actualizando»), guías de Mantenimiento, administración (solicitudes, guías, Mi cuenta), menú móvil abierto de usuario y de administración, las tres confirmaciones de Seguridad, la de cerrar sesión y el aviso flotante. Método: copia del frontend sin cambios contra la copia nueva, con la API simulada en el navegador (Chrome sin cabeza), diferencia por píxeles y revisión de las capturas.

## 7. Diferencias visuales y pendientes (nada se oculta)
**Diferencias que sí son C1–C9**
- C1: los botones `.compact` pasan de 44 px a 38 px en el panel (antes la regla del panel los forzaba a 44 px). «Primaria» y «Peligro» son un degradado translúcido (92 % de opacidad) en lugar de sólido.
- C2: «Guardar preferencias» deshabilitado se ve verde al 45 %, ya no gris.
- C3: campos de contraseña, de llave y filtros del panel pasan de verde oscuro a vidrio claro; el foco de los campos pasa de naranja a verde.
- C4: las insignias de solicitudes y guías son cápsulas de color (verde, ámbar, rojo y gris).
- C9: la campana aparece para administradores.

**Diferencias que NO son C1–C9** (decisiones 1 a 4 aprobadas por el responsable; las 5 y 6 se informan sin objeción)
1. Los botones del panel **ya no llevan `backdrop-filter`** (C7 lo pide para elementos internos y C1 dice «con blur»; elegí C7: sobre una tarjeta ya desenfocada no se nota y cuesta pintar). El vidrio viene del relleno translúcido y el reflejo superior. Se conserva el blur de los botones del menú lateral porque sin él pierden su verde saturado (se veía gris).
2. El botón «Iniciar sesión» de la portada cambió de forma casi imperceptible (0,05 % de la captura) al quitarle el blur interno del encabezado.
3. Aviso de cookies: el aviso «Preferencias guardadas» ahora es de la misma familia que el resto (abajo a la derecha; centrado en móvil) en vez de una píldora centrada.
4. Se añadió un ícono propio `alert` (triángulo) a `icons`, para el aviso de error. Sin librería de íconos.
5. Se subió la versión de los recursos de `mvc.3` a `mvc.4` para evitar CSS en caché.
6. La confirmación de cerrar sesión ya no muestra «Cerrando sesión…» dentro del diálogo; si falla, sale un aviso de error.

**Pendientes**
- La campana del administrador apunta a `#avisos`, pero el enrutador redirige a un administrador fuera de esa ruta (`enrutador.js`). Queda sin contador y sin destino útil hasta la fase 4, como pide el prompt. No toqué el enrutador ni permisos.
- Hallazgo previo: en el panel `--garden-green` resuelve a blanco (restos de la piel oscura), por lo que la línea de la gráfica del Panel técnico y algunos íconos de Mi huerto salen blancos sobre crema. Conservé el valor para no cambiar lo visible; las pantallas se rehacen en las fases 3 y 4.
- Pantallas con datos reales (Mi huerto, Panel técnico, Soporte, Mantenimiento y Avisos del usuario; flota, soporte y mantenimientos del administrador) responden 503 desde la fase 1: solo pude comprobar su estado «Esta sección se está actualizando».
- Recorrido manual real hecho por el responsable en `localhost:8780`: sin errores de CSP en la consola.
- Quedaron sin variable los valores únicos (no repetidos) de sombras y colores sueltos; la limpieza de `!important` y de reglas duplicadas del resto de `base.css` es de la fase 7.

## 8. Cómo probarlo a mano
1. Ctrl+F5 en `http://localhost:8780` (los recursos cambiaron a `mvc.4`).
2. Portada y acceso: deben verse igual. Aviso de cookies: «Aceptar» muestra el aviso flotante «Preferencias guardadas».
3. Con una cuenta de usuario: Mi cuenta › Seguridad: «Desactivar», «Quitar» y «Generar códigos nuevos» piden confirmación (Cancelar y Esc no ejecutan; «Quitar» y «Desactivar» van en rojo). «Cerrar sesión» pide confirmación en escritorio y móvil.
4. Campos de Mi cuenta y de contraseña en vidrio claro; en el acceso siguen oscuros.
5. Con una cuenta de administración: campana visible junto al perfil; Solicitudes y Guías con insignias de color y botones de 38 px.
6. Reducir el tamaño a 375 px: menú, tarjetas y confirmaciones siguen bien.

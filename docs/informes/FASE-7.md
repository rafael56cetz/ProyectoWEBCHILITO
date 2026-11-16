# Informe de fase 7 · Limpieza, verificación y documentación

Rama: `fase-7-cierre` (sobre `fase-6-admin-adaptada`, commit `8e0ea7e`).

## 1. Resumen

Se corrigieron las dos fallas de la prueba manual de la fase 6 (tendencias de flota con un solo punto y consultas repetidas del contador de avisos), se cerró el hueco de dos textos sin escapar, se renombró la clave de idempotencia, se borraron los tres HTML legales y las reglas CSS sin uso, y se reescribió el inventario de la interfaz. Se añadió la matriz de seguridad. **No se redujo el uso de `!important` de forma apreciable** (ver §3): sin un navegador que compare pantalla por pantalla no pude garantizar «ningún cambio visual», así que no lo hice. **No se probó en un navegador ni se comparó nada visualmente.**

## 2. Archivos

Sin archivos nuevos salvo este informe y `docs/MATRIZ-SEGURIDAD-v2.md`.

Correcciones:
- `frontend/vistas/huerto.js`: `lineChart` dibuja la gráfica desde un punto (antes exigía dos). El mismo cambio vale para las gráficas de telemetría de la persona. Además, la etapa de la planta y el origen del último riego, cuando no están en la tabla de textos, ahora se escapan.
- `frontend/controladores/administracion.js`: `refreshBell` no repite la consulta si hay una en curso ni dentro de 5 s (estado compartido entre montajes de `AppController`); las llamadas tras leer avisos fuerzan la consulta porque el número cambió. El intervalo de 60 s no cambia.
- `frontend/pruebas/pruebas.cjs`: prueba de un punto y de cero puntos en la flota; prueba de etapa y origen escapados.

Renombre: `CHILITO_SUPPORT_KEY` → **`CHILITO_IDEMPOTENCIA_SECRETO`** en `config/settings/base.py`, `web/services.py`, `tools/generar_sql_instalacion.py` y `tests/test_configuracion_despliegue.py`. No había ejemplo de `.env` ni documentación vigente que lo nombrara (los informes 4 y 5 se dejan como estaban). Sin alias del nombre viejo.

Eliminado:
- `frontend/legales/*.html` (3 archivos): nada los leía; los textos salen de la base. Se corrigieron `README.md` (tabla, sección de edición de textos y la «Propuesta» de la fase anterior, ya cumplida; se conservaron las decisiones pendientes), `backend/tools/armar_entrega.py` y `sql/instalacion/LEEME.md`.
- `frontend/vistas/publico.js`: la rama de texto plano de `LegalViews.fill` (el servidor siempre envía `html`).
- CSS sin referencia en ningún JS ni HTML: `.maint-dialog-actions`, `.maint-dialog-close` y `dialog[data-maint-dialog]` (apariencia.css), `.assistant-panel`, `.reading-note` (también en `base.css`), `.privacy-notice/-information/-feedback`, `.app-header`, `.btn-liquid-secondary`, `.btn-liquid-dark`, `.button.is-focus`, `.button.is-pressed` y `.btn-liquid-sidebar.is-active`.

Documentación: `docs/INVENTARIO-INTERFAZ-ACTUAL.md` (reescrito: 1238 → 183 líneas; rutas, pantallas y 84 endpoints salen de `urls.py`), `docs/MATRIZ-SEGURIDAD-v2.md`. `index.html`: versión de los archivos `mvc.8` → `mvc.9`.

No se tocó (decisión tuya): `sql/FUNCIONAMIENTO-BASE-DE-DATOS.md` (l. 246) y un comentario de `sql/el_chilito_base_completa.sql` (l. 1525) todavía mencionan `frontend/legales`; son parte del diseño de la base.

## 3. CSS antes y después

| Archivo | Líneas | `!important` |
|---|---|---|
| tokens.css | 101 → 101 | 0 → 0 |
| base.css | 1711 → 1710 | 416 → 414 |
| acceso.css | 126 → 126 | 25 → 25 |
| panel.css | 584 → 582 | 145 → 145 |
| navegacion.css | 145 → 145 | 108 → 108 |
| apariencia.css | 619 → 606 | 234 → 233 |
| cookies.css | 106 → 106 | 2 → 2 |
| **Total** | **3392 → 3376** | **930 → 927** |

(Conteo de apariciones de `!important`.) La tarea pedía reducirlos «al mínimo necesario» sin cambio visual. `apariencia.css` es una capa de ajustes con selectores del tipo `html body[data-private=true]:is(...)` que gana por especificidad **y** por `!important`; quitar uno sin ver la pantalla puede cambiar el resultado, y hoy no hay forma automática de comprobarlo (los paneles requieren sesión y el servidor lo enciendes tú). Quedan pendientes, para hacerlos con comparación visual: `apariencia.css` (233), `base.css` (414) y `navegacion.css` (108).

Selectores que mi búsqueda marcó sin uso pero se **conservan** porque se arman en tiempo de ejecución: `.tone-*`, `.btn-liquid-*`, `.plant-1…3`, `.is-0…2`, `.aviso--*`, `.is-publicada/.is-retirada` y `.inquiry-state.is-atendida`.

Hay un `{` sin cerrar en `apariencia.css` que ya existía antes de esta fase (balance −1); no lo toqué.

## 4. Búsquedas de código sin uso

- **Endpoints:** las 84 rutas de `urls.py` tienen llamador (en el frontend, o el equipo ESP32 en `dispositivos/vincular`). Ninguna sobra.
- **Funciones y clases Python/JS** con una sola aparición: solo ganchos de Django/allauth/`HTMLParser`. Ninguna sobra.
- **Restos del token de soporte, «Vinculación de huertos» y la maqueta comercial:** ninguno en el código. Quedan las redirecciones `#admin/vinculacion`, `#admin/comercial` y `#admin/consola` (a propósito, para enlaces viejos). La vinculación del **equipo** (`CodigoVinculacion`, `/api/huertos/<id>/vinculacion`) es v2 y se queda.
- **Referencias v1:** ninguna; los «v1» que aparecen son la API `_allauth/browser/v1`.
- No revisé textos de interfaz sin uso uno por uno.

## 5. `innerHTML` (44 usos en el frontend)

Revisé por interpolación (`${…}`) cada vista. Resumen:

| Uso | Dato | Saneo |
|---|---|---|
| Plantillas de las vistas (`paint`, `fillSlot`, diálogos, marcos) | Nombres, correos, notas, motivos, textos | `escaparHTML` o `textContent` en cada interpolación de texto |
| Texto legal (`LegalViews.fill`, vista previa y detalle de administración) | HTML del servidor | Saneado en el servidor con la lista blanca (`privacidad/legales.py`) |
| Íconos, spinners, plantillas fijas | Propios | Sin datos del servidor |
| Números e identificadores (`item.id`, `plant.number`, `chiles`, `duration`) | Enteros, UUID o `bigint` como texto | Tipados por la base y el serializador; no pasan por el escape. Los avisos además validan el id con `/^[1-9][0-9]{0,18}$/` |

Hallazgos corregidos: `STAGES[plant.stage] || plant.stage` y `… [lastWatering.origin] || lastWatering.origin` insertaban el valor sin escapar cuando no estaba en la tabla. Los valores reales son listas cerradas de la base, pero se escapan ahora; prueba en la suite «Mi huerto».

Limitación: la revisión de las ~700 interpolaciones fue por lectura de las que no pasan por `escaparHTML` o un ayudante conocido, no con una herramienta que lo demuestre.

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `makemigrations --check --dry-run` | Sin cambios |
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 308 pruebas, OK (antes y después de los cambios) |
| `pruebas_local.py flujos` | 29/29, 45/45 y 56/56 |
| `sql/pruebas/pruebas_v2.py` (base creada con `migrate`, temporal, sin textos publicados) | 149 correctas, 0 fallos |
| `sql/pruebas/prueba_depuracion.py` (misma base) | Termina sin error; resume y depura 1 medición |
| `node frontend/pruebas/pruebas.cjs` | 7 de 7 suites OK |

Notas: las pruebas se corrieron con `CHILITO_IDEMPOTENCIA_SECRETO` generada al vuelo (tu `.env` aún trae el nombre viejo). `pruebas_v2.py` falla si la base ya tiene textos legales publicados (espera una base recién instalada); por eso se corrió antes de publicarlos. La corrección del contador de avisos **no tiene prueba automática**: la suite de Node no monta controladores (la prueba MVC lo prohíbe); se comprueba mirando la pestaña Red.

## 7. Dependencias (`backend/requirements-lock.txt`)

asgiref 3.12.1 · cffi 2.1.1 · cryptography 50.0.2 · Django 5.2.18 · django-allauth 65.20.0 · fido2 2.2.1 · psycopg 3.3.6 · psycopg-binary 3.3.6 · pycparser 3.11 · PyJWT 2.15.1 · qrcode 8.2 · sqlparse 0.6.0 · typing-extensions 4.16.0 (solo Python < 3.13) · tzdata 2026.5.

`pip-audit` **no está instalado** y no lo instalé. Pendiente: dime si lo instalo en el entorno de desarrollo o lo corres tú.

## 8. Para el despliegue

- **`chilito_pkg_owner` no debe tener `CREATEDB` en producción.** Hoy lo tiene para que las pruebas creen la base temporal.
- **El simulador (`backend/tools/simular_equipo.py`) y `backend/tools/` de prueba no se despliegan** (`armar_entrega.py` excluye el simulador, pero **sí copia** `pruebas_local.py`, `probar_*.py`, `destino_temporal.py` y `soporte_local.py`; hay que quitarlas de la lista antes de desplegar, decisión tuya).
- **`chilito_mantenimiento_periodico()` se programa cada hora** (Cloud Scheduler o `pg_cron`).
- Antes de arrancar: en el `.env` real, **renombrar `CHILITO_SUPPORT_KEY` a `CHILITO_IDEMPOTENCIA_SECRETO`** (mismo valor; al arrancar con el nombre viejo, Django falla con «Suministra CHILITO_IDEMPOTENCIA_SECRETO…»). Las respuestas guardadas por idempotencia usan esa clave solo para la huella de la petición, así que cambiar el valor solo haría que un reintento viejo se trate como petición nueva.

## 9. Pendientes (RV.1)

1. Reducir `!important` con comparación visual (escritorio y móvil) contra la fase 6.
2. `pip-audit`.
3. Recorrido manual con el servidor como `chilito_pkg_runtime` sobre consola, flota y mantenimientos (viene de la fase 6).
4. El enlace `#admin/consola` que escribe la función de la base en el aviso de «Nueva solicitud de soporte» (la interfaz lo redirige; cambiar el texto de la función es decisión tuya).
5. Quitar la mención a `frontend/legales` de `sql/FUNCIONAMIENTO-BASE-DE-DATOS.md` y del comentario del script SQL.
6. `docs/EJECUCION-v2.md` l. 163 llama «Clave de tokens de soporte» a `CHILITO_VINCULACION_SECRETO`; es texto del plan, no lo cambié.

## 10. Cómo probarlo a mano

1. Repite las pruebas manuales de las fases 1 a 6; la página debe verse igual que al final de la fase 6, en escritorio y móvil.
2. **Flota:** con un equipo que tenga un solo punto en 7 días, las dos gráficas muestran el valor (p. ej. 50,1 % y 27,5 °C) y un punto; con ninguno, siguen vacías.
3. **Avisos:** abre la pestaña Red, recarga cualquier pantalla del panel: una sola petición a `/api/avisos/contador`, luego una cada 60 s. Abre un aviso sin leer: se pide una más al leerlo.
4. Cambia el nombre de la variable en el `.env` y arranca el servidor.

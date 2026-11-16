# Informe · Ajustes: consola remota persistente y textos legales desde Word

Rama: `ajustes-consola-legales`. Antes de empezar, los 9 archivos de diseño que estaban sin commit se guardaron tal cual en un commit propio (`17eef40`, mvc.21). La base de datos no se tocó.

## 1. Resumen

La consola remota tiene ahora una pantalla por caso (`#admin/soporte/<folio>`) separada de la bandeja. Salir de la pantalla ya no cierra la sesión técnica: al volver se retoma sola. «Órdenes del caso» muestra todas las órdenes de soporte del caso con su estado, y una orden igual en curso bloquea su botón y dice por qué. En textos legales se puede subir un `.docx` (lo convierte mammoth en el servidor y pasa por el saneador ampliado), pegar desde Word (el servidor sanea el HTML del portapapeles) y el borrador se guarda solo cada 10 s si cambió. La vista previa y la página pública comparten la misma tipografía de lectura. **No se probó en un navegador.**

## 2. Archivos

Creados: este informe.

Modificados (backend):
- `datos/services.py`: detalle del caso por folio; `_ordenes_del_caso` (todas las órdenes de soporte del caso, la usan el detalle, el estado de la sesión y la vista de la persona); `conectar_caso` comprueba la autorización antes de devolver la sesión abierta.
- `datos/api.py`, `config/urls.py`: el detalle pasa a `api/admin/soporte/<folio>`; rutas `legales/importar` y `legales/sanear`.
- `privacidad/documentos_html.py`: lista blanca nueva (h2, h3, h4, p, br, strong, em, u, ul, ol, li, a, blockquote, table, thead, tbody, tr, th, td); h2 ya no se convierte en h3; h1→h2, h5/h6→h4, b→strong, i→em; enlaces solo http/https/mailto con `rel`; se omiten `xml`, `title` y las secciones condicionales de Word.
- `privacidad/legales.py`: `importar_docx` y `sanear_pegado`; `MAXIMO_CONTENIDO` de 28 000 a 200 000 (el de la base).
- `privacidad/api.py`: las dos vistas nuevas.
- `web/api.py`: `endpoint(..., archivo=…)` y `subida()` para un POST multipart con un único archivo.
- `web/middleware.py` + `config/settings/base.py`: `LimiteDeSubida` (413 si un multipart pasa de 2 MB + 64 KB, antes de que CSRF lo lea); `DATA_UPLOAD_MAX_MEMORY_SIZE` de 32 KB a 256 KB (decisión tuya).
- `requirements-lock.txt`: `mammoth==1.13.0` y su dependencia `cobble==0.1.4`, con hashes.
- Pruebas: `datos/tests/test_admin.py`, `privacidad/tests.py`.

Modificados (frontend):
- `controladores/administracion.js`: `ConsoleController` (bandeja o caso según la ruta, sin cierre al salir, retoma la sesión, bloqueo de órdenes); `LegalAdminController` (subida, pegado y autoguardado).
- `vistas/administracion.js`: `ConsoleViews.inboxScreen/caseScreen/lockOrders`, panel «Órdenes del caso»; `LegalAdminViews` con el botón «Subir documento (.docx)», el aviso «Guardado · hh:mm» y los errores nuevos.
- `modelos/administracion.js`: `ConsoleService.detail(folio)`; `LegalAdminService.importDocx/sanitize/fileProblem`; se quita `keepalive`.
- `modelos/cuenta.js`: `ChilitoHTTP.request` envía `FormData` sin JSON ni clave de idempotencia; se quita `keepalive` (solo lo usaba el cierre al salir).
- Estilos: `tokens.css` (tokens de lectura legal), `panel.css` (reglas comunes de `.legal-prose` y `.legal-preview`), `apariencia.css` (escala de títulos en la vista previa). Se borran las reglas sin uso de la rejilla bandeja+detalle, del caso seleccionado y del marcador «Selecciona un caso».
- `index.html`: `mvc.21` → `mvc.22`.
- `pruebas/pruebas.cjs`: casos de bandeja y caso, bloqueo de órdenes, adaptador `FormData` y una suite nueva del editor legal.

Docs: `INVENTARIO-INTERFAZ-ACTUAL.md` (rutas y pantallas).

Eliminados: ninguno.

## 3. Líneas

`git diff --shortstat` (sin este informe): 22 archivos, 764 añadidas y 189 eliminadas.

## 4. Endpoints

| Cambio | Ruta | Capacidad |
|---|---|---|
| Cambiado | `GET api/admin/soporte/<folio>` (antes `<uuid>`); ahora trae `orders` | `atender_soporte` |
| Cambiado | `GET api/admin/sesiones/<id>`: `orders` son las del caso, no solo las de la sesión | `atender_soporte` |
| Cambiado | `POST api/admin/soporte/<id>/conectar`: con la autorización revocada o vencida ya no devuelve la sesión abierta | `atender_soporte` |
| Nuevo | `POST api/admin/legales/importar` (multipart, campo `documento`) | `gestionar_legales` |
| Nuevo | `POST api/admin/legales/sanear` (multipart, campo `html`) | `gestionar_legales` |

Los dos nuevos pasan por `@endpoint`: sesión, cuenta, capacidad, segundo factor y cuota de escritura. No usan recibo de idempotencia porque no cambian datos y la respuesta puede pesar mucho.

## 5. Seguridad

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V5 (archivos subidos) | Extensión `.docx`, firma `PK\x03\x04`, ≤ 2 MB (también antes de leer el cuerpo), ZIP legible con `word/document.xml`, ≤ 200 entradas y ≤ 20 MB descomprimidos. mammoth sin acceso a archivos externos, sin el mapa de estilos incrustado y sin imágenes. El archivo no se guarda | `ImportarDocumentos.test_rechaza_lo_que_no_es_un_docx_valido` (pdf, firma falsa, ZIP corrupto, sin documento, bomba de 21 MB, > 2 MB, 3 MB → 413), `test_solo_un_archivo_en_su_campo_y_con_la_capacidad` |
| V1/V3 (saneamiento en servidor) | El HTML del .docx y el del portapapeles pasan por `sanear_html`; el navegador solo coloca el HTML del servidor en la vista previa y mete el resto en el `textarea` como texto | `test_quita_scripts_imagenes_estilos_y_enlaces_peligrosos`, `test_pegado_se_sanea_en_el_servidor`, `DocumentosHTML.*`, suite Node «editor legal» |
| V8 (autorización) | `gestionar_legales` en importar y sanear; en la consola solo quien atiende retoma, conecta y ordena; otro administrador no ve la sesión | `Capacidades` (rutas nuevas), `Consola.test_otro_admin_no_retoma_la_sesion` |
| V8 (autorización vigente) | Cada orden relee la autorización; conectar no retoma una sesión revocada o vencida | `test_revocar_con_la_sesion_abierta_no_deja_retomarla`, pruebas de fase 6 |
| V16 (auditoría) | `importar_documento_legal` con solo el tamaño en KB y el número de avisos de la conversión; nada del contenido ni del nombre del archivo | `test_titulos_listas_formato_enlace_y_tabla` |
| Dependencia (SSDF PW.4) | mammoth fijada con hashes; `pip-audit` sin vulnerabilidades | `pip-audit -r backend/requirements-lock.txt` |

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 320 pruebas, OK (eran 308) |
| `python3 backend/tools/pruebas_local.py flujos` | 29/29, 45/45 y 56/56 |
| `node frontend/pruebas/pruebas.cjs` | 8 de 8 suites OK (una nueva) |
| `pip-audit -r backend/requirements-lock.txt` | No known vulnerabilities found |

## 7. Pendientes y dudas

- **No probado en navegador** ni con el servidor como `chilito_pkg_runtime` sobre las rutas nuevas. Los flujos de `flujos` no cubren importar ni sanear.
- **Versiones ya publicadas:** el saneador vale para todas. Un `h2` publicado se ve ahora como `h2` con el mismo estilo que tenía el `h3`; un `h3` escrito a mano se ve un poco más chico que antes; un enlace relativo (`#…` o `/…`) queda como texto. El contenido guardado no cambia.
- **Pegar listas desde Word:** el portapapeles de Word no trae `ul/li`, sino párrafos con viñetas de respaldo. Se quitan las viñetas y quedan como párrafos. Para conservar las listas conviene «Subir documento (.docx)».
- **Autoguardado:** cada guardado deja un registro `editar_borrador_legal` en la auditoría (como mucho uno cada 10 s y solo si hubo cambios). Un borrador nuevo se crea solo cuando la versión tiene formato válido y hay título y contenido. Si otra persona cambió el borrador, el autoguardado se detiene y lo avisa.
- **`LimiteDeSubida`** es una pieza que el plan no nombraba: va en `web/middleware.py` porque Django no limita el tamaño de un archivo y CSRF lee el formulario completo antes de la vista. Una subida sin `Content-Length` se rechaza.
- **Un administrador, una sesión abierta** (regla de la base): como la sesión ya no se cierra al salir, para conectar otro caso hay que cerrar la anterior con «Cerrar sesión técnica». La bandeja no marca qué caso tiene la sesión abierta.
- **Órdenes en curso:** el bloqueo replica el índice `comando_uno_en_curso` (mismo tipo y planta en estado `pendiente` o `enviado`). Si la orden nunca recibe respuesta, el botón sigue bloqueado hasta que la base la marque `expirado`.

## 8. Cómo probarlo a mano

1. **Consola:** en `#admin/soporte` toca un caso: se abre `#admin/soporte/CS-…` sin la bandeja. «Atender» → «Conectar» → «Reiniciar equipo».
2. Ve a otra pantalla del menú y vuelve al caso: la sesión sigue abierta sin pulsar «Conectar», «Órdenes del caso» muestra el reinicio como pendiente y el botón «Reiniciar equipo» está desactivado con el motivo visible.
3. «← Volver a la bandeja» regresa a la pestaña que tenías.
4. Con otra cuenta de soporte abre el mismo folio: no ve la sesión ni puede conectar.
5. La persona pulsa «Revocar acceso»: en menos de 10 s aparece el aviso de cierre; «Conectar» ya no la retoma.
6. «Cerrar sesión técnica», «Resolver caso» y cerrar la sesión de la cuenta siguen cerrando la sesión técnica.
7. **Legales:** en «+ Nueva versión», escribe versión y título, pega un fragmento desde Word: entra limpio, sin estilos. «Subir documento (.docx)» con un Word que tenga títulos, listas, negritas, un enlace y una tabla: confirma que reemplaza y revisa la vista previa.
8. Espera 10 s sin guardar: aparece «Guardado · hh:mm» y la dirección cambia a `#admin/legales/<id>`; «Publicar» aparece.
9. Intenta subir un `.pdf`, un archivo renombrado a `.docx` y uno de más de 2 MB: cada uno muestra su mensaje.
10. Publica y abre la página pública: títulos, listas, tablas y espacios iguales a la vista previa, también en móvil (la tabla se desplaza dentro de su caja).

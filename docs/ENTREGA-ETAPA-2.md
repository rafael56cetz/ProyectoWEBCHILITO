# ETAPA 2 — Privacidad y derechos ARCO

Fecha: 17 de octubre de 2026. Alcance: frontend de Privacidad y ARCO sobre HTML/CSS/JavaScript y MVC existentes. Repositorio: `entregas/ProyectoWEBCHILITO`, rama `main`, base `f5605359cdff0fb596a63cfc0c352026fb5060e2`. Se conservan los cambios locales de las etapas 0 y 1. Sin commit ni push; la etapa 3 no se ejecuta.

## Contexto revisado y conservación

Se leyeron README, plan de etapa 0, entrega de etapa 1 y guía de backend, junto con modelos, rutas, controladores, plantillas, estilos y revisión local. Se comprobó el estado de Git y no se encontraron instrucciones AGENTS aplicables en la ruta examinada. Se trabajó exclusivamente en esta copia. La etapa 1 se mantuvo: bloqueo de alta con documentos pendientes, aceptación demostrativa, código de registro y recuperación por enlace.

Se conservan portada, logo, imágenes, fuentes Geist, componentes comunes Liquid Glass, métricas, modelo/servicio del huerto, electrónica y las cuatro entradas Mi huerto, Avisos, Asistente y Mi cuenta. Privacidad es un subapartado. No se modificaron Blender, Notion, tecnología, arquitectura ni tareas del equipo.

## Resultado y recorridos

| Ruta | Presentación y comportamiento |
| --- | --- |
| `#derechos-arco` | Pública sin cuenta ni términos; resumen de cuatro derechos, aviso de canal no operativo, pendientes y formulario compartido |
| `#cuenta/privacidad` | Enlaces legales, formulario compartido desplegable, carga, lista, vacío confirmado, indisponibilidad, sesión vencida y errores de permiso |
| `#cuenta/privacidad/solicitudes/:id` | Detalle, folio/fechas del servicio, historial y requerimiento de información solo cuando el servicio lo permite |

Se enlaza ARCO desde pie público, aviso y Privacidad. Mi cuenta ofrece su acceso también si el perfil está cargando o falla. Las subrutas completas se reconocen sin perder el ID, con títulos y tratamiento de IDs inválidos; se conserva la navegación anterior.

El único formulario ARCO se reutiliza en público y cuenta: nombre, contacto, tipo (incluido «No sé cuál corresponde»), descripción, relación opcional con cuenta y corrección condicional. La obligatoriedad es una propuesta visible, pendiente del procedimiento. No impone patrones al nombre ni exige aceptación de términos. Incluye etiquetas, ayudas, errores asociados, `select`, `textarea`, foco y bloqueo durante envío. No se solicitan identificaciones, firmas, fotografías ni adjuntos.

El servicio normal siempre responde indisponible. Solo un acuse válido devuelto por un servicio puede producir recepción confirmada; nunca se inventan folios/fechas en la vista. El aviso público deja claro que el canal no está operativo. Los estados de seguimiento son provisionales y no prometen aprobación ni borrado inmediato.

## Abrir y revisar

Desde `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO`, terminal normal:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

- [ARCO normal](http://127.0.0.1:8766/index.html#derechos-arco).
- [Privacidad normal](http://127.0.0.1:8766/index.html#cuenta/privacidad): muestra servicio no disponible; no hay contraseña funcional.

En otra terminal desde la misma carpeta, para revisión sintética:

```powershell
python -m http.server 8767 --bind 127.0.0.1
```

- [Formulario público de revisión](http://127.0.0.1:8767/revision/index.html#derechos-arco).
- [Lista de revisión](http://127.0.0.1:8767/revision/index.html#cuenta/privacidad).
- [Requerimiento ficticio](http://127.0.0.1:8767/revision/index.html#cuenta/privacidad/solicitudes/demo-informacion).

La barra «Demostración local», dentro de «Controles y datos de revisión», permite seleccionar la respuesta de privacidad y abrir cada estado. Para probar envío, abrir Formulario público y pulsar «Rellenar solicitud ficticia»; también puede completarse manualmente con datos inventados. La selección lenta permite observar carga/envío durante cinco segundos. El escenario de error de validación o acuse incompleto se observa al enviar. El permiso de respuesta desactivado se observa en «Pendiente de información». Las muestras `demo-recibida`, `demo-informacion`, `demo-revision`, `demo-respondida` son solo identificadores ficticios.

El adaptador de revisión no retiene el nombre, correo, descripción o corrección escritos: usa contenido sintético y conserva en memoria únicamente los cambios de escenario. Recargar reinicia los expedientes, elimina nuevas solicitudes ficticias y borra aclaraciones. La normal no carga este adaptador ni permite activarlo con parámetros. `revision/` continúa excluida de Git por la regla existente; se mantiene como herramienta local separada.

## Archivos de esta etapa y responsabilidad

Rutas relativas a este repositorio; no se renombró, movió o eliminó ningún archivo existente.

| Archivo | Acción | Responsabilidad |
| --- | --- | --- |
| `dist/modelo/privacidad.js` | Ampliado | Modelo: conserva documentos/bloqueo del alta; añade tipos/estados, validación y normalización de lista, detalle y acuse |
| `dist/modelo/servicio-privacidad.js` | Creado | Modelo: frontera de integración desconectada, compatible con cancelación |
| `dist/vista/privacidad.js` | Creado | Vista: formulario único, página pública, cuenta, lista, detalle, historial, estados y acuse |
| `dist/vista/css/privacidad.css` | Ampliado | Vista: estilos acotados a privacidad, campos, foco, tamaños y alternativas accesibles; conserva legales |
| `dist/vista/legales.js` | Modificado | Vista: enlace ARCO en aviso |
| `dist/vista/paginas.js` | Modificado | Vista: único enlace ARCO nuevo en pie público; portada/huerto intactos |
| `dist/vista/aplicacion.js` | Modificado | Vista: acceso Privacidad dentro de Mi cuenta, incluso con carga/error del perfil |
| `dist/controlador/privacidad.js` | Creado | Controlador: eventos, lectura/validación del formulario, llamadas al servicio, aborto, timeout, permiso de aclaración y foco |
| `dist/controlador/aplicacion.js` | Modificado | Controlador: monta y libera el controlador de privacidad, contempla select/textarea en foco móvil |
| `dist/controlador/site.js` | Modificado | Controlador: inyección de servicio, rutas públicas/nested completas, IDs y títulos; conserva otras rutas |
| `dist/index.html` | Modificado | Entrada: orden de carga y versiones de los archivos afectados |
| `revision/privacidad.js` | Creado, solo local | Adaptador sintético explícito: estados, expedientes, acuses y aclaraciones en memoria |
| `revision/index.html`, `revision/escenarios.js` | Ampliados, solo local | Selector de escenarios y accesos de revisión; usan exactamente las vistas/controladores normales |
| `revision/revision.css` | Ajustado, solo local | Mínimo táctil de 44 px para los botones de revisión frente a reglas comunes de mayor prioridad |
| `revision/comprobar-etapa2.cjs` | Creado, solo local | Automatización de recorridos, respuestas, accesibilidad técnica y adaptación, sin capturas |
| `revision/comprobar-etapa1.cjs` | Ajustado, solo local | Aislamiento de navegación entre casos y espera del cambio a recuperación; no cambia expectativas funcionales |
| `revision/resultado-etapa1.json`, `revision/resultado-etapa2.json` | Regenerados, solo local | Evidencia textual de pruebas, sin datos personales |
| `README.md` | Actualizado | Rutas, apertura, MVC, estado de etapas y revisión |
| `docs/INTEGRACION-BACKEND.md` | Actualizado | Contratos entendidos, responsabilidades y pendientes para activación |
| `docs/PLAN-INTEGRACIONES-FRONTEND-ETAPA-0.md` | Actualizado | Nota de estado posterior; conserva el inventario histórico |
| `docs/ENTREGA-ETAPA-2.md` | Creado | Esta entrega, pruebas y límites |

El modelo define datos/validaciones y el acceso al servicio; la vista presenta datos escapados y el controlador coordina navegación y eventos. No se añade framework, compilador, arquitectura paralela o copia de pantallas.

## Comprobaciones

Resultado: **20/20 grupos de etapa 2 y 19/19 de regresión de etapa 1 aprobados**. Evidencias locales: `revision/resultado-etapa2.json` y `revision/resultado-etapa1.json`; scripts reproducibles junto a los resultados. Las comprobaciones son automatizadas, sin imágenes y sin perfiles personales del navegador.

- Chromium: entrada pública/enlaces, mismas vistas en ambos entornos, cuatro destinos, IDs válidos/malformados/codificados, rutas profundas, títulos, recarga, Atrás y Adelante.
- Controles de revisión a 320 px: mínimo de 44 px, apertura del formulario público y relleno/envío sintético. La barra gestiona su foco por separado para que la corrección del encabezado del sitio no interrumpa el clic.
- Validaciones de modelo y formulario: nombre sin patrón arbitrario, correo, select, textarea, rectificación condicional, lectura de valores, errores asociados, foco al campo inválido, validación del servicio y acuse incompleto. El envío normal termina en indisponibilidad sin expediente/acuse.
- Estados: carga/envío en curso, bloqueo de doble envío, lista con cuatro solicitudes, vacío confirmado, indisponibilidad, sesión vencida, denegación y solicitud inexistente; historial y respuesta autorizada sin cambio de estado elegido por el cliente.
- Cancelación y respuesta tardía con adaptador controlado; reentrada sin duplicar manejadores; timeout; textos del servicio escapados; solicitudes de revisión descartadas al recargar; almacenamiento local y de sesión vacío.
- Anchos **320, 390, 768, 1024 y 1440 px** en formulario público, lista y detalle de revisión; sin elementos fuera del ancho, con título libre del encabezado, controles de al menos 44 px y cuatro entradas móviles. Texto al 200 % y cadenas largas en 320 px sin desbordamiento.
- Tab/Enter y select/textarea; foco visible y libre de encabezado/barra inferior en ventana 390×600, como aproximación de espacio reducido por teclado. Movimiento reducido, material sólido y colores forzados. Contraste calculado de las parejas de texto añadidas sobre sus fondos, al menos 4.5:1; botones compartidos cubiertos por regresión de etapa 1.
- Firefox y WebKit: registro con casilla desmarcada conservado, formulario público con rectificación/envío sin recepción real y detalle con requerimiento a 390 px, sin desbordamiento. Se detectó y corrigió en WebKit el desplazamiento del contenedor durante pointer-down que impedía completar el clic en Enviar; el ajuste de foco se limita a controles y avisos.
- Regresión de etapa 1 completa: casilla, bloqueo normal, errores, verificación, documentos, recuperación y enlace de restablecimiento, salida durante envío, adaptación y navegación. Los tests ahora esperan el cambio de ruta y aíslan la entrada entre casos; los resultados anteriores no se sustituyen por expectativas más débiles.
- La matriz de Chromium no detectó errores JavaScript, recursos HTTP fallidos ni tráfico a servicios externos. Se comprobó que parámetros de revisión no activan datos sintéticos en la versión normal.

También se comprobó sintaxis JavaScript y diferencias de Git. Los cambios previos de acceso permanecen; el único cambio en `paginas.js` es el enlace del pie. La guía histórica de etapa 0 solo incorpora la nota de estado posterior. No se cambian modelo/servicio IoT, estilos base, imágenes ni fuentes.

Límites: no se ejecutó una prueba manual con NVDA/VoiceOver, teclado virtual de teléfono físico o Safari en un dispositivo Apple (WebKit es una comprobación de motor). Las asociaciones de errores/estados se verificaron en el DOM, sin afirmar su lectura auditiva. La reducción de ventana no sustituye un teclado móvil real. No se prueba recepción, autenticación, autorización, correo, persistencia o cumplimiento jurídico de un servicio real porque no existe en esta entrega. Las salidas iniciales por servidores detenidos o sincronización de la prueba se resolvieron antes de la ejecución final.

## Contratos, pendientes y responsabilidades

La [guía de integración](INTEGRACION-BACKEND.md#privacidad-y-arco-interfaz-de-etapa-2) concreta `arco-create`, `arco-list`, `arco-detail` y `arco-add-info`. Respecto del plan se precisan `request` para expediente, `informationRequestId` para su requerimiento y `canRespond` como permiso explícito. No se implementan endpoints HTTP. El folio o ID no concede permisos; la identidad/autorización se verificará en servidor.

- Rafael: backend, validación de servidor, sesión, autorización de cada expediente, idempotencia y transporte, después de acordar contratos/procedimiento.
- Carolina: PostgreSQL, relación opcional con cuenta, expediente/historial/requerimientos y conservación, después de aprobar minimización y procedimiento. Conserva además la responsabilidad del logo.
- Rafael y Gabriela: diseño/frontend y revisión de los recorridos.
- Por designar/aprobar: responsable y contacto de datos, documentos legales, acreditación y representación, canal operativo, obligatoriedad/límites de campos, estados, información visible y retención. No se fijan plazos legales.
- Pendiente: mecanismo seguro de seguimiento sin cuenta. No se implementa correo + folio como contraseña ni se capturan documentos.
- Pendiente de integración: endpoints, sesión, permisos, idempotencia ante reintentos/timeouts, paginación y estados específicos de límite/conflicto. Los botones bloqueados no sustituyen estas garantías del backend.
- Pendiente de revisión con equipo: lectores de pantalla reales, teclado móvil físico y validación jurídica. La aceptación sobre documentos vacíos sigue siendo solo demostrativa; registro real bloqueado.

No se implementaron passkeys, biometría, PIN, base de datos, backend, correo, servicios externos, Notion ni cambios IoT. No se avanzó a la etapa 3; requiere una solicitud independiente.

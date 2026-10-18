# El Chilito — Integraciones del frontend: ETAPA 0

Fecha: 17 de octubre de 2026. **Registro histórico de ETAPA 0: revisión y planificación terminadas.** El inventario y los resultados de esta revisión describen la base anterior a implementar. Cada etapa necesita una solicitud posterior del usuario. Este documento propone interfaces y contratos; no activa servicios ni constituye contenido legal aprobado.

Actualización posterior autorizada: la [ETAPA 1 — registro y páginas legales](ENTREGA-ETAPA-1.md) y la [ETAPA 2 — privacidad y ARCO](ENTREGA-ETAPA-2.md) cuentan con implementación local y revisión demostrativa. Consultar esas entregas y la guía de integración para distinguir el contrato implementado de las propuestas históricas de este plan. La etapa 2 precisa las claves `request` e `informationRequestId` y el permiso `canRespond`; no activa recepción, identidad, autorización ni almacenamiento reales.

Actualización de ETAPA 3 autorizada: [Seguridad y llaves de acceso](ENTREGA-ETAPA-3.md) ya dispone de interfaces, estados y contratos de revisión, conservando `AuthService`. No se invoca WebAuthn ni se crean credenciales o sesiones reales. Se precisa confirmación de sesión para el acceso con llave, ID de respuesta para revocar y un puente demostrativo explícito en la revisión. La oferta posterior a verificación vive solo en el contexto del controlador, sin una ruta que confirme sesión. **Solo la etapa 4 queda pendiente de solicitud.** El resto de este plan se conserva como registro histórico de propuestas.

Actualización de ETAPA 4 autorizada: la [revisión conjunta y cierre](CIERRE-INTEGRACIONES-FRONTEND.md) registra la pasada integrada de las etapas 1–3 y los cruces adicionales. La [guía central](INTEGRACION-BACKEND.md) es la referencia vigente de contratos y pendientes; los apartados de este plan conservan su carácter histórico. No se activan servicios ni se declara preparación para producción.

Documento de entrada: `output/documentacion/El_Chilito_Plan_integraciones_frontend_2026-10-17.md`, ubicado en el proyecto local IOTCHILITO, fuera de este repositorio de entrega. Se conserva sin cambios. Complementa el [README](../README.md) y la [guía del contrato actualmente comprendido por la interfaz](INTEGRACION-BACKEND.md).

## 1. Base revisada y preservación

| Comprobación | Resultado al 17-10-2026 |
| --- | --- |
| Repositorio de trabajo | `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO` |
| Rama local | `main`, con seguimiento de `origin/main` |
| Revisión local | `f5605359cdff0fb596a63cfc0c352026fb5060e2`, 14-10-2026, 16:52:41, UTC−06:00 |
| Revisión remota | Consulta directa a GitHub: HEAD y `refs/heads/main` coinciden con ese commit. La consulta de ramas y etiquetas solo devolvió `main`; no se encontró una revisión más reciente publicada. |
| Cambios locales iniciales de esta copia | Ninguno, incluidos el índice y los archivos sin seguimiento |
| Instrucciones | No se encontró `AGENTS.md` en los directorios antecesores examinados ni dentro de IOTCHILITO. Se aplican las instrucciones del usuario, el plan, README y la guía de integración. |
| Proyecto original | `disenios/sites-geist` es otro repositorio, en `main`, con 27 entradas de cambios locales. Se conservan; no se sincroniza ni sustituye esa copia. La raíz IOTCHILITO no es un repositorio Git. |
| Alcance de lectura | Entrada HTML, modelos, adaptadores, vistas, controladores, estilos compartidos y específicos, referencias de recursos, `.gitignore`, README y guía de integración |

`dist/index.html` carga directamente los archivos de `dist/modelo/`, `dist/vista/` y `dist/controlador/`. Son fuentes editables, no una salida que deba regenerarse. No hay framework, compilador ni paquete de pruebas en esta entrega. El servidor estático debe servir `dist/`; una página servida desde la copia original no demuestra el estado de esta copia.

La etapa 0 modifica únicamente tres documentos: este archivo, README y la guía de integración. No cambia HTML, CSS, JavaScript, logo, fuentes, imágenes ni recursos de Blender; tampoco crea pantallas, simuladores, credenciales o migraciones. No incluye commit, push, publicación ni cambios en Notion.

## 2. Inventario de vistas, rutas y comportamiento actual

Todas las rutas usan el fragmento de `index.html`. «Privada» describe la intención de la pantalla: hoy `canEnter` permite entrar por defecto y no existe autenticación real.

| Vista o destino existente | Ruta | MVC y comportamiento observado |
| --- | --- | --- |
| Portada | sin fragmento o `#inicio` | `vista/paginas.js`: `landing`, encabezado, logo y pie compartidos |
| Secciones de portada | `#el-proyecto`, `#prototipo`, `#como-funciona` | Mismo contenido; `controlador/site.js` y `navigation.js` desplazan y enfocan el ancla |
| Iniciar sesión | `#acceso` | `AuthViews` / `AuthController` / `AuthModel`; correo y contraseña; acción `login` |
| Crear cuenta | `#registro` | Correo, contraseña y confirmación; acción `register`; aún sin aceptación de términos |
| Verificar correo del registro | `#verificar` | Código, correo y contexto de desafío; `verify` y `resend`; no es un paso obligatorio del inicio de sesión |
| Recuperar acceso | `#recuperar` | Correo; `request-reset`; confirmación neutral si el servicio acepta |
| Restablecer contraseña | `#restablecer?token=…` | `inspect-reset` antes del formulario; token retirado de la URL y conservado temporalmente en memoria; sin token muestra enlace no disponible |
| Mi huerto | `#huerto` | `AppController`, `AppModel` y `garden`; consulta `garden`; estado normal actual: esperando lecturas |
| Avisos y detalle | `#avisos`, `#avisos/:id` | Consulta `notices`, filtros, detalle obtenido de la lista y acción `mark-read`; el adaptador normal devuelve error de consulta |
| Compatibilidad de avisos | `#huerto/avisos` | Se reemplaza por `#avisos` |
| Asistente | `#asistente` | Información de próxima etapa; sin servicio de IA |
| Mi cuenta | `#cuenta` | Consulta `profile`; muestra correo y verificación cuando existan; hoy ambos valores son `null` |
| Cambiar contraseña | `#cuenta/contrasena` | `AuthController.mount('cambiar', …)` dentro de la misma estructura de cuenta; acción `change-password` |
| Cerrar sesión | botón, sin ruta propia | Acción `logout`; solo navega a `#acceso` si el servicio responde `accepted` |
| Términos y condiciones | enlaces `#terminos` en dos lugares del pie | Destino existente, pantalla no implementada; el router termina mostrando la portada |
| Aviso de privacidad | enlaces `#privacidad` en dos lugares del pie | Destino existente, pantalla no implementada; muestra la portada |
| Seguridad y protección de datos | enlace público `#seguridad` | Pantalla no implementada; muestra la portada. No equivale a Seguridad de Mi cuenta. |
| Ruta no reconocida | otros fragmentos | Regresa a la portada; no hay vista específica de ruta inexistente |

`AppModel.destinations` define exactamente **Mi huerto, Avisos, Asistente y Mi cuenta**. `AppViews.shell` reutiliza esas cuatro entradas en escritorio y en la barra inferior móvil, que se fija a partir de 768 px. Sus nombres, orden y destinos se conservan.

El adaptador `AuthService` responde `unavailable`; `AppService` devuelve estados iniciales sin datos reales. La apertura de `#huerto` no confirma sesión ni autorización. Los contratos actuales completos permanecen en la guía de integración.

### Hallazgos que afectan las siguientes etapas

1. El router solo lee el primer y segundo segmento: `#cuenta/privacidad/solicitudes/:id` perdería los últimos segmentos. Hoy cualquier detalle de cuenta salvo `contrasena` acaba mostrando el perfil. Será necesario reconocer subrutas explícitas, decodificar identificadores con manejo de errores y comparar la ruta completa al decidir título, foco y montaje. Conservar enlaces antiguos, Atrás/Adelante y recuperación con token.
2. `AuthController.values()` obtiene `input.value` para todos los campos. Una casilla necesita `input.checked` booleano; `value="on"` no prueba aceptación. Además, el estado ocupado actual usa `readOnly`, que no bloquea una casilla: habrá que tratar su bloqueo y restauración por separado, sin perder el valor enviado.
3. El formulario usa `novalidate`: añadir solo `required` no basta. La validación del modelo y del controlador debe impedir la llamada al adaptador y reutilizar el resumen de errores, `aria-invalid`, descripción asociada y foco al primer error.
4. Los estilos heredados de `.field input` y `.login-form input` son amplios. La casilla requiere un selector propio acotado para no recibir dimensiones de un campo de texto. ARCO también necesita `select` y `textarea`; los controladores actuales solo recogen/enfocan ciertos tipos de elementos.
5. `AppController` ya cancela solicitudes y destruye el formulario de contraseña al salir. Privacidad y Seguridad deben integrarse en ese ciclo, sin duplicar eventos, peticiones ni la estructura de navegación.
6. El encabezado y la barra inferior calculan sus alturas en variables CSS; las subpantallas deben respetar esos espacios, el teclado móvil, el foco y las áreas seguras. No se cambia su posicionamiento en esta etapa.
7. El plan de entrada enumera también colores históricos cálidos. Los estilos de acceso/aplicación actuales ya usan `#F6F9F6`–`#EBF1EC`, texto `#142419`, secundario `#4A5D4E` y acento `#264D32`. Prevalece conservar el diseño actual; no se restablece la paleta antigua ni se limpia globalmente la cascada CSS.
8. El comentario de `modelo/servicio-acceso.js` todavía menciona a Kevin. Queda registrado como referencia histórica a actualizar cuando se trabaje en ese adaptador; el reparto vigente se corrige ahora en documentación, sin tocar JavaScript.

## 3. Mapa propuesto de vistas y estados

| Etapa | Ruta / punto de entrada | Vista y estados previstos |
| --- | --- | --- |
| 1 | `#registro` | Formulario existente + casilla obligatoria. Inicial sin marcar, error de aceptación, corrección, envío ocupado, documentos pendientes, versión cambiada, indisponibilidad y confirmación demostrativa solo en revisión. |
| 1 | `#terminos` | Página pública, reutilizando enlaces del pie y añadiendo el del registro. Título y «Contenido pendiente de revisión». Contenido/versionado publicado queda sujeto a aprobación posterior. |
| 1 | `#privacidad` | Aviso público independiente de la aceptación de términos. Pendiente, carga/error futuros y documento aprobado/versionado futuro. En etapa 2, enlace a derechos ARCO. |
| 2 | `#derechos-arco` | Entrada pública desde pie, aviso y cuenta. Información pendiente + formulario; vacío, errores de campo, enviando, indisponible, límite temporal y acuse recibido solo si lo confirma el servicio. |
| 2 | `#cuenta/privacidad` | Resumen de privacidad, enlaces legales, acceso al mismo formulario ARCO y lista propia de solicitudes: cargando, vacía, disponible, error, sesión vencida. Mantiene Mi cuenta seleccionada. |
| 2 | `#cuenta/privacidad/solicitudes/:id` | Detalle y seguimiento autorizado: cargando, disponible, no disponible/sin permiso, error y solicitud de información adicional. Identificador opaco; ninguna información personal en el fragmento. |
| 3 | `#cuenta/seguridad` | Cambio de contraseña existente y gestión opcional de llaves de acceso: carga, lista vacía, lista disponible, indisponibilidad, reautenticación requerida y error. Mantiene Mi cuenta seleccionada. |
| 3 | `#cuenta/contrasena` | Ruta vigente intacta, accesible también desde Seguridad; misma vista y controlador de cambio. |
| 3 | `#acceso` | Botón opcional «Acceder con llave de acceso» junto al acceso por correo/contraseña. Preparando, esperando dispositivo, comprobando, cancelado, no compatible o no disponible son estados de diseño; no se invoca el dispositivo. |
| 3 | resultado de verificación con sesión confirmada | Oferta opcional «Crear llave de acceso» / «Ahora no». Solo tras correo verificado **y** sesión válida confirmada por servicio; no al abrir directamente la ruta de verificación. |

Las nuevas páginas públicas reutilizarán `siteHeader`, `publicFooter`, marca, tipografía y botones; las de cuenta reutilizarán `AppViews.shell`, paneles y estados existentes. No se añade una quinta entrada principal. El formulario ARCO será una sola vista reutilizable; tampoco habrá un registro, una cuenta o un acceso alternativos exclusivos del modo de revisión.

Se mantienen HTML/CSS/JavaScript, MVC, Geist con Arial de respaldo, Liquid Glass, paleta y logo actuales. Se reutilizan botones, paneles Bento y sus alternativas sólidas; los ajustes serán locales a las nuevas vistas. No añadir bibliotecas, etiquetas decorativas ni explicaciones técnicas dentro de la interfaz de usuario.

**Enlace público `#seguridad`: decisión pendiente.** Se propone conservarlo como entrada pública a información de seguridad dentro del aviso, con contenido pendiente hasta su aprobación. No se redirigirá silenciosamente a una pantalla privada ni se creará otra sección principal. La decisión debe resolverse antes de implementar ese destino; no impide terminar esta planificación.

### Registro y páginas legales

Orden: correo, contraseña, confirmación, casilla «Acepto los Términos y condiciones de El Chilito», referencia separada «Consulta cómo utilizamos tus datos en el Aviso de privacidad», mensajes y envío. Identificar la casilla como obligatoria; nunca premarcarla. Error: «Debes aceptar los Términos y condiciones para continuar».

El botón puede seguir habilitado para explicar el error al intentar continuar. Sin marcar, tanto clic como Enter deben terminar en validación y **cero llamadas a `register`**. El estado ocupado bloquea envíos repetidos. Etiqueta, error y foco deben funcionar por teclado y lector de pantalla; la validación del servidor será además obligatoria al integrar. [Referencia técnica WAI: validación de formularios](https://www.w3.org/WAI/tutorials/forms/validation/).

Propuesta de lectura legal desde registro: abrir los documentos en otra pestaña con aviso accesible de ese comportamiento y `rel="noopener"`; así permanece el formulario original sin guardar contraseñas. La casilla no cambia al visitar o cerrar el documento. No persistir contraseña, código ni aceptación demostrativa en almacenamiento del navegador.

Mientras el contenido esté pendiente, el entorno normal debe explicar la indisponibilidad y no crear cuentas. Solo un adaptador de revisión explícito, separado del arranque normal, podrá representar el recorrido de aceptación con datos sintéticos y aviso visible de demostración. No transforma la casilla en consentimiento real. Antes de registros reales se exigirán documentos aprobados, versionados y publicados, y comprobación en servidor; no basta con ocultar o deshabilitar un botón.

Aceptar términos y consultar el aviso son acciones distintas. No se incorpora aceptación genérica de todos los tratamientos ni consentimiento de publicidad. No se redactan textos legales definitivos ni se declara cumplimiento normativo en esta etapa.

### ARCO público y Privacidad de Mi cuenta

Formulario propuesto: nombre de la persona solicitante, correo de contacto, derecho solicitado (acceso, rectificación, cancelación, oposición o «No sé cuál corresponde»), descripción, relación con una cuenta opcional e información a corregir cuando corresponda. No añadir nombre al registro de cuenta por esta razón. Validar formato y campos necesarios sin exigir que una persona que pide acceso conozca de antemano todos sus datos almacenados.

No exigir inicio de sesión, creación de cuenta ni aceptación de términos para presentar la solicitud. Identificación, representación y canal de contacto requieren definición: no solicitar documentos oficiales, archivos ni datos biométricos en esta entrega. Tampoco prometer cancelación automática de toda información.

Estados de seguimiento propuestos: `received` (recibida), `awaiting-information` (requiere información), `in-review` (en revisión) y `responded` (respondida). Son estados de producto por acordar, no plazos ni etapas legales certificados. Conservar fecha, descripción pública e historial suministrados por el servicio; la vista no hace avanzar el expediente por tiempo ni inventa fechas, folios o respuestas.

La persona sin cuenta necesitará un canal de seguimiento verificado aún por acordar. **Un folio no autentica** y no permite consultar datos por sí solo. Hasta resolverlo, se podrá revisar el diseño con escenarios locales, pero no ofrecer recepción o seguimiento reales. El mensaje de indisponibilidad nunca debe decir que la solicitud se recibió.

### Seguridad y passkeys

Correo y contraseña siguen disponibles; el código continúa reservado a verificación de registro y la recuperación sigue mediante enlace. La opción de llave de acceso no exige volver a autenticarse en cada cambio de ruta.

El texto de ayuda explicará que el dispositivo puede usar huella, rostro o su propio PIN, según su configuración. El sitio no crea un PIN, no captura biometría ni imita un diálogo del sistema operativo. Las etapas 0–4 no llaman a `navigator.credentials.create()` ni `navigator.credentials.get()` y no generan credenciales reales.

La gestión mostrará nombre de la llave, creación y último uso cuando el servicio los entregue; ausencia de datos no equivale a inventar un nombre o fecha. No afirmar que una llave pertenece a un único aparato: la estrategia de sincronización y compatibilidad queda por acordar. Crear o revocar requerirá en la futura integración reautenticación según política y una vía de recuperación; «Ahora no» no bloquea el acceso.

En revisión, los estados de creación/revocación y su confirmación serán sintéticos y explícitos; en modo normal, indisponibilidad. Cancelación y error genérico permitirán volver a correo/contraseña sin afirmar que la cuenta no tiene llaves. Se actualizará la lista solo después de confirmación, no antes.

## 4. Archivos previstos y responsabilidad MVC

Todos los caminos de la siguiente tabla son relativos a este repositorio. **Son cambios futuros propuestos, no archivos implementados en etapa 0.** No se renombra ni mueve ningún archivo existente.

| Archivo | Etapa | Motivo y límite |
| --- | --- | --- |
| `dist/modelo/acceso.js` | 1, 3 | Validar aceptación booleana, configurar política pendiente y normalizar estados de acceso/llaves sin llamadas al dispositivo. Conservar contraseña y código. |
| `dist/controlador/acceso.js` | 1, 3 | Leer `checked`, validar antes del envío, bloquear casilla mientras procesa, agregar referencia de versión, gestionar respuestas legales y opción de passkey, limpiar datos y cancelar al salir. |
| `dist/vista/acceso.js` | 1, 3 | Casilla, error asociado, enlaces legales y acción opcional de llave reutilizando formularios y resultados existentes. |
| `dist/vista/css/acceso.css` | 1, 3 | Ajustes acotados de casilla, textos legales, estados y acción opcional; sin una segunda implementación de botones. |
| `dist/modelo/servicio-acceso.js` | 1, 3 | Documentar/ampliar frontera de acciones de registro y llaves; mantener adaptador normal sin transporte. Corregir comentario de responsable al tocarlo. |
| `dist/modelo/privacidad.js` — nuevo | 1, 2 | Estado pendiente/versionado legal, validaciones y normalización ARCO, historial y campos permitidos; sin HTML ni política legal inventada. |
| `dist/modelo/servicio-privacidad.js` — nuevo | 1, 2 | Frontera `request(action, payload, {signal})` para documentos y ARCO, inyectable en revisión; no HTTP, base de datos ni correos en estas etapas. |
| `dist/vista/legales.js` — nuevo | 1 | Una plantilla pública para términos y aviso con contenido pendiente; reutilizar encabezado/pie, sin copiar portada. |
| `dist/vista/privacidad.js` — nuevo | 2 | Formulario ARCO compartido y vistas de lista/detalle, reutilizando paneles y estados existentes. |
| `dist/controlador/privacidad.js` — nuevo | 1, 2 | Coordinar estado legal y, después, eventos ARCO, consultas, errores, foco y cancelación. Un montaje con variante pública o de cuenta. |
| `dist/vista/css/privacidad.css` — nuevo | 1, 2 | Solo composición de lectura, formulario y seguimiento; usar tokens y componentes existentes, selectores acotados a estas vistas. |
| `dist/controlador/site.js` | 1–3 | Rutas públicas y subrutas de cuenta, identificador completo, títulos, foco y montaje/desmontaje; inyectar el adaptador de privacidad sin alterar el arranque normal. |
| `dist/vista/paginas.js` | 2; 1 si se acuerda `#seguridad` | Reutilizar enlaces legales, añadir ARCO al pie. No modificar portada, métricas, logo ni tarjetas del huerto. |
| `dist/vista/aplicacion.js` | 2, 3 | Accesos Privacidad/Seguridad desde cuenta y presentación de seguridad/llaves; misma estructura privada y cuatro destinos. |
| `dist/controlador/aplicacion.js` | 2, 3 | Montar privacidad/seguridad en la cuenta, conservar cambio de contraseña, cancelar solicitudes y limpiar eventos; incluir `select`/`textarea` en visibilidad del foco si procede. |
| `dist/vista/css/aplicacion.css` | 2, 3 | Ajustes puntuales de subapartados, foco y campos nuevos sobre navegación inferior; sin rediseñar huerto/avisos. |
| `dist/index.html` | 1, 2 | Cargar únicamente los módulos y CSS nuevos en orden de dependencias; actualizar referencias necesarias sin compilación. |
| `README.md`, `docs/INTEGRACION-BACKEND.md`, este documento | 0 y 4 | Reparto, alcance, contratos propuestos frente a vigentes y, finalmente, resultados de comprobaciones. |

`modelo/aplicacion.js`, `modelo/servicio-aplicacion.js`, las funciones de métricas/huerto de `vista/paginas.js`, `vista/icons.js`, `controlador/navigation.js` y los estilos base `site.css`/`geist-glass.css` se reutilizan sin cambios previstos. Si una prueba revela un defecto indispensable en un componente compartido, documentar el motivo y limitar el ajuste; no realizar limpieza global ni otra arquitectura.

Para demostrar estados en etapas posteriores se propone un punto de entrada local y adaptadores en `revision/` (ya excluido por `.gitignore`), cargando las mismas vistas/controladores de `dist/`. No se crea en etapa 0 ni se introduce un parámetro de URL que active simulación en el arranque normal. No se copian las pantallas antiguas de `disenios/sites-geist/revision/`. Los escenarios usarán solo información sintética, sin persistencia de credenciales ni acceso a servicios.

## 5. Propuesta de contratos para Rafael y Carolina

**Propuestas pendientes de acuerdo, sin endpoints implementados.** Conservar `request(action, payload, {signal})`; el transporte futuro traducirá HTTP a estos resultados. Los nombres actuales de autenticación se mantienen; no sustituir su contrato por el de esta propuesta sin actualizar controlador y validación.

### Reglas compartidas

- Identificadores opacos de texto; fechas de servicio en ISO 8601 con zona, mostradas en `es-MX`. El cliente no fija fechas de aceptación, recepción ni último uso.
- Distinguir `status` de una respuesta y `state` del documento, expediente o llave. Listas vacías, ausencia de datos y error son estados diferentes; estado desconocido termina en indisponibilidad, no éxito.
- Nuevas respuestas comunes propuestas: `validation-error` con `fieldErrors` permitidos por el modelo, `limited` con `retryAfterSeconds`, `unavailable`; para lecturas privadas, `unauthenticated`, `forbidden` o `not-found` con presentación que no exponga expedientes ajenos. Mantener los estados específicos vigentes de acceso.
- Repetir validaciones y autorización en servidor. La cuenta se determina desde la sesión, no desde un `accountId` aceptado del formulario. Confirmar sesión/CSRF, permisos, reautenticación y mapeo de 401/403 antes de integrar.
- Conservar `AbortSignal`, tiempos de espera y descarte de respuestas posteriores a abandonar una vista. Deshabilitar envíos repetidos; acordar idempotencia para solicitudes ARCO y operaciones de llaves antes del transporte real.
- No guardar contraseñas, códigos, tokens de recuperación, contenido ARCO o respuestas de credenciales en localStorage, URLs, registros de consola ni fixtures con datos reales. Un adaptador de revisión nunca comunica con el real.

### 5.1 Documentos y registro

| Acción / frontera | Entrada propuesta | Respuesta y efecto |
| --- | --- | --- |
| `legal-document` / PrivacyService | `kind: 'terms' \| 'privacy'`, versión opcional | `ready` + `document:{kind, version, state:'published', effectiveAt, content}`; `pending` + `document:{kind, version:null, state:'draft', effectiveAt:null, content:null}`; o `unavailable`. Contenido vacío nunca habilita registro. |
| `registration-policy` / PrivacyService | sin datos personales | `ready` + `canRegister`, `termsVersion`, `privacyNoticeVersion`; versiones nulas o documentos pendientes implican `canRegister:false`. El servidor sigue decidiendo al registrar. |
| `register` / AuthService | `email`, `password`, `termsAccepted:boolean`, `termsVersion`, `privacyNoticeVersion` | Mantener `accepted`, `password-rejected`, `limited`, `unavailable`; añadir `terms-required`, `legal-version-changed` y `registration-disabled`. `accepted` conserva respuesta neutral y contexto de verificación actual. |

`confirmation` sigue siendo solo validación local. `privacyNoticeVersion` registra qué aviso se mostró, no un consentimiento genérico. El servidor comprueba aceptación, versiones vigentes, publicación y contenido aprobado de ambos documentos; una bandera del navegador no autoriza el alta. Si cambia la versión durante el formulario, mostrarlo, recargar el documento y solicitar aceptación de la versión nueva, sin marcarla automáticamente. En revisión usar versiones inequívocamente sintéticas; nunca registrarlas como evidencia real.

Persistencia conceptual para Carolina: documento legal (`kind`, versión, estado, fecha de vigencia y referencia a contenido aprobado); evidencia de aceptación asociada a cuenta/solicitud de registro (versión de términos, fecha de servidor, referencia al aviso y evidencia mínima acordada). Resolver cuándo se vincula al alta verificada y cuánto se conserva. No añadir IP o información de dispositivo por defecto. No se propone SQL ni migración.

### 5.2 ARCO

| Acción / PrivacyService | Entrada propuesta | Resultado esperado |
| --- | --- | --- |
| `arco-create` | `requesterName`, `contactEmail`, `right: 'access' \| 'rectification' \| 'cancellation' \| 'opposition' \| 'unsure'`, `description`, `accountRelation?`, `requestedCorrection?`; clave de idempotencia por acordar | `accepted` + `receipt:{id, reference, receivedAt, state:'received'}` solo tras recepción confirmada; `validation-error`, `limited` o `unavailable` en los demás casos. Sin acuse válido no anunciar recepción. |
| `arco-list` | filtro/cursor opcionales; identidad obtenida de sesión | `ready` + `items`, `nextCursor` opcional. `items:[]` significa ausencia confirmada; no convertir error en lista vacía. |
| `arco-detail` | `id` | `ready` + expediente autorizado; `not-found`, `forbidden`, `unauthenticated` o `unavailable`. El folio/ID solo localiza, no concede acceso. |
| `arco-add-info` | `id`, `message`, referencia al requerimiento del servicio | `accepted` + historial actualizado cuando esté permitido; validación, sesión/permisos, conflicto o indisponibilidad. Sin adjuntos ni avance de estado decidido por cliente. |

Forma de seguimiento propuesta: `{id, reference, right, state, receivedAt, updatedAt, publicSummary, history:[{state, at, publicMessage}], informationRequest?}`. Definir con el responsable qué texto se puede mostrar, qué campos se minimizan en listas y qué información permanece interna. Ningún identificador del ejemplo representa un expediente real.

La lectura y aportación sin cuenta necesitarán una autorización temporal por canal verificado. Su contrato, caducidad y acreditación quedan pendientes: no usar la combinación correo+folio como contraseña, ni reciclar automáticamente el código de registro. No se implementan correos o enlaces para ello en estas etapas.

Persistencia conceptual: solicitud con cuenta opcional, contacto, tipo, descripción, fechas y estado; historial separado, requerimientos y respuesta. Asociación de identidad/representación, adjuntos, roles internos y retención quedan pendientes de decisión. Una solicitud ARCO no se guarda como aviso IoT. La relación con una cuenta declarada por la persona no prueba que sea titular.

### 5.3 Llaves de acceso

Todas las acciones siguientes son una **frontera de integración posterior** en AuthService. En las etapas visuales sus respuestas solo podrán ser indisponibilidad o escenarios sintéticos inyectados.

| Acción propuesta | Entrada | Respuesta / condición futura |
| --- | --- | --- |
| `passkey-register-begin` | nombre opcional de la llave; sesión y reautenticación según política | `ready` + `operationId`, `publicKeyOptions`, `expiresAt`; requiere correo verificado y sesión válida |
| `passkey-register-finish` | `operationId`, respuesta pública serializada de credencial | `created` + `credential`; no mostrar creada antes de validación de servidor |
| `passkey-login-begin` | contexto del acceso sin contraseña; decidir si es descubrible o parte de correo | `ready` + `operationId`, opciones y caducidad; respuesta pública que no enumere cuentas |
| `passkey-login-finish` | `operationId`, respuesta pública serializada de autenticación | `authenticated` solo tras validación y creación de sesión; entonces navegar a Mi huerto |
| `passkey-list` | sin identificador de cuenta del cliente | `ready` + `items:[]` o metadatos de llaves propias |
| `passkey-revoke` | `id` de llave propia | `revoked` tras autorización y política de recuperación; `reauthentication-required`, `recovery-required` o error si no procede |

Respuestas adicionales por acordar: `reauthentication-required`, `verification-required`, `expired-operation`, `invalid-response`, `limited` y `unavailable`. Cancelación, incompatibilidad y espera del dispositivo son estados de presentación, no pruebas de inexistencia de una llave. Caducidad y política se suministran desde servicio; no fijar valores ficticios.

Para la integración real, el servidor tendrá que emitir desafíos caducables de un solo uso, asociarlos a operación/cuenta según el flujo y verificar desafío, origen permitido, RP ID, firma y requisitos de verificación del usuario. Acordar serialización de binarios y biblioteca de servidor antes del transporte. La aplicación recibirá material público, nunca clave privada, huella o PIN. Estas obligaciones se apoyan en los procedimientos de registro y autenticación de [WebAuthn, secciones 7.1 y 7.2](https://www.w3.org/TR/webauthn-2/#sctn-rp-operations); aquí no se implementan.

Metadatos propuestos para la interfaz: `{id, name, createdAt, lastUsedAt}` con último uso nulo permitido. Persistencia conceptual para Carolina: múltiples credenciales públicas por cuenta, identificador, clave pública, metadatos necesarios para el verificador elegido, nombre y fechas/revocación. No guardar PIN, biometría ni claves privadas. Desafíos temporales no requieren decidir ahora una tabla PostgreSQL. Dominio, HTTPS, RP ID, compatibilidad, sesión y recuperación deben quedar acordados antes de activar WebAuthn.

## 6. Criterios de aceptación por etapa

| Etapa | Entrega comprobable | Condición de cierre |
| --- | --- | --- |
| **0 — revisión y planificación** | Inventario verificado en código, revisión local/remota, rutas/estados, archivos MVC, contratos propuestos, responsables y dependencias | Solo documentos modificados; código y cambios del equipo conservados. Sin capturas, implementación ni push. **Es la única etapa ejecutada ahora.** |
| **1 — registro y legales** | Casilla nativa sin marcar, error asociado, rutas públicas `#terminos` y `#privacidad`, enlaces heredados reutilizados | Clic/Enter sin aceptación no llaman a `register`; con aceptación y documentos pendientes no crean cuentas. Teclado, foco, cambio de versión, bloqueo ocupado y regreso desde lectura legal comprobados. Mismos formularios en revisión; aviso demostrativo y ningún transporte real. |
| **2 — privacidad y ARCO** | Entrada pública, formulario compartido, Privacidad en cuenta y lista/detalle con historial | Presentación sin exigir cuenta/términos, errores accesibles, vacío distinguido de error, folio/fecha solo de respuesta, seguimiento protegido en contrato. No adjuntos ni recepción falsa; rutas profundas, foco y cancelación funcionan con escenarios de revisión. |
| **3 — seguridad y passkeys** | Seguridad dentro de cuenta, contraseña conservada, opción de llave en acceso y oferta posterior a verificación/sesión | Correo/contraseña y recuperación siguen presentes; «Ahora no» continúa el recorrido; cancelar/error no revela cuentas; cero llamadas WebAuthn y cero credenciales reales. Estados de lista/crear/revocar exclusivamente demostrativos mientras no haya servicio. |
| **4 — revisión y documentación** | Recorridos integrados y registro textual de pruebas, guía actualizada y pendientes claros | Navegación anterior y nueva, teclado, textos largos, errores y adaptabilidad comprobados; revisión separada del arranque normal. No da por integrada seguridad, validez legal, correo, PostgreSQL ni IoT. |

Cada etapa visual deberá comprobar 320, 390, 768, 1024 y 1440 px, textos al 200 %, ausencia de desbordamiento horizontal, orden de Tab, activación con teclado, foco visible/no tapado por encabezado o barra inferior y respuesta al teclado móvil. Comprobar `select` y `textarea`, lectores de pantalla para errores/estados, áreas táctiles de al menos 44 px conforme al diseño, contraste de texto normal de al menos 4.5:1 sobre sus fondos, movimiento reducido, material sólido y colores forzados. Son pruebas pendientes, no resultados de esta etapa documental.

Matriz mínima de regresión futura: portada y sus anclas; menú; acceso válido/erróneo/indisponible; registro y verificación/reenvío; recuperación por enlace válido/inválido/vencido; cambio de contraseña; cuatro destinos y selección móvil; aviso/lista/detalle; cierre y sesión vencida; Atrás/Adelante, recarga, entrada por subruta e identificador inválido; abandonar una vista mientras responde el servicio. Revisar huerto sin modificar datos, mediciones ni estados existentes. Comprobar también que una simulación no deja sesión, aceptación o expedientes persistentes en el entorno normal.

## 7. Responsabilidades y decisiones pendientes

Reparto actualizado por instrucción del usuario; sustituye las referencias documentales de la entrega del 14 de octubre que asignaban backend a Kevin.

| Área | Responsable / participación | Resultado esperado |
| --- | --- | --- |
| Diseño, frontend y revisión UX | Rafael y Gabriela | Aprobar recorridos y ejecutar cada etapa solicitada conservando MVC y sistema visual |
| Backend | **Rafael** | Acordar contratos, validación de servidor, sesión/autorización, correos y futuras operaciones WebAuthn; implementación fuera de estas etapas |
| PostgreSQL | **Carolina** | Diseñar persistencia de versiones/aceptaciones, solicitudes/historial y llaves públicas con las políticas acordadas; sin crear base de datos ahora |
| Logo | Carolina | Se conserva el recurso existente; sin cambios en esta entrega |
| Responsable de datos y revisión jurídica | Por designar | Identidad/contacto, textos definitivos, acreditación, representación, procedimiento, conservación y aprobación de publicación |
| Documento definitivo de electrónica | Entrega y aprobación pendientes; responsable por confirmar | Contrastar componentes y contrato de mediciones antes de cualquier cambio IoT |

| Decisión / dependencia | Qué bloquea | Tratamiento en las etapas visuales |
| --- | --- | --- |
| Textos legales, responsable, contacto, versiones y aprobación | Registro real y publicación de documentos definitivos | Títulos y contenido pendiente; aceptación solo demostrativa |
| Procedimiento ARCO: acreditación/representación, respuesta, plazos, retención y seguimiento sin cuenta | Recepción y seguimiento reales | Formularios/estados sintéticos, sin documentos oficiales ni fechas legales inventadas |
| Límites y obligatoriedad final de campos ARCO, estados e información visible | Contrato definitivo y validación del servidor | Propuesta revisable; no imponer formatos arbitrarios para nombres ni plazos |
| Destino público `#seguridad` | Resolver todos los enlaces legales heredados | Conservar ruta hasta acordar su contenido/alias público; no llevar a área privada |
| Framework Python, endpoints, sesión, restauración, CSRF, política de contraseña/código | Integración de autenticación y autorización | Django sigue siendo propuesta; no decidir framework ni exigir OTP en cada acceso |
| Versiones de documentos y vínculo aceptación–alta verificada | Evidencia real en PostgreSQL | Contrato conceptual; sin aceptación persistente ni migración |
| Dominio/HTTPS/RP ID, política de llaves y reautenticación/recuperación | Passkeys reales | Diseñar estados; no WebAuthn, credenciales ni PIN propio |
| Documento definitivo de electrónica | Cambios de métricas, sensores, unidades, calidad o controles | Congelar IoT actual; registrar cualquier discrepancia para una entrega separada |
| Alcance y fecha de entrega con las integraciones nuevas | Compromiso de calendario | El plan menciona el 19 de octubre; no se asume aprobado ni suficiente para activación real |

No se necesita resolver estas decisiones para cerrar la etapa 0. Antes de implementar cada etapa se confirmarán únicamente las que afecten su navegación, funcionalidad o tecnología; los ajustes rutinarios se resolverán dentro del alcance solicitado.

## 8. Comprobaciones y límites de esta entrega documental

Se examinó el código y se contrastó el remoto por lectura, sin traer ni aplicar cambios. Se comprobaron enlaces locales de los documentos, diferencias y preservación de los 23 archivos de `dist/` mediante SHA-256. El índice y HEAD permanecen sin cambios; las 27 entradas de trabajo de la copia original se preservan.

No se ejecutaron pruebas visuales o funcionales en navegador, lector de pantalla, dispositivos, autenticación real o WebAuthn; no se generaron capturas. La matriz de rutas se deriva del código y la revisión de las importaciones no sustituye una prueba de ejecución. Las nuevas rutas, formularios y servicios están **planificados, no disponibles**. Las comprobaciones visuales citadas en la guía anterior corresponden a la entrega previa, no a esta revisión.

Al cerrar la etapa 0 se esperó la solicitud de etapa 1. Su entrega se registra por separado; la **ETAPA 2 — privacidad y ARCO** no se inicia automáticamente.

# ETAPA 1 — Registro y páginas legales

Fecha: 17 de octubre de 2026. Implementación local sobre `f560535`, rama `main`, exclusivamente en `entregas/ProyectoWEBCHILITO`. Se conservaron los cambios documentales de etapa 0. Sin commit ni push.

## Resultado

- Registro con casilla nativa, inicialmente desmarcada, después de confirmar contraseña. Etiqueta: «Acepto los Términos y condiciones de El Chilito». El error «Debes aceptar los Términos y condiciones para continuar» se asocia a la casilla, con foco y corrección mediante teclado.
- Lectura estricta de `checked` como booleano. Clic o Enter sin marcar no ejecutan `register`; `required` se complementa con validación del modelo/controlador porque el formulario usa `novalidate`.
- Enlaces identificables a términos y aviso en otra pestaña, con aviso visible y accesible. El formulario original conserva sus datos en memoria; no se guardan contraseñas para ello. La aceptación no se marca al visitar un documento.
- Rutas públicas `#terminos` y `#privacidad`, reutilizando los enlaces del pie y una sola plantilla. Ambas indican contenido pendiente de aprobación. No se inventan cláusulas, responsables, contactos, versiones, fechas ni compromisos legales.
- Estado normal de registro bloqueado: documentos pendientes y servicio sin conectar. No se crean cuentas, se envían correos ni se registran aceptaciones, incluso con la casilla marcada.
- Entrada local de revisión con escenarios identificados como demostrativos. Reutiliza los mismos formularios/controladores y permite llegar a verificación, probar un código incorrecto, reenviar de forma simulada y terminar sin sesión real.
- Conservados Geist/Arial, Liquid Glass, colores actuales, logo, recursos y portada; dashboard, métricas y los cuatro destinos no se modificaron. `#seguridad` sigue siendo un pendiente público separado.

## Archivos y organización MVC

| Archivo | Cambio | Responsabilidad |
| --- | --- | --- |
| `dist/modelo/acceso.js` | Modificado | Validar aceptación estrictamente booleana en registro, sin cambiar política de contraseña/código |
| `dist/modelo/privacidad.js` | Creado | Estado pendiente de los documentos, versiones nulas y bloqueo local de registro |
| `dist/modelo/servicio-acceso.js` | Modificado | Mantener frontera sin transporte; `register` devuelve `registration-disabled`; actualizar comentario de responsable a Rafael |
| `dist/vista/acceso.js` | Modificado | Casilla, errores, enlaces legales y distinción entre registro pendiente y demostración |
| `dist/vista/legales.js` | Creado | Plantilla pública común de términos y aviso, usando encabezado, paneles y pie existentes |
| `dist/vista/css/acceso.css` | Modificado | Estilos acotados de casilla/mensajes, foco y movimiento reducido en botones de acceso |
| `dist/vista/css/privacidad.css` | Creado | Composición legal adaptable, encabezado y espacio para foco; material sólido, movimiento reducido y colores forzados |
| `dist/controlador/acceso.js` | Modificado | Leer `checked`, bloquear envíos sin aceptación y altas reales, gestionar ocupado/error/reintento/cambio de términos y limpiar contraseñas |
| `dist/controlador/site.js` | Modificado | Resolver las dos rutas públicas y pasar la opción de revisión explícita; conservar las demás rutas |
| `dist/index.html` | Modificado | Cargar modelo, vista y CSS legales y actualizar referencias de los archivos cambiados |
| `revision/index.html` | Creado, excluido de Git | Entrada independiente con aviso y controles demostrativos; referencias directas a `dist/` |
| `revision/escenarios.js` | Creado, excluido de Git | Adaptador sintético en memoria, escenarios y controles de revisión, sin transporte ni persistencia |
| `revision/revision.css` | Creado, excluido de Git | Composición de la barra de revisión; no se carga en el sitio normal |
| `revision/comprobar-etapa1.cjs` | Creado, excluido de Git | Comprobaciones reproducibles con Playwright disponible en el entorno; no añade dependencias al sitio |
| `revision/resultado-etapa1.json` | Generado, excluido de Git | Resultados textuales de las comprobaciones, sin capturas |
| `README.md`, `docs/INTEGRACION-BACKEND.md` | Modificados | Apertura de ambas versiones, reparto y contrato vigente frente a propuestas futuras |
| `docs/PLAN-INTEGRACIONES-FRONTEND-ETAPA-0.md` | Modificado | Conservar revisión histórica y enlazar la entrega autorizada de etapa 1 |
| `docs/ENTREGA-ETAPA-1.md` | Creado | Esta entrega, comprobaciones y pendientes |

No se crearon `servicio-privacidad.js` ni `controlador/privacidad.js`: en esta etapa los documentos son estados locales estáticos, sin carga asíncrona ni formulario ARCO. Su presentación la coordina el router existente; añadir ahora servicios sin operaciones duplicaría responsabilidades. Tampoco se amplió el router para subrutas ARCO, que corresponden a otra etapa. No se movió ni renombró ningún archivo.

## Abrir ambas versiones

PowerShell, versión normal:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory "C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO\dist"
```

- [Registro normal](http://127.0.0.1:8766/index.html#registro)
- [Términos y condiciones](http://127.0.0.1:8766/index.html#terminos)
- [Aviso de privacidad](http://127.0.0.1:8766/index.html#privacidad)

Otra terminal, revisión local:

```powershell
python -m http.server 8767 --bind 127.0.0.1 --directory "C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO"
```

[Abrir revisión demostrativa](http://127.0.0.1:8767/revision/index.html#registro). Mantener las terminales abiertas; Ctrl+C detiene cada servidor. Si el puerto ya sirve esta copia, reutilizarlo en lugar de iniciar otro proceso. Ctrl+F5 recarga recursos en una pestaña anterior.

En «Controles y datos de revisión», elegir escenario y pulsar «Rellenar datos ficticios». Se usan `revision@example.org`, `Huerto!Revision2026` y el código sintético `246810`. La casilla se marca manualmente. Tras un error se limpian las contraseñas: volver a rellenarlas para reintentar. Estos datos no son credenciales funcionales. La política de contraseña/código no se cambió.

Escenarios: continuar a verificación, indisponibilidad, primer intento fallido y segundo correcto, registro no habilitado y cambio de términos que desmarca la casilla. En todos, los documentos siguen pendientes; el escenario de cambio no publica ni inventa otra versión. No se guarda evidencia legal. La recarga pierde el desafío de revisión y cualquier aceptación; para repetir, reiniciar registro. Las otras operaciones conservan indisponibilidad.

`revision/` sigue excluida por `.gitignore`, no hay copias alternativas de vistas y el sitio normal no carga sus scripts. No se puede activar mediante `?review=true` u otro parámetro. La revisión nunca utiliza el adaptador real, WebAuthn, almacenamiento persistente ni un servicio externo.

## Comprobaciones

Las 19 comprobaciones finalizaron correctamente en un navegador Chromium independiente con datos sintéticos y un perfil temporal. El archivo `revision/resultado-etapa1.json` registra cada resultado. Se comprobó además el foco claro de los enlaces sobre el pie oscuro de las páginas legales. No se generan imágenes.

- Modelo: rechazo de `false`, valor ausente y texto `on`; solo `true` satisface la aceptación.
- Formulario: clic/Enter sin aceptación, cero llamadas a `register` mediante adaptador espía, asociación del error, foco en casilla, corrección con Espacio y envío después de aceptar.
- Bloqueo normal incluso con aceptación y adaptador que podría responder éxito; ningún parámetro de revisión habilita simulación.
- Lectura de ambos documentos en otra pestaña, sin `opener`, conservando los valores del formulario original; rutas directas, recarga, Atrás/Adelante y retorno a portada.
- Ocupado: casilla y botón bloqueados, envíos duplicados ignorados, controles restaurados y contraseñas limpiadas después de error; reintento correcto.
- Revisión: código incorrecto, reenvío simulado, verificación correcta sin sesión; cambio de términos desmarca y exige nueva aceptación; no verificación al abrir directamente sin desafío; cancelación de petición al abandonar registro.
- Acceso y recuperación normales siguen mostrando indisponibilidad; restablecimiento sin enlace muestra error, y el token de un enlace de revisión se retira de la URL.
- Anchos 320, 390, 768, 1024 y 1440 px: sin desbordamiento en registro y documentos, tanto normal como revisión; casilla nativa sin deformación, etiqueta táctil, título libre del encabezado; acceso/recuperación/huerto/cuenta conservan disposición y cuatro entradas, con barra inferior hasta 768 px.
- Texto aumentado al 200 % y cadenas largas en las vistas nuevas: sin desbordamiento; Tab/Espacio, foco visible, espacio del encabezado y salto al contenido; ventana reducida a 390×400 como aproximación de espacio con teclado.
- Contraste de textos nuevos sobre fondo claro, movimiento reducido, paneles/encabezado sólidos y casilla nativa en colores forzados; sin errores JavaScript ni recursos fallidos. Sin peticiones de servicios, cookies ni datos en localStorage/sessionStorage.

Las comprobaciones detectaron prioridades CSS heredadas que mantenían la transición del botón de registro y el vidrio oscuro del encabezado legal. Se corrigieron en estilos específicos de acceso y páginas legales, junto con el foco claro del pie oscuro, sin reformar el sistema global.

Límites: pruebas de DOM, estilos calculados y comportamiento en Chromium. No se hizo inspección mediante capturas, prueba manual con lector de pantalla, teclado de un teléfono físico ni verificación completa en otros navegadores. No se afirma certificación de accesibilidad. No se prueban backend, correos, aceptación jurídica ni cuentas reales porque no existen en esta entrega.

## Pendientes y cierre

Rafael desarrollará el backend y Carolina PostgreSQL. Antes de registrar personas reales deben aprobarse los documentos, identificarse responsable/contacto, acordarse versiones y evidencia mínima, y validarse todo en servidor. La bandera local no sustituye autorización de servidor. La política de contraseña/código y Django siguen pendientes de acuerdo.

No se implementaron ARCO, privacidad de cuenta, seguridad/passkeys, base de datos, correos, notificaciones ni servicios. No se alteraron métricas o componentes IoT, ni Notion. No se hizo commit, push o publicación. **La etapa 2 queda pendiente de solicitud explícita.**

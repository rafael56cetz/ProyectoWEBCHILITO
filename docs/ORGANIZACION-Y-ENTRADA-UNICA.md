# Organización independiente y entrada única

Fecha: 17 de octubre de 2026. Alcance: trasladar por copia verificada y unificar el frontend existente, sin backend, PostgreSQL, electrónica, funciones nuevas o publicación.

## Fuente activa y respaldo

- Activa: `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`.
- Entrada: `dist/index.html`.
- Enlace principal: [El Chilito](http://127.0.0.1:8766/index.html).
- Respaldo conservado: `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO`.

La ruta de Documentos comunicada por Windows es `C:\Users\rafae\OneDrive\Documentos`, padre del destino. El destino no existía; no se sobrescribió otro proyecto. El origen contiene etapas 1–4 y el ajuste posterior de entrada libre `previewNavigation`, verificado en README/controladores/entrada. Se leyeron las instrucciones aplicables; no se encontró AGENTS en los antecesores examinados ni dentro del proyecto.

La raíz tiene `dist/` (fuentes editables sin compilación), `docs/`, `revision/`, README, configuración e historial Git. Las vistas están en `dist/vista/`, estilos en `dist/vista/css/`, imágenes/fuentes en `dist/vista/img/` y `dist/vista/fonts/`, controladores en `dist/controlador/` y modelos/servicios en `dist/modelo/`.

## Copia verificada antes de editar

`revision/copia-verificada.json` registra origen/destino, rutas, bytes, huellas SHA-256 y exclusiones. Se copiaron **121 archivos, 5 276 450 bytes**, incluido `.git/` completo y sus referencias/objetos/configuración. Antes de editar se verificaron todas las huellas y la igualdad de HEAD, rama, remoto y estado Git completo, incluidos archivos nuevos y cambios sin confirmar.

HEAD/rama conservados: `f5605359cdff0fb596a63cfc0c352026fb5060e2`, `main`. Remoto conservado: `https://github.com/rafael56cetz/ProyectoWEBCHILITO.git`. Sin commit, push o cambios de remoto. No hay submódulos, alternates ni trabajo enlazado que dependan del origen. No se usó un clon como sustituto de los cambios locales.

Exclusiones: `debug.log`, `revision/servidor-local.log` y `revision/servidor-local-error.log`, registros desechables. No se encontraron archivos de secretos, entornos o cachés dentro del proyecto. No se copiaron herramientas instaladas fuera de la carpeta; Python/Node/Playwright se usan desde el equipo y son reconstruibles. No se muestran secretos.

Tras comprobar la copia, todos los ajustes se hicieron en el destino. El origen no se borró ni se añadió una marca que alterara su contenido: este documento declara que deja de ser activo. La comprobación final contrasta los archivos del respaldo con el manifiesto inicial.

## Unificación y responsabilidad MVC

`revision/` aportaba respuestas ficticias de registro/verificación, ARCO y llaves, selección de errores, herramientas y evidencias. No tenía otras vistas: ya reutilizaba las de `dist/`. Se aprovechó ese trabajo, sin crear copias de pantallas.

- La única aplicación arranca en `dist/index.html`.
- Las respuestas ficticias se trasladan a fábricas en `dist/desarrollo/`: `comun.js`, `acceso.js`, `privacidad.js`, `seguridad.js`, `aplicacion.js` e `inicio.js`. No realizan transporte, no acceden a una base de datos y no guardan entradas del usuario.
- `inicio.js` inyecta los adaptadores sintéticos en `SiteController`, con `review:true` para los avisos de simulación y `previewNavigation:true` para la entrada/salida libre. No se seleccionan por parámetros de URL.
- La entrada anterior `revision/index.html`, sus controles y CSS se conservan como texto en `revision/historico/`; ya no hay otra página que abrir ni otro servidor.
- Las pruebas anteriores y sus evidencias se mantienen. Los scripts que dependían de los dos servidores están archivados como históricos; las pruebas activas usan solo 8766 y comprueban los casos de error directamente con las mismas fábricas/controladores.
- Las vistas siguen en `vista`, coordinación/eventos en `controlador` y normalización/validación/fronteras futuras en `modelo`. No se cambia framework o sistema de compilación.

El acceso «Iniciar sesión» no lee/valida/envía lo escrito para autenticar: navega al huerto y restablece el formulario. «Cerrar sesión» regresa al acceso sin consultar el servicio. Se conserva la validación de registro (correo, confirmación, términos booleanos), recuperación y formularios ARCO.

El registro ficticio muestra el código de simulación `246810`; la oferta de llave puede continuarse con «Ahora no». Recuperación permite revisar la misma pantalla de restablecimiento mediante una referencia ficticia temporal que no va a la URL. Cambiar contraseña solo muestra simulación, sin guardar valores. ARCO usa acuses/historial ficticios; Seguridad usa metadatos de ejemplo. Los resultados indican simulación y se borran al recargar. Huerto mantiene el estado de espera y las lecturas ausentes. Avisos puede recorrerse con su estado vacío, sin inventar medidas.

### Qué deberá sustituirse cuando se autorice el backend

La entrada libre y los módulos `desarrollo` no son autenticación. Habrá que retirar esa composición, configurar `previewNavigation:false` y conectar los adaptadores futuros con sesión/autorización en cada operación. Las referencias `previewCode`, `previewResetToken` y la respuesta de llave `demonstration` son exclusivamente herramientas del recorrido: no deben aceptarse como credenciales, verificaciones o respuestas WebAuthn de producción.

Los contratos y decisiones siguen en [INTEGRACION-BACKEND.md](INTEGRACION-BACKEND.md). No se activan registro real con documentos vacíos, recepción ARCO, correo o credenciales reales. No se define SQL, endpoints, RP ID, política jurídica o un framework nuevo.

## Servidor identificado y nuevo arranque

El puerto 8766 estaba ocupado por Python **PID 19276**, invocado desde una carpeta relativa. Se contrastaron por huella `index.html`, `controlador/site.js` y `controlador/acceso.js`: coincidían con `IOTCHILITO/disenios/sites-geist/dist`, no con la entrega elegida. Se volvió a verificar proceso/comando/contenido antes de detener únicamente ese servidor Python. No se cerraron aplicaciones ajenas.

Se inició un único servidor Python oculto, enlazado a `127.0.0.1`, con directorio absoluto del destino. No se usa 8767. Para reiniciarlo:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web'
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

No iniciar otro si el puerto ya está sirviendo esta carpeta. No se publica el sitio o habilita acceso externo. Las pruebas contrastan el archivo servido con el archivo de entrada local.

## Pruebas actuales y preservación

Las pruebas afectadas son `revision/comprobar-navegacion-diseno.cjs` y `revision/comprobar-frontend-unificado.cjs`, coordinadas por `revision/comprobar-integraciones.cjs`. Las baterías anteriores permanecen en `revision/historico/`, con expectativas históricas sin atribuirles el arranque nuevo.

En este equipo:

```powershell
$env:NODE_PATH = 'C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH = 'C:\Users\rafae\AppData\Local\ms-playwright'
node revision/comprobar-integraciones.cjs
```

No se añaden dependencias a la aplicación. Los informes actuales llevan fecha, raíz activa, única URL, resultados y huellas de runtime; se distinguen de la evidencia histórica de etapas 1–4. Resultado final: **28 comprobaciones aprobadas, 0 fallidas** (11 de entrada/navegación y 17 grupos de recorridos integrados). Se revisaron clic y Enter con campos vacíos o arbitrarios, salida, registro/verificación/recuperación, ARCO, llaves, errores y cancelación, recarga e historial, teclado, tamaños de 320 a 1440 px, movimiento reducido y alternativa sólida. Se verificaron ausencia de errores de JavaScript, llamadas a servicios reales, persistencia de credenciales e invocaciones WebAuthn; además se realizaron recorridos básicos en Firefox y WebKit. Dos fallos iniciales eran supuestos incorrectos de las pruebas (una propiedad reservada del navegador y un control de menú inexistente en esa vista); se corrigieron las pruebas y se repitieron únicamente los grupos afectados, sin cambiar el producto para satisfacerlos. Los informes identifican esas reejecuciones. No se generan capturas o imágenes.

`revision/verificacion-traslado-final.json` registra la preservación de los 121 archivos del origen, HEAD/remoto/configuración Git y .gitignore, 21 archivos protegidos sin cambios, 11 recursos servidos contrastados por SHA-256, una sola entrada y las dos baterías aprobadas. Los estilos, fuentes, imágenes y logo existentes se conservan. `git diff --check` no encontró errores de espacios. README y documentación de organización se cerraron después de esas pruebas, sin cambios posteriores de runtime.

Pendiente: revisión manual en teléfonos/teclados reales y lectores de pantalla; backend, PostgreSQL, documentos/procedimientos legales, configuración de llaves y documento definitivo de componentes. Ninguna de esas implementaciones está autorizada por este traslado. Rafael desarrollará backend; Carolina PostgreSQL; Rafael y Gabriela frontend/revisión visual.

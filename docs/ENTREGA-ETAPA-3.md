# ETAPA 3 — Seguridad de la cuenta y llaves de acceso

Fecha: 17 de octubre de 2026. Alcance: interfaces y contratos para integración posterior, dentro de `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO`. Base conservada: `main`, commit `f5605359cdff0fb596a63cfc0c352026fb5060e2`, con los cambios locales de las etapas 0–2. No se hizo commit, push o publicación. La etapa 4 no se ejecuta.

## Revisión previa y preservación

Se revisaron la solicitud de esta etapa, README, plan de etapa 0, entregas 1 y 2, guía de integración, estado de Git y organización MVC. No se encontraron instrucciones AGENTS aplicables en los antecesores examinados ni dentro de esta copia. Se registraron las huellas de los archivos de `dist/` antes de editar en `revision/base-etapa3.json` para contrastar la preservación.

Se conservan HTML/CSS/JavaScript, Geist, colores, Liquid Glass, logo, recursos y cuatro entradas principales, incluida la barra inferior móvil. Seguridad es un subapartado de Mi cuenta, junto a Privacidad. Los cambios se acotan a acceso, cuenta, montaje/rutas, un componente de Seguridad y revisión/documentación. No se modifica el servicio/modelo IoT, métricas, dashboard, portada, documentos legales, Blender, Notion ni bases de datos.

## Implementado

| Punto de entrada | Resultado |
| --- | --- |
| Mi cuenta → `#cuenta/seguridad` | Acceso al cambio de contraseña existente, explicación de llaves, crear, lista de metadatos y quitar con confirmación dentro de la página |
| `#cuenta/contrasena` | Mismo formulario/controlador de contraseña; no existe una implementación adicional |
| `#acceso` | «Acceder con llave de acceso» fuera del formulario tradicional; no exige ni envía correo/contraseña; cancelación/error permite volver a ese formulario |
| Resultado verificado con sesión confirmada | Invitación opcional a crear una llave, montada en la misma vista de verificación; «Ahora no» continúa a Mi huerto |
| Resultado verificado sin sesión confirmada | Resultado conservado con enlace a iniciar sesión, sin invitación |

`#seguridad` público sigue siendo el destino pendiente previo, separado de `#cuenta/seguridad`; no se convierte en gestión privada. Una subruta sobrante de Seguridad muestra página no disponible sin consultar llaves.

La lista distingue carga, vacío confirmado, datos disponibles, error, indisponibilidad, sesión vencida, reautenticación, recuperación y verificación requeridas. Nombre/fechas ausentes se indican como ausencia, sin inventarlos ni afirmar que la llave nunca se usó. La explicación no limita una llave a un único aparato. El dispositivo podrá usar huella, reconocimiento facial o su propio PIN en la integración futura; no se pide un PIN de El Chilito ni se captura biometría.

Los pasos de creación/acceso son preparación, espera demostrativa y comprobación. Se contemplan cancelación, no compatible/no disponible, vencimiento, error y confirmación. La gestión de retirada mantiene la llave durante la operación; solo una confirmación válida del servicio permite actualizar la lista. Se consulta nuevamente tras crear/quitar para obtener el estado del servicio, sin completar la lista con metadatos inventados.

## Abrir sin cuenta real

Los dos servidores se sirven únicamente en `127.0.0.1`. Desde la raíz de esta copia:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

En otra terminal, para la revisión:

```powershell
python -m http.server 8767 --bind 127.0.0.1
```

No ejecutar un segundo servidor en un puerto que ya esté ocupado por esta misma copia. El servidor estático únicamente entrega archivos; no conecta el backend.

### Recorridos de revisión

1. [Seguridad de Mi cuenta](http://127.0.0.1:8767/revision/index.html#cuenta/seguridad). Abre directamente sin contraseña. En «Controles y datos de revisión» → «Seguridad y llaves de acceso», elegir la respuesta deseada. La opción inicial permite crear y quitar; la retirada pide confirmar. «Lista vacía confirmada» permite comprobar que vacío y error son estados distintos.
2. [Acceso con llave](http://127.0.0.1:8767/revision/index.html#acceso). Pulsar «Acceder con llave de acceso» sin llenar el formulario de contraseña. Elegir escenario antes de iniciar. Con respuesta correcta se ofrece «Continuar a Mi huerto». Tras cancelar/error, «Usar correo y contraseña» devuelve el foco al correo existente.
3. [Oferta tras registro y verificación](http://127.0.0.1:8767/revision/index.html#registro). En los controles, pulsar «Registro: oferta con sesión ficticia». Pulsar «Rellenar datos ficticios», marcar términos manualmente y enviar. Verificar con el código ficticio `246810`. Entonces aparecen «Crear llave de acceso» y «Ahora no». Este último permite continuar de inmediato o cancelar una creación en curso. Si se crea y el servicio ficticio confirma, aparece «Continuar a Mi huerto».
4. Para el mismo recorrido sin oferta, pulsar «Registro: sin sesión confirmada», completar el registro ficticio y verificar con el mismo código. Termina en el resultado existente con enlace al acceso. Abrir `#verificar` directamente, regresar después de continuar o recargar no concede verificación ni sesión.

La barra identifica la demostración. Los escenarios incluyen lista vacía/con datos/error, indisponibilidad, creación/acceso cancelado o fallido, método no compatible, confirmaciones incompletas, revocación rechazada, sesión vencida, reautenticación, recuperación o verificación requerida, operación vencida y pasos lentos. El selector reinicia los metadatos sintéticos al cambiar de escenario. El modo lento permite observar los pasos o cancelar.

Todos los ejemplos son sintéticos en memoria. No se guardan credenciales, sesiones, PIN, contraseñas o biometría en almacenamiento persistente. Las llaves nuevas y operaciones ficticias se descartan al recargar. El adaptador y el puente de interacción están únicamente en `revision/`, excluida de Git por la regla existente y separada del arranque normal.

### Versión normal

- [Seguridad normal](http://127.0.0.1:8766/index.html#cuenta/seguridad).
- [Acceso normal](http://127.0.0.1:8766/index.html#acceso).
- [Registro normal](http://127.0.0.1:8766/index.html#registro).

La versión normal indica indisponibilidad, mantiene el bloqueo de registro por documentos pendientes y no confirma creación, retirada o sesión real. No existe un parámetro de URL que habilite escenarios. Incluso un `begin` artificialmente preparado no puede finalizar sin el puente demostrativo explícito. No hay una URL para forzar la invitación posterior a verificación.

## Archivos y responsabilidad MVC

No se movieron, renombraron o eliminaron archivos existentes.

| Archivo | Acción y responsabilidad |
| --- | --- |
| `dist/modelo/acceso.js` | Ampliado: conserva validación/política de acceso y agrega `PasskeyModel` para metadatos, listas, operaciones y confirmaciones estrictas |
| `dist/modelo/servicio-acceso.js` | Comentario ampliado: frontera `AuthService` compartida, conservando indisponibilidad y ausencia de transporte |
| `dist/vista/seguridad.js` | Creado: un componente con variantes cuenta, alternativa de acceso y oferta; lista, confirmación y estados accesibles |
| `dist/vista/css/seguridad.css` | Creado: composición acotada, foco, 44 px, adaptación y alternativas de material/movimiento/colores; reutiliza botones y paneles |
| `dist/vista/acceso.js` | Modificado: alojamiento de la alternativa fuera del formulario de contraseña; registro/recuperación y sus vistas conservados |
| `dist/vista/aplicacion.js` | Modificado: enlace Seguridad en los apartados de Mi cuenta, también con carga/error del perfil |
| `dist/controlador/seguridad.js` | Creado: consultas/operaciones, confirmación, cancelación, timeout, coordinación de estados, foco y rechazo de respuestas ambiguas |
| `dist/controlador/acceso.js` | Modificado: monta/libera alternativa u oferta, coordina bloqueo con contraseña y exige verificación más sesión confirmada para invitar |
| `dist/controlador/aplicacion.js` | Modificado: monta/libera Seguridad dentro de la misma estructura privada y conserva el formulario de contraseña |
| `dist/controlador/site.js` | Modificado: ruta exacta, título y comparación de Seguridad; inyección explícita del puente de revisión, sin activación mediante URL |
| `dist/index.html` | Modificado: carga de los componentes y CSS nuevos y actualización de referencias afectadas |
| `revision/seguridad.js` | Creado, local: adaptador de acciones AuthService y puente de interacción sintéticos, con metadatos temporales y validación del propósito ficticio |
| `revision/index.html` | Ampliado, local: controles y escenarios de llaves; opción de verificación con sesión ficticia y aviso demostrativo actualizado |
| `revision/escenarios.js` | Ampliado, local: delegación de acciones de llaves, inyección del puente, selección/reinicio y dos recorridos de verificación |
| `revision/comprobar-etapa3.cjs` | Creado, local: comprobaciones automatizadas sin capturas; instrumentación de APIs de dispositivo para detectar cualquier llamada |
| `revision/resultado-etapa3.json` | Creado, local: resultados textuales sin datos personales |
| `revision/resultado-etapa1.json`, `revision/resultado-etapa2.json` | Regenerados, local: regresión de las etapas previas sin cambiar sus scripts o expectativas |
| `revision/base-etapa3.json` | Creado, local: huellas de los archivos previos para comprobar preservación |
| `README.md`, `docs/INTEGRACION-BACKEND.md` | Actualizados: rutas, recorridos, contratos, responsables y límites de activación |
| `docs/PLAN-INTEGRACIONES-FRONTEND-ETAPA-0.md` | Nota posterior de estado; propuestas e inventario histórico conservados |
| `docs/ENTREGA-ETAPA-3.md` | Creado: esta entrega |

El modelo normaliza datos/confirmaciones; la vista presenta metadatos escapados; el controlador coordina eventos y servicios. La frontera de autenticación sigue siendo `AuthService`; no se agrega otro servicio real o arquitectura. No se añade framework, compilador o biblioteca. El único cambio de contraseña sigue en `AuthController.mount('cambiar')`.

## Comprobaciones realizadas

Resultado: **27/27 grupos de etapa 3, 19/19 de regresión de etapa 1 y 20/20 de regresión de etapa 2 aprobados**. Evidencias: `revision/resultado-etapa3.json`, `revision/resultado-etapa1.json` y `revision/resultado-etapa2.json`, con sus scripts reproducibles en la misma carpeta. Las comprobaciones son automatizadas y textuales; no se generan capturas ni imágenes. Se comprobó sintaxis JavaScript, referencias y diferencias de Git además de los recorridos de navegador.

La ejecución cubre:

- Separación entre `#seguridad` público y `#cuenta/seguridad`, acceso desde cuenta, cuatro entradas y selección de Mi cuenta. Reutilización del cambio de contraseña.
- Validación de metadatos ausentes/incorrectos, lista vacía confirmada, errores sin lista vacía ficticia, confirmaciones incompletas de creación/acceso/retirada y sesión estrictamente booleana.
- Pasos de creación/acceso, cancelación, incompatibilidad, vencimiento, rechazo y reintento; retirada con confirmación y conservación de la llave ante fallo. Metadatos solo desde servicio, sin fechas/nombres inventados en la vista.
- Oferta tras verificar con y sin sesión; «Ahora no» y su funcionamiento durante una creación; entrada directa, recarga y regreso sin fabricar verificación/sesión.
- Doble envío, coordinación con contraseña, payload alternativo sin sus campos, abortos, timeout, respuestas tardías, reentrada sin duplicar eventos y salida de una vista durante espera.
- Entrada directa, título, Atrás/Adelante, recarga y subruta inválida; ausencia de nueva autenticación por cada cambio de pantalla.
- Anchos 320, 390, 768, 1024 y 1440 px, texto al 200 %, nombres largos, confirmación dentro de la página, áreas táctiles de 44 px y ausencia de elementos fuera del ancho. Foco de botones libre del encabezado/barra inferior en 390×600 como aproximación de espacio con teclado.
- Tab/Enter en confirmación y conservación de llave, vuelta al correo, foco visible, movimiento reducido, material sólido, colores forzados y contraste calculado de los pares de texto añadidos (mínimo 4.5:1 sobre sus fondos).
- Chromium con instrumentación de APIs de credenciales: sin llamadas de creación/obtención de credenciales, almacenamiento del navegador vacío y cero tráfico a servicios externos. Parámetros de URL no activan demostración. Una recarga reinicia las llaves ficticias.
- Firefox y WebKit a 390 px: crear, quitar con confirmación, alternativa no disponible con retorno al correo y oferta con «Ahora no», sin desbordamiento. No equivalen a una prueba de Safari o autenticadores físicos.
- Regresión completa de etapas 1 y 2, con los scripts anteriores sin modificaciones en esta entrega.

La primera ejecución detectó que el modo de material sólido aún conservaba desenfoque en las tarjetas de Seguridad; se añadió la alternativa acotada y la ejecución final pasó los 27 grupos. No hubo errores JavaScript ni recursos HTTP fallidos en la matriz de Chromium. Las huellas previas confirman que solo cambiaron los ocho archivos existentes de `dist/` enumerados en esta entrega, además de los tres componentes nuevos; privacidad, legales, imágenes, estilos base y fuentes conservaron sus archivos.

Límites: no se afirma revisión manual con lectores de pantalla, teclado de teléfono físico, autenticadores o dispositivos Apple. Las asociaciones y estados se revisaron técnicamente en navegador, sin afirmar lectura auditiva. No se prueban WebAuthn, autenticación/autorización reales, recuperación real o persistencia porque no se han implementado. Firefox/WebKit comprueban motores de navegador y no sustituyen dispositivos reales.

## Contratos y pendientes

La [guía de integración](INTEGRACION-BACKEND.md#seguridad-y-llaves-interfaz-de-etapa-3) documenta los payloads y respuestas de las seis acciones propuestas. Se precisa `sessionConfirmed:true` para acceso por llave, ID coincidente para retirada y respuesta de metadatos válida para creación. La interacción ficticia no constituye WebAuthn ni un formato de producción; dominio, RP ID, opciones y serialización siguen pendientes.

- Rafael: backend, sesión, autorización en cada operación, desafíos/validación futuros, idempotencia y concurrencia, reautenticación y recuperación acordadas antes de activación. No se implementan estas áreas ahora.
- Carolina: PostgreSQL y metadatos/material público que necesite el verificador aprobado; asociación con cuenta, revocación y conservación. No se crean tablas o migraciones; nunca guardar biometría, PIN o clave privada.
- Rafael y Gabriela: diseño/frontend y revisión de los recorridos.
- Pendiente de acuerdo: dominio/HTTPS, RP ID, compatibilidad, formato definitivo de opciones/respuestas, sesión, nombres/metadatos, política de recuperación y reautenticación, límites y conflictos. No se elige biblioteca de servidor ni framework.
- Pendiente de comprobación real: lectores de pantalla, teclado móvil físico, dispositivos/autenticadores y servicios cuando se apruebe la integración. Los avisos de reautenticación/recuperación preparados no implementan procedimientos nuevos.

El registro normal sigue bloqueado con documentos legales pendientes, el canal ARCO sigue desconectado y la electrónica permanece congelada. Esta entrega no avanza a la etapa 4.

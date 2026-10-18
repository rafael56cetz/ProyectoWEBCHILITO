# Mi huerto sin asignación y vinculación visual

Fecha: 17 de octubre de 2026. Entrega limitada a la interfaz existente.

## Motivo y resultado

Antes, garden-unassigned sustituía todo Mi huerto por una tarjeta de estado. Ahora una cuenta autenticada y verificada sin membresía puede revisar la estructura genérica prevista del producto: Planta 1, Planta 2, Planta 3, temperatura ambiental, humedad ambiental, depósito y actualización.

Se reutiliza el modelo de presentación existente: AppModel.garden ya descarta datos de huerto cuando el estado es unassigned y produce nombres genéricos y valores nulos. Se modificó su presentación, sin cambiar la respuesta del servidor ni otorgar permisos. Los nombres genéricos no son registros creados en PostgreSQL.

Los valores ausentes se presentan como —, sin unidades, fechas inventadas ni barras rellenas. Se retiraron las notas repetidas de ausencia por lectura. La fecha general es — cuando no existe. El depósito muestra — cuando su estado no está disponible; no se deduce que está vacío ni que hay falta de agua. No se generan avisos de cultivo sin mediciones. No se añadieron métricas descartadas.

## Estados y contrato

| Estado | Presentación y autorización |
| --- | --- |
| Cuenta sin huerto asignado | GET /api/huertos/actual sigue respondiendo 403 garden-unassigned. La vista muestra solo estructura genérica y el bloque Vincula tu huerto. |
| Huerto autorizado sin mediciones | Consulta real conservada. Tarjetas, nombres autorizados y valores ausentes; estado Sin mediciones y una frase breve. Sin invitación a vincular. |
| Información disponible | Conserva los valores, calidad, nombres, fechas y estado del depósito del contrato existente. |
| Error o respuesta incompleta | Error recuperable con Reintentar. No se convierte en una estructura vacía con éxito. |
| Sesión vencida o correo no verificado | Se conserva el manejo existente de sesión y el regreso al acceso; no se mantienen vistas privadas. |

No hay cambios en endpoints, permisos, esquemas, migraciones ni servicios del backend. No se consultan avisos o huertos ajenos para completar el dashboard. Los identificadores de las tres posiciones de presentación no conceden acceso a registros del servidor.

## Cuenta, membresía y dispositivo

- Cuenta: identidad y acceso autenticado, con verificación de correo por allauth.
- Membresía: autorización explícita de la cuenta sobre un huerto. Crear/verificar una cuenta no la asigna automáticamente.
- Dispositivo: equipo físico y su futura asociación. El contrato actual no informa si hay un equipo vinculado o conectado.

La membresía no prueba conectividad del equipo. Una cuenta que ya tiene acceso no ve el bloque de invitación como requisito ni recibe un indicador inventado de conexión. El procedimiento administrativo de membresía existente permanece separado y sin cambios.

## Vinculación visual

Solo para el estado unassigned, un bloque compacto muestra:

- Vincula tu huerto.
- Asocia tu equipo a tu cuenta para consultar sus mediciones.
- Vincular mi huerto.

La acción abre un dialog nativo reutilizando la superficie y botones del diálogo de salida existente. Incluye título Vincular mi huerto, etiqueta Código de vinculación, ayuda Introduce el código de vinculación de tu equipo, campo de texto, Cancelar y Vincular deshabilitado.

No se define patrón, longitud ni seis dígitos; no se reutiliza el código de correo. No se generan códigos, solicitudes de vinculación, confirmaciones de éxito ni registros. El submit se previene incluso si se intenta enviar con Enter. No hay QR, cámara, Wi-Fi, MQTT, credenciales del equipo ni permisos nuevos.

El foco entra al campo. Escape y Cancelar cierran, limpian el contenido y devuelven el foco al botón de origen. Cambiar de sección o desmontar el controlador también limpia el campo. El código no se incluye en almacenamiento, logs ni analítica. El botón deshabilitado tiene presentación atenuada y no aparenta ejecución disponible.

## Archivos y MVC

| Archivo | Responsabilidad |
| --- | --- |
| dist/modelo/aplicacion.js | Modelo de presentación: conserva unassigned y las estructuras genéricas existentes; ajusta el texto de waiting a Sin mediciones. |
| dist/vista/paginas.js | Vista: reutiliza el mismo dashboard para unassigned, elimina notas repetidas de ausencia y conserva lecturas disponibles. |
| dist/vista/aplicacion.js | Vista: bloque de vinculación y diálogo, dentro de la estructura compartida. |
| dist/vista/css/aplicacion.css | Vista: estilos comunes de diálogos reutilizados, bloque compacto, campo y control deshabilitado. |
| dist/controlador/aplicacion.js | Controlador: abre, cierra, limpia y gestiona foco; impide envíos y restringe la apertura al estado unassigned. |
| backend/tests/ui_garden_link.cjs | Nuevo recorrido de navegador aislado de permisos, estados, datos y diálogo. |
| backend/tools/comprobar_frontend.py | Añade --etapa 3 --vinculacion; prepara dos cuentas aisladas, compara tablas del dominio antes/después y limpia fixtures. |
| backend/tests/ui_stage3.cjs | Ajusta las aserciones a los textos y depósito vacío nuevos. |
| infra/verificar_entrega.ps1 | Incorpora la nueva comprobación al verificador existente. |
| docs/HUERTO-SIN-ASIGNACION-Y-VINCULACION-VISUAL.md | Esta entrega. |
| docs/CONTRATOS-INTEGRACION-LOCAL.md, README.md y docs/MEJORAS-DE-ACCESO.md | Actualizan la explicación del dashboard y enlazan esta entrega. |

Se preservan los cambios manuales del equipo, acceso real, Geist, Liquid Glass, logo y cuatro destinos. No hay quinta entrada ni otra aplicación.

## Comprobaciones y evidencia

Todas las pruebas funcionales se ejecutaron en PostgreSQL aislado; no se crearon cuentas o mediciones de ejemplo en la principal y no se enviaron correos reales.

- 172 comprobaciones nuevas de navegador aprobadas: cuenta sin membresía y respuesta real 403, nombres genéricos, cinco lecturas y depósito con —, ausencia de fechas/barras rellenas/notas repetidas, diálogo, teclado, Escape, Cancelar y limpieza.
- Ocho viewports para el nuevo diálogo: 320 × 568, 390 × 844, 568 × 320, 844 × 390, 768 × 1024, 820 × 1180, 1024 × 768 y 1440 × 900. Sin desbordamiento y con el diálogo dentro del área visible. Fuente del campo de 16 px.
- Durante las aperturas, escritura, Enter y cancelaciones del diálogo se registraron cero solicitudes de red. No hubo llamadas de vinculación.
- Comparación exacta de las filas de Huerto, Zona, Membresia, Aviso y AvisoLeido antes/después del recorrido: sin cambios. Las sesiones de prueba y fixtures son independientes y se limpian por el ejecutor.
- Huerto autorizado sin mediciones: tarjetas visibles, respuesta 200 real y ausencia de invitación a vincular.
- Datos disponibles: se inyectó exclusivamente una respuesta de fixture en el navegador, sobre una cuenta con membresía. Se comprobó conservación de valores, barras y fechas. Esto prueba el contrato de presentación; no acredita ingestión o telemetría real.
- Consulta 503 y respuesta 200 incompleta: error con reintento; respuesta 401: regreso al acceso y retirada de interfaz privada.
- Acceso a avisos de la fixture ajena desde la cuenta sin membresía: denegado sin devolver contenido.
- 24 pruebas Django existentes del dominio/permisos aprobadas.
- 161 comprobaciones existentes de huerto, navegación y confirmación de salida aprobadas, además de las aserciones de lectura concurrente del ejecutor.
- 209 combinaciones de pantalla/estado y tamaño de la revisión adaptable aprobadas, sin incidencias geométricas ni errores JavaScript. Esta revisión corresponde al recorrido autorizado; el estado sin membresía y su diálogo se cubren con la batería nueva anterior.
- Sintaxis JavaScript, sintaxis PowerShell y git diff --check sin errores; advertencias previas de finales de línea conservadas.

Las pruebas de tamaños se hicieron en Chromium simulado. Queda la comprobación de teclado virtual, gestos y áreas seguras en dispositivos físicos. Sin capturas ni imágenes.

Para repetir, desde backend con el entorno de pruebas preparado:

    python tools/comprobar_frontend.py --etapa 3 --vinculacion

No ejecutar en paralelo con otras pruebas que usen la misma base aislada.

## Pendientes de vinculación real

Investigar y acordar el mecanismo de asociación y prueba de propiedad del equipo, formato/emisión/vigencia/consumo del código, permisos y recuperación de asociación, estados de dispositivo y contrato de errores. La conexión física, transporte, autenticación de dispositivo y recepción de mediciones requieren otra entrega autorizada.

No hay protocolo IoT aprobado ni emparejamiento implementado. Los documentos legales y las llaves de acceso mantienen sus pendientes anteriores.

## Revisión local

URL: http://127.0.0.1:8766/index.html#huerto

Entrar con una cuenta sin membresía, abrir Vincular mi huerto y revisar el campo y la acción deshabilitada. Cancelar o Escape limpian y cierran. Una cuenta con membresía válida conserva su dashboard autorizado sin la invitación. Recargar con Ctrl+F5 para obtener los recursos actualizados.

Sin commit, push, despliegue, cambios en Notion ni avance hacia integración física.

Comprobación final: el servidor habitual estaba apagado y se inició mediante infra/iniciar_aplicacion.ps1 en una ventana oculta. Quedó escuchando en 127.0.0.1:8766; se verificó por HTTP que los cinco recursos modificados coinciden con los archivos actuales. No se crearon cuentas o membresías para esa revisión.

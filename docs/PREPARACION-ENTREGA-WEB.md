# Preparación de la entrega web integrada

27 de octubre de 2026. Este documento registra la preparación de una copia Git separada para revisión. **El propietario solicitó publicar en GitHub la versión actual de trabajo.** La revisión técnica previa y sus evidencias no equivalen a la aprobación final del diseño ni al despliegue de la aplicación. La aplicación aún recibe las comprobaciones de cierre y correo autorizadas en el chat. El compañero realizará la dockerización posteriormente; este trabajo no implementa ni comprueba un nuevo despliegue Docker.

## Repositorio y rama

- Remoto: `https://github.com/rafael56cetz/ProyectoWEBCHILITO.git`.
- Rama de base: `origin/main`.
- Revisión de base comprobada al clonar: `1eb74e526f847124889b578eee18a92dac4b9709`.
- Rama local propuesta para la entrega: `entrega/integracion-web-etapa4`.
- El checkout estaba limpio antes de añadir este documento. Los otros checkouts existentes con modificaciones se conservaron intactos.

Antes de publicar, volver a comprobar que la base remota no cambió y revisar los archivos que quedarían en el commit. No hacer push directamente a `main` ni sustituir el repositorio entero por otra carpeta. El contenido y la rama se mostraron al propietario; la solicitud posterior de subir el código autoriza su publicación. El cierre de diseño y correo sigue pendiente.

## Incorporación aditiva prevista

La aplicación integrada está preparada bajo **[`web-integracion/`](../web-integracion/README.md)** para revisar su incorporación. Su README es la entrada operativa de la copia actual. Las carpetas previas `backend/`, `dist/`, `frontend/`, `infra/` y sus documentos se conservan sin sobrescribir.

La selección contiene código integrado, instrucciones, configuración de ejemplo sin secretos, migraciones, dependencias fijadas y evidencias revisadas. Se publicará mediante un commit en la rama de entrega indicada. Las evidencias de revisión identifican expresamente su fase anterior al commit y al push. El código y los recursos de backend/frontend coinciden byte a byte con la copia local comprobada. El cierre sigue pendiente del diseño reciente, el correo real y los recorridos de navegador indicados en sus evidencias. Las instrucciones de Ubuntu Server, dominio, systemd, Nginx o despliegue definitivo quedan fuera por indicación actual del propietario. El `compose.yaml` histórico se conserva como antecedente; no es una dockerización de esta aplicación.

## Lista de inclusión para revisar

| Ruta de la aplicación integrada | Criterio |
|---|---|
| `README.md`, `docs/` | Instrucciones y controles actuales para la aplicación. Enlaces internos relativos; conservar los pendientes reales del correo y de la revisión del diseño final. |
| `backend/` | Código Python, modelos, migraciones, pruebas y herramientas pertinentes; `requirements-lock.txt` con versiones fijadas. Excluir cachés y entornos. |
| `frontend/` | HTML, JavaScript, CSS, iconos, fuente/licencia y recursos utilizados. Pruebas de contrato incluidas; no copiar sesiones, revisiones de personas ni datos reales. |
| `sql/` | Scripts operativos de roles/privilegios coordinados con migraciones, sin contraseñas. |
| `.env.example`, `.gitignore` | Solo nombres y valores de ejemplo sin secretos; las credenciales se configuran externamente. |
| `evidencias/` | Solo resultados de pruebas, revisión identificada y datos sintéticos saneados. Leer el contenido seleccionado antes de añadirlo. |
| `referencias/` | Solo referencias necesarias y saneadas; los resultados históricos deben identificarse como antecedentes, nunca como pruebas actuales. |
| `MANIFEST.sha256` | Regenerar sobre la selección final, con rutas relativas; no reutilizar un manifiesto que describa archivos excluidos. |

## Exclusiones obligatorias

- `evidencias/entorno-local.json`: metadatos volátiles y rutas del entorno de una computadora; no es configuración portable.
- `.env`, `.env.*` salvo `.env.example`; JSON de ejecución con contraseñas/claves y cualquier configuración externa real.
- Buzones y mensajes de correo, códigos, enlaces de recuperación, tokens completos, cookies y sesiones de navegador.
- Bases de datos, dumps de pruebas, volúmenes, datos personales y capturas que los expongan.
- Entornos virtuales, `__pycache__`, `*.pyc`, `node_modules`, temporales y archivos de registros no saneados.
- Huellas o documentos de procedencia con rutas absolutas de la computadora: excluirlos de publicación o producir una referencia relativa revisada, sin modificar el antecedente original.

Los nombres de prueba y contraseñas sintéticas declaradas en pruebas automatizadas no deben confundirse con credenciales de uso real; revisar el contexto en lugar de eliminar toda aparición de la palabra `password`.

## Revisión antes de commit

1. Revisar `git status --short --branch`, `git diff --name-status` y `git diff --stat`.
2. Comparar la selección con la lista de inclusión; no usar una copia indiscriminada del árbol local.
3. Revisar `git diff --cached` y la lista exacta de rutas añadidas. Buscar valores de credenciales, datos personales, rutas absolutas y material de buzón/cookies sin imprimir valores encontrados en el chat o en evidencias públicas.
4. Relacionar los cambios con la revisión realmente probada: la ejecución vigente aprobó 114 pruebas, incluidas las 105 regresiones anteriores, cinco pruebas SMTP sin red y cuatro del arranque local. No acredita envío ni recepción de correo real. Los controles o recorridos pendientes conservan su estado.
5. Mostrar resumen, rama de destino y pendientes al propietario antes de hacer push.

La inspección inicial de nombres ya rastreados encontró componentes históricos llamados `backend/config/private.py`, `backend/tools/private_files.py` e `infra/guardar_credenciales_backend.ps1`. **No se leyeron secretos ni se infiere una fuga por esos nombres**; forman parte de la base existente y no se modificaron. Este cierre revisa el contenido nuevo propuesto, no reescribe todo el historial del equipo.


## Selección preparada para revisar

Los archivos de esta selección ya están copiados y preparados para revisar. Su publicación como versión actual de trabajo fue solicitada por el propietario; no se presenta como cierre definitivo de seguridad o de correo. El [estado del cierre](../web-integracion/docs/cierre-entrega.md) y los [resultados](../web-integracion/docs/resultados.md) separan lo comprobado de lo pendiente.

- Código Python pertinente, dependencias fijadas, frontend y recursos, `sql/privilegios.sql`, `.gitignore` y `.env.example`.
- README y documentos de cuentas, contrato, matriz de seguridad, resultados, cierre y correo real, con rutas relativas y pendientes explícitos.
- Evidencias vigentes: `validacion-integracion.json`, `pruebas-integracion.txt`, `pruebas-frontend.txt`, `revision-codigo-verificado.json`, `reinicio-local.json` y `conservacion-originales.json`. `historial-correcciones.json` identifica fallos históricos corregidos, no fallos vigentes.
- `navegador.json`, `navegador-cierre.json` y siete capturas revisadas visualmente, sin correos personales, códigos ni tokens completos. Sus recorridos parciales y revisiones están diferenciados.
- Excluir `evidencias/entorno-local.json`, `evidencias/procedencia-inicial.json` y archivos históricos de huellas/conservación que incluyan rutas personales. Si se necesita procedencia pública, preparar un resumen relativo específico de la entrega, conservando intactos los archivos locales originales.
- La carpeta `referencias/capa-datos/` contiene una selección del antecedente validado. El SQL histórico requiere la baseline, no incluye los cambios posteriores de la aplicación y no es la ruta operativa de instalación: esta aplicación utiliza sus migraciones Django.
- `MANIFEST.sha256` enumera únicamente la selección copiada, con rutas relativas. No incluye el manifiesto ni configura secretos.
- Excluir `deploy/`, documentación específica de Ubuntu y nuevos archivos de dockerización de esta preparación; la dockerización corresponderá al compañero y necesitará su verificación posterior.

Las credenciales SMTP y la dirección de prueba autorizada se suministran externamente. La evidencia deberá distinguir aceptación por SMTP y recepción confirmada en el buzón. No presentar el correo como configurado o recibido mientras falten esos datos y comprobaciones.

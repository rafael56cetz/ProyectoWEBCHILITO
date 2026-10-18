# CI inicial y publicación de la entrega
Fecha: 18 de octubre de 2026.

## Objetivo y alcance
El workflow .github/workflows/ci.yml ejecuta una instalación limpia en Ubuntu 24.04/Python 3.13 con PostgreSQL 17, dependencias fijadas y roles separados. Se dispara por push a main, pull request o ejecución manual. Solo tiene contents: read; las acciones están fijadas a revisiones. Las credenciales se generan para ese runner y no se suben como artefactos.
Se comprueban dependencias consistentes, configuración Django, modelos sin migraciones pendientes, pruebas del servidor con rol de aplicación limitado y sintaxis JavaScript. Los errores detienen el job. La base aislada y el correo en memoria impiden modificar datos locales o enviar Gmail real.
Este CI inicial no incluye pruebas visuales Playwright, correo real, teléfono físico, auditoría completa, hardware ni despliegue. pip check comprueba coherencia de dependencias, no vulnerabilidades. No se declara cumplimiento íntegro ASVS/SSDF por tener CI.

## Ver y ejecutar
Abrir https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions y elegir CI El Chilito.
Cada push a main ejecuta el flujo. Para repetir manualmente: Run workflow, rama main, Run workflow.
Para la evidencia del profesor registrar URL del run, SHA, fecha, resultado y alcance. Un YAML sin ejecución correcta no cierra E19-07.

## Revisión antes de publicar
Versionar frontend actual, backend/migraciones, dependencias, infraestructura reproducible y documentación. Excluir secretos, entorno virtual, dumps, logs privados, revision/ y scratch/.
No sustituir el trabajo manual del equipo. Revisar git diff y archivos preparados antes del commit. El README vigente debe dirigir a INSTALACION-EQUIPO.md e INICIO-LOCAL-PRESENTACION.md; documentos de etapas previas conservan resultados históricos.
Publicar el repositorio no publica la aplicación en Internet.

## Referencias
- GitHub Actions: https://docs.github.com/en/actions/get-started/understand-github-actions
- PostgreSQL en CI: https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers
- Marco acordado SSDF 1.1: https://csrc.nist.gov/pubs/sp/800/218/final

## Verificacion local previa a la primera publicacion de CI
18 de octubre de 2026: 127 pruebas del servidor aprobadas en la base aislada, pip check sin incompatibilidades y makemigrations --check --dry-run sin cambios pendientes. Analisis sintactico de Python y PowerShell aprobado.
Se preparo una instalacion nueva en un contenedor PostgreSQL temporal separado: 31 migraciones, tres zonas, cero cuentas, rol de aplicacion sin privilegios administrativos y repeticion sin sustituir secretos. El contenedor temporal fue retirado; la base principal se conservo.
Se revisaron los archivos candidatos a Git y no se encontraron coincidencias con las claves privadas locales ni respaldos incluidos. Estas comprobaciones no sustituyen las auditorias de seguridad pendientes.
El resultado remoto debe consultarse en Actions para el commit publicado; no se deduce del resultado local.

## Estado real de GitHub Actions al publicar
El codigo se publico en main. El primer intento tuvo un error de contexto en el YAML, corregido en 3c6229b9771bd4404f8b148eeb02bb9e4da06655.
GitHub acepto el flujo corregido, pero no inicio ningun paso: la cuenta tiene un bloqueo de facturacion. Evidencia: https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39149110084
Mensaje: The job was not started because your account is locked due to a billing issue.
Por tanto, CI esta configurado pero su ejecucion remota satisfactoria sigue pendiente. Las pruebas locales aprobadas no equivalen a un run de Actions aprobado.
Se fijo Ubuntu 24.04 para evitar el cambio anunciado de ubuntu-latest durante la fecha de entrega.
El titular debe revisar Settings > Billing and licensing en GitHub. Si no hay un problema visible que resolver, contactar soporte; no es necesario asumir que debe comprar otro plan. Guia oficial: https://docs.github.com/en/billing/how-tos/troubleshooting/locked-account
Despues de resolverlo, abrir Actions > CI El Chilito > Run workflow > main > Run workflow y comprobar todos los pasos. No se cambiaron pagos, suscripciones ni presupuestos.

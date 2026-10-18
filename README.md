# El Chilito · Aplicación web
Entrega local integrada: 18 de octubre de 2026. Django/Python, PostgreSQL 17 en Docker y frontend MVC existente. Un solo origen: http://127.0.0.1:8766/index.html.

## Instalar y abrir
Requisitos: Windows 10/11, Python 3.13 con lanzador py, Git y Docker Desktop con contenedores Linux/Compose v2. Abrir Docker Desktop antes.
~~~powershell
git clone https://github.com/rafael56cetz/ProyectoWEBCHILITO.git El-Chilito-Aplicacion-Web
Set-Location .\El-Chilito-Aplicacion-Web
& .\infra\preparar_equipo.ps1
& .\infra\configurar_correo_local.ps1
& .\infra\iniciar_aplicacion.ps1
~~~
[Instalación completa y correo propio](docs/INSTALACION-EQUIPO.md). Primera instalación y migraciones son explícitas; el inicio diario no reinstala ni migra. No usar http.server.

## Qué funciona
- Registro local con casilla obligatoria, verificación por código, correo/contraseña, sesión, perfil, recuperación y cierre reales.
- Huerto y tres zonas persistidos, avisos y lectura individual con permisos.
- Sin membresía: estructura genérica; la API no entrega información privada. Sin mediciones: guiones, no números inventados.
- Contraseñas de 15 a 256 caracteres; el código de correo verifica el registro, no se exige en cada inicio.
- Registro habilitado solo en perfil local; confirmación técnica no equivale a documentos legales aprobados.

## Límites
Vinculación visual sin envío; sin telemetría/actuadores, IA, ARCO o passkeys operativos. No hay app instalada ni despliegue público. PostgreSQL y Django solo escuchan en loopback. Un teléfono no accede a la PC usando 127.0.0.1.
Cada integrante genera sus credenciales y su base; no copiar secretos, dumps ni datos personales. El correo requiere Gmail configurado, Internet y disponibilidad del proveedor.

## Evidencias y trabajo del equipo
- [Guía de presentación y revisión del 18/10](docs/INICIO-LOCAL-PRESENTACION.md).
- [CI y publicación](docs/CI-Y-PUBLICACION.md) · [ejecuciones en GitHub](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions).
- [Contratos de integración](docs/CONTRATOS-INTEGRACION-LOCAL.md).
- [Seguridad y verificación parcial](docs/SEGURIDAD-Y-VERIFICACION-LOCAL.md).
- [Matriz ASVS actualizada y evidencias del hito](docs/MATRIZ-REQUISITOS-Y-EVIDENCIAS-2026-10-18.md).
- [Arquitectura, flujos de datos y diagrama exportable](docs/ARQUITECTURA-Y-FLUJOS-2026-10-18.md).
- [Hito del 19: índice de evidencias](docs/INDICE-EVIDENCIAS-HITO-1-2026-10-19.md), [dos historias](docs/BACKLOG-HU-01-HU-02-2026-10-19.md) y [alcance congelado](docs/ALCANCE-CONGELADO-HITO-1-2026-10-19.md).
- [Backend, migraciones y pruebas](backend/README.md).
- [Historial anterior del README](docs/HISTORIAL-README-ANTES-CI.md).
Rafael: backend/integración; Carolina: PostgreSQL/logo; Rafael y Gabriela: frontend. Revisar diffs y documentar cambios. No cambiar permisos ni compartir claves para simplificar una demostración.
Los documentos de etapas conservan resultados de su fecha. Las notas antiguas de registro cerrado, frontend sin backend o servidores de revisión no sustituyen este estado.

## CI inicial
Push a main, pull request o ejecución manual ejecutan instalación limpia, PostgreSQL aislado, migraciones, validación Django, pruebas servidor y sintaxis JavaScript. Correo en memoria; sin secretos de producción. No equivale a auditoría completa ni ejecuta la revisión visual en dispositivos físicos.

Estado remoto al 18/10: [CI inicial aprobado](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39150814752), con 127 pruebas del servidor y revision de sintaxis del frontend. Ver [alcance y evidencia](docs/CI-Y-PUBLICACION.md#estado-verificado-de-github-actions).

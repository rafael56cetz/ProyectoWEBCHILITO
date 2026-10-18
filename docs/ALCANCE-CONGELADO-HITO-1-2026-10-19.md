# Alcance congelado del Hito 1: entrega del 19 de octubre de 2026

Línea base fijada el 18 de octubre por solicitud de Rafael para presentar al equipo. Código de referencia: 130336d0f5b8c96a6325e4578f7f6cd26768b9ce. Los cambios de este cierre son documentales. La aceptación de los demás integrantes está pendiente de confirmación; no se atribuye un acuerdo colectivo ya firmado.

## Objetivo de la entrega

Presentar una aplicación web local que permite verificar una cuenta, iniciar y cerrar sesión y consultar un huerto de tres zonas mediante una API Django y PostgreSQL. Se mostrará qué información existe y qué falta medir. El registro no concede permisos sobre el huerto.

Este alcance corresponde al hito académico del 19. El proyecto completo mantiene sus integraciones futuras. El profesor pidió requisitos, arquitectura y un esqueleto integrado; Rafael aclaró que por ahora se presenta la web. La demostración de una app instalada queda fuera de esta entrega y no se sustituye por abrir una web adaptable.

## Incluido en la aplicación

| Elemento | Comportamiento incluido | Condición o límite |
| --- | --- | --- |
| Ejecución local | Un solo origen Django en http://127.0.0.1:8766; PostgreSQL 17 en Docker, puerto local 5433 | Sin publicación en Internet; no abrir puertos para improvisar acceso externo |
| Registro local | Correo, contraseña, casilla obligatoria y confirmación técnica guardada | Perfil local autorizado por Rafael; documentos legales sin aprobación efectiva |
| Verificación | Código de correo con caducidad y límites, gestionado por allauth | Requiere Internet y SMTP configurado para entrega real; no asigna membresía |
| Acceso y sesión | Correo/contraseña, sesión de servidor, restauración y cierre | Contraseña de 15 a 256 caracteres; no exige código por correo en cada login |
| Recuperación y cambio | Enlace de recuperación y cambio con contraseña actual | Pruebas técnicas existentes; disponibilidad de correo depende del proveedor |
| Mi cuenta | Consulta del perfil propio y estado de asignación | No se promete edición completa de todos los datos ni procedimiento ARCO operativo |
| Huerto | Un huerto persistido con tres zonas; permisos por membresía explícita | La asignación actual es administrativa local, no vinculación de dispositivo |
| Mediciones ausentes | Sustrato por planta, temperatura, humedad ambiental y depósito con ausencia/estado desconocido | Sin números, fechas, volumen o conexión física inventados |
| Cuenta sin membresía | Estructura genérica de tres plantas y guiones | La API conserva 403 para información privada |
| Avisos | Lista, detalle, filtros de presentación y lectura persistida por usuario, cuando existan registros | Sin generación de alertas físicas ni avisos ficticios en la base principal |
| Diseño | Frontend MVC existente y adaptación de diseño a distintos anchos | Emulación documentada; no acredita teléfono físico ni cliente móvil instalado |
| Vincular mi huerto | Diálogo visual existente | No envía el código ni concede membresía o identidad física |

## Incluido como evidencia del hito

- Repositorio con el código actual, migraciones, dependencias fijadas e instrucciones de instalación.
- CI inicial remoto aprobado: instalación, PostgreSQL aislado, migraciones, validaciones, 127 pruebas del servidor y sintaxis JavaScript.
- Dos historias HU-01/HU-02 con criterios, resultados y enlaces a evidencia.
- Matriz ASVS 5.0.0 seleccionada y nota de evaluación móvil MASVS aplazada. Mantiene 7 controles verificados localmente y 6 parciales; 332 requisitos del catálogo pendientes de evaluar.
- Diagrama y catálogo de flujos de datos con límites de confianza.
- MVP de Gabriela, pendiente de recibir y enlazar su documento.
- Modelo de amenazas reducido y resultados adicionales de Kevin, pendientes de recibir.
- Demostración manual prevista para el 19, pendiente de ejecutar y registrar.

Los últimos tres puntos son compromisos del paquete con evidencia todavía pendiente. No se presentan como archivos ya entregados. El [índice de evidencias](INDICE-EVIDENCIAS-HITO-1-2026-10-19.md) identifica su estado.

## Fuera de la entrega funcional

| Elemento | Situación posterior |
| --- | --- |
| ESP32 y telemetría | Sin ingesta autenticada, asociación de dispositivo ni datos físicos conectados a esta web |
| Bombas, lámpara y actuadores | Sin control web, confirmación de actuación ni pruebas de seguridad física |
| Sensores | Tres sondas, DHT22 y sensor de nivel son referencia física; firmware/calibración y contrato definitivo de ingesta quedan para integración |
| Vinculación real | Faltan protocolo, credencial de vinculación, autorización, revocación y backend del flujo |
| IA | Se prevé integración por API; no hay asistente operativo conectado |
| ARCO | Sin recepción/seguimiento real ni procedimiento y responsable legal definitivos |
| Passkeys, huella o PIN | Sin credenciales WebAuthn reales ni autenticación biométrica integrada |
| App instalada | Sin APK/PWA instalada ni demostración de un segundo cliente independiente |
| Hosting público | Sin dominio, HTTPS productivo, despliegue o base de datos pública |
| Certificación integral | No se declara nivel completo ASVS, cumplimiento MASVS ni auditoría de todo WSTG/SSDF |

## Condiciones de aceptación y pendientes conocidos

La referencia técnica incluye pruebas aprobadas y controles parciales. El cierre del hito requiere revisar los archivos, adjuntar MVP y amenazas y registrar la demostración. HU-01 conserva la revisión de logs parcial; las seis comprobaciones adicionales se asignaron a Kevin con instrucción de registrar hallazgos sin modificar la aplicación. Una brecha documentada no queda resuelta por excluir nuevas funciones.

La presentación funciona por HTTP exclusivamente en loopback. Las cookies locales no usan Secure y PostgreSQL local no usa TLS. No se trata como prueba de transporte cifrado público. El correo SMTP tiene su conexión STARTTLS; iniciar Docker/Django o autenticar SMTP no garantiza recibir el mensaje en el buzón.

## Responsabilidades para este cierre

| Integrante | Responsabilidad vigente |
| --- | --- |
| Rafael | Backend e integración; coordinación de esta entrega, versión y demostración |
| Gabriela | Frontend/diseño con Rafael y documento MVP indicado por Rafael |
| Carolina | PostgreSQL, revisión de persistencia y logo |
| Kevin | Pruebas pendientes y modelo de amenazas reducido; documentar resultados sin cambiar frontend/backend |

## Control de cambios hasta presentar

1. Se conserva esta línea base funcional para el hito. Las nuevas integraciones pasan a trabajo posterior.
2. Una corrección necesaria debe registrar motivo, responsable, archivos, commit, impacto en criterios y pruebas afectadas.
3. Después de una corrección se actualizan las evidencias afectadas y se comprueba CI; no se reutiliza un resultado antiguo como si validara código cambiado.
4. Kevin comunica los hallazgos. Rafael coordina las correcciones que se decidan y su revisión.
5. El equipo confirma recepción y aceptación del alcance. No hay constancia de esa aceptación colectiva en esta versión.

## Enlaces de la entrega

[Backlog y criterios](BACKLOG-HU-01-HU-02-2026-10-19.md) · [Matriz](MATRIZ-REQUISITOS-Y-EVIDENCIAS-2026-10-18.md) · [Flujos](ARQUITECTURA-Y-FLUJOS-2026-10-18.md) · [Instalación](INSTALACION-EQUIPO.md) · [Guía de presentación](INICIO-LOCAL-PRESENTACION.md).

# Etapa 1 · Django y persistencia

17-10-2026. Autorización: «continua con la etapa 1». Solo esta etapa; no se conecta todavía el recorrido visual ni se avanza a correos/acceso reales de Etapa 2.

## Resultado

Backend nuevo separado en backend/, conservando HTML/CSS/JavaScript, MVC, Geist, Liquid Glass, logo, imágenes, distribución y navegación de dist. Misma raíz de trabajo, sin duplicar interfaz o dist.

- Entorno Windows independiente fuera de OneDrive, Python 3.13.7.
- Django **5.2.18 LTS**, django-allauth[headless] **65.20.0**, psycopg[binary] **3.3.6** y dependencias transitivas exactas registradas.
- PostgreSQL 17.11 existente conservado en Docker y su volumen original.
- Usuario por correo configurado antes de primera migración; autoridad de verificación: allauth, sin booleano verified paralelo.
- 27 migraciones de Django/allauth/proyecto aplicadas en el_chilito como **el_chilito_migrador**.
- 14 tablas public, todas propiedad del migrador; no se recrearon a mano tablas de biblioteca.
- Un huerto id=1 y zonas 1,2,3 persistidos por **el_chilito_app**, mediante comando transaccional/idempotente.
- Cero cuentas, direcciones de correo, sesiones y membresías en la base de presentación al cerrar la revisión. Ninguna lectura o última comunicación inventada.
- **34 pruebas nuevas aprobadas** en el_chilito_test con rol app restringido.

La interfaz visible mantiene su comportamiento previo y sus simulaciones. El backend está preparado y probado como base, **no hay login real conectado en la web todavía**. No se retiran/activan pantallas en esta etapa para aparentar integración terminada.

## Revisión inicial y preservación

Se volvieron a leer instrucciones, README, guía y documentos de Etapa 0; no se encontraron AGENTS aplicables. Rama main, HEAD f5605359cdff0fb596a63cfc0c352026fb5060e2. Se conservaron los cambios locales y archivos sin seguimiento. No se usó GitHub como sustituto, ni reset/clean/checkout/commit/push.

Antes de escribir se registraron huellas de 56 archivos existentes no secretos. La evidencia final lista archivos nuevos y compara los existentes; solo README y la nota de vigencia de docs/INTEGRACION-BACKEND.md se actualizan documentalmente. El frontend, Compose, SQL administrativo, borradores externos y demás documentación histórica se preservan.

Se volvió a inspeccionar la DB antes de migrar: el_chilito existía, dueño migrador, roles sin privilegios administrativos y sin tablas. No se reejecutó el SQL de creación, borró la base/volumen, restableció contraseña o sobrescribió trabajo de Carolina.

Rafael introdujo las contraseñas de roles mediante el asistente privado. El asistente no inspeccionó ni mostró sus valores; Django las usa en ejecución para conectar. No se reutilizó el secreto administrativo como credencial de aplicación.

## Modelo implementado y ajustes al borrador

Se implementa solo la base necesaria para identidad y pertenencia: Usuario, Huerto, Zona y Membresia. Las tablas de telemetría, calibraciones, mensajes, actuadores, avisos y auditoría del borrador **no se copian ahora**: requieren sus contratos y etapas correspondientes. Esto evita aprobar implícitamente validaciones relacionales, índices, retención o borrados que la revisión detectó pendientes.

| Elemento | Implementación y motivo |
| --- | --- |
| Usuario | AbstractUser sin username, email único y restricción SQL Lower(email); manager normaliza correo, valida política de contraseña y usa set_password. No contraseñas legibles |
| Verificación | EmailAddress de allauth es la autoridad; no se añade una bandera de dominio contradictoria. Verificar correo no crea membresía |
| Huerto | Clave estable de provisión, nombre, zona IANA validada y fecha real de creación. La fecha no representa comunicación IoT |
| Zona | FK protegida, número 1–3 y único por huerto; nombre/cultivo. Provisión crea exactamente tres en transacción; no habilita sensores |
| Membresia | FK cuenta/huerto, combinación única, activa y fecha de asignación; se concede mediante comando local explícito |
| Integridad | Checks SQL para rangos/nombres, FK y unicidad. Trigger de migración evita reasignar zona a otro huerto/número o membresía a otra cuenta/huerto, incluso con QuerySet.update |
| Validación | save de modelos de dominio aplica full_clean; reglas críticas anteriores también se verifican en SQL, sin depender únicamente de clean |
| Permisos | Servicio filtra por cuenta activa, EmailAddress verificada y membresía activa. Rutas/IDs o staff no conceden acceso por sí solos |

No se añade un esquema alternativo manual. Las migraciones son la fuente de estructura; los triggers propios tienen reversión explícita en migración. No se define aún retención/ARCO ni borrado en cascada para resolver protecciones.

La política de 15 caracteres usada en la base del backend es conservadora para creación administrativa/pruebas; el alta pública permanece cerrada. La política final, expiración de códigos, reenvíos y sesiones se revisará antes de habilitar los flujos de Etapa 2. No hay código fijo, verificador criptográfico propio o API real de llaves.

## Archivos creados y responsabilidades

La lista exacta con huellas está en [evidencia](EVIDENCIA-ETAPA-1-LOCAL.json). Archivos vacíos __init__.py solo identifican paquetes.

| Ruta/grupo | Responsabilidad |
| --- | --- |
| backend/manage.py | CLI, selección segura de pruebas aisladas y guardas de rol |
| backend/requirements.txt; requirements-lock.txt | Dependencias directas y las 11 distribuciones exactas resueltas |
| backend/config/settings/{base,local,testing}.py | Django, auth/headless, DB/roles, cookies/CSRF y separación local/pruebas |
| backend/config/private.py | Carga de secretos al ejecutar, fuera del repositorio, sin valores en errores |
| backend/config/{urls,views}.py | Servir los archivos originales de dist con control de ruta, sin copia o plantilla nueva |
| backend/config/{asgi,wsgi}.py | Entradas de servidor; rechazan rol migrador |
| backend/config/test_runner.py | Base preprovisionada, nombre/rol verificados, sin privilegios administrativos ni borrado |
| backend/cuentas/{apps,models,adapters,email}.py | Identidad, manager, registro cerrado y correo bloqueado mientras espera Etapa 2 |
| backend/cuentas/migrations/0001_initial.py | Usuario personalizado antes de migraciones allauth |
| backend/huerto/{apps,models,services}.py | Persistencia de huerto/zonas/membresías, provisión y permisos |
| backend/huerto/migrations/0001_initial.py; 0002_identidades_estables.py | Estructura y protección SQL de relaciones |
| backend/huerto/management/commands/{preparar_huerto,asignar_huerto}.py | Provisión idempotente y asignación explícita por operador autorizado |
| backend/tools/{private_files,preparar_pruebas}.py | Secretos nuevos privados y provisión de DB/roles exclusivamente de pruebas |
| backend/tests/{test_foundation,test_allauth_compatibility,headless_urls}.py | Pruebas de datos/permisos, recursos compartidos y contrato de la biblioteca; URLconf solo de pruebas |
| infra/guardar_credenciales_backend.ps1 | Entrada privada de claves existentes; no cambia passwords PostgreSQL ni sobrescribe archivos |
| backend/README.md | Instalación, configuración, migración, asignación, pruebas y límites |
| docs/ETAPA-1-DJANGO-Y-PERSISTENCIA.md; EVIDENCIA-ETAPA-1-LOCAL.json | Entrega y evidencia actuales |

Modificados: README.md y docs/INTEGRACION-BACKEND.md, solo para indicar vigencia y enlazar esta entrega. Frontend conserva vista/controlador/modelo; backend añade persistencia, servicios y configuración sin mover sus carpetas.

## Evidencia y comprobaciones realizadas

1. Entorno nuevo: pip check correcto. Compatibilidad de requisitos del tag oficial allauth 65.20.0 (commit 5ea117e72397adbd8ca6bc61c692d64ecca4d31b), Python/Django fijados, más pruebas ejecutadas.
2. manage.py check sin incidencias; makemigrations --check --dry-run sin diferencias y migrate --check sin pendientes.
3. Revisión de migraciones y SQL antes de aplicarlas, primero en DB aislada y después en local; migrador autenticado desde Windows sin SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS.
4. Credencial app independiente conectó desde Windows; schema/database CREATE=false, sin pertenencia administrativa. En pruebas se rechazaron CREATE TABLE y ALTER TABLE con el rol app.
5. Provisión ejecutada dos veces: mismo huerto id=1 y tres zonas, sin duplicados. Un proceso posterior independiente leyó los mismos registros confirmados. No se reinició Docker para esta comprobación.
6. Suite actual de 34 casos: email/contraseña, registro cerrado, autoridad allauth, permisos positivos/negativos, membresía explícita, FK/rangos/unicidad/identidades protegidas, rollback/idempotencia y recursos de dist.
7. Compatibilidad headless verificada solo mediante URLconf de pruebas: login por contraseña de cuenta de prueba verificada, cookie HttpOnly, sesión browser sin app-token y rechazo por falta de CSRF. No se habilita código en cada login.
8. TestCase revirtió las cuentas/sesiones/huertos de prueba; base aislada quedó sin esos datos al terminar. No se otorgó CREATEDB, TRUNCATE, SUPERUSER o CREATEROLE al rol normal.
9. Django TestClient devolvió el index original byte a byte, CSS/favicon, rechazó rutas fuera de dist. El servidor visual existente permanece en su puerto; no se creó otra copia o aplicación visual.

Estas son pruebas actuales del backend, no las cifras de 28 pruebas visuales de entregas anteriores. No se ejecutaron escaneos externos, envío SMTP, WebAuthn, hardware, notificaciones o pruebas con terceros. Sin capturas/imágenes.

## Seguridad y límites de esta entrega

La configuración prepara sesión servidor HttpOnly/SameSite, middleware CSRF y autoridad de biblioteca; las excepciones Secure=false son solo HTTP loopback local. No hay despliegue productivo preparado ni autorización de publicación. No CORS abierto, JWT en localStorage o exenciones CSRF propias.

El alta real permanece cerrada incluso llamando directamente al endpoint allauth en pruebas; SMTP está bloqueado. Las rutas headless aún no están montadas en config/urls.py, para no habilitar funciones de Etapa 2 por accidente. Los objetos de verificación/sesión provienen de migraciones de biblioteca, no de tablas propias.

Los procedimientos WSTG y el catálogo ASVS completo siguen pendientes de verificación sobre la integración final. Estos resultados prueban partes del contrato, no cumplimiento ASVS/SSDF total ni seguridad del firmware. Se conserva la línea base documentada en [seguridad](SEGURIDAD-Y-VERIFICACION-LOCAL.md).

## Qué falta y siguiente autorización

Etapa 2: conectar frontend a sesión/registro/verificación/recuperación reales, configurar correo y destinatario autorizado, aprobar documentos/versiones y retirar adaptadores ficticios del arranque. La aprobación legal pendiente bloquea registro público, no esta base de persistencia.

Etapa 3: APIs y datos de Mi huerto/Avisos/Mi cuenta, modelo de avisos/lecturas según contrato, tratamiento acordado de ARCO/llaves/Asistente. No activar óptico/ventilador, actuadores o telemetría simulada.

Etapa 4: pruebas completas de flujos reales, reinicio de servicios y persistencia, respaldo/restauración aislados, accesibilidad/móvil y evidencia/CI de entrega. No se ha realizado dump/restore ni una evaluación jurídica.

La única URL visual actual sigue siendo [El Chilito](http://127.0.0.1:8766/index.html). El reinicio del frontend existente sigue indicado en README; no se reemplaza por un servidor con apariencia de autenticación completa. **Etapa 1 terminada; esperar solicitud de Etapa 2.**

Fuentes primarias consultadas: [Django 5.2/migraciones](https://docs.djangoproject.com/en/5.2/topics/migrations/), [Django/usuario personalizado](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/), [versiones mantenidas](https://www.djangoproject.com/download/), [allauth 65.20.0/requisitos](https://github.com/pennersr/django-allauth/blob/65.20.0/docs/installation/requirements.rst), [headless](https://github.com/pennersr/django-allauth/blob/65.20.0/docs/headless/installation.rst) e [instalación psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html).

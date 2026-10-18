# PostgreSQL local y revisión del borrador de modelos

Etapa 0, 17-10-2026. **Revisión de solo lectura; no se aprobó/copió el borrador, no se ejecutaron migraciones, no se crearon ni eliminaron bases, roles, tablas o volúmenes.**

## 1. Estado real observado

| Elemento | Resultado |
| --- | --- |
| Docker cliente/servidor | 29.8.2 / 29.8.2 |
| Proyecto Compose / servicio | el-chilito / db; configuración de la raíz activa |
| Contenedor | el-chilito-db-1, running, health healthy |
| Imagen / servidor consultado | postgres:17 / PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2) |
| Puerto publicado | 127.0.0.1:5433 → 5432, limitado al equipo |
| Persistencia | Volumen Docker el-chilito_pgdata montado en /var/lib/postgresql/data; no bind del directorio vivo de datos en OneDrive |
| Base | el_chilito, UTF8, owner el_chilito_migrador |
| Roles | el_chilito_migrador y el_chilito_app: LOGIN; sin SUPERUSER, CREATEDB, CREATEROLE, REPLICATION o BYPASSRLS |
| Tablas de usuario / public | Ninguna encontrada; sin secuencias/vistas materializadas o normales en public |
| Migraciones Django | public.django_migrations ausente |
| Datos de aplicación | No se consultaron filas personales; no hay estructura de aplicación en el esquema examinado |
| Secreto administrativo | Compose referencia archivo privado externo; se verificó montaje/metadatos sin abrir el archivo o leer contraseñas |

El estado actual ya supera el borrador LEEME que decía «no se inició PostgreSQL». Tener contenedor saludable y objetos preparados no demuestra un login TCP correcto desde Django, migraciones válidas, credenciales de ambos roles o respaldos recuperables.

### Permisos comprobados por catálogo

- ACL de base sin entrada PUBLIC; migrador propietario con privilegios de base y app únicamente CONNECT.
- public pertenece a pg_database_owner. PUBLIC conserva USAGE, pero no CREATE; app tiene USAGE explícito y no CREATE.
- has_database_privilege(app, CONNECT)=true; CREATE=false. has_schema_privilege(app, public, USAGE)=true; CREATE=false.
- Default privileges de el_chilito_migrador en public: tablas SELECT/INSERT/UPDATE/DELETE para app; secuencias USAGE/SELECT para app.
- No hay grants sobre tablas aún, porque no existen.

Estas comprobaciones se hicieron mediante psql dentro del contenedor como postgres, exclusivamente con BEGIN READ ONLY / COMMIT. Solo SHOW y SELECT sobre catálogos; no se consultaron hashes de contraseñas, entornos de contenedor, secretos o logs de correo. No se autenticó como migrador/app ni se verificaron sus contraseñas.

Default privileges se aplican a objetos futuros creados por el rol indicado; no corrigen objetos existentes ni los creados como postgres. Las migraciones deberán correr realmente como migrador. Revisar sus efectos sobre tablas de Django/allauth y limitar operaciones sensibles cuando se apruebe el esquema. [PostgreSQL 17: ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).

## 2. SQL administrativo existente

La raíz activa contiene infra/00_preparar_postgresql_local.sql, autorizado en un turno anterior. Tiene metacomandos psql, por lo que no es un archivo para Query Tool genérico ni una migración Django.

La base y los roles ya existen: **no volver a ejecutar como si la instancia fuera nueva**, no borrar para hacerlo pasar. El script no es idempotente y tampoco debe envolverse en una transacción global por CREATE DATABASE. Corregir o ampliar permisos futuros únicamente después de revisar el catálogo de ese momento y con una tarea autorizada.

No se ha cambiado ese archivo ni compose.yaml. PostgreSQL sigue funcionando con su volumen actual; no se detuvo ni reinició Docker.

## 3. Origen de la propuesta revisada

Directorio externo, conservado sin cambios:

`C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\output\propuesta-bd-2026-10-17`

Leídos: LEEME.md, cuentas/models.py, huerto/models.py, settings_fragment.py y SQL administrativo. Es un borrador con revisión previa de sintaxis, no una aplicación Django probada.

Incluye 16 modelos conceptuales: Usuario; Huerto, Membresia, Zona, Dispositivo, Sensor, Canal, Calibracion, MensajeDispositivo, Lectura, Actuador, EventoActuador, Aviso, AvisoLeido y Auditoria. No se importaron/ejecutaron ni se copiaron a backend.

## 4. Hallazgos y decisiones antes de migrar

| ID / prioridad | Evidencia del borrador | Ajuste/propuesta y criterio futuro |
| --- | --- | --- |
| DB-01 / alta | Usuario(AbstractUser), username=None, email unique + UniqueConstraint Lower(email); manager busca iexact, normaliza en create_user | Base razonable para identidad por correo. Aprobar normalización y errores de colisión/carrera con allauth EmailAddress. Configurar AUTH_USER_MODEL en primera migración. No crear otro estado verified ni confiar en manager para validar fortaleza |
| DB-02 / alta | create_user aplica set_password y save, pero no full_clean/validate_password; is_active heredado no significa correo verificado | Alta/cambio pasan por biblioteca/validadores antes de persistir. Sesión, correo y membresía son estados distintos; pruebas para usuario activo sin correo y correo sin membresía |
| DB-03 / alta | Membresia única usuario/huerto, activa; Zona única huerto/numero, rango 1–3 | No se fuerza «exactamente tres filas» o un solo huerto global en SQL. Provisionar huerto + zonas en transacción/operación idempotente; asignación explícita, no automática en signup. DB tests de duplicados/concurrencia; no convertir tres zonas en tres dispositivos inventados |
| DB-04 / alta | Sensor/Actuador/Aviso comparan pertenencia a huerto en clean(); Lectura y EventoActuador comparan dispositivo relacionado | Son comprobaciones Python, no restricciones SQL entre tablas. save/update/bulk_create pueden saltarlas. Definir frontera de escritura y transacciones/bloqueos o restricciones/triggers mediante migración cuando proceda. Probar canal/mensaje, zona/dispositivo y aviso/huerto cruzados, incluso intentando evitar el servicio |
| DB-05 / alta | Las relaciones estructurales siguen siendo editables; clean del hijo no revalida historial cuando se cambia Sensor.dispositivo, Canal.sensor o Zona.huerto | Proponer inmutabilidad tras existir historial o procedimiento controlado y transaccional; probar reasignación concurrente y su efecto en lecturas/avisos previos. No solo validar la inserción inicial |
| DB-06 / alta | Lectura CheckConstraint permite valor numérico o booleano o fallo; clean distingue variable, rango, calibración y motivo | SQL no garantiza que canal nivel_bajo reciba booleano o que una lectura inválida tenga motivo. Reforzar restricciones locales representables y validación relacional en cada escritura. Rechazar no finitos/incompatibles; sin datos no insertar una lectura cero |
| DB-07 / media | Canal.choices/unidad, tipos/calidad/severidad/origen son choices; Calibracion solo evita referencias iguales; rango numérico de temperatura no se acuerda | choices no son automáticamente CHECK SQL. Determinar checks de dominio y límites técnicos confirmados; no agregar umbrales agronómicos supuestos. Restringir calibración a sonda/canal correspondiente, versión válida e historial estable |
| DB-08 / alta | Mensaje único dispositivo/id_emisor; clean exige coherencia medido_en/reloj_valido; origen es campo modificable | UUID identifica/deduplica, no autentica. Origen, recibido_en y permiso los fija servidor; definir replay, mismo UUID con contenido distinto, reloj inválido y desfases. No activar ingesta ahora |
| DB-09 / alta | Todas las FK relevantes usan PROTECT, incluso usuario/membresía/auditoría | Evita cascadas destructivas, pero no constituye política de eliminación/retención ARCO. Aprobar anonimización, conservación y baja lógica antes de tratar datos reales. No cambiar a CASCADE para resolver una excepción |
| DB-10 / media | Índice Lectura(canal,mensaje); unique(mensaje,canal); Aviso(huerto,-creado_en); otras FK/unique de Django | Inventariar índices generados antes de añadir duplicados. Consulta de última lectura filtra canal y ordena por tiempo en Mensaje: probar plan/volumen real en etapa autorizada. Definir retención y particionado solo si se justifica; no crecimiento ilimitado por defecto |
| DB-11 / alta | Auditoria con actor/dispositivo opcionales, sin secretos por comentario; defaults SQL dan app UPDATE/DELETE de todas las tablas futuras | Una tabla no es evidencia inmutable. Tras migraciones revisar grants de Auditoria, inserciones y acceso; limitar actualización/borrado ordinarios y establecer procedimiento de retención. Las restricciones de rol no sustituyen controles por fila/huerto en Django |
| DB-12 / media | Aviso y AvisoLeido separados, unique usuario/aviso; fechas coherentes de resolución | Mantener leído por usuario e idempotente; resolver condición por evidencia real, no por click. Autorizar cada lectura/consulta mediante membresía. Mapeo severidad/frontend explícito |
| DB-13 / alta | No hay modelos de términos/versiones/aceptación o una biblioteca integrada de verificación/sesión | No crear tablas Django/allauth a mano. Aceptación legal necesita propuesta aprobada/migración propia y registro cerrado hasta documentos efectivos. No duplicar código/sesiones/banderas verificadas |
| DB-14 / media | Actuador, EventoActuador propuestos; dispositivo/sensor/actuador deshabilitados por defecto | No habilitar bombas/lámpara ni agregar tablas de órdenes por inferencia. Un evento reportado no prueba flujo de agua/luz. Óptico/ventilador fuera; mantener defaults seguros |
| DB-15 / media | settings_fragment usa env DB_* y puerto predeterminado 5432 | En Windows la instancia actual usa **5433**. El fragmento no carga .env ni configura apps/auth/headless/CSRF/SMTP. Adaptar explícitamente; no copiarlo como settings completo |
| DB-16 / alta | Roles sin CREATEDB; no existe base de pruebas preparada según inventario de esta etapa | Django no debe crear test DB con rol app ni concederle CREATEDB. Preprovisionar otra DB aislada mediante operación administrativa autorizada; migrar con rol propietario de pruebas y correr acceso DML con rol de pruebas restringido. Nunca pruebas sobre el_chilito de presentación |

Django documenta que full_clean no se ejecuta automáticamente con save. Las validaciones de modelo y las restricciones de BD tienen responsabilidades diferentes: [instancias de modelo 5.2](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects).

La compatibilidad Django/allauth/psycopg debe demostrarse con dependencias exactas y migraciones en PostgreSQL. Django 5.2 soporta PostgreSQL 14+ y psycopg 3.1.8+ según [su documentación](https://docs.djangoproject.com/en/5.2/ref/databases/); esto no constituye una elección final de versiones ni pruebas de este borrador.

## 5. Estado de configuración privada

No se abrieron archivos secretos o .env, ni se solicitaron valores en chat. No se probó conectividad autenticada TCP desde Windows con cada rol.

Cuando se autorice Etapa 1: Rafael aportará privadamente DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT y política SSL local para cada proceso. Migración y ejecución usan credenciales distintas; el rol postgres no es usuario de la aplicación. Configuración propuesta: DB_NAME=el_chilito, HOST=127.0.0.1, PORT=5433; contraseñas fuera de dist/Git y sin imprimirlas. PostgreSQL vive en Docker, Django inicialmente en Windows.

Para SMTP y SECRET_KEY se necesitarán secretos separados en su etapa. No reutilizar el secreto administrativo como contraseña de app. No es necesario leerlo para esta revisión.

## 6. Comprobaciones futuras y recuperación

Antes de Etapa 1: volver a inspeccionar catálogo por si Carolina/Rafael avanzaron; no asumir que seguirá vacío. Revisar migraciones de usuario antes de migrate; si ya hubiese datos, preservar y planificar evolución.

Pruebas de esquema/contrato futuras: restricciones de duplicados y zonas, limpieza transversal y reassignment, carreras, rollback, persistencia y privilegios negativos (app sin CREATE/DROP/ALTER; migrador crea objetos de los que app obtiene solo grants acordados). Contraseñas/identidad verificadas por biblioteca; acceso por membresía.

Etapa 4: respaldar con herramientas PostgreSQL y demostrar restauración **en base aislada**, incluyendo inventario de migraciones/roles/objetos y comprobaciones de integridad. No se hizo dump/restore en Etapa 0, ni se guardaron datos personales en docs o Git. No usar down -v ni recrear el volumen como corrección.

Pendientes: aprobación Carolina/Rafael del modelo ajustado, políticas de retención/borrado/auditoría y contrato firmware; credenciales privadas y entorno aislado; versiones bloqueadas de dependencias; prueba de migración real. Estado de este documento: revisión realizada, correcciones propuestas, implementación y verificación funcional pendientes.

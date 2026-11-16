# Base de datos de El Chilito

Guía de instalación, funcionamiento y seguridad de la base. PostgreSQL 17. Comprobado el 8 de noviembre de 2026.

**Contenido:** 43 tablas, 25 funciones, 43 triggers y 60 migraciones. Ningún archivo de esta carpeta contiene contraseñas ni cuentas de usuario.

## 1. Qué archivo usar

| Situación | Qué ejecutar |
|---|---|
| Base **nueva** | `01`, `02`, `03`. **Sin parches** |
| Base que ya tiene datos | Solo los `parches/` que falten, en orden |
| Cambiar el esquema | Ver la sección 7 |

### El script definitivo es `03_esquema_completo.sql`

Reúne todo lo que hicieron los parches. Corre en una sola transacción y hace, en orden:

1. Comprueba base, rol, PostgreSQL 17 y que la base esté vacía. Si algo no coincide, se detiene.
2. Crea todas las tablas, restricciones, índices, funciones y triggers de las 61 migraciones.
3. Carga los datos iniciales: versiones de textos legales, finalidad opcional y las 9 preguntas de la guía de cuidado.
4. Registra tipos de contenido, permisos y capacidades, y marca las migraciones como aplicadas.
5. Aplica los privilegios de `sql/privilegios.sql`.

**Verificación:** se instaló sobre una base temporal vacía y se comparó con la base oficial, que recibió los parches 01 a 07 (antes de existir el 08; el 08 y la migración 0013 aún no se han aplicado ni comparado en la oficial). Coinciden las 264 columnas, 235 restricciones, 183 índices, 43 triggers, 25 funciones y todos los privilegios del rol de la aplicación. `manage.py migrate --check` no encontró migraciones pendientes.

**No ejecutar `03` sobre una base con datos.** Se detiene por seguridad.

### Parches (solo bases anteriores)

| Parche | Añade |
|---|---|
| `01_correccion_exige_tipo` | Una corrección de mantenimiento debe indicar el tipo |
| `02_documentos_con_texto_publicado` | Versión 0.2 del aviso y los términos |
| `03_auditoria_retiro_factores` | Auditoría del retiro de segundo factor |
| `04_soporte_resuelto_y_buzon` | Casos resueltos, avisos por correo y buzón de consultas |
| `05_consulta_archivada_a_atendida` | Pasar una consulta de archivada a atendida |
| `06_vinculacion_huerto` | Códigos de vinculación y una cuenta por huerto activo |
| `07_guias_cuidado` | Guías de cuidado y capacidad `gestionar_guias` |
| `08_retiro_capacidades_gobernanza` | Retira las capacidades `ver_gobernanza` y `gestionar_cambios`. **Antes** hay que comprobar con un `SELECT` (fase 0 de `PLAN-RETIRO-GOBERNANZA-Y-DESPLIEGUES.md`) que ninguna cuenta administradora dependa solo de ellas |

## 2. Instalación desde cero

### Instalar el servidor (Ubuntu)

pgAdmin es solo la ventana; hace falta el servidor. Ubuntu 24.04 trae la versión 16, así que se usa el repositorio oficial de PostgreSQL:

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install -y postgresql-17
sudo -u postgres psql -c "\password postgres"
```

El último comando pide la contraseña del administrador sin mostrarla.

### Crear roles y base

En pgAdmin, registra el servidor con host `localhost`, puerto `5432` y usuario `postgres`. Después, en la base `postgres`, abre **Query Tool**:

1. Ejecuta `01_roles.sql`.
2. En **Login/Group Roles**, pon una contraseña distinta a `chilito_pkg_owner` y a `chilito_pkg_runtime`, en la pestaña **Definition**.
3. Ejecuta `02_crear_base.sql`, solo esa sentencia.

### Crear el esquema

1. Registra otra conexión con usuario `chilito_pkg_owner` y base `chilito_integracion_sinteticos`.
2. En su **Query Tool**, carga `03_esquema_completo.sql` y ejecútalo completo.

Si falla, no queda nada a medias: copia el error y usa **Rollback** antes de reintentar.

### Comprobar

- `04_inspeccion.sql` muestra la estructura, sin datos personales.
- `05_prueba_triggers.sql`: en **Messages** debe terminar en `RESUMEN: 19 casos, 0 fallos`. No deja datos.

### Configurar la aplicación

En el `.env` local, que nunca se comparte:

```
CHILITO_DB_HOST=127.0.0.1
CHILITO_DB_PORT=5432
CHILITO_DB_NAME=chilito_integracion_sinteticos
CHILITO_DB_USER=chilito_pkg_runtime
CHILITO_DB_PASSWORD=
CHILITO_ORIGIN=http://localhost:8780
```

La aplicación usa siempre `chilito_pkg_runtime`. `chilito_pkg_owner` queda solo para cambios de esquema.

## 3. Después de instalar

Todos se ejecutan en **Query Tool** como `chilito_pkg_owner`, cambiando solo las líneas marcadas. La cuenta debe existir y, para capacidades, tener TOTP o llave de acceso.

| Script | Para qué |
|---|---|
| `preparar_administrador_principal.sql` | Prepara una cuenta registrada con las cinco capacidades iniciales, el huerto principal, su dispositivo y su asignación de mantenimientos |
| `asignar_capacidad.sql` | Concede una capacidad concreta: atender consultas, vincular huertos o gestionar guías |
| `09_registrar_equipo.sql` | Registra un huerto entregable y su dispositivo. No crea membresías |
| `07_consultar_cookies.sql` | Consulta decisiones de cookies, solo lectura y sin identidades |

### Asignar una capacidad

Abre `asignar_capacidad.sql` y cambia las dos líneas marcadas: `correo` y `capacidad`.
Elige solo una de estas capacidades por ejecución:

| Valor de `capacidad` | Qué permite | Estructura necesaria |
|---|---|---|
| `atender_consultas` | Acceder al buzón de «Solicitudes del producto» | Instalación actual o parche 04 |
| `vincular_huertos` | Emitir y revocar códigos de vinculación | Instalación actual o parche 06 |
| `gestionar_guias` | Crear, editar, publicar y retirar guías de cuidado | Instalación actual o parche 07 |

Ejecuta el archivo completo en Query Tool. La cuenta debe estar activa y haber configurado TOTP o una
llave de acceso. Repetir la ejecución conserva una sola asignación; elegir otra capacidad concede
únicamente esa otra. El script no crea cuentas, huertos ni capacidades y no cambia privilegios de PostgreSQL.
Al emitir o revocar códigos, el panel sigue pidiendo un segundo factor usado en los últimos cinco minutos.

## 4. Cómo funciona

### Cuentas y acceso

| Tabla | Qué guarda |
|---|---|
| `cuentas_usuario` | Cuentas. La contraseña se guarda solo como resumen |
| `account_emailaddress`, `account_emailconfirmation` | Correos y su verificación |
| `mfa_authenticator` | TOTP, códigos de recuperación y llaves de acceso. Los secretos van cifrados. Nunca PIN ni biometría |
| `django_session` | Sesiones en el servidor |
| `cuentas_cuotas_acceso` | Contadores de límites de uso |
| `cuentas_confirmacionregistrolocal` | Confirmación técnica del registro |
| `auth_*`, `cuentas_usuario_groups`, `cuentas_usuario_user_permissions` | Permisos. Las capacidades administrativas se asignan aquí |

Un índice sobre `chilito_identidad_correo` impide duplicar cuentas: en Gmail ignora puntos y lo que va tras `+`.

### Huertos

| Tabla | Qué guarda |
|---|---|
| `huerto_huerto` | Cada huerto. Al crearlo, un trigger genera sus 3 zonas |
| `huerto_zona` | Las 3 plantas. No se pueden borrar |
| `huerto_membresia` | Qué cuenta tiene qué huerto. Una sola activa por cuenta |
| `huerto_aviso`, `huerto_avisoleido` | Avisos y su lectura |
| `datos_dispositivo` | Equipo de cada huerto |

### Operación

| Tabla | Qué guarda |
|---|---|
| `datos_codigovinculacion` | Códigos de vinculación, solo su resumen. Se cierran una vez |
| `datos_mantenimiento` | Cuidados registrados. Nunca se modifican |
| `datos_revisionmantenimiento` | Correcciones y anulaciones. No hay borrado físico |
| `datos_asignacionmantenimiento` | Qué huertos gestiona cada administrador |
| `datos_casosoporte`, `datos_permisosoporte` | Casos y permisos de máximo 24 h, con verificador HMAC |
| `datos_sesiontecnica`, `datos_resolucionsoporte` | Sesiones técnicas y resolución del caso |
| `datos_solicitud` | Solicitudes de riego, lámpara o despliegue, sin ejecutar |
| `datos_validacionversion`, `datos_revisionconocimiento` | Registro administrativo de versiones y notas |
| `datos_consultaproducto`, `datos_avisocorreo` | Consultas de «Consíguelo» y estado de los avisos |
| `datos_guiacuidado` | Guías de cuidado. Se retiran, no se borran |
| `datos_auditoria` | Quién hizo qué, sin texto libre ni secretos |
| `web_idempotencia` | Evita repetir una escritura al reintentar |

### Privacidad

| Tabla | Qué guarda |
|---|---|
| `privacidad_documentoversion` | Versiones de los textos legales, con su huella |
| `privacidad_finalidadopcional` | Finalidades opcionales |
| `privacidad_sujetoprivacidad` | Identificador seudónimo de cuenta o navegador |
| `privacidad_decisionprivacidad`, `privacidad_preferenciafinalidad` | Decisiones y su estado vigente |
| `privacidad_eventoprivacidad` | Accesos y rectificaciones |
| `privacidad_conteonavegacion` | Totales diarios, sin identidad |

Los textos visibles se redactan y publican desde Administración → Textos legales.

### Flujos

- **Vincular:** el operador emite un código; la cuenta lo consume; se crea la membresía. Un trigger exige, al confirmar, un código consumido coherente.
- **Soporte:** la persona abre un caso y autoriza con un token mostrado una vez; se guarda solo el verificador. El administrador abre una sesión técnica mientras el permiso esté vigente.
- **Mantenimiento:** el registro original no cambia. Cada corrección o anulación es una fila nueva y exige asignación del editor al huerto.
- **Consulta del producto:** se guarda con su aviso en la misma transacción. Un fallo de correo no pierde la consulta.

## 5. Funciones y triggers

| Función | Qué impide o hace |
|---|---|
| `chilito_historial_inmutable` | Modificar o borrar historiales: auditoría, mantenimiento, casos, solicitudes, resoluciones, versiones, conocimiento, revisiones y dispositivos |
| `chilito_privacidad_historial_inmutable` | Lo mismo para decisiones, eventos, documentos y finalidades |
| `chilito_datos_relaciones` | Mezclar recursos: dispositivo de otro huerto, permiso de otro solicitante, auditoría o sesión de otro caso |
| `chilito_auditoria_revision` | Auditar una revisión con otro actor u otro huerto |
| `chilito_revision_mantenimiento` | Editar sin asignación, fuera de orden o tras una anulación |
| `chilito_permiso_revocar` | Cambiar un permiso; solo revocarlo, sin vuelta atrás |
| `chilito_tecnica_cerrar` | Cambiar una sesión técnica; solo cerrarla una vez |
| `chilito_codigo_vinculacion` | Borrar un código, reabrirlo o alterar sus datos |
| `chilito_membresia_por_codigo` | Crear una membresía sin código consumido, salvo el propietario de la tabla |
| `chilito_consulta_atencion` | Borrar consultas o saltarse las transiciones de atención |
| `chilito_aviso_correo` | Borrar avisos o modificarlos una vez aceptados |
| `chilito_guia_cuidado` | Borrar guías, cambiar identidad o autoría, o editar sin avanzar la versión |
| `chilito_usuario_sin_privilegios` | Que el rol de la aplicación cree cuentas `staff`, superusuario o inactivas |
| `chilito_proteger_relacion`, `chilito_asignacion_estable`, `chilito_proteger_mfa`, `chilito_proteger_aviso`, `chilito_proteger_lectura_aviso`, `chilito_privacidad_sujeto_estable` | Reasignar la identidad o el dueño de un registro |
| `chilito_lectura_exige_membresia` | Marcar leído un aviso sin membresía activa |
| `chilito_conservar_zona`, `chilito_crear_tres_zonas` | Borrar zonas; crea las 3 de cada huerto |
| `chilito_privacidad_ambitos`, `chilito_privacidad_relaciones` | Decisiones que no corresponden al sujeto o al documento |
| `chilito_identidad_correo` | Normaliza el correo para detectar cuentas duplicadas |

## 6. Seguridad

Esto describe controles comprobados. **No es una certificación** ni afirma cumplimiento integral de ASVS o SSDF.

| Control | Cómo se aplica | Comprobado |
|---|---|---|
| Mínimo privilegio (alineado con ASVS v5.0.0-13.2.2) | La web usa `chilito_pkg_runtime`, sin `DELETE` en historiales, sin DDL y con `UPDATE` por columna donde basta | Prueba `crud`: 71 de 71 |
| Separación de roles | `chilito_pkg_owner` solo para esquema; ambos sin superusuario ni creación de roles | `01_roles.sql` |
| Historial protegido | Los triggers bloquean cambios, incluso con errores en la aplicación | `05_prueba_triggers`: 19 casos, 0 fallos |
| Autorización por recurso (alineado con ASVS v5.0.0-8.2.2) | El servidor decide; los triggers son una segunda barrera entre huertos, casos y cuentas | Suite y `crud` |
| Secretos | Solo resúmenes o verificadores de contraseñas, códigos y tokens; 2FA cifrado | Suite |
| Integridad | `CHECK`, claves foráneas, índices únicos y transacciones | Instalación y suite |
| Sin contraseñas en SQL | Se definen aparte, nunca en estos archivos | Búsqueda de secretos |
| Instalación segura | `03` se detiene si la base, el rol o la versión no coinciden | Instalación en base temporal |

**Límites:**
- Los triggers protegen frente a errores de la aplicación, no frente a un propietario de la base malintencionado o un rol totalmente comprometido.
- Las contraseñas de los roles dependen de quien administra el servidor.
- En la nube falta comprobar TLS real, respaldos, restauración y cuentas administrativas del servicio. En un servicio gestionado, `01` a `03` pueden necesitar ajustes de permisos; **no está probado**.

## 7. Si cambia el esquema

No edites `03_esquema_completo.sql`: se genera desde las migraciones y `sql/privilegios.sql`. En este orden:

1. Migración nueva. Nunca editar las existentes.
2. Actualizar `sql/privilegios.sql` si hay tablas o columnas nuevas.
3. Regenerar: `python backend/tools/generar_sql_instalacion.py`.
4. Crear un parche nuevo en `parches/` para las bases con datos.

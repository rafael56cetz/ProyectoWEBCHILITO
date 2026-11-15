# El Chilito · Base de datos v2: cómo funciona

Guía de la base **v2** (`el_chilito_base_v2.sql`), diseñada desde cero el 14 de noviembre de 2026 sobre el flujo nuevo de vinculación IoT. Sustituye por completo a la v1 (`el_chilito_base_completa.sql`, `designar_administrador.sql` y parches).

**Contexto fijo del proyecto:** huerto urbano inteligente de chile habanero · 1 huerto = 1 ESP32 = 3 plantas = 1 depósito de 19 L · solo Yucatán (`America/Merida`) · Python + Django + allauth · PostgreSQL 17 · Google Cloud · MQTT con Mosquitto.

---

## Índice

1. [Archivos](#1-archivos)
2. [Los tres roles](#2-los-tres-roles)
3. [Instalar desde cero](#3-instalar-desde-cero)
4. [Las 46 tablas](#4-las-46-tablas)
5. [Flujos](#5-flujos)
6. [El «actor»: cómo sabe la base quién hace cada cambio](#6-el-actor)
7. [Administración y super administrador](#7-administración-y-super-administrador)
8. [Reglas que protege la base](#8-reglas-que-protege-la-base)
9. [Qué puede hacer cada rol](#9-qué-puede-hacer-cada-rol)
10. [Funciones y vistas](#10-funciones-y-vistas)
11. [Tarea periódica y conservación de datos](#11-tarea-periódica-y-conservación-de-datos)
12. [Publicar los textos legales](#12-publicar-los-textos-legales)
13. [Consultas útiles en pgAdmin](#13-consultas-útiles-en-pgadmin)
14. [Qué cambió respecto a la v1](#14-qué-cambió-respecto-a-la-v1)
15. [Instrucciones para adaptar Django](#15-instrucciones-para-adaptar-django)
16. [Cómo se probó](#16-cómo-se-probó)
17. [Pendiente para la fase IoT](#17-pendiente-para-la-fase-iot)

---

## 1. Archivos

| Archivo | Para qué |
|---|---|
| `sql/el_chilito_base_v2.sql` | **Script único.** Instala la base completa en una base vacía, en una sola transacción |
| `sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md` | Esta guía |
| `sql/pruebas/pruebas_v2.py` | 149 pruebas automáticas de flujos y reglas con los tres roles |
| `sql/pruebas/prueba_depuracion.py` | Prueba de la depuración de 90 días con resumen por hora |

`designar_administrador.sql` **ya no se usa**: lo sustituyen funciones (sección 7).

---

## 2. Los tres roles

| | `chilito_pkg_owner` | `chilito_pkg_runtime` | `chilito_pkg_iot` (nuevo) |
|---|---|---|---|
| ¿Quién lo usa? | **Tú**, en pgAdmin, y la tarea periódica | **La página** (Django). `.env`: `CHILITO_DB_USER` | **Servicios en la nube**: receptor MQTT del ESP32 y la IA |
| ¿Dueño de la base? | Sí | No | No |
| ¿Crear o borrar tablas? | Sí | No | No |
| ¿Nombrar super admin? | **Sí**, con una función | No | No |
| ¿Ve cuentas, legal, soporte, ventas? | Sí | Sí (Django decide qué muestra) | **No** |
| ¿Escribe telemetría? | — | No | **Sí**: mediciones, actuaciones, eventos, resultados de comandos y autodiagnósticos, avisos al dueño y resúmenes de IA |

Si alguien vulnera el servicio IoT, **no puede leer cuentas ni correos, vincular equipos, crear comandos ni tocar nada legal**.

---

## 3. Instalar desde cero

La base v1 no tiene datos que conservar, así que se instala desde cero.

**Paso 1 · Roles** (como `postgres`, en la base `postgres`):

```sql
CREATE ROLE chilito_pkg_owner   LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE chilito_pkg_iot     LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE chilito_pkg_runtime SET search_path = pg_catalog, public;
ALTER ROLE chilito_pkg_iot     SET search_path = pg_catalog, public;
```

Si los dos primeros ya existen, crea solo el tercero. Pon las contraseñas en pgAdmin (**Login/Group Roles › Definition**), nunca en un archivo.

**Paso 2 · Base** (como `postgres`), esta línea **sola**:

```sql
CREATE DATABASE chilito_v2 OWNER chilito_pkg_owner;
```

**Paso 3 · Esquema con las migraciones de Django** (fuente de verdad, según el diseño de seguridad, sección 11). En `backend/`, como propietario y solo para este comando:

```
CHILITO_DB_NAME=chilito_v2 CHILITO_DB_USER=chilito_pkg_owner CHILITO_DB_PASSWORD=<contraseña> python manage.py migrate
```

Las migraciones crean una base **equivalente** a `el_chilito_base_v2.sql`; la equivalencia se comprueba en la fase 1 de `docs/EJECUCION-v2.md`. **Nunca se usa `migrate --fake`.**

El script SQL sirve para **revisar** la estructura en una base aparte o para las **pruebas** de `sql/pruebas/` (pgAdmin › Query Tool como `chilito_pkg_owner` › abrir el archivo › ejecutar). Comprobación en cualquiera de las dos rutas: 46 tablas y 5 vistas.

```sql
SELECT count(*) FILTER (WHERE table_type='BASE TABLE') AS tablas,
       count(*) FILTER (WHERE table_type='VIEW') AS vistas
FROM information_schema.tables WHERE table_schema='public';
```

**Paso 4 · Textos legales** (sección 12). **Sin términos y aviso publicados nadie puede registrarse**: la base lo impide.

**Paso 5 · Tu cuenta.** Regístrate en la página, verifica el correo y ejecuta en pgAdmin:

```sql
SELECT chilito_designar_super_admin('tu-correo@dominio.com');
```

Al entrar, la página te pedirá activar la app autenticadora o una llave de acceso para usar el panel.

**Paso 6 · Tarea periódica** cada hora (sección 11).

**Paso 7 · `.env`** (la página usa el rol de la aplicación):

```
CHILITO_DB_NAME=chilito_v2
CHILITO_DB_USER=chilito_pkg_runtime
CHILITO_DB_PASSWORD=<contraseña de chilito_pkg_runtime>
```

---

## 4. Las 46 tablas

**Django y allauth (13)**, con el formato exacto de Django. No se cambian sus nombres.

| Tabla | Qué guarda |
|---|---|
| `django_migrations`, `django_content_type`, `django_session` | Migraciones, catálogo de modelos y sesiones (también los códigos de 6 dígitos de registro y acceso) |
| `auth_permission` | Permisos de Django. **Aquí viven las 10 capacidades** |
| `auth_group`, `auth_group_permissions`, `cuentas_usuario_groups` | Grupos: Django los exige, El Chilito no los usa |
| `cuentas_usuario` | La cuenta. Añade `anonimizacion_solicitada_en` y `anonimizada_en` |
| `cuentas_usuario_user_permissions` | **Capacidades de cada cuenta** |
| `account_emailaddress`, `account_emailconfirmation` | Correo verificado (allauth). La segunda queda vacía |
| `mfa_authenticator` | App autenticadora, llaves de acceso y códigos de recuperación |
| `cuentas_cuotas_acceso` | Caché de Django: límites de intentos |

**Huertos (3):** `huerto` · `huerto_planta` · `huerto_planta_etapa`

**Equipos e IoT (11):** `dispositivo` · `codigo_vinculacion` · `dispositivo_evento` · `medicion` · `medicion_planta` · `resumen_hora_huerto` · `resumen_hora_planta` · `actuacion` · `comando` · `autodiagnostico` · `autodiagnostico_revision`

**Cuidados y soporte (5):** `cuidado` · `cuidado_revision` · `guia_cuidado` · `soporte_caso` · `soporte_sesion`

**Comunicación y ventas (5):** `notificacion` · `ia_resumen` · `consulta_producto` · `correo_pendiente` · `venta`

**Legal y privacidad (6):** `documento_legal` · `privacidad_finalidad` · `privacidad_sujeto` · `privacidad_decision` · `privacidad_preferencia` · `conteo_navegacion`

**Control (3):** `capacidad_historial` · `auditoria` · `web_idempotencia`

Cada tabla está explicada con un comentario en el script, justo antes de crearla.

---

## 5. Flujos

### 5.1 Visitante sin cuenta

- Lee la portada y los textos legales. **Ahora el texto sale de `documento_legal`** (la versión vigente), no de un HTML.
- **Cookies:** al aceptar, rechazar o configurar, se crea un `privacidad_sujeto` de ámbito `navegador`, una fila en `privacidad_decision` (con la política de cookies vigente, IP recortada y navegador) y la preferencia vigente en `privacidad_preferencia`. Si hay sesión iniciada, la decisión guarda `usuario_id` y en la bitácora aparece su correo.
- **«Consíguelo»:** una fila en `consulta_producto` (folio `CP-…`). La base crea sola el correo al buzón de soporte (`correo_pendiente`) y un aviso a cada admin con `atender_consultas`.

### 5.2 Registro (sin cambios para la persona)

Correo, contraseña y **las dos casillas obligatorias**. En **una transacción**, Django inserta:

1. `cuentas_usuario` y `account_emailaddress` (sin verificar).
2. `privacidad_sujeto` (ámbito `cuenta`).
3. **Dos** filas en `privacidad_decision`: `aceptacion_terminos` y `lectura_aviso`, cada una con el documento **vigente** (`chilito_documento_vigente('terminos')` y `chilito_documento_vigente('aviso_privacidad')`), IP recortada y navegador.

**Al confirmar la transacción, la base comprueba que existan esas dos aceptaciones. Si falta alguna, la cuenta no se crea.**

El código de 6 dígitos, la verificación, la bienvenida, el inicio de sesión, el segundo factor, las llaves de acceso y la recuperación de contraseña **funcionan igual que antes**.

### 5.3 Nueva versión de términos o aviso

1. Un admin con `gestionar_legales` crea un **borrador**, lo edita y lo **publica**.
2. La base calcula la huella SHA-256, exige que la versión sea **mayor** que la vigente y **avisa a todas las cuentas** (notificación de origen `legal`).
3. Al iniciar sesión, Django consulta `SELECT * FROM chilito_aceptaciones_pendientes(<id>)`. Si devuelve filas, muestra la pantalla de aceptación y **no deja seguir** hasta guardar las decisiones con la versión vigente.

### 5.4 Huerto y plantas

- La persona **crea su huerto**. El nombre es opcional («Mi huerto») y la zona siempre es `America/Merida`. Nace con **3 plantas** («Planta 1, 2, 3»).
- Límites: **3 huertos activos** por cuenta y **solo 1 sin equipo** a la vez.
- Cada planta tiene nombre, fecha de siembra y etapa: `sin_sembrar → germinacion → plantula → crecimiento → floracion → fructificacion`. Al cambiar la etapa, la fecha se pone sola (hoy en Mérida) y queda en `huerto_planta_etapa`.
- Un huerto **no se borra: se archiva**, y antes hay que desvincular su equipo.

### 5.5 Vinculación del equipo (flujo nuevo)

| Paso | Quién | En la base |
|---|---|---|
| 0 | Admin con `gestionar_dispositivos` da de alta el ESP32 en el inventario | `dispositivo` (disponible) + evento `alta` |
| 1 | La persona, en su huerto, pulsa «Vincular equipo» | Django genera un código aleatorio seguro, guarda su **HMAC-SHA256** en `codigo_vinculacion` (10 min) y lo muestra **una vez** |
| 2 | Conecta el ESP32, entra a `Huerto-Setup-XXXX` → `192.168.4.1`, escribe su Wi-Fi y el código | Nada (es local) |
| 3 | El ESP32 llama por HTTPS al backend con su identificador, su credencial y el código | Django **verifica la credencial** contra `credencial_hash` y llama a `chilito_vincular_dispositivo(identificador, hmac_del_codigo)` |
| 4 | La función comprueba código, vigencia, uso, equipo, retiro, ocupación y huerto | Código `utilizado`, equipo `vinculado`, evento `vinculado`, notificación a la persona y auditoría |
| 5 | El backend entrega las credenciales MQTT y el ESP32 empieza a publicar | `dispositivo.conexion = 'en_linea'` (lo marca el servicio IoT) |

Respuestas posibles de la función: `vinculado`, `codigo_invalido`, `codigo_vencido`, `codigo_usado`, `dispositivo_desconocido`, `dispositivo_retirado`, `dispositivo_ocupado`, `huerto_no_disponible`.

**Desvincular:** el dueño, o un admin con `gestionar_dispositivos`, llama a `chilito_desvincular_dispositivo(id)`. El equipo vuelve a `disponible`, queda el evento y llega un aviso al dueño. `dispositivo_evento` guarda **a qué huerto perteneció cada equipo y cuándo**.

### 5.6 Telemetría (servicio IoT)

- Cada mensaje es una fila en `medicion` (temperatura, humedad del aire, luz, depósito con agua) y **3 filas** en `medicion_planta`: humedad del sustrato de cada planta en porcentaje y, además, la **lectura cruda del sensor** (`adc_crudo`, 0–4095) para calibración y soporte.
- La base solo acepta mediciones del **equipo vinculado a ese huerto** y con valores en rango.
- Riegos automáticos, lámpara y ventilador van a `actuacion`. **El estado actual de la lámpara es su última fila.**
- Conexión y firmware: el servicio IoT actualiza `dispositivo.conexion`, `ultima_conexion_en` y `firmware_version`, y la base escribe sola los eventos `conectado`, `desconectado` y `firmware_actualizado`.
- **Gráficas:** detalle de los últimos 90 días en `medicion`; para más tiempo, `resumen_hora_huerto` y `resumen_hora_planta`.

### 5.7 IA y avisos

- El servicio de IA lee mediciones, resúmenes y cuidados, y escribe en `ia_resumen` (la ficha de «Mi huerto» muestra el último; hay historial de 30 días).
- Los avisos críticos («Depósito sin agua», «Planta 2 seca», «Equipo desconectado») son filas en `notificacion` con origen `dispositivo` o `ia`. El servicio IoT **solo puede avisar al dueño de ese huerto**.
- **`notificacion` es el centro de avisos de todos:** equipo, IA, legal, soporte, vinculación y sistema. Los administradores reciben ahí los casos y las consultas nuevas.

### 5.8 Comandos: riego, lámpara y soporte

- Persona: `regar` (planta y segundos, 1 a 30), `lampara_apagar` («Apagar lámpara»), `lampara_automatico` («Restaurar control») y `autodiagnostico`.
- Soporte, solo dentro de una sesión técnica: además `reiniciar`, `probar_bomba`, `ventilador_encender`, `ventilador_apagar` y `lectura_inmediata`.
- Estados: `pendiente → enviado → confirmado | fallido | expirado`. No se acumulan dos órdenes iguales sin resolver. A los 10 minutos sin respuesta, la tarea periódica las marca `expirado`.

### 5.9 Autodiagnóstico («Revisar mi equipo»)

1. La persona crea un comando `autodiagnostico` y **la base crea sola** el autodiagnóstico (`en_curso`).
2. El ESP32 reporta una fila por componente en `autodiagnostico_revision`: conexión, sensor de ambiente, sensor de luz, los 3 sensores de sustrato, flotador, las 3 bombas, lámpara y ventilador. Cada una puede ser `correcto`, `falla`, `sin_respuesta` o `no_instalado`.
3. Al marcarlo `completado`, **la base calcula** `correcto` o `con_fallas`. Si el comando expira, queda `sin_respuesta`.

### 5.10 Soporte remoto (sin token)

| Paso | Quién | En la base |
|---|---|---|
| 1 | La persona pulsa «Solicitar revisión técnica», elige el problema, escribe una nota y **marca la autorización** | `soporte_caso` (abierto, folio `CS-…`, autorización de 24 h, autodiagnóstico adjunto) |
| 2 | Automático | Correo al buzón de soporte y aviso a cada admin con `atender_soporte` |
| 3 | El admin pulsa **«Atender»** | `estado = en_atencion`, `atendido_por_id`; aviso a la persona |
| 4 | El admin pulsa **«Conectar»** | `soporte_sesion`, solo si la autorización está vigente y no revocada |
| 5 | Diagnóstico y acciones remotas | Comandos de origen `soporte` ligados a la sesión |
| 6a | La persona pulsa **«Revocar acceso»** | `autorizacion_revocada_en`; **la base cierra la sesión al instante** y bloquea más órdenes |
| 6b | El admin **resuelve** | `resuelto` con su resultado; termina la autorización y se cierra la sesión |

La identidad está garantizada porque **solo el dueño del huerto, con su sesión iniciada, puede crear el caso**. No viaja ningún secreto.

### 5.11 Cuidados

- `rellenar_deposito` es **del huerto** (un solo depósito). `sustrato`, `germinacion` y `cosecha` son **de una planta**. `inspeccion` puede ser de una planta o del huerto.
- La cosecha admite el **número de chiles** (opcional). La fecha real del cuidado puede ser de **hasta 7 días atrás**.
- No se modifican. Un admin con `gestionar_mantenimientos` los **corrige o anula** en `cuidado_revision` (numeradas 1, 2, 3…, siempre con motivo).

### 5.12 Ventas

Un admin con `gestionar_ventas` registra equipo, comprador (nombre, correo y cuenta si la tiene), **municipio de Yucatán**, precio en MXN y fecha de venta (no futura).

- **Pago:** importe recibido (de 0 al precio) y referencia del pago. La base calcula `estado_pago`: `pendiente`, `parcial` o `completo`.
- **Entrega:** a domicilio o recogida acordada, con fecha prevista y fecha real.

Solo hay **una venta vigente por equipo**. Las ventas no se borran: se cancelan. Después de registrarla solo cambian el pago, la entrega, la nota o la cancelación.

### 5.13 Anonimizar la cuenta («borrar mi cuenta»)

1. La persona lo pide: Django guarda `anonimizacion_solicitada_en = now()`. Puede **cancelarlo** dentro de los 15 días (volviendo a poner `NULL`).
2. A los 15 días, la tarea periódica ejecuta `chilito_anonimizar_cuenta`:
   - libera sus equipos y archiva sus huertos;
   - cancela sus casos y le retira las capacidades;
   - borra su correo, su segundo factor y sus avisos;
   - deja la cuenta como `anonimo-<id>@anonimo.invalid`, inactiva.
3. Se conservan **sin datos personales**: la bitácora de consentimientos (aparece como «Cuenta eliminada», como prueba legal), la auditoría, los cuidados y las mediciones de los huertos. Las **ventas** conservan sus datos de facturación.

---

## 6. El «actor»

Para las reglas de «solo el dueño» o «solo quien tiene la capacidad», **Django debe decirle a la base qué cuenta hace el cambio**. En cada transacción de una petición con sesión:

```python
with connection.cursor() as c:
    c.execute("SELECT set_config('chilito.actor_id', %s, true)", [str(request.user.id)])
    # opcional, para el historial de capacidades:
    c.execute("SELECT set_config('chilito.motivo', %s, true)", [motivo])
```

El `true` hace que solo valga **dentro de esa transacción**. Lo más sencillo es un middleware con `ATOMIC_REQUESTS = True`, o un decorador en las vistas que escriben.

**Sin actor, la base rechaza:** crear huertos, generar códigos, dar órdenes, registrar cuidados, crear o atender casos, conectar o cerrar sesiones técnicas, marcar avisos leídos, dar o quitar capacidades, publicar textos legales, editar guías, registrar ventas, desvincular equipos y dar de alta equipos.

**No necesitan actor:** el registro de cuentas, la vinculación desde el ESP32 (`chilito_vincular_dispositivo`), las decisiones de cookies y el formulario «Consíguelo».

---

## 7. Administración y super administrador

### Las 10 capacidades

| Capacidad | Pantalla del panel |
|---|---|
| `ver_flota` | Telemetría de flota |
| `atender_soporte` | Consola remota |
| `gestionar_mantenimientos` | Corregir y anular cuidados (todos los huertos) |
| `atender_consultas` | Solicitudes del producto («Consíguelo») |
| `gestionar_dispositivos` | Inventario de equipos, desvinculación, retiro y rotación de credencial |
| `gestionar_ventas` | Ventas |
| `gestionar_guias` | Guías de cuidado |
| `gestionar_legales` | Textos legales: borradores y publicación |
| `ver_consentimientos` | Bitácora de consentimientos |
| `gestionar_administradores` | **Super administrador:** dar y quitar las otras 9; ver administradores, historial y actividad |

En Django: `user.has_perm('cuentas.ver_flota')`. Cada pantalla exige su capacidad **y** el segundo factor (app o llave), como hasta ahora.

### Reglas del super administrador

- **Solo se nombra desde pgAdmin:** `SELECT chilito_designar_super_admin('correo');`. Recibe las 10 capacidades. Puede haber más de uno.
- Desde el panel, el super admin **da y quita las otras 9** insertando o borrando en `cuentas_usuario_user_permissions` (con actor y motivo).
- La base **impide**:
  - dar o quitar `gestionar_administradores` desde el panel;
  - que alguien cambie **sus propias** capacidades;
  - quedarse **sin ningún super admin activo**;
  - dar capacidades a cuentas **sin correo verificado**.
- **Cada alta o baja queda en `capacidad_historial`** (quién la recibió, qué capacidad, quién la dio, motivo y fecha). Ese registro no se borra nunca. Se consulta en `v_capacidad_historial`.

### Funciones para pgAdmin

```sql
SELECT chilito_designar_super_admin('rafael@dominio.com');
SELECT chilito_retirar_super_admin('otro@dominio.com');            -- si queda otro super admin
SELECT chilito_conceder_capacidad('alejandro@gmail.com', 'atender_soporte', 'Turno de soporte');
SELECT chilito_retirar_capacidad('alejandro@gmail.com', 'atender_soporte', 'Dejó el equipo');
```

Devuelven un mensaje y avisan si la cuenta aún no tiene app autenticadora ni llave de acceso.

---

## 8. Reglas que protege la base

Si algo intenta saltarse una regla, la base responde con el error **23514** y no guarda nada.

| Área | Regla |
|---|---|
| Registro | No hay cuenta sin aceptar los términos y el aviso **vigentes** |
| Cuentas | No se borran (se anonimizan) · la anonimización no se deshace · nunca `is_staff`/`is_superuser` · un buzón real, una cuenta (Gmail sin puntos ni «+») |
| Capacidades | Reglas del super admin (sección 7) · historial automático |
| Huertos | Máximo 3 activos y 1 sin equipo · el dueño no cambia · solo Yucatán · no se borran · para archivar, antes desvincular |
| Plantas | Siempre 3, creadas por la base · solo el dueño las edita · fechas no futuras · historial de etapas |
| Equipos | Alta con capacidad · identidad fija · vincular **solo con código utilizado en la misma operación** · desvincula el dueño o un admin · retirado es definitivo · IoT solo toca conexión y firmware |
| Códigos | Solo el dueño, para su huerto activo y sin equipo · 10 min · uno pendiente por huerto · se cierran una sola vez |
| Telemetría | Solo del equipo vinculado a ese huerto · rangos válidos · sin duplicados · no se modifica |
| Comandos | El dueño, o el soporte dentro de su sesión autorizada · tipos según origen · riego con planta y duración · estados solo hacia delante |
| Autodiagnóstico | Nace de su comando · resultado calculado por la base · no admite revisiones una vez cerrado |
| Soporte | Lo pide el dueño con consentimiento · 24 h · un caso activo por huerto · solo atiende quien tiene `atender_soporte` · revocar cierra la sesión al instante · cerrado es definitivo |
| Ventas | Con `gestionar_ventas` · una vigente por equipo · fecha no futura · importe recibido entre 0 y el precio · estado de pago calculado · no se borran |
| Cuidados | Planta según tipo · 7 días atrás como máximo · correcciones numeradas solo por admin · anulado no admite más |
| Legal | Publicar exige capacidad y una versión mayor · lo publicado no cambia ni se borra · decisiones solo con la versión vigente y el ámbito correcto · IP siempre recortada |
| Historiales | No se modifican ni se borran: eventos de equipo, mediciones (salvo depuración a 90 días), actuaciones, revisiones, cuidados, bitácora de consentimientos, historial de capacidades y auditoría |

**Límite honesto:** estas reglas protegen contra errores de la aplicación y contra un servicio vulnerado. No protegen contra alguien con la contraseña de `chilito_pkg_owner` que desactive los triggers a propósito.

---

## 9. Qué puede hacer cada rol

| | runtime (página) | iot (servicios) |
|---|---|---|
| Leer | Todas las tablas (Django filtra lo que muestra) | Solo huerto, plantas, equipo, telemetría, comandos, autodiagnósticos, cuidados e IA |
| Cuentas | Crear y editar perfil, contraseña, último acceso, bienvenida y solicitud de anonimización | — |
| Capacidades | Insertar y borrar (el trigger exige super admin) | — |
| Huertos y plantas | Crear y editar nombre, estado, etapas y fechas | — |
| Equipos | Alta, vincular, desvincular, retirar y rotar credencial | Conexión, última conexión y firmware |
| Telemetría | — | Insertar mediciones, actuaciones, eventos y resúmenes |
| Comandos | Crear y cambiar estado | Cambiar estado |
| Autodiagnóstico | (lo crea su comando) | Insertar revisiones y cerrar |
| Soporte, cuidados, guías, ventas, legal, privacidad | Lo que permite cada flujo | — |
| Notificaciones | Crear y marcar leída o resuelta | Crear (solo al dueño, origen dispositivo o ia) |
| Borrar | Sesiones, cuotas, correos de allauth, segundo factor, capacidades y borradores legales | Nada |

---

## 10. Funciones y vistas

| Función | Quién | Para qué |
|---|---|---|
| `chilito_vincular_dispositivo(identificador, hmac)` | runtime | Vincular cuando el ESP32 presenta su código |
| `chilito_desvincular_dispositivo(id)` | runtime | Desvincular (dueño o admin; con actor) |
| `chilito_aceptaciones_pendientes(usuario_id)` | runtime | Textos legales por aceptar al entrar |
| `chilito_documento_vigente(tipo)` | runtime | Id de la versión vigente de un tipo |
| `chilito_tiene_capacidad(usuario_id, capacidad)` | runtime, iot | ¿Tiene la capacidad? |
| `chilito_identidad_correo(correo)` | runtime | Buzón real de un correo |
| `chilito_resumir_mediciones(desde, hasta)` | owner, iot | Recalcular resúmenes por hora |
| `chilito_mantenimiento_periodico()` | **owner** | Tarea periódica (sección 11) |
| `chilito_anonimizar_cuenta(id)` | **owner** | La usa la tarea periódica |
| `chilito_designar_super_admin`, `chilito_retirar_super_admin`, `chilito_conceder_capacidad`, `chilito_retirar_capacidad` | **owner** | Administración desde pgAdmin |
| `chilito_publicar_documento_legal(tipo, versión, título, texto)` | **owner** | Carga inicial de textos legales |

| Vista | Muestra |
|---|---|
| `v_administradores` | Cada admin, sus capacidades, si es super admin, si tiene segundo factor y su último acceso |
| `v_capacidad_historial` | Historial de capacidades con correos legibles |
| `v_bitacora_consentimientos` | **Quién** (correo, «Visitante anónimo» o «Cuenta eliminada»), qué, qué versión, aceptó o rechazó, fecha (también en hora de Mérida), IP recortada y navegador |
| `v_documento_legal_vigente` | Versión vigente de cada texto |
| `v_estado_equipos` | Cada equipo: estado, conexión, huerto, dueño y última medición |

---

## 11. Tarea periódica y conservación de datos

Ejecútala **cada hora como `chilito_pkg_owner`**. En Cloud SQL se puede usar la extensión `pg_cron`; si no, un Cloud Scheduler que se conecte como owner.

```sql
SELECT chilito_mantenimiento_periodico();   -- devuelve un resumen en JSON
```

| Qué hace | Cuándo |
|---|---|
| Recalcula los resúmenes por hora | Últimas 48 h, y todo lo que va a salir del detalle |
| Borra el detalle de mediciones | Más de **90 días** (el resumen por hora se queda **para siempre**) |
| Marca códigos de vinculación como `expirado` | Pasados sus 10 minutos |
| Marca comandos sin respuesta como `expirado` | Pasados 10 minutos |
| Cierra sesiones técnicas con la autorización vencida | Pasadas las 24 h |
| Borra resúmenes de IA | Más de 30 días |
| Borra avisos leídos | Más de 180 días |
| Borra recibos de idempotencia | Más de 7 días |
| Borra cuotas y sesiones web vencidas | Al vencer |
| **Anonimiza cuentas** | 15 días después de pedirlo |
| Anonimiza mensajes de «Consíguelo» | 1 año después de atendidos o archivados |

---

## 12. Publicar los textos legales

**Primera vez (paso 4 de la instalación), desde pgAdmin.** Pega el texto vigente de cada documento, por ejemplo el que hoy está en `frontend/legales/`, y publícalo:

```sql
SELECT chilito_publicar_documento_legal('terminos', '1.0', 'Términos y condiciones', $texto$
…pega aquí el texto completo…
$texto$);
SELECT chilito_publicar_documento_legal('aviso_privacidad', '1.0', 'Aviso de privacidad', $texto$ … $texto$);
SELECT chilito_publicar_documento_legal('politica_cookies', '1.0', 'Política de cookies', $texto$ … $texto$);
```

**Después, desde el panel** (`gestionar_legales`):

1. Crear un borrador: `INSERT INTO documento_legal(tipo, version, titulo, contenido, contenido_sha256, creado_por_id)` con `contenido_sha256` en cualquier valor de 64 caracteres (la base lo recalcula).
2. Editarlo todas las veces que haga falta.
3. Publicarlo con `UPDATE … SET estado='publicada'`.

Al publicar, todas las cuentas reciben un aviso y, si es de términos o del aviso de privacidad, deberán aceptarlo al entrar.

Las versiones usan el formato `1.0`, `1.1` o `2.0.1`, y cada una debe ser mayor que la vigente.

---

## 13. Consultas útiles en pgAdmin

```sql
-- Administradores y capacidades
SELECT * FROM v_administradores ORDER BY email;

-- Quién dio o quitó qué capacidad
SELECT * FROM v_capacidad_historial ORDER BY realizada_en DESC LIMIT 50;

-- Bitácora de consentimientos (lo más reciente primero)
SELECT registrada_en_merida, cuenta, que, version_documento, decision, ip_recortada, navegador
FROM v_bitacora_consentimientos ORDER BY registrada_en DESC LIMIT 100;

-- Quién aceptó una versión concreta de los términos
SELECT cuenta, registrada_en_merida FROM v_bitacora_consentimientos
WHERE que='Términos y condiciones' AND version_documento='1.0';

-- Equipos y su estado
SELECT * FROM v_estado_equipos ORDER BY identificador;

-- Huertos de cada cuenta
SELECT u.email, h.id, h.nombre, h.estado, d.identificador
FROM huerto h JOIN cuentas_usuario u ON u.id=h.propietario_id
LEFT JOIN dispositivo d ON d.huerto_id=h.id ORDER BY u.email;

-- Historial de un equipo
SELECT ocurrido_en, tipo, huerto_id, detalle FROM dispositivo_evento
WHERE dispositivo_id=(SELECT id FROM dispositivo WHERE identificador='ESP32-A1B2') ORDER BY ocurrido_en;

-- Casos de soporte activos
SELECT folio, estado, incidente, creado_en, autorizacion_vence_en FROM soporte_caso
WHERE estado IN ('abierto','en_atencion') ORDER BY creado_en;

-- Últimas acciones auditadas
SELECT a.creada_en, u.email, a.accion, a.entidad, a.entidad_id, a.resultado
FROM auditoria a LEFT JOIN cuentas_usuario u ON u.id=a.actor_id ORDER BY a.creada_en DESC LIMIT 50;
```

**Dar de alta un ESP32 desde pgAdmin** (por ejemplo, para el prototipo):

```sql
INSERT INTO dispositivo(identificador, mac, credencial_hash)
VALUES ('ESP32-A1B2', 'AA:BB:CC:DD:EE:FF', '<hash PBKDF2 de su credencial MQTT>');
```

---

## 14. Qué cambió respecto a la v1

De 43 a **46 tablas**: 5 eliminadas, 5 fusionadas en 2 y 13 nuevas.

| Eliminadas | Por qué |
|---|---|
| `cuentas_confirmacionregistrolocal` | La sustituye la regla de aceptación obligatoria |
| `huerto_membresia` | El huerto tiene dueño directo |
| `datos_asignacionmantenimiento` | La capacidad aplica a todos los huertos y todo se audita |
| `datos_validacionversion`, `datos_revisionconocimiento` | Sin pantalla ni relación con el flujo |

| Fusionadas | En |
|---|---|
| `huerto_aviso` + `huerto_avisoleido` | `notificacion` |
| `datos_permisosoporte` + `datos_resolucionsoporte` | `soporte_caso` |
| `privacidad_eventoprivacidad` | `auditoria` |

| Renombradas y mejoradas | Cambio |
|---|---|
| `huerto_huerto` → `huerto` | Dueño, estado, límites, solo Mérida |
| `huerto_zona` → `huerto_planta` | Nombre, siembra y etapa |
| `datos_dispositivo` → `dispositivo` | Inventario, credencial, estado y conexión |
| `datos_codigovinculacion` → `codigo_vinculacion` | Lo genera el usuario y lo usa el ESP32 |
| `datos_solicitud` → `comando` | Estados reales; riego por planta |
| `datos_mantenimiento` (+ revisión) → `cuidado` (+ `cuidado_revision`) | Por planta, chiles cosechados, fecha real |
| `datos_casosoporte` / `datos_sesiontecnica` → `soporte_caso` / `soporte_sesion` | Sin token, con estados y admin asignado |
| `datos_auditoria` → `auditoria` | Genérica (antes tenía 12 columnas de referencia) |
| `privacidad_documentoversion` → `documento_legal` | Texto completo en la base, borrador o publicada |
| `privacidad_decisionprivacidad` → `privacidad_decision` | IP recortada, navegador y cuenta |
| `datos_avisocorreo` → `correo_pendiente` | Sin el tipo `token_solicitado` |

**Nuevas:** `huerto_planta_etapa`, `dispositivo_evento`, `medicion`, `medicion_planta`, `resumen_hora_huerto`, `resumen_hora_planta`, `actuacion`, `autodiagnostico`, `autodiagnostico_revision`, `notificacion`, `ia_resumen`, `venta`, `capacidad_historial`.

Todos los valores están ahora **en español** (`regar` en lugar de `water`, `rellenar_deposito` en lugar de `refill`).

---

## 15. Instrucciones para adaptar Django

Para quien ejecute el plan. **La base manda; Django se adapta a ella.**

1. **Modelos.** Reescribe los modelos de las apps `cuentas`, `huerto`, `datos`, `privacidad` y `web` para que coincidan **exactamente** con las tablas: mismo `db_table`, columnas, tipos y restricciones. Pon en cada `Meta` `default_permissions = ()`. En el modelo `Usuario`, declara `permissions` con las 10 capacidades (mismo `codename` y nombre que en la sección 15 del script).
2. **Migraciones nuevas.** Borra las migraciones antiguas de esas apps y genera una `0001_initial` por app. Una migración más (`web/0002_reglas_v2`) aplica con `RunSQL`, copiado del script, lo que los modelos no expresan: funciones, CHECK, índices parciales, triggers, vistas, datos iniciales y privilegios.
3. **Equivalencia.** Una base creada con `migrate` debe pasar `sql/pruebas/pruebas_v2.py` y `prueba_depuracion.py` y coincidir con la del script (salvo nombres automáticos de FK e índices). **Nunca `migrate --fake`.** Si `makemigrations --check` detecta diferencias, se corrige el modelo, no la base.
4. **Columnas generadas.** `folio` en `soporte_caso` y en `consulta_producto` lo calcula la base. En Django usa `GeneratedField` (Django 5+) o déjalo fuera del modelo y léelo con `.extra()` o `RawSQL`.
5. **Guardar solo lo que cambia.** El rol de la página solo puede actualizar algunas columnas. Usa siempre `save(update_fields=[...])` o `QuerySet.update(...)`. Un `save()` completo falla con `permission denied`.
6. **Actor** en cada transacción que escribe (sección 6). Recomendado: `ATOMIC_REQUESTS = True` y un middleware que ejecute el `set_config` al inicio de la petición si hay sesión.
7. **Errores 23514.** Tradúcelos a mensajes claros en la interfaz. El texto del error explica la causa.
8. **Registro:** inserta las dos decisiones legales en la misma transacción que la cuenta (sección 5.2).
9. **Inicio de sesión:** consulta `chilito_aceptaciones_pendientes` y bloquea hasta aceptar.
10. **Código de vinculación:** genéralo con `secrets`, guarda `hmac.new(SECRETO, codigo, sha256).hexdigest()` y muéstralo una sola vez. Normaliza el código antes de calcular el HMAC (mayúsculas, sin guiones ni espacios), igual al generarlo que al recibirlo del ESP32.
11. **Pantallas que dejan de existir o cambian:**
    - «Vinculación de huertos» del admin → **«Inventario de equipos»** (`gestionar_dispositivos`);
    - «Equipos y ventas» → **«Ventas»**, que ahora sí se guardan (`gestionar_ventas`);
    - la consola remota pierde «Solicitar token» y «Pegar token» y gana **«Atender»** y **«Conectar»**;
    - aparecen **«Textos legales»**, **«Bitácora de consentimientos»** y **«Administradores»**.
12. **Comando de retirar factores** (`retirar_factores`): sigue igual, pero escribe su auditoría en `auditoria` con la acción `retirar_segundo_factor`.

**Catálogo sugerido de acciones de auditoría:** `iniciar_sesion`, `cerrar_sesion`, `cambiar_contrasena`, `retirar_segundo_factor`, `consultar_mis_datos`, `rectificar_perfil` (detalle: `{"campo":"alias"}`, nunca el valor), `crear_huerto`, `archivar_huerto`, `generar_codigo`, `vincular_dispositivo`, `desvincular_dispositivo`, `registrar_cuidado`, `corregir_cuidado`, `crear_comando`, `abrir_caso`, `atender_caso`, `conectar_sesion`, `resolver_caso`, `publicar_documento`, `publicar_guia`, `registrar_venta`, `anonimizar_cuenta`.

---

## 16. Cómo se probó

El 14 de noviembre de 2026, en un **PostgreSQL 17.11** temporal, con los tres roles reales:

| Prueba | Resultado |
|---|---|
| Instalación del script en una base vacía | Correcta: 46 tablas, 5 vistas, 63 funciones, 49 triggers, 10 capacidades, 9 guías |
| `pruebas_v2.py`: flujos completos (registro, legal, capacidades, huertos, plantas, inventario, vinculación, telemetría, comandos, autodiagnóstico, soporte con revocación, cuidados, guías, publicación legal y reaceptación, cookies, ventas con pagos, desvinculación, anonimización y auditoría), más intentos de saltarse cada regla | **149 de 149** correctas |
| `prueba_depuracion.py`: una medición de hace 100 días se resume por hora y se borra el detalle | Correcta |

Para repetirlas en una base **de pruebas** recién instalada (su nombre debe contener «prueba» o «test»: las pruebas escriben datos):

```
CHILITO_PRUEBAS_DB=chilito_pruebas CHILITO_PRUEBAS_HOST=localhost CHILITO_PRUEBAS_PUERTO=5432 \
CHILITO_PRUEBAS_CLAVE_OWNER=… CHILITO_PRUEBAS_CLAVE_RUNTIME=… CHILITO_PRUEBAS_CLAVE_IOT=… python3 pruebas_v2.py
```

---

## 17. Pendiente para la fase IoT

La base ya está preparada. Faltan las piezas que no son de la base:

- receptor MQTT (Mosquitto con TLS, autenticación y ACL por equipo) que escriba con `chilito_pkg_iot`;
- publicación de comandos al ESP32 y actualización de su estado;
- endpoint HTTPS de vinculación que verifique la credencial del equipo y llame a `chilito_vincular_dispositivo`;
- servicio de IA en Google Cloud que escriba en `ia_resumen` y `notificacion`;
- firmware del ESP32: modo Access Point, portal local, NVS y botón de reinicio de configuración.

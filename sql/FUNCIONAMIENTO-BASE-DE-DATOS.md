# El Chilito: cómo funciona la base de datos y la página

Guía de la base de datos **tal como queda con todos los parches aplicados**, y del recorrido de la persona usuaria y de la administradora por la página. Revisada contra el código el 14 de noviembre de 2026.

---

## Índice

1. [Qué archivo usar a partir de ahora](#1-qué-archivo-usar-a-partir-de-ahora)
2. [Los dos usuarios de la base: `chilito_pkg_owner` y `chilito_pkg_runtime`](#2-los-dos-usuarios-de-la-base-chilito_pkg_owner-y-chilito_pkg_runtime)
3. [Instalar desde cero](#3-instalar-desde-cero)
4. [Cómo está armado todo: página, servidor y base](#4-cómo-está-armado-todo-página-servidor-y-base)
5. [Las 43 tablas, por área](#5-las-43-tablas-por-área)
6. [Flujo de una persona SIN cuenta](#6-flujo-de-una-persona-sin-cuenta)
7. [Crear una cuenta](#7-crear-una-cuenta)
8. [Iniciar sesión](#8-iniciar-sesión)
9. [Seguridad: app autenticadora, llaves de acceso y códigos de recuperación](#9-seguridad-app-autenticadora-llaves-de-acceso-y-códigos-de-recuperación)
10. [Recuperar o cambiar la contraseña](#10-recuperar-o-cambiar-la-contraseña)
11. [Lo que puede hacer una persona con sesión](#11-lo-que-puede-hacer-una-persona-con-sesión)
12. [Administración: cómo se crea un administrador y qué puede hacer](#12-administración-cómo-se-crea-un-administrador-y-qué-puede-hacer)
13. [Cookies y sesión: qué se guarda, dónde y cuánto dura](#13-cookies-y-sesión-qué-se-guarda-dónde-y-cuánto-dura)
14. [Correos que envía el sistema](#14-correos-que-envía-el-sistema)
15. [Reglas que protege la propia base (triggers)](#15-reglas-que-protege-la-propia-base-triggers)
16. [Qué puede y qué no puede hacer la aplicación en la base](#16-qué-puede-y-qué-no-puede-hacer-la-aplicación-en-la-base)
17. [Datos con los que nace la base](#17-datos-con-los-que-nace-la-base)
18. [Cómo se comprobó el script nuevo](#18-cómo-se-comprobó-el-script-nuevo)
19. [Cómo trabajar con la base de aquí en adelante](#19-cómo-trabajar-con-la-base-de-aquí-en-adelante)
20. [Consultas útiles](#20-consultas-útiles)
21. [Cosas que hoy existen solo a medias](#21-cosas-que-hoy-existen-solo-a-medias)

---

## 1. Qué archivo usar a partir de ahora

| Archivo | Para qué sirve |
|---|---|
| **`sql/el_chilito_base_completa.sql`** | **El script único.** Instala la base completa en una base vacía, de una vez y sin parches. Incluye tablas, reglas, datos iniciales y privilegios. |
| **`sql/designar_administrador.sql`** | Convierte una cuenta ya registrada en administradora, o le quita capacidades. Sustituye a `preparar_administrador_principal.sql` y a `asignar_capacidad.sql`. |
| `sql/FUNCIONAMIENTO-BASE-DE-DATOS.md` | Este documento. |
| `sql/privilegios.sql` | Copia de los privilegios. El script único ya los incluye. |
| `sql/instalacion/` | Archivos anteriores: `01`, `02`, `03`, los parches `01` a `08` y utilidades. **Para una base nueva ya no hacen falta.** |

Utilidades de `sql/instalacion/` que siguen siendo válidas con la base nueva:

- `09_registrar_equipo.sql`: da de alta un huerto y su dispositivo. Es la única forma de crear huertos; la página no tiene esa función.
- `07_consultar_cookies.sql`: lista las decisiones de cookies.
- `04_inspeccion.sql`: muestra la estructura.
- `05_prueba_triggers.sql`: prueba 19 reglas y lo deshace todo al final.

### Estado de la base oficial que ya tienes

La base `chilito_integracion_sinteticos` de tu equipo tiene **60 de las 61 migraciones**. Le falta el **parche 08**, que retira las capacidades antiguas `ver_gobernanza` y `gestionar_cambios`. Se comprobó hoy con una consulta de solo lectura, sin cambiar nada.

- Si **instalas una base nueva** con el script único, nace con las 61 y sin esas dos capacidades viejas.
- Si **sigues usando la base oficial actual**, conserva sus datos y le falta solo ese paso. Aplica antes el `SELECT` de la fase 0 de `PLAN-RETIRO-GOBERNANZA-Y-DESPLIEGUES.md` y después `parches/08_retiro_capacidades_gobernanza.sql`.

> El script único es para bases **vacías**. Se detiene solo si encuentra tablas, para no tocar datos existentes.

---

## 2. Los dos usuarios de la base: `chilito_pkg_owner` y `chilito_pkg_runtime`

PostgreSQL tiene «roles», que son los usuarios con los que alguien se conecta. El Chilito usa dos. Los dos nombres empiezan por `chilito_pkg_`; lo que cambia es el final, que indica su papel:

- **owner** significa *propietario*.
- **runtime** significa *en ejecución*: el usuario con el que trabaja la página mientras está encendida.

| | `chilito_pkg_owner` (propietario) | `chilito_pkg_runtime` (la aplicación) |
|---|---|---|
| ¿Quién lo usa? | **Tú**, desde pgAdmin, para instalar y administrar | **La página (Django)**. Está en el `.env` como `CHILITO_DB_USER` |
| ¿Es dueño de la base? | Sí. Es dueño de la base y de todas sus tablas | No. Solo tiene los permisos que se le dan uno a uno |
| ¿Puede crear o borrar tablas? | Sí | **No** |
| ¿Puede borrar historiales? | Los triggers se lo impiden igual que a la app (salvo que los desactive a propósito) | **No**: ni tiene permiso `DELETE` ni los triggers lo dejan |
| ¿Puede dar capacidades de administrador? | **Sí**, con `designar_administrador.sql` | **No**: solo puede *leer* los permisos |
| ¿Puede crear huertos y dispositivos? | **Sí**, con `09_registrar_equipo.sql` | **No**: huertos y dispositivos son de solo lectura para la app |
| ¿Puede crear membresías a mano? | **Sí**: el trigger de vinculación lo exime | No: solo con un código de vinculación consumido |
| ¿Puede crear cuentas `staff`, superusuario o inactivas? | Sí | **No**: lo bloquea un trigger |
| ¿Superusuario de PostgreSQL? | No | No |

**Por qué hay dos.** Si alguien encontrara un fallo en la página y lograra hacerle ejecutar SQL, solo tendría los permisos de `chilito_pkg_runtime`. No podría borrar tablas, darse permisos de administrador, crear huertos ni borrar el historial. Es el principio de **mínimo privilegio**.

Existe además el usuario **`postgres`**, administrador del servidor. Solo se usa para crear los dos roles y la base (pasos 1 y 2 de la instalación).

> En tu equipo, `chilito_pkg_owner` tiene además permiso para **crear bases** (`CREATEDB`). Las pruebas automáticas lo usan para crear y borrar la base temporal `test_chilito_integracion_sinteticos`. La instalación descrita en el script lo crea **sin** ese permiso. Si quieres ejecutar las pruebas en otra máquina, concédeselo con `ALTER ROLE chilito_pkg_owner CREATEDB;` como `postgres`.

---

## 3. Instalar desde cero

Las instrucciones también están al principio de `el_chilito_base_completa.sql`.

**Paso 1. Roles** (como `postgres`, en la base `postgres`):

```sql
CREATE ROLE chilito_pkg_owner   LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE chilito_pkg_runtime SET search_path = pg_catalog, public;
```

Después ponles contraseña en pgAdmin: **Login/Group Roles › (rol) › Definition**. Las contraseñas nunca van en un archivo `.sql`.

**Paso 2. Base** (como `postgres`). Ejecuta esta línea **sola**, porque `CREATE DATABASE` no admite ir acompañada de otras sentencias:

```sql
CREATE DATABASE chilito_integracion_sinteticos OWNER chilito_pkg_owner;
```

**Paso 3. Esquema completo.** Registra en pgAdmin una conexión con el usuario `chilito_pkg_owner` a la base `chilito_integracion_sinteticos`. Abre **Query Tool**, carga `sql/el_chilito_base_completa.sql` y ejecútalo completo. Corre en una sola transacción: si falla, pulsa **Rollback** y no queda nada a medias.

**Paso 4. Configurar la página** (`.env`, que nunca se comparte):

```
CHILITO_DB_NAME=chilito_integracion_sinteticos
CHILITO_DB_USER=chilito_pkg_runtime
CHILITO_DB_PASSWORD=<la contraseña de chilito_pkg_runtime>
```

**Paso 5. Primer administrador.** La persona se registra en la página y luego ejecutas `sql/designar_administrador.sql` con su correo (sección 12).

**Paso 6. Huertos.** Por cada equipo físico, ejecuta `sql/instalacion/09_registrar_equipo.sql`. Crea el huerto, sus 3 plantas y su dispositivo. Después se vincula a la cuenta de la persona con un código (sección 12.5).

---

## 4. Cómo está armado todo: página, servidor y base

```
 Navegador (frontend/)                Servidor Django (backend/)                     PostgreSQL
 ─────────────────────                ──────────────────────────                     ──────────
 index.html + modelos/ vistas/        config/  urls, ajustes, seguridad              chilito_integracion_sinteticos
 controladores/ (JavaScript)  ──────► web/     contrato JSON, sesión, cuotas  ──────► 43 tablas
                                      cuentas/ registro, acceso, 2FA (allauth)        25 funciones, 43 triggers
 Cookies: sessionid, csrftoken,       huerto/  huertos, zonas, avisos                 (conecta como
 chilito_preferencia,                 datos/   operación, soporte, vinculación,        chilito_pkg_runtime)
 chilito_estadistica                           guías, buzón, auditoría
                                      privacidad/ textos legales, cookies, perfil
```

- **El navegador nunca habla con la base.** Solo llama a direcciones `/api/...` y `/_allauth/...` del mismo servidor.
- **Django decide todo**: quién eres, qué puedes ver y qué puedes cambiar. El JavaScript solo muestra lo que el servidor permite.
- **La base es la segunda barrera.** Aunque la aplicación tuviera un error, los triggers, las restricciones y los privilegios impiden guardar algo incoherente o borrar historiales.

### Qué pasa en cada petición

1. El navegador envía la cookie `sessionid` y, si escribe algo, la cabecera `X-CSRFToken` (copiada de la cookie `csrftoken`) y una `Idempotency-Key` única.
2. Django busca la sesión en `django_session`. Comprueba que no haya vencido: 8 horas como máximo, 30 minutos sin actividad para usuarios y 15 para administradores.
3. Comprueba que la cuenta esté **activa** y con el **correo verificado**. Si la pantalla es de administración, comprueba también la **capacidad** y el **segundo factor**.
4. En las escrituras revisa la **cuota**: 60 por minuto, o 15 por minuto en soporte técnico. Si la misma `Idempotency-Key` ya se usó, devuelve el resultado guardado en `web_idempotencia` en vez de repetir la operación.
5. Ejecuta la operación en una **transacción**. Si algo falla, no se guarda nada.
6. Los **triggers** revisan cada fila antes de aceptarla.

---

## 5. Las 43 tablas, por área

### Django (internas)

| Tabla | Qué guarda |
|---|---|
| `django_migrations` | Qué migraciones están aplicadas (61). Django la revisa al arrancar |
| `django_content_type` | Una fila por modelo (39). Los permisos cuelgan de aquí |
| `auth_permission` | 162 permisos, entre ellos las **6 capacidades de administración** |
| `auth_group`, `auth_group_permissions`, `cuentas_usuario_groups` | Grupos de permisos. Existen, pero **hoy no se usan** |
| `django_session` | **Sesiones abiertas.** La cookie `sessionid` es la clave |

### Cuentas

| Tabla | Qué guarda |
|---|---|
| `cuentas_usuario` | La cuenta: correo, contraseña (**solo el resumen**, nunca en claro), nombre, apellidos, alias, fecha de alta, último acceso y si ya atendió la bienvenida |
| `cuentas_usuario_user_permissions` | **Capacidades de cada cuenta.** Si tiene alguna, la cuenta es administradora |
| `account_emailaddress` | El correo de cada cuenta y si está **verificado** |
| `account_emailconfirmation` | Confirmaciones por enlace. Queda **vacía**, porque la página verifica por código |
| `mfa_authenticator` | Segundo factor: `totp` (app autenticadora), `recovery_codes` (códigos de recuperación) y `webauthn` (llaves de acceso). Los secretos van **cifrados** |
| `cuentas_cuotas_acceso` | Caché de Django: contadores de límites (intentos de acceso, formulario, cookies…) y marcas temporales |
| `cuentas_confirmacionregistrolocal` | Constancia técnica de que, al registrarse, la persona marcó las dos casillas |

### Huertos

| Tabla | Qué guarda |
|---|---|
| `huerto_huerto` | Cada huerto: clave, nombre y zona horaria. Al crearlo, un trigger crea sus 3 plantas |
| `huerto_zona` | Las plantas 1, 2 y 3 de cada huerto («Planta 1», chile habanero). No se borran |
| `huerto_membresia` | Qué cuenta tiene qué huerto. **Una sola activa por cuenta.** Solo nace al consumir un código de vinculación |
| `huerto_aviso`, `huerto_avisoleido` | Avisos del huerto y cuáles leyó cada persona |

### Operación

| Tabla | Qué guarda |
|---|---|
| `datos_dispositivo` | El equipo (ESP32) de cada huerto. Uno por huerto |
| `datos_mantenimiento` | Cuidados registrados (depósito, sustrato, germinación, cosecha, inspección). **Nunca cambian** |
| `datos_revisionmantenimiento` | Correcciones y anulaciones de un cuidado, como filas nuevas numeradas |
| `datos_asignacionmantenimiento` | Qué huertos puede corregir cada administradora |
| `datos_casosoporte` | Casos de soporte que abre la persona usuaria |
| `datos_permisosoporte` | Autorización de soporte de hasta 24 h. Del token solo se guarda un verificador HMAC |
| `datos_sesiontecnica` | Sesión técnica que abre la administradora con el token |
| `datos_resolucionsoporte` | Cierre del caso: resultado y nota |
| `datos_solicitud` | Solicitudes de riego o de lámpara. **Se guardan, no se ejecutan** |
| `datos_codigovinculacion` | Códigos de vinculación. Solo se guarda su resumen |
| `datos_guiacuidado` | Guías de cuidado (preguntas frecuentes) |
| `datos_consultaproducto` | Mensajes del formulario «Consíguelo» |
| `datos_avisocorreo` | Cola de avisos automáticos por correo y su estado |
| `datos_auditoria` | Quién hizo qué y sobre qué registro, **sin texto libre ni secretos** |
| `datos_validacionversion`, `datos_revisionconocimiento` | Registro administrativo de versiones y notas. **Sin pantalla hoy** |

### Privacidad

| Tabla | Qué guarda |
|---|---|
| `privacidad_documentoversion` | Versiones registradas del aviso de privacidad, los términos y la política de cookies, con su huella SHA-256 |
| `privacidad_finalidadopcional` | Finalidades opcionales. Hoy solo «estadísticas internas de navegación» |
| `privacidad_sujetoprivacidad` | Identificador seudónimo de una **cuenta** o de un **navegador** |
| `privacidad_decisionprivacidad` | Historial de decisiones: aceptar términos, leer el aviso y decidir sobre cookies |
| `privacidad_preferenciafinalidad` | Decisión **vigente** de cada sujeto, que apunta a la última del historial |
| `privacidad_eventoprivacidad` | Eventos: decisión, oposición, acceso a «Mis datos» y rectificación (solo qué campo, nunca el valor) |
| `privacidad_conteonavegacion` | Visitas por día y sección. Solo totales, sin identidad |

### Otros

| Tabla | Qué guarda |
|---|---|
| `web_idempotencia` | Recibos de escrituras para que un reintento no repita la operación. No guarda tokens, contraseñas ni códigos |

---

## 6. Flujo de una persona SIN cuenta

Quien entra sin sesión ve la **portada pública** y puede hacer lo siguiente.

### 6.1 Leer la portada

La portada tiene cinco secciones, accesibles desde el menú:

1. **Inicio**: «Tu huerto de habanero, dentro de casa».
2. **El proyecto**: «Un pequeño huerto. Una nueva conexión».
3. **Prototipo**: «Conoce el prototipo».
4. **Consíguelo**: «Sé de los primeros en tener tu Chilito», con el botón **«Quiero más información»**.
5. **Cómo funciona**: riego por tiempos, 5 sensores, asistente de IA previsto (aún no conectado) e iluminación LED, con el botón **«Iniciar sesión en el panel»**.

**En la base:** nada, salvo que el navegador haya **aceptado** las estadísticas (6.4).

### 6.2 Leer los textos legales

Desde el pie de página puede abrir el **Aviso de privacidad** (`#privacidad`), los **Términos** (`#terminos`) y la **Política de cookies** (`#cookies`).

- El servidor lee el texto vigente de cada documento de la tabla `documento_legal`, lo limpia (solo deja texto, títulos, listas y enlaces seguros) y lo devuelve.
- Los textos legales viven en `documento_legal`; se redactan y publican desde Administración → Textos legales. No hay archivos HTML que editar.
- **En la base:** solo se **lee** `privacidad_documentoversion`.

### 6.3 Mandar un mensaje desde «Consíguelo»

1. Pulsa **«Quiero más información»** y se abre la ventana **«Cuéntanos qué quieres saber»**.
2. Escribe nombre (opcional), **correo** y **mensaje** (hasta 2000 caracteres) y pulsa **«Enviar mensaje»**.
3. El servidor comprueba:
   - el **límite de 5 mensajes por hora por dirección IP**, que se cuenta en `cuentas_cuotas_acceso` y se gasta aunque el mensaje no sea válido;
   - el **campo trampa** «Sitio web», invisible para personas. Si viene lleno, es un robot: se responde «recibido» y no se guarda nada;
   - que el correo sea válido y el mensaje no esté vacío.
4. **En la base, en una sola transacción:**
   - una fila en `datos_consultaproducto` con estado `nueva` y una **huella** de correo + mensaje. Si llega el mismo correo con el mismo mensaje en menos de 10 minutos, **no se duplica**;
   - una fila en `datos_avisocorreo` de tipo `consulta_nueva`.
5. Al confirmar, se envía un correo a la cuenta de soporte (`CHILITO_CONTACTO_SOPORTE`) con el asunto «[El Chilito] Pregunta sobre el producto». Su «Responder a» es el correo de la persona. Si el envío falla, **el mensaje no se pierde**: el aviso queda `fallido` y se reintenta (sección 14).
6. La persona ve «Recibimos tu mensaje. Te responderemos a tu correo».
7. El mensaje aparece en **«Solicitudes del producto»** del panel de administración (12.4).

### 6.4 Decidir sobre las cookies

La primera vez aparece **«Tu privacidad y las cookies»** con tres opciones: **aceptar**, **rechazar** o **configurar**. Cerrar la ventana **no** cuenta como aceptar. El detalle completo está en la sección 13.

### 6.5 Ir a «Iniciar sesión», «Crear cuenta» o «Recuperar contraseña»

Son las pantallas `#acceso`, `#registro` y `#recuperar` (secciones 7, 8 y 10).

### 6.6 Lo que NO puede hacer

Si intenta abrir una pantalla privada (`#huerto`, `#mantenimiento`, `#admin/...`), la página consulta al servidor. Como no hay sesión, lo lleva a **`#acceso`** con el mensaje «Inicia sesión para continuar».

---

## 7. Crear una cuenta

Pantalla **`#registro`**. Solo aparece si el servidor lo permite (`CHILITO_REGISTRATION_ENABLED`: activado en local y desactivado por defecto en producción).

1. **Datos.** La persona escribe:
   - **correo**;
   - **contraseña**: entre 15 y 256 caracteres, que no sea común, ni solo números, ni parecida al correo;
   - **confirmación** de la contraseña;
   - marca **«Acepto los términos»** y **«He leído el aviso de privacidad»**. Las dos casillas son obligatorias.
2. **Comprobaciones.** Si el envío de correo no está disponible, responde «correo no disponible». Si el correo ya existe, incluidas sus variantes de Gmail, **no lo revela**: sigue el mismo camino que una cuenta nueva.
3. **En la base, en una sola transacción:**
   - `cuentas_usuario`: la cuenta, activa y con la contraseña como resumen;
   - `account_emailaddress`: el correo con `verified = false`;
   - `cuentas_confirmacionregistrolocal`: la constancia de las casillas;
   - `privacidad_sujetoprivacidad` (ámbito `cuenta`) y dos filas en `privacidad_decisionprivacidad`: **aceptación de términos** (versión vigente) y **lectura del aviso** (versión vigente). Cada una genera una fila en `privacidad_eventoprivacidad`.
4. **Código por correo.** Llega un correo con un **código de 6 dígitos**. Vale **10 minutos** y admite **3 intentos**; se puede reenviar tras 60 segundos, hasta 5 veces. El código se guarda **en la sesión del servidor** (`django_session`), no en una tabla aparte.
5. **Verificar** (`#verificar`). La persona escribe el código y entonces:
   - `account_emailaddress.verified` pasa a `true`;
   - **queda con la sesión iniciada directamente**, sin pedirle otro código.
6. **Bienvenida.** La primera vez que entra a su huerto aparece **«Te damos la bienvenida»**. Puede escribir alias, nombre y apellidos o pulsar «Ahora no». En los dos casos se guarda `cuentas_usuario.bienvenida_atendida_en` y no vuelve a salir. Si escribió algo, también se guarda un evento de rectificación con el **nombre del campo**, nunca su valor.

> **Cuentas duplicadas.** La función `chilito_identidad_correo` impide dos cuentas para el mismo buzón. En Gmail, `Juan.Perez+huerto@googlemail.com` y `juanperez@gmail.com` son la misma cuenta.

---

## 8. Iniciar sesión

Pantalla **`#acceso`**.

### 8.1 Primer paso: correo y contraseña

1. La persona escribe correo y contraseña.
2. Hay límites: 30 intentos por minuto por IP, 10 fallos por minuto por IP y **5 fallos cada 5 minutos por cuenta**. Se cuentan en `cuentas_cuotas_acceso`. Si se pasan, responde «Demasiados intentos».
3. Si la contraseña es incorrecta, responde «credenciales no válidas» sin decir si el correo existe.
4. Si el correo **aún no está verificado**, la lleva a `#verificar` para terminar el registro.

### 8.2 Segundo paso (`#segundo-paso`, «Confirma tu acceso»)

Siempre hay un segundo paso. Depende de lo que tenga activado la cuenta.

**A) Sin app autenticadora ni llave de acceso** (la situación por defecto):

1. Le llega un correo con un **código de 6 dígitos**.
2. La pantalla dice «Código de 6 dígitos. Te lo enviamos por correo. Vence en 5 minutos».
3. Escribe el código y pulsa **«Continuar»**. Tiene **3 intentos** y el código vale **5 minutos**.
4. Si es correcto, entra. Si se equivoca, ve «El código no es válido». Si el proceso vence, ve «El proceso venció. Inicia sesión de nuevo».

**B) Con app autenticadora o llave de acceso:**

1. **No llega código por correo.**
2. La pantalla pide «Código de tu app o de recuperación». Puede escribir:
   - el código de 6 dígitos de su app autenticadora, o
   - uno de sus **códigos de recuperación** (cada uno sirve una sola vez).
3. Si tiene una llave registrada y el navegador la admite, aparece el botón **«Usar llave de acceso»**. El navegador pide huella, rostro o PIN del dispositivo; **ese dato nunca sale del dispositivo**.
4. Si no tiene ni la app, ni la llave, ni los códigos, usa el enlace **«No tengo mi app ni mis códigos»** (sección 9.5).

En los dos casos puede pulsar **«Cancelar»** para volver a `#acceso`.

### 8.3 Al entrar

- Django crea la sesión en `django_session`, guarda la hora de inicio y de última actividad y actualiza `cuentas_usuario.last_login`.
- **Persona usuaria:** va a `#huerto`.
- **Administradora:** va a su primer panel permitido. Si **no** tiene app ni llave, va a `#cuenta/seguridad` con el aviso «Activa un método para usar el panel».
- La página vuelve a consultar la decisión de cookies, por si con la cuenta cambia la que aplica.

### 8.4 Cuánto dura la sesión

| Regla | Valor |
|---|---|
| Duración máxima desde que entró | **8 horas** |
| Sin actividad, persona usuaria | **30 minutos** |
| Sin actividad, administradora | **15 minutos** |
| Al cerrar el navegador | La cookie se borra |

Las consultas automáticas en segundo plano, como el buzón que se actualiza cada 30 segundos, **no cuentan** como actividad. Al vencer, la página muestra «Tu sesión ha vencido. Inicia sesión de nuevo» y cierra cualquier sesión técnica de soporte abierta.

### 8.5 Cerrar sesión

Se borra la sesión de `django_session` y se cierran sus sesiones técnicas abiertas (`motivo_cierre = 'logout'`). La página vuelve a `#acceso`.

---

## 9. Seguridad: app autenticadora, llaves de acceso y códigos de recuperación

Pantalla **`#cuenta/seguridad`** (Mi cuenta › Seguridad). Tiene cuatro tarjetas.

### 9.1 «Código por correo»

Es informativa:

- Sin métodos más fuertes dice «**Activo**: te enviamos un código cada vez que entras con tu contraseña».
- Con app o llave dice «**Inactivo**: ya confirmas tu acceso con un método más fuerte».

### 9.2 «App autenticadora» (TOTP: Google Authenticator, Microsoft Authenticator, etc.)

1. Pulsa **«Activar»**. Si hace tiempo que confirmó su identidad, aparece **«Confirma tu contraseña»** y la escribe.
2. Aparecen un **código QR** y la **clave manual**. El secreto vive solo en la sesión del servidor hasta que se confirma; el QR lo genera el servidor.
3. Escanea el QR con la app, escribe el código de 6 dígitos que muestra y pulsa **«Confirmar»**.
4. **En la base:** una fila en `mfa_authenticator` con `type = 'totp'` y el secreto **cifrado**.
5. Si es su primer método, se generan **10 códigos de recuperación** (`type = 'recovery_codes'`) y **se muestran una sola vez**: «Guárdalos ahora: no se volverán a mostrar».
6. Desde ese momento ya no recibe código por correo al entrar; usa la app.
7. **«Desactivar»** (también pide la contraseña si hace falta) borra la fila de TOTP.

### 9.3 «Llaves de acceso» (WebAuthn / passkeys)

1. Escribe un nombre, por ejemplo «Teléfono personal», y pulsa **«Agregar llave»**.
2. El navegador pide huella, rostro o PIN. **El PIN y la biometría nunca salen del dispositivo**; el servidor solo guarda la parte pública de la credencial.
3. **En la base:** una fila en `mfa_authenticator` con `type = 'webauthn'`. Puede haber varias llaves.
4. Si era su primer método, también se generan y se muestran los códigos de recuperación.
5. Cada llave tiene un botón **«Quitar»**.

> Las llaves sirven como **segundo paso**, no para entrar sin contraseña: el acceso solo con llave está desactivado.

### 9.4 «Códigos de recuperación»

- Muestra cuántos quedan: «Te quedan 8 de 10».
- **«Generar códigos nuevos»** invalida los anteriores y muestra 10 nuevos, una sola vez.
- Solo sirven en el segundo paso si se pierde la app. **No** cuentan como método fuerte para administrar.

### 9.5 Si lo perdió todo

En `#sin-acceso` («Sin acceso a tu segundo paso») ve el contacto de soporte. Cambiar la contraseña **no** quita el segundo paso.

Tras verificar su identidad por otro medio, el equipo ejecuta en el servidor:

```
python manage.py retirar_factores correo@persona --operador correo@quien-atiende --identidad-verificada
```

Esto borra sus filas de `mfa_authenticator` y deja una auditoría `mfa-reset`. **No existe una ruta web** para hacerlo.

---

## 10. Recuperar o cambiar la contraseña

### Recuperar (`#recuperar`)

1. Escribe su correo. Siempre recibe la misma respuesta, exista o no la cuenta.
2. Si la cuenta existe, le llega un **enlace** que vale **10 minutos**.
3. El enlace abre `#restablecer`, donde escribe la nueva contraseña (mismas reglas que al registrarse).
4. **En la base:** se actualiza `cuentas_usuario.password` (solo el resumen). El enlace no se guarda en ninguna tabla: lo firma Django.
5. **No inicia sesión sola.** Después entra normalmente, con su segundo paso.

### Cambiar (Mi cuenta › «Cambiar contraseña»)

Pide la contraseña actual y la nueva. La sesión sigue abierta.

---

## 11. Lo que puede hacer una persona con sesión

Menú lateral: **Mi huerto · Panel técnico · Mantenimiento · Soporte técnico · Avisos · Mi cuenta**.

### 11.1 Si todavía no tiene huerto

Ve el estado **«Sin huerto asignado»** y la tarjeta **«Vincular mi huerto»**:

1. Pega el **código de vinculación** de 26 caracteres. Puede llevar guiones o espacios; la O cuenta como 0 y la I o la L como 1.
2. Pulsa **Vincular**. El servidor comprueba, en este orden:
   - **Ya tiene un huerto:** «ya vinculado».
   - **10 rechazos en la última hora:** «limitado».
   - **Sin código pendiente para ella, código vencido (más de 10 minutos) o código incorrecto:** «rechazado», sin decir el motivo. Cada error suma un intento; **al 5.º el código se bloquea**.
   - **Correcto:** se crea su fila en `huerto_membresia` (activa), el código pasa a `consumido` y se audita `binding-consumed`.
3. Desde ese momento ve su huerto.

**Ayuda.** Si no tiene código o no le funciona, un botón prepara un **borrador de correo** (`mailto`) para soporte. Solo abre su programa de correo: **no envía nada, no crea casos y no guarda nada**. Avisa si el texto parece contener un código.

Mi cuenta funciona igual aunque no tenga huerto, y el servidor entrega las guías de cuidado sin exigir huerto. Las pantallas del huerto muestran «Sin huerto asignado» junto a la tarjeta para vincular.

### 11.2 Mi huerto

- Saludo («Hola, *alias*»), nombre del huerto y **«Tus tres plantas»** (Planta 1, 2 y 3).
- Hoy el estado es **«Huerto vinculado · Sin lecturas recibidas»**: los sensores aún no envían datos a la base. Las lecturas salen como «sin datos».
- La tarjeta **«Resumen de tu huerto»** está preparada, pero el servidor devuelve `diagnosis: null` porque todavía no hay un productor de resúmenes (ni IA ni reglas conectadas).
- **«Control de lámpara»**: «Apagar lámpara» o, si ya hay una solicitud de apagado, «Restaurar control». Cada pulsación guarda una solicitud (`lamp-off` o `lamp-auto`), igual que el riego del Panel técnico.
- **«¿Algo no responde como debería?»** lleva a Soporte técnico.
- **En la base:** lectura de `huerto_membresia`, `huerto_huerto` y `huerto_zona`. Solo escribe si pide algo para la lámpara.

### 11.3 Panel técnico (`#telemetria`)

- Tarjetas de sensores, humedad, ambiente, histórico, depósito y conectividad, y bitácora de actuadores. Hoy no tienen datos.
- **«Solicitar riego puntual»**.
- **En la base**, para el riego y para la lámpara: una fila en `datos_solicitud` (`water`, `lamp-off` o `lamp-auto`) con estado **`pending`** y su auditoría `request-recorded`. **Ni la base ni el servidor encienden nada.** La página lo dice: «Una solicitud no confirma que la bomba se haya activado».

### 11.4 Mantenimiento (`#mantenimiento`)

- Tarjetas de cuidados manuales: **Nivel de agua** («Ya rellené el depósito»), **Sustrato y perlita**, **Germinación externa**, **Cosecha** («Registrar cosecha») e **Inspección visual** («Registrar inspección»).
- Al registrar un cuidado se guarda una fila en `datos_mantenimiento` (tipo `refill`, `substrate`, `germination`, `harvest` o `inspection`) y su auditoría `maintenance`. **El registro nunca se modifica.** Si estaba mal, una administradora lo corrige o lo anula con una fila nueva (12.3).
- Lista y calendario de lo registrado. Los anulados no aparecen y los corregidos muestran el tipo corregido.
- **«Guía de cuidado y preguntas frecuentes»**: las guías publicadas de `datos_guiacuidado`, de solo lectura.

### 11.5 Soporte técnico (`#soporte`)

1. **«Reportar un incidente»**: elige el problema (bomba, humedad, lámpara, conexión u otro) y marca la autorización expresa.
2. **En la base, en una transacción:**
   - si ya tenía una autorización activa, **se revoca** (`support-revoked`) y se cierran sus sesiones técnicas;
   - una fila en `datos_casosoporte` con folio `CS-XXXXXXXX`;
   - una fila en `datos_permisosoporte` con vigencia de **24 h**. **Del token solo se guarda un verificador HMAC-SHA256**: el token en claro no se guarda en ningún sitio;
   - auditoría `support-granted`;
   - un aviso `caso_nuevo` en `datos_avisocorreo`, que se envía al correo de soporte. **El correo no incluye el token.**
3. La persona ve **su token una sola vez**, con el folio y el correo de soporte. Si decide pedir ayuda, lo envía por correo al equipo.
4. **«Estado de la autorización»**: activa, vencida o revocada. Puede **revocarla** cuando quiera, y la revocación no tiene vuelta atrás.

### 11.6 Avisos (`#avisos`)

- Lista de avisos del huerto (crítico, advertencia, información), filtrable por activos o resueltos, y detalle de cada uno.
- Al abrir uno se marca como leído en `huerto_avisoleido`.
- **Hoy ningún proceso crea avisos**: la tabla `huerto_aviso` está lista, pero vacía.

### 11.7 Mi cuenta (`#cuenta`)

Tiene tres pestañas y un enlace:

- **Perfil.** Nombre, apellidos y alias. Al guardar se actualiza `cuentas_usuario` y, por cada campo que cambió, se guarda un evento `rectificacion` con el **nombre del campo**, nunca su valor.
- **Seguridad.** Sección 9.
- **Privacidad** (`#cuenta/privacidad`):
  - **«Mis datos»** muestra correo, nombre, apellidos, alias, fecha de alta y huertos. Cada consulta guarda un evento `acceso`.
  - **«Estadísticas de este navegador»** permite cambiar la decisión de cookies, igual que el aviso (sección 13).
- **Cambiar contraseña.** Sección 10.

> No existe un botón para **borrar la cuenta**. Si alguien lo pide, hoy se atiende fuera de la página.

---

## 12. Administración: cómo se crea un administrador y qué puede hacer

### 12.1 Qué hace que una cuenta sea administradora

- **No hay superusuario ni panel de Django.** No se usan `is_staff` ni `is_superuser`, y `django.contrib.admin` no está instalado.
- Una cuenta es **administradora si tiene al menos una de estas 6 capacidades** en `cuentas_usuario_user_permissions`:

| Capacidad | Pantalla del panel |
|---|---|
| `ver_flota` | **Telemetría de flota** |
| `atender_soporte` | **Consola remota** |
| `gestionar_mantenimientos` | **Mantenimientos** |
| `atender_consultas` | **Solicitudes del producto** |
| `vincular_huertos` | **Vinculación de huertos** y **Equipos y ventas** |
| `gestionar_guias` | **Guías de cuidado** |

- Cada capacidad abre **solo su pantalla**. El menú muestra únicamente las pantallas que la cuenta tiene.
- **Requisito:** para usar cualquier pantalla del panel, la cuenta debe tener **app autenticadora o llave de acceso**. Sin eso, el servidor responde «se requiere segundo factor» y la página la lleva a Seguridad.
- Una administradora **no ve las pantallas de persona usuaria** (Mi huerto, Soporte…). Al entrar va directo al panel; de las pantallas de usuario solo conserva **Mi cuenta**.
- Su inactividad máxima es de **15 minutos**.

### 12.2 Cómo se nombra una administradora

Coincide con lo que describes: eliges un correo, le das los permisos y, cuando inicia sesión, entra como administradora.

1. La persona **se registra en la página** como cualquiera y verifica su correo con el código.
2. Abres `sql/designar_administrador.sql` en Query Tool como `chilito_pkg_owner` y cambias solo:
   - `correo`: su correo;
   - `accion`: `'conceder'` (o `'retirar'`);
   - `capacidades`: por defecto, **las seis**. Quita las que no quieras darle;
   - `asignar_huerto_principal`: si das `gestionar_mantenimientos`, crea el huerto «principal» con su dispositivo, si no existen, y se lo asigna para mantenimientos.
3. Ejecutas el archivo completo. Los mensajes dicen qué pasó, qué capacidades tiene ahora y te avisan si le falta verificar el correo o activar el segundo factor.
4. La próxima vez que entre, la página la lleva al panel. Si no tiene app ni llave, primero a **Seguridad** para activarla.

**Para quitarle el acceso**, ejecuta el mismo archivo con `accion := 'retirar'`. Si le quitas todas las capacidades, vuelve a ser cuenta normal.

### 12.3 Mantenimientos (`gestionar_mantenimientos`)

- Lista los cuidados registrados **solo de los huertos que tiene asignados** en `datos_asignacionmantenimiento`, con filtros por huerto, estado, tarea y fechas.
- Puede **registrar** un cuidado en un huerto asignado.
- Puede **corregir** el tipo o **anular** un registro, siempre con **motivo**. Cada cambio es una fila nueva en `datos_revisionmantenimiento` (número 1, 2, 3…) con su auditoría. El registro original no se toca.
- Si otra persona lo revisó mientras tanto, se rechaza con «registro desactualizado». Un registro anulado ya no admite cambios.
- **Asignar otros huertos** se hace en SQL (sección 20).

### 12.4 Solicitudes del producto (`atender_consultas`)

- Bandeja de los mensajes de «Consíguelo». Se actualiza sola cada 30 segundos.
- Cada mensaje muestra folio `CP-XXXXXXXX`, fecha, nombre, correo, mensaje, estado y el estado de su aviso por correo.
- Puede marcarlo **atendido** o **archivado**. Transiciones permitidas: nueva → atendida o archivada; atendida → archivada; archivada → atendida. **Nunca vuelve a «nueva» ni se borra.** Se guarda quién lo atendió y cuándo.
- Para responder hay un acceso a Gmail con la cuenta de soporte. La página no envía la respuesta.

### 12.5 Vinculación de huertos (`vincular_huertos`)

Requiere además haber usado la **app o la llave en los últimos 5 minutos**. Si no, aparece **«Confirma tu segundo factor»**.

1. Ve los **huertos disponibles**: con dispositivo y sin dueño activo.
2. **Emitir código.** Elige huerto, escribe el correo de la cuenta (activa y verificada) y elige la entrega:
   - **Presencial:** el código de 26 caracteres aparece **una sola vez** en pantalla para dictarlo o entregarlo.
   - **Por correo:** solo se permite si antes hubo una emisión presencial para ese mismo huerto y esa cuenta. El correo sale después de guardar; si no se puede confirmar el envío, **el código se anula solo**.
3. **En la base:** una fila en `datos_codigovinculacion` con el **resumen** del código (nunca el código), vigencia de **10 minutos** y estado `pendiente`. Si había otro pendiente para ese huerto o esa cuenta, pasa a `reemplazado`. Auditoría `binding-issued`.
4. Los rechazos posibles: la cuenta ya tiene huerto, el huerto ya está ocupado, la cuenta ya tuvo ese huerto antes o la cuenta no es válida. Cada uno se explica en pantalla.
5. Ve los **pendientes** (puede **revocarlos**) y los **últimos cerrados**: usado, vencido, revocado, reemplazado o bloqueado.

### 12.6 Consola remota (`atender_soporte`)

1. Lista de **casos de soporte**: folio, dispositivo, incidente, estado de la autorización y estado de los avisos.
2. **«Solicitar token»** manda un correo a la persona pidiéndole el token (como mucho, uno por caso cada 10 minutos). Se audita `token-requested`.
3. **Pegar el token** que la persona envió abre una **sesión técnica** en `datos_sesiontecnica`, si la autorización sigue vigente y el token coincide con el verificador. Solo puede haber **una sesión abierta por administradora**.
4. **Diagnóstico.** Hoy devuelve vacío porque el dispositivo no está conectado; se audita `diagnostic-requested`.
5. **Resolver el caso** (solucionado, sin falla, sin respuesta u otro con nota) guarda una fila en `datos_resolucionsoporte`, **revoca la autorización** y cierra la sesión técnica. Es definitivo.

### 12.7 Guías de cuidado (`gestionar_guias`)

- **Crear:** siempre nace como **borrador**.
- **Editar:** cada cambio sube la `version` y guarda quién lo hizo. Si otra persona la cambió mientras tanto, se rechaza.
- **Publicar** y **retirar**. Retirar **no borra**; la guía se puede volver a publicar.
- Todo queda auditado (`guide-created`, `guide-updated`, `guide-published`, `guide-withdrawn`).

### 12.8 Telemetría de flota (`ver_flota`)

Lista los dispositivos registrados (hasta 100). Hoy no muestra conexión ni lecturas: no hay datos de sensores en la base.

### 12.9 Equipos y ventas (visible con `vincular_huertos`)

Formularios de equipos, ventas, entregas y resumen económico. **No guardan nada en la base**: son borradores que viven mientras la pantalla está abierta. No acreditan pagos ni autorizan vinculaciones.

---

## 13. Cookies y sesión: qué se guarda, dónde y cuánto dura

### 13.1 Las cuatro cookies

| Cookie | Para qué | Cuánto dura | ¿JavaScript puede leerla? | Qué hay en la base |
|---|---|---|---|---|
| `sessionid` | Mantener la sesión | Hasta cerrar el navegador (el servidor la corta a las 8 h) | **No** (HttpOnly) | Una fila en **`django_session`** con la sesión firmada: cuenta, pasos de acceso, hora de inicio y última actividad, y códigos pendientes |
| `csrftoken` | Que otra web no pueda hacer acciones en tu nombre | 1 año (valor de Django) | **Sí**, a propósito: la página la copia en la cabecera `X-CSRFToken` | Ninguna fila |
| `chilito_preferencia` | Recordar la decisión sobre cookies **de este navegador** | **180 días** | No (HttpOnly) | El valor es el **identificador firmado** de un `privacidad_sujetoprivacidad` de ámbito `navegador` |
| `chilito_estadistica` | Contar visitas por sección **solo si se aceptó** | **30 minutos** | No (HttpOnly) | Ninguna fila con ese valor: solo totales en `privacidad_conteonavegacion` |

Las cuatro son `SameSite=Lax` y, en producción, `Secure` (solo por HTTPS). **La página no usa `localStorage` ni `sessionStorage`** para nada de esto.

### 13.2 Qué pasa al decidir sobre las cookies

En el aviso **«Tu privacidad y las cookies»** o en **«Configurar cookies»**, al pie:

- **Cookies necesarias** (`sessionid`, `csrftoken`, `chilito_preferencia`): siempre activas.
- **Estadísticas opcionales** (`chilito_estadistica`): el interruptor.

Cuando la persona pulsa aceptar, rechazar o guardar:

1. Si el navegador no tenía `chilito_preferencia` válida, se crea un **sujeto de navegador** en `privacidad_sujetoprivacidad` (`ambito = 'navegador'`). Si tiene sesión abierta, queda ligado a su cuenta (`usuario_id`).
2. Se guarda una fila **nueva** en `privacidad_decisionprivacidad` con `acto = 'cookies'`, la decisión (sí o no), la **versión vigente del aviso de privacidad** y la **versión vigente de la política de cookies**. El historial nunca se borra.
3. Se crea o actualiza `privacidad_preferenciafinalidad` para que apunte a esa decisión, que es la **vigente**.
4. Se guarda un evento en `privacidad_eventoprivacidad`: `decision`, u `oposicion` si rechaza con sesión iniciada.
5. El servidor devuelve la cookie `chilito_preferencia` firmada. Si rechazó, borra `chilito_estadistica`.

**La decisión deja de valer**, y el aviso vuelve a salir, cuando:

- pasan **180 días**;
- se registra una **versión nueva** del aviso de privacidad o de la política de cookies;
- la decisión era de **otra cuenta** y ahora hay una sesión distinta.

**Cerrar el aviso sin elegir no es aceptar.** Si el servidor no responde, no se presume nada y se vuelve a preguntar.

**Límite:** 20 decisiones por minuto por IP.

### 13.3 Cómo se cuentan las visitas (solo si aceptó)

1. Al cambiar de sección (inicio, proyecto, prototipo, funcionamiento, huerto, panel técnico, mantenimiento, soporte, avisos, cuenta o privacidad), la página avisa al servidor.
2. El servidor **vuelve a comprobar** la decisión vigente. Si no aceptó, no cuenta nada.
3. Si aceptó, crea la cookie `chilito_estadistica` (un valor aleatorio firmado, 30 minutos) y suma **1** a la fila del **día y la sección** en `privacidad_conteonavegacion`.
4. La misma sección no se cuenta dos veces para el mismo navegador en esos 30 minutos. La marca se guarda **resumida con HMAC** en `cuentas_cuotas_acceso`.
5. **No se guarda quién visitó**: solo «hoy, sección X, N visitas».

Para ver las decisiones guardadas: `sql/instalacion/07_consultar_cookies.sql`.

### 13.4 La tabla `cuentas_cuotas_acceso`

Es la **caché de Django guardada en PostgreSQL**. Contiene contadores temporales con caducidad (`expires`):

| Límite | Valor |
|---|---|
| Registro | 10 por minuto por IP |
| Inicio de sesión | 30 por minuto por IP |
| Fallos de acceso | 10 por minuto por IP y 5 cada 5 minutos por cuenta |
| Reenviar código de verificación | 1 cada 60 s |
| Recuperar contraseña | 10 por minuto por IP y 1 por minuto por correo |
| Cambiar contraseña | 5 por minuto |
| Confirmar identidad | 10 por minuto |
| Formulario «Consíguelo» | **5 por hora por IP** |
| Decisiones de cookies | 20 por minuto por IP |
| Avisos de sección | 60 por minuto por IP |
| Escrituras del panel | 60 por minuto por cuenta (15 en soporte técnico) |

---

## 14. Correos que envía el sistema

| Correo | Cuándo | Dónde queda constancia |
|---|---|---|
| Código de verificación (6 dígitos, 10 min) | Al registrarse | Sesión (`django_session`) |
| Código de acceso (6 dígitos, 5 min) | Al entrar sin app ni llave | Sesión (`django_session`) |
| Enlace para restablecer la contraseña (10 min) | En «Recuperar» | No se guarda: lo firma Django |
| Código de vinculación (por correo) | Entrega «correo» en Vinculación | `datos_codigovinculacion.envio` |
| «Nuevo caso de soporte» → soporte | Al reportar un incidente | `datos_avisocorreo` (`caso_nuevo`) |
| «Soporte solicita el token» → persona | «Solicitar token» en Consola remota | `datos_avisocorreo` (`token_solicitado`) |
| «Pregunta sobre el producto» → soporte | Formulario «Consíguelo» | `datos_avisocorreo` (`consulta_nueva`) |

**Los avisos de `datos_avisocorreo`** se envían justo después de guardar. Si fallan:

- quedan como `fallido`;
- el comando `python manage.py enviar_avisos_pendientes` los reintenta esperando 2, 4, 8 y 16 minutos, hasta **5 intentos**;
- `aceptado_smtp` significa que el servidor de correo lo aceptó, **no** que llegó a la bandeja.

No se envían avisos de «tu contraseña cambió» ni similares: `ACCOUNT_EMAIL_NOTIFICATIONS` no está activado en la configuración.

En local, sin SMTP, los correos van a un buzón de archivos (`CHILITO_MAILBOX`). En producción el servidor no arranca sin SMTP.

---

## 15. Reglas que protege la propia base (triggers)

Si algo intenta saltarse estas reglas, la base responde con el error **23514** y no guarda nada.

| Regla | Función |
|---|---|
| No se modifica ni se borra: dispositivos, mantenimientos, revisiones, casos, resoluciones, solicitudes, versiones, notas de conocimiento y auditoría | `chilito_historial_inmutable` |
| No se modifica ni se borra: textos legales, finalidades, decisiones ni eventos de privacidad | `chilito_privacidad_historial_inmutable` |
| La aplicación no puede crear cuentas staff, superusuario ni inactivas | `chilito_usuario_sin_privilegios` |
| Un segundo factor no cambia de dueño ni de tipo | `chilito_proteger_mfa` |
| Cada huerto nace con 3 plantas y estas no se borran | `chilito_crear_tres_zonas`, `chilito_conservar_zona` |
| Zonas, membresías, avisos y lecturas no se reasignan | `chilito_proteger_relacion`, `chilito_proteger_aviso`, `chilito_proteger_lectura_aviso` |
| Marcar un aviso como leído exige membresía activa | `chilito_lectura_exige_membresia` |
| Una membresía solo nace de un código consumido coherente (salvo el propietario) | `chilito_membresia_por_codigo` |
| Un código de vinculación se cierra una sola vez y no se borra | `chilito_codigo_vinculacion` |
| Una autorización de soporte solo se revoca, sin vuelta atrás | `chilito_permiso_revocar` |
| Una sesión técnica solo se cierra, una vez | `chilito_tecnica_cerrar` |
| Coherencia entre caso, dispositivo, permiso, sesión, solicitud y auditoría | `chilito_datos_relaciones` |
| Una corrección exige asignación, número consecutivo y que el registro no esté anulado | `chilito_revision_mantenimiento` |
| La auditoría de una revisión debe ser del mismo editor y huerto | `chilito_auditoria_revision` |
| Una asignación de mantenimiento no cambia de persona ni de huerto | `chilito_asignacion_estable` |
| Las consultas del buzón solo avanzan de estado y no se borran | `chilito_consulta_atencion` |
| Un aviso por correo solo suma intentos hasta ser aceptado | `chilito_aviso_correo` |
| Las guías no se borran; cada cambio sube la versión | `chilito_guia_cuidado` |
| Cada acto de privacidad corresponde a su documento, sujeto y ámbito | `chilito_privacidad_relaciones`, `chilito_privacidad_ambitos`, `chilito_privacidad_sujeto_estable` |
| Correo único por buzón real (Gmail sin puntos ni «+») | `chilito_identidad_correo` (índice único) |

Además hay **restricciones `CHECK`** (valores válidos, longitudes, fechas coherentes, vigencias de 10 minutos o 24 horas) e **índices únicos** (una membresía activa por cuenta, un código pendiente por huerto y por cuenta, una sesión técnica abierta por administradora, etc.).

**Límite honesto:** estas reglas protegen contra errores de la aplicación. No protegen contra alguien que tenga la contraseña de `chilito_pkg_owner` y desactive los triggers a propósito.

---

## 16. Qué puede y qué no puede hacer la aplicación en la base

Resumen de los privilegios de `chilito_pkg_runtime` (sección 10 del script):

| Puede | No puede |
|---|---|
| Leer cuentas, permisos, huertos, zonas y dispositivos | Crear, cambiar o borrar huertos, zonas ni dispositivos |
| Crear cuentas y cambiar email, contraseña, nombre, alias, último acceso y bienvenida | Cambiar `is_staff`, `is_superuser` ni `is_active` |
| Gestionar sesiones, cuotas y correos de las cuentas | Darse capacidades (`cuentas_usuario_user_permissions` es de solo lectura) |
| Crear y borrar sus métodos de segundo factor | Cambiar el dueño o el tipo de un segundo factor |
| Insertar mantenimientos, revisiones, casos, permisos, sesiones, solicitudes y auditoría | Borrar ninguno de ellos |
| Revocar permisos, cerrar sesiones técnicas y avanzar el estado de consultas, avisos y códigos | Cambiar otras columnas de esas filas |
| Crear y editar guías (sin borrarlas) | Cambiar la clave, la autoría o la fecha de creación de una guía |
| Crear membresías (con un código válido) | Asignar huertos para mantenimiento |
| Insertar decisiones y eventos de privacidad | Modificar o borrar decisiones y eventos; registrar textos legales |
| Ejecutar `chilito_identidad_correo` | Crear o borrar tablas (sin DDL) |

---

## 17. Datos con los que nace la base

- **39 tipos de contenido** y **162 permisos**, entre ellos las 6 capacidades.
- **Textos legales registrados:**
  - aviso de privacidad **0.1** y **0.2** (borrador);
  - términos **0.1** y **0.2** (borrador);
  - política de cookies **0.1** (borrador).

  La vigente de cada tipo es la más reciente.
- **Finalidad opcional:** `estadisticas_internas_navegacion`.
- **9 guías de cuidado publicadas:**
  1. germinación;
  2. tiempo de brotación;
  3. trasplante;
  4. sustrato y perlita;
  5. riego;
  6. depósito;
  7. mangueras y goteros;
  8. cosecha;
  9. sin lecturas.
- **61 migraciones** marcadas como aplicadas.
- **No nace con ninguna cuenta, huerto ni contraseña.**

---

## 18. Cómo se comprobó el script nuevo

Se hizo el 14 de noviembre de 2026, **solo en bases temporales** que después se borraron. La base oficial no se tocó; solo se leyó la lista de migraciones.

| Prueba | Resultado |
|---|---|
| Instalar el `03_esquema_completo.sql` anterior y el script nuevo, cada uno en una base vacía, y comparar su catálogo | **Iguales** en 264 columnas, 235 restricciones, 183 índices, 43 triggers, 25 funciones (incluido el código de cada una), privilegios por tabla y por columna, secuencias, tipos de contenido, permisos con sus `id`, textos legales, guías y migraciones. Única diferencia: la **posición interna** de dos columnas de `django_content_type`, porque el script anterior crea y luego borra una columna. No afecta al funcionamiento |
| `05_prueba_triggers.sql` sobre la base nueva | **19 casos, 0 fallos** |
| `manage.py migrate --check` | Sin migraciones pendientes |
| Suite completa de Django sobre la base creada con el script nuevo (`--keepdb`, sin que Django la recree) | **323 de 323** correctas |
| Prueba CRUD con el rol limitado `chilito_pkg_runtime` | **72 de 72** correctas |
| Flujos HTTP: seguridad, segundo factor (45 de 45) y privacidad (54 de 54) | Todos correctos |
| `designar_administrador.sql`: conceder, repetir, retirar en parte, retirar todo, correo inexistente y archivo sin editar | Correcto. Se corrigió un error de nombre de variable durante la prueba |

---

## 19. Cómo trabajar con la base de aquí en adelante

La estructura de la base **la define Django** con sus migraciones (`backend/*/migrations/`). Al arrancar, Django compara `django_migrations` con sus archivos. Por eso:

- **Base nueva:** solo `el_chilito_base_completa.sql`. Sin parches.
- **Cambiar la estructura** (tabla, columna o regla nueva):
  1. Crea la **migración** en Django. Es la fuente de la verdad.
  2. Añade el cambio al **script único**, en su sección, y la fila nueva en el registro de migraciones (9.5).
  3. Si cambian permisos de la aplicación, actualiza la sección 10.
  4. Para una base que **ya tiene datos**, aplica el cambio con `manage.py migrate` usando el usuario propietario, o con un script equivalente.
  5. Repite las comprobaciones de la sección 18 en una base temporal.
- Si cambias una tabla **a mano en pgAdmin** sin migración, Django no lo sabrá y la siguiente migración puede fallar. Evítalo.
- `backend/tools/generar_sql_instalacion.py` sigue generando el **antiguo** `03_esquema_completo.sql` a partir de las migraciones. Puedes usarlo para comparar, pero ya no es el archivo que se instala.

---

## 20. Consultas útiles

Todas como `chilito_pkg_owner` en Query Tool.

**¿Quién es administrador y con qué capacidades?**

```sql
SELECT u.email, string_agg(p.codename, ', ' ORDER BY p.codename) AS capacidades
FROM cuentas_usuario u
JOIN cuentas_usuario_user_permissions up ON up.usuario_id = u.id
JOIN auth_permission p ON p.id = up.permission_id
JOIN django_content_type c ON c.id = p.content_type_id AND c.app_label = 'datos'
WHERE p.codename IN ('ver_flota','atender_soporte','gestionar_mantenimientos',
                     'atender_consultas','vincular_huertos','gestionar_guias')
GROUP BY u.email ORDER BY u.email;
```

**¿Quién tiene qué huerto?**

```sql
SELECT u.email, h.clave, h.nombre, m.activa, m.asignada_en
FROM huerto_membresia m
JOIN cuentas_usuario u ON u.id = m.usuario_id
JOIN huerto_huerto h ON h.id = m.huerto_id
ORDER BY m.asignada_en DESC;
```

**Asignar otro huerto a una administradora para mantenimientos:**

```sql
INSERT INTO datos_asignacionmantenimiento(usuario_id, huerto_id, activa, asignada_en)
SELECT u.id, h.id, true, now()
FROM cuentas_usuario u, huerto_huerto h
WHERE lower(u.email) = lower('correo@ejemplo.com') AND h.clave = 'CLAVE-DEL-HUERTO'
ON CONFLICT (usuario_id, huerto_id) DO UPDATE SET activa = true;
```

**¿Qué segundo factor tiene cada cuenta?** (sin mostrar secretos)

```sql
SELECT u.email, a.type, a.created_at, a.last_used_at
FROM mfa_authenticator a JOIN cuentas_usuario u ON u.id = a.user_id
ORDER BY u.email, a.type;
```

**Sesiones abiertas ahora:**

```sql
SELECT count(*) FROM django_session WHERE expire_date > now();
```

**Mensajes de «Consíguelo» sin atender:**

```sql
SELECT recibida_en, nombre, correo, left(mensaje, 80) FROM datos_consultaproducto
WHERE estado = 'nueva' ORDER BY recibida_en DESC;
```

**Visitas por sección (solo de quien aceptó estadísticas):**

```sql
SELECT dia, seccion, visitas FROM privacidad_conteonavegacion ORDER BY dia DESC, seccion;
```

**Últimas acciones auditadas:**

```sql
SELECT a.creada_en, u.email, a.accion, a.resultado
FROM datos_auditoria a JOIN cuentas_usuario u ON u.id = a.actor_id
ORDER BY a.creada_en DESC LIMIT 50;
```

---

## 21. Cosas que hoy existen solo a medias

Funcionan como se describe arriba, pero conviene saberlo:

- **Sensores:** la base no recibe lecturas. «Mi huerto», «Panel técnico» y «Telemetría de flota» muestran «sin datos».
- **Resumen del huerto:** preparado, pero sin productor; el servidor devuelve `diagnosis: null`.
- **Solicitudes de riego y lámpara:** se guardan como `pending`; nada las ejecuta.
- **Avisos del huerto:** la tabla está lista, pero ningún proceso crea avisos.
- **Diagnóstico remoto:** abre la sesión técnica, pero devuelve vacío.
- **Equipos y ventas:** solo borradores en pantalla; no se guardan.
- **`datos_validacionversion` y `datos_revisionconocimiento`:** existen y están protegidas, pero no tienen pantalla.
- **Grupos de permisos y `account_emailconfirmation`:** existen porque las usa Django o allauth, pero quedan vacías.
- **Textos legales:** las versiones registradas son borradores (0.2 para aviso y términos; 0.1 para cookies).
- **Borrar la cuenta:** no hay opción en la página.
- **Base oficial actual:** le falta el parche 08 (sección 1).

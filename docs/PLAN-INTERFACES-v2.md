# El Chilito · Plan de interfaces v2 (usuario y administración)

Plan de **qué contiene cada pantalla, cómo se ve y qué hace**, adaptado a la base de datos v2 (`el_chilito_base_v2.sql`).
Lo escribe el equipo de planificación; lo ejecuta quien programe el frontend y Django. **No es código.**

**Fuentes contrastadas (14 de noviembre de 2026):**
- `INVENTARIO-INTERFAZ-ACTUAL.md` (lectura del código, sin navegador).
- **Revisión visual en `localhost:8780`** con una cuenta de usuario sin huerto y una de administrador con 5 capacidades.
- `FUNCIONAMIENTO-BASE-DE-DATOS-v2.md` (base nueva).

---

## Índice

0. [Reglas de este plan](#0-reglas-de-este-plan)
1. [Sistema visual: qué se conserva y qué se corrige](#1-sistema-visual)
2. [Navegación nueva](#2-navegación-nueva)
3. [Componentes nuevos o unificados](#3-componentes-nuevos-o-unificados)
4. [Pantallas de la persona usuaria](#4-pantallas-de-la-persona-usuaria)
5. [Pantallas de administración](#5-pantallas-de-administración)
6. [Parte pública y acceso](#6-parte-pública-y-acceso)
7. [Mapa pantalla → base de datos](#7-mapa-pantalla--base-de-datos)
8. [Orden de construcción](#8-orden-de-construcción)
9. [Decisiones tomadas y preguntas abiertas](#9-decisiones-tomadas-y-preguntas-abiertas)

---

## 0. Reglas de este plan

1. **El estilo no cambia.** El panel conserva el aspecto actual (fondo crema con brillo naranja, menú lateral verde flotante, tarjetas de vidrio claras), igual para usuario y administración. La portada y el acceso conservan su vidrio oscuro sobre fotos. Solo se **corrigen inconsistencias** (sección 1.3).
2. **El flujo de acceso no se toca:** registro, código de verificación, inicio de sesión, segundo paso, llaves de acceso, recuperar contraseña y bienvenida. Solo se añade la pantalla de **aceptar una versión legal nueva** (4.0).
3. **Se reutiliza lo que ya existe** (tarjeta `.bento-panel`, pestañas `.account-tabs`, diálogo `.app-dialog`, tabla `.user-table`, calendario, estados `.app-state`). Lo nuevo se construye con esas mismas piezas.
4. **Nada se inventa en pantalla.** Si un dato no viene de la base, no se muestra. Se quitan los textos y métricas sin fuente: evaluación de IA, correlaciones, «evaporación estimada» y el estado `ready` que nunca llegaba.
5. **Toda acción destructiva o de efecto inmediato pide confirmación** con el diálogo estándar (3.6).
6. Los textos entre comillas «…» son **literales propuestos**. Se pueden pulir, pero manteniendo el sentido.

---

## 1. Sistema visual

### 1.1 Lo que se ve hoy (comprobado en navegador)

| Zona | Aspecto real |
|---|---|
| Portada | Encabezado de vidrio oscuro flotante con cápsula de navegación; hero a pantalla completa con foto del habanero; titular grande blanco. Aviso de cookies como barra de vidrio oscuro abajo. |
| **Acceso** | **Vidrio oscuro sobre la foto** (no claro, como decía el inventario): foto a la izquierda con la cita, tarjeta de vidrio oscuro a la derecha, campos oscuros. |
| Panel (usuario y admin) | Fondo crema `#fdf3e8` con manchas naranjas difusas; menú lateral verde flotante (268 px, radio 26 px) con botones de vidrio; tarjetas de vidrio claro (radio 22 px); títulos grandes en negro verdoso peso 800; barra flotante arriba a la derecha con botones redondos verdes (perfil y campana). |
| Móvil | Barra superior con logotipo, perfil, campana y «Menú»; contenido apilado. Correcto. |

### 1.2 Se conserva

Paleta del panel (`--claro-*`), menú lateral verde, tarjetas de vidrio claro, tipografía Geist, íconos de trazo propios, radios (botones en cápsula, tarjetas 22 px), pestañas en cápsula, acordeones de las guías y diálogos centrados.

### 1.3 Se corrige (para que todo sea Liquid Glass coherente)

| # | Problema visto | Corrección |
|---|---|---|
| C1 | Botones de **tres aspectos**: verde sólido («Vincular huerto», «Cambiar contraseña», «Consultar mis datos»), blanco de vidrio («Cambiar datos», «Cerrar sesión») y plano. | Solo **tres variantes**, todas de vidrio: **Primaria** (vidrio verde translúcido con reflejo superior y `blur`, texto blanco), **Secundaria** (vidrio claro, texto verde oscuro) y **Peligro** (vidrio rojo translúcido, texto blanco). Mismo alto (44 px; 38 px compacta), radio y animación. |
| C2 | Botones **deshabilitados** pierden el vidrio y quedan como píldoras grises casi invisibles (p. ej. «Registrar recarga» y el de la lámpara). | Deshabilitado = **la misma variante con 45 % de opacidad** y `cursor:not-allowed`. Siempre legible. Si una acción no está disponible, se explica con texto debajo («Disponible cuando tu equipo esté conectado.»). |
| C3 | **Campos y selectores verde oscuro** con texto blanco dentro de tarjetas crema (código de vinculación, «Tipo de problema», «Nombre de la llave», filtros de Mantenimientos). | Campos de **vidrio claro**: fondo `rgba(255,250,244,.72)`, borde `rgba(70,40,20,.18)`, texto `--claro-tinta`, foco con anillo verde de 3 px. Lista desplegable con el mismo vidrio claro. |
| C4 | Insignias planas (6 px, sin vidrio). | Cápsula pequeña de vidrio con color por significado: verde (correcto o activo), ámbar (pendiente o advertencia), rojo (falla o crítico) y gris (neutro). Siempre con texto, nunca solo color. |
| C5 | Mensajes de éxito o error como cajas sueltas arriba; el único «toast» es el de cookies. | **Un solo sistema de avisos flotantes** («toast») de vidrio, abajo a la derecha (abajo al centro en móvil), `role="status"`, que se ocultan a los 5 s. Los errores de formulario siguen junto al campo. |
| C6 | Sin huerto, la página enseña **todo el contenido bloqueado y gris** debajo de «Vincular». | Si no hay huerto o equipo, la pantalla muestra **solo** el estado vacío útil (4.1-A y 4.1-B). No se pinta contenido deshabilitado. |
| C7 | Tarjetas que tardan en pintarse al desplazarse (demasiados `backdrop-filter`). | `blur` solo en tarjetas de primer nivel; los elementos internos (filas, campos, insignias) usan fondo translúcido **sin** `blur`. |
| C8 | Los tokens viven en 4 `:root` y 5 ámbitos, con 1 046 `!important`. | Un único archivo `vistas/estilos/tokens.css` con los tokens de las tres zonas (pública, acceso y panel). Las demás hojas solo **consumen** variables. La limpieza de `!important` se hace en la fase final (sección 8). |
| C9 | Los administradores no tienen campana de avisos. | Campana en la barra flotante para **todas** las cuentas, con contador de no leídas. |

> Lo que sea ajuste fino (sombras, tonos exactos, tamaños) lo decide el responsable de diseño sobre esta base.

---

## 2. Navegación nueva

### 2.1 Persona usuaria

Menú lateral: **Mi huerto · Panel técnico · Mantenimiento · Soporte técnico · Mi cuenta**. En la barra flotante: perfil, **campana con contador** y, en móvil, «Menú». Si tiene más de un huerto, aparece el **selector de huerto** (3.1) arriba del contenido de las 4 primeras pantallas.

| Ruta | Pantalla | Cambio |
|---|---|---|
| `#huerto` | Mi huerto | Rediseñada (4.1) |
| `#huerto/nuevo` | Crear huerto | **Nueva** (4.2) |
| `#huerto/vincular` | Vincular equipo | **Nueva**; sustituye «Vincular mi huerto» (4.3) |
| `#huerto/plantas/<n>` | Ficha de planta | **Nueva** (4.4) |
| `#telemetria` | Panel técnico | Con datos reales (4.5) |
| `#mantenimiento` (+ `/guias`, `/historial`) | Mantenimiento | Cuidados por planta (4.6) |
| `#soporte` | Soporte técnico | Sin token; con autodiagnóstico (4.7) |
| `#avisos`, `#avisos/<id>` | Avisos | Centro de notificaciones (4.8) |
| `#cuenta`, `#cuenta/seguridad`, `#cuenta/privacidad`, `#cuenta/contrasena` | Mi cuenta | + «Mis huertos» y «Eliminar mi cuenta» (4.9) |
| `#aceptar-legales` | Aceptar textos legales | **Nueva**, bloqueante (4.0) |

Todas las rutas con huerto aceptan `?h=<id>` cuando la cuenta tiene más de uno; sin parámetro se usa el último elegido en esta visita o, si no hay, el primero.

### 2.2 Administración

Menú lateral con rótulo «Administración». Solo aparecen los destinos de las capacidades que tiene la cuenta.

| Grupo | Destino | Ruta | Capacidad | Cambio |
|---|---|---|---|---|
| Operación | Telemetría de flota | `#admin/flota` | `ver_flota` | Datos reales (5.1) |
| | Consola remota | `#admin/soporte` | `atender_soporte` | Sin token (5.2) |
| | Mantenimientos | `#admin/mantenimientos` | `gestionar_mantenimientos` | Todos los huertos (5.3) |
| Gestión | Solicitudes del producto | `#admin/solicitudes` | `atender_consultas` | Casi igual (5.4) |
| | Inventario de equipos | `#admin/equipos` | `gestionar_dispositivos` | **Nueva**; sustituye «Vinculación de huertos» (5.5) |
| | Ventas | `#admin/ventas` | `gestionar_ventas` | **Nueva**; sustituye la maqueta «Equipos y ventas» (5.6) |
| | Guías de cuidado | `#admin/guias` | `gestionar_guias` | Igual + confirmaciones (5.7) |
| Legal | Textos legales | `#admin/legales` | `gestionar_legales` | **Nueva** (5.8) |
| | Bitácora de consentimientos | `#admin/consentimientos` | `ver_consentimientos` | **Nueva** (5.9) |
| Super admin | Administradores | `#admin/administradores` | `gestionar_administradores` | **Nueva** (5.10) |
| | Abrir correo de soporte | (enlace externo) | cualquiera | Igual |
| — | Mi cuenta | `#cuenta` | — | Igual |

Rutas retiradas: `#admin/vinculacion` → `#admin/equipos`; `#admin/comercial` → `#admin/ventas`.

---

## 3. Componentes nuevos o unificados

### 3.1 Selector de huerto
Cápsula de vidrio arriba del título: `[🌿 Mi huerto de casa ▾]`. Al pulsarla se abre una lista con cada huerto, una insignia de estado del equipo («En línea», «Desconectado», «Sin equipo») y una última opción, «+ Crear otro huerto» (desactivada con la nota «Máximo 3 huertos» si ya tiene 3, o «Primero vincula tu huerto sin equipo» si ya tiene uno sin equipo). **Solo se muestra si hay 2 o más huertos.**

### 3.2 Línea de estado del equipo
Debajo del título de las pantallas de huerto: `● En línea · Última lectura hace 2 min · Firmware 1.0.3`. Estados (de `dispositivo.conexion` y la última `medicion.medida_en`):

| Estado | Insignia | Texto |
|---|---|---|
| `en_linea` y lectura < 15 min | verde | «En línea · Última lectura hace N min» |
| `en_linea` y lectura ≥ 15 min | ámbar | «Conectado, sin lecturas recientes» |
| `desconectado` | rojo | «Desconectado desde <fecha>» |
| `nunca` | gris | «Equipo vinculado · Esperando su primera conexión» |

### 3.3 Tarjeta de orden (comando) con estado
Para riego, lámpara, autodiagnóstico y acciones de soporte: título de la orden + insignia de estado: «Pendiente» (ámbar), «Enviada» (ámbar con pulso), «Confirmada» (verde), «Falló» (rojo, con `detalle_error`) y «Sin respuesta» (gris, al expirar). Mientras esté pendiente o enviada, la pantalla consulta su estado **cada 5 s durante 10 min como máximo** (en segundo plano, sin alargar la sesión).

### 3.4 Campana y centro de avisos
Botón redondo con contador rojo de no leídas (máximo «9+»). Al pulsarlo va a `#avisos`. El contador se actualiza al cargar cada pantalla y cada 60 s en segundo plano.

### 3.5 Aviso flotante («toast»)
Ver C5. Variantes: éxito (ícono check verde), información (ícono info) y error (ícono alerta rojo; permanece hasta cerrarlo).

### 3.6 Diálogo de confirmación estándar
`dialog.app-dialog`: título en pregunta («¿Revocar el acceso de soporte?»), una o dos frases de consecuencia, botón **Secundario** «Cancelar» (con foco inicial) y botón **Primario** o **Peligro** con el verbo exacto («Revocar acceso»). Si la acción es irreversible, la última frase lo dice: «No se puede deshacer.»

### 3.7 Tarjeta de autodiagnóstico
Lista de componentes con ícono y resultado: ✔ Correcto (verde), ✖ Falla (rojo), ⏱ Sin respuesta (ámbar) y — No instalado (gris). Resultado general arriba («Todo funciona» o «Encontramos N problemas»). Componentes en este orden y con estas etiquetas: Conexión · Sensor de ambiente (SHT31) · Sensor de luz · Sustrato planta 1, 2 y 3 · Flotador del depósito · Bomba 1, 2 y 3 · Lámpara · Ventilador.

### 3.8 Pantalla de código grande (vinculación y alta de credencial)
Código en tipografía monoespaciada de 32 px, agrupado (`XXXX-XXXX`), con botón «Copiar», contador regresivo («Vence en 9:42») y la advertencia «Solo se muestra ahora.».

---

## 4. Pantallas de la persona usuaria

> Plantilla de cada ficha: **Propósito · Disposición · Contenido · Acciones · Estados · Datos (base v2)**.

### 4.0 Aceptar textos legales nuevos — `#aceptar-legales` (NUEVA)
- **Propósito:** cumplir la reaceptación obligatoria cuando se publica una versión nueva de términos o aviso.
- **Cuándo:** justo después de iniciar sesión (y en cada carga de una ruta privada) si `chilito_aceptaciones_pendientes(usuario)` devuelve filas. El enrutador **no deja ir a ninguna otra ruta privada** hasta aceptar, salvo cerrar sesión.
- **Disposición:** el mismo marco del acceso (vidrio oscuro sobre foto), tarjeta a la derecha.
```
 Actualizamos nuestros documentos
 Para seguir usando El Chilito, revisa y acepta la versión nueva.
 ┌ Términos y condiciones · versión 1.1 ── [Leer documento ↗] ┐
 │ ☐ Acepto los Términos y condiciones (versión 1.1)          │
 └────────────────────────────────────────────────────────────┘
 ┌ Aviso de privacidad · versión 1.1 ─── [Leer documento ↗] ┐
 │ ☐ He leído el Aviso de privacidad (versión 1.1)            │
 └────────────────────────────────────────────────────────────┘
 [ Aceptar y continuar ]        Cerrar sesión
```
- **Acciones:** «Aceptar y continuar» (Primaria, desactivada hasta marcar todas las casillas mostradas) → inserta las `privacidad_decision` correspondientes y va al destino original. «Cerrar sesión» (enlace).
- **Estados:** cargando; error «No pudimos guardar tu aceptación. Inténtalo de nuevo.».

### 4.1 Mi huerto — `#huerto`
Tiene **tres versiones** según la situación.

**4.1-A Sin ningún huerto** (cuenta nueva):
```
 Hola, <alias>
 Te damos la bienvenida a El Chilito.
 ┌ [ilustración de 3 plantas] ───────────────────────────────┐
 │ Aún no tienes un huerto                                    │
 │ Crea tu huerto en la página y después conecta tu equipo    │
 │ El Chilito con el código que te daremos.                   │
 │ [ Crear mi huerto ]                                        │
 │ ¿Todavía no tienes tu equipo? Conoce El Chilito ↗ (#consiguelo) │
 └────────────────────────────────────────────────────────────┘
 Guías de cuidado (acceso rápido a #mantenimiento/guias)
```

**4.1-B Huerto sin equipo:** título con el nombre del huerto, tarjeta «Conecta tu equipo» con 3 pasos ilustrados («1. Genera tu código», «2. Conéctate a la red Huerto-Setup de tu equipo», «3. Escribe tu Wi-Fi y el código») y el botón «Vincular equipo» (→ 4.3). Debajo, las **tres plantas** (sí se pueden nombrar y registrar su siembra aunque no haya equipo).

**4.1-C Huerto con equipo (versión completa):**
```
 [selector de huerto]*                                  (*si tiene 2 o más)
 Hola, <alias> · <nombre del huerto>
 <frase del día>
 ● En línea · Última lectura hace 2 min           (3.2)
 ┌Depósito┐┌Humedad media┐┌Ambiente┐┌Lámpara┐      ← 4 métricas
 Tus tres plantas
 ┌Planta 1 ───┐┌Planta 2 ───┐┌Planta 3 ───┐
 │ Chilito    ││ …          ││ …          │        nombre, etapa, días desde siembra,
 │ Floración  ││            ││            │        humedad del sustrato (%) con barra,
 │ 41 %  ███░ ││            ││            │        insignia si está seca
 │ [Ver planta]││           ││            │
 ┌ Resumen de tu huerto (IA) ────────────── Ver anteriores ┐
 │ «Tus plantas se regaron bien; el depósito necesita agua.» │
 │ Generado hace 1 h                                        │
 └──────────────────────────────────────────────────────────┘
 Acciones rápidas
 ┌Registrar recarga┐┌Registrar un cuidado┐┌Revisar mi equipo┐
 ┌ Lámpara ─────────── Encendida (automático) ── [Apagar lámpara] ┐
 Ante una emergencia, utiliza el paro físico del equipo.
 ┌ ¿Algo no responde? ── [Solicitar revisión técnica] ┐
```
- **Métricas:**
  - «Depósito de agua»: «Con agua» o «Nivel bajo» (de `medicion.deposito_con_agua`) + «Depósito de 19 L · el flotador solo detecta nivel bajo».
  - «Humedad media del sustrato»: promedio de las 3 plantas.
  - «Ambiente»: temperatura en °C y humedad relativa en %.
  - «Lámpara»: «Encendida» o «Apagada» (última `actuacion` de la lámpara) y modo («Automático» o «Apagado manual» si el último comando de lámpara confirmado fue `lampara_apagar`).
- **Plantas:** nombre (`huerto_planta.nombre`), etapa con insignia, «Sembrada hace N días» si hay fecha, humedad de su última `medicion_planta` e insignia «Seca» (ámbar) si baja del umbral de pantalla (35 %, solo visual: los umbrales reales están en el ESP32). «Ver planta» → 4.4.
- **Resumen de IA:** último `ia_resumen` del huerto; «Ver anteriores» abre una lista de los últimos 30 días. Si no hay: «El resumen aparecerá cuando tu equipo haya enviado lecturas.». Etiqueta fija «Generado con IA · no sustituye tu revisión».
- **Acciones:**

| Botón | Variante | Hace | Confirmación | Base |
|---|---|---|---|---|
| «Registrar recarga» | Secundaria | registra el cuidado del depósito | no (acción reversible por admin) | `cuidado` tipo `rellenar_deposito` |
| «Registrar un cuidado» | Secundaria | va a `#mantenimiento` con el formulario abierto | — | — |
| «Revisar mi equipo» | Secundaria | inicia el autodiagnóstico y abre su tarjeta (3.7) con estado (3.3) | no | `comando` `autodiagnostico` |
| «Apagar lámpara» / «Restaurar automático» | Secundaria | orden a la lámpara | **sí** («¿Apagar la lámpara? Se enviará la orden a tu equipo. Volverá a encenderse según su horario cuando restaures el modo automático.») | `comando` `lampara_apagar` / `lampara_automatico` |
| «Solicitar revisión técnica» | Primaria | va a `#soporte` | — | — |

- **Estados:** cargando (esqueleto); error con «Reintentar»; equipo desconectado → métricas con la última lectura y su fecha en gris, más el aviso «Tu equipo está desconectado. Revisa su corriente y tu Wi-Fi.»; sin lecturas aún → «Esperando la primera lectura de tu equipo».

### 4.2 Crear huerto — `#huerto/nuevo` (NUEVA)
- Tarjeta centrada:
```
 Crea tu huerto
 Ponle un nombre para reconocerlo. Podrás cambiarlo después.
 Nombre del huerto (opcional)   [ Mi huerto            ]   (máx. 60)
 Tu huerto tendrá 3 plantas de chile habanero. Disponible solo en Yucatán.
 [ Crear huerto ]   Cancelar
```
- Al crear → va directo a 4.3 (vincular equipo).
- Errores de la base traducidos: «Máximo 3 huertos activos» → «Ya tienes 3 huertos. Archiva uno para crear otro.»; «sin equipo» → «Ya tienes un huerto sin equipo. Vincúlalo antes de crear otro.».
- **Base:** `INSERT huerto` (la base crea las 3 plantas).

### 4.3 Vincular equipo — `#huerto/vincular` (NUEVA, asistente de 3 pasos)
Indicador de pasos arriba: `① Código ─ ② Conecta tu equipo ─ ③ Listo`.

**Paso 1 · Código** — «Genera el código que escribirás en tu equipo. Vence en 10 minutos y solo sirve una vez.» → botón «Generar código» → pantalla de código grande (3.8) con el formato **8 caracteres `XXXX-XXXX`** (alfabeto sin letras confusas) y botón «Ya lo tengo, continuar».

**Paso 2 · Conecta tu equipo** — instrucciones numeradas con ilustración y el código visible a un lado:
1. «Enchufa tu equipo El Chilito. Si ya lo habías configurado, mantén presionado su botón de configuración hasta que la pantalla lo indique.»
2. «En tu celular o computadora, conéctate a la red Wi-Fi **Huerto-Setup-XXXX** con la contraseña de la etiqueta del equipo.»
3. «Abre **192.168.4.1** en tu navegador.»
4. «Escribe el nombre y la contraseña de tu Wi-Fi y este código: **XXXX-XXXX**.»
5. «Vuelve aquí: veremos cuando tu equipo quede conectado.»

Mientras tanto, estado en vivo «Esperando a tu equipo… (vence en 8:15)» (consulta cada 5 s el estado del código y del equipo). Botones: «Generar otro código» (cancela el anterior) y «Cancelar».

**Paso 3 · Listo** — «¡Tu equipo quedó vinculado!», identificador del equipo y botón «Ir a mi huerto».

- **Errores visibles:** código vencido → «El código venció. Genera otro.»; el equipo lo rechazó (lo informa el backend) → «Tu equipo no pudo usar el código. Revisa que lo escribiste bien o genera otro.». Ayuda plegable «¿Problemas para conectar?» con los casos de la guía «sin-lecturas» y un enlace a Soporte.
- **Base:** `INSERT codigo_vinculacion`; el paso 2 consulta `codigo_vinculacion.estado` y `dispositivo.huerto_id`; la vinculación la hace el endpoint del ESP32 con `chilito_vincular_dispositivo`.

### 4.4 Ficha de planta — `#huerto/plantas/<n>` (NUEVA)
```
 ← Mi huerto
 Planta 1 · «Chilito feliz»                 [Editar]
 Etapa: Floración (desde el 3 mar)  ·  Sembrada el 10 ene (hace 64 días)
 ┌ Humedad del sustrato ─ 1 h | 24 h | 7 días | 30 días ┐   gráfica
 ┌ Línea de vida ───────────────────────────────────────┐
 │ ● Floración · 3 mar   ● Crecimiento · 2 feb   ● Germinación · 10 ene │
 ┌ Cuidados de esta planta ────────────── [Registrar cuidado] ┐
 │ Cosecha · 12 chiles · ayer   Sustrato · hace 5 días …      │
 ┌ Riego ───────────────────────── [Regar esta planta] ┐
 │ Último riego: automático, 8 s, hace 3 h              │
```
- **Editar** (diálogo): «Nombre de la planta» (máx. 40), «Fecha de siembra» (calendario, no futura), «Etapa» (selector: Sin sembrar, Germinación, Plántula, Crecimiento, Floración, Fructificación) con la ayuda «Al cambiar la etapa, guardamos la fecha de hoy en su línea de vida.».
- **«Regar esta planta»** → diálogo con duración (selector 5, 8, 10, 15 o 20 s; por defecto 8) y la advertencia «Si el depósito no tiene agua, tu equipo no regará.» → tarjeta de orden (3.3).
- **Base:** `huerto_planta`, `huerto_planta_etapa`, `medicion_planta` (detalle de 90 días) y `resumen_hora_planta` (7 y 30 días), `cuidado` filtrado por planta, `actuacion` (bomba de esa planta) y `comando` `regar`.

### 4.5 Panel técnico — `#telemetria`
```
 Panel técnico · <huerto>         ● En línea …
 ┌SHT31 · Ambiente┐┌BH1750 · Luz┐┌Flotador┐┌Conexión┐
 Histórico   1 h | 24 h | 7 días | 30 días
 ┌Humedad del sustrato (3 líneas, una por planta)┐┌Temperatura┐
 ┌Humedad relativa┐┌Luz (lux)*┐                  (*solo si el equipo la envía)
 Lecturas por planta   tabla: Planta · Humedad % · ADC (0–4095) · Hora
 Bitácora del equipo   pestañas: Órdenes | Actuaciones | Eventos
 ┌ Regar una planta ── [Planta ▾] [Duración ▾] [Regar] ┐
```
- **Tarjetas:** «Ambiente · SHT31» (°C y % HR); «Luz · BH1750» (lux; si nunca llegó, la tarjeta no se muestra); «Flotador» («Con agua» o «Nivel bajo» + «Depósito de 19 L»); «Conexión» (estado, última conexión y firmware).
- **Histórico:** 1 h y 24 h desde `medicion`; 7 y 30 días desde `resumen_hora_*` (promedio con banda mínima y máxima). Las 3 plantas en una gráfica con leyenda («Planta 1», etc., con su nombre).
- **Lecturas por planta:** tabla con humedad % **y ADC crudo** (para calibración y soporte).
- **Bitácora:** «Órdenes» (`comando`: fecha, orden, origen «Tú» o «Soporte», estado 3.3), «Actuaciones» (`actuacion`: riegos por planta con duración, lámpara y ventilador; origen «Automático», «Tú» o «Soporte») y «Eventos» (`dispositivo_evento`: conectado, desconectado, error, reinicio, firmware). Paginadas de 25 en 25.
- **Regar:** selector de planta + duración → confirmación → orden.
- **Estados:** sin lecturas en el periodo → gráfica vacía con «Aún no hay registros para este periodo.».

### 4.6 Mantenimiento — `#mantenimiento`
```
 Mantenimiento · <huerto>
 ┌ Registrar un cuidado ───────────────────────────────────────┐
 │ ¿Qué hiciste? [Rellenar depósito ▾]  ¿En qué planta? [— ▾]   │
 │ ¿Cuándo? [Hoy ▾ / calendario, hasta 7 días atrás]            │
 │ Chiles cosechados (opcional) [   ]   ← solo si es cosecha    │
 │ [ Registrar ]                                                │
 └──────────────────────────────────────────────────────────────┘
 Accesos rápidos: [Rellené el depósito] [Registrar cosecha] [Revisé el sustrato]
 Historial   filtros: Planta | Tipo | Fechas
   fecha · tipo · planta · detalle · «Corregido por soporte» / «Anulado» (insignias)
 Guía de cuidado y preguntas frecuentes (acordeón, igual que hoy)
```
- **Reglas del formulario (las de la base):** «Rellenar depósito» oculta la planta (es del huerto); «Sustrato», «Germinación» y «Cosecha» exigen planta; «Inspección» permite «Todo el huerto» o una planta; la fecha va de 7 días atrás a ahora; los chiles solo en cosecha (0 a 999).
- **Historial:** muestra el tipo y la planta **vigentes**, aplicando las correcciones de `cuidado_revision`. Los anulados aparecen tachados con la insignia «Anulado» y el motivo al desplegar.
- **Accesos rápidos:** registran con la fecha de ahora y abren el selector de planta si hace falta.
- **Base:** `cuidado`, `cuidado_revision`, `guia_cuidado`.

### 4.7 Soporte técnico — `#soporte` (rediseñada, sin token)
**Sin caso activo:**
```
 Soporte técnico · <huerto>
 ┌ 1 · Revisa tu equipo ─────────────────────────────┐
 │ Comprueba sensores, bombas, lámpara y conexión.     │
 │ [ Revisar mi equipo ]   Última revisión: hace 2 días · Encontramos 1 problema │
 │ (tarjeta de autodiagnóstico 3.7)                    │
 ┌ 2 · Solicita una revisión técnica ─────────────────┐
 │ ¿Qué problema tiene? [La bomba no responde ▾]       │
 │ Cuéntanos más (opcional) [                     ] 500│
 │ ☐ Adjuntar la última revisión de mi equipo          │
 │ ☐ Autorizo al equipo de soporte a revisar mi equipo │
 │   durante 24 horas. Puedo revocarlo cuando quiera.  │
 │ [ Solicitar revisión ]                              │
 Historial de solicitudes
```
**Con caso activo** (sustituye el formulario):
```
 ┌ Caso CS-1A2B3C4D · La bomba no responde ─────────── En espera / En revisión ┐
 │ Autorización vigente · vence en 18 h 42 min                                  │
 │ (si en revisión) «<Alias del admin o “Soporte”> está revisando tu equipo»    │
 │ Lo que soporte ha hecho:  10:42 Reinició el equipo · Confirmada              │
 │                           10:45 Probó la bomba 3 (3 s) · Falló               │
 │ [ Revocar acceso ] (Peligro)    [ Cancelar solicitud ] (Secundaria)          │
 └──────────────────────────────────────────────────────────────────────────────┘
```
- **Confirmaciones:** «¿Revocar el acceso de soporte? Soporte dejará de ver y controlar tu equipo de inmediato. Tu caso seguirá abierto.» / «¿Cancelar tu solicitud? Se cerrará el caso y se revocará el acceso.».
- **Resuelto:** tarjeta «Tu caso se resolvió · Resultado: Problema solucionado · nota de soporte».
- **Base:** `comando`/`autodiagnostico`/`autodiagnostico_revision`, `soporte_caso` (insertar, revocar y cancelar) y `comando` con origen `soporte` (lo hecho por soporte).

### 4.8 Avisos — `#avisos` (centro de notificaciones)
```
 Avisos                                   [Marcar todo como leído]
 Filtros: Todos | No leídos | Mi equipo | IA | Soporte | Legales
 ● CRÍTICO · Depósito sin agua · Mi huerto de casa · hace 10 min     →
 ○ Tu equipo quedó vinculado · hace 2 días                            →
 ○ Actualizamos los términos (versión 1.1) · hace 3 días              →
```
- Cada fila: punto de no leído, insignia de severidad (Crítico rojo, Advertencia ámbar, Información gris), título, huerto (si aplica), tiempo relativo. Al pulsar, se marca como leída y abre `enlace` (o `#avisos/<id>` si no tiene).
- Detalle `#avisos/<id>`: título, texto, fecha, huerto y botón «Ir» al enlace. Los críticos del equipo muestran «Marcar como resuelto».
- **Base:** `notificacion` (marcar `leida_en` y `resuelta_en`).

### 4.9 Mi cuenta — `#cuenta`
Pestañas: **Perfil · Mis huertos (nueva) · Seguridad · Privacidad**.
- **Perfil:** igual que hoy (datos de la cuenta, datos personales, tu sesión).
- **Mis huertos** (nueva): una tarjeta por huerto con nombre (editable), equipo vinculado (identificador, estado y desde cuándo) y acciones «Renombrar», «Desvincular equipo» (Peligro; confirmación: «¿Desvincular el equipo <id>? Dejará de enviar lecturas a este huerto. Para volver a usarlo tendrás que vincularlo de nuevo.») y «Archivar huerto» (solo sin equipo; confirmación: «¿Archivar <nombre>? Dejarás de verlo. Su historial se conserva.»). Botón «Crear otro huerto» con los límites de 3.1.
- **Seguridad:** igual que hoy, pero «Desactivar», «Quitar» y «Generar códigos nuevos» piden confirmación.
- **Privacidad:** «Mis datos» (igual) + «Estadísticas de este navegador» (igual) + **«Documentos que aceptaste»** (nueva: lista de tus aceptaciones con documento, versión y fecha, de `privacidad_decision`) + **«Eliminar mi cuenta»** (nueva, abajo, tarjeta con borde rojo suave):
  - Sin solicitud: «Borraremos tus datos personales 15 días después de pedirlo. Tus equipos quedarán libres y tus huertos se archivarán. Puedes cancelarlo antes de que pase el plazo.» → botón Peligro «Eliminar mi cuenta» → diálogo que pide **escribir tu contraseña** y confirma: «¿Eliminar tu cuenta? Se borrará el <fecha+15 días>.».
  - Con solicitud: aviso ámbar fijo en todas las pantallas («Tu cuenta se eliminará el <fecha>. [Cancelar eliminación]») y aquí el botón «Cancelar eliminación».

---

## 5. Pantallas de administración

> Todas exigen su capacidad **y** segundo factor fuerte (como hoy). Encabezado común: título + subtítulo + barra de acciones a la derecha. Tablas con búsqueda, filtros y **paginación visible** (25 por página).

### 5.1 Telemetría de flota — `#admin/flota`
```
 Telemetría de flota
 ┌Equipos vinculados┐┌En línea┐┌Desconectados┐┌Problemas (24 h)┐
 ┌Humedad media del sustrato · 7 días┐┌Temperatura media · 7 días┐
 Equipos   búsqueda: identificador o correo · filtros: Estado | Conexión
  Identificador · Huerto · Dueño · Conexión · Última lectura · Firmware · Última revisión
 ┌ Problemas recientes ───────────────────────────────────────┐
 │ Autodiagnósticos con fallas · órdenes fallidas · equipos desconectados >24 h │
```
- **Quitar:** «Evaporación estimada», «Telemetría para evaluación de IA», «Correlaciones por temperatura», «Vida mediana del sensor» y «Órdenes de mini bombas»: no tienen fuente.
- **Base:** `v_estado_equipos`, `resumen_hora_huerto` y `resumen_hora_planta` (agregados de todos los huertos), `autodiagnostico` y `comando` fallidos.
- Fila → abre el detalle del equipo del Inventario (5.5) si la cuenta tiene `gestionar_dispositivos`; si no, un panel lateral de solo lectura.

### 5.2 Consola remota — `#admin/soporte` (rediseñada, sin token)
```
 Consola remota
 Pestañas: Nuevos (3) | En atención | Resueltos      [Actualizar]
 ┌Bandeja (izquierda, 40 %)────────┐┌Detalle (derecha, 60 %)──────────────────────┐
 │ CS-1A2B · Bomba · hace 5 min    ││ Caso CS-1A2B3C4D · Nuevo                     │
 │  ana@… · ESP32-A1B2 · 23 h rest.││ Persona: Ana López · ana@example.com         │
 │ CS-9F8E · Conexión · hace 1 h   ││ Huerto: Mi huerto de casa · Equipo ESP32-A1B2│
 └─────────────────────────────────┘│ Problema: La bomba no responde · Nota: «…»   │
                                    │ Autorización: vigente · vence en 23 h 10 min │
                                    │ Autodiagnóstico adjunto (3.7)                │
                                    │ [ Atender ]                                  │
                                    └──────────────────────────────────────────────┘
```
- **«Atender»** (Primaria) → el caso queda a tu nombre (`en_atencion`); otros admins ven «Lo atiende <correo>».
- **«Conectar»** (Primaria, tras atender) → abre la sesión técnica:
```
 ┌ Sesión técnica · ESP32-A1B2 · abierta hace 2 min ───────── [Cerrar sesión técnica] ┐
 │ Estado: ● En línea · firmware 1.0.3 · última lectura hace 1 min                   │
 │ Lecturas actuales: Ambiente 29.5 °C / 71 % · Luz 18 000 lx · Depósito con agua   │
 │   Planta 1 41 % (ADC 2710) · Planta 2 38 % (2802) · Planta 3 55 % (2190)          │
 │ Acciones: [Pedir lectura] [Revisar equipo] [Probar bomba ▾] [Lámpara ▾]          │
 │           [Ventilador ▾] [Reiniciar equipo]                                      │
 │ Órdenes de esta sesión (3.3) · Eventos recientes del equipo (últimas 24 h)       │
 └───────────────────────────────────────────────────────────────────────────────────┘
 Resolver el caso: Resultado [▾]  Nota (obligatoria si «Otro»)  [ Resolver caso ]
```
- **Confirmaciones:** «Reiniciar equipo» («El equipo dejará de responder unos segundos.»), «Probar bomba» (eligiendo planta y duración, 1 a 5 s) y «Resolver caso» («Se cerrará el caso y terminará el acceso. No se puede deshacer.»).
- **En vivo:** si la persona revoca, la sesión se cierra sola y aparece el aviso «La persona revocó el acceso. La sesión se cerró.» (comprobación cada 10 s). Al salir de la pantalla se cierra la sesión técnica (como hoy).
- **Base:** `soporte_caso`, `soporte_sesion`, `comando` (origen `soporte`), `medicion`, `medicion_planta`, `dispositivo_evento`, `autodiagnostico`.

### 5.3 Mantenimientos — `#admin/mantenimientos`
- Igual estructura que hoy, pero:
  - **todos los huertos** (sin asignaciones);
  - búsqueda por **correo del dueño o nombre del huerto**;
  - filtros Huerto, Planta, Tipo, Estado y fechas;
  - paginación visible.
- La corrección permite cambiar **tipo, planta y chiles**, siempre con motivo. «Anular registro» pide confirmación.
- El formulario «Registrar intervención» se mantiene (huerto + planta + tipo + fecha).
- **Base:** `cuidado`, `cuidado_revision`.

### 5.4 Solicitudes del producto — `#admin/solicitudes`
Sin cambios de estructura (funciona bien). Solo: «Archivar» pide confirmación, se añaden la búsqueda por correo y la estética de insignias (C4). **Base:** `consulta_producto`, `correo_pendiente`.

### 5.5 Inventario de equipos — `#admin/equipos` (NUEVA)
```
 Inventario de equipos                                   [ + Dar de alta equipo ]
 ┌Disponibles┐┌Vinculados┐┌Retirados┐
 búsqueda: identificador, MAC o correo · filtros: Estado | Conexión | Vendido
  Identificador · MAC · Estado · Huerto · Dueño · Conexión · Venta · [Ver]
```
- **Alta** (diálogo): «Identificador» (p. ej. `ESP32-A1B2`), «MAC» (`AA:BB:CC:DD:EE:FF`) y «Firmware» (opcional). Al guardar, Django **genera la credencial MQTT** y la muestra **una sola vez** con el componente 3.8 («Grábala en el equipo ahora. No se volverá a mostrar.»). En la base solo queda su hash.
- **Detalle del equipo** (página `#admin/equipos/<id>`):
  - ficha: estado, conexión, firmware, alta y quién;
  - huerto y dueño actuales;
  - venta vigente (con enlace a Ventas);
  - **historial** de `dispositivo_evento` (alta, vinculado, desvinculado, conexiones, errores…);
  - últimos autodiagnósticos.
  - Acciones: «Desvincular» (Peligro, confirmación), «Rotar credencial» (confirmación: «El equipo dejará de conectarse hasta que grabes la nueva credencial.») y «Retirar equipo» (Peligro, solo si está disponible: «Es definitivo.»).
- **Base:** `dispositivo`, `dispositivo_evento`, `v_estado_equipos`, `venta`, `chilito_desvincular_dispositivo`.

### 5.6 Ventas — `#admin/ventas` (NUEVA; sustituye la maqueta)
Pestañas: **Ventas · Resumen**.
- **Ventas:** tabla con equipo, comprador, municipio, fecha, precio, **pago** (insignia Pendiente/Parcial/Completo y «$1 000 de $3 500»), entrega (Por entregar con fecha prevista / Entregada) y estado (Vigente/Cancelada). Filtros: fechas, pago, entrega, municipio y búsqueda.
- **«+ Registrar venta»** (página o diálogo grande):

| Campo | Tipo | Regla |
|---|---|---|
| Equipo | selector de equipos sin venta vigente y no retirados | obligatorio |
| Nombre del comprador | texto ≤120 | obligatorio |
| Correo del comprador | correo ≤254 | obligatorio; si existe una cuenta con ese correo, se enlaza (aviso «Cuenta encontrada») |
| Municipio | selector con los municipios de Yucatán | obligatorio |
| Precio total (MXN) | número > 0, 2 decimales | obligatorio |
| Importe recibido (MXN) | 0…precio | por defecto 0 |
| Referencia del pago | texto ≤120 | opcional |
| Modalidad de entrega | Entrega a domicilio / Recogida acordada | obligatorio |
| Fecha de venta | calendario, no futura | obligatorio |
| Fecha prevista de entrega | calendario ≥ venta | opcional |
| Nota | ≤500 | opcional |

- **Detalle de venta:** «Registrar pago» (nuevo importe acumulado y referencia), «Marcar entregada» (fecha), «Editar nota» y «Cancelar venta» (Peligro, confirmación).
- **Resumen:** periodo (Este mes, Mes anterior, Todo o Personalizado) → tarjetas «Ventas», «Importe vendido», «Cobrado» y «Por cobrar»; tabla por municipio. Sin «Ganancias» (no hay costos en la base).
- **Base:** `venta` (con `estado_pago` calculado), `dispositivo`.

### 5.7 Guías de cuidado — `#admin/guias`
Igual que hoy (funciona bien). Solo: «Publicar» y «Retirar» piden confirmación, y estética C1 a C4.

### 5.8 Textos legales — `#admin/legales` (NUEVA)
```
 Textos legales
 Pestañas: Términos y condiciones | Aviso de privacidad | Política de cookies
 ┌ Versión vigente: 1.1 · publicada el 14 nov 2026 por rafael@… · huella a3f9…  [Ver] ┐
 ┌ Borradores ─────────────────────────────────────────── [ + Nueva versión ] ┐
 │ 1.2 · editado hace 1 h por …    [Editar] [Vista previa] [Publicar] [Eliminar] │
 Historial de versiones publicadas: 1.1 · 1.0 (cada una: fecha, quién, [Ver])
```
- **Editor** (página `#admin/legales/<id>`): «Versión» (formato `1.2`, debe ser mayor que la vigente), «Título», «Contenido» (texto con formato sencillo: títulos, listas, negritas y enlaces, con barra mínima) y vista previa lado a lado tal como la verán las personas. Botones «Guardar borrador», «Vista previa» y «Publicar».
- **Publicar** → confirmación fuerte: «¿Publicar la versión 1.2 de Términos y condiciones? Todas las cuentas recibirán un aviso y deberán aceptarla al entrar. Una versión publicada no se puede editar ni borrar.» (para cookies: «…deberán volver a decidir sobre cookies»).
- **Base:** `documento_legal`, `v_documento_legal_vigente`. La página pública (6.2) muestra la vigente.

### 5.9 Bitácora de consentimientos — `#admin/consentimientos` (NUEVA)
```
 Bitácora de consentimientos                           [Exportar CSV]
 filtros: Documento (Términos | Aviso | Cookies) · Decisión (Aceptó | Rechazó)
          · Fechas · Buscar correo · Versión
  Fecha y hora (Mérida) · Cuenta · Qué · Versión · Decisión · IP · Navegador
  14 nov 2026 18:02 · ana@example.com · Términos y condiciones · 1.1 · Aceptó · 189.203.45.0 · Chrome 130 · Android
  14 nov 2026 17:55 · Visitante anónimo · Cookies · 1.0 · Rechazó · 201.141.12.0 · Safari 18 · iPhone
```
- Al pulsar una fila: panel con todos los datos y, si es una cuenta, el historial completo de esa cuenta.
- Tarjetas arriba: «Aceptaciones de la versión vigente: N de M cuentas» (términos y aviso) y «Estadísticas: % de navegadores que aceptaron».
- **Exportar CSV** del filtro actual (se audita como `exportar_consentimientos`).
- **Base:** `v_bitacora_consentimientos` (solo lectura).

### 5.10 Administradores — `#admin/administradores` (NUEVA, solo super admin)
Pestañas: **Administradores · Historial · Actividad**.
- **Administradores:** tabla de `v_administradores` (correo, nombre, capacidades como insignias, ★ super admin, segundo factor ✔/✖ y último acceso) + botón «+ Dar acceso a una cuenta».
- **Dar o editar acceso** (diálogo): «Correo de la cuenta» (debe existir y estar verificada) + **casillas de las 9 capacidades** con su descripción, agrupadas en Operación (Flota, Soporte, Mantenimientos), Gestión (Consultas, Equipos, Ventas, Guías) y Legal (Textos legales, Consentimientos) + «Motivo» (obligatorio, ≤300). La casilla de super admin **no aparece** (aviso: «La capacidad de super administrador solo se asigna desde la base de datos.»). Tu propia fila no es editable.
  - Confirmación: «Darás: Soporte, Ventas. Quitarás: Flota. ¿Continuar?».
- **Historial:** `v_capacidad_historial` con filtros por cuenta, capacidad y fechas.
- **Actividad:** `auditoria` filtrada por administrador (fecha, acción, sobre qué y resultado).
- **Base:** `cuentas_usuario_user_permissions` (con actor y motivo), `v_administradores`, `v_capacidad_historial`, `auditoria`.

---

## 6. Parte pública y acceso

| Pantalla | Cambio |
|---|---|
| Portada | Sin cambios de diseño. Revisar textos: «5 sensores» (con el BH1750 opcional pueden ser 6; decisión de contenido) y «Asistente IA previsto» (ya habrá resúmenes de IA en el panel). |
| **Textos legales** (`#terminos`, `#privacidad`, `#cookies`) | Muestran la **versión vigente de la base** con su número y fecha: «Versión 1.1 · vigente desde el 14 nov 2026». Si no hay ninguna publicada: «Documento en preparación». Se elimina la lectura de `frontend/legales/*.html`. |
| Registro | Sin cambios visuales. Las casillas enlazan a la versión vigente y en las etiquetas aparece el número de versión («Acepto los Términos y condiciones (versión 1.1)»). |
| Acceso, verificación, segundo paso, recuperar | **Sin cambios.** Tras iniciar sesión, si hay aceptaciones pendientes → `#aceptar-legales` (4.0). |
| Aviso de cookies | Sin cambios visuales. El backend añade IP recortada y navegador a la decisión. |
| «Consíguelo» | Sin cambios. |

---

## 7. Mapa pantalla → base de datos

| Pantalla | Lee | Escribe |
|---|---|---|
| 4.0 Aceptar legales | `chilito_aceptaciones_pendientes`, `documento_legal` | `privacidad_decision` |
| 4.1 Mi huerto | `huerto`, `huerto_planta`, `dispositivo`, `medicion`, `medicion_planta`, `actuacion`, `ia_resumen`, `comando` | `cuidado`, `comando` |
| 4.2 Crear huerto | — | `huerto` |
| 4.3 Vincular | `codigo_vinculacion`, `dispositivo` | `codigo_vinculacion` |
| 4.4 Planta | `huerto_planta`, `huerto_planta_etapa`, `medicion_planta`, `resumen_hora_planta`, `cuidado`, `actuacion` | `huerto_planta`, `comando` |
| 4.5 Panel técnico | `medicion`, `medicion_planta`, `resumen_hora_*`, `comando`, `actuacion`, `dispositivo_evento` | `comando` |
| 4.6 Mantenimiento | `cuidado`, `cuidado_revision`, `guia_cuidado` | `cuidado` |
| 4.7 Soporte | `soporte_caso`, `autodiagnostico*`, `comando` | `comando`, `soporte_caso` |
| 4.8 Avisos | `notificacion` | `notificacion` (leída, resuelta) |
| 4.9 Mi cuenta | `cuentas_usuario`, `huerto`, `dispositivo`, `privacidad_decision`, `mfa_authenticator` | `cuentas_usuario`, `huerto`, `chilito_desvincular_dispositivo` |
| 5.1 Flota | `v_estado_equipos`, `resumen_hora_*`, `autodiagnostico`, `comando` | — |
| 5.2 Consola | `soporte_caso`, `soporte_sesion`, `medicion*`, `dispositivo_evento`, `autodiagnostico*`, `comando` | `soporte_caso`, `soporte_sesion`, `comando` |
| 5.3 Mantenimientos | `cuidado`, `cuidado_revision`, `huerto`, `cuentas_usuario` | `cuidado`, `cuidado_revision` |
| 5.4 Solicitudes | `consulta_producto`, `correo_pendiente` | `consulta_producto` |
| 5.5 Equipos | `dispositivo`, `dispositivo_evento`, `v_estado_equipos`, `venta` | `dispositivo`, `chilito_desvincular_dispositivo` |
| 5.6 Ventas | `venta`, `dispositivo`, `cuentas_usuario` | `venta` |
| 5.7 Guías | `guia_cuidado` | `guia_cuidado` |
| 5.8 Legales | `documento_legal` | `documento_legal` |
| 5.9 Consentimientos | `v_bitacora_consentimientos` | `auditoria` (exportar) |
| 5.10 Administradores | `v_administradores`, `v_capacidad_historial`, `auditoria` | `cuentas_usuario_user_permissions` |

---

## 8. Orden de construcción

| Fase | Contenido | Por qué en este orden |
|---|---|---|
| **1. Base y Django** | Instalar la base v2, modelos y migraciones `--fake`, middleware de actor, publicar textos legales | Sin esto nada funciona |
| **2. Sistema visual** | `tokens.css`, botones C1 y C2, campos C3, insignias C4, toast C5, confirmación 3.6 | Todas las pantallas nuevas los usan |
| **3. Flujo principal del usuario** | 4.0, 4.1 (A, B y C), 4.2, 4.3, 4.4, 4.9 «Mis huertos» | Es el camino crítico: cuenta → huerto → equipo |
| **4. Operación del usuario** | 4.5, 4.6, 4.7, 4.8 | Requieren datos de equipo (simulados con el rol IoT hasta la fase IoT) |
| **5. Administración nueva** | 5.5, 5.10, 5.8, 5.9, 5.6 | Inventario antes que ventas; super admin pronto para delegar |
| **6. Administración adaptada** | 5.1, 5.2, 5.3, 5.4, 5.7 | Cambios sobre pantallas existentes |
| **7. Limpieza** | Quitar `!important` y reglas muertas, eliminar `legales/*.html`, `#admin/vinculacion` y `#admin/comercial` | Al final, cuando todo usa los tokens |

> Para probar las fases 4 y 6 sin ESP32 real: un pequeño script que, con el rol `chilito_pkg_iot`, inserte mediciones, actuaciones y respuestas a comandos de un equipo de prueba.

---

## 9. Decisiones tomadas y preguntas abiertas

### Decidido en este plan
1. El estilo del panel se conserva; se unifican botones, campos, insignias, avisos y confirmaciones (1.3).
2. Código de vinculación: **8 caracteres `XXXX-XXXX`** (alfabeto sin letras confusas), en lugar de los 26 actuales, porque se escribe a mano en el portal del ESP32. Su seguridad la dan los 10 minutos, el uso único, la credencial del equipo y el límite de intentos por equipo en el backend.
3. Telemetría de flota sin métricas inventadas.
4. Umbral visual de «planta seca»: 35 % (solo para la insignia; el riego lo decide el ESP32).
5. Duraciones de riego para la persona: 5, 8, 10, 15 o 20 s; para la prueba de soporte, 1 a 5 s.

### Preguntas abiertas para el responsable
1. **Portada:** ¿«5 sensores» pasa a «6 sensores» si el BH1750 se queda? ¿Se mantiene «Asistente IA previsto» o se cambia por «Resúmenes con IA»?
2. **Admin de soporte:** cuando atiende un caso, ¿la persona ve el **alias** del admin o solo «Soporte»? (propuesta: solo «Soporte»).
3. **Exportar CSV** de la bitácora de consentimientos: ¿lo quieres desde el panel? (propuesta: sí, auditado).
4. **Municipios de Yucatán** en ventas: ¿lista completa de los 106 municipios o solo los que atienden hoy (Mérida, Progreso, Kanasín, Umán…)?

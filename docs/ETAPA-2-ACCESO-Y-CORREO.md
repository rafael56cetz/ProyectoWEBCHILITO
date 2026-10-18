# Etapa 2 — Acceso, sesión y correo real

Fecha: 17-10-2026. Carpeta activa: `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`.
Se trabajó sobre main, HEAD `f5605359cdff0fb596a63cfc0c352026fb5060e2`, conservando los cambios locales previos. Sin commit, push, publicación, capturas ni tareas de Notion.

## Estado de la entrega

Implementados: arranque con Django en el mismo origen, login por correo/contraseña, sesión de servidor/restauración/cierre, perfil de la cuenta, cambio de contraseña, adaptadores de verificación y reenvío de código y recuperación por enlace de allauth. Se retiraron del arranque los seis módulos de desarrollo, el acceso libre, el código visible y el atajo de recuperación. Django tampoco sirve la carpeta desarrollo.

**Registro cerrado** por decisión de Rafael: documentos legales, versiones efectivas y responsable pendientes. El servidor rechaza el alta incluso con aceptación marcada o llamando directamente al endpoint. No se fabrica evidencia legal ni se crea una cuenta. El adaptador allauth conserva un segundo bloqueo. Habilitar el registro requerirá una entrega posterior que incorpore versiones aprobadas y validación/evidencia de aceptación en el servidor.

**Correo real comprobado:** Gmail aceptó un único mensaje de comprobación dirigido exclusivamente a la cuenta autorizada de pruebas; Rafael confirmó su recepción en Recibidos. El mensaje no creó cuentas ni verificó direcciones. Los códigos y enlaces se comprobaron con allauth y correo en memoria únicamente en la base aislada; no se ha recorrido un registro público real cerrado por la dependencia legal.

La base principal conserva un huerto, tres zonas, cero cuentas, cero verificaciones y cero membresías. No existe una contraseña de acceso de muestra. Verificar el correo no asigna un huerto.

## Arranque único

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
```

Abrir [El Chilito](http://127.0.0.1:8766/index.html).
El script espera a PostgreSQL, usa el rol app y sirve el dist original mediante Django en loopback. Detecta el servicio ya iniciado y evita arrancar otro en 8766. Para detener un arranque hecho en esa terminal: Ctrl+C. No usar http.server: no ofrece la API ni la sesión.

Se retiraron únicamente los servidores estáticos identificados como esta misma aplicación. Queda un servidor Django de la aplicación; el servidor temporal de pruebas se cierra al terminar. Los archivos de los adaptadores históricos se preservan en disco, fuera del arranque y de las rutas servidas.

## Organización y archivos

Se conserva MVC del frontend: modelo para transporte/validación, vista para presentación, controlador para coordinación y navegación. Sin otra aplicación visual, framework o sistema de compilación.

### Modificados

| Archivo | Responsabilidad y motivo |
| --- | --- |
| dist/index.html | Misma entrada; sustituye composición de desarrollo por controlador/inicio.js y actualiza versiones de scripts cambiados. |
| dist/modelo/servicio-acceso.js | Transporte del mismo origen, CSRF, traducción del contrato exacto allauth, sesión, logout y validación de respuestas. Sin almacenamiento de credenciales/tokens en navegador. |
| dist/modelo/servicio-aplicacion.js | Perfil real y cierre; comprueba sesión. Huerto sin membresía: unassigned; integración de datos/avisos aplazada: error honesto, sin lista ni mediciones inventadas. |
| dist/modelo/acceso.js | Aclara que formato local no autentica; la política activa se carga del servidor. |
| dist/modelo/privacidad.js | Cierra registro en cliente; autoridad definitiva en servidor. |
| dist/controlador/acceso.js | Retira navegación libre/código/atajos; gestiona verificación pendiente, sesión vencida, CSRF y rechazo legal. |
| dist/controlador/site.js | Guardián asíncrono con sesión del servidor, restauración del proceso de verificación y descarte de respuestas de rutas anteriores. |
| dist/controlador/aplicacion.js | Retira cierre ficticio; conserva coordinación/vistas existentes. |
| dist/vista/acceso.js | Retira código de revisión; correo de verificación vinculado al proceso, solo lectura; estado de comprobación de sesión con componentes existentes. |
| backend/config/urls.py | Expone únicamente endpoints browser autorizados y recursos originales; desarrollo no se sirve. |
| backend/config/settings/base.py | Política de sesión/contraseña/código, CSRF, correo autorizado y límites persistentes con DatabaseCache. |
| backend/config/settings/local.py | Enlaces canónicos de recuperación/verificación del origen local. |
| backend/cuentas/adapters.py | Conserva registro cerrado y añade máximo de contraseña en cambios/altas gestionados por allauth. |
| backend/cuentas/email.py | SMTP Gmail STARTTLS, autorización privada de destinatarios y fallos genéricos sin cuerpos/secretos en logs. |
| backend/cuentas/models.py | Esquema del almacenamiento de cuotas de Django; no duplica identidad/códigos. |
| backend/tests/test_foundation.py | Actualiza comprobaciones de superficie y correo para el arranque real; mantiene pruebas previas. |
| README.md, backend/README.md | Entrada vigente, configuración y reproducción; historial identificado. |
| docs/INTEGRACION-BACKEND.md, docs/CONTRATOS-INTEGRACION-LOCAL.md | Distinguen contrato actual de propuesta histórica. |
| docs/SEGURIDAD-Y-VERIFICACION-LOCAL.md | Evidencia y límites de la verificación de esta etapa. |

### Creados

| Archivo | Responsabilidad |
| --- | --- |
| dist/controlador/inicio.js | Composición única de servicios reales y carga de política del servidor. |
| backend/cuentas/api.py | Configuración pública, perfil propio, contexto seguro de verificación y coordinación de vistas allauth; sin algoritmos propios de credenciales. |
| backend/cuentas/migrations/0002_cuotas_acceso.py | Tabla para Django DatabaseCache/allauth: límites sobreviven al reinicio del proceso. |
| backend/cuentas/management/commands/comprobar_correo_local.py | Un mensaje inocuo al remitente/destinatario privado autorizado; sin alta ni códigos. |
| backend/cuentas/management/__init__.py, backend/cuentas/management/commands/__init__.py | Paquetes del comando administrativo. |
| backend/tests/test_access_integration.py | Contratos positivos/negativos en PostgreSQL aislado. |
| backend/tests/ui_stage2.cjs | Recorridos de navegador sobre las mismas vistas, sin capturas. |
| backend/tools/comprobar_frontend.py | Cuenta fixture solo aislada, servidor temporal, ejecución y limpieza controlada. |
| infra/configurar_correo_local.ps1 | Entrada privada interactiva de contraseña de aplicación; no envía ni sobrescribe configuración existente. |
| infra/iniciar_aplicacion.ps1 | Arranque de Docker/Django, rol app, loopback y detección de puerto ocupado. |
| docs/ETAPA-2-ACCESO-Y-CORREO.md | Esta entrega, contrato ejecutado, responsabilidades y pendientes. |
| docs/EVIDENCIA-ETAPA-2-LOCAL.json | Resultados textuales y huellas, sin secretos/códigos. |

No se cambiaron CSS, imágenes, fuentes, logo, portada, métricas, Blender, compose.yaml ni organización de carpetas ajenas al alcance. La única nueva migración se aplicó con migrador en ambas bases, sin borrar/recrear bases/volúmenes; total 28 migraciones.

## Contrato vigente

Todos los cuerpos son JSON. Cookies del mismo origen; mutaciones con X-CSRFToken obtenido de la cookie, que se vuelve a leer tras rotación de sesión. No JWT ni session_token de aplicaciones.

| Método y ruta | Entrada / respuesta y autoridad |
| --- | --- |
| GET /api/acceso/configuracion | Política pública; registrationAllowed:false, legal.approved:false y versiones null. Establece cookie CSRF; sin secretos. |
| GET /api/cuenta | Solo la cuenta de sesión activa y verificada: status:ready, email, verified:true y gardenAssigned. No admite elegir usuario por parámetros. 401 sin sesión, 403 si verificación revocada. |
| GET /api/acceso/verificacion | Solo metadatos del proceso allauth de esa sesión: email y expiresAt; 409 si venció/no existe. No verifica código ni consume intentos en GET. |
| GET /_allauth/browser/v1/auth/session | 200/meta.is_authenticated:true o 401 con flujos pendientes/anónimo. |
| DELETE /_allauth/browser/v1/auth/session | Invalida sesión; el 401/meta.is_authenticated:false de allauth confirma el cierre. CSRF obligatorio. |
| POST /_allauth/browser/v1/auth/login | email,password. 200 sesión; 401 con verify_email pendiente para cuenta no verificada; 400 credenciales inválidas/límite por clave según código allauth; 429 límite general. |
| POST /_allauth/browser/v1/auth/signup | Siempre 403/code:registration-disabled, sin alta, correo ni aceptación ficticia. |
| POST /_allauth/browser/v1/auth/email/verify | key: código. Lo comprueba allauth contra el proceso de la sesión, sin challengeId propio ni devolución de código. |
| POST /_allauth/browser/v1/auth/email/verify/resend | Sin correo elegido por cliente; usa proceso de sesión. 200 enviado, 429 límite, 409 proceso/cuota no disponible. |
| POST /_allauth/browser/v1/auth/password/request | email. 200 neutral si se pudo atender; 503 si envío/configuración no disponible o destinatario no autorizado, independientemente de que exista cuenta. |
| GET /_allauth/browser/v1/auth/password/reset | X-Password-Reset-Key. 200 válido o 400 inválido/vencido. No token en ruta ni cuerpo de respuesta. |
| POST /_allauth/browser/v1/auth/password/reset | key,password. En éxito, allauth responde 401/meta.is_authenticated:false: la contraseña cambia sin iniciar sesión automáticamente. |
| POST /_allauth/browser/v1/account/password/change | current_password,new_password. Sesión verificada obligatoria; valida contraseña actual/política. Conserva sesión actual rotada; otras sesiones dejan de validar su hash. |

400 con errors/param se traduce únicamente a campos conocidos; errores desconocidos/respuestas incompletas no confirman éxito. 403 CSRF se identifica como csrf-failed y pide recarga; no reintenta automáticamente contraseñas. No se exponen clientes app, social, login por código, gestión de correo/teléfono o WebAuthn.

El enlace de recuperación es `http://127.0.0.1:8766/index.html#restablecer?token={key}`. El controlador retira el token del fragmento al leerlo y lo conserva solo durante esa pantalla. No viaja en logs de URL, localStorage ni query del servidor; la inspección lo envía por cabecera y el cambio por cuerpo.

## Políticas locales y configuración privada

- Contraseña nueva: mínimo 15, máximo 256 caracteres, validadores Django de similitud/comunes/numérica. Acceso normal sigue correo y contraseña.
- Código allauth: seis dígitos generados por biblioteca, diez minutos, tres fallos por proceso, máximo cinco reenvíos por proceso y al menos 60 segundos entre envíos por dirección. Reenviar no reinicia el plazo original ni el contador de fallos; al agotar/vencer se vuelve a iniciar sesión.
- Cuotas allauth: login 30/min/IP y fallos 10/min/IP + 5/300s/clave; recuperación 10/min/IP + 1/60s/dirección; uso de enlace 20/min/IP; cambio 5/min/usuario. La biblioteca devuelve algunos límites de contraseña como error 400/too_many_login_attempts. El frontend muestra espera orientativa de 60s; el servidor decide cuándo permite otro intento.
- Enlace de recuperación: 30 minutos, invalidado tras uso/cambio según allauth/Django. No crea sesión automática ni códigos de login.
- Sesión en PostgreSQL, cookie HttpOnly/SameSite=Lax, límite local ocho horas y cookie de sesión del navegador. Secure=false se limita a HTTP loopback en settings.local; no configuración de producción.
- Códigos, contraseñas, cookies, tokens y respuestas SMTP no se registran en logs. DEBUG=false, sin consola de correo; logs HTTP generales silenciados.
- `%LOCALAPPDATA%\ElChilito\secrets\correo_local.json` contiene remitente/destinatarios autorizados; `gmail_app_password.txt` contiene la contraseña de aplicación. Se cargan en ejecución fuera de Git/OneDrive/dist, con permisos privados. La contraseña normal de Gmail no se usa.
- SMTP `smtp.gmail.com:587`, STARTTLS, tiempo máximo 10s. El backend impide destinatarios fuera de autorización privada antes de abrir conexión. No se habilita distribución general por añadir Gmail.

Rafael configura su cuenta según [Google/contraseñas de aplicación](https://support.google.com/accounts/answer/185833?hl=es) y [Gmail/SMTP](https://support.google.com/mail/answer/7104828?hl=en). La configuración se introduce con el asistente; una actualización futura no debe sobrescribirla sin revisión.

## Verificación actual

- Django: **57 pruebas aprobadas** en la base aislada (34 existentes adaptadas + 23 de integración).
- Navegador Chromium: **64 comprobaciones aprobadas**, anchos 320/390/768/1024/1440, rutas públicas/legales, acceso inválido/válido, guardia directa, restauración, perfil, cambio/cierre, checkbox/error de registro, recuperación, enlace inválido, teclado, movimiento reducido, cuatro destinos, navegación inferior móvil y ausencia de scroll horizontal. Sin errores JavaScript ni carga de desarrollo. Respuestas incompletas de acceso/verificación no producen éxito.
- SMTP: un mensaje aceptado por Gmail; recepción en Recibidos confirmada por Rafael. No se han enviado códigos o enlaces reales de alta a terceros.
- Base principal preservada: 1 huerto, 3 zonas y 0 cuentas/membresías. Aplicación usa rol el_chilito_app sin DDL. Fixtures retiradas de base aislada.
- Fuentes/estilos/imágenes/logo y cambios manuales conservados por huellas respecto al comienzo de esta etapa.
- Sin capturas. Estos resultados son de esta revisión; no se presentan las cifras históricas de la maqueta como pruebas de autenticación.

Reproducir desde backend:

```powershell
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py test --verbosity 1

# Con Playwright/Chromium instalados en este equipo:
$env:NODE_PATH='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\rafae\AppData\Local\ms-playwright'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_frontend.py
```

Las pruebas fuerzan settings.testing/base el_chilito_test y rol el_chilito_test_app; no crean/recrean bases, ni usan SMTP real. La prueba de navegador abre 8768 solo temporalmente para automatización; no es otra aplicación de demostración. No ejecutar pruebas simultáneas sobre esa misma base. El comando comprobar_correo_local envía de verdad y no forma parte de esas baterías.

## Responsabilidades y pendientes

Rafael: backend Django, contratos, correo y decisiones de acceso. Carolina: PostgreSQL/modelo de datos y logo. Rafael y Gabriela: frontend y revisión visual. Kevin no figura como responsable del backend vigente.

Pendientes:
1. Responsable/contacto, aprobación y versiones legales; modelo y validación de aceptación antes de habilitar alta. Registro real, envío de su código y recorrido de bienvenida con una cuenta autorizada siguen bloqueados; no se crean cuentas para sortearlo.
2. Cambiar la cuenta de Gmail provisional por el remitente definitivo cuando Rafael lo decida y actualizar autorización privada. No publicar esa contraseña.
3. Acordar antes de modificar/ocultar navegación cómo presentar funciones aplazadas: ARCO, llaves y Asistente. Conservan accesos existentes y fallos honestos, sin acuses, llaves o IA ficticios. No WebAuthn ni capturas de PIN/biometría.
4. Etapa 3 requiere autorización: persistencia/contratos de datos y avisos. Ninguna lectura, sensor, bombeo o fecha física se inventa o cambia aquí.
5. Etapa 4 requiere autorización: respaldo/restauración aislada, reinicios completos, CI y revisión final. No se ejecutaron en esta etapa. Lectores de pantalla, teléfono físico y revisión jurídica siguen pendientes.

Se aplicaron las habilidades de seguridad solicitadas al hito; los casos trazan R-01, R-02, R-04, R-05, R-06, R-08, R-11 y R-12 de SEGURIDAD-Y-VERIFICACION-LOCAL.md. Se mantienen NIST SSDF 1.1, selección ASVS 5.0.0 y WSTG 4.2; sin declaración de cumplimiento total. No se avanzó automáticamente a Etapa 3.

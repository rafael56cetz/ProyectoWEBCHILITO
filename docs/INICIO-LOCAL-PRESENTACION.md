# Inicio local para la presentación de El Chilito

Revisión: **18 de octubre de 2026**, America/Mexico_City. Presentación: lunes **19 de octubre de 2026**.

Proyecto: C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web.

Se revisaron los archivos actuales, incluidos los cambios manuales de diseño. Solo se autorizó y modificó el procedimiento de inicio y esta documentación. Las pruebas históricas no se utilizaron como evidencia del estado actual.

## Resultado y hallazgos

No se detectaron incidencias que bloqueen la presentación en los recorridos y tamaños comprobados.

- Rama main, HEAD local f560535. Hay modificaciones previas de frontend/documentación y carpetas nuevas sin seguimiento, incluido backend. No se restauró, confirmó ni publicó trabajo.
- No se encontraron AGENTS.md aplicables en el proyecto ni en sus directorios superiores revisados.
- Se inspeccionaron README.md, docs/INTEGRACION-BACKEND.md, entregas vigentes de acceso/huerto/responsividad, configuración local, Compose, pruebas y script de inicio.
- La web local respondió HTTP 200: 30 recursos solicitados, seis hojas CSS analizadas, sin recursos fallidos ni errores JavaScript observados en esa carga.
- Los recorridos aislados comprobaron navegación pública/privada, acceso, registro con código, recuperación por enlace, contraseña, Mi cuenta, Avisos y salida con confirmación.
- La ayuda conserva la palomita y la política de 15 a 256 caracteres. El acceso habitual usa correo y contraseña; el código pertenece a la verificación del registro.
- Con y sin membresía se revisaron plantas, ambiente y depósito. Las mediciones ausentes muestran «—», sin valores o fechas inventados. La cuenta sin membresía ve su estructura genérica; la API sigue rechazando la consulta del huerto con 403 garden-unassigned.
- El diálogo de vinculación abre, enfoca, permite escribir, cancela/Escape, limpia y devuelve el foco. Enviar sigue deshabilitado y no hubo solicitudes durante su uso.
- Se comprobaron sesión, CSRF, rutas privadas, correo verificado, permisos por huerto/aviso y validaciones del servidor.
- Una búsqueda limitada de patrones evidentes de secretos sobre 34 archivos públicos de texto y la diferencia Git no encontró coincidencias. Se revisó la carga privada de configuración del backend. No es una búsqueda exhaustiva ni una certificación de seguridad.

| Hallazgo | Impacto para la presentación | Pasos para reproducir | Archivo o apartado | Recomendación, sin aplicarla a la aplicación |
| --- | --- | --- | --- | --- |
| Conviven instrucciones vigentes e históricas: http.server, registro cerrado, demostración sin backend y recuentos antiguos de cuentas | **Importante, pero permite presentar**: seguir una instrucción histórica puede abrir la web sin API o llevar a una conclusión equivocada | Leer las secciones antiguas de apertura/registro y compararlas con Django y GET /api/acceso/configuracion actual | README.md, backend/README.md y documentación histórica | Usar el comando y esta guía para presentar. Simplificar referencias históricas en una tarea documental posterior |
| No se observaron defectos nuevos en los casos revisados | No se identificó un bloqueo dentro del alcance comprobado | Repetir los recorridos aislados indicados debajo | Aplicación actual y pruebas existentes | Completar la revisión manual en el equipo de presentación |

No se reparó ni rediseñó la aplicación. Las funciones aplazadas de la tabla siguiente no se clasificaron como defectos.

## Implementado y pendiente

| Apartado | Estado actual contrastado con código y pruebas |
| --- | --- |
| Acceso y sesión | Django/allauth; correo/contraseña; sesión del servidor y confirmación al salir |
| Registro local | Habilitado desde esta computadora para correos válidos; casilla obligatoria, código de seis dígitos y confirmación técnica |
| Documentos legales | Contenido/aprobación/versiones pendientes; el endpoint actual informa legal.approved=false. La aceptación local no acredita consentimiento sobre versiones aprobadas |
| Recuperación | Correo con enlace y cambio; probado con transporte de pruebas, sin mensajes reales en esta revisión |
| Huerto y Avisos | Proyección y permisos por cuenta/huerto; avisos y lectura individual según autorización |
| Sin membresía | Dashboard genérico; no asigna automáticamente un huerto ni permite consultar otros |
| Vinculación física y telemetría | Pendientes; formulario visual sin envío. No hay lecturas físicas inventadas |
| IA, ARCO y passkeys | Operaciones aplazadas, con disponibilidad informada por las vistas actuales. Sin WebAuthn, captura biométrica/PIN ni credenciales reales |
| Publicación | No preparada ni realizada; este perfil local no es una configuración de producción |

Rafael conserva backend; Carolina PostgreSQL y logo; Rafael y Gabriela frontend/revisión. No se modificó Notion.

## Pruebas realizadas nuevamente

Las pruebas que escriben utilizan exclusivamente el_chilito_test y el_chilito_test_app. El ejecutor comprueba esa identidad y rechaza privilegios administrativos. TestCase revierte transacciones; las fixtures del navegador se limpian. No se aplicaron migraciones ni se crearon cuentas, sesiones de prueba, membresías o avisos en la base principal. No se instalaron dependencias ni se modificaron pruebas.

| Prueba actual | Resultado |
| --- | --- |
| manage.py test tests --verbosity 1 --settings=config.settings.testing | 127 aprobadas; system check sin incidencias |
| comprobar_frontend.py --etapa 2 | 64 comprobaciones aprobadas |
| comprobar_frontend.py --etapa 3 | 161 aprobadas, incluida navegación y confirmación de salida |
| comprobar_frontend.py --etapa 2 --contrasenas | 75 aprobadas: ayuda, pegado, límites Unicode, recuperación/cambio aislados |
| comprobar_registro_local.py | 81 aprobadas: casilla por teclado, código, sesión y ausencia de membresía automática |
| comprobar_frontend.py --etapa 3 --vinculacion | 172 aprobadas; diálogo sin tráfico y dominio aislado sin cambios |
| comprobar_frontend.py --etapa 3 --responsive | 209 combinaciones de pantalla/estado y tamaño; 0 incidencias y 0 errores JavaScript |
| Lectura concurrente de aviso | Tres aserciones aprobadas en los ejecutores pertinentes |
| Carga real local | HTTP 200, 30 recursos, sin respuestas fallidas observadas; sin enviar formularios |
| SMTP sin mensaje | Configuración privada válida, autenticación Gmail aceptada mediante STARTTLS y certificado validado; sin envío |

Son **553 comprobaciones de navegador**, más las **209 combinaciones responsive**, y **127 pruebas de servidor**.

Tamaños responsive: 320×568, 390×844, 568×320, 844×390, 768×1024, 820×1180, 900×650, 1024×768, 1180×820, 1440×900 y 640×450. Se midieron desbordamientos, elementos cortados, tamaños táctiles, fuentes de campos, títulos ocultos bajo el encabezado, controles enfocados tapados y límites del diálogo. Las pruebas existentes revisaron etiquetas, errores y teclado. El recorrido responsive usa movimiento reducido.

No se generaron capturas, imágenes, videos o trazas visuales. Las herramientas existentes regeneraron resultados textuales ignorados por Git en revision/resultado-responsivo.json y revision/etapaB-navegador.json.

### Límites

- Chromium automatizado con tamaños simulados; falta probar teléfono/tablet físicos y el navegador del profesor.
- No es una auditoría exhaustiva de accesibilidad o seguridad ni acredita cumplimiento íntegro de un estándar.
- SMTP se autenticó sin enviar; no se comprobó recepción de un mensaje nuevo en esta tarea.
- No se ejecutaron carga, fuerza bruta, ataques externos ni servicios futuros.
- No se detuvieron Docker, PostgreSQL o Django activos para simular un inicio en frío.
- Desktop apagado, nuevo Django en segundo plano, parada opcional y ramas de error se revisaron estáticamente; no se ejecutaron para no interrumpir el servicio en uso.
- **El inicio desde una computadora recién encendida no se comprobó**. Hacerlo antes del lunes.
- La vinculación física y las mediciones requieren integración posterior.

## Comando único de inicio

Desde cualquier carpeta de PowerShell:

~~~powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
~~~

URL: **http://127.0.0.1:8766/index.html**

No usar http.server: Django sirve el frontend y la API en el mismo origen.

### Requisitos y funcionamiento

Requiere Windows PowerShell 5.1 o compatible, Docker Desktop/Compose con motor Linux local, imagen PostgreSQL 17, volumen existente el-chilito_pgdata, entorno y dependencias ya preparados, credenciales privadas y migraciones aplicadas. Puertos: 5433 para PostgreSQL y 8766 para Django, ambos en loopback.

El script:

1. Resuelve rutas desde su carpeta y comprueba el Python existente en %LOCALAPPDATA%\ElChilito\venvs\backend\Scripts\python.exe.
2. Verifica cualquier listener de 8766 por comando/procedencia del proceso y, antes de abrir, por contenido servido y contrato del endpoint. Una respuesta HTTP cualquiera no basta.
3. Detecta Docker CLI/Desktop y exige un contexto mediante pipe local de Windows; rechaza motores remotos.
4. Si el motor está apagado, intenta abrir Desktop oculto y espera aproximadamente hasta 120 segundos con consultas acotadas. Si requiere aceptar avisos/configurar WSL, informa para intervenir manualmente.
5. Inicia/espera únicamente db de este Compose, sin recrear el contenedor, descargar imágenes ni crear una base vacía cuando falte el volumen. Espera PostgreSQL saludable.
6. Selecciona config.settings.local, base local y rol app. Comprueba configuración, identidad de conexión y plan de migraciones mediante lectura. **Nunca aplica migraciones**.
7. Comprueba que la configuración privada del correo puede cargarse. Si falta, avisa y permite abrir las funciones que no requieren envío.
8. Reutiliza Django identificado o inicia uno propio oculto en 127.0.0.1:8766 --noreload. Espera aproximadamente hasta 30 segundos por web/endpoint.
9. Comprueba HTTP 200, coincidencia con dist/index.html y GET /api/acceso/configuracion. Solo entonces solicita abrir el navegador predeterminado.
10. Restaura las variables de la terminal llamadora al terminar.

No cambia globalmente la política de ejecución, no pide administración, no abre puertos a Internet ni crea túneles.

Registro saneado: %LOCALAPPDATA%\ElChilito\logs\inicio-local.log. No incluye cuerpos de solicitudes, contraseñas, códigos o respuestas privadas.
Metadatos propios: %LOCALAPPDATA%\ElChilito\runtime\inicio-local.json, con ruta, PID, fecha del proceso y si db se inició en esa ejecución; sin credenciales.

Un comando auxiliar que exceda su tiempo solo retira el proceso temporal creado por el script. Si falla un Django recién iniciado en esa ejecución, se retira exclusivamente ese servidor propio. El inicio no detiene servicios preexistentes.

### Repetición comprobada

Se ejecutó desde carpetas distintas al proyecto con servicios activos, en Windows PowerShell. Las repeticiones reutilizaron el mismo listener Django (PID observado 24040) y contenedor db. Hubo una ejecución completa con solicitud de apertura del navegador predeterminado. La sintaxis final fue validada.

Para repetir sin abrir otra pestaña:

~~~powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1' -NoAbrirNavegador
~~~

Una primera ejecución del borrador devolvió un error genérico. Se reforzaron la espera del motor y el manejo/diagnóstico de auxiliares. Las ejecuciones posteriores pasaron; la causa original no se estableció con certeza. El inicio en frío sigue pendiente.

Dos procesos Python relacionados pueden pertenecer a una sola ejecución. Se comprobó un único listener en 127.0.0.1:8766; no se cerraron procesos por su apariencia de duplicados.

### Errores: acción siguiente

| Servicio o situación | Acción |
| --- | --- |
| Docker no encontrado | Revisar Desktop/CLI; el script no instala dependencias |
| Motor no listo | Abrir Desktop, revisar avisos y WSL; repetir cuando esté listo |
| Contexto remoto | Seleccionar el contexto local adecuado de Desktop |
| Volumen ausente | Revisar preparación/contexto; no borrar o recrear la base para iniciar |
| db no saludable | Consultar docker compose ps y credenciales privadas; conservar el volumen |
| Configuración/rol/conexión | Consultar backend/README.md y manage.py check con perfil local y rol app |
| Migraciones pendientes | Solicitar revisión y aplicación por el procedimiento autorizado; no se aplican al iniciar |
| Puerto 8766 ocupado/no identificado | Identificar su aplicación de origen; no se cierra ni se cambia silenciosamente la URL |
| Correo no disponible | Revisar configuración privada, Internet y Google; usar las demás funciones mientras se resuelve |
| Ejecución bloqueada por PowerShell | Leer la política aplicable y resolver el bloqueo concreto; no desactivar la política global ni elevar permisos por rutina |

## Correo opcional

Django carga correo_local.json y gmail_app_password.txt desde el directorio privado existente bajo %LOCALAPPDATA%\ElChilito\secrets, o las alternativas privadas ya admitidas. No se copiaron valores al proyecto ni se mostraron credenciales.

El inicio **no envía correos** ni garantiza recepción. Se comprobó aparte autenticación Gmail con STARTTLS y validación de certificado, sin mensaje. Recibir el código depende de Internet, credenciales, proveedor y filtros del destinatario; Docker/Django listos no prueban entrega.

Existe el comando real comprobar_correo_local. Actualmente **no acepta destinatario arbitrario**: envía a la cuenta remitente incluida en la configuración privada autorizada, sin crear cuentas ni códigos.

Solo cuando quieras solicitar ese mensaje real a la cuenta de pruebas configurada:

~~~powershell
$env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
$env:ELCHILITO_DB_SCOPE = 'local'
$env:ELCHILITO_DB_ROLE = 'app'
Push-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
try {
    & "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py comprobar_correo_local
} finally {
    Pop-Location
}
~~~

No se ejecutó ese envío durante esta tarea. El éxito significa aceptación por SMTP; confirmar Recibidos/Spam.

Para otra dirección que tú indiques, ampliar el comando administrativo requiere una tarea separada y autorizada. No existe una opción --destinatario. También se puede demostrar manualmente el registro con una dirección autorizada por su propietario, teniendo presente que crea una cuenta local y envía su código. No automatizarlo sobre la base principal.

Si falla, informar la causa comprobada sin revelar respuestas privadas, sin simular verificación o envío.

## Detener sin perder datos

El nuevo inicio deja Django en segundo plano. Cerrar la terminal o usar Ctrl+C después de que el comando haya terminado no lo detiene.

Parada explícita de Django de este proyecto:

~~~powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1' -Detener
~~~

- Para un Django iniciado por el script, comprueba PID, fecha y comando antes de detener su árbol.
- Para uno preexistente, exige identificarlo por proceso/procedencia y contenido servido; la opción pide explícitamente detener ese servidor existente. El inicio normal lo reutiliza.
- Si no puede identificarlo, informa y no cierra procesos ajenos. Para un servidor manual en primer plano, Ctrl+C en su terminal original.
- Esta opción no inicia ni detiene PostgreSQL ni Docker Desktop. **No se ejecutó** porque la aplicación estaba en uso.

PostgreSQL puede permanecer activo. Si deseas detener también solo db:

~~~powershell
docker compose --project-directory 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web' -f 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\compose.yaml' stop db
~~~

Detiene ese servicio tanto si lo inició el script como si ya funcionaba. Conserva el volumen persistente y el siguiente inicio reutiliza los datos. No usar down -v, borrar volúmenes ni detener Docker Desktop completo para cerrar El Chilito. Tampoco se probó esta parada en la revisión.

## Antes de presentar

- Probar el comando después del encendido normal, con margen para Desktop/WSL.
- Confirmar URL y una sola instancia; repasar cuenta, navegación y confirmación de salida.
- Revisar teléfono/tablet físicos y navegador del profesor.
- Tener Internet y un destinatario autorizado para el correo; revisar Recibidos/Spam.
- Si se demuestra registro, utilizar un correo nuevo autorizado y recordar que crea una cuenta real local.
- Presentar vinculación/IA/ARCO/llaves conforme a su disponibilidad actual.
- Aprobar documentos, procedimiento de privacidad y remitente definitivo antes de publicar.

## Archivos de esta entrega

- Modificado: infra/iniciar_aplicacion.ps1, procedimiento operativo de inicio/parada.
- Creado: docs/INICIO-LOCAL-PRESENTACION.md, revisión, límites y guía.
- Se compararon las huellas de 144 archivos iniciales: 143 permanecen idénticos y solo cambió infra/iniciar_aplicacion.ps1. El único archivo nuevo de fuente/documentación es esta guía. Frontend, backend funcional, pruebas, Compose y documentos anteriores quedaron intactos.
- Registros/metadatos operativos fuera del proyecto; dos resultados textuales de pruebas en revision/ ignorado.
- Sin commit, push, despliegue, cambios de Notion o nuevas funcionalidades.

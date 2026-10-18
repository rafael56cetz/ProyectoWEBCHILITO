# Etapa 0: revisión para integración local real

Fecha: 17-10-2026. Presentación prevista: lunes 19-10-2026. **Solo diagnóstico y contratos; no se autoriza implementar etapas 1–4 con este documento.**

Raíz activa y referencia visual: `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`. Se conserva la copia local modificada por Rafael. No se sustituye por GitHub, respaldos o capturas.

## 1. Lectura y preservación

- Leídos README, guía de integración, documentos de organización/cierre/entregas, entrada, vistas, controladores, modelos, adaptadores, desarrollo, Compose y SQL administrativo.
- No se encontraron instrucciones AGENTS.md en los antecesores examinados ni dentro de esta raíz.
- Git: rama `main`, HEAD `f5605359cdff0fb596a63cfc0c352026fb5060e2`. HEAD no representa toda la copia actual: hay 16 archivos rastreados modificados y numerosos archivos nuevos, incluidos desarrollo, privacidad, seguridad, Compose, infra y documentación. El detalle inicial está en [evidencia](EVIDENCIA-ETAPA-0-LOCAL.json).
- No se hizo fetch, checkout, reset, clean, restauración, commit, push ni modificación de remoto. Las únicas escrituras de esta etapa son documentales.
- Se contrastó la copia actual con las huellas del traslado anterior, sin restaurar nada: **16 archivos de runtime cambiaron** desde aquella evidencia. Esto identifica diferencias, no atribuye cada línea a una persona.
- Cambios a preservar: barra lateral fija de escritorio de 260 px, navegación inferior móvil, pestañas/filtros en cápsula, ajustes del ancho de botones, foco que respeta pestañas y formularios, textos de acceso/privacidad/llaves, borradores legales y escenarios inicialmente vacíos.
- El acceso ahora pasa por validación antes del salto de navegación: el texto histórico «entrar con campos vacíos o cualquier texto» ya no describe el controlador actual. Un correo con formato válido y contraseña no vacía aún permite entrar **sin verificar credenciales**. Además las rutas privadas se abren directamente: `canEnter` tiene valor predeterminado permisivo.

La evidencia conserva huellas iniciales de 50 archivos de dist/docs/infra/scratch y archivos de raíz no secretos. La verificación final distingue los cambios documentales autorizados del runtime, Compose, SQL y recursos preservados.

## 2. Documentación histórica frente a realidad vigente

| Referencia | Uso y diferencia actual |
| --- | --- |
| README y ORGANIZACION-Y-ENTRADA-UNICA | Explican el traslado y una sola entrada. Sus cifras de 28 pruebas y el acceso con campos vacíos son históricos, no resultados de esta etapa ni comportamiento garantizado hoy |
| INTEGRACION-BACKEND, entregas y cierre anterior | Inventario útil de acciones semánticas. Las referencias a revisión separada, documentos vacíos, registro bloqueado y Django pendiente quedaron desactualizadas |
| Código local actual | Autoridad sobre presentación y comportamiento observado; contiene desarrollo ficticio, no autenticación/persistencia |
| Compose + infra | PostgreSQL local ya preparado por Rafael; no implican aplicación Django integrada |
| Propuesta de BD en output | Borrador externo revisado; no se copia ni se declara aprobado/migrado |

Django/Python en Windows y PostgreSQL Docker están **decididos por Rafael**. El backend aún no existe en esta raíz. No se encontraron manage.py, settings ejecutable, migraciones, manifiesto de dependencias backend o CI en .github. La instalación global de bibliotecas no equivale a un backend reproducible del proyecto.

## 3. Inventario de rutas y acciones actuales

Todas parten de `dist/index.html`, con fragmentos de URL. Se reutilizan las mismas vistas. Inventario de navegador de 21 rutas en la evidencia JSON; los estados condicionales se contrastaron también con el código.

| Ruta | Vista/controlador | Formularios, botones o acciones |
| --- | --- | --- |
| #inicio; #el-proyecto; #prototipo; #como-funciona | paginas.js / site + navigation | Marca, anclas, iniciar sesión, enlaces legales y ARCO. Sin formulario público de contacto |
| #acceso | acceso.js / AuthController | email y password; mostrar/ocultar contraseña; Iniciar sesión; Recuperar; Crear cuenta; acceso alternativo de llave |
| #registro | mismas vistas de acceso | email, password, confirmation, termsAccepted obligatorio; Crear cuenta; documentos en pestaña independiente |
| #verificar | acceso / AuthController | email y code; verificar; reenviar; tiempos/errores; después puede montar oferta de llave con Crear/Ahora no/Continuar |
| #recuperar | acceso / AuthController | email; solicitar enlace; resultado actual añade Continuar a cambio de contraseña por token ficticio |
| #restablecer y #restablecer?token=… | acceso / site y AuthController | Inspección del enlace; nueva password/confirmation si válido; guardar, reintentar o solicitar enlace. El fragmento se limpia; el contexto vive en memoria |
| #terminos; #privacidad | legales.js / site | Borradores redactados manualmente, volver, documento relacionado y ARCO; sin aprobación/versionado efectivos |
| #derechos-arco | privacidad / PrivacyController | requesterName, contactEmail, right, description, accountRelation opcional; requestedCorrection solo para rectificación; Enviar solicitud, nuevo formulario |
| #huerto | paginas.garden / AppController | Tres plantas, temperatura, humedad ambiental, flotador; Reintentar solo con error; sin control remoto de bomba/luz |
| #avisos; #avisos/:id | aplicacion / AppController | Todos/Activos/Resueltos; ver detalle; marcar leído si existe aviso; Reintentar. Lista vacía actual; leer no resuelve condición |
| #huerto/avisos | site | Alias redirigido a #avisos |
| #asistente | aplicacion / AppController | Información de disponibilidad futura; no chat, formulario, API ni respuestas de IA |
| #cuenta | aplicacion / AppController | Consulta de email/verificación; Perfil, Seguridad, Privacidad; Cambiar contraseña; Cerrar sesión en encabezado |
| #cuenta/contrasena | acceso embebida / AuthController | currentPassword, password, confirmation; mostrar/ocultar; guardar/cancelar |
| #cuenta/privacidad | privacidad / PrivacyController | Mis solicitudes; abrir/cerrar formulario; crear; detalle; recargar |
| #cuenta/privacidad/solicitudes/:id | privacidad / PrivacyController | Detalle, historial, message e informationRequestId para aclaración habilitada; enviar información; volver a lista |
| #cuenta/seguridad | seguridad / SecurityController | Consultar lista, Crear llave, Quitar/confirmar/conservar, cancelar/reintentar y cambiar contraseña |
| #seguridad público | site | **Sin vista propia: cae a portada**, aunque el pie promete Seguridad y protección de datos |

Las cuatro entradas privadas se conservan: Mi huerto, Avisos, Asistente, Mi cuenta. La navegación inferior sigue fija a 390 px. Mostrar/ocultar contraseña, filtros locales, anclas, pestañas, cancelar y volver son interacciones locales; no requieren por sí mismas endpoint.

## 4. Simulaciones localizadas y tratamiento posterior

| Archivo/punto | Situación encontrada | Cambio futuro requerido |
| --- | --- | --- |
| dist/index.html; desarrollo/inicio.js | Carga seis módulos desarrollo; inyecta review:true, previewNavigation:true e interacción sintética | Sustituir composición al integrar, con los adaptadores reales; no conservar selector alternativo o segunda app |
| controlador/site.js | canEnter por defecto permite rutas privadas; callback dirige al huerto sin restaurar sesión | Inicio asincrónico de sesión; bloqueo de consultas antes de conocer identidad; guardas son UX, autorización siempre servidor |
| controlador/acceso.js | Valida campos antes de saltar login; no consulta servicio si previewNavigation; usa previewCode/previewResetToken | Credenciales reales, restauración y errores; retirar ramas/atajos sintéticos sin retirar validación |
| desarrollo/acceso.js | Código fijo 246810; challenge fijo; token development-reset-only; verificación y contraseñas ficticias | Biblioteca de autenticación como autoridad. No devolver códigos/tokens de revisión; no atajo de restablecimiento |
| controlador/seguridad.js; desarrollo/seguridad.js | Exige response.demonstration===true; begin/finish en memoria; sesión ficticia; fechas prefijadas y IDs demo-operation | No es un puente utilizable para WebAuthn real. Decidir alcance; no presentar éxito ni autenticación mientras esté aplazado |
| desarrollo/privacidad.js | Lista inicialmente vacía, pero crear genera folios/fechas; detalles arco-1/demo-informacion se fabrican al consultar | ARCO aplazado: no recepción/seguimiento inventados en la aplicación integrada |
| desarrollo/aplicacion.js | Garden waiting; perfil con null; avisos ready/items vacíos sin consulta | Consultar datos autorizados; un fallo real no se sustituye por vacío |
| modelo/privacidad.js; vista/legales.js | registrationAllowed:true; documentos state:pending/version:null, aunque hay textos legales | Alta real bloqueada por servidor hasta aprobación y versiones efectivas; no confundir contenido redactado con aprobación |
| vistas/controladores de acceso, privacidad, seguridad | Se retiraron mensajes de simulación y ahora algunos resultados dicen «Correo verificado», «Solicitud registrada» o «Llave vinculada» | Son afirmaciones no respaldadas hoy. Documentadas; no se alteran pantallas en etapa 0 |

No se encontraron peticiones fetch/XHR durante el inventario, ni respuestas prefabricadas de IA en el asistente. Las mediciones siguen sin valores físicos; las fechas de ejemplos ARCO/llaves no son telemetría. No convertir ausencia de datos en 0, alarma, desconexión o última comunicación inventada.

## 5. Clasificación acordada para la integración

«Integrar» significa trabajo de etapas posteriores, no autorización de ejecución en este turno.

| Clasificación | Funciones |
| --- | --- |
| Integrar en etapas 1–3 | Django y persistencia; sesión correo/contraseña; registro con documentos aprobados, código de verificación y correo real; recuperación por enlace; perfil/cambio/cierre; membresía explícita; consulta autorizada del huerto sin lecturas y avisos persistidos/lectura |
| Decisión pendiente | Alcance y navegación de llaves; tratamiento visible de ARCO aplazado; destino público #seguridad; aprobación/versiones legales; proveedor/remitente/cuenta autorizada de correo; quién recibe membresía; política de contraseñas/códigos/sesiones; modelos/retención |
| Aplazadas por Rafael | Recepción y seguimiento ARCO; IA con API; ingesta electrónica/firmware, comandos y horarios remotos; sensores ópticos/ventilador no confirmados; notificaciones externas; despliegue público |

### Propuesta de navegación pendiente de aprobación

Conservar las cuatro entradas principales, portada y diseño. Asistente ya indica futura incorporación: mantener ese estado sin chat ni respuestas inventadas. Conservar enlaces legales reutilizando sus rutas.

Para ARCO: mantener acceso informativo, pero proponer sustituir únicamente envío y seguimiento por disponibilidad real sin acuse; definir antes el canal y responsable. Para llaves: proponer conservar Seguridad con contraseña y mostrar disponibilidad futura sin botones operativos de llave; retirar la alternativa de llave del login y la oferta posterior si se acuerda aplazarlas. Resolver #seguridad como información pública o enlace a un destino acordado. **No se ha ocultado ni cambiado ninguno de estos accesos en etapa 0.**

La portada dice «Sensores en tiempo real», describe comunicación cifrada y un asistente que interpreta lecturas; el aviso redactado promete finalidades/canal ARCO. Son promesas de producto, no evidencia técnica. Requieren revisión de contenido al acordar el alcance, sin rediseñar o activar funciones para justificar las frases.

## 6. Documentos de contrato de esta revisión

- [Contrato HTTP, sesión y datos](CONTRATOS-INTEGRACION-LOCAL.md): acción → entrada → respuesta → permiso → persistencia → error.
- [PostgreSQL y evaluación del borrador](REVISION-POSTGRESQL-Y-MODELOS.md): consultas de metadatos, privilegios y riesgos antes de migrar.
- [Seguridad y verificación](SEGURIDAD-Y-VERIFICACION-LOCAL.md): amenazas, requisitos seleccionados, plan WSTG, SSDF e IoT.
- [Evidencia textual](EVIDENCIA-ETAPA-0-LOCAL.json): inventario real, huellas y límites de comprobación.
- [Catálogo ASVS de alcance](ASVS-5.0.0-ALCANCE-LOCAL.csv): selección inicial y resto pendiente, sin certificación.

## 7. Archivos previstos para etapas autorizadas

No se crean archivos backend ni se modifica el frontend en este turno.

| Etapa | Archivos nuevos o existentes previstos | Motivo |
| --- | --- | --- |
| 1 | backend/manage.py, backend/config/{settings,urls,asgi,wsgi}.py; backend/requirements.txt y registro de dependencias resueltas | Django separado dentro de la misma raíz; configuración local privada/producción diferenciada; versiones exactas; servir dist existente sin copiarlo |
| 1 | backend/cuentas/{models,managers,adapters,apps}.py; migrations/0001_initial.py y tests | Usuario por correo antes de primera migración; compatibilidad allauth; autoridad única de verificación; aceptación legal versionada cuando se acuerde |
| 1 | backend/huerto/{models,services,permissions,views,urls}.py, migrations/, management/commands/preparar_huerto.py, tests/ | Aprobar/adaptar borrador, huerto + tres zonas sin datos, asignación explícita, permisos y APIs de dominio |
| 1 | backend/config/settings de pruebas y pruebas de esquema/roles; infra si precisa procedimiento documentado | Base de pruebas aislada, separación DDL/DML; no ejecutar otra vez el SQL de creación |
| 2 | dist/modelo/servicio-acceso.js, servicio-aplicacion.js y modelo/acceso.js | Transporte browser, CSRF, traducción de allauth, sesión y política real; preservación de separación MVC |
| 2 | dist/index.html y nuevo controlador de arranque si hace falta; controlador/site.js y acceso.js | Arrancar una sola aplicación con sesión real; retirar desarrollo del arranque, previewNavigation y atajos/códigos; restaurar sesión sin renderizar datos privados anticipadamente |
| 2 | backend/cuentas/adapters.py, servicios legales/correo y tests de contrato | Validar términos efectivos en servidor antes de guardar/enviar; SMTP privado; respuestas neutras y límites |
| 2 | vista/acceso.js únicamente si exige el contrato aprobado | Estado correo pendiente, errores reales y enlace de recuperación; retirar código/atajo ficticio sin reconstrucción visual |
| 3 | controlador/aplicacion.js, modelo/aplicacion.js, servicio-aplicacion.js; vistas solo si falta estado aprobado | HTTP 401/403, unassigned, fallo frente a vacío, perfil y avisos reales. Sin cambiar CSS o métricas por conveniencia |
| 3 | vistas/controladores de seguridad/privacidad y enlaces públicos, solo tras decisión | Evitar éxito de funciones aplazadas manteniendo rutas y presentación acordadas |
| 4 | pruebas backend/contrato y revision/comprobar-*.cjs; CI cuando se acuerde; docs | Reescribir expectativas de simulación para integración, probar permisos/restauración y evidencias actuales |

Los nombres de archivos backend son propuesta, no una estructura ya instalada. Se preservan dist/vista, dist/controlador y dist/modelo; el backend aplica su propia separación sin mover o duplicar las vistas frontend.

## 8. Dependencias, bloqueos y responsables

| ID | Pendiente concreto | Efecto y responsable |
| --- | --- | --- |
| B1 | Elegir versión mantenida exacta de Django 5.2, allauth headless y psycopg; crear entorno reproducible | Rafael. Hay bibliotecas globales, no manifiesto ni driver psycopg. Revisar parche/migraciones antes de integrar |
| B2 | Acceso privado desde Windows con credenciales distintas de migrador y app; base aislada de pruebas | Rafael/Carolina. No se leyeron ni probaron contraseñas; metadatos correctos no prueban conexión con ambos roles |
| B3 | Aprobación, responsable, contacto y versiones efectivas de términos/aviso | Equipo y revisión competente. Bloquea registro real, aunque el texto actual y casilla existan; no bloquea esquema/sesión independientes |
| B4 | Proveedor SMTP, remitente, secreto privado y destinatario de prueba autorizado | Rafael. Bloquea demostrar entrega real/código/recuperación; no enviar a terceros ni usar consola como sustituto |
| B5 | Decisión ARCO/llaves/#seguridad y autorización del tratamiento de sus accesos | Rafael. Necesaria antes de modificar navegación de funciones aplazadas; no conservar simulación activa como funcionamiento real |
| B6 | Aprobar ajustes al modelo propuesto y autoridad allauth; retención/borrado/auditoría | Carolina/Rafael. Resolver antes de migraciones definitivas; no copiar modelos en bloque |
| B7 | Usuario(s) autorizados, facultad de asignar huerto y política de sesión/límites | Rafael. Verificación de correo no crea membresía; al menos una cuenta de prueba sin membresía |
| B8 | Contrato futuro ESP32: identidad, reloj, calibración, periodicidad y estados seguros | Rafael/equipo de electrónica. Bloquea ingesta/actuación; no bloquea huerto sin datos |
| B9 | Evidencia actual de accesibilidad en dispositivos reales y CI | Rafael/Gabriela. Navegación automatizada parcial no sustituye esa revisión |

Secretos: el archivo administrativo externo montado por Compose no se abrió. En la etapa correspondiente Rafael introducirá privadamente claves de DB, Django y SMTP en el entorno del proceso o almacén local fuera de dist y Git; no debe pegarlas en el chat/documentación.

Responsabilidades conservadas: Rafael backend e integración; Carolina PostgreSQL/modelado y logo; Rafael y Gabriela frontend/revisión visual. No se modificaron tareas Notion.

## 9. Condiciones de salida por etapa

| Etapa | Criterios antes de declararla terminada |
| --- | --- |
| 0, este turno | Copia actual inventariada, diferencias preservadas, estado DB consultado sin mutaciones, contrato propuesto y bloqueos documentados. Detener aquí |
| 1 | Dependencias fijadas y entorno aislado; AUTH_USER_MODEL antes de migrate; migraciones revisadas/ejecutadas sin pérdida; permisos DDL/DML comprobados; un huerto/tres zonas sin lecturas; membresía explícita; pruebas positivas/negativas de restricciones y persistencia en DB aislada |
| 2 | Login por contraseña y sesión restaurable/cerrable; registro solo con legales efectivos; código temporal real por correo, reenvío/límites; recuperación enlace de uso limitado; cambio/perfil; sin código fijo, omisión, JWT en storage o adaptador sintético en arranque. Entrega real solo al destinatario autorizado |
| 3 | Cuenta y huerto consultados por sesión/membresía; avisos persistentes, lectura independiente de resolución; waiting/null/unknown frente a fallo real; sin datos físicos inventados, IA/ARCO/llaves simulados. Navegación aplazada acordada y móvil conservado |
| 4 | Pruebas de accesos, códigos vencidos/incorrectos, CSRF, IDOR, cuenta sin membresía, reinicio/persistencia, aislamiento y ausencia de desarrollo; respaldo/restauración solo en base aislada; teclado/móvil; dependencias y CI documentados; resultados de revisión actual, límites y única URL/arranque |

Estas etapas son la integración real nueva; no equivalen a las entregas visuales 1–4 anteriores. Ninguna etapa se avanza automáticamente. Los bloqueos jurídicos/correo no autorizan atajos y no impiden trabajar las partes independientes cuando se soliciten.

## 10. Resultado de la revisión actual y límites

Se observó la aplicación en 1440 px: 21 rutas (incluidas anclas, legales, detalle inexistente y #seguridad), sin enviar formularios. A 390 px se recorrieron las cuatro entradas y se confirmó barra inferior fija, sin desbordamiento horizontal en esas comprobaciones. Sin errores pageerror ni fetch/XHR o solicitudes externas observadas; esto no es una auditoría completa de consola, accesibilidad o seguridad. El HTML servido coincide byte a byte con el archivo local.

La base se consultó exclusivamente en transacciones READ ONLY, sin filas personales/secretos. No se instalaron dependencias, reiniciaron servicios, crearon tablas/roles, ejecutaron migraciones o correos. No se ejecutó la batería antigua: contiene expectativas de navegación libre/simulaciones ya cambiadas y no demuestra autenticación real. No se reutilizan sus cifras.

Cierre de preservación: 49 de los 50 archivos iniciales permanecen idénticos por SHA-256; el único archivo existente modificado es docs/INTEGRACION-BACKEND.md, mediante nota de vigencia. Los seis archivos nuevos se enumeran en la evidencia. README, frontend completo, estilos, recursos, Compose, SQL y scratch no cambiaron. Los cinco archivos del borrador externo conservan sus huellas. Se comprobó sintaxis de los 25 JavaScript sin ejecutarlos, enlaces documentales, JSON y los IDs seleccionados contra el catálogo. git diff --check de documentación no encontró errores de espacios. Estas comprobaciones no se presentan como pruebas de backend.

Falta implementar y probar toda la integración real. El frontend permanece exactamente como se recibió, con sus simulaciones todavía activas: este documento no declara la aplicación lista para el lunes. **Etapa 0 terminada; esperar autorización expresa de Etapa 1.**

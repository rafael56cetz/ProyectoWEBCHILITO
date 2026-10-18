# Mejoras de acceso · documento acumulativo

Fecha de esta entrega: 17 de octubre de 2026. Aplicación activa: C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web. Etapas de este encargo: **A y B implementadas; registro propio confirmado por Rafael y registro local con cualquier correo válido habilitado y probado en aislamiento; C no iniciada**. Los informes de integración 0–4 conservan su historia; esta actualización no los sustituye ni reutiliza sus cifras como pruebas nuevas.

## Etapa A · Ayuda visual para crear contraseñas

### Necesidad y comportamiento

Antes: los campos nuevos mostraban instrucciones estáticas. El usuario debía contar por su cuenta. La validación del frontend utilizaba string.length (unidades UTF-16), mientras Python len(str) cuenta puntos de código; por eso algunos caracteres fuera del plano básico se contaban distinto.

Ahora, registro, recuperación y Mi cuenta → Cambiar contraseña comparten el mismo componente:

- Contador inmediato; por ejemplo, 12 caracteres · Faltan 3 para el mínimo; 15 caracteres · Mínimo alcanzado.
- Indicador con icono y texto de Al menos 15 caracteres, pendiente/cumplido.
- Máximo de 256 visible antes de escribir y error explícito si se supera.
- Confirmación sin indicador mientras esté vacía; después muestra coincidencia o diferencia. También se actualiza si se modifica la contraseña original.
- Instrucciones existentes sobre contraseñas comunes, solo numéricas o similares al correo. No se marcan como aprobadas en el navegador; las comprueba Django al guardar.
- Se conserva pegar, autocompletar, mostrar/ocultar y navegar con teclado. La ayuda no se presenta en acceso ni como requisito de contraseña actual.

Mínimo alcanzado solo describe longitud; no es una valoración de seguridad. No se añadieron porcentajes, requisitos de mayúsculas/símbolos ni comprobaciones ficticias.

### Decisión y contrato

Se reutiliza GET /api/acceso/configuracion: password.minLength=15, password.maxLength=256 y password.requirements. No se introdujo una política paralela en JavaScript. Las pruebas comparan ese contrato con el mínimo configurado de Django y el máximo del adaptador actual. Se mantienen MinimumLengthValidator, CommonPasswordValidator, NumericPasswordValidator y UserAttributeSimilarityValidator.

AuthModel.passwordLength utiliza Array.from para contar puntos de código, coherente con Python, y lo reutilizan validación y contador. Un carácter astral cuenta uno; una secuencia de base más marca combinada cuenta dos. No se convierten a NFC/NFD, no se cambia el uso de mayúsculas y no se recortan espacios.

El campo no utiliza maxlength HTML: su conteo UTF-16 podría truncar prematuramente caracteres astrales. Se conserva el texto pegado y se muestra/rechaza el exceso al enviar, tanto en el cliente como en el servidor.

### Corrección necesaria en la entrada del backend

La prueba con espacios detectó que los inputs headless de django-allauth 65.20.0 usan CharField de Django, cuyo strip predeterminado recortaba espacios. Las vistas y adaptadores existentes no compensaban esa diferencia. La prueba del adaptador solo no habría detectado el problema.

Se añadieron subclases locales de LoginInput, ResetPasswordInput y ChangePasswordInput que fijan strip=False únicamente en los campos de contraseña de la instancia. Se pasan por input_class al crear las mismas vistas mediante as_api_view; no se modifica la biblioteca instalada ni se copian validadores, hash, sesiones o criptografía.

Esto conserva la contraseña exacta al cambiarla, recuperarla y autenticarla, incluida la contraseña actual. Las pruebas confirman que la variante sin sus espacios no permite entrar. No hubo migraciones ni modificación de contraseñas existentes: la base principal sigue con cero cuentas.

El registro permanece en su endpoint cerrado y no se añadieron inputs o excepciones que lo habiliten. Al abordar B habrá que conservar esta misma propiedad en el input de alta, sin darla por implementada hoy.

### Accesibilidad y datos

Los campos enlazan errores e instrucciones mediante aria-describedby. La longitud visible tiene aria-live=off; una región de estado separada, polite/atomic, anuncia cambios de rango y de coincidencia con una demora breve de 400 ms. No anuncia cada incremento del contador. Los indicadores combinan icono, texto y color; no dependen solo de color.

El cálculo es local. No se hacen peticiones por pulsación, ni se guardan contraseñas o confirmaciones en storage, logs o analítica. Al limpiar/restablecer el formulario se reinician contador e indicadores; al desmontar se cancela el anuncio pendiente. Los atributos new-password/current-password, pegado y controles de visibilidad se conservan.

### Archivos y responsabilidades

| Archivo | Cambio / responsabilidad |
| --- | --- |
| dist/modelo/acceso.js | Modificado: conteo Unicode y estado de longitud/coincidencia según configuración del servidor; validación coherente sin recorte de espacios. |
| dist/vista/acceso.js | Modificado: presentación compartida de ayuda, indicadores, instrucciones y asociaciones accesibles. |
| dist/controlador/acceso.js | Modificado: coordina eventos, actualización, anuncios de cambios relevantes y limpieza del estado. |
| dist/vista/css/acceso.css | Modificado: estilos pequeños, usando la paleta/tipografía existentes y colores forzados; sin rehacer botones ni materiales. |
| backend/cuentas/inputs.py | Nuevo: inputs derivados de allauth que conservan exactamente los caracteres de contraseña. |
| backend/cuentas/api.py | Modificado: selecciona esos inputs en las vistas de allauth ya existentes; sin nuevas rutas ni excepciones de registro. |
| backend/tests/test_password_guidance.py | Nuevo: siete casos de servidor, transaccionales y aislados; no hereda ni duplica la batería anterior. |
| backend/tests/ui_password_help.cjs | Nuevo: comprobación enfocada de los tres formularios en Chromium, sin capturas. |
| backend/tools/comprobar_frontend.py | Modificado: opción --contrasenas; reutiliza el servidor/fixture aislados y limpieza. El enlace de recuperación usa un token temporal exclusivo de esa fixture, sin imprimirlo. |
| infra/verificar_entrega.ps1 | Modificado: incluye la nueva comprobación enfocada en el ejecutor local existente. La infraestructura sigue siendo opcional. |
| README.md; backend/README.md | Modificados: actualización acotada y enlace a esta entrega; historia anterior conservada. |
| docs/MEJORAS-DE-ACCESO.md | Nuevo: este documento acumulativo, preparado para añadir futuras entregas autorizadas. |
| docs/EVIDENCIA-ETAPA-A-CONTRASENAS.json | Nuevo: resultados y huellas saneadas de esta revisión. |

Se preservan MVC frontend y responsabilidades de Django. Sin framework nuevo, cambios de dependencias, migraciones, CSS ajeno, logo, portada, recursos o navegación móvil. Sin commit, push o despliegue.

### Verificación ejecutada

| Prueba actual | Resultado |
| --- | --- |
| Batería Django en PostgreSQL aislado | 93 casos, 0 fallidos; incluye siete nuevos de esta etapa. |
| Navegador enfocado en ayuda de contraseña | 69 comprobaciones, 0 fallidas. |
| Regresión de acceso | 64 comprobaciones, 0 fallidas. |
| Regresión de huerto/cuenta/navegación | 65 comprobaciones, 0 fallidas. |
| Concurrencia de lectura existente | 3 aserciones, 0 fallidas. |
| Base principal | Misma huella de filas/esquema que el respaldo verificado de Etapa 4: 30 migraciones, 1 huerto, 3 zonas; cero cuentas, membresías, avisos y sesiones. |
| Limpieza de pruebas | Cero fixtures, sesiones y entradas de caché restantes en el_chilito_test; servidor temporal retirado. |
| Sintaxis y entrega local | Python y JavaScript modificados válidos; recursos servidos actualizados; git diff --check sin errores. |
| Contraste de textos nuevos | Mínimos calculados sobre blanco/#EBF1EC/#F6F9F6: secundario 6.18:1, verde 8.37:1 y error 7.53:1. No es auditoría completa de accesibilidad. |

Se probaron 14, 15, 16 y 256 puntos de código, exceso de 257, astrales y marcas combinadas, conservación de espacios, pegado real mediante portapapeles/Control+V, confirmación incorrecta/correcta y corrección al editar el original, visibilidad, error real del servidor, teclado y movimiento reducido. Los formularios se revisaron a 320, 390, 768, 1024 y 1440 px sin desbordamiento horizontal.

Recuperación y cambio se enviaron realmente contra el servidor aislado; el servidor rechazó valores inválidos aun sin JavaScript. La prueba de navegador confirmó que escribir no dispara peticiones de mutación y que no se repite un anuncio de estado en cada pulsación. No se enviaron correos reales; el correo de pruebas del servidor se conserva exclusivamente en memoria.

No se repitieron respaldo/restauración ni reinicio de PostgreSQL. Solo se recargó el proceso Django local identificado para aplicar los inputs. Las pruebas de infraestructura de Etapa 4 mantienen su evidencia histórica, no se presentan como reejecutadas en A.

Evidencia actual: [EVIDENCIA-ETAPA-A-CONTRASENAS.json](EVIDENCIA-ETAPA-A-CONTRASENAS.json).

### Pruebas reproducibles

Docker Desktop debe estar encendido y el entorno/credenciales de pruebas ya preparado según [manual backend](../backend/README.md). No ejecutar baterías simultáneas sobre la misma base.

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py test tests.test_password_guidance --verbosity 1
$env:NODE_PATH='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\rafae\AppData\Local\ms-playwright'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_frontend.py --contrasenas
```

Para la regresión habitual completa está infra/verificar_entrega.ps1, sin -Infraestructura. Sus rutas de Playwright son las del equipo de revisión y se pueden proporcionar mediante las variables de entorno indicadas.

### Relación con seguridad y fuentes

Selección adicional y parcial de ASVS 5.0.0 para esta mejora; no redefine el nivel objetivo ni marca el catálogo existente como satisfecho:

| Referencia | Relación con este cambio | Evidencia / límite |
| --- | --- | --- |
| v5.0.0-2.2.1 | Validación coherente en servidor. | Límites y negativos por HTTP sin JavaScript; no revisión de toda la aplicación. |
| v5.0.0-6.2.1 | Longitud mínima del proyecto, 15. | Contrato y validación Django comprobados. |
| v5.0.0-6.2.6 | Entrada enmascarada con opción de mostrar. | Pruebas de visibilidad y teclado. |
| v5.0.0-6.2.7 | Permitir pegar/gestores. | Pegado real y atributos; pendiente revisión manual con gestores concretos. |
| v5.0.0-6.2.8 | Contraseña completa sin transformación. | Unicode y espacios conservados por frontend y vistas reales allauth. |
| v5.0.0-6.2.9 | Capacidad de contraseñas largas. | Política vigente permite 256; aceptación comprobada. |

Fuente de identificadores: [ASVS 5.0.0 oficial](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv). Es una selección de seis referencias para A, no cobertura de un nivel completo ni modificación de la matriz histórica de Etapa 0.

[NIST SP 800-63B-4, sección de contraseñas](https://pages.nist.gov/800-63-4/sp800-63b.html#passwords) respalda orientación, conteo por puntos Unicode y permitir gestores/pegado; no se adopta unilateralmente su recomendación de normalización porque este encargo exige conservar la representación vigente. [Django 5.2](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/) fundamenta mantener los validadores del servidor. [W3C 4.1.3](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) orienta el estado accesible sin exceso de anuncios.

Compatibilidad revisada contra código instalado de allauth 65.20.0: headless/account/inputs.py, headless/internal/restkit/inputs.py y base/views.py. Sin actualización de versiones ni copia de configuración latest de MFA.

Las prácticas de SSDF 1.1 ya adoptadas se mantienen: cambio acotado, requisitos trazables, preservación de trabajo, bibliotecas existentes, regresión con datos aislados y resultados/puntos pendientes documentados. No se declara cumplimiento integral de NIST/ASVS, certificación o auditoría completa.

### Cómo revisarlo y pendientes

Encender mediante infra/iniciar_aplicacion.ps1 y abrir **[registro en El Chilito](http://127.0.0.1:8766/index.html#registro)**. Recargar si la página ya estaba abierta. Escribir o pegar una contraseña permite comprobar longitud e indicador; empezar a escribir en confirmación muestra coincidencia. La contraseña actual y el inicio conservan su presentación habitual.

El registro continúa cerrado: A no habilita cuentas ni inventa aceptación legal. No existe contraseña de muestra para entrar. Recuperación y cambio requieren una cuenta real y su enlace/sesión; fueron verificados sobre fixtures aisladas, no mediante acceso alternativo en la base principal.

Quedan pendientes prueba manual con lector de pantalla/gestores reales y teléfono físico. No se han probado todos los navegadores. La excepción HTTP de loopback, cookies y origen canónico siguen iguales; esta mejora no autoriza exposición pública ni traslada excepciones locales a producción.

Responsables: Rafael backend/operación; Carolina PostgreSQL/logo; Rafael y Gabriela frontend. B requiere solicitud expresa; C también. No se modifica Notion.

## Etapa B · Registro propio autorizado en local

Fecha: 17 de octubre de 2026. **Implementado y verificado en entorno aislado; registro local habilitado. Prueba manual con correo real pendiente de Rafael. C no iniciada.**

### Necesidad y estado vigente

Rafael autorizó su registro real en esta computadora mientras se terminan los documentos. Esta autorización sustituye el bloqueo de alta anterior solo para esa prueba local. No aprueba los documentos ni permite abrir registro público.

Antes, configuración, adaptador, endpoint y controlador bloqueaban todo registro. Ahora GET /api/acceso/configuracion informa registrationAllowed=true únicamente al combinar el perfil/opt-in local válido y una petición desde loopback. El mismo endpoint de allauth registra, envía el código por el correo existente, verifica y establece sesión según la política vigente. Los documentos siguen con approved=false, termsVersion=null y privacyVersion=null.

Se reutilizan HTML/CSS/JavaScript y MVC, el único dist, componentes y vistas existentes. Sin plantillas predeterminadas, aplicaciones alternativas, acceso libre, cambios de framework, WebAuthn, push o despliegue.

### Corrección visual solicitada después de A

La indicación visible se simplificó a **Al menos 15 caracteres**, con círculo vacío y palomita al cumplir el mínimo. No muestra Pendiente/Cumplido como texto, ni 0 caracteres · Faltan…, Máximo 256 caracteres o El servidor comprobará estas condiciones al guardar.

El conteo Unicode continúa en el modelo y, cuando hay texto, como descripción accesible no visible; no cambia la contraseña ni la validación. Se mantiene la confirmación de coincidencia y la orientación existente sobre contraseñas comunes, solo numéricas o similares al correo. No se da por aprobada esa revisión solo por cumplir longitud. Los errores necesarios siguen informando por qué se rechaza una contraseña, incluido el exceso de 256.

La sección de A conserva la historia de su primera entrega; su presentación anterior queda sustituida por esta corrección.

### Configuración y límites de confianza

- Base: ELCHILITO_LOCAL_PRESENTATION=false y ELCHILITO_LOCAL_REGISTRATION_ENABLED=false.
- Perfil config.settings.local: presentación local explícita y alta habilitada para esta etapa. ELCHILITO_LOCAL_REGISTRATION=0 puede desactivarla al iniciar/recargar el proceso; el valor local predeterminado autorizado es 1.
- Solo se aceptan perfil local, base el_chilito, correo AuthorizedSMTPBackend, ALLOWED_HOSTS exactamente limitado a 127.0.0.1 y enlaces de correo del origen canónico. No depende únicamente de DEBUG, Host o un dato del formulario.
- Cada solicitud de registro exige además REMOTE_ADDR=127.0.0.1, HTTP local y Host canónico con puerto 8766. Un Host local desde una dirección remota no habilita la excepción. No se usan cabeceras reenviadas para inferir al usuario local.
- Comprobación Django cuentas.E001 rechaza la activación con otro perfil, host abierto, proxy configurado, CORS abierto, origen incorrecto o base/correo incompatibles. El control de ejecución falla cerrado también si se omite manage.py check.
- Las pruebas usan config.settings.testing con base el_chilito_test, correo en memoria y opt-in independiente ELCHILITO_TEST_LOCAL_REGISTRATION=1. La excepción está apagada por defecto en las demás pruebas. El puerto 8768 es solo transitorio para ese ejecutor.
- Los listeners comprobados siguen en 127.0.0.1:8766 y 127.0.0.1:5433. No se abrió ningún puerto, proxy, túnel ni servicio público.

La configuración local no debe copiarse a una publicación. El proyecto no adquiere una configuración de producción completa por añadir este control.

### Casilla y confirmación técnica

La casilla está desmarcada al abrir la pantalla. Frontend y backend impiden continuar si falta. El endpoint exige **el booleano JSON true**, no cadenas, números o solo un botón habilitado. Se mantienen CSRF y validación del formulario de allauth.

Se añadió ConfirmacionRegistroLocal vinculada uno a uno a la cuenta, con fecha, casilla_marcada=true y documentos_pendientes=true. Una restricción de PostgreSQL impide transformar ese registro en una declaración de documentos aprobados.

Esta fila es una confirmación técnica de la prueba local. No representa consentimiento legal definitivo, no contiene versiones inventadas, no modifica las páginas legales y no asigna membresía. Los campos de aprobación/versiones enviados por el navegador no se aceptan como autoridad.

La cuenta, dirección de correo y confirmación técnica se guardan juntas en una transacción mediante el input derivado de allauth. La migración cuentas.0003_confirmacion_registro_local se aplicó primero y probó en la base aislada; después, con el rol migrador, en la principal. La principal pasó de 17 a 18 tablas y de 30 a 31 migraciones. Se conservaron los datos previos de negocio; las únicas filas de metadatos nuevas corresponden a migración, tipo de contenido y permisos del nuevo modelo. El rol app recibió DML por los privilegios predeterminados, sin DDL administrativo.

### Autenticación, correo y errores

Se utiliza SignupView/SignupInput de django-allauth 65.20.0 y el adaptador existente, conservando mínimo 15, máximo 256, Unicode exacto, espacios, validadores Django, sesiones y límites. El input local añade el contexto del correo al validador de similitud. No se diseñaron contraseñas derivadas, códigos, hash o sesiones propios.

Solo el correo previamente autorizado puede recibir mensajes reales. La configuración privada existente se comprobó como disponible sin imprimirla ni enviar otro mensaje. Actualización autorizada por Rafael el 17-10-2026: el destinatario correcto para su registro es rafaelcetz80@gmail.com. La dirección inicialmente indicada con las letras t y e intercambiadas se retiró de la lista privada tras confirmar la corrección. Se conserva econeeksugerencias@gmail.com como remitente de pruebas y la lista previa de destinatarios. No se habilitó el envío a direcciones arbitrarias. Un rechazo de entrega/configuración devuelve 503. Un correo fuera de la lista autorizada devuelve 403 email-not-authorized; ninguno se presenta como éxito de envío.

Se mantienen código de seis dígitos, vigencia de 600 segundos, máximo de tres intentos, espera de reenvío, máximo de cinco reenvíos y cuotas de allauth. El acceso normal sigue con correo/contraseña; no exige código en cada login.

Resultados tratados:

| Caso | Resultado |
| --- | --- |
| Casilla ausente o distinta del booleano true | 400 terms-required, sin cuenta ni correo. |
| Perfil/solicitud no autorizados | 403 registration-disabled. |
| Datos o contraseña inválidos | 400 de validación; sin alta. |
| Destinatario no autorizado para la prueba local | 403 email-not-authorized antes de crear cuenta; error asociado al correo y foco en ese campo. No consulta ni revela existencia de cuentas. |
| Configuración de correo no disponible | 503 mail-unavailable antes de crear cuenta. |
| Alta válida y envío completado | 401 de allauth con flujo verify_email pendiente; frontend muestra la vista existente de verificación. No hay sesión autenticada todavía. |
| Código incorrecto/vencido | Rechazo y mantenimiento/fin del proceso según la biblioteca; no verifica ni concede acceso. |
| Reenvío | Respeta límites; el nuevo código invalida el anterior. |
| Código correcto | Verificación y sesión de allauth; continúa mediante la vista existente. |
| Correo duplicado | Se conserva prevención de enumeración de allauth: respuesta genérica pendiente y mensaje al propietario del correo; no crea otra cuenta, cambia contraseña o concede sesión. El propietario continúa con Iniciar sesión/recuperación según ese mensaje. |
| Fallo SMTP después de guardar el alta | 503, sin fingir entrega. Puede quedar una cuenta **sin verificar**, con confirmación técnica. Iniciar sesión con la contraseña elegida permite reintentar el envío del código cuando el correo esté disponible. |
| Error de base de datos | Error de servicio saneado, sin detalles internos. |
| Cuenta verificada sin membresía | Perfil propio disponible, huerto denegado; nunca asignación automática. |

Un código no se devuelve en respuestas ni aparece en pantalla, logs o documentos. El test de navegador obtiene únicamente el código de una fixture aislada por un canal interno del ejecutor; no se añadió endpoint HTTP para recuperar códigos ni mecanismo de acceso alternativo a la aplicación.

### Archivos de B y responsabilidades

| Archivo | Cambio |
| --- | --- |
| backend/cuentas/registration.py | Nuevo: política de perfil/origen local y comprobaciones para fallar cerrado. |
| backend/cuentas/checks.py | Nuevo: comprobación Django de configuración. |
| backend/cuentas/apps.py | Registra la comprobación. |
| backend/config/settings/base.py, local.py, testing.py | Flags cerrados por defecto fuera del perfil local; pruebas con opt-in aislado. |
| backend/cuentas/inputs.py | Input de alta derivado de allauth: contraseña exacta, casilla y guardado transaccional de la confirmación técnica. |
| backend/cuentas/adapters.py | Habilita alta solo cuando la política local lo permite; conserva el nombre de clase existente y validadores. |
| backend/cuentas/models.py | Modelo de confirmación técnica, sin aprobación ni versiones legales. |
| backend/cuentas/migrations/0003_confirmacion_registro_local.py | Nueva migración generada por Django y aplicada con migrador a ambas bases. |
| backend/cuentas/api.py, backend/config/urls.py | Mismo endpoint de alta: autorización, literal true, destinatario y delegación en la biblioteca; configuración refleja disponibilidad real. |
| dist/modelo/acceso.js, dist/controlador/inicio.js | Configuración de disponibilidad del servidor, cerrada si falta. |
| dist/modelo/servicio-acceso.js | Reconoce respuestas reales de alta, errores y contexto de verificación. |
| dist/controlador/acceso.js | Usa esa disponibilidad; coordina errores/envío sin bloquear por aprobación pendiente en esta excepción. |
| dist/vista/acceso.js, dist/vista/css/acceso.css | Indicación mínima con palomita, retirada de textos solicitados, mismas vistas. |
| infra/iniciar_aplicacion.ps1 | Reconoce el servidor existente con disponibilidad booleana abierta o cerrada, sin duplicarlo. |
| backend/tests/test_local_registration.py | Nuevo: 19 casos de registro, configuración, casilla, código, correo, duplicados, roles y confirmación. |
| backend/tests/ui_local_registration.cjs | Nuevo: recorrido de alta → código → sesión → cuenta sin huerto, teclado y móvil. |
| backend/tools/comprobar_registro_local.py | Nuevo: ejecutor aislado, canal interno de fixture, limpieza sin SMTP real. |
| backend/tests/ui_password_help.cjs, ui_stage2.cjs | Ajustados a la presentación corregida y al mensaje genérico cuando registro está cerrado. |
| infra/verificar_entrega.ps1 | Añade el recorrido aislado de registro al ejecutor existente. |
| README.md, backend/README.md, docs/INTEGRACION-BACKEND.md, docs/CONTRATOS-INTEGRACION-LOCAL.md | Notas del estado vigente y enlace a este documento. |
| docs/MEJORAS-DE-ACCESO.md, docs/EVIDENCIA-ETAPA-B-REGISTRO-LOCAL.json | Documento acumulativo y evidencia saneada actual. |

No se movieron ni eliminaron archivos existentes. Se conserva el contenido legal, logo, Geist, recursos, portada y cuatro entradas con navegación móvil. No se modificó Notion ni se avanzó a C.

### Pruebas actuales

| Revisión | Resultado |
| --- | --- |
| Backend Django/PostgreSQL aislado | 112 casos aprobados, incluidos 19 de B. |
| Comando administrativo asignar_huerto | Comprobado además de forma enfocada con cuenta aislada verificada; acceso denegado antes, concedido solo tras ejecutar el comando. No cuenta como otro caso distinto en el total. |
| Navegador: alta real, código incorrecto/correcto, recarga, sesión, no membresía y logout | 40 comprobaciones aprobadas. |
| Navegador: contraseñas y presentación corregida | 75 comprobaciones aprobadas. |
| Regresión de acceso | 64 comprobaciones aprobadas. |
| Regresión de huerto/cuenta | 65 comprobaciones y 3 aserciones de concurrencia aprobadas. |
| Página canónica | Casilla desmarcada, registro disponible, documentos no aprobados, palomita operativa y textos retirados; cero POST durante esta inspección. |
| Configuración | Django check sin errores, makemigrations --check sin cambios y listeners solo loopback. |

Anchuras: 320, 390, 768, 1024 y 1440 px. Se revisaron teclado, ausencia de desbordamiento, Unicode/pegado y estados de error. Sin capturas. Fixtures y servidor temporal retirados; sin cuentas ficticias en la principal.

No se repitieron respaldo/restauración o reinicio de PostgreSQL. Solo se aplicó la migración necesaria y recargó el proceso Django identificado. No se enviaron correos reales ni se escribió una contraseña o código de Rafael durante la automatización.

Los procedimientos completos se pueden repetir con infra/verificar_entrega.ps1 **sin -Infraestructura**. Solo el nuevo recorrido:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
$env:NODE_PATH='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\rafae\AppData\Local\ms-playwright'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_registro_local.py
```

No ejecutar pruebas simultáneas en la misma base aislada. Evidencia: [EVIDENCIA-ETAPA-B-REGISTRO-LOCAL.json](EVIDENCIA-ETAPA-B-REGISTRO-LOCAL.json).

### Cómo revisar tu registro y asignar el huerto

1. Encender con infra/iniciar_aplicacion.ps1 si hace falta.
2. Abrir **[registro de El Chilito](http://127.0.0.1:8766/index.html#registro)** y recargar la página.
3. Escribir el correo autorizado y una contraseña propia; confirmar, consultar los documentos existentes y marcar la casilla.
4. Crear cuenta. Abrir el correo recibido e introducir el código **en la página**, sin compartir contraseña o código en el chat.
5. Tras verificar, la sesión estará confirmada. El huerto seguirá sin asignar hasta una acción administrativa explícita.
6. Si falla el envío, no se da por enviado: intentar más tarde o iniciar sesión con la contraseña elegida para solicitar el código.

Para asignar explícitamente el huerto principal existente (ID 1), después de verificar tu cuenta, el operador local ejecuta:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
$env:ELCHILITO_DB_SCOPE='local'
$env:ELCHILITO_DB_ROLE='app'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py asignar_huerto --email 'rafaelcetz80@gmail.com' --huerto 1
```

Es una operación de administración local, no un paso automático del registro ni un endpoint público. El comando no crea usuarios, no cambia contraseña, no verifica correos ni concede permisos de superusuario. Volver a Mi huerto/recargar consulta la membresía nueva. Para revocarla, el mismo comando admite --desactivar.

### Retirar la excepción y pendientes

Para desactivarla en el proceso local actual, establecer ELCHILITO_LOCAL_REGISTRATION=0 y recargar Django. El iniciador por sí solo reconoce el proceso existente y no vuelve a cargar su configuración. Con la aplicación ya encendida, se puede usar el recargador identificado existente:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
$env:ELCHILITO_LOCAL_REGISTRATION='0'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" -c "from tools.verificar_reinicio_local import restart_canonical_server; restart_canonical_server()"
```

Esto recarga solo Django, sin repetir la prueba de infraestructura. La variable afecta procesos iniciados desde ese entorno; para retirar permanentemente la excepción habrá que dejar ELCHILITO_LOCAL_REGISTRATION_ENABLED=false/eliminar el opt-in de local.py y conservar base.py cerrado.

Cuando existan documentos aprobados, se requerirá otra entrega explícita para versiones efectivas, aceptación legal definitiva y su evidencia de servidor. No se debe convertir la confirmación técnica existente en consentimiento definitivo ni cambiar approved=true para reutilizar este flujo. Una publicación exige configuración propia, HTTPS, origen estable, correo autorizado definitivo y revisión correspondiente.

Pendientes: prueba manual real de Rafael, confirmación de recepción del correo de ese registro, asignación administrativa posterior si la desea, revisión con lector/gestores/teléfono físico, documentos legales definitivos y C. La prueba automatizada no acredita entrega SMTP real nueva ni interacción con autenticadores físicos.

### Seguridad relacionada

Selección parcial ASVS 5.0.0: v5.0.0-2.2.1 (validación de casilla/entrada), v5.0.0-3.5.1 (CSRF), v5.0.0-6.2.8 (contraseña exacta), v5.0.0-6.3.1 (límites), v5.0.0-7.2.1 (sesión de servidor), v5.0.0-8.2.1 y v5.0.0-8.2.2 (permiso explícito del huerto). Evidencia en las pruebas citadas; no cubre el catálogo o un nivel completo.

Las prácticas SSDF 1.1 ya adoptadas se aplican al cambio acotado, preservación, biblioteca existente, separación de migrador/app, regresión aislada y documentación de pendientes. La confirmación técnica no es una evaluación jurídica. Referencias: [ASVS 5.0.0](https://github.com/OWASP/ASVS/tree/v5.0.0/5.0), [transacciones Django 5.2](https://docs.djangoproject.com/en/5.2/topics/db/transactions/). Se revisó el código instalado de allauth 65.20.0 para SignupView, SignupInput, BaseSignupForm, verificación por código y respuesta de duplicados; no se copiaron configuraciones MFA de latest.

**C permanece pendiente de solicitud expresa.**

### Corrección posterior de destinatario y diagnóstico del registro — 17-10-2026

**Causa confirmada con Rafael:** el correo autorizado tenía dos letras intercambiadas. El destinatario de registro correcto es rafaelcetz80@gmail.com. Se corrigió únicamente la lista privada de destinatarios; se retiró la dirección equivocada y se conservaron remitente, demás destinatarios, credencial y permisos del archivo. No se abrió el envío a terceros.

Además, el mismo mensaje ocultaba dos causas distintas. El registro local ahora diferencia la falta de autorización del destinatario (403 email-not-authorized) de una configuración o entrega no disponible (503 mail-unavailable). El primer error se asocia al campo de correo mediante aria-invalid y su descripción, y mueve allí el foco. No añade etiquetas permanentes, revela la lista permitida ni informa si existe una cuenta. Recuperación y otros flujos conservan sus respuestas.

Archivos de esta corrección:
- backend/cuentas/email.py: diagnóstico de disponibilidad reutilizado por delivery_available.
- backend/cuentas/api.py: distinción del rechazo previo al registro.
- dist/modelo/servicio-acceso.js: traducción del nuevo código de respuesta.
- dist/controlador/acceso.js: error accesible en el campo existente.
- backend/tests/test_local_registration.py: pruebas de configuración, autorización y respuesta independiente de existencia de cuentas.
- backend/tests/ui_local_registration.cjs: error, foco, reintento y recorrido completo en la base aislada.
- docs/MEJORAS-DE-ACCESO.md y docs/CONTRATOS-INTEGRACION-LOCAL.md: causa, contrato y comprobaciones.
- correo_local.json, fuera del proyecto: corrección autorizada del destinatario, sin guardar credenciales en código.

**Comprobaciones:** 45 pruebas Django de acceso/registro aprobadas; 48 comprobaciones de navegador aprobadas en 320, 390, 768, 1024 y 1440 px, sin capturas. El ensayo de navegador usa la base aislada y correo en memoria; el escenario de error intercepta exclusivamente una respuesta de esa prueba. La prueba se ajustó al borrado existente de contraseñas tras un error, antes de reintentar.

Se comprobó autenticación SMTP mediante el transporte TLS de Django sin transmitir mensajes. Se recargó únicamente Django local y se comprobó en HTTP que la dirección correcta pasa la autorización de correo y que la equivocada recibe el error específico. Ambas solicitudes usaron una contraseña deliberadamente inválida para impedir alta/envío. Sintaxis JavaScript y git diff --check sin errores; solo advertencias previas de finales de línea.

La recepción real del código y la elección de contraseña siguen correspondiendo al registro que Rafael realiza en la página. No se crearon cuentas ni membresías en la base principal, no se enviaron correos durante esta corrección y no se avanzó a C. Se conservan los controles de entrega, validación del servidor y errores saneados del alcance ASVS previamente documentado.

### Registro local con cualquier correo válido — 17-10-2026

**Decisión vigente de Rafael:** retirar la autorización manual de destinatarios en la computadora. Esta instrucción sustituye la conservación anterior de la lista para los flujos locales de cuenta. La restricción era una decisión de pruebas, no una limitación de SMTP o de ejecutar la aplicación en loopback. Los apartados anteriores conservan el comportamiento histórico.

El registro admite cualquier dirección con formato válido. La cuenta sigue pendiente hasta verificar el código recibido; el formato no demuestra que el buzón exista ni que el usuario pueda leerlo. Acceso normal por contraseña, reenvío y recuperación mediante enlace usan la misma política de entrega. No se asigna un huerto automáticamente.

#### Configuración y contrato

- ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT=False en base y testing. En local toma la variable de entorno homónima, con valor predeterminado 1 autorizado por Rafael. Persiste al volver a iniciar normalmente la aplicación.
- El permiso de enviar a direcciones fuera de la lista exige perfil exacto config.settings.local y todas las comprobaciones de entorno ya existentes: presentación local, hosts/origen canónicos, base local, transporte SMTP y ausencia de proxy/CORS abierto. La comprobación cuentas.E001 también se ejecuta si el registro está apagado y esta opción permanece activa.
- El registro sigue exigiendo petición local, casilla literal true, contraseña válida, CSRF y validadores allauth. No se abren puertos, rutas ni servicios públicos.
- La lista authorized_recipients del archivo privado deja de decidir los destinatarios en este modo; no se modifica ni se amplía automáticamente. El remitente, contraseña privada y asistente administrativo de comprobación se conservan. El comando comprobar_correo_local sigue enviando solo al remitente de pruebas configurado.
- Para volver al modo restringido: configurar ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT=0 y reiniciar Django. El código email-not-authorized y su tratamiento accesible se conservan para ese modo. No aparecen para correos válidos bajo la configuración local vigente.
- El transporte sigue validando destinatarios y utilizando TLS. Configuración incompleta o fallo SMTP conserva mail-unavailable; no se declara un envío exitoso cuando falla.
- No cambia el contrato de signup, verificación, reenvío o recuperación. Los documentos permanecen pendientes y approved=false. No hay migraciones, cambios de contraseñas, dependencia nueva, edición visual, publicación ni avance a C.

#### Archivos y responsabilidades

- backend/cuentas/email.py: valida destinatarios y aplica la misma política al preflight y al transporte.
- backend/cuentas/registration.py: reutiliza las comprobaciones del entorno local y expone la autorización de destinatarios sin lista.
- backend/config/settings/base.py, local.py y testing.py: configuración explícita y separación de perfiles.
- backend/tests/test_email_policy.py (nuevo): política local, configuración incompatible, destinatarios inválidos, SMTP/TLS y fallos de entrega; transporte sustituido para no enviar.
- backend/tests/test_local_registration.py: añade el recorrido con correo fuera de lista, usando la clase real de transporte y conexión SMTP sustituida.
- README.md, backend/README.md, docs/INTEGRACION-BACKEND.md, docs/CONTRATOS-INTEGRACION-LOCAL.md y este documento: estado vigente y diferencias respecto del historial.

#### Evidencia y límites

57 pruebas Django aprobadas de correo, registro y acceso. Incluyen formato inválido, ausencia de configuración, modo restringido, entornos incompatibles incluso con registro apagado, alta pendiente, reenvío limitado, verificación, login sin nuevo correo, recuperación y ausencia de membresía automática. Las pruebas usan la base aislada; los metadatos ficticios de la política no cambian la conexión a esa base.

48 comprobaciones de navegador aprobadas en 320, 390, 768, 1024 y 1440 px, sin capturas. Se conserva la prueba del error específico del modo restringido como regresión; el registro posterior recorre las mismas vistas, código y sesión.

Django check y git diff --check aprobados; las advertencias de finales de línea pertenecen a cambios previos. Se recargó únicamente Django local y se verificaron dos direcciones de dominios distintos fuera de la lista mediante solicitudes HTTP con una contraseña deliberadamente inválida: ambas pasaron la política de correo y fueron rechazadas únicamente por contraseña, sin crear cuentas ni enviar mensajes. Los conteos de usuarios, direcciones, confirmaciones técnicas y membresías de la base principal permanecieron iguales. Los listeners siguen en 127.0.0.1:8766 y 127.0.0.1:5433.

Rafael confirmó que su registro anterior recibió y validó el código real. Durante este cambio no se enviaron correos reales ni se registraron personas adicionales; la recepción en un destinatario nuevo se comprobará al usar el formulario. La aceptación de un envío por SMTP no garantiza su llegada a Recibidos.

Se mantiene el alcance parcial de desarrollo seguro/ASVS ya documentado: validación de servidor, verificación de correo, errores saneados, límites y autorización de recursos. No se declara cumplimiento integral ni configuración lista para publicación.


### Navegación sin parpadeo y confirmación de cierre de sesión — 17-10-2026

Necesidad: al cambiar entre las secciones aparecía durante un instante la pantalla completa «Comprobando sesión». El cierre de sesión se ejecutaba con un único clic sin permitir cancelar.

Causa: el router destruía el controlador y sustituía toda la aplicación por la vista de comprobación en cada destino privado. Ahora conserva el encabezado, las cuatro entradas de navegación y la vista autorizada mientras el servidor comprueba la siguiente ruta. Después actualiza el contenido con el mismo controlador. La comprobación inicial se mantiene cuando todavía no hay una vista privada autorizada. Sesión vencida o comprobación fallida siguen retirando el contenido privado y llevando al acceso; no se usa una sesión inventada o un permiso guardado en el navegador.

Las solicitudes de navegación anteriores se cancelan al cambiar de destino. Un contador de secuencia impide que respuestas tardías sobrescriban la sección actual. El contenido previo queda inerte mientras carga el siguiente apartado; las cargas rápidas se sustituyen directamente y las lentas conservan un estado de carga después de 200 ms. No se ocultan errores ni se cambian mediciones IoT.

Cerrar sesión abre un dialog nativo con el estilo y los botones existentes. Muestra «¿Cerrar sesión?», «Cancelar» y «Cerrar sesión». El foco comienza en Cancelar. Cancelar o Escape cierran el diálogo y devuelven el foco al botón de origen, sin enviar la salida. Confirmar solicita el cierre real una sola vez y bloquea ambos botones durante el envío. Un fallo mantiene el diálogo, muestra el error y permite cancelar o reintentar. La salida confirmada regresa al formulario de acceso.

Archivos y MVC:
- dist/controlador/site.js: conserva la estructura privada, coordina comprobaciones cancelables y reutiliza el controlador al navegar.
- dist/controlador/inicio.js: transmite la señal de cancelación a la comprobación de sesión existente.
- dist/controlador/aplicacion.js: actualiza secciones, cancela cargas obsoletas y coordina el diálogo y la salida real.
- dist/vista/aplicacion.js: presentación del diálogo dentro de la estructura compartida.
- dist/vista/css/aplicacion.css: dimensiones adaptables y superficie del diálogo, reutilizando botones y tarjetas existentes.
- backend/tests/ui_navigation.cjs (nuevo): pruebas de navegación y confirmación con fixtures aisladas.
- backend/tests/ui_stage3.cjs: incorpora esas pruebas al recorrido del huerto.
- backend/tests/ui_stage2.cjs y ui_local_registration.cjs: confirman la salida explícitamente en sus recorridos.
- docs/MEJORAS-DE-ACCESO.md: entrega acumulativa.

Comprobaciones realizadas:
- 161 comprobaciones de navegador del huerto, navegación y cierre de sesión aprobadas; además 3 aserciones existentes de lectura concurrente aprobadas.
- 64 comprobaciones de acceso/recuperación/cambio y 48 de registro/verificación aprobadas.
- Anchos 320, 390, 768, 1024 y 1440 px, sin desbordamiento horizontal. Se comprobaron foco inicial y retorno, teclado, Escape, contención modal, altura táctil y movimiento reducido.
- Navegación con respuestas lentas y cambios rápidos: ninguna pantalla intermedia de comprobación ni sustitución del encabezado/menú; respuestas antiguas no pisan el destino actual.
- Fallo de comprobación de sesión y sesión vencida: retirada de vistas privadas y regreso al acceso. Fallo de salida: sesión conservada y reintento disponible. Confirmación exitosa: una única solicitud efectiva de salida y retiro de la interfaz privada.
- Sintaxis JavaScript de los archivos modificados y git diff --check sin errores; advertencias previas de finales de línea conservadas.
- El servidor habitual entregó los cinco recursos del frontend idénticos a sus archivos actualizados. URL: http://127.0.0.1:8766/index.html#huerto.

Pruebas sobre PostgreSQL aislado y correo en memoria, sin capturas, mensajes reales, cambios a la cuenta de Rafael, migraciones, publicación o push. La comprobación final de recursos estuvo temporalmente impedida por un fallo de revisión automática de permisos debido a uso; se completó tras la indicación de continuar. No quedan comprobaciones bloqueadas de esta entrega. La revisión personal se realiza recargando con Ctrl+F5. No se avanza a llaves de acceso ni a otra etapa.


### Revisión adaptable — 17-10-2026

Se revisaron teléfono, horizontal, tablet y escritorio en once tamaños. Se corrigieron la altura táctil de botones privados y el título de portada que podía quedar bajo el encabezado en horizontal. Informe, archivos, pruebas y límites: [Revisión responsiva](REVISION-RESPONSIVA.md). Revisión de 209 combinaciones sin incidencias geométricas o JavaScript; 81 comprobaciones del recorrido de registro aprobadas. Comprobaciones en Chromium con base aislada, sin capturas, correo real, publicación ni avance a otra etapa.


### Mi huerto sin membresia y vinculacion visual — 17-10-2026

Mi huerto conserva las tarjetas genericas con valores — para cuentas sin membresia y ofrece un dialogo de vinculacion con envio deshabilitado. La API mantiene 403 garden-unassigned; no se conceden permisos ni se inventa conectividad. [Entrega, MVC, pruebas y pendientes](HUERTO-SIN-ASIGNACION-Y-VINCULACION-VISUAL.md). Se conservan errores recuperables y datos autorizados.

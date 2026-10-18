# Etapa 3 — Mi huerto, Avisos y Mi cuenta

17-10-2026. Carpeta activa: `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`.
Rama main, HEAD f5605359cdff0fb596a63cfc0c352026fb5060e2; cambios previos del equipo conservados. Sin commit, push, publicación, capturas o cambios en Notion.

## Resultado y límites

Se conectó el huerto persistido y sus tres zonas, la lista/detalle de avisos y su lectura por usuario. Mi cuenta conserva perfil, cambio de contraseña, cierre y autoridad de correo de allauth de Etapa 2. Cada API privada comprueba cuenta activa, verificación y, para huerto/avisos, membresía activa al huerto principal.

Sin lecturas físicas ni contrato definitivo de electrónica aprobado, el servidor presenta estado waiting, números/fechas null y flotador unknown. Los nombres del huerto y las zonas sí se consultan en PostgreSQL. No se crean tablas de sensores/lecturas/actuadores, ingesta, calibración, umbrales, offline/stale automáticos ni valores de muestra. El contrato visual conserva tres humedades de sustrato, temperatura/humedad ambiental del DHT22 y estado binario de flotador. No se incorpora óptico ni ventilador.

Los avisos se consultan realmente en PostgreSQL. Se añadió persistencia y lectura por usuario, sin generar avisos ni datos iniciales en la base principal. Leer un aviso no modifica su resolución ni ninguna condición física. El servidor no expone creación/resolución de avisos, riego, comandos o notificaciones.

Rafael eligió conservar los accesos y el contenido visual existente, con disponibilidad para funciones aplazadas. Se mantienen las cuatro entradas y los enlaces de Privacidad/Seguridad/legales. IA sigue informativa; ARCO y llaves muestran explicación breve y controles deshabilitados, sin acuses, credenciales o interacciones simuladas. Los textos legales no se modificaron ni se declararon aprobados. Registro continúa cerrado.

## Archivos y responsabilidades MVC

### Modelo y servicios

- **Modificado:** dist/modelo/aplicacion.js: valida íntegramente la respuesta, mantiene nombres persistidos y distingue carga, vacío, no asignado y error; rechaza avisos incompletos/duplicados/estados desconocidos.
- **Modificado:** dist/modelo/servicio-aplicacion.js: transporte real de huerto, lista/detalle y PUT de lectura; no utiliza perfil como sustituto del dominio; comprueba confirmación/id/objeto antes de actualizar.
- **Modificado:** dist/modelo/servicio-acceso.js: disponibilidad de llaves en false y descarte del perfil de memoria al perder sesión.
- **Modificado:** dist/modelo/servicio-privacidad.js: disponibilidad explícita false, sin envío/expedientes reales.
- **Modificado:** backend/huerto/models.py: Aviso y AvisoLeido, referencias protegidas, restricciones de severidad, fechas y unicidad. Fecha del aviso requerida; no se inventa el momento de un evento físico.
- **Modificado:** backend/huerto/services.py: resolución del huerto principal por membresía, proyección sin lecturas, consultas acotadas y lectura transaccional idempotente.
- **Creado:** backend/huerto/migrations/0003_avisos.py: esquema de ambas tablas e índices/restricciones mediante Django.
- **Creado:** backend/huerto/migrations/0004_relaciones_avisos.py: comprueba pertenencia zona/huerto también al evitar full_clean; impide reasignar avisos y lecturas.

### Controladores y API

- **Modificado:** dist/controlador/aplicacion.js: consulta real según lista/detalle, estado de carga y actualización solo con respuesta confirmada; maneja aviso eliminado o membresía retirada.
- **Modificados:** dist/controlador/privacidad.js y dist/controlador/seguridad.js: conservan rutas y vistas, presentan disponibilidad y bloquean envíos/creaciones aplazadas.
- **Creado:** backend/huerto/api.py: endpoints del dominio, identidad por sesión, autorización, validación de ID/cuerpo, errores neutrales, CSRF global y no-store.
- **Modificado:** backend/cuentas/api.py: gardenAssigned se refiere al huerto principal que sirve /actual.
- **Modificado:** backend/config/urls.py: conecta las cuatro rutas del dominio, sin añadir ingesta ni APIs de funciones aplazadas.

### Vistas y arranque

- **Modificado:** dist/vista/paginas.js: reutiliza estado de carga sin presentar ausencia antes de consultar. Tarjetas/métricas conservadas.
- **Modificado:** dist/vista/aplicacion.js: estado Sin huerto asignado también en Avisos.
- **Modificados:** dist/vista/privacidad.js y dist/vista/seguridad.js: un bloque reutilizable de disponibilidad con estilos existentes.
- **Modificado:** dist/index.html: invalida caché de los scripts cambiados. Continúa una sola entrada sin desarrollo.
- CSS, Geist, logo, imágenes, Blender, estructura y contenido de términos/aviso legal se conservaron.

### Pruebas y documentación

- **Creado:** backend/tests/test_garden_integration.py: 24 casos de permisos, datos ausentes, lectura y restricciones.
- **Creado:** backend/tests/ui_stage3.cjs: 65 comprobaciones de navegador en las mismas vistas, sin capturas.
- **Modificado:** backend/tests/ui_stage2.cjs: adapta únicamente la expectativa de disponibilidad ARCO; vuelve a comprobar 64 casos de acceso.
- **Modificado:** backend/tools/comprobar_frontend.py: reutiliza la ejecución aislada con --etapa 2 o 3, añade fixtures/lectura concurrente y las retira sin tocar la base principal.
- **Modificados:** README.md, backend/README.md, docs/INTEGRACION-BACKEND.md, docs/CONTRATOS-INTEGRACION-LOCAL.md y docs/SEGURIDAD-Y-VERIFICACION-LOCAL.md: estado vigente, contratos, seguridad y responsables.
- **Creados:** este documento y docs/EVIDENCIA-ETAPA-3-LOCAL.json.

No se cambió la arquitectura ni se movieron archivos. El frontend mantiene modelo/transporte, vista y controlador; el backend separa modelos, servicios y vistas de API. Las credenciales externas y las migraciones anteriores se preservan.

## Contrato ejecutado

Un origen: [El Chilito](http://127.0.0.1:8766/index.html). Sesión de Django en cookie HttpOnly; no user_id/huerto_id elegidos por el navegador. Respuestas privadas no-store.

| Método/ruta | Resultado y permisos |
| --- | --- |
| GET /api/huertos/actual | Cuenta verificada + membresía activa a clave principal. status:waiting, nombre y tres zonas persistidas; lecturas null/missing y fechas null; tank.state:unknown. |
| GET /api/huertos/actual/avisos | Mismo permiso. status:ready, items:[...] completa y ordenada por creado_en/id descendentes. items:[] confirma ausencia real. |
| GET /api/huertos/actual/avisos/:id | Mismo permiso y aviso perteneciente al huerto. status:ready,item. ID ajeno/inexistente/inválido: 404 idéntico, sin contenido ajeno. |
| PUT /api/huertos/actual/avisos/:id/lectura | CSRF y permiso revalidados. Cuerpo {} (otros campos: 400). Persiste AvisoLeido único aviso/usuario. Devuelve status:accepted,id,read:true,readAt y item actualizado tras la transacción. |

GET /api/cuenta conserva email/verified desde allauth y gardenAssigned propio. La cuenta sin huerto puede consultar perfil/cambiar contraseña/cerrar; las APIs del huerto devuelven 403 garden-unassigned sin revelar nombre/ID. No hay membresía automática, ni excepción para staff.

401: sesión ausente/inactiva; 403 verification-required: revocada/no verificada; 403 garden-unassigned: cuenta sin permiso del huerto principal; 404 notice-not-found: aviso no disponible; 503: consulta/configuración no disponible. Una zona ausente no se rellena: devuelve garden-configuration-unavailable. Un fallo de DB/API o JSON incompleto nunca se traduce a vacío válido.

El adaptador descarta perfil en memoria ante 401/verificación revocada y retira el contenido privado al navegar al acceso. Un fallo de red no afirma que la sesión se haya cerrado. No se reintentan mutaciones automáticamente.

Aviso contiene: id textual; title,description,recommendation,zone; createdAt,resolvedAt; importance high/medium/info, condition active/resolved, read booleano por usuario. Severidad persistida critico/advertencia/informacion tiene mapeo explícito; SQL y cliente rechazan valores ajenos. No se convierte un registro malformado en informativo ni se elimina para simular una lista vacía.

Sin paginación nueva ni filtros de servidor: se conserva la lista completa y los filtros actuales. Si el volumen crece, acordar paginación y límites antes de recortar silenciosamente resultados.

## Persistencia, permisos y concurrencia

Dos migraciones incrementales aplicadas primero en el_chilito_test y después en el_chilito con sus respectivos roles migradores. Total: 30 migraciones. El rol normal el_chilito_app continúa sin CREATE/ALTER ni permisos administrativos. Sin borrar/recrear bases, tablas previas o volúmenes.

Aviso.zona debe pertenecer al mismo huerto; triggers migrados también cubren bulk_create/update. Aviso.huerto/zona y AvisoLeido.aviso/usuario no se reasignan. FK PROTECT y unicidad aviso/usuario protegen relaciones.

La lectura bloquea la membresía y el aviso dentro de transaction.atomic, consulta por el huerto autorizado y utiliza get_or_create con restricción única. La respuesta se entrega tras el retorno/commit del servicio. Una repetición conserva el primer leido_en. Dos conexiones simultáneas produjeron una sola fila y el mismo readAt. Esto no equivale a pruebas de carga o a ingesta IoT.

La base principal termina con un huerto, tres zonas, cero cuentas/membresías/avisos/lecturas de avisos. Ninguna fixture del navegador se inserta allí.

## Verificación de esta revisión

- **81 pruebas Django aprobadas**, incluidas las 24 nuevas y la regresión del acceso previo, en PostgreSQL aislado.
- **65 comprobaciones del dashboard aprobadas**: sin lecturas/cero ficticio, tres plantas, nombres largos, cinco anchos (320,390,768,1024,1440), cuatro destinos y navegación inferior, lista/filtros/detalle, texto escapado, aviso ajeno, lectura persistente tras recarga, error de escritura sin éxito, vacío válido frente a fallo y JSON incompleto, limpieza de perfil al perder sesión, disponibilidad, teclado y movimiento reducido.
- **64 comprobaciones de acceso aprobadas** sobre la versión actual: portada/legal/móvil, validaciones, login/restauración/cierre/cambio y rechazo legal, sin atajos ni código visible.
- **3 aserciones de concurrencia aprobadas** con dos conexiones independientes: ambas confirmadas, mismo timestamp, una sola fila.
- Sin capturas, correos reales adicionales ni contacto de terceros. Fixtures y servidor temporal retirados. Recursos gráficos/CSS/legal comparados por huella con el comienzo de la etapa.
- El reinicio efectuado fue únicamente del servidor de la aplicación para cargar endpoints nuevos. No sustituye la prueba integral de persistencia/reinicio/restauración prevista en Etapa 4.

Reproducir desde backend:

```powershell
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py test --verbosity 1
$env:NODE_PATH='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\rafae\AppData\Local\ms-playwright'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_frontend.py --etapa 3
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_frontend.py --etapa 2
```

Las dos baterías usan solo la base/rol de pruebas y correo en memoria. 8768 existe temporalmente para automatización; no es otra aplicación de demostración. No ejecutar baterías simultáneamente sobre esa base.

Para iniciar el resultado normal:

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
```

## Pendientes y responsables

- Rafael: backend, contratos, correo, autorización de cuentas/membresías y futura integración de IA. Carolina: PostgreSQL y logo. Rafael/Gabriela: frontend/revisión visual.
- Responsable de datos, aprobación/versiones legales y evidencia de aceptación: pendientes; registro cerrado. No se creó una cuenta o contraseña de muestra para sortearlo.
- ARCO, IA y llaves reales: aplazados, con accesos conservados y disponibilidad explícita según la decisión de Rafael. No WebAuthn, credenciales, PIN propio, captura de biometría o envío de solicitudes.
- Documento definitivo de electrónica/firmware, autenticación de dispositivo, procedencia/calidad/calibración, reloj y frecuencia: pendientes. Las notas históricas con BME280/óptico no sustituyen las decisiones actuales DHT22/flotador. No se alteró el hardware.
- Canales de ingesta, lecturas físicas, generación real de avisos, notificaciones, actuadores y sus controles seguros: pendientes de entregas explícitas posteriores; no operativos por tener tablas de avisos.
- Etapa 4 no iniciada: respaldo/restauración aislada, reinicios integrales, revisión de CI y entrega final requieren solicitud. Teléfono físico/lector de pantalla y pruebas de carga siguen pendientes.

La trazabilidad usa riesgos R-xx propios de SEGURIDAD-Y-VERIFICACION-LOCAL.md. Se conservan SSDF 1.1, ASVS 5.0.0 y WSTG 4.2 como línea base parcial; no se declara conformidad integral o seguridad del firmware. Referencias de implementación: [transacciones/locks y get_or_create de Django 5.2](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update), [restricciones de Django 5.2](https://docs.djangoproject.com/en/5.2/ref/models/constraints/).

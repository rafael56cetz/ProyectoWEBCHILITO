# Inventario de la interfaz · estado tras la fase 7

Describe lo que existe hoy en el código: rutas del navegador, pantallas, el archivo que las dibuja y los endpoints que usan. Las rutas, pantallas y endpoints salen de `frontend/modelos/comun.js`, `frontend/controladores/enrutador.js` y `backend/config/urls.py`. El aspecto (portada y acceso en vidrio oscuro, panel crema con menú verde y tarjetas de vidrio claro) se conserva; los valores de color, sombra, radio y tamaño están en `frontend/vistas/estilos/tokens.css`.

## 1. Organización del frontend

`index.html` carga, en este orden, `modelos/`, `vistas/` y `controladores/` como scripts clásicos (sin módulos ni empaquetador). Los archivos llevan una versión en la URL (`?v=mvc.N`) para que el navegador no use copias viejas.

| Dominio | Modelo | Vista | Controlador |
|---|---|---|---|
| Portada, legales públicos, cookies, contacto | `modelos/publico.js`, `modelos/comun.js` (`PrivacyModel`) | `vistas/publico.js` | `controladores/publico.js` |
| Acceso, segundo paso, seguridad, perfil, privacidad de la cuenta | `modelos/cuenta.js` | `vistas/cuenta.js` | `controladores/cuenta.js` |
| Marco del panel, avisos, tablas y calendario compartidos | `modelos/comun.js` (`AppModel`, `AppService`) | `vistas/comun.js`, `vistas/navegacion.js` | `controladores/administracion.js` (`AppController`), `controladores/enrutador.js` |
| Huerto, plantas, telemetría, mantenimiento, soporte, guías, mantenimientos de administración | `modelos/huerto.js` | `vistas/huerto.js` | `controladores/huerto.js` |
| Inventario de equipos | `modelos/equipos.js` | `vistas/equipos.js` | `controladores/equipos.js` |
| Flota, consola, solicitudes, ventas, administradores, textos legales, consentimientos | `modelos/administracion.js` | `vistas/administracion.js` | `controladores/administracion.js` |

Estilos: `tokens.css` (valores), `base.css`, `acceso.css`, `navegacion.css`, `panel.css`, `cookies.css` y `apariencia.css` (ajustes del panel). Fuentes e imágenes en `vistas/fuentes/` y `vistas/imagenes/`.

## 2. Rutas del navegador

### Públicas

| Ruta | Pantalla |
|---|---|
| `#inicio`, `#el-proyecto`, `#prototipo`, `#consiguelo`, `#como-funciona` | Secciones de la portada (la ventana «Cuéntanos qué quieres saber» envía `POST /api/contacto`) |
| `#terminos`, `#privacidad`, `#cookies` | Texto vigente de cada documento, leído de la base y saneado en el servidor |

### Acceso

| Ruta | Pantalla |
|---|---|
| `#acceso`, `#registro`, `#verificar`, `#recuperar`, `#restablecer` | Inicio de sesión, alta, verificación de correo, recuperar y elegir contraseña nueva |
| `#segundo-paso`, `#sin-acceso` | Segundo factor y ayuda si no se tiene |
| `#aceptar-legales` | Aceptación de textos nuevos; con textos pendientes es la única pantalla privada disponible |

### Persona usuaria

| Ruta | Pantalla |
|---|---|
| `#huerto` | Resumen del huerto, tres plantas, riego y órdenes (`?h=<id>` elige el huerto) |
| `#huerto/nuevo`, `#huerto/vincular`, `#huerto/plantas/<n>` | Crear huerto, vincular el equipo con un código, ficha de planta |
| `#telemetria`, `#mantenimiento`, `#soporte` | Panel técnico, cuidados (con guías) y soporte técnico |
| `#avisos`, `#avisos/<id>` | Lista y detalle de avisos |
| `#cuenta`, `#cuenta/huertos`, `#cuenta/seguridad`, `#cuenta/privacidad`, `#cuenta/contrasena` | Perfil, mis huertos, segundo factor y llaves, privacidad y eliminación, cambio de contraseña |

Redirecciones que se conservan para enlaces viejos: `#asistente` y `#huerto/avisos` → `#huerto`/`#avisos`; `#derechos-arco` → `#privacidad`.

### Administración (`#admin/<destino>`)

El menú agrupa los destinos; cada uno aparece solo con su capacidad y el servidor la exige de nuevo en cada endpoint.

| Grupo | Ruta | Capacidad | Pantalla | Archivos |
|---|---|---|---|---|
| Operación | `#admin/flota` | `ver_flota` | Telemetría de flota: totales, tendencias de 7 días, tabla y problemas | `FleetViews/Controller` |
| Operación | `#admin/soporte` | `atender_soporte` | Consola remota: bandeja, atender, conectar, órdenes, resolver | `ConsoleViews/Controller` |
| Operación | `#admin/mantenimientos` | `gestionar_mantenimientos` | Cuidados de todos los huertos: buscar, corregir, anular | `MaintenanceViews/Controller` (`huerto.js`) |
| Gestión | `#admin/solicitudes` | `atender_consultas` | Consultas del producto | `InquiryViews/Controller` |
| Gestión | `#admin/equipos` (y `/<id>`) | `gestionar_dispositivos` | Inventario de equipos: alta, desvincular, rotar credencial, retirar | `EquipmentViews/Controller` |
| Gestión | `#admin/ventas` | `gestionar_ventas` | Ventas, pagos, entregas y notas | `SalesViews/Controller` |
| Gestión | `#admin/guias` | `gestionar_guias` | Guías de cuidado: crear, editar, publicar, retirar | `CareGuideViews/AdminController` (`huerto.js`) |
| Legal | `#admin/legales` (y `/<id>`) | `gestionar_legales` | Textos legales: borradores, vista previa, publicar | `LegalAdminViews/Controller` |
| Legal | `#admin/consentimientos` | `ver_consentimientos` | Bitácora de consentimientos y exportación CSV | `ConsentViews/Controller` |
| Super admin | `#admin/administradores` | `gestionar_administradores` | Altas y bajas de capacidades, historial y actividad | `AdminAccessViews/Controller` |

Rutas retiradas que redirigen: `#admin/vinculacion` → `#admin/equipos`, `#admin/comercial` → `#admin/ventas`, `#admin/consola` → `#admin/soporte`. Un destino desconocido o sin capacidad lleva a `#admin/flota` o al primer destino permitido.

## 3. Cómo se decide el menú

`AppModel.destinations` (persona usuaria) y `AppModel.adminGroups` (administración) son solo presentación. La sesión que devuelve `GET /api/cuenta` trae rol y capacidades; el servidor decide siempre. Una cuenta de administración ve solo los destinos que su capacidad permite más «Mi cuenta»; sin segundo factor activo se la lleva a `#cuenta/seguridad`.

## 4. Elementos compartidos

| Elemento | Dónde |
|---|---|
| Tarjeta de vidrio `.bento-panel`, diálogos `.app-dialog`, pestañas `.account-tabs` | `base.css`, `panel.css`; `vistas/comun.js` (`AdminTableViews.dialog`, `tabs`, `pager`, `table`) |
| Aviso flotante y confirmación | `vistas/comun.js` (`mostrarAviso`, `confirmar`), con `textContent` |
| Calendario de filtros | `vistas/comun.js` (`DateFilterViews`) |
| Campana de avisos | `AppController`: una consulta a `/api/avisos/contador` al cargar y luego cada 60 s; tras leer avisos se vuelve a pedir |
| Peticiones | `ChilitoHTTP` (`modelos/cuenta.js`): CSRF, idempotencia, `X-Chilito-Sondeo` para consultas que no alargan la sesión |

## 5. Endpoints (`backend/config/urls.py`)

Todos devuelven JSON con el formato de `web/respuestas.py`. «Sesión» significa cuenta autenticada, activa y con la propiedad del recurso comprobada en el servidor; las rutas con capacidad exigen además segundo factor. Además de estas, `/_allauth/browser/v1/…` atiende el acceso, el segundo factor y las llaves (django-allauth).

### Persona usuaria: huerto, equipo y soporte

| Ruta | Métodos | Quién |
|---|---|---|
| `/api/guias` | GET | sesión |
| `/api/comandos/<comando_id>` | GET | sesión |
| `/api/huertos` | GET,POST | sesión |
| `/api/huertos/<huerto_id>` | GET | sesión |
| `/api/huertos/<huerto_id>/renombrar` | POST | sesión |
| `/api/huertos/<huerto_id>/archivar` | POST | sesión |
| `/api/huertos/<huerto_id>/ia` | GET | sesión |
| `/api/huertos/<huerto_id>/codigo` | POST | sesión |
| `/api/huertos/<huerto_id>/vinculacion` | GET | sesión |
| `/api/huertos/<huerto_id>/desvincular` | POST | sesión |
| `/api/huertos/<huerto_id>/plantas/<numero>` | GET,POST | sesión |
| `/api/huertos/<huerto_id>/comandos` | POST | sesión |
| `/api/huertos/<huerto_id>/cuidados` | GET,POST | sesión |
| `/api/huertos/<huerto_id>/telemetria` | GET | sesión |
| `/api/huertos/<huerto_id>/bitacora` | GET | sesión |
| `/api/huertos/<huerto_id>/soporte` | GET,POST | sesión |
| `/api/soporte/<caso_id>/revocar` | POST | sesión |
| `/api/soporte/<caso_id>/cancelar` | POST | sesión |
| `/api/autodiagnosticos/<diagnostico_id>` | GET | sesión |

### Cuenta, avisos, privacidad y acceso

| Ruta | Métodos | Quién |
|---|---|---|
| `/api/acceso/configuracion` | ver vista | pública |
| `/api/cuenta` | ver vista | sesión |
| `/api/acceso/verificacion` | ver vista | pública |
| `/api/cuenta/seguridad/totp-qr` | ver vista | sesión |
| `/api/contacto` | ver vista | pública |
| `/api/legales/aceptar` | POST | sesión |
| `/api/dispositivos/vincular` | ver vista | pública |
| `/api/avisos` | GET | sesión |
| `/api/avisos/leer-todos` | POST | sesión |
| `/api/avisos/contador` | GET | sesión |
| `/api/avisos/<aviso_id>` | GET | sesión |
| `/api/avisos/<aviso_id>/leido` | POST | sesión |
| `/api/avisos/<aviso_id>/resuelto` | POST | sesión |
| `/api/cuenta/aceptaciones` | GET | sesión |
| `/api/cuenta/eliminar` | ver vista | sesión |
| `/api/cuenta/eliminar/cancelar` | POST | sesión |
| `/api/cuenta/perfil` | POST | sesión |
| `/api/cuenta/bienvenida` | POST | sesión |
| `/api/privacidad/mis-datos` | POST | sesión |
| `/api/privacidad/documentos/<str:kind>` | ver vista | pública |
| `/api/privacidad/cookies` | ver vista | pública |
| `/api/estadisticas/seccion` | ver vista | pública |

### Administración

| Ruta | Métodos | Quién |
|---|---|---|
| `/api/admin/guias` | GET,POST | `gestionar_guias` |
| `/api/admin/guias/<guide_id>/editar` | POST | `gestionar_guias` |
| `/api/admin/guias/<guide_id>/publicar` | POST | `gestionar_guias` |
| `/api/admin/guias/<guide_id>/retirar` | POST | `gestionar_guias` |
| `/api/admin/equipos` | GET,POST | `gestionar_dispositivos` |
| `/api/admin/equipos/<equipo_id>` | GET | `gestionar_dispositivos` |
| `/api/admin/equipos/<equipo_id>/desvincular` | POST | `gestionar_dispositivos` |
| `/api/admin/equipos/<equipo_id>/rotar` | POST | `gestionar_dispositivos` |
| `/api/admin/equipos/<equipo_id>/retirar` | POST | `gestionar_dispositivos` |
| `/api/admin/administradores` | GET | `gestionar_administradores` |
| `/api/admin/administradores/historial` | GET | `gestionar_administradores` |
| `/api/admin/administradores/actividad` | GET | `gestionar_administradores` |
| `/api/admin/administradores/cuenta` | POST | `gestionar_administradores` |
| `/api/admin/ventas` | GET,POST | `gestionar_ventas` |
| `/api/admin/ventas/resumen` | GET | `gestionar_ventas` |
| `/api/admin/ventas/<venta_id>/pago` | POST | `gestionar_ventas` |
| `/api/admin/ventas/<venta_id>/entrega` | POST | `gestionar_ventas` |
| `/api/admin/ventas/<venta_id>/nota` | POST | `gestionar_ventas` |
| `/api/admin/ventas/<venta_id>/cancelar` | POST | `gestionar_ventas` |
| `/api/admin/legales` | GET,POST | `gestionar_legales` |
| `/api/admin/legales/vista-previa` | POST | `gestionar_legales` |
| `/api/admin/legales/<documento_id>` | GET | `gestionar_legales` |
| `/api/admin/legales/<documento_id>/editar` | POST | `gestionar_legales` |
| `/api/admin/legales/<documento_id>/eliminar` | POST | `gestionar_legales` |
| `/api/admin/legales/<documento_id>/publicar` | POST | `gestionar_legales` |
| `/api/admin/consentimientos` | GET | `ver_consentimientos` |
| `/api/admin/consentimientos/resumen` | GET | `ver_consentimientos` |
| `/api/admin/consentimientos/exportar` | GET | `ver_consentimientos` |
| `/api/admin/flota` | GET | `ver_flota` |
| `/api/admin/soporte` | GET | `atender_soporte` |
| `/api/admin/soporte/<caso_id>` | GET | `atender_soporte` |
| `/api/admin/soporte/<caso_id>/atender` | POST | `atender_soporte` |
| `/api/admin/soporte/<caso_id>/conectar` | POST | `atender_soporte` |
| `/api/admin/soporte/<caso_id>/resolver` | POST | `atender_soporte` |
| `/api/admin/sesiones/<sesion_id>` | GET | `atender_soporte` |
| `/api/admin/sesiones/<sesion_id>/accion` | POST | `atender_soporte` |
| `/api/admin/sesiones/<sesion_id>/cerrar` | POST | `atender_soporte` |
| `/api/admin/mantenimientos` | GET,POST | `gestionar_mantenimientos` |
| `/api/admin/mantenimientos/<cuidado_id>` | GET | `gestionar_mantenimientos` |
| `/api/admin/mantenimientos/<cuidado_id>/corregir` | POST | `gestionar_mantenimientos` |
| `/api/admin/mantenimientos/<cuidado_id>/anular` | POST | `gestionar_mantenimientos` |
| `/api/admin/consultas` | GET | `atender_consultas` |
| `/api/admin/consultas/<inquiry_id>/estado` | POST | `atender_consultas` |

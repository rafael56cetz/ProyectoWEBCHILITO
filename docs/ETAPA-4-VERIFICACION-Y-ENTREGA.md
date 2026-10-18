# Etapa 4 · Verificación y entrega local

Fecha: 17 de octubre de 2026, America/Mexico_City. Carpeta activa: `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`.

Esta entrega verifica las integraciones locales de etapas 1–3. No habilita nuevas funciones, no rediseña el frontend ni declara lista una aplicación pública. Los documentos de etapas anteriores conservan sus resultados históricos; las cifras actuales y límites son los de este documento y [su evidencia](EVIDENCIA-ETAPA-4-LOCAL.json).

## Estado entregado

| Parte | Implementado y verificado | Pendiente |
| --- | --- | --- |
| Acceso | Correo/contraseña con allauth, sesión de servidor, restauración, cierre, perfil propio y cambio de contraseña. | Cuenta real de presentación y membresía asignada explícitamente. La base principal tiene cero cuentas. |
| Verificación y recuperación | Código temporal por sesión, errores, expiración, límites, reenvío que invalida código anterior; enlace de recuperación y rechazo de sesión/contraseña anteriores después del cambio. Pruebas con correo en memoria exclusivamente en base aislada. | Registro público y recorrido de alta real por correo: bloqueados por documentos legales sin aprobación/versiones efectivas. No hay código fijo ni acceso alternativo. |
| Correo | SMTP Gmail de pruebas configurado; un mensaje aceptado y recibido en Recibidos, confirmado por Rafael durante Etapa 2. | Correo definitivo y destinatarios autorizados. No se enviaron correos reales durante Etapa 4. |
| Huerto y Avisos | Nombre y tres zonas persistidos; membresía exigida por el servidor; avisos persistidos y lectura individual idempotente. | No existen avisos, membresías o lecturas físicas en la base principal. Sin generador de avisos ni controles de hardware. |
| Interfaz | Mismas vistas MVC, cuatro entradas principales y navegación inferior móvil. Ausencia de datos distinta de error. | Revisión con lector de pantalla y teléfono físico; no se declara auditoría completa de accesibilidad. |
| IA, ARCO y llaves | Enlaces conservados con disponibilidad y operaciones aplazadas deshabilitadas por decisión de Rafael. | Integración posterior autorizada. Sin respuestas sintéticas, WebAuthn, credenciales o solicitudes ARCO reales. |
| Operación | Arranque único, permisos separados, respaldo/restauración aislada y persistencia tras reinicio. | Despliegue, HTTPS, operación y políticas de respaldo de producción. |

Los textos legales visibles se conservan como presentación. Su existencia no acredita aprobación ni permite registrar consentimiento efectivo. El código corresponde a verificación del correo; el inicio habitual sigue usando contraseña, sin exigir código en cada acceso.

## Arquitectura y fronteras de confianza

Navegador → Django en Windows → PostgreSQL 17 en Docker. Django sirve el mismo dist y la API en un origen local. El navegador solo recibe contratos HTTP, nunca contraseñas de PostgreSQL, clave Django o credenciales SMTP.

- **Modelo frontend:** dist/modelo conserva validación, estados y adaptadores HTTP reales. No toma identidad o permisos de fragmentos de URL ni de almacenamiento local.
- **Vista:** dist/vista y dist/index.html conservan presentación, componentes, Geist, logo, imágenes y estilos. Sin cambios en Etapa 4.
- **Controlador:** dist/controlador coordina rutas, eventos, foco y respuestas. Sin cambios en Etapa 4.
- **Servidor:** cuentas utiliza Django/allauth para identidad y sesión; huerto exige usuario activo/verificado y membresía al huerto principal en cada consulta. Una cuenta verificada no obtiene huerto automáticamente.
- **PostgreSQL:** migraciones definen tablas y restricciones. El rol migrador administra estructura; el rol app tiene DML, sin DDL/superusuario/creación de roles o bases. Las mismas separaciones se usan en pruebas.
- **Correo saliente:** SMTP utiliza configuración privada y destinatario de prueba autorizado. No se envía a terceros durante las pruebas.
- **Dispositivo:** no hay ingesta IoT ni órdenes al ESP32. Contrato físico, firmware, calibración y autenticación del dispositivo siguen pendientes. DHT22, tres sensores de sustrato y flotador no se reemplazan por números generados.

Django escucha en 127.0.0.1:8766; PostgreSQL solo expone 127.0.0.1:5433. HTTP local implica Secure=false en la excepción local; no demuestra cifrado ni sirve como configuración de producción. Cookie de sesión HttpOnly/SameSite, sesión en servidor y CSRF en mutaciones. No JWT en localStorage ni CORS abierto.

## Contratos vigentes

No cambiaron endpoints en esta etapa. Detalles de cuerpos y errores: [Etapa 2](ETAPA-2-ACCESO-Y-CORREO.md) y [Etapa 3](ETAPA-3-DASHBOARD-Y-CUENTA.md).

| Ruta | Método | Autoridad y resultado |
| --- | --- | --- |
| /api/acceso/configuracion | GET | Configuración pública/CSRF; registro cerrado y disponibilidad. |
| /_allauth/browser/v1/auth/login | POST | Correo/contraseña; CSRF y límites. Sesión allauth, no autenticación propia. |
| /_allauth/browser/v1/auth/session | GET, DELETE | Consulta o cierre de sesión del navegador. El 401 con is_authenticated=false tras DELETE confirma cierre según contrato de allauth. |
| /_allauth/browser/v1/auth/signup | POST | 403, registro cerrado; no aceptación de documentos pendientes. |
| /api/acceso/verificacion | GET | Contexto de verificación ligado a la sesión pendiente. |
| /_allauth/browser/v1/auth/email/verify | POST | Código temporal comprobado por allauth, intentos limitados. |
| /_allauth/browser/v1/auth/email/verify/resend | POST | Sesión pendiente, límites y envío autorizado; invalida el código anterior. |
| /_allauth/browser/v1/auth/password/request | POST | Recuperación con respuesta no reveladora, límites y correo autorizado. |
| /_allauth/browser/v1/auth/password/reset | GET, POST | Validación/consumo del enlace de recuperación; no inicia sesión automáticamente. |
| /_allauth/browser/v1/account/password/change | POST | Sesión verificada y contraseña actual/nueva validadas. |
| /api/cuenta | GET, PATCH | Exclusivamente perfil propio verificado; identidad no elegida en el cuerpo. |
| /api/huertos/actual | GET | Usuario activo/verificado y membresía al principal; 401 sin sesión, 403 sin asignación, 503 si falla el servicio. |
| /api/huertos/actual/avisos | GET | Mismo permiso; vacío válido distinto de fallo. |
| /api/huertos/actual/avisos/:id | GET | ID dentro del huerto autorizado; ajeno/inexistente dan 404 neutral. |
| /api/huertos/actual/avisos/:id/lectura | PUT | CSRF, identidad de sesión y membresía; lectura individual idempotente, no resuelve el aviso. |

Las API privadas y validación de recuperación usan no-store. Sin lecturas: value=null, estado missing/unknown, sin fecha de comunicación inventada; no se representa como cero. No se añadió esquema de telemetría en esta etapa.

## Pruebas ejecutadas sobre la versión actual

| Comprobación | Resultado actual |
| --- | --- |
| Django / PostgreSQL aislado | 86 casos, 0 fallidos |
| Acceso en Chromium | 64 comprobaciones, 0 fallidas |
| Huerto/cuenta/navegación en Chromium | 65 comprobaciones, 0 fallidas |
| Lectura concurrente, dos conexiones | 3 aserciones, 0 fallidas; una lectura por usuario/aviso |
| Restauración funcional con rol app de pruebas | 18 comprobaciones, 0 fallidas |
| Persistencia tras reinicios reales | 15 comprobaciones, 0 fallidas |
| Superficie local | 28 recursos/importaciones/fuentes/imágenes, 13 comprobaciones de rutas; todos correctos |
| Sintaxis y configuración | 54 archivos Python analizados; JavaScript activo válido; Django check sin errores; makemigrations --check sin cambios; pip check sin dependencias rotas |
| Git | main, HEAD f5605359cdff0fb596a63cfc0c352026fb5060e2; diff --check sin errores (avisos existentes LF/CRLF). Sin commit, push ni cambio de rama |

Los contadores son casos/aserciones automatizados de alcance distinto; no equivalen al número de requisitos ASVS satisfechos. Las pruebas se volvieron a ejecutar en esta etapa.

Chromium comprobó 320, 390, 768, 1024 y 1440 px: ausencia de desbordamiento horizontal en recorridos, navegación, errores, texto persistido escapado, Tab/foco y movimiento reducido. Sin capturas. No se probó Safari, Firefox, lector de pantalla, todos los dispositivos ni contraste completo por inspección visual.

Cobertura de servidor: login erróneo/inactivo/no verificado, cuotas, código incorrecto/vencido/limitado, reenvío, recuperación inválida/vencida/usada, cambio de contraseña, rotación de sesión, CSRF, logout/reutilización, acceso anónimo, sin membresía/revocada, ID ajeno, permisos DB, restricciones y errores sin datos ficticios. El registro público sigue cerrado; las fixtures de verificación no lo abren.

Las pruebas utilizan el_chilito_test y un servidor efímero 8768. Se retiraron cuentas, huertos, zonas, membresías, avisos, lecturas, sesiones y caché de prueba; el puerto temporal está cerrado. La aplicación del usuario permanece solo en 8766.

## Respaldo y restauración

Respaldo privado comprobado:

- Archivo: C:\Users\rafae\AppData\Local\ElChilito\backups\el_chilito_20261017_2c0bc0e1.dump
- Tamaño: 69 201 bytes.
- SHA-256: 6c6a98a97849353bfec6422297c0653ab75a43373f4423a5e267e5ba91713134
- Origen: el_chilito. Destino nuevo: el_chilito_restore_20261017_2c0bc0e1.
- Propietario del destino: el_chilito_test_migrador. Acceso funcional: el_chilito_test_app, sin DDL.
- 17 tablas, filas y estructura equivalentes; también secuencias antes de la prueba funcional.
- 18 comprobaciones de API/restricciones con fixtures dentro de transacción revertida.
- La base principal conserva exactamente la huella previa al respaldo y reinicio: 30 migraciones, 1 huerto, 3 zonas; 0 cuentas/membresías/avisos/lecturas/sesiones.

Se utilizó pg_dump -Fc y pg_restore en una base nueva con transacción y parada ante errores; no se usó --clean ni se reemplazaron bases o volúmenes. El dump no incluye roles globales ni secretos de configuración. Se verificaron restricciones y aplicación después de restaurar.

El comparador normaliza únicamente el ordinal físico de columnas eliminadas (mantiene orden y tipos de columnas existentes) y una conversión equivalente conocida varchar[]/text[] de aviso_severidad_valida, reanalizada por PostgreSQL al restaurar. Sus tres valores permitidos y el rechazo de un valor inválido se probaron en el destino. Las secuencias se comparan antes de las fixtures porque nextval no se revierte con rollback; después se vuelven a comparar filas y estructura restante. No se declara igualdad de secuencias después de consumir IDs de prueba.

El archivo queda fuera de OneDrive/Git, con ACL de Windows para usuario actual y SYSTEM; **no está cifrado**. Una copia preliminar de diagnóstico, el_chilito_restore_20261017_2274d5e2 y su dump privado del mismo sufijo, se conservó sin borrar. La copia verificada de entrega es la terminada en 2c0bc0e1. No se autorizó limpieza destructiva.

Referencias oficiales: [pg_dump de PostgreSQL 17](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore de PostgreSQL 17](https://www.postgresql.org/docs/17/app-pgrestore.html).

## Persistencia y operación

Se reiniciaron PostgreSQL y el proceso canónico Django, además del servidor Django aislado usado para las aserciones. Sesión, perfil, membresía, huerto, aviso leído y caché de límites sobrevivieron. Las mutaciones de prueba ocurrieron solo en la base aislada; la base principal no cambió.

Versiones observadas: Python 3.13.7; Django 5.2.18; django-allauth 65.20.0; psycopg/psycopg-binary 3.3.6; PostgreSQL 17.11. Las 11 distribuciones resueltas están fijadas en backend/requirements-lock.txt. Entorno Python y secretos fuera de OneDrive, en %LOCALAPPDATA%\ElChilito. Instalación/roles/configuración privada: [manual backend](../backend/README.md). No ejecutar de nuevo el SQL administrativo sobre la instancia existente ni recrear bases para arrancar.

### Abrir o volver a encender

Docker Desktop debe estar iniciado. En PowerShell:

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
```

Una sola dirección: **[El Chilito](http://127.0.0.1:8766/index.html)**. El iniciador espera la salud de PostgreSQL y reconoce el servidor ya iniciado, sin duplicarlo. No utilizar http.server para esta integración.

Si Django se inició en una terminal, Ctrl+C lo detiene; repetir el iniciador lo levanta. Para repetir el reinicio completo verificado (incluye fixtures aisladas y conserva la base principal), con la aplicación ya encendida y sin otras pruebas simultáneas:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" backend/tools/verificar_reinicio_local.py
```

El script comprueba identidad y carpeta servida antes de reiniciar Django. Si encuentra otro proceso/puerto o base inesperada, se detiene; no debe sustituirse por cerrar procesos Python indiscriminadamente.

### Repetir las comprobaciones

Desde cualquier PowerShell, con Docker y dependencias de pruebas disponibles:

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\verificar_entrega.ps1'
```

Este comando ejecuta dependencias, Django, migraciones pendientes, JavaScript, 86 pruebas servidor y los dos recorridos Chromium. No envía SMTP real. Requiere Node/Playwright/Chromium del entorno de revisión; admite NODE_PATH y PLAYWRIGHT_BROWSERS_PATH. Las rutas predeterminadas de herramientas corresponden a este equipo; no forman parte del frontend ni obligan a instalar un framework.

La opción **-Infraestructura** añade respaldo privado, otra base nueva de restauración y reinicio real de servicios. Conserva esas copias; puede interrumpir unos segundos una sesión local y requiere que la base de pruebas esté vacía. No ejecutarla en paralelo con otras pruebas. Los resultados saneados quedan en revision/etapa4-respaldo.json y revision/etapa4-reinicio.json; revision está excluido de Git. La evidencia entregable se conserva en docs/EVIDENCIA-ETAPA-4-LOCAL.json.

No hay pipeline CI remoto configurado en esta copia (.github/workflows, GitLab, Jenkins o Azure). Se añadió la puerta de verificación local reproducible; no se configuraron cuentas remotas ni se hizo push. pip check comprueba coherencia de paquetes, no es una auditoría de vulnerabilidades de dependencias.

## Archivos de esta etapa

| Archivo | Cambio y responsabilidad |
| --- | --- |
| backend/tests/test_final_review.py | Nuevo: cinco casos de regresión de sesión/código/recuperación/caché; reutiliza helpers sin ejecutar duplicada la batería anterior. |
| backend/config/settings/restoration.py | Nuevo: configuración que solo acepta una base nueva de restauración con nombre acotado; no selecciona la principal. |
| backend/tools/revision_local.py | Nuevo: utilidades locales, huellas de filas/esquema, destinos permitidos y servidor aislado. No imprime cuerpos privados. |
| backend/tools/verificar_respaldo_local.py | Nuevo: respaldo fuera del proyecto, restauración nueva y comparación; no borra bases existentes. |
| backend/tools/verificar_restauracion.py | Nuevo: valida el destino con rol restringido y revierte fixtures. |
| backend/tools/verificar_reinicio_local.py | Nuevo: reinicia servicios identificados, comprueba persistencia y retira sus fixtures aisladas. |
| infra/verificar_entrega.ps1 | Nuevo: ejecutor secuencial de comprobaciones, infraestructura opcional explícita. |
| docs/ETAPA-4-VERIFICACION-Y-ENTREGA.md | Nuevo: entrega, arquitectura, operación, resultados y pendientes. |
| docs/EVIDENCIA-ETAPA-4-LOCAL.json | Nuevo: resultados y huellas saneadas, sin contraseñas, códigos, cookies o tokens. |
| README.md, backend/README.md | Modificados: estado vigente y enlaces a comprobación/entrega; historia preservada. |
| docs/INTEGRACION-BACKEND.md, docs/CONTRATOS-INTEGRACION-LOCAL.md | Modificados: referencia vigente de Etapa 4, sin cambiar contratos anteriores. |
| docs/SEGURIDAD-Y-VERIFICACION-LOCAL.md | Modificado: trazabilidad parcial y límites de verificación. |

No se movieron/renombraron/eliminaron archivos existentes. HTML/CSS/JavaScript, recursos y migraciones se conservan respecto al inicio de esta etapa. Los archivos de verificación están fuera del arranque de la aplicación. Se preservan los cambios manuales y el trabajo previo sin atribuirlos a Etapa 4.

## Decisiones y responsabilidades pendientes

Rafael: backend, operación local, remitente definitivo e integración posterior. Carolina: PostgreSQL y logo. Rafael y Gabriela: frontend/revisión visual. Responsable de datos, aprobación legal, versiones efectivas y procedimiento de acreditación ARCO: pendientes; no se modificó Notion.

Antes de habilitar registro: aprobar documentos y versiones, definir responsable, implementar y comprobar evidencia de aceptación de la versión efectiva, autorizar correo y probar alta real de extremo a extremo. Esta entrega no inventa ese consentimiento ni crea una cuenta/contraseña de muestra. Registrar/verificar una cuenta no asigna el huerto.

Siguen aplazados IA, ARCO, passkeys, telemetría/órdenes reales, políticas de borrado/retención, HTTPS/despliegue, correo definitivo y revisión de seguridad/accesibilidad de producción. No hay autorización implícita para la siguiente etapa.

# El Chilito · Aplicación web

> **Dashboard actual (17-10-2026):** una cuenta sin membresia ve la estructura generica de Mi huerto y el dialogo visual de vinculacion; la API conserva 403 garden-unassigned. No hay asociacion de equipos ni permisos automaticos. [Entrega y comprobaciones](docs/HUERTO-SIN-ASIGNACION-Y-VINCULACION-VISUAL.md). Las descripciones anteriores que sustituian todo el dashboard por Sin huerto asignado quedan como historia.

> **Etapa B vigente — registro local con cualquier correo válido.** Ya no se autoriza cada destinatario manualmente. Se mantienen casilla, verificación por código, límites y acceso únicamente desde esta computadora. Rafael confirmó su registro y código reales. Los documentos continúan pendientes y no se asigna un huerto automáticamente. 57 pruebas Django y 48 comprobaciones de navegador aprobadas para esta actualización. Ver [cambio, configuración y comprobaciones](docs/MEJORAS-DE-ACCESO.md). C no iniciada; las notas posteriores conservan la historia de las entregas anteriores.

> **Actualización: Etapa A de ayuda de contraseñas.** Contador Unicode, mínimo/coincidencia y máximo del contrato existente en registro, recuperación y cambio. Se conservan espacios al entrar/cambiar/recuperar mediante allauth. 93 pruebas Django, 69 comprobaciones nuevas de navegador y regresiones de acceso/dashboard aprobadas. [Entrega acumulativa, archivos y revisión](docs/MEJORAS-DE-ACCESO.md). Registro todavía cerrado; B y C no iniciadas. Los resultados del hito Etapa 4 conservados debajo corresponden a su revisión anterior.

## Estado vigente: Etapa 4 de integración local verificada

Django sirve el frontend original, acceso y dominio en un solo origen. Mi huerto y Avisos usan PostgreSQL con permisos por cuenta/huerto. Se verificaron sesión, recuperación, perfil, lectura individual, respaldo/restauración aislada y persistencia tras reiniciar servicios. Sin lecturas físicas, las mediciones siguen vacías y el flotador es desconocido.

Se conservan cuatro entradas, navegación inferior móvil, Geist, Liquid Glass, logo y recursos. IA, ARCO y llaves conservan sus accesos y disponibilidad; sus operaciones aplazadas están deshabilitadas. **Registro cerrado** hasta aprobar documentos/versiones legales. La base principal tiene cero cuentas y membresías; no hay contraseña ni entrada de muestra.

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
```

Abrir **[El Chilito](http://127.0.0.1:8766/index.html)**. Docker Desktop debe estar iniciado; el script espera PostgreSQL y evita servidores duplicados. No usar http.server para esta aplicación.

- [Etapa 4: entrega, archivos, arquitectura, reinicio y pendientes](docs/ETAPA-4-VERIFICACION-Y-ENTREGA.md).
- [Evidencia actual saneada](docs/EVIDENCIA-ETAPA-4-LOCAL.json).
- [Configuración e instalación del backend](backend/README.md).
- [Contratos de acceso/correo](docs/ETAPA-2-ACCESO-Y-CORREO.md) y [huerto/avisos](docs/ETAPA-3-DASHBOARD-Y-CUENTA.md).

**86 pruebas Django + 64 comprobaciones de acceso + 65 del dashboard + 3 aserciones concurrentes, todas aprobadas.** Restauración: 17 tablas equivalentes y 18 comprobaciones funcionales. Reinicio: 15 comprobaciones aprobadas. Base principal preservada. Sin capturas, commit, push ni despliegue.

Para repetir la batería, con las dependencias de revisión instaladas:

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\verificar_entrega.ps1'
```

La opción -Infraestructura añade un respaldo, una base nueva de restauración y reinicio real. Ver efectos/requisitos en la entrega; no ejecutar pruebas simultáneas. No existe CI remoto configurado. Rafael: backend; Carolina: PostgreSQL/logo; Rafael y Gabriela: frontend. Etapa 4 cerrada en su alcance local, sin avanzar a nuevas funciones.

## Documentación anterior de la entrega visual

Las secciones siguientes conservan la historia del frontend independiente. Su mención a «solo frontend», a backend no autorizado y a 28 pruebas corresponde a esa entrega anterior; el estado vigente de Etapa 4 se documenta arriba. El acceso vacío también había cambiado manualmente antes de integrar, según la revisión de Etapa 0.

**Carpeta activa:** `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`

**Una aplicación, una entrada:** `dist/index.html`. Para abrir el proyecto en Codex selecciona la carpeta activa completa, no solo `dist`.

## Abrir

Desde PowerShell:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web'
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

Abrir **[El Chilito](http://127.0.0.1:8766/index.html)**. Si ese servidor ya está encendido, utiliza el enlace; no abras otro en el mismo puerto. El servidor solo escucha en este equipo y no publica el proyecto.

## Recorrer el frontend

- **Acceso libre:** «Iniciar sesión» abre Mi huerto con los campos vacíos, cualquier texto o datos inventados, mediante clic y Enter. «Cerrar sesión» regresa al formulario. No se leen para autenticar ni se envían credenciales; no existe una cuenta real.
- **Cuatro destinos:** Mi huerto, Avisos, Asistente y Mi cuenta. Desde Mi cuenta se entra a Privacidad y Seguridad. El huerto mantiene sus métricas esperando datos; Avisos muestra el estado vacío de la simulación.
- **Registro:** conserva correo con formato válido, confirmación de contraseña y aceptación de términos sin premarcar. Los documentos permanecen pendientes. Tras el registro ficticio, el formulario muestra el código de simulación `246810`. La verificación ofrece crear una llave o «Ahora no», que continúa al huerto.
- **Recuperación:** escribe un correo inventado con formato válido. El resultado indica que no se envió un correo y permite «Revisar cambio de contraseña». Utiliza la misma pantalla de cambio ya diseñada; no se guarda una contraseña.
- **ARCO:** desde el pie/aviso o Privacidad, utiliza solo datos ficticios. El acuse y el seguimiento son simulaciones temporales. El detalle de ejemplo pendiente de información permite probar la aclaración autorizada.
- **Llaves:** desde Seguridad puedes crear/quitar ejemplos, con confirmación al quitar. La alternativa del formulario de acceso recorre los pasos ficticios sin usar huella, rostro, PIN o WebAuthn.

No hay una barra permanente de escenarios ni una segunda página de revisión. Los casos de error se conservan en herramientas de pruebas. Recargar reinicia los ejemplos de ARCO y llaves; no se persisten contactos, descripciones, contraseñas, códigos o sesiones.

## Organización MVC

| Carpeta/archivo | Responsabilidad |
| --- | --- |
| `dist/index.html` | Única entrada y orden de carga |
| `dist/vista/` | Plantillas/presentación compartidas, logo e iconos |
| `dist/vista/css/` | Estilos existentes: Geist, Liquid Glass y adaptaciones |
| `dist/vista/img/`, `dist/vista/fonts/` | Imágenes y fuente local con licencia |
| `dist/controlador/` | Navegación, eventos, coordinación, foco y cancelación |
| `dist/modelo/` | Datos, estados, validación y fronteras futuras de servicios |
| `dist/desarrollo/` | Respuestas ficticias separadas del transporte futuro; composición explícita del prototipo |
| `docs/` | Entregas, contratos, cierre y organización vigente |
| `revision/` | Pruebas/evidencias locales, sin una aplicación navegable |
| `revision/historico/` | Pruebas anteriores y entrada/barra retiradas conservadas como texto |

La navegación libre depende de `previewNavigation:true`. Los controladores conservan su valor predeterminado `false` y sus validaciones para el futuro. `dist/desarrollo/inicio.js` inyecta las respuestas sintéticas con las mismas vistas y controladores; no es una autenticación para producción. Los adaptadores `AuthService`, `PrivacyService` y `AppService` originales permanecen separados y desconectados.

Antes de integrar un backend habrá que sustituir explícitamente esa composición, retirar la entrada libre y validar identidad/permisos en servidor. Los parámetros de URL no deciden transporte, escenarios o identidad.

## Origen, copia e historial

La carpeta anterior `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO` queda **como respaldo, sin borrar ni modificar durante este traslado**. Deja de ser la fuente activa. La copia incluyó las etapas 1–4, el ajuste posterior `previewNavigation`, recursos, documentación, historial/configuración Git, archivos sin seguimiento y herramientas/evidencias. Se verificaron las huellas de 121 archivos y equivalencia de HEAD, rama, remoto y cambios locales antes de ajustar el destino.

Solo se excluyeron tres logs de depuración/servidor. No se encontraron entornos, cachés o archivos de secretos que requirieran traslado. Las dependencias de pruebas instaladas en el equipo no forman parte del frontend.

No se hizo commit/push ni se cambió el remoto. Los cambios recientes siguen siendo locales; un clon de GitHub no equivale automáticamente a esta carpeta. `revision/` sigue excluida de Git por la regla existente, pero sus archivos sí están en esta copia verificada.

## Documentación y comprobaciones

- [Organización, copia verificada y unificación](docs/ORGANIZACION-Y-ENTRADA-UNICA.md).
- [Guía de integración futura](docs/INTEGRACION-BACKEND.md), con nota del arranque actual.
- [Cierre histórico de etapas 1–4](docs/CIERRE-INTEGRACIONES-FRONTEND.md).
- [Etapa 1](docs/ENTREGA-ETAPA-1.md), [etapa 2](docs/ENTREGA-ETAPA-2.md), [etapa 3](docs/ENTREGA-ETAPA-3.md).

Pruebas actuales desde esta raíz, con Node/Playwright y navegadores disponibles:

```powershell
node revision/comprobar-integraciones.cjs
```

En este equipo Playwright está en el runtime de herramientas; el documento de organización indica las variables de ejecución. Las baterías de dos servidores se preservan como históricas y no se presentan como válidas para el arranque unificado. Los resultados nuevos están en `revision/resultado-unificacion.json` y sus informes individuales: **28 comprobaciones aprobadas, 0 fallidas**. La preservación de archivos y Git, los recursos servidos y la entrada única están registrados en `revision/verificacion-traslado-final.json`.

**Solo frontend.** Backend, PostgreSQL y cambios por componentes/electrónica todavía no están autorizados. No se implementaron correos, servicios reales, WebAuthn o conexión IoT. Responsabilidades vigentes: Rafael, backend; Carolina, PostgreSQL; Rafael y Gabriela, frontend/revisión visual. Los documentos legales, responsable de datos, acreditación ARCO y configuración de integración siguen pendientes.

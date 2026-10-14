# El Chilito · Frontend principal

Diseño principal de la web de El Chilito, preparado para integrar el backend. Incluye la portada, acceso, registro, verificación, recuperación, Mi huerto, Avisos, Asistente y Mi cuenta. Conserva el logo actual sin recuadro, Geist y los estilos Liquid Glass existentes.

**Punto de entrada: `dist/index.html`.** Los archivos de `dist/` son el código fuente editable; no se requiere compilación, Node ni un framework.

## Abrir en local

Con Python 3 instalado, desde la raíz de este repositorio:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

Abrir <http://127.0.0.1:8766/index.html> en el navegador. Este comando solo sirve los archivos estáticos; no implementa el backend de El Chilito.

## Estado del acceso

**Todavía no hay cuentas ni contraseñas funcionales.** El adaptador normal de acceso devuelve «servicio no disponible» hasta que se integre el backend. No se incluyeron credenciales, datos de prueba ni el modo de demostración.

Para revisar directamente la presentación de cada pantalla se puede abrir la ruta correspondiente, por ejemplo <http://127.0.0.1:8766/index.html#huerto>. Las vistas privadas no tienen datos reales ni autorización implementada; abrir una ruta no concede permisos sobre un dispositivo.

| Pantalla | Ruta |
| --- | --- |
| Portada | `#inicio` |
| Inicio de sesión | `#acceso` |
| Registro | `#registro` |
| Verificar correo | `#verificar` |
| Recuperar acceso | `#recuperar` |
| Restablecer contraseña | `#restablecer` (requiere enlace válido del futuro servicio) |
| Mi huerto | `#huerto` |
| Avisos / detalle | `#avisos` / `#avisos/:id` |
| Asistente | `#asistente` |
| Mi cuenta / contraseña | `#cuenta` / `#cuenta/contrasena` |

El enlace antiguo `#huerto/avisos` redirige a Avisos. Los destinos legales heredados siguen siendo provisionales.

## Organización MVC

```text
dist/
├── index.html                    Entrada: carga modelos, vistas y controladores
├── favicon.svg
├── modelo/
│   ├── acceso.js                 Validaciones y configuración del acceso
│   ├── aplicacion.js             Datos, estados y normalización para las vistas
│   ├── servicio-acceso.js        Punto de integración de autenticación
│   └── servicio-aplicacion.js    Punto de integración de huerto, avisos y perfil
├── vista/
│   ├── paginas.js                Portada, logo compartido y tarjetas del huerto
│   ├── acceso.js                 Formularios y resultados de acceso
│   ├── aplicacion.js             Navegación privada, Avisos, Asistente y Mi cuenta
│   ├── icons.js                  Iconos compartidos
│   ├── css/                      Estilos base y ajustes de acceso/aplicación
│   ├── fonts/                    Geist y su licencia
│   └── img/                      Imágenes utilizadas por la web actual
└── controlador/
    ├── site.js                   Rutas y coordinación de pantallas
    ├── navigation.js             Encabezado, anclas y foco
    ├── acceso.js                 Eventos y respuestas de los formularios
    └── aplicacion.js             Consultas, filtros, lectura de avisos y cierre
docs/
└── INTEGRACION-BACKEND.md         Guía de conexión para Kevin
```

Esta entrega contiene una sola versión del diseño. Se excluyeron demostraciones, escenarios ficticios, capturas, diseños anteriores, documentos académicos, modelos de Blender y recursos sin uso. Los archivos del frontend incluidos conservan su contenido y rutas relativos del proyecto original.

## Para Kevin

Comenzar por [la guía de integración](docs/INTEGRACION-BACKEND.md) y los dos adaptadores de `dist/modelo/`. El backend se desarrollará en Python; Django continúa como propuesta pendiente de confirmación. La estructura de información y los contratos indicados necesitan acuerdo del equipo antes de integrar servicios reales.

La portada describe las capacidades previstas del proyecto. Esta entrega no implementa base de datos, correos, IA, conexión ESP32 ni control del riego. El Asistente solo presenta el apartado inicial de próxima etapa.

Rafael y Gabriela trabajan en diseño y frontend; Carolina en logo y base de datos; Kevin en backend.

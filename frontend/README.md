# El Chilito · Frontend integrado

Versión de diseño del 26 de octubre de 2026. Esta carpeta reúne la portada, el acceso y los paneles de usuario y administrador actuales. Mantiene Geist, los controles Liquid Glass, las fichas de tres plantas y los menús móviles superiores.

## Abrir el diseño

Desde la raíz del repositorio, ejecutar:

```sh
python3 -m http.server 8770 --bind 127.0.0.1
```

Abrir http://127.0.0.1:8770/frontend/index.html. Este servidor sirve exclusivamente los archivos de diseño de `frontend/`. Para la aplicación Django original de `dist/`, seguir las instrucciones de la raíz; sus servicios y su base de datos no se modificaron.

## Alcance de esta entrega

El frontend no está conectado a PostgreSQL, Django, SMTP, MQTT, sensores, IA ni actuadores. Las lecturas y los paneles administrativos comienzan sin datos inventados. Mantenimiento y solicitudes conservan estado solo en memoria. El soporte no emite tokens sin un proveedor real configurado.

El adaptador `vista-trabajo.js` permite revisar los paneles con `demo@example.com` y `admin@example.com`, ambos con contraseña `ChilitoDemo2026!`. Son accesos de revisión del diseño, no cuentas de servidor, y la sesión se reinicia al recargar. El registro visual usa un código local fijo; no envía correos. La separación visual de roles no es una autorización de servidor.

La política original que se debe conservar al conectar el acceso exige entre 15 y 256 caracteres y está implementada en `../backend/`. El adaptador aislado de diseño aún declara 12 a 128; esta publicación conserva su estado actual y no sustituye la política del servidor.

## Archivos y fotografía

La entrada es `index.html`; los modelos, las vistas y los controladores mantienen su organización MVC. La portada y el acceso usan `vista/img/habanero-fondo.webp`; `vista/img/habanero-fondo-original.png` conserva el original generado. Ambos están incluidos en el repositorio. La referencia, instrucción y procedencia están en `diseno/imagen-habanero/`. Las rutas de la web son relativas a esta carpeta.

## Comprobaciones

```sh
node revision/usuario/comprobar-estado.cjs
node revision/admin/comprobar-estado.cjs
node revision/menu-movil/comprobar-frontend.cjs
```

Los dobles de soporte solo se cargan desde las pruebas, no desde `index.html`. Estas verificaciones comprueban el estado y los contratos del frontend; no prueban una integración con el backend.

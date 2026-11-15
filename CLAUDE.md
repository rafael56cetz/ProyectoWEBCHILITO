# El Chilito · Reglas del proyecto para Claude Code

Lee este archivo completo antes de cualquier cambio. Estas reglas valen en todas las sesiones y fases.

## 1. Qué es el proyecto
- Huerto urbano inteligente de chile habanero. 1 huerto = 1 ESP32 = 3 plantas = 1 depósito de 19 L. Solo Yucatán (`America/Merida`).
- Pila fija: **Python + Django + django-allauth**, **PostgreSQL 17**, frontend en **HTML, CSS y JavaScript sin framework**. Despliegue futuro en Google Cloud. Nunca propongas Node.js, MariaDB, React, TypeScript ni otro framework.
- Proceso: desarrollo de software seguro (SSDLC) con **NIST SSDF 1.1** y requisitos seleccionados de **OWASP ASVS 5.0.0**. Pruebas orientadas por **OWASP WSTG 4.2**.

## 2. Documentos de referencia (en este orden de autoridad)
1. `docs/seguridad/Diseño de seguridad de la aplicación web El Chilito` (Etapa 3): manda en seguridad.
2. `sql/el_chilito_base_v2.sql` y `sql/FUNCIONAMIENTO-BASE-DE-DATOS-v2.md`: la base de datos acordada. **No se cambia el diseño de la base** sin que el responsable lo apruebe.
3. `docs/PLAN-INTERFACES-v2.md`: qué contiene cada pantalla y cómo se ve.
4. `docs/INVENTARIO-INTERFAZ-ACTUAL.md`: dónde está hoy cada cosa en el código.
5. `docs/EJECUCION-v2.md`: las fases. **Trabaja solo en la fase que se te indique.**

Si dos documentos se contradicen, **detente y pregunta**. No elijas tú.

## 3. Estructura que NO se cambia
```
backend/   Django: config/ (ajustes, urls), web/ (API común, respuestas, middleware, sesión),
           cuentas/, huerto/, datos/, privacidad/  → cada app con models.py, api.py, services.py
frontend/  index.html + modelos/ + vistas/ (+ estilos/, fuentes/, imagenes/) + controladores/
sql/       script de instalación, guía y pruebas de la base
docs/      documentación
```
- El frontend es **MVC por dominio**: `modelos/<dominio>.js` (datos y llamadas HTTP), `vistas/<dominio>.js` (HTML), `controladores/<dominio>.js` (eventos). Un dominio nuevo solo si el plan lo nombra.
- El backend expone **API JSON** bajo `/api/…`, con el formato de respuesta y errores que ya existe (`web/respuestas.py`). Las vistas HTTP están en `api.py` y la lógica en `services.py`.
- No conviertas el frontend en plantillas Django. No agregues un empaquetador ni módulos ES.

## 4. Reglas contra el código de más
1. **No crees archivos** que la fase no nombre. Si crees que hace falta uno, pregunta primero y explica por qué.
2. **No agregues dependencias** (pip ni npm) sin aprobación.
3. **Reutiliza** lo que existe: `ChilitoHTTP`, `AppModel`, `AppViews`, componentes `.bento-panel`, `.app-dialog`, `.account-tabs`, calendario `DateFilterViews`, `web/respuestas.py`, cuotas, idempotencia.
4. **Borra lo que reemplazas** en la misma fase. No dejes código comentado, funciones sin uso ni archivos «por si acaso».
5. **Nada de archivos de configuración sueltos** (JSON, YAML, mapas de textos). Las constantes viven en el módulo que las usa; los textos de la interfaz, en su vista.
6. Una función hace una cosa. Si una función pasa de ~40 líneas o un archivo crece sin control, para y revisa.
7. Nombres en **español**, igual que el código actual (`huerto`, `cuidado`, `comando`). Sin abreviaturas raras.
8. Comentarios **solo** cuando explican el porqué de algo no evidente. Nada de comentarios que narren lo obvio, emojis, banners decorativos ni textos de marketing.
9. Escribe como lo haría un desarrollador del equipo: claro, directo, sin capas innecesarias (sin «managers», «factories», «helpers» genéricos ni patrones que el proyecto no usa).
10. Antes de terminar una fase, revisa tu propio diff y elimina lo que sobre.

## 5. Reglas de seguridad (ASVS 5.0 / diseño Etapa 3)
- **Autorización en el servidor, en cada petición** (ASVS V8): sesión, cuenta activa, capacidad y propiedad del recurso. Los identificadores recibidos son referencias a comprobar. Los listados se filtran en el servidor.
- **El actor**: en toda transacción que escribe en nombre de una cuenta, ejecuta `SELECT set_config('chilito.actor_id', <id>, true)` (lo hace el middleware de la fase 1). La base rechaza sin él.
- **Validación** de tipos, longitudes y valores permitidos en el servidor (V2). La del navegador solo ayuda.
- **SQL**: solo el ORM o consultas con parámetros. Las funciones de la base se llaman con parámetros.
- **Salida segura** (V1, V3): datos de usuarios o servicios se insertan como texto (`textContent`), nunca con `innerHTML` sin sanear. Los textos legales se sanean en el servidor con la lista blanca que ya existe.
- **Sesión y CSRF** (V7): no se toca la configuración actual; nunca se desactiva CSRF.
- **Secretos** (V13, V14): fuera del código, en `.env`. Nunca en el frontend, en URL, en registros ni en la auditoría. Códigos y credenciales: solo su HMAC o hash.
- **Errores** (V16): mensajes comprensibles, sin trazas, SQL ni rutas internas. Los errores `23514` de la base se traducen a mensajes claros.
- **Auditoría** (V16): acción, actor, recurso, fecha y resultado; nunca contraseñas, códigos, tokens ni valores personales.
- Identificadores `bigint` hacia el navegador **como texto**.
- La interfaz muestra estados reales: sin datos es «sin datos», nunca cero ni una fecha inventada.

## 6. Estilo visual
- **Se conserva** el aspecto actual: portada y acceso en vidrio oscuro sobre fotos; panel crema con brillo naranja, menú lateral verde flotante y tarjetas de vidrio claro. Tipografía Geist e íconos propios.
- Las correcciones visuales son solo las de `docs/PLAN-INTERFACES-v2.md` sección 1.3 (C1–C9).
- Ningún color, sombra, radio o tamaño nuevo fuera de `frontend/vistas/estilos/tokens.css` (se crea en la fase 2).
- No se agregan imágenes, fuentes ni librerías de íconos.

## 7. Forma de trabajar en cada fase
1. Lee la fase en `docs/EJECUCION-v2.md` y los documentos que cita.
2. **Presenta primero tu plan**: archivos que vas a cambiar, crear o borrar, y por qué. **Espera aprobación.**
3. Implementa. Ejecuta las comprobaciones de la fase.
4. Entrega el **informe de fase** (formato al final de `docs/EJECUCION-v2.md`).
5. No empieces la fase siguiente.

## 8. Lo que nunca debes hacer
- Cambiar la base de datos, sus triggers o sus privilegios para que «funcione» tu código. Si la base rechaza algo, el error está en el código o hay que preguntar.
- Usar `migrate --fake`.
- Desactivar validaciones, CSRF, límites de intentos o comprobaciones de capacidad.
- Crear datos falsos en pantalla para «rellenar».
- Tocar el flujo de acceso (registro, verificación, inicio de sesión, segundo paso, llaves, recuperar contraseña), salvo lo que pida una fase.
- Hacer commits a `main` directamente.

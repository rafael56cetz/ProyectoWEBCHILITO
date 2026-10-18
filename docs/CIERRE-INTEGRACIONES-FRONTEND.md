# Cierre de integraciones del frontend — ETAPA 4

> Organización posterior: esta evidencia se conserva como histórica. La fuente activa ahora es `El-Chilito-Aplicacion-Web`, con una entrada en `dist/index.html`; ya no se usa el segundo servidor o la barra de revisión. Consultar [organización y entrada única](ORGANIZACION-Y-ENTRADA-UNICA.md) para las pruebas vigentes.


> Nota posterior, 17 de octubre de 2026: este cierre conserva los resultados históricos de la etapa 4. Por petición de Rafael se modificó después la navegación de acceso/salida para poder revisar el diseño con cualquier texto o sin completar campos, sin servicios ni autenticación. Las huellas y los 72 resultados de este documento corresponden al código anterior; no se atribuyen automáticamente al ajuste. Consultar el estado vigente en README y la guía central. El backend no se ha implementado.

Fecha: **17 de octubre de 2026**. Se revisaron conjuntamente registro/legales, Privacidad/ARCO y Seguridad/llaves. Esta entrega cierra la revisión de interfaces, con servicios desconectados. No declara la aplicación lista para producción.

## 1. Alcance y estado local comprobado

Trabajo exclusivo en `C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO`. Se leyeron README, plan de etapa 0, entregas 1–3, guía de integración, scripts/resultados anteriores, modelos, controladores, vistas, referencias y configuración Git. No se encontraron instrucciones AGENTS aplicables en los antecesores examinados o dentro de esta copia.

- Rama: `main`. HEAD: `f5605359cdff0fb596a63cfc0c352026fb5060e2`, del 14 de octubre. La referencia **local** `origin/main` coincide; no se realizó una nueva consulta remota en esta etapa.
- El trabajo de las etapas anteriores está modificado o sin seguimiento en esta copia; no está incorporado a ese commit. Esta etapa tampoco crea commit, push o despliegue. No se afirma que los cambios revisados estén en GitHub.
- Huella SHA-256 del árbol completo de `dist/` comprobado: `2fe0d7d4bc0ef0038db26942ffdabb41ca7dc47373f809d6f93024d471bb3b9f`. Se calcula sobre rutas/huellas de archivos, ordenadas, según el script de revisión. Manifiesto detallado y resultados en `revision/resultado-integraciones.json`; referencia inicial en `revision/base-etapa4.json`.
- El árbol de `dist/` no cambió durante la pasada integrada ni por esta entrega documental. Se conservan MVC, HTML/CSS/JavaScript, Geist, Liquid Glass, logo, recursos, portada, dashboard y cuatro entradas de navegación. No se modifica electrónica, IoT, Blender, Notion, `.gitignore` o dependencias.

La [guía central de integración](INTEGRACION-BACKEND.md) reúne acciones, entradas, respuestas, validación frontend/servidor y decisiones pendientes. Las entregas anteriores se conservan como historial, sin duplicar aquí sus contratos.

## 2. Mapa de rutas y disponibilidad

«Demostración» significa datos sintéticos y estados de interfaz. Una pantalla privada abierta no acredita identidad, sesión o autorización. **No hay una cuenta o contraseña real para entrar.** Los valores ficticios que aparecen en los controles solo rellenan formularios.

| Ruta/pantalla | Interfaz normal | Demostración o comprobación disponible | Integración pendiente |
| --- | --- | --- | --- |
| `#inicio`, `#el-proyecto`, `#prototipo`, `#como-funciona` | Portada/anclas existentes | Navegación y recursos conservados | Capacidades reales descritas por el proyecto, fuera del alcance |
| `#acceso`, correo/contraseña | Formulario y recuperación; servicio no disponible | Indisponibilidad en revisión; rechazo/éxito de controlador comprobados con adaptador controlado de prueba, sin cuenta real | Sesión, credenciales, permisos, políticas y transporte |
| `#registro` | Casilla y errores; alta bloqueada por documentos pendientes | Registro/consulta de documentos/verificación sintéticos | Aprobación legal, versiones, alta y correo reales |
| `#verificar` | Código de registro; directo no acredita verificación/sesión | Error, reenvío y resultado con/sin sesión ficticia | Código/desafío, vigencia, uso único y sesión del servidor |
| Oferta posterior a verificación, sin URL propia | Solo podría aparecer tras `verified` y sesión confirmada por servicio | Crear o «Ahora no»; este último continúa al huerto y cancela una creación en curso | Sesión y creación real de llaves |
| `#recuperar` | Formulario; servicio no disponible | Indisponibilidad; confirmación neutral comprobada con adaptador controlado de prueba | Canal de correo y recuperación real |
| `#restablecer?token=…` | Sin token muestra enlace inválido; con token no hay servicio para comprobarlo | Ramas válidas/actualización comprobadas con adaptador controlado de prueba; no hay enlace operativo generado | Inspección, caducidad, consumo y política reales |
| `#cuenta/contrasena` | Único formulario de cambio; servicio no disponible | Error normal y rechazo/éxito comprobados con adaptador controlado de prueba | Sesión, contraseña y autorización |
| `#huerto`, `#avisos`, `#avisos/:id`, `#asistente`, `#cuenta` | Cuatro destinos existentes; huerto espera datos, avisos indican error, asistente informativo, perfil sin datos reales | Navegación entre destinos y subapartados; sin simular métricas IoT | Backend/permisos y, para IoT, documento definitivo de electrónica |
| `#terminos`, `#privacidad` | Páginas públicas con contenido pendiente | Apertura/lectura y regreso al registro; aceptación solo demostrativa | Responsable, contenido aprobado y versiones |
| `#derechos-arco` | Página/formulario públicos; aviso de canal no operativo | Validación, envío/acuse sintético y errores | Procedimiento, responsable y canal real |
| `#cuenta/privacidad` | Acceso al mismo formulario y seguimiento indisponible | Lista, vacío confirmado, sesión vencida, errores y acuse | Identidad y autorización del servidor |
| `#cuenta/privacidad/solicitudes/:id` | Detalle indisponible sin servicio | Historial y respuesta a requerimiento autorizado sintéticos | Pertenencia/representación, requerimientos y conservación |
| `#cuenta/seguridad` | Cambio de contraseña existente y gestión de llaves indisponible | Lista, crear, quitar con confirmación, error/cancelación/reautenticación/recuperación | AuthService real, política y verificador de llaves |
| `#acceso`, alternativa de llave | Botón independiente de correo/contraseña; no disponible | Preparación/espera/comprobación, confirmación ficticia o retorno al correo | WebAuthn y sesión reales, expresamente fuera de esta entrega |
| `#seguridad` público | Destino previo pendiente; hoy termina en portada | Se comprueba que no equivale a Seguridad de Mi cuenta | Decidir destino/contenido público; sin afirmaciones de protección inventadas |
| `#huerto/avisos` | Alias existente a `#avisos` | Conservado | Sin cambio propuesto |
| Rutas inválidas | Desconocidas generales vuelven a portada; ARCO inválido muestra solicitud no disponible; segmento sobrante de Seguridad muestra página no disponible | Entrada directa, Atrás/Adelante y recarga comprobados | No se añade otro sistema de rutas |

## 3. Resultados de esta revisión

Se revisaron los scripts y resultados previos y se ejecutó **una pasada secuencial integrada**, sin cambiar sus expectativas. Se añadieron únicamente seis grupos de cruces que no estaban cubiertos como recorrido conjunto. No fue necesario repetir la batería.

| Batería | Resultado actual | Evidencia local |
| --- | --- | --- |
| Etapa 1 | 19/19 grupos aprobados | `revision/resultado-etapa1.json` |
| Etapa 2 | 20/20 grupos aprobados | `revision/resultado-etapa2.json` |
| Etapa 3 | 27/27 grupos aprobados | `revision/resultado-etapa3.json` |
| Cruces integrados nuevos | 6/6 grupos aprobados | `revision/resultado-recorridos-integrados.json` |
| Total de la pasada | **72/72 grupos, cero fallos** | `revision/resultado-integraciones.json` |

Ejecución: 17-10-2026, de `17:17:55.654Z` a `17:20:56.174Z` (UTC). Entorno: Python 3.13.7, Node v22.20.0, Playwright 1.62.1. Se usaron Chromium, Firefox y WebKit en las baterías que ya los incluían; los seis cruces adicionales usan Chromium. El catálogo de runtimes y las huellas de los scripts están en el resultado agregado. WebKit no equivale a una prueba de Safari en un dispositivo Apple.

Cobertura comprobada:

- Registro/aceptación, documentos en otra pestaña conservando el formulario, código incorrecto, reenvío y verificación. Oferta con/sin sesión confirmada, «Ahora no», creación/cancelación y continuación.
- Acceso clásico y alternativa, recuperación y cambio de contraseña. Las ramas positivas clásicas adicionales se comprobaron con respuestas controladas en el test; **no se incorporó un adaptador de acceso funcional al sitio normal ni a los controles de revisión**.
- Recorrido sin recargar entre cuatro destinos, Privacidad, nuevo acuse/detalle/historial, Seguridad/creación de llave y vuelta al cambio de contraseña/seguimiento. Requerimiento de información confirmado por servicio sintético.
- Lista vacía distinta de error, respuesta incompleta sin éxito, revocación confirmada/rechazada, sesión vencida y regreso al formulario de contraseña. Apertura pública ARCO independiente del estado privado.
- Atrás/Adelante, entrada directa, recarga y rutas inválidas. Salida durante operación ARCO hacia Seguridad y de Seguridad hacia Privacidad, sin aplicar respuestas tardías o mezclar estados.
- Anchos 320, 390, 768, 1024 y 1440 px, cuatro entradas/barra móvil, texto al 200 %, cadenas largas y ausencia de desbordamientos. Teclado/foco, mensajes/errores asociados, botones de 44 px, movimiento reducido, material sólido y colores forzados, según las matrices anteriores.
- Comprobación adicional del foco del encabezado del acuse ARCO y de la confirmación de retirada en 390×600; controles posteriores visibles fuera del encabezado y la barra inferior. Esta ventana es una aproximación de espacio con teclado, no un teléfono físico.
- El sitio normal no carga `revision/` ni interpreta parámetros como modo de demostración. Los adaptadores normales no transportan operaciones. No se observaron llamadas WebAuthn, correos, cuentas, sesiones, expedientes o credenciales reales. Los cambios sintéticos de ARCO y llaves desaparecen al recargar.
- En el contexto aislado de la comprobación adicional: almacenamiento local/de sesión vacío, ninguna base IndexedDB, caché o trabajador de servicio registrado, ninguna cookie de sesión y ninguna llamada de creación/obtención de credenciales. Cero errores JavaScript, recursos HTTP fallidos o tráfico de servicios externos en esa comprobación y las matrices de Chromium. Esto describe el entorno revisado, no certifica un backend inexistente.

No se generaron capturas o imágenes. No se hicieron pruebas manuales con teléfono/teclado virtual reales, lectores de pantalla o autenticadores. La lista manual y el efecto de cada pendiente se mantienen en [D7 de la guía central](INTEGRACION-BACKEND.md#7-pendientes-consolidados-y-efecto-real).

## 4. Correcciones y archivos de esta etapa

**No se reprodujo un defecto funcional que requiriera editar `dist/`.** Las comprobaciones nuevas pasaron sobre el mismo árbol de código que inició la revisión. No se añadieron pantallas, funciones del producto o dependencias.

Se corrigió y consolidó la documentación: el resumen anterior de verificación de la guía describía solo el caso demostrativo sin sesión; ahora distingue las dos respuestas de etapa 3. Se explicitan validaciones/respuestas entendidas frente a propuestas futuras, las entidades conceptuales y el reparto de responsabilidades. Se aclara que clonar Git no entrega ni los cambios locales sin confirmar ni las herramientas ignoradas de revisión.

| Archivo | Trabajo realizado |
| --- | --- |
| `docs/INTEGRACION-BACKEND.md` | Referencia central por operación: pantalla, entrada, respuestas/errores, validación frontend, validación/autorización servidor, acuerdos pendientes; entidades y pendientes clasificados |
| `docs/CIERRE-INTEGRACIONES-FRONTEND.md` | Este cierre, mapa, resultados, límites y reproducción |
| `README.md` | Estado de etapa 4 y enlaces al cierre/guía, conservando entregas anteriores |
| `docs/PLAN-INTEGRACIONES-FRONTEND-ETAPA-0.md` | Solo nota de cierre posterior; inventario histórico conservado |
| `revision/comprobar-recorridos-integrados.cjs` | Seis grupos adicionales de cruces y casos controlados, sin modificar las baterías 1–3 |
| `revision/comprobar-integraciones.cjs` | Ejecución secuencial de las cuatro baterías, comprobación de origen servido, entorno y huellas; conserva resultados individuales |
| `revision/base-etapa4.json`, `revision/resultado-integraciones.json`, `revision/resultado-recorridos-integrados.json` | Referencia y evidencia textual de esta pasada |
| `revision/resultado-etapa1.json`, `revision/resultado-etapa2.json`, `revision/resultado-etapa3.json` | Regenerados por la pasada; scripts existentes intactos |
| `revision/manifest-cierre.json` | Manifiesto de fuentes al cerrar: runtime y herramientas locales para acompañar una futura entrega reproducible |

Los archivos bajo `revision/` siguen siendo locales e ignorados. No se modifica `.gitignore`.

## 5. Ejecución y recorridos para revisar

Desde esta carpeta en PowerShell:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\IOTCHILITO\entregas\ProyectoWEBCHILITO'
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

Abrir [versión normal](http://127.0.0.1:8766/index.html#inicio). Acceso/registro/ARCO/llaves mantienen sus estados desconectados. Para la demostración, en otra terminal desde la misma carpeta:

```powershell
python -m http.server 8767 --bind 127.0.0.1
```

Si estos servidores ya sirven esta copia, usar los enlaces sin iniciar otro proceso en los mismos puertos. El servidor de revisión sirve la raíz local únicamente para revisión; no es la carpeta que se publicaría.

| Recorrido local sin cuenta real | Pasos |
| --- | --- |
| [Registro y legales](http://127.0.0.1:8767/revision/index.html#registro) | «Controles y datos de revisión», «Rellenar datos ficticios», casilla manual, consultar documentos y enviar. Verificar con `246810`; también permite reenvío |
| [Oferta opcional](http://127.0.0.1:8767/revision/index.html#registro) | En controles pulsar «Registro: oferta con sesión ficticia», completar el mismo flujo/código y elegir crear o «Ahora no». Probar «Registro: sin sesión confirmada» para comprobar que no aparece la oferta |
| [Acceso y alternativa](http://127.0.0.1:8767/revision/index.html#acceso) | «Acceder con llave de acceso» sin llenar contraseña; elegir escenario de llaves antes de comenzar. Cancelación/error permite «Usar correo y contraseña». El acceso clásico sigue desconectado |
| [Seguridad](http://127.0.0.1:8767/revision/index.html#cuenta/seguridad) | Lista, crear y quitar con confirmación; selector de llaves para errores, vacío, reautenticación, recuperación o lentitud. Enlace al mismo cambio de contraseña |
| [ARCO público](http://127.0.0.1:8767/revision/index.html#derechos-arco) | Selector de Privacidad y «Rellenar solicitud ficticia»; probar validación, acuse y error sin cuenta/términos |
| [Privacidad de cuenta](http://127.0.0.1:8767/revision/index.html#cuenta/privacidad) | Lista/detalles, formulario compartido y navegación a historial |
| [Requerimiento ficticio](http://127.0.0.1:8767/revision/index.html#cuenta/privacidad/solicitudes/demo-informacion) | Responder solo si el servicio sintético indica permiso; comprobar historial sin cambiar estado libremente |

El código `246810` y los campos de ejemplo son datos de prueba del recorrido, no credenciales reales. La barra identifica la demostración; al recargar se reinicia. Los recorridos clásicos positivos mediante adaptador controlado solo se ejecutan en las comprobaciones, no por introducir esos valores en el acceso normal.

### Repetir las comprobaciones si hay un cambio nuevo que lo justifique

La web estática solo necesita Python. Los scripts de pruebas requieren Node, Playwright 1.62.1 y sus navegadores; no son dependencias del producto. En este equipo se usó el runtime ya instalado:

```powershell
$env:NODE_PATH = 'C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH = 'C:\Users\rafae\AppData\Local\ms-playwright'
node revision/comprobar-integraciones.cjs
```

El script exige que los dos servidores coincidan con esta copia. Ejecuta una vez las etapas 1–3 y los cruces nuevos, registra fechas, entorno/huellas y falla ante un grupo fallido o modificación del runtime durante la pasada. Para una corrección futura, repetir las pruebas afectadas y relacionadas; no repetir toda la batería ya aprobada sin motivo nuevo.

## 6. Compartir después la revisión de forma reproducible

`revision/` está excluida de Git: **quien clone el repositorio no recibirá automáticamente ni la demostración, ni sus adaptadores, ni los scripts/resultados/manifiestos**. Además, las modificaciones actuales del frontend siguen locales y sin commit. Este documento no afirma que el clon de `f560535` contenga las etapas revisadas.

Propuesta para una entrega posterior autorizada, sin ejecutarla aquí:

1. Versionar primero la revisión exacta del frontend acordada por el equipo y asociarla a commit/huella.
2. Entregar las herramientas como un paquete de revisión separado o repositorio de herramientas: entrada de revisión, adaptadores sintéticos, CSS de revisión, las cuatro baterías y el ejecutor agregado. Mantener la distribución del sitio limitada a `dist/`.
3. Acompañar con manifiesto de fuentes, instrucciones de las rutas relativas, versiones de Node/Python/Playwright/navegadores y configuración de dependencias bloqueada del paquete de herramientas. No depender de las rutas privadas del runtime de Codex en otro equipo.
4. El destinatario coloca `revision/` junto al `dist/` correspondiente, verifica la huella, instala el entorno de herramientas acordado y ejecuta los dos servidores y la pasada. Sin secretos ni datos personales.

`revision/manifest-cierre.json` sirve como referencia local para esa entrega futura. En esta etapa no se crea un paquete publicable, no se comparte remotamente, no se añade una configuración de dependencias y no se cambia `.gitignore`.

## 7. Responsables, pendientes y siguiente trabajo

Los pendientes y sus causas/efectos visuales, de integración y publicación están consolidados en la [sección 7 de la guía](INTEGRACION-BACKEND.md#7-pendientes-consolidados-y-efecto-real), D1–D9. Incluyen responsable/contacto, legales, ARCO/acreditación/conservación, backend/sesión/políticas/correos, passkeys, electrónica, revisión manual, `#seguridad` público y distribución de la revisión. No todos impiden continuar diseñando.

Rafael desarrollará el backend; Carolina PostgreSQL; Rafael y Gabriela continúan en frontend y revisión visual. La [sección 6 de la guía](INTEGRACION-BACKEND.md#6-entidades-y-relaciones-conceptuales-para-carolina) reúne entidades/relaciones y datos todavía por definir, sin SQL o tablas creadas.

**Siguiente trabajo concreto:** acordar con Rafael y Carolina el contrato de sesión y acceso por correo/contraseña: `login`, restauración, `profile`, `logout`, permisos, errores y protección de solicitudes. Definir su persistencia conceptual y pruebas de servidor; después autorizar una tarea de implementación del transporte. Mantener registro real bloqueado hasta aprobar documentos/versiones y responsable. ARCO, llaves e IoT esperan sus propios acuerdos.

La etapa 4 termina aquí. No se implementaron backend, PostgreSQL, correos, autenticación real, WebAuthn o servicios externos, ni se publicó el sitio.

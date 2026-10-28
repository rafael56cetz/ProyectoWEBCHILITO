# Cierre de la página — estado de trabajo

27 de octubre de 2026. **Versión actual de trabajo; cierre de diseño y correo pendiente.** El propietario corrigió el destino: la dockerización la preparará un compañero. No se realiza despliegue Ubuntu/VirtualBox ni se declara un entorno Docker de producción operativo.

## Decisiones confirmadas y dependencias

- Conservar la integración, interfaz y flujo; proyectos originales y paquete de datos intactos.
- Registro público: enviar verificación/recuperación a direcciones válidas indicadas por usuarios; controles y cuotas de servidor se conservan. SMTP requiere credenciales externas nuevas, no recuperación automática de secretos antiguos.
- Diseño web v1 es antecedente. El propietario anunció una redacción posterior y pidió esperar antes de los trabajos dependientes de ella. No consta aprobación formal del equipo.
- No se localizaron archivos disponibles con los títulos exactos «Análisis y Requisitos de Seguridad» y «Modelado de Amenazas del sitio web actual». La matriz anterior menciona sus identificadores, pero no reconstruye su contenido ni demuestra recibir correcciones. Se necesitan esos documentos o sus rutas confirmadas.
- No se creará la cuenta ficticia de registro propuesta en navegador, conforme a la respuesta del propietario. La comprobación de registro/correo deberá realizarse con una cuenta real y recepción confirmada.

## Cambios comprobados de correo

La matriz existente permanece en `implementacion-seguridad.md`. Este registro añade solo la decisión confirmada de destinatarios y su implementación, sin inventar códigos REQ/AM pendientes.

| Fuente de decisión | Control | Implementación | Prueba / estado |
|---|---|---|---|
| Propietario: direcciones válidas de registro público | Política explícita `any-valid`, validación de destinatario y TLS; no endpoint libre de envío | `backend/cuentas/email.py`, `backend/config/settings.py` | 5 pruebas nuevas sin red en `tests/test_smtp_config.py`; SMTP real pendiente |
| Credenciales externas protegidas, sin secretos anteriores | Archivo explícito fuera del repo, modo 0600 y propietario; contraseña introducida sin eco ni argumentos | `backend/tools/configurar_correo.py`, `correo_config.py`; carga en `local.py` | Test de permisos, claves y política; configuración real aún no suministrada |
| Conservar comportamientos ya acordados | Reejecutar las regresiones afectadas | `backend/tools/verificar_integracion.py` | 114 pruebas aprobadas: 51 de datos, 25 de cuentas, 29 de API, 5 de SMTP sin red y 4 del arranque local; PostgreSQL 17.11 y prueba HTTP con runtime limitado |
| Reapertura local conservando el entorno | Consultar el puerto actual del contenedor propio, exigir loopback y esperar disponibilidad | `backend/tools/entorno.py`, `local.py`, `operador.py` | Cuatro pruebas sin Docker en `tests/test_local_environment.py`; reapertura real y GET de portada 200 en `evidencias/reinicio-local.json` |

Evidencia vigente del ensayo: `evidencias/validacion-integracion.json` y `evidencias/pruebas-integracion.txt`. Las ejecuciones anteriores de 105 y 110 pruebas son antecedentes. La ejecución vigente de 114 incluye esas regresiones, las cinco pruebas de configuración SMTP sin red y las cuatro de resolución del puerto local. No acredita SMTP real ni recepción en Gmail.

## Navegador durante el cierre

Se usó un servidor efímero separado en el puerto 8781 con cuentas y recurso sintéticos para no tocar la instancia del usuario en el puerto 8780. Se comprobó emitir permiso, conservar caso/permiso al recargar sin recuperar el token, consultar el mismo caso desde el administrador, validar el token exacto, actualizar diagnóstico sin fabricar lecturas y cerrar sesión técnica. Cerrar la sesión de cuenta volvió al acceso. Evidencia `evidencias/navegador-cierre.json`.

No se completó en esta ronda la revocación/caducidad en navegador, ni registro/verificación/recuperación reales. El registro ficticio propuesto no se creó. La prueba efímera se detuvo tras la indicación del propietario. Los tests HTTP/servicios cubren caducidad/revocación, sin convertirlos en evidencia de botones de navegador.

## Hallazgos para el contraste pendiente

Se registran sin aplicar decisiones dependientes del diseño nuevo o de la dockerización:

1. El perfil `deployment` restringe el rol a runtime; el compañero necesitará una ruta administrativa explícita de migración que no sirva la web con propietario.
2. La terminación HTTPS del proxy requiere confianza acotada y encabezados sobrescritos por el proxy, más backend privado. El perfil actual no acredita esa configuración ni ausencia de bucles.
3. En `deployment`, SMTP apagado selecciona el buzón de pruebas. Debe acordarse y comprobarse el fallo cerrado antes de utilizar ese perfil para servicio real; no presentar archivos locales como entrega de correo.
4. El respaldo anterior de la capa de datos no incluye toda la aplicación nueva ni la tabla `web_idempotencia`; el compañero debe respaldar/restaurar el esquema completo y custodiar claves por separado.

Estos puntos no se presentan como controles resueltos ni como despliegue probado. La versión solo podrá cerrarse después del contraste del diseño y de las pruebas reales pendientes.

## Repositorio

Se preparó un checkout independiente de `rafael56cetz/ProyectoWEBCHILITO`, base `main` revisión `1eb74e526f847124889b578eee18a92dac4b9709`, rama local `entrega/integracion-web-etapa4`. La aplicación se incorpora bajo `web-integracion/`, conservando las carpetas anteriores. Tras mostrar contenido y rama, el propietario solicitó subir el código actual. Las evidencias de validación conservan su estado anterior a publicación; el commit y la rama de GitHub identifican la versión compartida.

# Correo real: configuración y comprobación

27 de octubre de 2026. El propietario confirmó envío a direcciones válidas indicadas por usuarios en registro/recuperación. Esa autorización se configura en servidor con `CHILITO_SMTP_RECIPIENT_MODE=any-valid`, no mediante un campo del navegador. El modo anterior `restricted` sigue disponible para pruebas limitadas.

## Archivo externo protegido

Ejecutar desde la raíz de la aplicación, con el Python del entorno de backend:

```sh
python backend/tools/configurar_correo.py \
  --archivo "$HOME/.config/el-chilito/smtp.json" \
  --remitente "CUENTA_REMITENTE" \
  --registro-publico
```

La herramienta requiere terminal interactiva. Solicita la contraseña de aplicación sin mostrarla ni dejarla en los argumentos/historial y guarda JSON con modo 0600 fuera del repositorio. No envía mensajes. No se debe pegar el contenido del archivo en chats, commits ni informes.

Para Gmail, configurar verificación en dos pasos y crear una contraseña de aplicación si la cuenta permite ese mecanismo; no introducir la contraseña principal de Google. Si no está disponible, detener y revisar la política del proveedor, sin debilitar sus protecciones. El servidor documentado es `smtp.gmail.com`, puerto 587 con STARTTLS. En otro proveedor usar `--host` y `--puerto` conforme a su configuración compatible; la aplicación exige TLS y no ofrece una alternativa sin protección.

Fuentes: [Ayuda de Google sobre contraseñas de aplicación](https://support.google.com/accounts/answer/185833?hl=es) y [configuración SMTP de Gmail](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app). Esto no garantiza cuotas comerciales ni recepción; el proveedor puede filtrar/rechazar mensajes.

## Activación explícita local

El archivo no se descubre automáticamente y no se recuperan secretos de proyectos anteriores. Con el servicio detenido, suministrar la ruta al proceso de arranque:

```sh
CHILITO_SMTP_CONFIG="$HOME/.config/el-chilito/smtp.json" python backend/tools/local.py start
```

El cargador solo acepta las claves SMTP previstas, exige propiedad del operador y permisos sin acceso de grupo/otros, y rechaza archivos dentro del repositorio. Se combina únicamente configuración SMTP con el entorno local existente; no cambia datos ni claves de Django/soporte/PostgreSQL. Las variables de conexión equivalentes pueden suministrarse al proceso en un despliegue preparado por el compañero, sin incluirlas en el código.

No habilitar logging SMTP de protocolo, contraseñas, códigos ni enlaces. Una configuración inválida debe detener el arranque o producir error controlado, nunca considerarse correo enviado.

## Protocolo de prueba

Usar un destinatario autorizado por el propietario; para las primeras pruebas se propone el mismo buzón remitente y no personas ajenas. No enviar pruebas a direcciones arbitrarias por el hecho de que el registro público admita direcciones válidas.

1. Registro: validar 15–256, crear cuenta normal sin huerto, observar respuesta y confirmar mensaje en buzón.
2. Verificación: usar código del proceso, comprobar éxito y rechazo de reuso. No copiar código a evidencia.
3. Reenvío: comprobar espera de 60 s, sustitución de código y plazo inicial de 600 s; no eludir cuotas para SMTP real.
4. Recuperación: solicitar enlace, verificar que su origen sea el configurado; comprobar restablecimiento sin inicio automático y rechazo del token anterior tras el cambio. No publicar enlace ni contraseña.
5. Registrar cada evidencia por estado: solicitud aceptada por API, SMTP aceptó el mensaje, recepción confirmada en buzón, operación completada. No convertir aceptación SMTP en recepción.

Hasta que se suministre el archivo y se realicen esas pruebas, **el correo real sigue pendiente**. Los cinco tests nuevos del backend y del cargador son pruebas sin red, no entregas Gmail. Los registros deben contener resultados y códigos fijos, sin destinatarios personales, credenciales, cuerpos o secretos.

# Instalación local del equipo
Fecha: 18 de octubre de 2026. Plataforma de presentación: Windows 10/11, PowerShell, Python 3.13 (incluido lanzador py), Git y Docker Desktop con motor Linux/Compose v2. No se requiere Node para usar la web; solo para sus herramientas de revisión.
Cada integrante usa su propia base y Gmail. No compartir archivos privados ni respaldos de Rafael.

## Primera instalación
Abrir Docker Desktop y esperar a que termine de iniciar. Abrir PowerShell en la carpeta donde se desea descargar el proyecto:
```powershell
git clone https://github.com/rafael56cetz/ProyectoWEBCHILITO.git El-Chilito-Aplicacion-Web
Set-Location .\El-Chilito-Aplicacion-Web
& .\infra\preparar_equipo.ps1
& .\infra\configurar_correo_local.ps1
& .\infra\iniciar_aplicacion.ps1
```
Si se descargó ZIP, extraerlo y abrir PowerShell en la carpeta que contiene compose.yaml; omitir git clone.
El preparador instala las dependencias fijadas, genera secretos propios fuera del repositorio, levanta únicamente PostgreSQL del proyecto, crea los roles limitados, aplica migraciones y prepara un huerto con tres zonas. No crea cuentas, membresías ni lecturas. Puede descargar la imagen PostgreSQL si falta. No borra ni reinicia una base existente. Si encuentra roles sin credenciales privadas correspondientes, se detiene: no restablecer ni borrar volúmenes para forzarlo.
En una instalación existente, hacer respaldo antes de aplicar nuevas migraciones. El arranque habitual no migra ni reinstala.

## Correo real
Cada integrante elige un Gmail que controla. Habilitar verificación en dos pasos y generar una contraseña de aplicación de Google, si la política de su cuenta lo permite. Introducir remitente y contraseña de aplicación solo en el asistente interactivo; nunca en chat, repositorio o argumentos de comandos.
El asistente guarda configuración privada en %LOCALAPPDATA%/ElChilito/secrets y no envía mensajes. No modifica una configuración ya existente. Si esta cuenta no permite contraseñas de aplicación, detener la configuración de correo y consultar al responsable; no usar la contraseña normal ni desactivar TLS.
La web abre sin SMTP, pero registro/verificación y recuperación requieren correo disponible. No hay códigos fijos ni entradas alternativas. Las pruebas automatizadas usan correo en memoria.
Fuente: https://support.google.com/accounts/answer/185833

## Uso diario
Desde la raíz:
```powershell
& .\infra\iniciar_aplicacion.ps1
```
Abrir http://127.0.0.1:8766/index.html. Registrarse con un correo propio y confirmar el código recibido. El acceso posterior usa correo y contraseña (mínimo 15 caracteres). Sin asignación se ve la estructura del huerto, pero no se conceden permisos automáticos.
Comprobar el correo administrativo opcional, que envía al destinatario privado configurado:
```powershell
Push-Location .\backend
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py comprobar_correo_local
Pop-Location
```
No ejecutar este comando durante CI. La recepción depende de Internet, Google y la bandeja de destino.

## Permiso del huerto
Solo un operador autorizado debe asignar una cuenta ya registrada/verificada. Consultar backend/README.md y el identificador mostrado al preparar el huerto. No compartir contraseñas ni asignar permisos por completar el registro. El formulario de vinculación todavía es visual.

## Detener
```powershell
& .\infra\iniciar_aplicacion.ps1 -Detener
docker compose stop db
```
No ejecutar down -v: elimina el volumen de datos. No compartir el puerto de PostgreSQL; ambos servicios permanecen en loopback. 127.0.0.1 de un teléfono no apunta a la computadora.

## Actualizaciones
Guardar el trabajo propio, revisar cambios entrantes y seguir instrucciones de migración antes de actualizar; no usar reset --hard para resolver diferencias. Las claves quedan fuera de Git. Esta es una instalación local, no un despliegue público con HTTPS.

## Si falla
- Docker: abrir Desktop, seleccionar contenedores Linux y esperar a que el motor esté listo.
- Python: verificar py -3.13 --version.
- Puerto 5433/8766 ocupado: identificar el proyecto; no cerrar procesos ajenos.
- PowerShell bloquea un script: inspeccionarlo y solicitar el procedimiento permitido por la política del equipo; no cambiar políticas globales ni ejecutar como administrador por defecto.
- Dependencias: conservar el error y reportarlo; no sustituir versiones silenciosamente.

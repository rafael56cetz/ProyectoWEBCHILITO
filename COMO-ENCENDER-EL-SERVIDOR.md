# Cómo instalar y encender El Chilito en tu equipo

Esta guía es para quien acaba de clonar el repositorio. Al terminar, tendrás la aplicación funcionando en **http://localhost:8780**.

Todos los comandos se ejecutan desde la **carpeta raíz del proyecto** (la que contiene `backend/`, `frontend/` y este archivo).

## 1. Requisitos

| Programa | Versión | Para qué |
|---|---|---|
| Python | 3.12 o más reciente | Servidor (Django) |
| PostgreSQL | 17 | Base de datos. Trae `libpq`, que necesita el conector de Python |
| pgAdmin | 4 | Instalar la base y revisar sus datos |
| Node.js | 18 o más reciente | Solo para las pruebas del frontend |

La base de datos se instala aparte, siguiendo el **[Manual de instalación](MANUAL-DE-INSTALACION)**. Ahí se crean la base y sus tres roles (`chilito_pkg_owner`, `chilito_pkg_runtime` y `chilito_pkg_iot`) con sus contraseñas. Las necesitarás en el paso 3.

## 2. Entorno virtual y dependencias

El proyecto usa un solo entorno virtual: `.venv`, en la carpeta raíz. Git no lo rastrea.

```sh
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements-lock.txt
```

`requirements-lock.txt` fija cada versión con su hash: pip se niega a instalar un paquete que no coincida.

> **Windows:** cambia `.venv/bin/python` por `.venv\Scripts\python` en todos los comandos de esta guía. La carpeta `bin` de PostgreSQL debe estar en el `PATH` para que Python encuentre `libpq`.

## 3. Archivo `.env`

La configuración y los secretos van en un archivo `.env` en la raíz. Es el único archivo de entorno: lo usan el servidor, las pruebas y el simulador. Git no lo rastrea; **nunca lo subas ni lo compartas**.

```sh
cp .env.example .env
```

Abre `.env` y llena cada valor. Cada variable tiene un comentario que dice para qué sirve, si es obligatoria y cómo generarla. Lo mínimo para encender el servidor:

- `CHILITO_DJANGO_KEY`, `CHILITO_IDEMPOTENCIA_SECRETO` y `CHILITO_VINCULACION_SECRETO`: tres claves **distintas**. Genera cada una con:
  ```sh
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- `CHILITO_DB_PASSWORD`: la contraseña del rol `chilito_pkg_runtime`.
- `CHILITO_DB_NAME`: el nombre de la base que creaste.

## 4. Encender

```sh
.venv/bin/python backend/tools/servir_local.py
```

Cuando veas `Abre http://localhost:8780 ... Detén con Ctrl+C.`, abre **http://localhost:8780** en el navegador. Usa `localhost`, no `127.0.0.1`: la aplicación solo acepta ese nombre. Deja la terminal abierta: el servidor funciona mientras esté abierta.

`servir_local.py` carga el `.env` sin mostrar sus valores y solo arranca con `CHILITO_ENV=local`.

Sin SMTP configurado, los correos (códigos de verificación y de acceso) no se envían: quedan como archivos en la carpeta `CHILITO_MAILBOX`. Ábrelos ahí para leer el código.

## 5. Apagar, comprobar y reiniciar

- **Apagar:** pulsa **Ctrl+C** en la terminal del servidor. Si cerraste la terminal sin apagarlo:
  ```sh
  pkill -f servir_local.py
  ```
- **Comprobar si está encendido:**
  ```sh
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8780/
  ```
  `200` significa que está encendido. Si no responde, está apagado.
- **Reiniciar:** el servidor no recarga solo los cambios de Python (`backend/`). Apágalo y vuelve a encenderlo. Los archivos de `frontend/` se leen de nuevo en cada carga; si no ves un cambio, recarga con **Ctrl+Shift+R**.

## 6. Pruebas

Las pruebas del servidor **nunca usan tu base de trabajo**. Crean la base temporal `test_chilito_integracion_sinteticos` y la borran al terminar. Necesitan en el `.env` a `CHILITO_TEST_DB_USER=chilito_pkg_owner` con su contraseña (`CHILITO_TEST_DB_PASSWORD`).

```sh
.venv/bin/python backend/tools/pruebas_local.py suite     # todas las pruebas de Django
.venv/bin/python backend/tools/pruebas_local.py flujos    # registro, segundo factor y privacidad con el rol limitado
node frontend/pruebas/pruebas.cjs                         # frontend; no usa servidor ni base
```

- `flujos` también necesita `CHILITO_PRUEBAS_CLAVE_RUNTIME`.
- La prueba del simulador necesita `CHILITO_PRUEBAS_CLAVE_IOT`. Si falta, se omite y lo indica.
- Cada herramienta de `flujos` comprueba antes de escribir que la base sea la temporal. Si no lo es, se detiene.

## 7. Simulador de equipo

Sirve para probar la interfaz sin un ESP32. Solo corre con `CHILITO_ENV=local` y `CHILITO_DEBUG=1`, y usa sus propias variables `CHILITO_SIM_*` del `.env`.

**Primero, vincula un equipo de prueba.** El equipo debe existir en Administración → «Inventario de equipos». Necesitas su identificador y su credencial, que se muestra una sola vez al registrarlo o al rotarla.

1. Con el servidor encendido, entra como persona usuaria, abre tu huerto y elige «Vincular equipo». Aparece un código `XXXX-XXXX`.
2. En otra terminal:
   ```sh
   .venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 vincular
   ```
   Te pide la credencial del equipo (no se muestra al escribirla) y el código. Responde `Resultado: vinculado`. Si no, indica el motivo: `codigo_invalido`, `codigo_vencido`, `credencial_invalida`, etc.

Por omisión llama a `http://localhost:8780/api/dispositivos/vincular`. Para usar otro servidor, cambia `CHILITO_SIM_URL`: debe ser `https`, salvo hacia `localhost`.

**Después, con el equipo vinculado** (necesitas `CHILITO_SIM_CLAVE_IOT`, la contraseña del rol `chilito_pkg_iot`):

```sh
.venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 conectar
.venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 medir --n 12 --intervalo 300
.venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 atender --falla bomba_2
.venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 correr --cada 10     # Ctrl+C para detener
.venv/bin/python backend/tools/simular_equipo.py CHI-PRUEBA-0001 desconectar
```

Para ver todas las opciones, usa `--help`. Cada ejecución deja en la bitácora del equipo un evento «reinicio» con detalle «simulador». Así lo simulado no se confunde con la operación real.

## 8. Otras herramientas

| Comando | Para qué |
|---|---|
| `.venv/bin/python backend/tools/configurar_correo.py --archivo ../smtp-chilito.json --remitente tu-correo@gmail.com --destinatarios tu-correo@gmail.com` | Guarda la configuración SMTP en un archivo **fuera del proyecto**, con permisos 0600. Pide la contraseña de aplicación sin mostrarla. Después escribe esa ruta en `CHILITO_SMTP_CONFIG`. |
| `.venv/bin/python backend/tools/probar_correo.py destino@correo` | Envía un correo real de prueba con esa configuración. |
| `.venv/bin/python backend/tools/soporte_local.py correo@cuenta --operador correo@soporte` | Retira el segundo factor de una cuenta que perdió todos sus métodos. Queda auditado. |
| `.venv/bin/python backend/tools/armar_entrega.py [destino]` | Prepara una copia limpia para la nube, fuera de esta carpeta, y comprueba que no lleve secretos. |

## 9. Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `No module named 'django'` | Usaste `python3` en vez de `.venv/bin/python`, o no instalaste las dependencias (paso 2). |
| `Falta el archivo .env en la carpeta raíz del proyecto` | No copiaste `.env.example` como `.env`, o no estás en la carpeta raíz. |
| `Suministra CHILITO_DJANGO_KEY…` (o `…IDEMPOTENCIA…` o `…VINCULACION…`) | Falta esa clave en el `.env` o mide menos de 32 caracteres. Genérala como se indica en el paso 3. |
| `Esta herramienta solo sirve con CHILITO_ENV=local` | En el `.env` debe decir `CHILITO_ENV=local`. |
| `no pq wrapper available` o `libpq library not found` | Python no encuentra `libpq`. Instala PostgreSQL 17 (en Linux, también el paquete `libpq5`) y, en Windows, agrega su carpeta `bin` al `PATH`. |
| `password authentication failed` / `connection refused` | PostgreSQL está apagado o la contraseña del `.env` no es la del rol. Revísalo en pgAdmin. |
| `Address already in use` | Ya hay un servidor en el puerto 8780. Apágalo con `pkill -f servir_local.py`. |
| El navegador no conecta o rechaza la sesión | Usa `http://localhost:8780`, no `127.0.0.1`, y comprueba que la terminal del servidor siga abierta. |
| No llega el código de verificación | Sin SMTP, el correo queda como archivo en `CHILITO_MAILBOX`. |
| Las pruebas dicen `CHILITO_TEST_DB_USER del .env debe ser chilito_pkg_owner` | Las pruebas crean y borran bases: necesitan el rol dueño, no el de la aplicación. |
| El simulador responde `El simulador solo corre con…` | Pon `CHILITO_ENV=local` y `CHILITO_DEBUG=1` en el `.env`. |

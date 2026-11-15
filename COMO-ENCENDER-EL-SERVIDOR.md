# Cómo encender el servidor local de El Chilito

Sirve para ver la aplicación en tu navegador en **http://localhost:8780**.
(Usa `localhost`, no `127.0.0.1`: la aplicación está configurada para ese nombre.)

## Encender

Abre una terminal y ejecuta:

```sh
cd "/home/rafael/Documents/Proyecto finalizacion/web-integracion"
~/.local/share/ElChilito/venvs/backend/bin/python backend/tools/servir_local.py
```

Verás `Abre http://localhost:8780 ... Detén con Ctrl+C.` Deja la terminal abierta: mientras esté abierta, el servidor funciona. Luego abre http://localhost:8780 en el navegador.

Qué hace cada parte:
- `cd ...`: entra a la carpeta del proyecto.
- `~/.local/share/ElChilito/venvs/backend/bin/python`: el Python del entorno virtual, que es donde está instalado Django. Si usas `python3` a secas sale `No module named 'django'`.
- `backend/tools/servir_local.py`: carga el `.env` y arranca el servidor en el puerto 8780.

## Apagar

En esa misma terminal, pulsa **Ctrl+C**.

Si lo arrancaste en segundo plano o cerraste la terminal sin apagarlo:

```sh
pkill -f servir_local.py
```

## Comprobar si está encendido

```sh
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8780/
```

Responde `200` si está encendido. Si no responde, está apagado.

## Reiniciar (después de cambiar código Python)

El servidor se lanza con `--noreload`, así que **no recarga solo** los cambios de Python (`backend/`). Apágalo con Ctrl+C y vuelve a encenderlo. Los archivos del `frontend/` sí se leen de nuevo; si no ves el cambio, refresca con **Ctrl+Shift+R**.

## Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `No module named 'django'` | Usaste `python3` en vez del Python del entorno virtual. Usa el comando de arriba. |
| `Address already in use` | Ya hay un servidor en el 8780. Apágalo con `pkill -f servir_local.py` y vuelve a encender. |
| El navegador no conecta | Comprueba que la terminal siga abierta y que uses `http://localhost:8780`. |
| Error de base de datos / contraseña | PostgreSQL debe estar encendido y el `.env` de la carpeta del proyecto debe estar completo. |

## Aviso

Este servidor usa el `.env` del proyecto, es decir, la **base oficial**. Lo que hagas en la aplicación (crear cuentas, guías, etc.) se guarda de verdad. Las pruebas automáticas usan otra base temporal y no pasan por aquí.

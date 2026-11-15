# Herramientas

- `servir_local.py`: arranca la aplicación en http://localhost:8780.
- `comprobar_frontend_local.py`: compara por contenido la raíz, los scripts y los estilos de localhost:8780 con esta carpeta. Solo lectura; no consulta cuentas ni la base. Ejecutarlo en la terminal del equipo donde se abre la aplicación si el entorno del agente no puede acceder a localhost.
- `pruebas_local.py suite|crud|flujos`: pruebas; ver `README.md` de la raíz.
- `entorno_local.py`: carga los `.env` sin mostrar sus valores.
- `destino_temporal.py`: comprueba que los flujos apunten a la base temporal antes de escribir.
- `probar_seguridad.py`, `probar_mfa.py`, `probar_privacidad.py`, `probar_crud_runtime.py`: flujos con el rol limitado.
- `configurar_correo.py`, `correo_config.py`, `probar_correo.py`: configuración y prueba de SMTP.
- `probar_cuota_contacto.py`: comprueba el límite de «Consíguelo» en un entorno de pruebas desplegado.
- `soporte_local.py`: recuperación de acceso sin métodos.
- `generar_sql_instalacion.py`: regenera el instalador.
- `armar_entrega.py`: genera la copia limpia para la nube.

Las herramientas con Docker se guardaron en `../respaldo-docker/`, fuera de este proyecto.

## Comprobar el menú en la aplicación real

Desde la raíz de este proyecto, en la terminal del equipo donde se abre la aplicación:

```sh
python3 backend/tools/comprobar_frontend_local.py
```

`estado: coincide` y `archivos_identicos` igual a `archivos_comprobados` confirman que la raíz y todos los scripts/estilos referenciados responden con los mismos bytes que esta carpeta. La cantidad se calcula desde `frontend/index.html`: cambia cuando se agrupan archivos y no tiene un valor fijo. `revisar` enumera diferencias o errores HTTP. `no_comprobado` significa que no se pudo consultar el servidor; no demuestra que esté detenido. La comparación comprueba lo que el servidor entrega ahora; una pestaña ya abierta puede conservar código anterior. La herramienta no consulta la sesión ni la base, ni acredita el contenido de los documentos legales que se obtiene por la API.

Para comprobar la cuenta que se está usando, abrir [Equipos y ventas](http://localhost:8780/#admin/comercial) en el navegador habitual y completar el acceso allí. En F12 → Consola ejecutar este bloque; compartir únicamente su resultado, sin copiar la respuesta completa de `/api/cuenta` ni cookies:

```js
(async () => {
  if (location.origin !== 'http://localhost:8780') return 'Abre localhost:8780';
  const r = await fetch('/api/cuenta', {
    cache:'no-store', redirect:'error',
    headers:{'X-Chilito-Sondeo':'1'}
  });
  const b = await r.json();
  const s = typeof AuthService === 'undefined' ? null : AuthService.session;
  return JSON.stringify({
    http:r.status,
    permisoServidor:Array.isArray(b.session?.capabilities) ? b.session.capabilities.includes('vincular_huertos') : null,
    permisoEnMemoria:Array.isArray(s?.capabilities) ? s.capabilities.includes('vincular_huertos') : null,
    segundoFactorPendiente:b.mfaRequired === true,
    modeloComercialCargado:typeof AppModel !== 'undefined' && AppModel.adminDestinations.some(x=>x.id==='admin/comercial'),
    controladorComercialCargado:typeof CommerceController !== 'undefined',
    controladorVinculacionCargado:typeof BindingAdminController !== 'undefined',
    enlaceComercial:!!document.querySelector('.private-nav a[href="#admin/comercial"]'),
    enlaceVinculacion:!!document.querySelector('.private-nav a[href="#admin/vinculacion"]')
  }, null, 2);
})()
```

El bloque solo hace GET y devuelve booleanos/estado HTTP. No cambia capacidades ni muestra datos de la cuenta. No hace falta compartir la contraseña. Si hay errores de JavaScript en la consola, comunicar solo tipo, archivo y línea; los contenidos completos pueden contener datos.

| Resultado | Interpretación y siguiente paso |
|---|---|
| HTTP 200, `permisoServidor: false` | La cuenta autenticada no tiene la capacidad efectiva, ni directamente ni por grupo. El backend la consulta en la base en cada restauración; recargar no la concede. |
| HTTP 200, servidor `true`, memoria `false` | La copia de sesión del frontend está desactualizada. Volver a comprobar tras recargar. |
| HTTP 200, servidor/memoria `true`, modelo/controladores cargados, enlaces `false` | El menú no refleja los destinos confirmados. `frontend/controladores/enrutador.js` reconstruye el panel cuando cambian las capacidades. Recargar para cargar los archivos actuales y comprobar de nuevo. |
| Modelo/controladores ausentes o archivos diferentes | Investigar carga de archivos, versión del servidor y errores de JavaScript antes de atribuirlo a permisos. |
| Enlaces `true` pero no se ven | Revisar apertura del menú móvil y desplazamiento del panel hasta el grupo «Gestión». El permiso ya produjo los enlaces. |
| HTTP 401/403/503 | Sesión no confirmada, cuenta sin verificar o servicio no disponible. No clasificar como capacidad ausente. |
| `segundoFactorPendiente: true` | Completar TOTP o una llave de acceso en [Seguridad](http://localhost:8780/#cuenta/seguridad). |

Si se confirma la falta y el propietario decide concederla, el procedimiento es `sql/instalacion/asignar_capacidad.sql` en Query Tool de pgAdmin, con `chilito_pkg_owner`, sobre la base elegida conscientemente por el propietario. Indicar el correo y elegir `vincular_huertos` como única capacidad de esa ejecución. Requiere la estructura del parche 06 y TOTP o WebAuthn activos; no ejecutar instaladores ni parches de nuevo sin comprobar qué falta. `preparar_administrador_principal.sql` no incluye esta capacidad.

Es una concesión operativa: permite consultar huertos entregables e historial de vinculaciones y emitir/revocar códigos reales, con TOTP o WebAuthn usados en los últimos cinco minutos. Al consumirse, un código vincula realmente el huerto a la cuenta destinataria. Emitir otro reemplaza el pendiente; los códigos duran diez minutos y son de un solo uso. La visibilidad provisional de «Equipos y ventas» utiliza la misma capacidad, pero no conecta operaciones comerciales. Después de una concesión decidida y ejecutada por el propietario, recargar el panel para obtener el contrato actualizado; no es necesario alterar `is_staff`/`is_superuser`.

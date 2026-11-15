# Informe de fase 5 · Administración nueva

Rama: `fase-5-admin-nueva` (sobre `fase-4-operacion-usuario`).

## 1. Resumen

Cinco pantallas nuevas de administración, cada una con su capacidad y el segundo factor en cada endpoint: Inventario de equipos, Administradores (super admin), Textos legales, Bitácora de consentimientos y Ventas. El menú pasa a los grupos de 2.2 (Operación, Gestión, Legal, Super admin) con el mapa capacidad→destino completo. Se eliminaron la «Vinculación de huertos» del administrador y la maqueta «Equipos y ventas» (`Commerce*` y `comercial.css`), y la suite `comercial` que fallaba desde la Fase 1 se sustituyó por una de la administración nueva. Frente a la persona usuaria el administrador aparece solo como «Soporte». **No se probó en un navegador.**

## 2. Archivos

Creados (aprobados antes de empezar; siguen el precedente de `datos/guias.py`):
- `backend/datos/equipos.py`, `administradores.py`, `ventas.py`: servicios de inventario, administradores y ventas.
- `backend/privacidad/legales.py`, `consentimientos.py`: textos legales y bitácora de consentimientos.
- `backend/datos/tests/test_admin.py`: 29 pruebas de equipos, administradores y ventas.

Modificados (backend): `datos/api.py` y `privacidad/api.py` (endpoints), `config/urls.py`, `datos/paginacion.py` (paginador para SQL parametrizado), `web/api.py` (una vista de GET puede devolver un archivo), `web/respuestas.py` (`ReglaDeNegocio` y los mensajes de la base de esta fase), `web/services.py` (la credencial nueva no se guarda en el recibo de idempotencia), `datos/services.py` (el alias del administrador ya no se expone), `huerto/tests.py`, `privacidad/tests.py`, `tests/test_web.py`.

Modificados (frontend): `modelos|vistas|controladores/equipos.js` (reescritos: inventario), `modelos|vistas|controladores/administracion.js` (ventas, administradores, legales y consentimientos), `modelos/comun.js` (grupos y destinos), `vistas/comun.js` (menú por grupos y `AdminTableViews`, la pieza común de tabla, paginación, pestañas y diálogo), `controladores/administracion.js` (`AppController`), `controladores/enrutador.js`, `vistas/huerto.js` (componente 3.8 exportado), estilos (`panel.css`, `apariencia.css`), `index.html` (`mvc.7`), `pruebas/pruebas.cjs`.

Eliminados: `CommerceModel/Views/Controller`, `frontend/vistas/estilos/comercial.css` y su `<link>`, `BindingService/Views/AdminController`, las reglas `binding-*` sin uso y la suite `comercial`.

## 3. Líneas

`git diff --shortstat`: 31 archivos modificados, +2617 / −712, más los 6 archivos nuevos del backend.

## 4. Endpoints

Todos bajo `/api/admin/…`, con `@endpoint(cap=…)` (sesión, cuenta verificada, capacidad y segundo factor) y, en POST, cuota e `Idempotency-Key`.

| Capacidad | Rutas |
|---|---|
| `gestionar_dispositivos` | `GET/POST equipos`, `GET equipos/<id>`, `POST equipos/<id>/desvincular|rotar|retirar` |
| `gestionar_administradores` | `GET administradores`, `GET administradores/historial|actividad`, `POST administradores/cuenta` |
| `gestionar_legales` | `GET/POST legales`, `GET legales/<id>`, `POST legales/<id>/editar|eliminar|publicar`, `POST legales/vista-previa` |
| `ver_consentimientos` | `GET consentimientos`, `GET consentimientos/resumen`, `GET consentimientos/exportar` (CSV) |
| `gestionar_ventas` | `GET/POST ventas`, `GET ventas/resumen`, `POST ventas/<id>/pago|entrega|nota|cancelar` |

Eliminados: `api/admin/vinculacion`, `…/emitir` y `…/<id>/revocar` (eran 503). Siguen en 503 los de flota, soporte, sesiones y mantenimientos (fase 6).

## 5. Seguridad

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V8 | Capacidad y segundo factor en cada endpoint (el servicio la vuelve a exigir), nunca solo por el menú | `Capacidades.test_sin_sesion_sin_capacidad_y_sin_factor` (17 rutas: 401, 403 y `mfa-required`), `test_la_capacidad_de_otra_pantalla_no_sirve` |
| V11/V13 | Credencial con `secrets.token_urlsafe(32)`, solo `make_password`, mostrada una vez; `credential` se vacía del recibo de idempotencia | `test_alta_muestra_la_credencial_una_vez…`, `test_rotar_credencial` |
| V1/V3 | El texto legal se sanea en el servidor (vista previa y detalle); el editor escapa el contenido y la vista previa es el HTML del servidor. CSV: toda celda que empiece por `= + - @ tab CR` se vuelve texto | `test_vista_previa_y_detalle…`, `test_exportar_csv_sin_inyeccion…`, `test_celda_neutraliza_cada_caracter_peligroso` |
| V14 | La bitácora muestra la IP recortada; exportar exige `ver_consentimientos` y se audita con el conteo | `test_bitacora_con_filtros…`, `test_exportar_exige_ver_consentimientos` |
| V16 | Auditoría de cada acción (`alta_equipo`, `rotar_credencial`, `retirar_equipo`, `cambiar_capacidades`, `crear/editar/eliminar_borrador_legal`, `publicar_legal`, `exportar_consentimientos`, `registrar_venta`, `registrar_pago`, `entregar_venta`, `editar_nota_venta`, `cancelar_venta`); `desvincular_dispositivo` la escribe la función de la base y no se duplica; sin motivos, notas ni credenciales | pruebas de cada servicio |
| Capacidades | Rechaza `gestionar_administradores` y la propia cuenta **antes** de la base; altas y bajas con un solo motivo en una transacción; una cuenta sin correo verificado no recibe ni una alta | `test_no_deja_dar_gestionar_administradores`, `test_no_deja_cambiar_las_propias_capacidades`, `test_cuenta_sin_correo_verificado…` |

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 285 pruebas, OK (eran 243); después se repitieron `privacidad`, `huerto` y `datos.tests.test_admin`: 138, OK |
| `python3 backend/tools/pruebas_local.py flujos` | 29/29, 45/45 y 56/56 |
| `node frontend/pruebas/pruebas.cjs` | 6 de 6 suites OK (ya no hay una suite que falle) |

Cubren: con y sin capacidad; publicación (versión menor o igual rechazada, borrador obsoleto, aviso a las 2 cuentas de la prueba, la persona debe aceptar la versión nueva); CSV; ciclo completo de una venta; resumen por municipio; los 106 municipios sin repetir.

## 7. Pendientes y dudas

- **No probado en navegador.** El CSS nuevo (editor legal, diálogos, tablas) se escribió sin verlo.
- **Las pruebas de Django corren con el rol propietario**, así que no ejercitan las reglas que la base aplica solo al rol de la aplicación (por ejemplo, que `publicado_por` y `retirado_en` los pone el trigger, o el rechazo de la base a que alguien cambie sus propias capacidades). Lo de Python sí está probado. Hace falta el recorrido manual con el servidor corriendo como `chilito_pkg_runtime`. Para no depender del trigger, Django ya fija `retirado_en` al retirar.
- **Municipios de Yucatán (106):** la constante `MUNICIPIOS_YUCATAN` (`datos/ventas.py`) se contrastó con la lista oficial del Decreto 169/2026 del Congreso de Yucatán y quedó idéntica, en el mismo orden. Diferían tres nombres: Dzan, Tixméhuac y Tixpéual (el decreto los escribe así).
- **Tamaño de los textos legales: 28 000 caracteres.** La petición completa no puede pasar de 32 KB (`DATA_UPLOAD_MAX_MEMORY_SIZE`) y la fase no autoriza tocar esa configuración. La base admite 200 000; subir el tope es una decisión de configuración.
- **Ventas, reglas que la base no cubre:** Django exige que el importe acumulado no baje ni supere el precio y que la entrega caiga entre la venta y hoy. Se permite cancelar una venta ya entregada (la fase no dice lo contrario).
- **Administradores:** un super admin puede quitarle a otro cualquier capacidad que no sea `gestionar_administradores` (la base tampoco lo impide). La confirmación «Darás/Quitarás» conoce las capacidades actuales solo de las cuentas de la página cargada (25).
- **Fechas:** los filtros de página usan el calendario compartido (`DateFilterViews`); los diálogos de venta usan `<input type="date">` porque ese calendario crea un elemento global por montaje.
- **Exportación:** es una descarga por GET con auditoría; si el filtro pasa de 50 000 filas el botón se desactiva y se pide acotar.
- **Consola, flota, mantenimientos, solicitudes y token de soporte del administrador, y el enlace `#admin/consola`:** sin tocar, fase 6. El renombre de `CHILITO_SUPPORT_KEY`, fase 7.
- «Abrir correo de soporte» quedó al final del menú, antes de Mi cuenta, como en la tabla 2.2.

## 8. Cómo probarlo a mano

1. Entra como administrador con todas las capacidades menos la de super admin y revisa el menú por grupos.
2. **Equipos:** «+ Dar de alta equipo» (`ESP32-PRUEBA2`, MAC, firmware); la credencial sale una sola vez con «Copiar»; al cerrarla ya no se puede ver. Prueba búsqueda, filtros, detalle, rotar credencial, desvincular (con un equipo vinculado), retirar.
3. **Administradores** (como super admin): da solo «Ventas» con motivo a una cuenta de prueba, mira el historial; entra como esa cuenta y comprueba que solo ve Ventas. Intenta cambiar tus propias capacidades: no debe dejar.
4. **Textos legales:** crea el borrador de Términos 1.1, mira la vista previa, publícalo; la cuenta de prueba debe verlo en Avisos y aceptarlo al entrar. Intenta publicar una versión menor y editar una publicada.
5. **Bitácora:** busca por correo y versión, abre un registro, exporta el CSV y ábrelo en una hoja de cálculo.
6. **Ventas:** registra una venta con pago parcial, completa el pago, márcala entregada; mira el resumen por municipio; cancela otra venta.

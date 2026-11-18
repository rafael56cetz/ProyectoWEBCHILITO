// Pruebas del frontend (sin navegador, red ni base de datos). Uso, desde la raíz del proyecto:
//   node frontend/pruebas/pruebas.cjs
// Cada bloque «suite» es una de las pruebas anteriores; corren una tras otra y cada una dice PASS si pasa.
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path'), assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');

const FRONT = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(FRONT, name), 'utf8');
// Los archivos agrupados por área separan sus partes con «// ── Nombre ──»: devuelve solo la parte pedida.
function bloque(archivo, nombre) {
  const lineas = read(archivo).split('\n');
  const inicio = lineas.indexOf(`// ── ${nombre} ──`);
  assert.notEqual(inicio, -1, `${archivo} no tiene la parte «${nombre}»`);
  const fin = lineas.findIndex((linea, i) => i > inicio && /^\/\/ ── .* ──$/.test(linea));
  return lineas.slice(inicio, fin === -1 ? undefined : fin).join('\n');
}
// Carga archivos en un contexto, en el orden dado (igual que los <script> de index.html).
const cargar = (contexto, ...archivos) => archivos.forEach(a => vm.runInContext(read(a), contexto, {filename: a}));

const suites = [];
const suite = (titulo, ejecutar) => suites.push([titulo, ejecutar]);

// ── Administración nueva: inventario, ventas, administradores, legales y consentimientos ─────────
suite('administración: inventario, ventas, administradores, legales y consentimientos', async () => {
  const context = vm.createContext({console, crypto:webcrypto, structuredClone, DOMException, AbortController, AbortSignal, Date, Map, Set, Object, Array, JSON, Number, String, RegExp, Error, Intl, encodeURIComponent, decodeURIComponent,
    URLSearchParams, document:{cookie:'csrftoken=test-csrf'}, window:{dispatchEvent() {}}, Event, fetch:async () => { throw new Error('Sin red en esta prueba'); }});
  cargar(context, 'modelos/cuenta.js', 'modelos/comun.js', 'modelos/huerto.js', 'modelos/equipos.js', 'modelos/administracion.js',
    'vistas/comun.js', 'vistas/publico.js', 'vistas/cuenta.js', 'vistas/huerto.js', 'vistas/equipos.js', 'vistas/administracion.js');
  const run = code => vm.runInContext(code, context);
  // Menú: cada destino con su capacidad, agrupado y filtrado; «consola» se redirige.
  const menu = capabilities => { context.session = {capabilities}; return JSON.parse(JSON.stringify(run('AppModel.adminMenu(session)'))).map(group => [group.label, group.items.map(item => item.id)]); };
  assert.deepEqual(menu(['gestionar_ventas', 'ver_flota']), [['Operación', ['admin/flota']], ['Gestión', ['admin/ventas']]]);
  assert.deepEqual(menu(['gestionar_administradores']), [['Super admin', ['admin/administradores']]]);
  assert.deepEqual(menu([]), []);
  assert.equal(run('AppModel.adminDestinations.length'), 10);
  assert.equal(run('new Set(AppModel.adminDestinations.map(item => item.capability)).size'), 10);
  assert.deepEqual({...run("AppModel.adminRedirects")}, {consola:'soporte'});
  assert.deepEqual(Array.from(run("AppModel.allowedAdmin({capabilities:['gestionar_dispositivos','gestionar_legales']}).map(item => item.id)")), ['admin/equipos', 'admin/legales']);
  // Validaciones previas al envío (el servidor y la base vuelven a validar).
  assert.equal(run("EquipmentModel.validate({identifier:'ESP32-A1B2', mac:'AA:BB:CC:DD:EE:FF', firmware:'1.0.0'})"), null);
  for(const bad of [{identifier:'ab'}, {identifier:'con espacio'}, {mac:'nada'}, {mac:'AA:BB:CC:DD:EE'}, {firmware:'con espacio'}]) {
    context.values = {identifier:'ESP32-A1B2', mac:'AA:BB:CC:DD:EE:FF', firmware:'', ...bad};
    assert.ok(run('EquipmentModel.validate(values)'), JSON.stringify(bad));
  }
  for(const [amount, ok] of [['3500', true], ['3500.5', true], ['3500.50', true], ['0.01', true], ['3500.999', false], ['-1', false], ['1e3', false], ['', false], ['mil', false], ['123456789', false]]) assert.equal(run(`SalesModel.amount(${JSON.stringify(amount)})`) !== null, ok, amount);
  assert.deepEqual({...run("SalesModel.period('all')")}, {desde:'', hasta:''});
  assert.match(run("SalesModel.period('month').desde"), /^\d{4}-\d{2}-01$/);
  assert.equal(run("ConsentService.exportUrl({documento:'terminos', cuenta:''})"), '/api/admin/consentimientos/exportar?documento=terminos');
  // Los identificadores entran en la ruta: solo dígitos o UUID; con otra cosa no se hace ninguna llamada.
  for(const call of ["EquipmentService.detail('1/../x', 1)", "EquipmentService.rotate('abc')", "SalesService.cancel('x')", "LegalAdminService.detail('no-es-uuid')"]) assert.deepEqual({...await run(call)}, {status:'error', code:'invalid-input'}, call);
  // Vistas: texto del servidor siempre escapado y paginación visible.
  context.bad = '<img src=x onerror=alert(1)>';
  const equipo = {id:'5', identifier:context.bad, mac:'aa:bb:cc:dd:ee:01', state:'vinculado', connection:'en_linea', lastConnectionAt:null, firmware:null, gardenId:'1', garden:context.bad, owner:'a@b.test', sale:{id:'9', buyer:context.bad}};
  context.equipmentState = {status:'ready', list:{items:[equipo], page:1, total:1, counts:{disponible:0, vinculado:1, retirado:0}}, filters:{busqueda:context.bad}};
  const inventory = run('EquipmentViews.list(equipmentState)');
  assert.ok(!inventory.includes('<img src=x') && inventory.includes('Página 1 de 1') && inventory.includes('+ Dar de alta equipo') && inventory.includes('Inventario de equipos'));
  context.deviceState = {status:'ready', data:{device:{...equipo, registeredAt:'2026-11-08T11:00:00Z', registeredBy:null, retiredAt:null, linkedAt:null, garden:{id:'1', name:context.bad}, sale:null}, events:{items:[{type:'alta', detail:context.bad, actor:null, at:'2026-11-08T11:00:00Z'}], page:1, total:1}, diagnostics:[]}};
  const detail = run('EquipmentViews.detailScreen(deviceState)');
  assert.ok(!detail.includes('<img src=x') && detail.includes('Desvincular') && detail.includes('Rotar credencial') && !detail.includes('Retirar equipo'));
  const credential = run("EquipmentViews.credential('ESP32-1', 'AbC123_secreto-largo-de-prueba-0123456789')");
  assert.ok(credential.includes('Solo se muestra ahora.') && credential.includes('No se volverá a mostrar.') && credential.includes('copy-code') && !credential.includes('Vence en'));
  const sale = {id:'3', device:{id:'5', identifier:'ESP32-1'}, buyer:context.bad, email:'x@y.test', accountLinked:true, municipality:'Mérida', price:'3500.00', received:'1000.00', reference:context.bad, payment:'parcial', delivery:'por_entregar',
    method:'domicilio', plannedDelivery:null, deliveredAt:null, soldAt:'2026-11-08', state:'vigente', cancelledAt:null, note:context.bad};
  context.salesState = {status:'ready', tab:'ventas', list:{items:[sale], page:1, total:1}, catalog:{municipalities:['Mérida', 'Valladolid'], sellable:[{id:'5', identifier:'ESP32-1'}]}, filters:{busqueda:context.bad}, summary:null, preset:'month'};
  // El folio de un caso no se parte y el resto del texto se escapa.
  const folio = run("AppViews.conFolio('Caso CS-F36275A2 <b>x</b>')");
  assert.equal(folio, 'Caso <span class="folio">CS-F36275A2</span> &lt;b&gt;x&lt;/b&gt;');
  const salesScreen = run('SalesViews.screen(salesState)');
  assert.ok(!salesScreen.includes('<img src=x') && salesScreen.includes('Página 1 de 1') && salesScreen.includes('+ Registrar venta') && salesScreen.includes('Parcial'));
  context.sale = sale;
  const saleDetail = run('SalesViews.detail(sale)');
  assert.ok(!saleDetail.includes('<img src=x') && saleDetail.includes('Registrar pago') && saleDetail.includes('Marcar entregada') && saleDetail.includes('Cancelar venta'));
  assert.ok(!run('SalesViews.detail({...sale, state:"cancelada", cancelledAt:"2026-11-09"})').includes('Cancelar venta'), 'una venta cancelada ya no ofrece acciones');
  context.salesSummary = {status:'ready', tab:'resumen', list:{items:[], page:1, total:0}, catalog:{municipalities:[], sellable:[]}, filters:{}, preset:'month',
    summary:{sales:2, sold:'4500.00', collected:'2000.00', pending:'2500.00', byMunicipality:[{municipality:'Mérida', sales:2, sold:'4500.00', collected:'2000.00', pending:'2500.00'}]}};
  const summary = run('SalesViews.screen(salesSummary)');
  assert.ok(summary.includes('Por municipio') && !/ganancia/i.test(summary));
  assert.ok(run('SalesViews.createForm({municipalities:["Mérida"], sellable:[]})').includes('Fecha prevista de entrega'));
  const admins = {items:[{id:'1', email:'otro@b.test', name:context.bad, superAdmin:false, capabilities:['gestionar_ventas'], secondFactor:true, lastAccess:null}, {id:'2', email:'yo@b.test', name:null, superAdmin:true, capabilities:['gestionar_administradores'], secondFactor:true, lastAccess:null}], page:1, total:2, editable:[]};
  context.accessState = {status:'ready', tab:'administradores', admins, history:{items:[], page:1, total:0}, activity:{items:[], page:1, total:0}, filters:{}, ownEmail:'yo@b.test'};
  const accessScreen = run('AdminAccessViews.screen(accessState)');
  assert.ok(!accessScreen.includes('<img src=x') && accessScreen.includes('Tu cuenta') && accessScreen.includes('Página 1 de 1') && accessScreen.includes('+ Dar acceso a una cuenta'));
  // Super administrador: una sola insignia; los demás, hasta 3 y «+N» con la lista completa.
  assert.ok(accessScreen.includes('Super administrador · todas') && !accessScreen.includes('>Ventas</span> <span'));
  const many = {...admins, items:[{...admins.items[0], capabilities:['ver_flota', 'atender_soporte', 'gestionar_mantenimientos', 'gestionar_ventas', 'gestionar_guias']}]};
  context.accessMany = {...context.accessState, admins:many};
  const manyScreen = run('AdminAccessViews.screen(accessMany)');
  assert.ok(manyScreen.includes('>+2</span>') && manyScreen.includes('title="Flota, Soporte, Mantenimientos, Ventas, Guías"') && !manyScreen.includes('>Guías</span>'));
  // Tarjeta de resumen: las cifras llevan is-figure, el texto no,.
  assert.ok(run("AppViews.kpi('Equipos', '1 284')").includes('user-metric is-figure'));
  assert.ok(!run("AppViews.kpi('Cobrado', '$2,000.00')").includes('is-figure') && !run("AppViews.kpi('Estado', 'Sin lectura')").includes('is-figure'));
  const accessForm = run("AdminAccessViews.accessForm({})");
  assert.ok(!accessForm.includes('value="gestionar_administradores"') && accessForm.includes('solo se asigna desde la base de datos') && accessForm.includes('Motivo'));
  assert.equal(run("AdminAccessViews.confirmation(['gestionar_ventas'], ['ver_flota']).texto"), 'Darás: Ventas. Quitarás: Flota. ¿Continuar?');
  const draft = {id:'a', type:'terminos', version:'1.1', title:context.bad, state:'borrador', createdAt:'2026-11-08T11:00:00Z', updatedAt:'2026-11-08T11:00:00Z', publishedAt:null, publishedBy:null, sha256:'a'.repeat(64)};
  context.legalState = {status:'ready', type:'terminos', data:{current:{...draft, id:'b', version:'1.0', state:'publicada', publishedAt:'2026-11-01T11:00:00Z', publishedBy:'a@b.test'}, drafts:[draft], history:[]}};
  const legalList = run('LegalAdminViews.listScreen(legalState)');
  assert.ok(!legalList.includes('<img src=x') && legalList.includes('Versión vigente') && legalList.includes('Publicar') && legalList.includes('+ Nueva versión'));
  context.editorState = {status:'ready', type:'terminos', document:{...draft, content:'<p>' + context.bad + '</p>', html:'<p>servidor</p>'}};
  const editor = run('LegalAdminViews.editorScreen(editorState)');
  assert.ok(editor.includes('&lt;img src=x') && !editor.includes('<img src=x') && editor.includes('<p>servidor</p>'), 'el contenido va escapado en el editor; la vista previa es el HTML del servidor');
  assert.ok(editor.includes('data-admin-action="upload"') && editor.includes('data-legal-file') && editor.includes('accept=".docx') && editor.includes('maxlength="200000"') && editor.includes('data-legal-saved'));
  const toolbar = editor.match(/<div class="legal-toolbar"[^]*?<\/div>/)[0], upload = editor.match(/<div class="legal-upload">[^]*?<\/div>/)[0];
  assert.ok(!toolbar.includes('upload') && upload.includes('data-admin-action="upload"') && upload.includes('btn-liquid-accent') && upload.includes('aria-describedby="lg-upload-help"')
    && upload.includes('Sube tu Word y se conserva el formato') && upload.includes('data-legal-file'), 'el .docx va fuera de la barra, destacado y con su ayuda');
  assert.ok(/data-admin-action="publish-editor" hidden/.test(run("LegalAdminViews.editorScreen({status:'ready', type:'terminos', document:null})")), 'un borrador nuevo se publica cuando ya existe');
  assert.ok(run('LegalAdminViews.confirmations.publish("politica_cookies", "2.0").texto').includes('volver a decidir sobre cookies'));
  assert.ok(!run('LegalAdminViews.editorScreen({...editorState, document:{...editorState.document, state:"publicada", publishedAt:"2026-11-08T11:00:00Z"}})').includes('Guardar borrador'));
  context.consentState = {status:'ready', summary:{terms:{version:'1.1', accepted:3, accounts:5}, privacy:{version:'1.1', accepted:3, accounts:5}, statistics:{browsers:2, accepted:1, percent:50}}, filters:{}, exportUrl:'/api/admin/consentimientos/exportar', exportLimit:50000,
    list:{items:[{id:'7', at:'2026-11-08T11:00:00Z', account:context.bad, scope:'cuenta', what:'Cookies', version:'1.0', decision:'Aceptó', purpose:null, ip:'189.203.45.0', browser:context.bad}], page:1, total:1}};
  const consent = run('ConsentViews.screen(consentState)');
  assert.ok(!consent.includes('<img src=x') && consent.includes('Exportar CSV') && consent.includes('3 de 5 cuentas') && consent.includes('50% (1 de 2)') && consent.includes('Página 1 de 1'));
  assert.ok(run('AdminTableViews.pager({page:2, total:60})').includes('Página 2 de 3'));
  context.bigConsent = {...context.consentState, list:{...context.consentState.list, total:50001}};
  assert.ok(run('ConsentViews.screen(bigConsent)').includes('disabled>Exportar CSV'), 'un filtro demasiado grande no ofrece una descarga que fallaría');
  // Lo viejo ya no existe.
  const sources = ['modelos', 'vistas', 'controladores'].map(dir => ['administracion', 'equipos'].map(name => read(`${dir}/${name}.js`)).join('\n')).join('\n') + read('index.html');
  for(const gone of ['Commerce', 'BindingService', 'BindingViews', 'BindingAdminController', 'comercial.css', 'admin/comercial', 'admin/vinculacion']) assert.ok(!sources.includes(gone), gone);
  assert.ok(!fs.existsSync(path.join(FRONT, 'vistas/estilos/comercial.css')));
  console.log('PASS administración: menú por grupos, validaciones, rutas seguras, texto escapado y paginación visible');
});

// ── Flota, consola remota y mantenimientos ───────────────────────────────────────────────────
suite('flota, consola remota y mantenimientos', async () => {
  const context = vm.createContext({console, crypto:webcrypto, structuredClone, DOMException, AbortController, AbortSignal, Date, Map, Set, Object, Array, JSON, Number, String, RegExp, Error, Intl, encodeURIComponent, decodeURIComponent,
    URLSearchParams, document:{cookie:'csrftoken=test-csrf'}, window:{dispatchEvent() {}}, Event, fetch:async () => { throw new Error('Sin red en esta prueba'); }});
  cargar(context, 'modelos/cuenta.js', 'modelos/comun.js', 'modelos/huerto.js', 'modelos/equipos.js', 'modelos/administracion.js',
    'vistas/comun.js', 'vistas/publico.js', 'vistas/cuenta.js', 'vistas/huerto.js', 'vistas/equipos.js', 'vistas/administracion.js');
  const run = code => vm.runInContext(code, context);
  context.bad = '<img src=x onerror=alert(1)>';
  // Flota: totales reales, sin las métricas que no tienen fuente, y la fila según la capacidad de inventario.
  const item = {id:'5', identifier:context.bad, state:'vinculado', connection:'en_linea', lastConnectionAt:null, lastReadingAt:null, firmware:null, gardenId:'1', garden:context.bad, owner:'a@b.test', lastReviewAt:null};
  context.fleetState = {status:'ready', filters:{busqueda:context.bad}, data:{totals:{linked:3, online:2, offline:1, problems:1}, trends:{moisture:[], temperature:[]},
    problems:[{type:'order', deviceId:'5', identifier:context.bad, at:'2026-11-14T10:00:00Z', detail:'reiniciar'}], items:[item], page:1, total:1}};
  const fleet = run('FleetViews.screen(fleetState, {inventory:true})');
  assert.ok(!fleet.includes('<img src=x') && fleet.includes('Equipos vinculados') && fleet.includes('Problemas (24 h)') && fleet.includes('Página 1 de 1') && fleet.includes('href="#admin/equipos/5"') && fleet.includes('Orden fallida'));
  assert.ok(run('FleetViews.screen(fleetState, {inventory:false})').includes('data-admin-action="peek"'));
  for(const gone of ['Evaporación', 'Mosquitto', 'Correlaciones', 'Vida mediana', 'mini bombas']) assert.ok(!fleet.includes(gone), gone);
  // Con un solo punto la tendencia muestra su valor; sin puntos queda vacía.
  assert.equal((fleet.match(/user-chart is-empty/g) || []).length, 2);
  context.fleetState.data.trends = {moisture:[{at:'2026-11-14T12:00:00Z', value:50.1}], temperature:[]};
  const unPunto = run('FleetViews.screen(fleetState, {inventory:true})');
  assert.equal((unPunto.match(/user-chart is-empty/g) || []).length, 1);
  assert.ok(unPunto.includes('user-chart-dot') && unPunto.includes(run('AppModel.number(50.1)')));
  // Consola: sin token ni pines; cada paso solo aparece para quien corresponde.
  const caso = {id:'11111111-1111-4111-8111-111111111111', folio:'CS-1A2B3C4D', incident:'bomba', state:'abierto', createdAt:'2026-11-14T10:00:00Z', person:context.bad, email:'ana@b.test', garden:context.bad, device:'ESP32-1',
    note:context.bad, authorization:'vigente', authorizedUntil:new Date(Date.now() + 5 * 3600000).toISOString(), revokedAt:null, attendedBy:null, mine:false, result:null, resolutionNote:null, closedAt:null};
  // La bandeja y cada caso son pantallas aparte: la bandeja no muestra detalle y el caso no muestra la bandeja.
  context.inboxState = {status:'ready', tab:'abierto', counts:{abierto:1, en_atencion:1, resuelto:0}, inbox:{items:[caso], page:1, total:1}, detail:null};
  const bandeja = run('ConsoleViews.inboxScreen(inboxState)');
  assert.ok(!bandeja.includes('<img src=x') && bandeja.includes('Nuevos (1)') && bandeja.includes('data-folio="CS-1A2B3C4D"') && bandeja.includes('Página 1 de 1') && !bandeja.includes('data-admin-action="attend"'));
  const consoleState = (over, session = null, orders = []) => { context.consoleState = {status:'ready', detail:{case:{...caso, ...over}, diagnostic:null, session, orders}};
    return run('ConsoleViews.caseScreen(consoleState)'); };
  const nuevo = consoleState({});
  assert.ok(!nuevo.includes('<img src=x') && nuevo.includes('href="#admin/soporte"') && nuevo.includes('Volver a la bandeja') && nuevo.includes('data-admin-action="attend"')
    && !nuevo.includes('data-admin-action="connect"') && !nuevo.includes('console-item') && !nuevo.includes('Nuevos (1)'));
  assert.ok(run("ConsoleViews.caseScreen({status:'not-found'})").includes('Este caso no existe'));
  assert.ok(!/token|GPIO|pin/i.test(nuevo.replace(/spinner|pinned/gi, '')), 'la consola no habla de token ni de pines');
  const ajeno = consoleState({state:'en_atencion', attendedBy:'otra@b.test'});
  assert.ok(ajeno.includes('Lo atiende otra@b.test') && !ajeno.includes('data-admin-action="connect"') && !ajeno.includes('data-admin-form="resolve"'));
  const mio = consoleState({state:'en_atencion', attendedBy:'yo@b.test', mine:true});
  assert.ok(mio.includes('data-admin-action="connect"') && mio.includes('data-admin-form="resolve"') && !mio.includes('data-console-live') && mio.includes('Órdenes del caso'));
  // Sin sesión abierta, las órdenes del caso se siguen viendo con su estado.
  const pendiente = {id:'o1', type:'reiniciar', plant:null, duration:null, state:'pendiente', createdAt:'2026-11-14T10:00:00Z', error:null};
  assert.ok(consoleState({state:'en_atencion', attendedBy:'yo@b.test', mine:true}, null, [pendiente]).includes('Pendiente'));
  assert.ok(consoleState({state:'en_atencion', attendedBy:'yo@b.test', mine:true, authorization:'revocada'}).includes('data-admin-action="connect" disabled'));
  const conectado = consoleState({state:'en_atencion', attendedBy:'yo@b.test', mine:true}, {id:'22222222-2222-4222-8222-222222222222', startedAt:new Date().toISOString()});
  assert.ok(conectado.includes('Cerrar sesión técnica') && conectado.includes('data-type="reiniciar"') && conectado.includes('Probar bomba') && !conectado.includes('data-admin-action="connect"'));
  const huecos = {}; for(const name of ['live', 'orders', 'events']) huecos[`[data-console-${name}]`] = {innerHTML:''};
  // Botones de orden falsos: una orden igual en curso bloquea el suyo y el aviso dice por qué.
  const botones = ['reiniciar', 'lectura_inmediata'].map(type => ({dataset:{type}, disabled:false, textContent:type === 'reiniciar' ? 'Reiniciar equipo' : 'Pedir lectura'}));
  const enviar = {disabled:false}, bomba = {elements:{plant:{value:'2'}}, querySelector:() => enviar};
  huecos['[data-admin-form="pump"]'] = bomba; huecos['[data-console-busy]'] = {hidden:true, textContent:''};
  context.rootFalso = {querySelector: selector => huecos[selector] || null, querySelectorAll: () => botones};
  context.vivo = {session:{state:'open'}, device:{connection:'en_linea', lastConnectionAt:'2026-11-14T10:00:00Z', lastReadingAt:new Date().toISOString(), firmware:'1.0.3'},
    readings:{measuredAt:'2026-11-14T10:00:00Z', temperature:29.5, airHumidity:71, light:null, tankHasWater:true, plants:[{number:1, moisture:41, adc:2710}]},
    events:[{type:'conectado', detail:context.bad, at:'2026-11-14T09:00:00Z'}], orders:[{id:'o', type:'probar_bomba', plant:2, duration:3, state:'enviado', createdAt:'2026-11-14T10:00:00Z', error:null}], diagnostic:null};
  run('ConsoleViews.paintLive(rootFalso, vivo)');
  assert.ok(huecos['[data-console-live]'].innerHTML.includes('Sin lectura') && huecos['[data-console-live]'].innerHTML.includes('ADC 2710') && huecos['[data-console-live]'].innerHTML.includes('Con agua'));
  assert.ok(huecos['[data-console-orders]'].innerHTML.includes('Prueba de bomba · planta 2 · 3 s') && !huecos['[data-console-events]'].innerHTML.includes('<img src=x'));
  assert.deepEqual([botones[0].disabled, botones[1].disabled, enviar.disabled], [false, false, true]);
  assert.ok(!huecos['[data-console-busy]'].hidden && huecos['[data-console-busy]'].textContent.includes('Probar bomba · planta 2') && huecos['[data-console-busy]'].textContent.includes('Espera'));
  bomba.elements.plant.value = '1';
  context.ordenes = [pendiente, {...pendiente, id:'o2', type:'lectura_inmediata', state:'confirmado'}];
  run('ConsoleViews.lockOrders(rootFalso, ordenes)');
  assert.deepEqual([botones[0].disabled, botones[1].disabled, enviar.disabled], [true, false, false]);
  assert.ok(huecos['[data-console-busy]'].textContent.includes('Reiniciar equipo'));
  run('ConsoleViews.lockOrders(rootFalso, [])');
  assert.ok(huecos['[data-console-busy]'].hidden);
  assert.equal(run('ConsoleViews.closingText("revocada")'), 'La persona revocó el acceso. La sesión se cerró.');
  assert.match(run('ConsoleViews.confirmations.reboot.texto'), /unos segundos/);
  assert.match(run('ConsoleViews.confirmations.pump(2, 3).titulo'), /planta 2/);
  assert.match(run('ConsoleViews.confirmations.resolve.texto'), /No se puede deshacer/);
  // Mantenimientos de todos los huertos: paginación visible, estados y confirmación al anular.
  const registro = {id:'33333333-3333-4333-8333-333333333333', type:'cosecha', plant:2, chiles:5, doneAt:'2026-11-14T10:00:00Z', voided:false, corrected:true, reason:'Era cosecha',
    gardenId:'9', garden:context.bad, owner:'dueno@b.test', revision:1, registeredAt:'2026-11-14T10:00:00Z'};
  context.careState = {status:'ready', filters:{busqueda:context.bad}, list:{items:[registro], page:2, total:60}};
  const care = run('MaintenanceViews.screen(careState)');
  assert.ok(!care.includes('<img src=x') && care.includes('Página 2 de 3') && care.includes('Corregido') && care.includes('Correo del dueño o huerto') && care.includes('+ Registrar intervención'));
  context.record = registro; context.revisions = [{number:1, type:'correccion', correctedType:'cosecha', correctedPlant:2, correctedChiles:5, reason:context.bad, editor:'ed@b.test', at:'2026-11-14T11:00:00Z'}];
  const detail = run('MaintenanceViews.detail(record, revisions)');
  assert.ok(!detail.includes('<img src=x') && detail.includes('Anular registro') && detail.includes('Guardar corrección') && detail.includes('Motivo (obligatorio)'));
  assert.ok(!run('MaintenanceViews.detail({...record, voided:true}, revisions)').includes('Anular registro'), 'un registro anulado ya no se cambia');
  assert.ok(run('MaintenanceViews.createForm()').includes('N.º de huerto'));
  assert.equal(run('MaintenanceViews.errorText("stale-record")'), 'Otra persona cambió este registro. Se actualizó la lista.');
  // Confirmaciones nuevas en Solicitudes y Guías.
  assert.equal(run('InquiryViews.confirmations.archive.accion'), 'Archivar');
  assert.equal(run('CareGuideViews.confirmations.publish.accion'), 'Publicar'); assert.equal(run('CareGuideViews.confirmations.withdraw.peligro'), true);
  assert.equal(run('MaintenanceViews.confirmations.void.peligro'), true);
  // Lo viejo ya no existe.
  const sources = ['modelos', 'vistas', 'controladores'].map(dir => ['administracion', 'huerto'].map(name => read(`${dir}/${name}.js`)).join('\n')).join('\n') + read('index.html');
  for(const gone of ['validateToken', 'requestToken', 'admin-gpio', 'admin-logs', 'Evaporación estimada', 'Mosquitto']) assert.ok(!sources.includes(gone), gone);
  for(const gone of ['AdminService', 'AdminViews', 'AdminController']) assert.ok(!new RegExp(`\\b${gone}\\b`).test(sources), gone);
  for(const sheet of fs.readdirSync(path.join(FRONT, 'vistas/estilos')).filter(name => name.endsWith('.css'))) {
    const css = read(`vistas/estilos/${sheet}`);
    for(const gone of ['admin-gpio-grid', 'admin-logs', 'admin-token-form', 'admin-ticket-detail']) assert.ok(!css.includes(gone), `${sheet}: ${gone}`);
  }
  console.log('PASS flota, consola remota (sin token) y mantenimientos de todos los huertos');
});

// ── Fechas civiles y contrato HTTP de los filtros de mantenimientos ───────────────────────────
suite('fechas', async () => {
  const zonaOriginal = process.env.TZ;
  async function checkZone(TZ) {
    process.env.TZ = TZ;
    const calls = [];
    const context = vm.createContext({URLSearchParams, ChilitoHTTP:{
      async request(path) { calls.push(path); return {http:200, body:{status:'ready'}}; }
    }});
    cargar(context, 'modelos/huerto.js', 'modelos/administracion.js');
    const dates = vm.runInContext('MaintenanceDates', context);
    const now = new Date();
    const localToday = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    assert.equal(dates.format(dates.today()), localToday);
    for(const value of ['0001-01-01','0099-12-31','2000-02-29','2011-12-30','2024-02-29','2026-11-07','9999-12-31']) {
      assert.equal(dates.format(dates.parse(value)), value);
    }
    for(const value of ['','2026-02-29','1900-02-29','2026-04-31','2026-13-01','0000-01-01','10000-01-01','2026-1-01','07/11/2026']) {
      assert.equal(dates.parse(value), null, value);
    }
    for(const [value, days, months, expected] of [
      ['2024-02-28',1,0,'2024-02-29'],['2026-01-31',0,1,'2026-02-28'],
      ['2024-02-29',0,12,'2025-02-28'],['2026-12-31',1,0,'2027-01-01'],
      ['2026-03-08',1,0,'2026-03-09'],['2026-10-25',1,0,'2026-10-26'],
      ['2011-12-29',1,0,'2011-12-30'],
      ['0001-01-01',-1,0,'0001-01-01'],['9999-12-31',1,0,'9999-12-31']
    ]) assert.equal(dates.format(dates.shift(dates.parse(value), days, months)), expected);
    const february = dates.weeks(2024, 1).flat().filter(Boolean);
    assert.equal(february.length, 29);
    assert.equal(february.at(-1).value, '2024-02-29');
    const december = dates.weeks(2011, 11).flat().filter(Boolean).map(day => day.value);
    assert.equal(new Set(december).size, 31);
    assert.ok(december.includes('2011-12-30'));
    const service = vm.runInContext('MaintenanceService', context);
    await service.list({since:'2026-11-07', until:'2026-11-09', huerto:'1', estado:'anulado', tipo:'inspeccion', busqueda:'ana@x.test'}, 2);
    assert.equal(calls.at(-1), '/api/admin/mantenimientos?busqueda=ana%40x.test&huerto=1&tipo=inspeccion&estado=anulado&desde=2026-11-07&hasta=2026-11-09&page=2');
    await service.list({since:'', until:''}, 1);
    assert.equal(calls.at(-1), '/api/admin/mantenimientos?page=1');
    // Un día pasado se manda al mediodía de Mérida; hoy o vacío significa «ahora».
    assert.equal(service.moment('2026-11-10', '2026-11-14'), '2026-11-10T12:00:00-06:00');
    assert.equal(service.moment('2026-11-14', '2026-11-14'), null); assert.equal(service.moment('', '2026-11-14'), null);
    console.log(`PASS fechas civiles, límites, bisiestos y filtros ISO: ${TZ}`);
  }
  try {
    for(const zone of ['America/Mexico_City','America/Los_Angeles','Europe/Madrid','Pacific/Kiritimati','Pacific/Apia']) await checkZone(zone);
  } finally {
    if(zonaOriginal === undefined) delete process.env.TZ; else process.env.TZ = zonaOriginal;
  }
});

// ── Contrato de los adaptadores: rechazos del servidor, CSRF, idempotencia, contraseñas ───────
suite('contrato de adaptadores', async () => {
  const context = vm.createContext({console, crypto:webcrypto, structuredClone, DOMException, AbortController, AbortSignal, Date, Map, Set, Object, Array, JSON, Number, String, RegExp, Error, encodeURIComponent, decodeURIComponent,
    URLSearchParams, FormData, Blob, document:{cookie:'csrftoken=test-csrf'}, window:{dispatchEvent() {}}, Event, fetch:null});
  const calls = []; let respond;
  context.fetch = async (path, options) => { calls.push({path, options}); return respond(path, options); };
  cargar(context, 'modelos/cuenta.js', 'modelos/comun.js', 'modelos/huerto.js', 'modelos/administracion.js');
  const evaluate = code => vm.runInContext(code, context);
  const reply = (http, body) => ({status:http, json:async () => body});
  respond = () => reply(403, {code:'forbidden'});
  assert.deepEqual({...await evaluate("GardenService.care('1',{type:'inspeccion'})")}, {status:'error', code:'forbidden'});
  const p = calls.at(-1); assert.equal(p.path, '/api/huertos/1/cuidados'); assert.equal(p.options.method, 'POST'); assert.equal(JSON.parse(p.options.body).type, 'inspeccion'); assert.match(p.options.headers['Idempotency-Key'], /^[0-9a-f-]{36}$/);
  // Tras un fallo de red la clave se conserva: reintentar no duplica el cuidado.
  let n = 0; respond = () => { if(n++ === 0) throw new Error('network'); return reply(200, {status:'accepted'}); };
  await evaluate("GardenService.care('1',{type:'cosecha',plant:1})"); await evaluate("GardenService.care('1',{type:'cosecha',plant:1})");
  assert.equal(calls.at(-2).options.headers['Idempotency-Key'], calls.at(-1).options.headers['Idempotency-Key']);
  // Consola remota: no hay token. Las rutas llevan un UUID (el detalle, el folio) y, con otra cosa, no se hace ninguna llamada.
  const caso = '00000000-0000-4000-8000-000000000001', before = calls.length;
  assert.equal((await evaluate("ConsoleService.connect('no-es-uuid')")).code, 'invalid-input'); assert.equal(calls.length, before);
  assert.equal((await evaluate("ConsoleService.detail('cs-1a2b3c4d')")).code, 'invalid-input'); assert.equal(calls.length, before);
  respond = () => reply(200, {status:'accepted'});
  await evaluate(`ConsoleService.connect('${caso}')`);
  assert.equal(calls.at(-1).path, `/api/admin/soporte/${caso}/conectar`); assert.equal(calls.at(-1).options.method, 'POST');
  await evaluate(`ConsoleService.session('${caso}')`);
  assert.equal(calls.at(-1).path, `/api/admin/sesiones/${caso}`); assert.equal(calls.at(-1).options.headers['X-Chilito-Sondeo'], '1');
  await evaluate(`ConsoleService.order('${caso}', {type:'probar_bomba', plant:1, duration:3})`);
  assert.equal(calls.at(-1).path, `/api/admin/sesiones/${caso}/accion`); assert.deepEqual(JSON.parse(calls.at(-1).options.body), {type:'probar_bomba', plant:1, duration:3});
  await evaluate("ConsoleService.detail('CS-1A2B3C4D')");
  assert.equal(calls.at(-1).path, '/api/admin/soporte/CS-1A2B3C4D');
  await evaluate(`ConsoleService.endSession('${caso}')`);
  assert.equal(calls.at(-1).path, `/api/admin/sesiones/${caso}/cerrar`); assert.equal(calls.at(-1).options.keepalive, undefined);
  assert.equal(evaluate("typeof AdminService"), 'undefined');
  // Textos legales: el .docx y lo pegado viajan como formulario con archivo, sin JSON ni recibo de idempotencia.
  respond = () => reply(200, {status:'ready', html:'<p>x</p>'});
  await evaluate("LegalAdminService.sanitize('<p onclick=x>hola</p>')");
  const pegado = calls.at(-1);
  assert.equal(pegado.path, '/api/admin/legales/sanear'); assert.ok(pegado.options.body instanceof FormData);
  assert.equal(pegado.options.headers['Content-Type'], undefined); assert.equal(pegado.options.headers['Idempotency-Key'], undefined);
  assert.equal(await pegado.options.body.get('html').text(), '<p onclick=x>hola</p>');
  assert.equal(pegado.options.headers['X-CSRFToken'], 'test-csrf');
  assert.equal(evaluate("LegalAdminService.fileProblem({name:'aviso.pdf', size:10})"), 'documento-no-docx');
  assert.equal(evaluate("LegalAdminService.fileProblem({name:'Aviso.DOCX', size:3 * 1024 * 1024})"), 'documento-grande');
  assert.equal(evaluate("LegalAdminService.fileProblem({name:'aviso.docx', size:2 * 1024 * 1024})"), null);
  // Panel por sesión: el rol no abre nada por sí mismo, solo elige el destino que el servidor validará.
  assert.equal(evaluate("AppModel.panelHome({role:'user'})"), '#huerto');
  assert.equal(evaluate("AppModel.panelHome({role:'admin',capabilities:['ver_flota'],profile:{}})"), '#admin/flota');
  assert.equal(evaluate("AppModel.panelHome({role:'admin',capabilities:['ver_flota'],profile:{mfaRequired:true}})"), '#cuenta/seguridad');
  // Saludo: alias o frase neutra, nunca el correo.
  assert.equal(evaluate("AppModel.alias({profile:{profile:{alias:'  ',email:'a@b.test'}}})"), '');
  assert.equal(evaluate("AppModel.gardenGreeting('').title"), 'Te damos la bienvenida a tu huerto');
  assert.equal(evaluate("AppModel.gardenGreeting('').lead"), '');
  assert.equal(evaluate("AppModel.gardenGreeting('Ana').title"), 'Hola, Ana');
  assert.equal(evaluate("AppModel.gardenGreeting('Ana').lead"), 'Te damos la bienvenida a tu huerto.');
  assert.equal(evaluate("AppModel.addressed('Ana','Revisa tu huerto.')"), 'Ana, revisa tu huerto.');
  // Guía de contraseña: solo lo comprobable en el navegador; el rechazo real lo explica el servidor.
  assert.equal(evaluate("AuthModel.passwordProgress('123456789012345','',{password:{minLength:15,maxLength:256}}).numericOnly"), true);
  assert.equal(evaluate("AuthModel.passwordProgress('frase larga de huerto','',{password:{minLength:15,maxLength:256}}).numericOnly"), false);
  // Recomendaciones: orientan sin bloquear; el correo se detecta aunque lleve números o signos.
  assert.equal(evaluate("AuthModel.passwordHints('Maria.Lopez2026!','maria.lopez@ejemplo.test').usesEmail"), true);
  assert.equal(evaluate("AuthModel.passwordHints('frase larga de huerto','maria@ejemplo.test').usesEmail"), false);
  assert.equal(JSON.stringify(evaluate("(({cases,number,symbol})=>[cases,number,symbol])(AuthModel.passwordHints('Huerto#1'))")), '[true,true,true]');
  assert.match(evaluate("AuthModel.passwordRejection('password_too_similar')"), /correo/);
  assert.match(evaluate("AuthModel.passwordRejection('codigo-desconocido')"), /no aceptó/);
  const caps = evaluate("AppModel.allowedAdmin({capabilities:['atender_soporte']}).map(x=>x.id)"); assert.deepEqual(Array.from(caps), ['admin/soporte']);
  const unicodePassword = '🌶'.repeat(256); context.unicodePassword = unicodePassword; context.passwordConfig = {password:{minLength:15, maxLength:256}, code:{}};
  assert.equal(evaluate('AuthModel.passwordLength(unicodePassword)'), 256); assert.equal(evaluate("AuthModel.validate('restablecer',{password:unicodePassword,confirmation:unicodePassword},passwordConfig).password"), undefined);
  assert.ok(evaluate("AuthModel.validate('restablecer',{password:unicodePassword+'🌶',confirmation:unicodePassword+'🌶'},passwordConfig).password"));
  assert.equal(evaluate("AuthModel.passwordLength(' '+unicodePassword+' ')"), 258);
  for(const parameter of ['key', 'token']) {
    let replacement; context.linkLocation = {hash:'#restablecer?' + parameter + '=protected-reset-secret', pathname:'/index.html', search:''}; context.linkHistory = {replaceState(_a, _b, url) { replacement = url; }};
    assert.equal(evaluate('AuthModel.consumeResetLink(linkLocation,linkHistory)'), 'protected-reset-secret'); assert.equal(replacement, '/index.html#restablecer');
  }
  respond = (path, options) => { assert.equal(path, '/_allauth/browser/v1/auth/password/reset'); assert.equal(options.headers['X-Password-Reset-Key'], 'protected-reset-secret'); return reply(400, {status:400}); };
  await evaluate("AuthService.request('inspect-reset',{token:'protected-reset-secret'})"); assert.ok(!calls.at(-1).path.includes('protected-reset-secret'));
  respond = () => reply(401, {status:401, meta:{is_authenticated:false}, data:{flows:[{id:'login'}]}});
  assert.equal((await evaluate("AuthService.request('reset',{token:'reset-only-in-body',password:'Una clave extensa y válida 2048'})")).status, 'reset-complete');
  respond = () => reply(401, {status:401, meta:{is_authenticated:false}, errors:[{code:'rejected'}]});
  assert.notEqual((await evaluate("AuthService.request('reset',{token:'invalid-reset',password:'Una clave extensa y válida 2048'})")).status, 'reset-complete');
  respond = () => reply(400, {status:400, errors:[{param:'key', code:'invalid'}]});
  assert.equal((await evaluate("AuthService.request('reset',{token:'expired-reset',password:'Una clave extensa y válida 2048'})")).status, 'invalid-link');
  // Avisos: el servidor manda; el navegador valida la forma y no acepta enlaces fuera del patrón.
  const raw = {id:'7', origin:'dispositivo', severity:'critico', title:'Sin agua', text:'<img src=x onerror=alert(1)>', garden:'Patio', link:'#huerto', createdAt:'2026-11-08T11:58:00+00:00', read:false, resolvedAt:null, resolvable:true};
  context.rawNotice = raw;
  assert.equal(evaluate('AppModel.notice(rawNotice).text'), raw.text, 'el texto es dato, no HTML');
  for(const bad of [{id:'0'}, {id:'7x'}, {origin:'otro'}, {severity:'alta'}, {link:'javascript:alert(1)'}, {link:'#a b'}, {createdAt:'ayer'}, {read:'no'}, {title:' '}, {resolvedAt:'x'}]) {
    context.badNotice = {...raw, ...bad};
    assert.equal(evaluate('AppModel.notice(badNotice)'), null, JSON.stringify(bad));
  }
  context.noticePage = {status:'ready', items:[raw, {...raw, id:'8'}], page:1, total:2};
  assert.equal(evaluate('AppModel.notices(noticePage).status'), 'ready');
  context.noticePage = {status:'ready', items:[raw, raw], page:1, total:2}; assert.equal(evaluate('AppModel.notices(noticePage).status'), 'error');
  assert.equal(evaluate("AppModel.notices({status:'ready', items:[]}).status"), 'empty');
  // Servicio de avisos: ruta, método, filtro de lista blanca, id solo con dígitos y contador como sondeo.
  respond = () => reply(200, {status:'accepted', notice:{...raw, read:true}});
  assert.equal((await evaluate("AppService.request('mark-read',{id:'7'})")).status, 'accepted');
  assert.equal(calls.at(-1).path, '/api/avisos/7/leido'); assert.equal(calls.at(-1).options.method, 'POST');
  const sent = calls.length;
  assert.equal((await evaluate("AppService.request('mark-read',{id:'7/../x'})")).status, 'not-found'); assert.equal(calls.length, sent);
  respond = () => reply(200, {status:'ready', items:[], page:1, total:0});
  await evaluate("AppService.request('notices',{filter:'<script>',page:1})"); assert.equal(calls.at(-1).path, '/api/avisos?filtro=todos');
  await evaluate("AppService.request('notices',{filter:'no_leidos',page:3})"); assert.equal(calls.at(-1).path, '/api/avisos?filtro=no_leidos&page=3');
  respond = () => reply(200, {status:'ready', unread:4});
  assert.deepEqual({...await evaluate("AppService.request('counter')")}, {status:'ready', unread:4});
  assert.equal(calls.at(-1).options.headers['X-Chilito-Sondeo'], '1');
  respond = () => reply(200, {status:'ready', unread:-1}); assert.equal((await evaluate("AppService.request('counter')")).status, 'error');
  cargar(context, 'vistas/comun.js', 'vistas/publico.js', 'vistas/cuenta.js', 'vistas/huerto.js', 'vistas/administracion.js');
  context.bad = '<img src=x onerror=alert(1)>';
  const list = evaluate("AppViews.notices({status:'ready', items:[Object.assign({}, rawNotice, {title:bad, garden:bad})], page:1, total:1}, 'todos', null, '')");
  assert.ok(!list.includes('<img src=x') && list.includes('data-notice-open="7"') && list.includes('Marcar todo como leído'));
  const detailMarkup = evaluate("AppViews.notices({status:'ready', item:Object.assign({}, rawNotice, {title:bad})}, 'todos', '7', '')");
  assert.ok(!detailMarkup.includes('<img src=x') && detailMarkup.includes('Marcar como resuelto'));
  console.log('PASS frontend adapters: server refusal, CSRF, uncertain-write idempotency, notices, capabilities, Unicode password bounds and secret-free reset URLs.');
});

// ── Tarjeta del huerto (diagnóstico) y retirada de despliegues ───────────────────────────────
suite('Mi huerto y retirada de despliegues', async () => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const context = vm.createContext({AppModel:{date:value => `fecha:${value}`, number:value => String(value), gardenGreeting:() => ({phrase:'Frase.'})}});
  vm.runInContext(bloque('modelos/huerto.js', 'Huerto'), context);
  const M = vm.runInContext('GardenModel', context), S = vm.runInContext('GardenService', context);
  const NOW = Date.parse('2026-11-08T12:00:00Z');
  // Línea de estado 3.2: sale de la conexión del equipo y de su última lectura.
  const device = c => ({connection:'en_linea', lastReadingAt:'2026-11-08T11:58:00Z', lastConnectionAt:'2026-11-08T11:58:00Z', firmware:'1.0.3', ...c});
  assert.equal(M.connection(null, NOW), null);
  assert.deepEqual({...M.connection(device({connection:'nunca', lastReadingAt:null}), NOW)}, {tone:'gris', text:'Equipo vinculado · Esperando su primera conexión'});
  assert.equal(M.connection(device({connection:'desconectado'}), NOW).tone, 'rojo');
  const online = M.connection(device(), NOW);
  assert.equal(online.tone, 'verde'); assert.match(online.text, /hace 2 min.*Firmware 1\.0\.3/);
  assert.equal(M.connection(device({lastReadingAt:'2026-11-08T11:30:00Z'}), NOW).tone, 'ambar');
  assert.equal(M.connection(device({lastReadingAt:null}), NOW).tone, 'ambar');
  // Sin lectura no hay número: ni cero ni promedio inventado.
  assert.equal(M.averageMoisture([]), null);
  assert.equal(M.averageMoisture([{moisture:null}, {moisture:null}]), null);
  assert.equal(M.averageMoisture([{moisture:40}, {moisture:null}, {moisture:60}]), 50);
  M.reset();
  const gardens = [{id:'1'}, {id:'2'}];
  assert.equal(M.pick(gardens, '2').id, '2'); assert.equal(M.pick(gardens, 'x').id, '1'); assert.equal(M.pick([], null), null);
  M.remember('2'); assert.equal(M.pick(gardens, null).id, '2'); M.reset();
  assert.equal(M.groupCode('ABCD1234'), 'ABCD-1234');
  assert.equal(M.clock(125), '2:05');
  // El identificador entra en la ruta: solo dígitos; nada llega a la red con otra cosa.
  assert.deepEqual({...await S.detail('1/../../admin')}, {status:'error', code:'invalid-input'});
  assert.deepEqual({...await S.plant('abc', 1)}, {status:'error', code:'invalid-input'});
  assert.deepEqual({...await S.orderState('../x')}, {status:'error', code:'invalid-input'});
  // Vistas: tres versiones, selector solo con 2 o más huertos, y texto del servidor siempre escapado.
  const views = vm.createContext({escaparHTML:escape, icon:() => '', plantDrawing:() => '', GardenModel:M, MaintenanceDates:{format:() => '2026-11-08', today:() => 0},
    AppModel:{gardenGreeting:() => ({phrase:'Frase.'}), number:value => String(value)},
    AppViews:{date:value => `fecha:${value}`, heading:title => `<h1>${escape(title)}</h1>`, accountTabs:() => '', state:title => title}});
  vm.runInContext('const GardenModelAlias = GardenModel;', views);
  vm.runInContext(bloque('vistas/huerto.js', 'Huerto'), views);
  const V = vm.runInContext('GardenViews', views);
  const plants = [1, 2, 3].map(number => ({number, name:`Planta ${number}`, stage:'sin_sembrar', stageSince:null, sowingDate:null, daysSown:null, moisture:null, measuredAt:null}));
  const detail = (gardenDevice, extra = {}) => ({garden:{id:'1', name:'Mi huerto', device:gardenDevice}, plants, metrics:null, lamp:null, summary:null, ...extra});
  const A = V.summary({status:'ready', gardens:[], detail:null}, 'Ana');
  assert.ok(A.includes('Aún no tienes un huerto') && A.includes('Crear mi huerto') && !A.includes('disabled') && !A.includes('fieldset'));
  const B = V.summary({status:'ready', gardens:[detail(null).garden], detail:detail(null)}, 'Ana');
  assert.ok(B.includes('Conecta tu equipo') && B.includes('Vincular equipo') && B.includes('Ver planta') && !B.includes('Depósito de agua'));
  const equipo = {id:'9', identifier:'CHI-1', connection:'en_linea', lastConnectionAt:null, linkedAt:null, firmware:null, lastReadingAt:null};
  const C = V.summary({status:'ready', gardens:[detail(equipo).garden], detail:detail(equipo)}, 'Ana');
  assert.ok(C.includes('Depósito de agua') && C.includes('Esperando la primera lectura de tu equipo') && C.includes('Revisar mi equipo') && C.includes('Generado con IA') === false);
  assert.ok((C.match(/Sin lectura/g) || []).length >= 6, 'sin lectura se dice «Sin lectura»');
  assert.ok(!/(?<![\d.])0\s*(%|°C)/.test(C), 'ningún cero inventado');
  assert.ok(!C.includes('garden-selector'));
  const one = detail(equipo).garden, two = {...one, id: '2', device: equipo};
  assert.ok(V.summary({status:'ready', gardens:[one, two], detail:detail(equipo)}, '').includes('garden-selector'));
  assert.ok(V.summary({status:'ready', gardens:[one, two, {...one, id:'3'}], detail:detail(equipo)}, '').includes('Máximo 3 huertos'));
  assert.ok(V.summary({status:'ready', gardens:[one, {...two, device:null}], detail:detail(equipo)}, '').includes('Primero vincula tu huerto sin equipo'));
  const hostile = V.summary({status:'ready', gardens:[], detail:detail(equipo, {garden:{id:'1', name:'<img src=x onerror=alert(1)>', device:equipo}})}, '<b>x</b>');
  assert.ok(!hostile.includes('<img src=x') && !hostile.includes('<b>x</b>'));
  // Asistente de vinculación, ficha de planta, Mis huertos y alta: todos pintan sin romperse y escapan lo que viene del servidor.
  const garden = detail(null).garden;
  const wizard = o => V.linkWizard({garden, step:1, code:null, seconds:0, expired:false, device:null, ...o});
  assert.ok(wizard({}).includes('Generar código'));
  const waiting = wizard({step:2, code:'ABCD1234', seconds:540});
  assert.ok(waiting.includes('ABCD-1234') && waiting.includes('9:00') && waiting.includes('192.168.4.1') && waiting.includes('Solo se muestra ahora'));
  assert.ok(wizard({step:2, code:null, expired:true}).includes('El código venció. Genera otro.'));
  assert.ok(wizard({step:3, device:{identifier:'<b>CHI</b>'}}).includes('¡Tu equipo quedó vinculado!') && !wizard({step:3, device:{identifier:'<b>CHI</b>'}}).includes('<b>CHI</b>'));
  const page = V.plantPage({garden, plant:{...plants[0], name:'<i>x</i>'}, stages:[{stage:'germinacion', since:'2026-11-01'}], series:[], range:'24h', care:[], lastWatering:null, hasDevice:true});
  assert.ok(page.includes('Regar esta planta') && page.includes('Línea de vida') && !page.includes('<i>x</i>'));
  assert.ok(V.plantPage({garden, plant:plants[0], stages:[], series:[], range:'24h', care:[], lastWatering:null, hasDevice:true}).includes('<h1>Planta 1</h1>'), 'el nombre de fábrica no se repite en el título');
  assert.ok(page.includes('<h1>Planta 1 · «&lt;i&gt;x&lt;/i&gt;»</h1>'), 'un nombre propio sí se muestra, escapado');
  const hostil = V.plantPage({garden, plant:{...plants[0], stage:'<u>etapa</u>'}, stages:[], series:[], range:'24h', care:[], lastWatering:{origin:'<u>origen</u>', duration:3, at:'2026-11-14T10:00:00Z'}, hasDevice:true});
  assert.ok(!hostil.includes('<u>') && hostil.includes('&lt;u&gt;etapa'), 'etapa y origen del riego se escapan');
  assert.ok(V.plantDialogs(plants[0], true).water.includes('Si el depósito no tiene agua, tu equipo no regará.'));
  assert.ok(V.myGardens({status:'ready', gardens:[detail(equipo).garden]}).includes('Desvincular equipo'));
  assert.ok(V.myGardens({status:'ready', gardens:[detail(null).garden]}).includes('Archivar huerto'));
  assert.ok(V.newGarden().includes('Nombre del huerto (opcional)'));
  assert.ok(V.confirmations.desvincular('CHI-1').peligro && V.confirmations.archivar('Patio').accion === 'Archivar huerto');
  // Cálculos puros: cuándo se hizo un cuidado, problemas de una revisión y tiempo de una autorización.
  const full = vm.createContext({AppModel:{date:value => String(value)}, ChilitoHTTP:{request:async () => ({http:200, body:{}})}});
  vm.runInContext(read('modelos/huerto.js'), full);
  const model = code => vm.runInContext(code, full);
  const day = ago => model(`MaintenanceDates.format(MaintenanceDates.shift(MaintenanceDates.today(), ${ago}))`);
  assert.deepEqual({...model("GardenModel.careMoment('')")}, {valid:true, at:null});
  assert.deepEqual({...model(`GardenModel.careMoment('${day(0)}')`)}, {valid:true, at:null});
  const past = model(`GardenModel.careMoment('${day(-3)}')`); assert.equal(past.valid, true); assert.match(past.at, /^\d{4}-\d{2}-\d{2}T/);
  for(const bad of [day(-8), day(1), 'ayer', '2026-02-30']) assert.equal(model(`GardenModel.careMoment('${bad}')`).valid, false, bad);
  assert.equal(model("GardenModel.problems([{result:'falla'}, {result:'correcto'}, {result:'sin_respuesta'}, {result:'no_instalado'}])"), 2);
  assert.equal(model("GardenModel.lapse('2026-11-09T06:42:00Z', Date.parse('2026-11-08T12:00:00Z'))"), '18 h 42 min');
  assert.equal(model("GardenModel.lapse('2026-11-08T11:00:00Z', Date.parse('2026-11-08T12:00:00Z'))"), '0 h 0 min');
  {
  // Pantallas: Panel técnico, Mantenimiento y Soporte.
  Object.assign(views, {});
  vm.runInContext("var CareGuideService = {SUBSTRATE_KEY:'sustrato-perlita'}, CareGuideViews = {slot:() => '<section data-care-guides></section>'};", views);
  vm.runInContext(bloque('vistas/huerto.js', 'Operacion'), views);
  const T = vm.runInContext('TechnicalViews', views), Care = vm.runInContext('CareViews', views), Sp = vm.runInContext('SupportViews', views);
  const dirty = '<img src=x onerror=alert(1)>';
  const point = (at, value, min = null, max = null) => ({at, value, min, max});
  const series = {plants:[1, 2, 3].map(number => ({number, points:[point('2026-11-08T10:00:00Z', 40 + number), point('2026-11-08T11:00:00Z', 42 + number)]})),
    temperature:[point('2026-11-08T10:00:00Z', 25), point('2026-11-08T11:00:00Z', 27)], humidity:[], light:[]};
  const online = {id:'9', identifier:'CHI-1', connection:'en_linea', lastConnectionAt:'2026-11-08T11:58:00Z', linkedAt:null, firmware:'1.0.3', lastReadingAt:'2026-11-08T11:58:00Z'};
  const garden = {id:'1', name:dirty, device:online};
  const data = {range:'24h', garden, hasLight:false, latest:{temperature:26, airHumidity:60, light:null, tankHasWater:true}, series,
    plants:[{number:1, name:dirty, moisture:41, adc:2001, measuredAt:'2026-11-08T11:00:00Z'}, {number:2, name:'Dos', moisture:null, adc:null, measuredAt:null}, {number:3, name:'Tres', moisture:43, adc:2003, measuredAt:'2026-11-08T11:00:00Z'}]};
  const log = {type:'eventos', status:'ready', page:1, total:60, items:[{type:'reinicio', detail:'simulador', at:'2026-11-08T11:00:00Z'}]};
  const technical = T.screen({status:'ready', gardens:[garden], garden, data, range:'24h', log});
  assert.ok(technical.includes('ADC (0–4095)') && technical.includes('Regar una planta') && technical.includes('Página 1 de 3') && technical.includes('simulador'));
  // Rango de 24 h: miles de lecturas crudas se agrupan en un punto cada 10 min (máximo 144 por línea).
  const raw = Array.from({length:5000}, (_, i) => point(new Date(Date.parse('2026-11-08T00:00:00Z') + i * 17000).toISOString(), 30 + (i % 7)));
  const dense = T.screen({status:'ready', gardens:[garden], garden, data:{...data, series:{...series, temperature:raw}}, range:'24h', log});
  const drawn = (dense.match(/<polyline class="user-chart-line is-0" points="([^"]+)"/g) || []).map(line => line.split(' ').length - 3);
  assert.ok(drawn.length && drawn.every(count => count > 1 && count <= 145), 'la gráfica de 24 h agrupa las lecturas');
  assert.ok(!technical.includes('Luz · BH1750'), 'sin lecturas de luz no se muestra la tarjeta');
  assert.ok(technical.includes('Sin lectura') && !technical.includes('<img src=x'), 'sin lectura es «Sin lectura» y el texto del servidor va escapado');
  assert.ok(T.screen({status:'ready', gardens:[garden], garden, data:{...data, hasLight:true, latest:{...data.latest, light:1200}}, range:'24h', log}).includes('Luz · BH1750'));
  assert.ok(T.screen({status:'ready', gardens:[{...garden, device:null}], garden:{...garden, device:null}, data:null, range:'24h', log}).includes('Vincular equipo'));
  assert.ok(T.screen({status:'ready', gardens:[], garden:null}).includes('Crear mi huerto'));
  const careList = Care.list({status:'ready', page:1, total:2, items:[
    {id:'a', type:'sustrato', plant:3, chiles:null, doneAt:'2026-11-08T11:00:00Z', voided:true, corrected:false, reason:dirty},
    {id:'b', type:'cosecha', plant:null, chiles:7, doneAt:'2026-11-08T10:00:00Z', voided:false, corrected:true, reason:'Se anotó mal'}]});
  assert.ok(careList.includes('<s>') && careList.includes('Anulado') && careList.includes('Corregido por soporte') && careList.includes('7 chiles') && !careList.includes('<img src=x'));
  assert.ok(Care.screen({status:'ready', gardens:[garden], garden, plants:data.plants}).includes('¿Qué hiciste?'));
  // Rediseño: los chips muestran el tipo, pero el <select id="care-type" name="type"> y los atajos siguen en el formulario.
  const careScreen = Care.screen({status:'ready', gardens:[garden], garden, plants:data.plants});
  assert.equal((careScreen.match(/data-garden-action="care-type"/g) || []).length, 5, 'un chip por tipo de cuidado');
  assert.equal((careScreen.match(/aria-pressed="true"/g) || []).length, 1, 'un solo chip elegido al abrir');
  assert.ok(careScreen.includes('data-type="rellenar_deposito" aria-pressed="true"'), 'el elegido es el del select');
  assert.ok(/<select id="care-type" name="type"[^>]*>/.test(careScreen), 'el select del tipo sigue en el formulario');
  assert.equal((careScreen.match(/data-garden-action="care-quick"/g) || []).length, 3, 'los tres atajos siguen');
  assert.ok(careScreen.includes('data-care-guide-link') && careScreen.includes('Atajos'));
  assert.ok(careList.includes('is-corrected'), 'la fila corregida trae su clase para el estilo');
  const idle = {hasDevice:true, active:null, history:[], orders:[], lastDiagnostic:null};
  const support = Sp.screen({status:'ready', gardens:[garden], garden, data:idle, diagnostic:null});
  assert.ok(support.includes('Revisar mi equipo') && support.includes('Autorizo al equipo de soporte') && support.includes('disabled') && !/token/i.test(support));
  const caso = {id:'c1', folio:'CS-1A2B3C4D', incident:'bomba', note:'', state:'en_atencion', createdAt:'2026-11-08T10:00:00Z', authorizedUntil:'2999-01-01T00:00:00Z', revokedAt:null, closedAt:null, result:null, resolutionNote:null, attendedBy:dirty, diagnosticId:null};
  const active = Sp.screen({status:'ready', gardens:[garden], garden, data:{...idle, active:caso, orders:[{id:'o', type:'reiniciar', plant:null, duration:null, state:'confirmado', createdAt:'2026-11-08T10:30:00Z', error:null}]}, diagnostic:null});
  assert.ok(active.includes('Revocar acceso') && active.includes('Cancelar solicitud') && active.includes('Autorización vigente') && active.includes('está revisando') && !active.includes('<img src=x'));
  assert.ok(Sp.screen({status:'ready', gardens:[garden], garden, data:{...idle, active:{...caso, revokedAt:'2026-11-08T11:00:00Z'}}, diagnostic:null}).includes('Acceso revocado'));
  assert.ok(Sp.diagnosticCard({state:'completado', startedAt:'x', checks:[{component:'bomba_2', result:'falla', detail:dirty}, {component:'conexion', result:'correcto', detail:''}]}).includes('Encontramos 1 problema'));
  assert.ok(Sp.diagnosticCard({state:'completado', startedAt:'x', checks:[{component:'conexion', result:'correcto', detail:''}]}).includes('Todo funciona'));
  assert.ok(Sp.diagnosticCard({state:'en_curso', startedAt:'x', checks:[]}).includes('Revisando tu equipo'));
  assert.ok(Sp.confirmations.revoke.peligro && Sp.confirmations.cancel.accion === 'Cancelar solicitud');
  }
  assert.ok(V.orderCard({type:'regar', plant:2, duration:8, state:'confirmado'}).includes('Confirmada'));
  assert.ok(V.orderCard({type:'autodiagnostico', state:'expirado'}).includes('Sin respuesta'));
  assert.ok(V.errorText('huerto-limite').includes('3 huertos'));
  // Tarjeta de orden: consulta en segundo plano hasta la respuesta del equipo y luego se detiene.
  const calls = {intervals:[], cleared:0, notices:[]};
  const tracker = vm.createContext({GardenModel:M, GardenViews:{fillSlot() {}, orderCard:() => ''}, setInterval:f => { calls.intervals.push(f); return 1; }, clearInterval:() => { calls.cleared += 1; },
    mostrarAviso:(type, text) => calls.notices.push([type, text]), Date});
  vm.runInContext(bloque('controladores/huerto.js', 'Huerto').split('const GardenSummaryController')[0], tracker);
  const track = vm.runInContext('GardenOrderCard', tracker).track;
  const service = {orderState:async () => ({status:'ready', command:{id:'x', state:'confirmado'}})};
  track({root:{}, order:{id:'x', state:'pendiente'}, service, signal:{aborted:false}});
  await calls.intervals[0]();
  assert.equal(calls.cleared, 1); assert.equal(calls.notices[0][0], 'exito');
  // La vinculación de 26 caracteres y la ayuda por correo ya no existen en la parte de usuario.
  const equipos = ['modelos', 'vistas', 'controladores'].map(dir => read(`${dir}/equipos.js`)).join('\n');
  for(const gone of ['BindingHelp', 'BindingUserController', 'userPanel', 'mailto:', '26 caracteres', '/api/vinculacion\'']) assert.ok(!equipos.includes(gone), gone);
  const huertoSources = ['modelos', 'vistas', 'controladores'].map(dir => read(`${dir}/huerto.js`)).join('\n');
  for(const gone of ['UserGardenService', 'UserGardenViews', 'UserGardenController', 'user-locked', 'supportMail', 'issuePermission', 'copy-token', '/api/huertos/actual']) assert.ok(!huertoSources.includes(gone), gone);
  assert.ok(!/token/i.test(huertoSources), 'el token de soporte ya no existe');
  // Gobernanza y despliegues se retiraron del panel de administración.
  const admin = bloque('vistas/administracion.js', 'Administracion'), adminModel = bloque('modelos/administracion.js', 'Administracion'), adminControl = bloque('controladores/administracion.js', 'Administracion');
  for(const gone of ['Gobernanza de datos', 'Despliegues y parámetros', 'Comprobar formato', 'Registrar solicitud de despliegue', 'No está conectado a ningún asistente']) assert.ok(!admin.includes(gone), gone);
  assert.ok(!adminControl.includes('No se ha desplegado nada'));
  assert.ok(!/releaseTypes|validateRelease|requestRelease|saveKnowledge|restartPlatform/.test(adminModel));
  const panelModel = bloque('modelos/comun.js', 'Panel');
  for(const gone of ['admin/gobernanza', 'admin/despliegues', 'ver_gobernanza', 'gestionar_cambios']) assert.ok(!panelModel.includes(gone), gone);
  console.log('PASS Mi huerto (A, B y C), selector, tarjeta de orden y retirada de la vinculación de 26 caracteres');
});

// ── Guías de cuidado: modelo y separación de capas ────────────────────────────────────────────
suite('guías de cuidado', async () => {
  const calls = [];
  let reply = {http:200, body:{status:'ready', guides:[]}};
  const context = vm.createContext({URL, ChilitoHTTP:{sessionExpired() { calls.push('expired'); }, async request(path, options) {
    calls.push({path, options});
    if(reply === 'throw') throw new TypeError('network');
    return reply;
  }}});
  vm.runInContext(bloque('modelos/huerto.js', 'Guias'), context);
  const service = vm.runInContext('CareGuideService', context);
  // Enlaces y párrafos.
  for(const bad of ['javascript:alert(1)', 'data:text/html,x', 'ftp://a.test/', 'no-es-url', null, 7]) assert.equal(service.safeUrl(bad), null, String(bad));
  assert.equal(service.safeUrl('https://a.test/x'), 'https://a.test/x');
  assert.deepEqual([...service.paragraphs('Uno\nsigue\n\n  Dos \n \nTres')], ['Uno\nsigue', 'Dos', 'Tres']);
  // Adaptación: el enlace peligroso no llega a la vista y una ficha inválida se descarta.
  reply = {http:200, body:{status:'ready', guides:[
    {key:'a-1', question:'¿A?', answer:'x', source:{name:'F', url:'javascript:alert(1)'}},
    {key:'MAL CLAVE', question:'¿B?', answer:'x', source:null}]}};
  const list = await service.published();
  assert.equal(list.status, 'ready'); assert.equal(list.items.length, 1);
  assert.equal(list.items[0].source.url, null); assert.equal(list.items[0].source.name, 'F');
  // Estados de error.
  for(const [http, code, status] of [[403,'access-denied','forbidden'],[403,'mfa-required','mfa'],[409,'stale-record','stale'],[409,'operation-conflict','conflict'],[429,'rate-limited','limited'],[400,'invalid-input','invalid'],[503,'service-unavailable','error'],[401,'unauthenticated','unauthenticated']]) {
    reply = {http, body:{code}};
    assert.equal((await service.panel()).status, status, code);
  }
  assert.ok(calls.includes('expired'));
  reply = 'throw';
  assert.equal((await service.published()).status, 'network');
  assert.equal((await service.update('x', 1, {question:'a', answer:'b', order:'1', sourceName:'', sourceUrl:''})).status, 'network');
  // Escrituras: rutas, versión y solo los campos del contrato.
  reply = {http:200, body:{status:'accepted'}};
  await service.update('id/1', 3, {question:'q', answer:'a', order:'12', sourceName:'n', sourceUrl:'https://a.test', extra:'no'});
  const sent = calls.at(-1);
  assert.equal(sent.path, '/api/admin/guias/id%2F1/editar');
  assert.deepEqual(Object.keys(sent.options.body).sort(), ['answer','order','question','sourceName','sourceUrl','version']);
  assert.equal(sent.options.body.order, 12); assert.equal(sent.options.body.version, 3);
  // Aviso previo del formulario.
  const base = {question:'q', answer:'a', order:'1', sourceName:'', sourceUrl:''};
  assert.equal(service.check(base), null);
  for(const [change, field] of [[{question:' '},'question'],[{answer:''},'answer'],[{order:'0'},'order'],[{order:'x'},'order'],[{order:'10000'},'order'],[{sourceUrl:'javascript:alert(1)',sourceName:'n'},'sourceUrl'],[{sourceUrl:'https://a.test'},'sourceName']])
    assert.equal(service.check({...base, ...change}).field, field);
  // Sin catálogo paralelo ni HTML con datos del servidor.
  const model = bloque('modelos/huerto.js', 'Guias'), view = bloque('vistas/huerto.js', 'Guias'), control = bloque('controladores/huerto.js', 'Guias');
  for(const source of [model, view, control]) for(const question of ['germinar', '¿Para qué sirve', 'goteros', 'flotador']) assert.ok(!source.includes(question), question);
  assert.ok(!/fetch\(|ChilitoHTTP/.test(view));
  assert.ok(!/document\.|querySelector/.test(model));
  assert.ok(!/innerHTML/.test(view));
  assert.ok(!/fetch\(|ChilitoHTTP/.test(control));
  assert.ok(!/<img|data-image|placeholder/i.test(view));
  console.log('PASS guías de cuidado');
});

// ── Guardián MVC: los controladores coordinan; escribir en el DOM es de las vistas ─
// Revisión estática del código fuente; no sustituye la prueba en navegador.
suite('MVC', () => {
  const dir = name => path.join(FRONT, name);
  // Escrituras al DOM que no deben aparecer en controladores/.
  const writes = [
    /\.textContent\s*=(?!=)/, /\.innerHTML\s*=(?!=)/, /insertAdjacentHTML\(/, /\.disabled\s*=(?!=)/, /\.hidden\s*=(?!=)/,
    /\.inert\s*=(?!=)/, /\.checked\s*=(?!=)/, /\.value\s*=(?!=)/, /classList\./, /\.setAttribute\(/, /\.removeAttribute\(/,
    /\.toggleAttribute\(/, /\.replaceChildren\(/, /\.style\./, /\.showModal\(/, /scrollIntoView\(/, /\.focus\(/,
    /document\.title\s*=/, /\.tabIndex\s*=/, /\.src\s*=(?!=)/, /\.readOnly\s*=(?!=)/,
    // Cerrar diálogos y vaciar formularios también es presentación (salvo las operaciones de la propia vista).
    /(?<!view|calendars)\.close\(/, /(?<!view)\.reset\(\)/, /\.remove\(\)/
  ];
  // Excepciones explícitas, cada una con su motivo.
  const exceptions = {
    // La prueba de guías prohíbe cualquier uso de HTML en la vista de guías: la plantilla fija del panel se inserta aquí.
    'huerto.js': line => /root\.innerHTML = CareGuideViews\.adminShell\(service\.LIMITS\);/.test(line)
  };
  const found = [];
  for(const name of fs.readdirSync(dir('controladores')).filter(file => file.endsWith('.js'))) {
    read('controladores/' + name).split('\n').forEach((line, index) => {
      const code = line.replace(/\/\/.*$/, '');
      if(!writes.some(pattern => pattern.test(code))) return;
      if(exceptions[name]?.(code)) return;
      found.push(`controladores/${name}:${index + 1}: ${line.trim()}`);
    });
  }
  assert.deepEqual(found, [], 'Escrituras al DOM en controladores:\n' + found.join('\n'));

  // Ni vistas ni controladores hablan con el servidor: eso es del modelo.
  for(const folder of ['vistas', 'controladores'])
    for(const name of fs.readdirSync(dir(folder)).filter(file => file.endsWith('.js')))
      assert.ok(!/fetch\(|ChilitoHTTP\.(get|post|request|send)\(/.test(read(`${folder}/${name}`)), `${folder}/${name} no debe llamar al servidor`);

  // El menú y el encabezado (navegacion.js) son presentación: viven en vistas/, no en controladores/.
  assert.ok(fs.existsSync(dir('vistas/navegacion.js')) && !fs.existsSync(dir('controladores/navegacion.js')), 'navegacion.js debe estar en vistas/');

  // Las vistas no deciden por capacidades qué enlaces mostrar.
  assert.ok(!/allowedAdmin\(/.test(bloque('vistas/administracion.js', 'Administracion')), 'la vista de administración no debe consultar capacidades');
  assert.ok(!/allowedAdmin\(/.test(bloque('vistas/comun.js', 'Panel')), 'la vista del panel no debe consultar capacidades');

  console.log('PASS MVC: controladores sin escrituras al DOM (1 excepción documentada); vistas y controladores sin acceso al servidor.');
});

// ── Editor de textos legales: autoguardado, pegado y documento subido ─────────────────────────
suite('editor legal: autoguardado cada 10 s, pegado saneado en el servidor y .docx', async () => {
  const llamadas = {created:[], edited:[], sanitized:[], imported:[], inserted:[], saved:[], notices:[], replaced:[], cleared:0};
  let tick = null, editResult = null;
  const area = {name:'content', readOnly:false, selectionStart:2, selectionEnd:2, closest(selector) { return selector === '[name=content]' ? this : null; }};
  const form = {elements:{version:{value:'1.2'}, title:{value:'Términos'}, content:{value:'<p>a</p>'}}};
  const handlers = {};
  const root = {addEventListener:(type, fn) => { handlers[type] = fn; }, querySelector:selector => selector === '[data-admin-form="legal"]' ? form : null};
  const doc = {id:'11111111-1111-4111-8111-111111111111', type:'terminos', state:'borrador', updatedAt:'2026-11-16T10:00:00Z', html:'<p>a</p>'};
  const service = {TYPES:['terminos'], VERSION:/^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$/, fileProblem:file => /\.docx$/i.test(file.name) ? null : 'documento-no-docx',
    create:async values => { llamadas.created.push(values); return {status:'accepted', document:{...doc}}; },
    edit:async (id, values) => { llamadas.edited.push([id, values]); return editResult || {status:'accepted', document:{...doc, updatedAt:'2026-11-16T10:00:10Z'}}; },
    sanitize:async html => { llamadas.sanitized.push(html); return {status:'ready', html:'<p>hola</p>'}; },
    importDocx:async file => { llamadas.imported.push(file); return {status:'ready', html:'<h2>Doc</h2>'}; }};
  const history = {replaced:[], replaceState(state, title, url) { this.replaced.push(url); }};
  const context = vm.createContext({AbortController, JSON, Date, Promise, history, location:{hash:''},
    setInterval:fn => { tick = fn; return 7; }, clearInterval:() => { llamadas.cleared += 1; },
    mostrarAviso:(type, text) => llamadas.notices.push([type, text]), confirmar:async () => true,
    AdminTableViews:{paint() {}}, LegalAdminService:service,
    LegalAdminViews:{editorScreen:() => '', listScreen:() => '', errorText:code => code, showPreview() {}, insertTag() {},
      insertText:(r, text, start, end) => llamadas.inserted.push([text, start, end]), replaceContent:(r, text) => llamadas.replaced.push(text),
      saved:(r, at) => llamadas.saved.push(at), chooseFile() {}, confirmations:{replace:{}}}});
  vm.runInContext(bloque('controladores/administracion.js', 'Legales'), context);
  vm.runInContext('LegalAdminController', context).mount({root, route:{extra:'nuevo-terminos'}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(typeof tick, 'function', 'el editor de un borrador arranca el autoguardado');
  await tick();
  assert.equal(llamadas.created.length, 0, 'sin cambios no guarda');
  form.elements.version.value = 'abc'; form.elements.content.value = '<p>b</p>';
  await tick();
  assert.equal(llamadas.created.length, 0, 'un borrador nuevo sin versión válida no se crea solo');
  form.elements.version.value = '1.2';
  await tick();
  assert.deepEqual(JSON.parse(JSON.stringify(llamadas.created)), [{type:'terminos', version:'1.2', title:'Términos', content:'<p>b</p>'}]);
  assert.deepEqual(history.replaced, [`#admin/legales/${doc.id}`]);
  assert.ok(llamadas.saved.at(-1) instanceof Date);
  await tick();
  assert.equal(llamadas.edited.length, 0, 'lo ya guardado no se vuelve a enviar');
  form.elements.content.value = '<p>c</p>';
  await tick();
  assert.equal(llamadas.edited.length, 1); assert.equal(llamadas.edited[0][0], doc.id); assert.equal(llamadas.edited[0][1].expectedAt, doc.updatedAt);
  editResult = {status:'error', code:'stale-record'};
  form.elements.content.value = '<p>d</p>';
  const antes = llamadas.cleared;
  await tick();
  assert.equal(llamadas.cleared, antes + 1, 'si otra persona cambió el borrador, el autoguardado se detiene');
  assert.deepEqual(llamadas.notices.at(-1), ['error', 'stale-record']);
  // Pegar HTML: se cancela el pegado nativo y entra el resultado del servidor, nunca el HTML del portapapeles.
  let prevented = 0;
  const sucio = '<p onclick="x()">hola</p><script>alert(1)</script>';
  await handlers.paste({target:area, preventDefault:() => { prevented += 1; }, clipboardData:{types:['text/plain', 'text/html'], getData:() => sucio}});
  assert.equal(prevented, 1); assert.deepEqual(llamadas.sanitized, [sucio]); assert.deepEqual(llamadas.inserted, [['<p>hola</p>', 2, 2]]);
  await handlers.paste({target:area, preventDefault:() => { prevented += 1; }, clipboardData:{types:['text/plain'], getData:() => 'texto'}});
  assert.equal(prevented, 1, 'sin HTML el pegado es el normal');
  // Documento: un archivo que no es .docx no sale del navegador; uno válido reemplaza el contenido con el HTML del servidor.
  const input = files => ({matches:selector => selector === '[data-legal-file]', files});
  await handlers.change({target:input([{name:'aviso.pdf', size:10}])});
  assert.equal(llamadas.imported.length, 0); assert.deepEqual(llamadas.notices.at(-1), ['error', 'documento-no-docx']);
  await handlers.change({target:input([{name:'aviso.docx', size:10}])});
  assert.equal(llamadas.imported.length, 1); assert.deepEqual(llamadas.replaced, ['<h2>Doc</h2>']);
  console.log('PASS editor legal: autoguardado cada 10 s, pegado saneado en el servidor y .docx');
});

// ── Ejecución: una suite tras otra ────────────────────────────────────────────────────────────
(async () => {
  let fallas = 0;
  for(const [titulo, ejecutar] of suites) {
    try { await ejecutar(); }
    catch(error) { fallas++; console.error(`FALLA ${titulo}:`, error); }
  }
  console.log(fallas ? `\n${fallas} de ${suites.length} suites fallaron.` : `\nOK: ${suites.length} suites.`);
  process.exitCode = fallas ? 1 : 0;
})();

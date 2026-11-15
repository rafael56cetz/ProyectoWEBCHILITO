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

// ── Comercial: validaciones y borradores, sin red, DOM ni almacenamiento ──────────────────────
suite('comercial', () => {
  const forbidden = () => { throw new Error('El modelo comercial no debe consultar red, DOM ni almacenamiento'); };
  const context = vm.createContext({structuredClone, UserGardenService:{tasks:{}}, ChilitoHTTP:{request:forbidden}, fetch:forbidden,
    get document() { return forbidden(); }, get localStorage() { return forbidden(); }, get sessionStorage() { return forbidden(); }});
  cargar(context, 'modelos/cuenta.js', 'modelos/comun.js', 'modelos/huerto.js', 'modelos/administracion.js');
  const model = vm.runInContext('CommerceModel', context), app = vm.runInContext('AppModel', context);
  let checks = 0;
  function check(title, run) { run(); checks++; console.log('PASS ' + title); }
  check('Importes exactos en unidades menores; punto o coma decimal', () => {
    for(const [raw, expected] of [['0',0],['0.01',1],['0,10',10],['19.99',1999],[' 123,45 ',12345],['999999999.99',99999999999]]) assert.equal(model.amount(raw), expected);
    assert.equal(model.amount('0.10') + model.amount('0.20'), 30);
  });
  check('Rechaza negativos, exponentes, miles, fracciones excesivas y desbordamiento', () => {
    for(const raw of ['',null,1,'-1','+1','1e3','Infinity','NaN','1,000.00','1.000,00','0.001','0,001','.50','1.','1000000000.00']) assert.equal(model.amount(raw), null, String(raw));
  });
  const base = {equipment:'EQ-UNIT-1',email:'persona@example.test',saleDate:'2026-11-10',total:'0.30',received:'0.10',reference:'Referencia declarada',deliveryMode:'domicilio',deliveryDate:'2026-11-11'};
  check('Saldo de borrador exacto y sin estados persistidos de venta o pago', () => {
    const result = model.sale(base, '2026-11-11'); assert.equal(Object.keys(result.errors).length, 0); assert.equal(result.data.balanceMinor, 20);
    for(const key of ['paid','delivered','linked','saleId','saved']) assert.equal(Object.hasOwn(result.data, key), false);
    assert.equal(Object.keys(model.sale({...base, received:'0.30'}, '2026-11-11').errors).length, 0);
  });
  check('Precio positivo, recibido obligatorio y sin sobrepago', () => {
    for(const [patch, key] of [[{total:'0'},'total'],[{received:''},'received'],[{received:'-0.01'},'received'],[{received:'0.31'},'received']]) assert.ok(model.sale({...base, ...patch}, '2026-11-11').errors[key]);
    assert.equal(Object.keys(model.sale({...base, received:'0'}, '2026-11-11').errors).length, 0);
  });
  check('Fechas reales, bisiestos, venta no futura y entrega no anterior', () => {
    for(const [patch, key] of [[{saleDate:'2026-02-29'},'saleDate'],[{saleDate:'2026-11-12'},'saleDate'],[{deliveryDate:'2026-04-31'},'deliveryDate'],[{deliveryDate:'2026-11-09'},'deliveryDate']]) assert.ok(model.sale({...base, ...patch}, '2026-11-11').errors[key]);
    assert.equal(Object.keys(model.sale({...base, saleDate:'2024-02-29', deliveryDate:''}, '2026-11-11').errors).length, 0);
  });
  check('Identificador, destinatario, modalidad y referencia validados sin consultar cuentas', () => {
    for(const [patch, key] of [[{equipment:' '},'equipment'],[{email:'a@'},'email'],[{email:'a b@c.test'},'email'],[{email:'<a>@c.test'},'email'],[{email:'a)b@c.test'},'email'],[{email:'.a@b.test'},'email'],[{email:'a..b@c.test'},'email'],[{email:'a@-b.test'},'email'],[{email:'a\n@b.test'},'email'],[{email:'a'.repeat(255) + '@b.test'},'email'],[{reference:'x'.repeat(121)},'reference'],[{reference:'a\nb'},'reference'],[{deliveryMode:'envio-inventado'},'deliveryMode']]) assert.ok(model.sale({...base, ...patch}, '2026-11-11').errors[key]);
    assert.equal(Object.keys(model.sale({...base, email:'persona+etiqueta@example.test', deliveryMode:'recogida', reference:''}, '2026-11-11').errors).length, 0);
  });
  check('Equipo: no inventa vinculación o conexión; rechaza controles y disponibilidad ajena', () => {
    const result = model.equipment({identifier:'ESP32:ABC-01', gardenName:'Huerto uno', availability:'disponible'});
    assert.equal(Object.keys(result.errors).length, 0); assert.equal(Object.hasOwn(result.data, 'connected'), false);
    for(const [patch, key] of [[{identifier:'a b'},'identifier'],[{gardenName:'\n'},'gardenName'],[{gardenName:'x'.repeat(121)},'gardenName'],[{availability:'conectado'},'availability']]) assert.ok(model.equipment({...result.data, ...patch}).errors[key]);
  });
  check('Rangos de filtros y periodos civiles sin conversión UTC del dato escrito', () => {
    assert.ok(model.period({since:'2026-11-11', until:'2026-11-10'}).until);
    assert.ok(model.period({since:'2026-02-29', until:''}).since);
    assert.equal(Object.keys(model.period({since:'2024-02-29', until:'2024-02-29'})).length, 0);
    const current = model.periodPreset('current'); assert.equal(current.until, model.today()); assert.ok(current.since.endsWith('-01'));
  });
  check('Los borradores sobreviven a pestañas; una edición invalida su revisión', () => {
    const local = model.create(); local.edit('equipment', {identifier:'EQ-UNIT-1', gardenName:'Huerto de prueba', availability:'disponible'}); local.review('equipment');
    local.select('ventas'); local.edit('sale', {...base, saleDate:model.today(), deliveryDate:''}); local.review('sale');
    for(const tab of ['resumen','vinculacion','equipos','ventas']) local.select(tab);
    assert.equal(local.read().equipmentReview.identifier, 'EQ-UNIT-1'); assert.equal(local.read().saleReview.email, base.email);
    const snapshot = local.read(); snapshot.sale.email = 'alterado@example.test'; assert.equal(local.read().sale.email, base.email);
    local.edit('sale', {received:'0.20'}); assert.equal(local.read().saleReview, null); assert.ok(local.read().equipmentReview);
    local.dispose(); assert.equal(local.read().saleReview, null); assert.equal(Object.keys(local.read().sale).length, 0);
    assert.equal(model.create().read().sale.email, '');
  });
  check('Visibilidad provisional solo con capacidad existente; no por is_staff ni por rol', () => {
    for(const session of [{role:'admin',capabilities:[]},{is_staff:true,is_superuser:true},{capabilities:['ver_flota']},{capabilities:['atender_soporte']}]) assert.ok(!app.allowedAdmin(session).some(x => x.id === 'admin/comercial'));
    assert.ok(app.allowedAdmin({capabilities:['vincular_huertos']}).some(x => x.id === 'admin/comercial'));
  });
  console.log(`PASS comercial: ${checks} grupos, sin operaciones externas.`);
});

// ── Fechas civiles y contrato HTTP de los filtros de mantenimientos ───────────────────────────
suite('fechas', async () => {
  const zonaOriginal = process.env.TZ;
  async function checkZone(TZ) {
    process.env.TZ = TZ;
    const calls = [];
    const context = vm.createContext({URLSearchParams, UserGardenService:{tasks:{}}, ChilitoHTTP:{
      async request(path) { calls.push(path); return {http:200, body:{status:'ready'}}; }
    }});
    cargar(context, 'modelos/huerto.js');
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
    await service.list({since:'2026-11-07', until:'2026-11-09', garden:'1', state:'active', task:'inspection'});
    assert.equal(calls.at(-1), '/api/admin/mantenimientos?since=2026-11-07&until=2026-11-09&garden=1&state=active&task=inspection');
    await service.list({since:'', until:''});
    assert.equal(calls.at(-1), '/api/admin/mantenimientos');
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
    URLSearchParams, document:{cookie:'csrftoken=test-csrf'}, window:{dispatchEvent() {}}, Event, fetch:null});
  const calls = []; let respond;
  context.fetch = async (path, options) => { calls.push({path, options}); return respond(path, options); };
  cargar(context, 'modelos/cuenta.js', 'modelos/comun.js', 'modelos/huerto.js', 'modelos/administracion.js');
  const evaluate = code => vm.runInContext(code, context);
  const reply = (http, body) => ({status:http, json:async () => body});
  respond = () => reply(403, {code:'forbidden'});
  assert.equal((await evaluate("UserGardenService.recordTask('inspection')")).status, 'forbidden');
  const p = calls.at(-1); assert.equal(p.path, '/api/huertos/actual/mantenimiento'); assert.equal(p.options.method, 'POST'); assert.equal(JSON.parse(p.options.body).type, 'inspection'); assert.match(p.options.headers['Idempotency-Key'], /^[0-9a-f-]{36}$/); assert.equal(p.options.headers['X-CSRFToken'], 'test-csrf');
  let n = 0; respond = () => { if(n++ === 0) throw new Error('network'); return reply(200, {status:'accepted'}); };
  await evaluate("UserGardenService.recordTask('harvest')"); await evaluate("UserGardenService.recordTask('harvest')");
  assert.equal(calls.at(-2).options.headers['Idempotency-Key'], calls.at(-1).options.headers['Idempotency-Key']);
  const token = 'aB'.repeat(21) + '_'; const ticket = '4c0eb447-d16e-4ef6-89e5-127ab340c1b1';
  respond = () => reply(200, {status:'accepted', permission:{token, ticket, createdAt:Date.now(), expiresAt:Date.now() + 60000}});
  assert.equal((await evaluate("UserGardenService.issuePermission('connection',true)")).status, 'accepted');
  assert.equal(evaluate('UserGardenService.permission().token'), token);
  const before = calls.length;
  assert.equal((await evaluate("AdminService.validateToken('case',' '+ 'a'.repeat(43))")).status, 'invalid-token'); assert.equal(calls.length, before);
  respond = (path, options) => { assert.equal(JSON.parse(options.body).token, token); return reply(200, {status:'accepted', session:{id:'session-id', expiresAt:Date.now() + 60000}}); };
  context.exactToken = token; await evaluate("AdminService.validateToken('case',exactToken)");
  assert.equal(calls.at(-1).path, '/api/admin/soporte/case/abrir'); assert.ok(!calls.at(-1).path.includes(token));
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
  const missing = {value:null, quality:'missing', at:null};
  context.inputGarden = {status:'waiting', name:'Huerto', updatedAt:null, plants:[1, 2, 3].map(id => ({id, zoneId:String(BigInt(id) + 9007199254740992n), name:'Planta ' + id, crop:'Habanero propio', reading:missing})), temperature:missing, humidity:missing, tank:{state:'unknown', at:null}};
  // Texto decimal largo y explícito: los identificadores de zona no se convierten a Number.
  context.inputGarden.plants.forEach((p, i) => p.zoneId = String(9007199254740993n + BigInt(i)));
  assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].crop'), 'Habanero propio'); assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].zoneId'), '9007199254740993'); assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].reading.value'), null);
  cargar(context, 'vistas/comun.js', 'vistas/publico.js', 'vistas/cuenta.js', 'vistas/huerto.js', 'vistas/administracion.js');
  context.bad = '<img src=x onerror=alert(1)>'; context.inputGarden.name = context.bad; context.inputGarden.plants[0].name = context.bad; context.inputGarden.plants[0].crop = context.bad;
  const markup = evaluate("UserGardenViews.render('huerto',{garden:AppModel.garden(inputGarden),soil:{moisture:{value:null,quality:'missing',at:null}},connection:{wifi:null,mqtt:null}})"); assert.ok(!markup.includes('<img src=x')); assert.ok(markup.includes('&lt;img'));
  console.log('PASS frontend adapters: server refusal, CSRF, uncertain-write idempotency, exact support token, capabilities, crop/IDs/null, Unicode password bounds and secret-free reset URLs.');
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
  const views = vm.createContext({escaparHTML:escape, icon:() => '', plantDrawing:() => '', GardenModel:M, MaintenanceDates:{format:() => '2026-11-08', today:() => 0}, UserGardenViews:{chart:() => ''},
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
  assert.ok(V.plantDialogs(plants[0], true).water.includes('Si el depósito no tiene agua, tu equipo no regará.'));
  assert.ok(V.myGardens({status:'ready', gardens:[detail(equipo).garden]}).includes('Desvincular equipo'));
  assert.ok(V.myGardens({status:'ready', gardens:[detail(null).garden]}).includes('Archivar huerto'));
  assert.ok(V.newGarden().includes('Nombre del huerto (opcional)'));
  assert.ok(V.confirmations.desvincular('CHI-1').peligro && V.confirmations.archivar('Patio').accion === 'Archivar huerto');
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
  assert.ok(!bloque('vistas/huerto.js', 'Huerto usuario').includes('user-locked'));
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

// ── Guardián MVC (CLAUDE.md §2): los controladores coordinan; escribir en el DOM es de las vistas ─
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

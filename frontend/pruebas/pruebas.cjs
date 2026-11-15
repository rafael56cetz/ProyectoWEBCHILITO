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

// ── Ayuda para vincular: borrador de correo sin secretos ──────────────────────────────────────
suite('ayuda de vinculación', () => {
  function load(supportContact) {
    const context = vm.createContext({ChilitoHTTP:{configuration:{supportContact}}});
    cargar(context, 'modelos/equipos.js');
    return vm.runInContext('BindingHelp', context);
  }
  const SUPPORT = 'soporte@example.test';
  const SUBJECT = '[El Chilito] Ayuda con la vinculación';
  const OPENING = 'Hola, necesito ayuda para vincular mi huerto. ';
  const parts = href => {
    const [target, query] = href.slice('mailto:'.length).split('?');
    assert.deepEqual([...new URLSearchParams(query).keys()], ['subject', 'body']);
    const field = name => decodeURIComponent(query.split('&').find(p => p.startsWith(name + '=')).slice(name.length + 1));
    return {target, subject:field('subject'), body:field('body')};
  };
  const help = load(SUPPORT);

  // Cuatro motivos, destinatario y asunto.
  for(const [reason, detail, expected] of [
    ['expired', '', 'venció antes de completar la vinculación'],
    ['lost', '', 'Perdí o no encuentro el código'],
    ['rejected', '', 'no funciona al intentar vincular'],
    ['other', 'La pantalla se queda en blanco.', 'por este motivo: La pantalla se queda en blanco.']]) {
    const draft = help.draft(reason, detail);
    assert.equal(draft.status, 'ready', reason);
    const mail = parts(draft.href);
    assert.equal(mail.target, SUPPORT);
    assert.equal(mail.subject, SUBJECT);
    assert.ok(mail.body.startsWith(OPENING), reason);
    assert.ok(mail.body.includes(expected), reason);
    assert.ok(mail.body.includes('\r\n\r\nInformación adicional'), reason);
  }
  assert.ok(help.draft('expired').body.includes('El código que recibí venció antes de completar la vinculación. Quisiera solicitar orientación para obtener uno nuevo.'));

  // Texto para copiar: sale del mismo borrador, con las tres partes separadas y sin la URL.
  for(const [reason, detail] of [['expired'], ['lost'], ['rejected'], ['other', 'Se queda en blanco.']]) {
    const draft = help.draft(reason, detail);
    assert.equal(draft.text, `Para: ${SUPPORT}\nAsunto: ${SUBJECT}\n\nMensaje:\n${draft.body.trimEnd()}\n`, reason);
    assert.ok(!draft.text.includes('mailto'), reason);
    assert.ok(!draft.text.includes('%'), reason);
  }
  assert.notEqual(help.draft('expired').text, help.draft('lost').text);
  for(const refused of [help.draft('', ''), help.draft('other', ''), help.draft('other', 'el 2FA era 123456'), load('').draft('expired')])
    assert.equal(refused.text, undefined);
  assert.ok(help.draft('other', 'ñ & ?x=1 #a %20 🌶️').text.includes('ñ & ?x=1 #a %20 🌶️'));

  // «Otro motivo» exige explicación; un motivo cerrado ignora el texto oculto.
  assert.equal(help.draft('other', '').status, 'need-detail');
  assert.equal(help.draft('other', ' \n\t ').status, 'need-detail');
  assert.equal(help.draft('', '').status, 'need-reason');
  assert.equal(help.draft('__proto__', 'x').status, 'need-reason');
  const atLimit = 'ab '.repeat((help.MAX_DETAIL - 3) / 3) + 'abc';
  assert.equal(atLimit.length, help.MAX_DETAIL);
  assert.equal(help.draft('other', atLimit).status, 'ready');
  assert.equal(help.draft('other', atLimit + 'd').status, 'too-long');
  assert.ok(!help.draft('expired', 'texto oculto').body.includes('texto oculto'));

  // Caracteres especiales: no rompen la URL, no añaden cabeceras y vuelven idénticos.
  const special = 'ñáü & ?x=1 #a %20 + "c" <b> 🌶️\r\ncc: otro@example.test&bcc=x@example.test';
  const specialMail = help.draft('other', special);
  assert.equal(specialMail.status, 'ready');
  assert.ok(!/[\s#<>"]/.test(specialMail.href));
  assert.equal(specialMail.href.match(/&/g).length, 1);
  assert.equal(specialMail.href.match(/\?/g).length, 1);
  assert.ok(parts(specialMail.href).body.includes('ñáü & ?x=1 #a %20 + "c" <b> 🌶️\r\ncc: otro@example.test&bcc=x@example.test'));
  assert.equal(help.draft('other', 'mal \uD83D formado').status, 'ready');
  assert.ok(!parts(help.draft('other', 'a\u0000b\u0007c').href).body.includes('\u0000'));

  // Nada de secretos en el borrador.
  const code = '0123456789ABCDEFGHJKMNPQRS';
  for(const value of [`mi código es ${code}`, code.toLowerCase(), code.replace(/(.{6})/g, '$1-'), code.replace(/(.{6})/g, '$1 '), 'el 2FA era 123456'])
    assert.equal(help.draft('other', value).status, 'secret', value);
  assert.equal(help.draft('other', 'Mi teléfono no recibe el correo desde 2024.').status, 'ready');
  for(const reason of ['expired', 'lost', 'rejected']) {
    const body = help.draft(reason).body;
    assert.ok(!/(?:[0-9A-Z]-?){26}|\d{6}/.test(body), reason);
  }

  // Destinatario: solo el contacto configurado; si falta o no es válido, no se inventa otro.
  assert.equal(help.contact(), SUPPORT);
  assert.equal(help.draft('expired').address, SUPPORT);
  for(const value of ['', '   ', null, undefined, 'no-es-correo', 'a b@example.test', 7]) {
    const missing = load(value);
    assert.equal(missing.contact(), null);
    assert.equal(missing.draft('expired').status, 'unavailable');
  }
  const crafted = load('a?bcc=x@example.test');
  assert.equal(parts(crafted.draft('expired').href).target, 'a%3Fbcc%3Dx@example.test');

  // Separación de contextos y de capas (vinculación vive sola en su archivo de equipos).
  const view = read('vistas/equipos.js'), model = read('modelos/equipos.js'), controller = read('controladores/equipos.js');
  assert.ok(!view.includes('#consiguelo'));
  assert.ok(!view.includes('Consíguelo'));
  assert.ok(!view.includes('Copiar correo'));
  assert.ok(bloque('vistas/publico.js', 'Pagina publica').includes('id="consiguelo"'));
  for(const label of ['Solicitar ayuda para vincular mi huerto', 'El código venció.', 'Perdí o no encuentro el código.', 'El código no funciona.', 'Otro motivo', 'Preparar correo', 'Copiar mensaje preparado', 'Copiar dirección de soporte']) assert.ok(view.includes(label), label);
  assert.ok(!/fetch\(|ChilitoHTTP/.test(view));
  assert.ok(!/document\.|querySelector/.test(model));
  for(const source of [view, model, controller]) assert.ok(!/correo enviado|mensaje enviado/i.test(source));
  const helpSource = controller.slice(controller.indexOf('const BindingHelpController'));
  assert.ok(!/service\.consume|ChilitoHTTP|fetch\(/.test(helpSource));
  assert.equal(helpSource.match(/service\.draft\(/g).length, 1);
  assert.equal(helpSource.match(/openMail\(/g).length, 1);
  console.log('PASS ayuda de vinculación');
});

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
suite('tarjeta del huerto', async () => {
  const context = vm.createContext({});
  vm.runInContext(bloque('modelos/huerto.js', 'Diagnostico'), context);
  const D = vm.runInContext('GardenDiagnosis', context);
  const NOW = Date.parse('2026-11-08T12:00:00Z'), at = '2026-11-08T11:58:00+00:00';
  const rule = c => ({source:'rules', title:'Revisa', message:'Nivel bajo.', next:'Rellena', generatedAt:at, ...c});
  const exp = c => ({status:'available', source:'ai', text:'Porque…', generatedAt:at, expiresAt:'2026-11-08T13:00:00+00:00', ...c});
  const base = c => ({rule:rule(), readings:{state:'current', at}, explanation:null, ...c});
  const view = raw => D.present(D.adapt(raw), NOW);
  // Fechas: solo el formato canónico, con T y zona.
  for(const bad of ['2026-11-08T11:58:00', '2026-11-08 11:58:00+00:00', '2026-11-08', '20261108T115800Z', '2026-11-08T11:58Z', 'ayer']) assert.equal(D.adapt(base({rule:rule({generatedAt:bad})})), null, bad);
  for(const good of ['2026-11-08T11:58:00.000+00:00', '2026-11-08T11:58:00Z', '2026-11-08T05:58:00-06:00']) assert.notEqual(D.adapt(base({rule:rule({generatedAt:good})})), null, good);
  // Vacío e inválido: null, sin lanzar.
  for(const bad of [null, undefined, '', 'x', 7, [], {}, {rule:{}}, base({rule:rule({source:'ai'})}), base({rule:rule({title:' '})}), base({rule:rule({title:'x'.repeat(121)})}), base({rule:rule({message:7})}), base({rule:rule({message:'a\u0000b'})}), base({rule:rule({generatedAt:'ayer'})}), base({rule:rule({next:5})}), base({readings:null}), base({readings:{state:'fresh', at}}), base({readings:{state:'stale', at:null}}), base({readings:{state:'missing', at}})])
    assert.equal(D.adapt(bad), null, JSON.stringify(bad));
  assert.equal(D.present(null), null);
  // Solo reglas: sin nada que mencione IA.
  const solo = view(base());
  assert.equal(solo.title, 'Revisa'); assert.match(solo.origin, /^Resumen por reglas/); assert.equal(solo.explanation, null);
  assert.ok(!/\bIA\b/.test(JSON.stringify(solo)));
  assert.equal(view(base({rule:rule({next:null})})).next, null);
  // Lecturas: cada estado con su texto.
  assert.match(view(base({readings:{state:'missing', at:null}})).readings, /Sin lecturas disponibles/);
  assert.match(view(base({readings:{state:'stale', at}})).readings, /Lecturas antiguas/);
  assert.match(view(base()).readings, /^Lecturas del /);
  // Explicación: disponible, y etiquetada como IA solo entonces.
  const full = view(base({explanation:exp()}));
  assert.equal(full.explanation.state, 'available'); assert.equal(full.explanation.text, 'Porque…'); assert.match(full.explanation.note, /generada con IA/);
  assert.equal(full.title, 'Revisa', 'la explicación no sustituye al mensaje');
  // Sin validez: la regla se mantiene y no hay texto.
  for(const bad of [exp({text:''}), exp({text:'x'.repeat(1201)}), exp({status:'blocked'}), exp({status:'truncated'}), exp({status:'failed'}), exp({status:'empty'}), exp({source:'rules'}), exp({expiresAt:null}), exp({generatedAt:'x'}), 'x', 7, []]) {
    const v = view(base({explanation:bad}));
    assert.equal(v.title, 'Revisa'); assert.equal(v.explanation.state, 'unavailable', JSON.stringify(bad)); assert.equal(v.explanation.text, undefined);
  }
  // Caducidad: del servidor y al pasar el tiempo. No altera las lecturas.
  const fromServer = view(base({explanation:{status:'expired'}}));
  assert.equal(fromServer.explanation.state, 'expired'); assert.match(fromServer.readings, /^Lecturas del /);
  const live = D.adapt(base({explanation:exp()}));
  assert.equal(D.present(live, Date.parse('2026-11-08T13:00:00Z')).explanation.state, 'expired');
  assert.equal(D.present(live, Date.parse('2026-11-08T12:59:59Z')).explanation.state, 'available');
  assert.match(D.present(live, Date.parse('2026-11-08T14:00:00Z')).readings, /^Lecturas del /);
  assert.equal(D.msUntilExpiry(live, NOW), 3600000);
  assert.equal(D.msUntilExpiry(live, Date.parse('2026-11-09T00:00:00Z')), null);
  assert.equal(D.msUntilExpiry(D.adapt(base()), NOW), null);
  // El texto malicioso sigue siendo dato y la vista no usa HTML.
  assert.equal(view(base({rule:rule({title:'<img src=x onerror=alert(1)>'})})).title, '<img src=x onerror=alert(1)>');
  const v = bloque('vistas/huerto.js', 'Diagnostico'), card = bloque('vistas/huerto.js', 'Huerto usuario'), model = bloque('modelos/huerto.js', 'Huerto usuario');
  const admin = bloque('vistas/administracion.js', 'Administracion'), adminModel = bloque('modelos/administracion.js', 'Administracion'), adminControl = bloque('controladores/administracion.js', 'Administracion');
  assert.ok(!/innerHTML|fetch\(|ChilitoHTTP/.test(v));
  assert.ok(!/document\.|querySelector/.test(bloque('modelos/huerto.js', 'Diagnostico')));
  assert.ok(model.includes('diagnosis:GardenDiagnosis.adapt(raw.body.diagnosis)'));
  assert.ok(!/data\.diagnosis|diagnosis\.title/.test(card), 'la plantilla no inserta datos del resumen');
  assert.ok(card.includes('>Resumen de tu huerto</h2>') && !card.includes('Diagnóstico inteligente'));
  // Gobernanza y despliegues se retiraron del panel de administración.
  for(const gone of ['Gobernanza de datos', 'Despliegues y parámetros', 'Comprobar formato', 'Registrar solicitud de despliegue', 'No está conectado a ningún asistente']) assert.ok(!admin.includes(gone), gone);
  assert.ok(!adminControl.includes('No se ha desplegado nada'));
  assert.ok(!/releaseTypes|validateRelease|requestRelease|saveKnowledge|restartPlatform/.test(adminModel));
  const panelModel = bloque('modelos/comun.js', 'Panel');
  for(const gone of ['admin/gobernanza', 'admin/despliegues', 'ver_gobernanza', 'gestionar_cambios']) assert.ok(!panelModel.includes(gone), gone);
  // Caducidad: solo se repinta la tarjeta; la pantalla, con sus diálogos y su foco, no se reconstruye.
  const timers = [], paints = []; let rebuilt = 0, now = NOW;
  const root = {set innerHTML(_) { rebuilt += 1; }, querySelector: s => s === '[data-garden-diagnosis]' ? {} : null, addEventListener() {}};
  const sandbox = vm.createContext({AbortController, setTimeout: (f, ms) => timers.push({f, ms}), clearTimeout: id => { if(id) timers[id - 1].cleared = true; }, setInterval: () => 1, clearInterval() {},
    document:{addEventListener() {}}, UserGardenViews:{paint:root => { root.innerHTML = ''; }, dialog:() => null, closeDialog() {}}, GardenDiagnosisViews:{paint:(_, view) => paints.push(view)}, AppModel:{garden:g => g, alias:() => ''}, AuthService:{session:{}},
    CareGuideUserController:{attach:() => ({paint() {}})}, BindingUserController:{attach() {}}});
  vm.runInContext(bloque('modelos/huerto.js', 'Diagnostico'), sandbox);
  sandbox.nowValue = () => now;
  vm.runInContext('Date.now = () => nowValue();', sandbox);
  vm.runInContext(bloque('controladores/huerto.js', 'Huerto usuario'), sandbox);
  const adapted = vm.runInContext('GardenDiagnosis', sandbox).adapt(base({explanation:exp()}));
  const controller = vm.runInContext('UserGardenController', sandbox).mount('huerto', {root, service:{load:async () => ({garden:{status:'waiting'}, diagnosis:adapted})}});
  await new Promise(resolve => setImmediate(resolve));
  const timer = timers.filter(t => !t.cleared).at(-1);
  assert.equal(timer.ms, 3600000);
  assert.equal(paints.at(-1).explanation.state, 'available');
  const before = rebuilt;
  now += 3600000;
  timer.f();
  assert.equal(rebuilt, before, 'la caducidad no debe reconstruir la pantalla');
  assert.equal(paints.at(-1).explanation.state, 'expired');
  assert.equal(paints.at(-1).title, 'Revisa', 'la regla permanece');
  controller.dispose();
  console.log('PASS tarjeta del huerto y retirada de despliegues');
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

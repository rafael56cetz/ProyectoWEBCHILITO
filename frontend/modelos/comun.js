// MODELO · Común: documentos legales y estadísticas de privacidad, y datos del panel (destinos, saludo, huerto).
// Define: PrivacyModel, PrivacyData, AppModel, AppService.

// ── Privacidad ──
// Documentos legales y secciones que cuentan las estadísticas. La autoridad es del servidor.
const PrivacyModel = (() => {
  const documents = Object.freeze({
    terminos: Object.freeze({title:'Términos y condiciones', state:'pending', version:null}),
    privacidad: Object.freeze({title:'Aviso de privacidad', state:'pending', version:null}),
    cookies: Object.freeze({title:'Política de cookies', state:'pending', version:null})
  });
  // Pantallas a las que «Volver» no debe llevar: otro documento o un paso de acceso a medias.
  // Lista cerrada: cualquier otra pantalla, incluida la administración, no se cuenta.
  function sectionOf(route) {
    if(route.screen === 'cuenta') return route.detail === 'privacidad' ? 'privacidad' : route.detail ? null : 'cuenta';
    if(route.screen === 'inicio') return {'el-proyecto':'proyecto',prototipo:'prototipo','como-funciona':'funcionamiento'}[route.anchor] || 'inicio';
    return {huerto:'huerto',telemetria:'panel_tecnico',mantenimiento:'mantenimiento',soporte:'soporte',avisos:'avisos'}[route.screen] || null;
  }
  return Object.freeze({sectionOf,documents});
})();

// Datos de privacidad reales. Lo automático se marca como sondeo: no alarga la sesión.
const PrivacyData = (() => {
  const background = {'X-Chilito-Sondeo':'1'};
  async function send(path, options = {}) {
    try {
      const response = await ChilitoHTTP.request(path, options);
      if(response.http === 401) return {status:'unauthenticated'};
      if(response.http === 429) return {status:'limited'};
      if(![200,201].includes(response.http)) return {status:'unavailable'};
      return response.body;
    } catch { return {status:'unavailable'}; }
  }
  const post = (path, body, headers = {}) => send(path, {method:'POST', body, headers});
  return Object.freeze({
    cookies: () => send('/api/privacidad/cookies', {headers:background}),
    decide: statistics => post('/api/privacidad/cookies', {statistics}, background),
    section: section => post('/api/estadisticas/seccion', {section}, background),
    document: kind => send('/api/privacidad/documentos/'+encodeURIComponent(kind), {headers:background}),
    myData: () => post('/api/privacidad/mis-datos', {}),
    saveProfile: values => post('/api/cuenta/perfil', values),
    welcome: values => post('/api/cuenta/bienvenida', values),
    acceptLegal: documents => post('/api/legales/aceptar', {documents}),
    acceptances: () => send('/api/cuenta/aceptaciones'),
    // Borra la cuenta de inmediato con la contraseña. 200 = ya no existe. Una contraseña incorrecta es 400 y se distingue de un
    // fallo del servicio; 409 = cuenta con capacidades o con historial administrativo en registros ajenos.
    async requestDeletion(password) {
      try {
        const response = await ChilitoHTTP.request('/api/cuenta/eliminar', {method:'POST', body:{password}});
        if(response.http === 200 && response.body?.status === 'deleted') return {status:'deleted'};
        if(response.http === 409) return {status:response.body?.code === 'cuenta-con-historial-administrativo' ? 'admin-history' : 'admin-account'};
        return {status:{400:'wrong-password', 401:'unauthenticated', 429:'limited'}[response.http] || 'unavailable'};
      } catch { return {status:'unavailable'}; }
    }
  });
})();

// ── Panel ──
// Solo contratos de presentación; la autorización y el estado guardado son de Django.
const AppModel = (() => {
  const destinations = [
    {id:'huerto',label:'Mi huerto',icon:'leaf'},
    {id:'telemetria',label:'Panel técnico',icon:'activity'},
    {id:'mantenimiento',label:'Mantenimiento',icon:'tool'},
    {id:'soporte',label:'Soporte técnico',icon:'support'},
    {id:'avisos',label:'Avisos',icon:'bell'},
    {id:'cuenta',label:'Mi cuenta',icon:'user'}
  ];
  // Destinos de administración por grupo. Cada uno se ve solo con su capacidad; el servidor la vuelve a exigir en cada endpoint.
  const adminGroups = [
    {label:'Operación', items:[
      {id:'admin/flota',label:'Telemetría de flota',icon:'activity',capability:'ver_flota'},
      {id:'admin/soporte',label:'Consola remota',icon:'terminal',capability:'atender_soporte'},
      {id:'admin/mantenimientos',label:'Mantenimientos',icon:'tool',capability:'gestionar_mantenimientos'}]},
    {label:'Gestión', items:[
      {id:'admin/solicitudes',label:'Solicitudes del producto',icon:'inbox',capability:'atender_consultas'},
      {id:'admin/equipos',label:'Inventario de equipos',icon:'chip',capability:'gestionar_dispositivos'},
      {id:'admin/ventas',label:'Ventas',icon:'tag',capability:'gestionar_ventas'},
      {id:'admin/guias',label:'Guías de cuidado',icon:'book',capability:'gestionar_guias'}]},
    {label:'Legal', items:[
      {id:'admin/legales',label:'Textos legales',icon:'document',capability:'gestionar_legales'},
      {id:'admin/consentimientos',label:'Bitácora de consentimientos',icon:'clipboard',capability:'ver_consentimientos'}]},
    {label:'Super admin', items:[
      {id:'admin/administradores',label:'Administradores',icon:'users',capability:'gestionar_administradores'}]}
  ];
  const adminDestinations = adminGroups.flatMap(group=>group.items);
  const adminCapabilities = Object.fromEntries(adminDestinations.map(item=>[item.id,item.capability]));
  const allowedAdmin=(session=AuthService.session)=>adminDestinations.filter(item=>(session.capabilities||[]).includes(item.capability));
  const adminMenu=session=>adminGroups.map(group=>({label:group.label,items:group.items.filter(item=>(session?.capabilities||[]).includes(item.capability))})).filter(group=>group.items.length);
  // Los avisos de caso nuevo que guarda la base apuntan a «consola».
  const adminRedirects = {consola:'soporte'};
  // Gmail en otra pestaña con la cuenta de soporte seleccionada. Sin API ni credenciales: Gmail autentica por su cuenta.
  const supportMailUrl=()=>{const contact=ChilitoHTTP.configuration?.supportContact;
    return typeof contact==='string'&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)?'https://mail.google.com/mail/?authuser='+encodeURIComponent(contact):null;};
  const adminHome=session=>allowedAdmin(session)[0]?.id||'huerto';
  // Quien administra a los administradores o los textos legales nunca queda atrapado en «Aceptar textos»: sin el panel
  // nadie podría corregir ni publicar los textos. Se le recuerda que los tiene pendientes (aviso y campana).
  const legalGateExempt=session=>['gestionar_administradores','gestionar_legales'].some(cap=>(session?.capabilities||[]).includes(cap));
  // Panel de cada sesión completa. El servidor sigue decidiendo qué puede abrirse.
  const panelHome=session=>session?.role==='admin'?(session.profile?.mfaRequired?'#cuenta/seguridad':'#'+adminHome(session)):'#huerto';
  const alias=session=>{const value=session?.profile?.profile?.alias;return typeof value==='string'?value.trim():'';};
  const addressed=(name,text)=>name?`${name}, ${text[0].toLowerCase()}${text.slice(1)}`:text;
  // Sin afirmaciones sobre las plantas: no dependen de lecturas. Una por visita.
  const gardenPhrases=['Cada pequeño cuidado cuenta.','Cultivar es aprender un poco cada día.','Lo bueno de un huerto es que se cuida poco a poco.','Aquí tienes lo de tu huerto en un mismo lugar.','Un rato con tus plantas también es tiempo bien empleado.'];
  const gardenPhrase=gardenPhrases[Math.floor(Math.random()*gardenPhrases.length)];
  const gardenGreeting=name=>({title:name?`Hola, ${name}`:'Te damos la bienvenida a tu huerto',lead:name?'Te damos la bienvenida a tu huerto.':'',phrase:gardenPhrase});
  const text = value => typeof value === 'string' && value.trim().length > 0;
  const dateValid = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value));
  const idValid = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  const NOTICE_ORIGINS = ['dispositivo', 'ia', 'legal', 'soporte', 'vinculacion', 'sistema'];
  const NOTICE_SEVERITIES = ['informacion', 'advertencia', 'critico'];
  const NOTICE_FILTERS = ['todos', 'no_leidos', 'equipo', 'ia', 'soporte', 'legales'];
  const linkValid = value => value === null || typeof value === 'string' && /^#[A-Za-z0-9/_-]{1,119}$/.test(value);
  function notice(raw) {
    if(!raw || !idValid(raw.id) || !text(raw.title) || typeof raw.text !== 'string' || !NOTICE_ORIGINS.includes(raw.origin)
      || !NOTICE_SEVERITIES.includes(raw.severity) || !dateValid(raw.createdAt) || typeof raw.read !== 'boolean' || typeof raw.resolvable !== 'boolean'
      || !linkValid(raw.link) || raw.garden !== null && typeof raw.garden !== 'string' || raw.resolvedAt !== null && !dateValid(raw.resolvedAt)) return null;
    return {id:raw.id, origin:raw.origin, severity:raw.severity, title:raw.title, text:raw.text, garden:raw.garden, link:raw.link,
      createdAt:raw.createdAt, read:raw.read, resolvedAt:raw.resolvedAt, resolvable:raw.resolvable};
  }
  function notices(data = {}) {
    if(['loading', 'error', 'not-found'].includes(data.status)) return {status:data.status, items:[], page:1, total:0};
    if(data.status !== 'ready' || !Array.isArray(data.items)) return {status:'error', items:[], page:1, total:0};
    const items = data.items.map(notice);
    if(items.some(item => !item) || new Set(items.map(item => item.id)).size !== items.length) return {status:'error', items:[], page:1, total:0};
    return {status:items.length ? 'ready' : 'empty', items, page:Number.isInteger(data.page) ? data.page : 1, total:Number.isInteger(data.total) ? data.total : items.length};
  }
  return {
    destinations,supportMailUrl,adminDestinations,adminCapabilities,allowedAdmin,adminMenu,adminRedirects,adminHome,panelHome,legalGateExempt,alias,addressed,gardenGreeting,notices,notice,idValid,NOTICE_FILTERS,
    isPrivate(screen) { return screen === 'admin' || destinations.some(item=>item.id===screen); },
    profile(data={}) { return data.status==='ready' && text(data.email) && data.verified===true
      ? {email:data.email,verified:true,status:'ready',firstName:(data.profile||data).firstName||'',lastName:(data.profile||data).lastName||'',alias:(data.profile||data).alias||'',greeting:(data.profile||data).greeting||''} : {email:null,verified:null,status:'error'}; },
    date(value) { const d = new Date(value); return value && Number.isFinite(d.getTime()) ? d.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin registro'; },
    number(value) { return new Intl.NumberFormat('es-MX',{maximumFractionDigits:1}).format(value); }
  };
})();

// Datos guardados de cuenta, huerto y avisos, pedidos al mismo origen. Sin colecciones de respaldo.
const AppService = (() => {
  const background = {'X-Chilito-Sondeo':'1'};
  const query = values => { const params = new URLSearchParams(Object.entries(values).filter(([, value]) => value)); return params.size ? `?${params}` : ''; };
  // Cada acción: ruta, método y qué acepta como respuesta. El contador va como sondeo: no alarga la sesión.
  const actions = {
    profile:() => ({path:'/api/cuenta'}),
    notices:p => ({path:`/api/avisos${query({filtro:AppModel.NOTICE_FILTERS.includes(p.filter) ? p.filter : 'todos', page:p.page > 1 ? p.page : ''})}`}),
    notice:p => ({path:`/api/avisos/${p.id}`, needsId:true}),
    'mark-read':p => ({path:`/api/avisos/${p.id}/leido`, method:'POST', needsId:true}),
    'mark-resolved':p => ({path:`/api/avisos/${p.id}/resuelto`, method:'POST', needsId:true}),
    'mark-all-read':() => ({path:'/api/avisos/leer-todos', method:'POST'}),
    counter:() => ({path:'/api/avisos/contador', headers:background})
  };
  function adapt(action, body) {
    if(action === 'profile') return AppModel.profile(body);
    if(action === 'notices') return AppModel.notices(body);
    if(['notice', 'mark-read', 'mark-resolved'].includes(action)) {
      const item = AppModel.notice(body.notice);
      return item ? {status:action === 'notice' ? 'ready' : 'accepted', item} : {status:'error'};
    }
    if(action === 'counter') return Number.isInteger(body.unread) && body.unread >= 0 ? {status:'ready', unread:body.unread} : {status:'error'};
    return body.status === 'accepted' ? {status:'accepted', updated:body.updated ?? 0} : {status:'error'};
  }
  return Object.freeze({
    async request(action, payload = {}, {signal} = {}) {
      if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
      if (action === 'logout') return AuthService.logout({signal});
      const plan = actions[action]?.(payload);
      if(!plan) return {status:'unavailable'};
      if(plan.needsId && !AppModel.idValid(payload.id)) return {status:'not-found'};
      const response = await ChilitoHTTP.request(plan.path, {signal, method:plan.method, body:plan.method === 'POST' ? {} : undefined, headers:plan.headers});
      if(response.http === 401 || response.body?.code === 'verification-required') {
        AuthService.forgetSession();
        ChilitoHTTP.sessionExpired();
        return {status:'unauthenticated'};
      }
      if(response.http === 404) return {status:'not-found'};
      if(response.http === 429) return {status:'limited'};
      return response.http === 200 ? adapt(action, response.body) : {status:'error'};
    }
  });
})();

// ── Avisos ──
// Reglas del aviso flotante (3.5): tipos permitidos, ícono y permanencia. El error no se oculta solo (ms: 0).
const AvisoModel = Object.freeze({
  tipos:Object.freeze({
    exito:Object.freeze({icono:'check',rol:'status',ms:5000}),
    info:Object.freeze({icono:'info',rol:'status',ms:5000}),
    error:Object.freeze({icono:'alert',rol:'alert',ms:0})
  })
});

// ── Campos ──
// Reglas de los campos de entrada. Son las mismas que exige el servidor (backend/web/validacion.py), que no confía en el navegador.
// Cada campo declara la suya con data-campo; los límites salen de data-min/data-max (números) y de minlength/maxlength (texto).
const Campos = (() => {
  // Caracteres que se pueden escribir o pegar. Solo filtran los números, los importes, los nombres de persona y la MAC.
  const PERMITIDOS = Object.freeze({
    persona:/[\p{L}\p{M} '’-]/u, entero:/[0-9]/, digitos:/[0-9]/, dinero:/[0-9.]/, mac:/[0-9A-Fa-f:]/
  });
  const PERSONA = /^\p{L}[\p{L}\p{M} '’-]*$/u, COSA = /^[\p{L}\p{M}\p{N} -]+$/u, IMPORTE = /^[0-9]{1,8}(\.[0-9]{1,2})?$/;
  // Formatos fijos: el patrón completo y el mensaje.
  const FORMATOS = Object.freeze({
    identificador:[/^[A-Za-z0-9][A-Za-z0-9-]{3,31}$/, 'De 4 a 32 letras, números o guiones; empieza con letra o número.'],
    mac:[/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/, 'Escribe la MAC como AA:BB:CC:DD:EE:FF.'],
    firmware:[/^[A-Za-z0-9._-]{1,32}$/, 'Solo letras, números, punto, guion y guion bajo.'],
    version:[/^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$/, 'Escribe la versión como 1.2 o 1.2.3.']
  });
  // Caracteres de control (sin el salto de línea ni el tabulador de un texto de varias líneas).
  const CONTROL = /[\p{Cc}\p{Cf}]/gu, CONTROL_MULTILINEA = /(?![\n\t])[\p{Cc}\p{Cf}]/gu, HAY_CONTROL = /(?![\n\t])[\p{Cc}\p{Cf}]/u;
  // Espacios raros (duro, fino…) pasan a espacio normal y los separadores de línea a salto: el servidor solo admite esos.
  const espacios = (texto, multilinea) => texto.replace(/(?! )\p{Zs}/gu, ' ').replace(/[\p{Zl}\p{Zp}]/gu, multilinea ? '\n' : ' ');
  const filtra = regla => Boolean(PERMITIDOS[regla]);
  // Deja solo los caracteres permitidos (en los demás campos, quita los de control).
  function filtrar(regla, texto, {multilinea = false} = {}) {
    const original = String(texto ?? '');
    const permitido = PERMITIDOS[regla], normal = espacios(original, multilinea);
    let limpio = permitido ? Array.from(normal).filter(c => permitido.test(c)).join('') : normal.replace(multilinea ? CONTROL_MULTILINEA : CONTROL, '');
    if(regla === 'dinero') {
      const [entero, ...resto] = limpio.split('.');
      limpio = resto.length ? `${entero}.${resto.join('').slice(0, 2)}` : entero;
    }
    // «quitado»: se descartó algún carácter (merece aviso); «cambiado»: el texto ya no es el original (también por espacios raros).
    return {limpio, quitado:limpio !== normal, cambiado:limpio !== original};
  }
  // Mensaje de un carácter no permitido (al escribir o pegar).
  function bloqueo(regla, {min = 0, max = 999} = {}) {
    return {persona:'Solo letras', entero:`Solo números entre ${min} y ${max}`, digitos:'Solo números', dinero:'Solo números y un punto decimal',
      mac:'Solo dígitos hexadecimales y dos puntos'}[regla] || 'Se quitaron caracteres no permitidos';
  }
  const cuenta = texto => Array.from(texto).length;
  // ¿Cumple el valor completo su regla? null si sí; si no, el mensaje que va junto al campo.
  function validar(regla, valor, {min, max, minimo, maximo, requerido = false} = {}) {
    const texto = String(valor ?? '').trim();
    if(!texto) return requerido ? 'Este campo es obligatorio' : null;
    if(regla === 'persona') {
      const desde = minimo ?? 2, hasta = maximo ?? 60;
      if(!PERSONA.test(texto)) return 'Solo letras, espacios, apóstrofo y guion';
      return cuenta(texto) < desde || cuenta(texto) > hasta ? `Escribe entre ${desde} y ${hasta} letras` : null;
    }
    if(regla === 'cosa') {
      if(!COSA.test(texto)) return 'Solo letras, números, espacios y guion';
      return maximo && cuenta(texto) > maximo ? `Escribe como máximo ${maximo} caracteres` : null;
    }
    if(regla === 'entero') {
      const numero = Number(texto);
      return /^[0-9]+$/.test(texto) && numero >= (min ?? 0) && numero <= (max ?? 999) ? null : `Solo números entre ${min ?? 0} y ${max ?? 999}`;
    }
    if(regla === 'digitos') return /^[0-9]+$/.test(texto) && (!maximo || texto.length <= maximo) ? null : 'Solo números';
    if(regla === 'dinero') return IMPORTE.test(texto) ? null : 'Escribe un importe como 3500 o 3500.50';
    if(regla in FORMATOS) return FORMATOS[regla][0].test(texto) ? null : FORMATOS[regla][1];
    if(regla === 'libre') return HAY_CONTROL.test(texto) ? 'El texto tiene caracteres no permitidos' : maximo && cuenta(texto) > maximo ? `Escribe como máximo ${maximo} caracteres` : null;
    return null;
  }
  return Object.freeze({filtra, filtrar, bloqueo, validar, REGLAS:Object.freeze(['persona', 'cosa', 'entero', 'digitos', 'dinero', 'libre', ...Object.keys(FORMATOS)])});
})();

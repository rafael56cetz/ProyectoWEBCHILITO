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
    acceptLegal: documents => post('/api/legales/aceptar', {documents})
  });
})();

// ── Panel ──
// Solo contratos de presentación; la autorización y el estado guardado son de Django.
const AppModel = (() => {
  const destinations = [
    {id:'huerto',label:'Mi huerto',icon:'grid'},
    {id:'telemetria',label:'Panel técnico',icon:'activity'},
    {id:'mantenimiento',label:'Mantenimiento',icon:'tool'},
    {id:'soporte',label:'Soporte técnico',icon:'support'},
    {id:'avisos',label:'Avisos',icon:'bell'},
    {id:'cuenta',label:'Mi cuenta',icon:'user'}
  ];
  const adminDestinations = [
    {id:'admin/flota',label:'Telemetría de flota',icon:'grid'},
    {id:'admin/soporte',label:'Consola remota',icon:'support'},
    {id:'admin/mantenimientos',label:'Mantenimientos',icon:'tool'},
    {id:'admin/solicitudes',label:'Solicitudes del producto',icon:'inbox'},
    {id:'admin/guias',label:'Guías de cuidado',icon:'list'}
  ];
  const adminCapabilities={'admin/flota':'ver_flota','admin/soporte':'atender_soporte','admin/mantenimientos':'gestionar_mantenimientos','admin/solicitudes':'atender_consultas','admin/guias':'gestionar_guias'};
  const allowedAdmin=(session=AuthService.session)=>adminDestinations.filter(item=>(session.capabilities||[]).includes(adminCapabilities[item.id]));
  // Gmail en otra pestaña con la cuenta de soporte seleccionada. Sin API ni credenciales: Gmail autentica por su cuenta.
  const supportMailUrl=()=>{const contact=ChilitoHTTP.configuration?.supportContact;
    return typeof contact==='string'&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)?'https://mail.google.com/mail/?authuser='+encodeURIComponent(contact):null;};
  const adminHome=session=>allowedAdmin(session)[0]?.id||'huerto';
  // Panel de cada sesión completa. El servidor sigue decidiendo qué puede abrirse.
  const panelHome=session=>session?.role==='admin'?(session.profile?.mfaRequired?'#cuenta/seguridad':'#'+adminHome(session)):'#huerto';
  const alias=session=>{const value=session?.profile?.profile?.alias;return typeof value==='string'?value.trim():'';};
  const addressed=(name,text)=>name?`${name}, ${text[0].toLowerCase()}${text.slice(1)}`:text;
  // Sin afirmaciones sobre las plantas: no dependen de lecturas. Una por visita.
  const gardenPhrases=['Cada pequeño cuidado cuenta.','Cultivar es aprender un poco cada día.','Lo bueno de un huerto es que se cuida poco a poco.','Aquí tienes lo de tu huerto en un mismo lugar.','Un rato con tus plantas también es tiempo bien empleado.'];
  const gardenPhrase=gardenPhrases[Math.floor(Math.random()*gardenPhrases.length)];
  const gardenGreeting=name=>({title:name?`Hola, ${name}`:'Te damos la bienvenida a tu huerto',lead:name?'Te damos la bienvenida a tu huerto.':'',phrase:gardenPhrase});
  const states = {
    loading:['Consultando el huerto','Espera un momento.','clock'],
    waiting:['Huerto vinculado · Sin lecturas recibidas','Las mediciones aparecerán cuando el equipo empiece a enviarlas.','clock'],
    ready:['Datos disponibles','Consulta la fecha de cada lectura.','wifi'],
    stale:['Datos desactualizados','Las últimas lecturas se conservan como referencia; no describen necesariamente el estado actual.','clock'],
    offline:['Dispositivo sin conexión','No se están recibiendo nuevas lecturas. Se conserva la última información disponible.','off'],
    error:['No se pudo consultar el huerto','Inténtalo de nuevo para consultar su estado.','info'],
    invalid:['Hay una lectura inválida','Revisa el sensor indicado. Las otras lecturas mantienen su propia fecha y validez.','info'],
    unassigned:['Sin huerto asignado','Tu cuenta todavía no tiene un huerto asignado.','leaf']
  };
  const text = value => typeof value === 'string' && value.trim().length > 0;
  const dateValid = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value));
  const idValid = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  function validReading(raw, kind='humidity') {
    if(!raw || !['missing','valid','invalid'].includes(raw.quality) || raw.at !== null && !dateValid(raw.at)) return false;
    if(raw.quality === 'missing') return raw.value === null && raw.at === null;
    if(raw.quality === 'invalid') return raw.value === null;
    return typeof raw.value === 'number' && Number.isFinite(raw.value) && dateValid(raw.at)
      && (kind !== 'humidity' || raw.value >= 0 && raw.value <= 100);
  }
  function reading(raw, kind='humidity') {
    if (!validReading(raw,kind)) return {value:null,quality:'invalid',at:null};
    return {value:raw.value,quality:raw.quality,at:raw.at};
  }
  function garden(data={}) {
    let status = Object.hasOwn(states,data.status) ? data.status : 'error';
    if(!['loading','error','unassigned'].includes(status)) {
      const plants = data.plants;
      if(!text(data.name) || data.updatedAt !== null && !dateValid(data.updatedAt)
        || !Array.isArray(plants) || plants.length !== 3 || ![1,2,3].every(id=>plants.filter(p=>p?.id===id).length===1)
        || plants.some(p=>!text(p.name) || !validReading(p.reading))
        || !validReading(data.temperature,'temperature') || !validReading(data.humidity)
        || !data.tank || !['low','not-low','unknown'].includes(data.tank.state)
        || data.tank.at !== null && !dateValid(data.tank.at)
        || data.tank.state === 'unknown' && data.tank.at !== null
        || data.tank.state !== 'unknown' && !dateValid(data.tank.at)) status = 'error';
    }
    const usable = !['loading','error','unassigned'].includes(status);
    const missing = () => ({value:null,quality:'missing',at:null});
    return {
      status,name:usable ? data.name : 'Mi huerto',
      updatedAt:usable ? data.updatedAt : null,
      plants:[1,2,3].map(id=>{ const plant=usable ? data.plants.find(p=>p.id===id) : null;
        return {id,zoneId:plant?.zoneId || null,name:plant?.name || `Planta ${id}`,crop:plant?.crop || '',reading:plant ? reading(plant.reading) : missing()}; }),
      temperature:usable ? reading(data.temperature,'temperature') : missing(),humidity:usable ? reading(data.humidity) : missing(),
      tank:usable ? {state:data.tank.state,at:data.tank.at} : {state:'unknown',at:null}
    };
  }
  function notice(raw) {
    if(!raw || !idValid(raw.id) || !text(raw.title) || !text(raw.description) || !text(raw.zone)
      || typeof raw.recommendation !== 'string' || !dateValid(raw.createdAt)
      || !['high','medium','info'].includes(raw.importance) || !['active','resolved'].includes(raw.condition)
      || typeof raw.read !== 'boolean') return null;
    if(raw.condition === 'active' && raw.resolvedAt !== null) return null;
    if(raw.condition === 'resolved' && (!dateValid(raw.resolvedAt) || Date.parse(raw.resolvedAt) < Date.parse(raw.createdAt))) return null;
    return {id:raw.id,title:raw.title,description:raw.description,recommendation:raw.recommendation,
      zone:raw.zone,createdAt:raw.createdAt,resolvedAt:raw.resolvedAt,importance:raw.importance,condition:raw.condition,read:raw.read};
  }
  function notices(data={}) {
    if(['loading','error','unassigned','not-found'].includes(data.status)) return {status:data.status,items:[]};
    if(!['ready','empty'].includes(data.status) || !Array.isArray(data.items)) return {status:'error',items:[]};
    const items=data.items.map(notice);
    if(items.some(item=>!item) || new Set(items.map(item=>item.id)).size !== items.length
      || data.status==='empty' && items.length) return {status:'error',items:[]};
    return {status:items.length ? 'ready' : 'empty',items};
  }
  return {
    destinations,supportMailUrl,adminDestinations,adminCapabilities,allowedAdmin,adminHome,panelHome,alias,addressed,gardenGreeting,states,garden,notices,notice,reading,idValid,
    isPrivate(screen) { return screen === 'admin' || destinations.some(item=>item.id===screen); },
    filterNotices(items,filter) { return items.filter(item=>filter==='all' || item.condition===filter); },
    profile(data={}) { return data.status==='ready' && text(data.email) && data.verified===true
      ? {email:data.email,verified:true,status:'ready',firstName:(data.profile||data).firstName||'',lastName:(data.profile||data).lastName||'',alias:(data.profile||data).alias||'',greeting:(data.profile||data).greeting||''} : {email:null,verified:null,status:'error'}; },
    date(value) { const d = new Date(value); return value && Number.isFinite(d.getTime()) ? d.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin registro'; },
    number(value) { return new Intl.NumberFormat('es-MX',{maximumFractionDigits:1}).format(value); }
  };
})();

// Datos guardados de cuenta, huerto y avisos, pedidos al mismo origen. Sin colecciones de respaldo.
const AppService = Object.freeze({
  async request(action, payload={}, {signal}={}) {
    if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
    if (action === 'logout') return AuthService.logout({signal});
    const base='/api/huertos/actual';
    const path={profile:'/api/cuenta',notices:base+'/avisos'}[action];
    if(['notice','mark-read'].includes(action) && !AppModel.idValid(payload.id)) return {status:'not-found'};
    const endpoint=path || (action === 'notice' ? base+'/avisos/'+encodeURIComponent(payload.id)
      : action === 'mark-read' ? base+'/avisos/'+encodeURIComponent(payload.id)+'/lectura' : null);
    if(!endpoint) return {status:'unavailable'};
    const response=await ChilitoHTTP.request(endpoint,{signal,
      ...(action === 'mark-read' ? {method:'POST',body:{}} : {})});
    if(response.http === 401 || response.body?.code === 'verification-required') {
      AuthService.forgetSession();
      ChilitoHTTP.sessionExpired();
      return {status:'unauthenticated'};
    }
    if(response.http === 403 && response.body?.code === 'garden-unassigned') return {status:'unassigned'};
    if(response.http === 404) return {status:'not-found'};
    if(![200,201].includes(response.http)) return {status:'error'};
    if(action === 'profile') return AppModel.profile(response.body);
    if(action === 'notices') {
      const items=[...(response.body.items||[])];let page=response.body.page||1;
      while(response.body.total>items.length&&page<100) {
        const next=await ChilitoHTTP.request(endpoint+'?page='+(++page),{signal});
        if(next.http!==200||!Array.isArray(next.body.items))return {status:'error',items:[]};
        if(!next.body.items.length)break;items.push(...next.body.items);
      }
      return AppModel.notices({...response.body,items});
    }
    if(action === 'notice') {
      const item=AppModel.notice((response.body?.item || response.body?.notice));
      return response.body?.status === 'ready' && item?.id === payload.id ? {status:'ready',items:[item]} : {status:'error'};
    }
    if(action === 'mark-read') {
      const item=AppModel.notice((response.body?.item || response.body?.notice));
      return response.body?.status === 'accepted' && response.body.id === payload.id
        && response.body.read === true && item?.id === payload.id && item.read === true
        ? {status:'accepted',id:item.id,item} : {status:'error'};
    }
    return {status:'error'};
  }
});

// ── Avisos ──
// Reglas del aviso flotante (3.5): tipos permitidos, ícono y permanencia. El error no se oculta solo (ms: 0).
const AvisoModel = Object.freeze({
  tipos:Object.freeze({
    exito:Object.freeze({icono:'check',rol:'status',ms:5000}),
    info:Object.freeze({icono:'info',rol:'status',ms:5000}),
    error:Object.freeze({icono:'alert',rol:'alert',ms:0})
  })
});

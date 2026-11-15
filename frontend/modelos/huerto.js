// MODELO · Huerto: huertos y plantas de la persona usuaria, panel técnico y soporte, guías de cuidado y mantenimientos.
// Define: GardenService, GardenModel, UserGardenService, CareGuideService, MaintenanceService, MaintenanceDates.

// ── Huerto ──
// Huertos, plantas, órdenes y vinculación del equipo. El servidor decide; cada llamada devuelve su cuerpo o {status:'error', code}.
const GardenService = (() => {
  const base = '/api/huertos';
  const background = {'X-Chilito-Sondeo':'1'};
  const validId = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  async function call(path, {method = 'GET', body, signal, headers} = {}) {
    try {
      const response = await ChilitoHTTP.request(path, {method, body, signal, headers});
      if(response.http === 401) { ChilitoHTTP.sessionExpired(); return {status:'error', code:'unauthenticated'}; }
      return response.http === 200 ? response.body : {status:'error', code:response.body?.code || 'unavailable'};
    } catch { return {status:'error', code:'network'}; }
  }
  // El identificador entra en la ruta: solo dígitos.
  const garden = (id, rest = '') => validId(id) ? `${base}/${id}${rest}` : null;
  const get = (path, options) => path ? call(path, options) : Promise.resolve({status:'error', code:'invalid-input'});
  const post = (path, body = {}, options) => path ? call(path, {method:'POST', body, ...options}) : Promise.resolve({status:'error', code:'invalid-input'});
  return Object.freeze({
    validId,
    list: signal => call(base, {signal}),
    detail: (id, signal) => get(garden(id), {signal}),
    create: name => post(base, name ? {name} : {}),
    rename: (id, name) => post(garden(id, '/renombrar'), {name}),
    archive: id => post(garden(id, '/archivar')),
    summaries: (id, page) => get(garden(id, `/ia?page=${Number(page) || 1}`)),
    generateCode: id => post(garden(id, '/codigo')),
    linkState: (id, signal) => get(garden(id, '/vinculacion'), {signal, headers:background}),
    unlink: id => post(garden(id, '/desvincular')),
    plant: (id, number, range = '24h') => get(garden(id, `/plantas/${Number(number)}?rango=${encodeURIComponent(range)}`)),
    editPlant: (id, number, values) => post(garden(id, `/plantas/${Number(number)}`), values),
    order: (id, values) => post(garden(id, '/comandos'), values),
    orderState: (orderId, signal) => get(typeof orderId === 'string' && /^[0-9a-f-]{36}$/.test(orderId) ? `/api/comandos/${orderId}` : null, {signal, headers:background}),
    care: (id, values) => post(garden(id, '/cuidados'), values)
  });
})();

// Cálculos de presentación sobre lo que envía el servidor. Sin lectura, el valor es null: nunca un cero ni una fecha inventada.
const GardenModel = (() => {
  const RECENT_READING_MS = 15 * 60 * 1000;
  const FINAL_ORDER_STATES = ['confirmado', 'fallido', 'expirado'];
  const WATERING_SECONDS = [5, 8, 10, 15, 20];
  const STAGES = ['sin_sembrar', 'germinacion', 'plantula', 'crecimiento', 'floracion', 'fructificacion'];
  const RANGES = ['1h', '24h', '7d', '30d'];
  let chosen = null;
  function ago(value, now = Date.now()) {
    const minutes = Math.floor((now - Date.parse(value)) / 60000);
    if(!Number.isFinite(minutes)) return null;
    if(minutes < 1) return 'hace menos de 1 min';
    if(minutes < 60) return `hace ${minutes} min`;
    if(minutes < 1440) return `hace ${Math.floor(minutes / 60)} h`;
    return `hace ${Math.floor(minutes / 1440)} días`;
  }
  // Línea de estado 3.2: tono y texto salen de la conexión del equipo y de su última lectura.
  function connection(device, now = Date.now()) {
    if(!device) return null;
    const firmware = device.firmware ? ` · Firmware ${device.firmware}` : '';
    if(device.connection === 'nunca') return {tone:'gris', text:'Equipo vinculado · Esperando su primera conexión'};
    if(device.connection === 'desconectado') return {tone:'rojo', text:`Desconectado desde ${AppModel.date(device.lastConnectionAt)}`};
    const recent = device.lastReadingAt && now - Date.parse(device.lastReadingAt) < RECENT_READING_MS;
    return recent ? {tone:'verde', text:`En línea · Última lectura ${ago(device.lastReadingAt, now)}${firmware}`}
      : {tone:'ambar', text:'Conectado, sin lecturas recientes'};
  }
  // Promedio de las plantas que tienen lectura; sin ninguna, null.
  function averageMoisture(plants) {
    const values = plants.map(plant => plant.moisture).filter(Number.isFinite);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  }
  function pick(gardens, requested) {
    return gardens.find(item => item.id === requested) || gardens.find(item => item.id === chosen) || gardens[0] || null;
  }
  const remember = id => { chosen = id; };
  const reset = () => { chosen = null; };
  // El código se escribe en el equipo como XXXX-XXXX; aquí solo se agrupa para mostrarlo.
  const groupCode = code => typeof code === 'string' ? code.replace(/^(.{4})(.{4})$/, '$1-$2') : '';
  const remainingSeconds = (expiresAt, now = Date.now()) => Math.max(0, Math.floor((Date.parse(expiresAt) - now) / 1000));
  const clock = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  return Object.freeze({FINAL_ORDER_STATES, WATERING_SECONDS, STAGES, RANGES, ago, connection, averageMoisture, pick, remember, reset, groupCode, remainingSeconds, clock});
})();

// ── Huerto usuario ──
// Operaciones de la persona usuaria guardadas en el servidor (mismo origen). Los datos en memoria solo muestran respuestas del servidor.
const UserGardenService = (() => {
  const base='/api/huertos/actual';
  const tasks=Object.freeze({refill:'Recarga del depósito',substrate:'Revisión de sustrato y perlita',germination:'Germinación externa',harvest:'Cosecha',inspection:'Inspección visual de conexiones'});
  const incidents=Object.freeze({pump:'La bomba no responde',humidity:'Lectura de humedad inconsistente',lamp:'La lámpara no enciende',connection:'Conexión inestable',other:'Otro problema de hardware'});
  let active=null,reports=[];
  const failure=response=>response.http===401?'unauthenticated':response.http===403?'forbidden':response.http===429?'limited':'error';
  async function read(path,signal) {
    const response=await ChilitoHTTP.request(path,{signal});
    if(response.http!==200) {
      if(response.http===401)ChilitoHTTP.sessionExpired();
      throw new Error(response.body?.code||'unavailable');
    }
    const body=response.body;
    if(Array.isArray(body.items)) {
      // Todo el historial se pide por páginas con límite; nunca se inventan registros.
      const items=[...body.items];let page=body.page||1;
      while(body.total>items.length && page<100) {
        const next=await ChilitoHTTP.request(path+(path.includes('?')?'&':'?')+'page='+(++page),{signal});
        if(next.http!==200||!Array.isArray(next.body.items))throw new Error('unavailable');
        if(!next.body.items.length)break;
        items.push(...next.body.items);
      }
      return {...body,items};
    }
    return body;
  }
  async function write(path,body={},signal) {
    try {
      const response=await ChilitoHTTP.request(path,{method:'POST',body,signal});
      if(response.http===401)ChilitoHTTP.sessionExpired();
      return [200,201].includes(response.http)&&response.body.status==='accepted'?response.body:{status:failure(response)};
    }catch{return {status:'error'};}
  }
  const empty=range=>({range,soil:{adc:null,moisture:{value:null,quality:'missing',at:null}},connection:{wifi:null,mqtt:null},history:{soil:[],temperature:[],humidity:[]},maintenance:[],commands:[],permission:null,permissionState:'closed',supportAvailable:false,reports:[],lampRequest:null});
  function permission() {
    return active&&active.expiresAt>Date.now()?{...active}:null;
  }
  return {
    tasks,incidents,get supportAvailable(){return true;},permission,
    async load(range='1h',{signal}={}) {
      const raw=await ChilitoHTTP.request(base,{signal});
      if(raw.http===401)ChilitoHTTP.sessionExpired();
      if(raw.http!==200) {
        const status=raw.body?.code==='garden-unassigned'?'unassigned':'error';
        if(status==='error')return {garden:AppModel.garden({status})};
        // Sin huerto se conserva la estructura completa y vacía: ninguna lectura ni registro inventado.
        reports=[];active=null;
        return {...empty(range),garden:AppModel.garden({status})};
      }
      const g=raw.body.garden||raw.body;
      const [maintenance,commands,support]=await Promise.all([read(base+'/mantenimiento',signal),read(base+'/solicitudes',signal),read('/api/soporte',signal)]);
      reports=support.items||[];
      const latest=reports.find(r=>r.permissionState==='active'&&r.expiresAt>Date.now());
      if(!latest)active=null;
      else active={ticket:latest.id,folio:latest.folio,incident:incidents[latest.incident]||latest.incident,createdAt:Date.parse(latest.createdAt),expiresAt:latest.expiresAt,token:active?.ticket===latest.id?active.token:null};
      const records=(maintenance.items||[]).map(r=>({id:r.id,task:r.type,label:tasks[r.type]||r.type,at:r.at}));
      const orders=(commands.items||[]).map(r=>({id:r.id,at:r.at,actuator:r.type==='water'?'Bomba de riego':'Lámpara',action:{water:'Solicitud de riego puntual','lamp-off':'Solicitud de apagado de lámpara','lamp-auto':'Restaurar control de lámpara'}[r.type],origin:'Usuario',status:'Sin confirmación'}));
      const lamp=(commands.items||[]).find(r=>r.type==='lamp-off'||r.type==='lamp-auto');
      return {garden:AppModel.garden(g),range,soil:{adc:null,moisture:{value:null,quality:'missing',at:null}},connection:{wifi:null,mqtt:null},history:{soil:[],temperature:[],humidity:[]},maintenance:records,commands:orders,permission:permission(),permissionState:latest?'active':reports[0]?.permissionState||'closed',supportAvailable:true,reports:structuredClone(reports),lampRequest:lamp?.type||null};
    },
    async recordTask(task,{signal}={}) {
      if(!Object.hasOwn(tasks,task))return {status:'invalid'};
      const result=await write(base+'/mantenimiento',{type:task},signal);
      return {...result,label:tasks[task]};
    },
    async command(type,snapshot,{signal}={}) {
      if(!['water','lamp-off','lamp-auto'].includes(type))return {status:'invalid'};
      return write(base+'/solicitudes',{type},signal);
    },
    async issuePermission(incident,consent,{signal}={}) {
      if(consent!==true||!Object.hasOwn(incidents,incident))return {status:'invalid'};
      const result=await write('/api/soporte',{incident,consent:true},signal);
      if(result.status!=='accepted')return result;
      const p=result.permission;
      if(!p||!Number.isFinite(p.expiresAt)||typeof p.ticket!=='string'||(p.token!==null&&!/^[A-Za-z0-9_-]{43}$/.test(p.token)))return {status:'error'};
      active={...p,incident:incidents[incident]};
      return {status:'accepted',tokenAvailable:typeof p.token==='string'};
    },
    async revokePermission({signal}={}) {
      const p=permission();if(!p)return {status:'not-found'};
      const result=await write('/api/soporte/'+encodeURIComponent(p.ticket)+'/revocar',{},signal);
      if(result.status==='accepted')active=null;
      return result;
    },
    reset(){active=null;reports=[];},
    // Correo a soporte con destinatario y asunto preparados. El token nunca va en la URL: se pega a mano.
    supportMail(folio){
      const contact=ChilitoHTTP.configuration?.supportContact;
      if(typeof contact!=='string'||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)||!/^CS-[0-9A-F]{8}$/.test(folio||''))return null;
      const body=`Folio: ${folio}\n\nPega aquí tu token de soporte:\n\n\nNunca incluyas tu contraseña ni tus códigos de acceso.`;
      return {address:contact,href:`mailto:${contact}?subject=${encodeURIComponent('[El Chilito] Caso de soporte '+folio)}&body=${encodeURIComponent(body)}`};
    },
  };
})();

// ── Guias ──
// Guías de cuidado: transporte y adaptación. El contenido vive en PostgreSQL; aquí no hay otro catálogo.
// Validar, autorizar y publicar lo decide el servidor.
const CareGuideService = (() => {
  // Identificador estable de la ficha a la que apunta «Ver guía de cuidado». No es contenido.
  const SUBSTRATE_KEY = 'sustrato-perlita';
  const GERMINATION_KEY = 'germinacion-inicio';
  const KEY = /^[a-z0-9]+(-[a-z0-9]+)*$/;
  const LIMITS = Object.freeze({question:200, answer:4000, sourceName:120, sourceUrl:500, order:9999});
  const stateLabels = Object.freeze({borrador:'Borrador', publicada:'Publicada', retirada:'Retirada'});
  const statusOf = response => response.http===401?'unauthenticated'
    :response.body?.code==='stale-record'?'stale'
    :response.body?.code==='mfa-required'?'mfa'
    :response.http===403?'forbidden':response.http===429?'limited':response.http===400?'invalid':response.http===409?'conflict':'error';
  async function call(path, options = {}) {
    try {
      const response = await ChilitoHTTP.request(path, options);
      if(response.http===401) ChilitoHTTP.sessionExpired();
      return response.http===200 ? response.body : {status:statusOf(response)};
    } catch { return {status:'network'}; }
  }
  // Segunda comprobación del enlace antes de convertirlo en href: solo http y https.
  function safeUrl(value) {
    if(typeof value !== 'string') return null;
    try { return ['http:','https:'].includes(new URL(value).protocol) ? value : null; } catch { return null; }
  }
  const paragraphs = text => String(text ?? '').split(/\n\s*\n/).map(part => part.trim()).filter(Boolean);
  const text = value => typeof value === 'string' ? value : '';
  function adaptPublished(raw) {
    if(!raw || !KEY.test(raw.key) || !text(raw.question) || !text(raw.answer)) return null;
    const name = text(raw.source?.name);
    return {key:raw.key, question:raw.question, paragraphs:paragraphs(raw.answer), source:name ? {name, url:safeUrl(raw.source.url)} : null};
  }
  function dateText(value) {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin fecha';
  }
  // Aviso antes de enviar. El servidor vuelve a validar todo.
  function check(values) {
    if(!values.question.trim()) return {field:'question', message:'Escribe la pregunta.'};
    if(!values.answer.trim()) return {field:'answer', message:'Escribe la respuesta.'};
    if(!/^[0-9]{1,4}$/.test(values.order) || Number(values.order) < 1) return {field:'order', message:'El orden debe ser un número entero de 1 a 9999.'};
    const url = values.sourceUrl.trim();
    if(url && !/^https?:\/\//.test(url)) return {field:'sourceUrl', message:'El enlace debe empezar por http:// o https://.'};
    if(url && !safeUrl(url)) return {field:'sourceUrl', message:'Revisa el enlace de la fuente.'};
    if(url && !values.sourceName.trim()) return {field:'sourceName', message:'Indica el nombre de la fuente del enlace.'};
    return null;
  }
  const payload = values => ({question:values.question, answer:values.answer, order:Number(values.order), sourceName:values.sourceName, sourceUrl:values.sourceUrl});
  const editorTexts = Object.freeze({
    nueva:{title:'Nueva ficha', save:'Guardar como borrador', hint:'Se guardará como borrador. Nadie la verá hasta que pulses «Publicar» en la lista.'},
    borrador:{title:'Editar borrador', save:'Guardar como borrador', hint:'Sigue siendo un borrador. Nadie la verá hasta que pulses «Publicar» en la lista.'},
    publicada:{title:'Editar ficha publicada', save:'Guardar y actualizar lo publicado', hint:'Esta ficha está publicada: al guardar, los cambios serán visibles de inmediato para las personas usuarias.'},
    retirada:{title:'Editar ficha retirada', save:'Guardar (sigue retirada)', hint:'Guardar no la publica. Para mostrarla de nuevo, usa «Volver a publicar» en la lista.'}});
  const id = value => encodeURIComponent(value);
  return Object.freeze({
    SUBSTRATE_KEY, GERMINATION_KEY, LIMITS, stateLabels, editorTexts, safeUrl, paragraphs, dateText, check,
    async published({signal} = {}) {
      const result = await call('/api/guias', {signal});
      if(result.status !== 'ready' || !Array.isArray(result.guides)) return {status:result.status === 'ready' ? 'error' : result.status};
      return {status:'ready', items:result.guides.map(adaptPublished).filter(Boolean)};
    },
    panel: () => call('/api/admin/guias'),
    create: values => call('/api/admin/guias', {method:'POST', body:payload(values)}),
    update: (guideId, version, values) => call('/api/admin/guias/'+id(guideId)+'/editar', {method:'POST', body:{...payload(values), version}}),
    publish: (guideId, version) => call('/api/admin/guias/'+id(guideId)+'/publicar', {method:'POST', body:{version}}),
    withdraw: (guideId, version) => call('/api/admin/guias/'+id(guideId)+'/retirar', {method:'POST', body:{version}})
  });
})();

// ── Mantenimientos ──
// Solo respuestas autorizadas por Django. El estado vigente lo calcula el servidor.
const MaintenanceService = (() => {
  const tasks = UserGardenService.tasks;
  const base = '/api/admin/mantenimientos';
  async function send(path, options = {}) {
    try {
      const response = await ChilitoHTTP.request(path, options);
      if(response.http === 401) { ChilitoHTTP.sessionExpired(); return {status:'unauthenticated'}; }
      if(response.http === 409) return {status:response.body?.code === 'stale-record' ? 'stale' : 'conflict'};
      if(response.http === 403) return {status:'forbidden'};
      if(response.http === 429) return {status:'limited'};
      if(response.http === 400) return {status:'invalid'};
      return [200,201].includes(response.http) ? response.body : {status:'error'};
    } catch { return {status:'error'}; }
  }
  const query = filters => {
    const params = new URLSearchParams(Object.entries(filters).filter(([,value]) => value));
    return params.size ? '?'+params : '';
  };
  return Object.freeze({
    tasks,
    list: (filters = {}) => send(base+query(filters)),
    detail: id => send(base+'/'+encodeURIComponent(id)),
    create: (gardenId,task) => send(base,{method:'POST',body:{gardenId,task}}),
    correct: (id,task,reason,revision) => send(base+'/'+encodeURIComponent(id)+'/corregir',{method:'POST',body:{task,reason,revision}}),
    void: (id,reason,revision) => send(base+'/'+encodeURIComponent(id)+'/anular',{method:'POST',body:{reason,revision}})
  });
})();

// Fechas civiles: UTC solo para aritmética de calendario, sin convertir la fecha escrita.
// Hoy se obtiene del reloj local; las cadenas enviadas nunca usan toISOString().
const MaintenanceDates = (() => {
  function make(year, month, day) {
    const date = new Date(0);
    date.setUTCHours(12,0,0,0);
    date.setUTCFullYear(year,month,day);
    return date;
  }
  const format = date => `${String(date.getUTCFullYear()).padStart(4,'0')}-${String(date.getUTCMonth()+1).padStart(2,'0')}-${String(date.getUTCDate()).padStart(2,'0')}`;
  function parse(value) {
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const [year,month,day] = value.split('-').map(Number);
    if(year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31) return null;
    const date = make(year,month-1,day);
    return format(date) === value ? date : null;
  }
  function shift(date, days = 0, months = 0) {
    const target = make(date.getUTCFullYear(),date.getUTCMonth()+months,1);
    const last = make(target.getUTCFullYear(),target.getUTCMonth()+1,0).getUTCDate();
    target.setUTCDate(Math.min(date.getUTCDate(),last)+days);
    return target.getUTCFullYear() >= 1 && target.getUTCFullYear() <= 9999 ? target : date;
  }
  function weeks(year, month) {
    const offset = (make(year,month,1).getUTCDay()+6)%7;
    const count = make(year,month+1,0).getUTCDate();
    return Array.from({length:Math.ceil((offset+count)/7)},(_,week) =>
      Array.from({length:7},(_,weekday) => {
        const day = week*7+weekday-offset+1;
        return day > 0 && day <= count ? {value:format(make(year,month,day)),day} : null;
      }));
  }
  function today() {
    const local = new Date();
    return make(local.getFullYear(),local.getMonth(),local.getDate());
  }
  return Object.freeze({parse,format,make,shift,weeks,today});
})();

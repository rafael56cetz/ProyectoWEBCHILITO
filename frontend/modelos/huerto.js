// MODELO · Huerto: huertos y plantas de la persona usuaria, panel técnico y soporte, guías de cuidado y mantenimientos.
// Define: GardenService, GardenModel, CareGuideService, MaintenanceService, MaintenanceDates.

// ── Huerto ──
// Huertos, plantas, órdenes y vinculación del equipo. El servidor decide; cada llamada devuelve su cuerpo o {status:'error', code}.
const GardenService = (() => {
  const base = '/api/huertos';
  const background = {'X-Chilito-Sondeo':'1'};
  const validId = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  const validUuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
  const query = values => { const params = new URLSearchParams(Object.entries(values).filter(([, value]) => value !== '' && value != null)); return params.size ? `?${params}` : ''; };
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
    orderState: (orderId, signal) => get(validUuid(orderId) ? `/api/comandos/${orderId}` : null, {signal, headers:background}),
    care: (id, values) => post(garden(id, '/cuidados'), values),
    telemetry: (id, range, signal) => get(garden(id, `/telemetria${query({rango:range})}`), {signal}),
    log: (id, type, page) => get(garden(id, `/bitacora${query({tipo:type, page:Number(page) || 1})}`)),
    cares: (id, filters, page) => get(garden(id, `/cuidados${query({...filters, page:Number(page) || 1})}`)),
    tank: (id, signal) => get(garden(id, '/deposito'), {signal}),
    support: (id, {signal, quiet = false} = {}) => get(garden(id, '/soporte'), {signal, headers:quiet ? background : undefined}),
    openCase: (id, values) => post(garden(id, '/soporte'), values),
    revokeCase: caseId => post(validUuid(caseId) ? `/api/soporte/${caseId}/revocar` : null),
    cancelCase: caseId => post(validUuid(caseId) ? `/api/soporte/${caseId}/cancelar` : null),
    diagnostic: (diagnosticId, signal) => get(validUuid(diagnosticId) ? `/api/autodiagnosticos/${diagnosticId}` : null, {signal, headers:background})
  });
})();

// Cálculos de presentación sobre lo que envía el servidor. Sin lectura, el valor es null: nunca un cero ni una fecha inventada.
const GardenModel = (() => {
  const RECENT_READING_MS = 15 * 60 * 1000;
  const FINAL_ORDER_STATES = ['confirmado', 'fallido', 'expirado'];
  const WATERING_SECONDS = [5, 8, 10, 15, 20];
  const STAGES = ['sin_sembrar', 'germinacion', 'plantula', 'crecimiento', 'floracion', 'fructificacion'];
  const RANGES = ['1h', '24h', '7d', '30d'];
  const INCIDENTS = Object.freeze({bomba:'La bomba no responde', humedad:'Lectura de humedad inconsistente', lampara:'La lámpara no enciende',
    conexion:'Conexión inestable', otro:'Otro problema'});
  const CARE_NEEDS_PLANT = ['sustrato', 'germinacion', 'cosecha'];
  const CARE_WINDOW_DAYS = 7;
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
  // «Cuándo» del cuidado: vacío o hoy es ahora (lo fija el servidor); otro día, a mediodía. Hasta 7 días atrás y nunca futuro.
  function careMoment(value) {
    if(!value) return {valid:true, at:null};
    const day = MaintenanceDates.parse(value), today = MaintenanceDates.today();
    if(!day || day > today || day < MaintenanceDates.shift(today, -CARE_WINDOW_DAYS)) return {valid:false, at:null};
    if(value === MaintenanceDates.format(today)) return {valid:true, at:null};
    const [year, month, date] = value.split('-').map(Number);
    return {valid:true, at:new Date(year, month - 1, date, 12).toISOString()};
  }
  const problems = checks => checks.filter(check => ['falla', 'sin_respuesta'].includes(check.result)).length;
  // Tiempo que queda de una autorización: «18 h 42 min».
  function lapse(until, now = Date.now()) {
    const minutes = Math.max(0, Math.floor((Date.parse(until) - now) / 60000));
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  }
  const remainingSeconds = (expiresAt, now = Date.now()) => Math.max(0, Math.floor((Date.parse(expiresAt) - now) / 1000));
  const clock = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

  // ── Depósito ── Fechas en hora de Mérida y duraciones en días y horas. Las reglas las decide el servidor (tank.canRefill).
  const MERIDA = 'America/Merida';
  const plainSpaces = text => String(text).replace(/[\u00a0\u202f]/g, ' ');
  const meridaKey = value => new Date(value).toLocaleDateString('en-CA', {timeZone:MERIDA});
  const dayOffset = (value, now) => Math.round((Date.parse(meridaKey(value)) - Date.parse(meridaKey(now))) / 864e5);
  const meridaTime = value => plainSpaces(new Date(value).toLocaleTimeString('es-MX', {timeZone:MERIDA, hour:'2-digit', minute:'2-digit', hourCycle:'h23'}));
  // «hoy a las 14:05», «ayer a las 9:30», «mañana a las 8:00» o «el 18 nov a las 14:05».
  function meridaWhen(value, now = Date.now()) {
    if(!value || !Number.isFinite(Date.parse(value))) return '';
    const offset = dayOffset(value, now);
    const day = {0:'hoy', [-1]:'ayer', 1:'mañana'}[offset]
      ?? `el ${plainSpaces(new Date(value).toLocaleDateString('es-MX', {timeZone:MERIDA, day:'numeric', month:'short'})).replace(/\./g, '')}`;
    return `${day} a las ${meridaTime(value)}`;
  }
  // «jueves 20 de noviembre».
  const meridaDay = value => plainSpaces(new Date(value).toLocaleDateString('es-MX', {timeZone:MERIDA, weekday:'long', day:'numeric', month:'long'})).replace(',', '');
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  function humanDuration(seconds) {
    if(!Number.isFinite(seconds) || seconds < 3600) return 'menos de 1 hora';
    const hours = Math.floor(seconds / 3600), days = Math.floor(hours / 24), rest = hours % 24;
    if(!days) return plural(hours, 'hora', 'horas');
    return rest ? `${plural(days, 'día', 'días')} y ${plural(rest, 'hora', 'horas')}` : plural(days, 'día', 'días');
  }
  const REFILL_AUTHOR = refill => refill.origin === 'equipo' ? 'detectada por tu equipo' : refill.byOwner ? 'registrada por ti' : 'registrada por soporte';
  // ¿Se puede registrar una recarga a mano? Si no, el motivo que se muestra junto al botón.
  function refillState(tank, now = Date.now()) {
    if(!tank || tank.canRefill) return {allowed:true, reason:''};
    const last = tank.lastRefill ? meridaWhen(tank.lastRefill.at, now) : '';
    if(tank.refillBlock === 'espera') {
      const next = meridaWhen(tank.nextRefillAt, now);
      return {allowed:false, reason:`Podrás registrar otra recarga ${next.startsWith('hoy ') ? next.slice(4) : next}.`};
    }
    if(tank.refillBlock === 'repetida') return {allowed:false, reason:`Ya registraste esta recarga (${last}): tu equipo la confirmará cuando el flotador detecte agua.`};
    return {allowed:false, reason:last ? `Tu depósito tiene agua desde tu última recarga (${last}).` : 'Tu depósito tiene agua: podrás registrar una recarga cuando el flotador marque nivel bajo.'};
  }
  // Textos de la tarjeta Depósito: estado, desde cuándo, última recarga y duración (o frecuencia sin equipo).
  function tankSummary(tank, now = Date.now()) {
    const status = tank?.hasWater === true ? 'Con agua' : tank?.hasWater === false ? 'Nivel bajo' : 'Sin lectura';
    const lowSince = tank?.hasWater === false && tank.lowSince ? meridaWhen(tank.lowSince, now) : '';
    const lines = [];
    if(!tank) return {status, tone:'', lowSince, lines};
    lines.push(tank.lastRefill ? `Última recarga: ${meridaWhen(tank.lastRefill.at, now)} (${REFILL_AUTHOR(tank.lastRefill)})` : 'Aún no hay recargas registradas.');
    if(tank.hasDevice) {
      if(Number.isFinite(tank.averageSeconds)) {
        lines.push(`Tu depósito dura en promedio ${humanDuration(tank.averageSeconds)}.`);
        if(tank.estimatedLowAt) lines.push(Date.parse(tank.estimatedLowAt) > now
          ? `Al ritmo actual, necesitará agua alrededor del ${meridaDay(tank.estimatedLowAt)}.` : 'Al ritmo actual, ya podría necesitar agua.');
      } else lines.push('Te diremos cuánto dura tu depósito cuando se termine esta carga.');
    } else if(Number.isFinite(tank.refillEverySeconds)) {
      lines.push(`Sueles rellenar cada ${plural(Math.max(1, Math.round(tank.refillEverySeconds / 86400)), 'día', 'días')}.`);
    }
    return {status, tone:tank.hasWater === true ? ' is-ok' : tank.hasWater === false ? ' is-low' : '', lowSince, lines};
  }
  return Object.freeze({FINAL_ORDER_STATES, WATERING_SECONDS, STAGES, RANGES, INCIDENTS, CARE_NEEDS_PLANT, ago, connection, averageMoisture,
    pick, remember, reset, groupCode, careMoment, problems, lapse, remainingSeconds, clock,
    meridaWhen, meridaDay, humanDuration, refillState, tankSummary});
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
// Cuidados de todos los huertos para quien tiene `gestionar_mantenimientos`. El estado vigente y el número de revisión los calcula el servidor.
const MaintenanceService = (() => {
  const base = '/api/admin/mantenimientos';
  const record = (id, rest = '') => AdminHTTP.validUuid(id) ? `${base}/${id}${rest}` : null;
  return Object.freeze({
    list: (filters, page) => AdminHTTP.call(base + AdminHTTP.query({busqueda:filters.busqueda, huerto:filters.huerto, planta:filters.planta, tipo:filters.tipo,
      estado:filters.estado, desde:filters.since, hasta:filters.until, page})),
    detail: id => AdminHTTP.call(record(id)),
    create: values => AdminHTTP.call(base, {method:'POST', body:values}),
    correct: (id, values) => AdminHTTP.call(record(id, '/corregir'), {method:'POST', body:values}),
    void: (id, values) => AdminHTTP.call(record(id, '/anular'), {method:'POST', body:values}),
    // Día escrito por quien registra → mediodía de Mérida (UTC−6 todo el año). Hoy o vacío significa «ahora»: el mediodía aún no llegó.
    moment: (day, today) => !day || day === today ? null : `${day}T12:00:00-06:00`
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

// MODELO · Administración: paneles de operación, buzón de consultas, ventas, administradores, textos legales y consentimientos.
// Define: FleetService, ConsoleService, InquiryService, AdminHTTP, SalesModel, SalesService, AdminAccessService, LegalAdminService, ConsentService.

// ── Administracion ──
// Flota y consola remota. Solo transportan datos: la capacidad, la propiedad del caso y la autorización las decide el servidor en cada llamada.
const FleetService = Object.freeze({
  load: (filters, page) => AdminHTTP.call('/api/admin/flota' + AdminHTTP.query({...filters, page}))
});

const ConsoleService = (() => {
  const cases = '/api/admin/soporte', sessions = '/api/admin/sesiones';
  const results = Object.freeze({solucionado:'Problema solucionado', sin_falla:'Sin falla detectada', sin_respuesta:'Sin respuesta de la persona usuaria', otro:'Otro (explicado en la nota)'});
  const bombSeconds = Object.freeze({min:1, max:5});
  const path = (root, id, rest = '') => AdminHTTP.validUuid(id) ? `${root}/${id}${rest}` : null;
  const post = (url, body = {}) => AdminHTTP.call(url, {method:'POST', body});
  return Object.freeze({
    results, bombSeconds,
    inbox: (state, page) => AdminHTTP.call(cases + AdminHTTP.query({estado:state, page})),
    detail: folio => AdminHTTP.call(/^CS-[0-9A-F]{8}$/.test(folio) ? `${cases}/${folio}` : null),
    attend: id => post(path(cases, id, '/atender')),
    connect: id => post(path(cases, id, '/conectar')),
    resolve: (id, result, note) => post(path(cases, id, '/resolver'), {result, note}),
    // El sondeo no cuenta como actividad: la consola abierta sin tocarla no mantiene viva la sesión de la cuenta.
    session: (id, signal) => AdminHTTP.call(path(sessions, id), {signal, headers:{'X-Chilito-Sondeo':'1'}}),
    order: (id, body) => post(path(sessions, id, '/accion'), body),
    endSession: id => post(path(sessions, id, '/cerrar'))
  });
})();

// ── Consultas ──
// Buzón de consultas del producto. Solo transporta y adapta datos: la autorización la decide Django.
const InquiryService = (() => {
  const states = Object.freeze({nueva:'Nueva', atendida:'Atendida', archivada:'Archivada'});
  // Estado real del aviso: aceptado por SMTP no significa que llegara a la bandeja.
  const notices = Object.freeze({pendiente:'Aviso pendiente de envío', aceptado_smtp:'Aviso aceptado por el servidor de correo', fallido:'El aviso por correo falló; se reintentará'});
  const statusOf = response => response.http===401?'unauthenticated':response.body?.code==='stale-record'?'stale':response.http===403?'forbidden':response.http===429?'limited':'error';
  async function call(path, options = {}) {
    try {
      const response = await ChilitoHTTP.request('/api/admin/consultas'+path, options);
      if(response.http===401) ChilitoHTTP.sessionExpired();
      return [200,201].includes(response.http) ? response.body : {status:statusOf(response)};
    } catch { return {status:'error'}; }
  }
  return Object.freeze({
    states, notices,
    // En segundo plano se marca como sondeo: el servidor no lo cuenta como actividad de la sesión.
    list(state = '', page = 1, {background = false} = {}) {
      const query = new URLSearchParams({page:String(page)});
      if(Object.hasOwn(states, state)) query.set('state', state);
      return call('?'+query, background ? {headers:{'X-Chilito-Sondeo':'1'}} : {});
    },
    advance(id, state) {
      if(!['atendida','archivada'].includes(state)) return Promise.resolve({status:'invalid'});
      return call('/'+encodeURIComponent(id)+'/estado', {method:'POST', body:{state}});
    },
    // Una archivada puede no haberse respondido: su responsable es el último registro, no «atendida por».
    attentionText(item) {
      if(!item.attendedBy) return 'Sin atender';
      const when = this.dateText(item.attendedAt);
      return item.state === 'atendida' ? `Atendida por ${item.attendedBy} el ${when}` : `Último registro: ${item.attendedBy}, ${when}`;
    },
    // Fecha legible como texto plano: la vista la inserta con textContent.
    dateText(value) {
      const date = new Date(value);
      return Number.isFinite(date.getTime()) ? date.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin fecha';
    },
    // Responder en Gmail web, en una pestaña nueva y con la cuenta de soporte si está configurada.
    // Es un enlace de redacción: sin API, sin OAuth y sin enviar nada en nombre del panel.
    replyHref(item) {
      const valid = value => typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      if(!valid(item.email)) return null;
      const query = new URLSearchParams({view:'cm', fs:'1', to:item.email, su:`Re: [El Chilito] Pregunta sobre el producto (${item.folio})`});
      const account = ChilitoHTTP.configuration?.supportContact;
      if(valid(account)) query.set('authuser', account);
      return 'https://mail.google.com/mail/?'+query;
    }
  });
})();

// ── Transporte ──
// Llamadas de las pantallas de administración. El servidor decide con la capacidad y el segundo factor; aquí solo se adapta la respuesta.
const AdminHTTP = (() => {
  const validId = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  const validUuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
  const query = values => { const params = new URLSearchParams(Object.entries(values).filter(([, value]) => value !== '' && value != null)); return params.size ? `?${params}` : ''; };
  async function call(path, {method = 'GET', body, signal, headers} = {}) {
    if(!path) return {status:'error', code:'invalid-input'};
    try {
      const response = await ChilitoHTTP.request(path, {method, body, signal, headers});
      if(response.http === 401) { ChilitoHTTP.sessionExpired(); return {status:'error', code:'unauthenticated'}; }
      return response.http === 200 ? response.body : {status:'error', code:response.body?.code || 'unavailable'};
    } catch { return {status:'error', code:'network'}; }
  }
  return Object.freeze({validId, validUuid, query, call});
})();

// ── Ventas ──
// Ventas de equipos. Los importes viajan como texto («3500.00»): el servidor valida y la base calcula el estado del pago.
const SalesModel = Object.freeze({
  // Periodos del resumen: «Este mes», «Mes anterior» y «Todo»; el personalizado usa las fechas escritas.
  period(preset) {
    const today = MaintenanceDates.today(), first = MaintenanceDates.make(today.getUTCFullYear(), today.getUTCMonth(), 1);
    if(preset === 'month') return {desde:MaintenanceDates.format(first), hasta:MaintenanceDates.format(today)};
    if(preset === 'previous') {
      const start = MaintenanceDates.make(today.getUTCFullYear(), today.getUTCMonth() - 1, 1), end = MaintenanceDates.make(today.getUTCFullYear(), today.getUTCMonth(), 0);
      return {desde:MaintenanceDates.format(start), hasta:MaintenanceDates.format(end)};
    }
    return {desde:'', hasta:''};
  },
  amount: value => /^\d{1,8}(\.\d{1,2})?$/.test(String(value).trim()) ? String(value).trim() : null
});

const SalesService = (() => {
  const base = '/api/admin/ventas';
  const sale = (id, rest) => AdminHTTP.validId(id) ? `${base}/${id}/${rest}` : null;
  return Object.freeze({
    list: (filters, page) => AdminHTTP.call(base + AdminHTTP.query({...filters, page})),
    summary: filters => AdminHTTP.call(`${base}/resumen${AdminHTTP.query(filters)}`),
    create: values => AdminHTTP.call(base, {method:'POST', body:values}),
    pay: (id, received, reference) => AdminHTTP.call(sale(id, 'pago'), {method:'POST', body:{received, reference}}),
    deliver: (id, deliveredAt) => AdminHTTP.call(sale(id, 'entrega'), {method:'POST', body:{deliveredAt}}),
    note: (id, note) => AdminHTTP.call(sale(id, 'nota'), {method:'POST', body:{note}}),
    cancel: id => AdminHTTP.call(sale(id, 'cancelar'), {method:'POST', body:{}})
  });
})();

// ── Administradores ──
const AdminAccessService = (() => {
  const base = '/api/admin/administradores';
  return Object.freeze({
    list: page => AdminHTTP.call(base + AdminHTTP.query({page})),
    history: (filters, page) => AdminHTTP.call(`${base}/historial${AdminHTTP.query({...filters, page})}`),
    activity: (filters, page) => AdminHTTP.call(`${base}/actividad${AdminHTTP.query({...filters, page})}`),
    change: (email, capabilities, reason) => AdminHTTP.call(`${base}/cuenta`, {method:'POST', body:{email, capabilities, reason}})
  });
})();

// ── Legales ──
const LegalAdminService = (() => {
  const base = '/api/admin/legales';
  const document = (id, rest = '') => AdminHTTP.validUuid(id) ? `${base}/${id}${rest}` : null;
  const MAX_FILE = 2 * 1024 * 1024;
  const upload = (rest, field, value, name) => { const form = new FormData(); form.append(field, value, name); return AdminHTTP.call(base + rest, {method:'POST', body:form}); };
  return Object.freeze({
    TYPES: ['terminos', 'aviso_privacidad', 'politica_cookies'],
    VERSION: /^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$/,
    // Solo ayuda a la persona: el servidor vuelve a revisar extensión, firma y tamaño.
    fileProblem: file => !/\.docx$/i.test(file.name) ? 'documento-no-docx' : file.size > MAX_FILE ? 'documento-grande' : null,
    importDocx: file => upload('/importar', 'documento', file, file.name),
    // El HTML del portapapeles viaja como archivo: puede pesar más que el límite de una petición JSON.
    sanitize: html => upload('/sanear', 'html', new Blob([html], {type:'text/html'}), 'pegado.html'),
    byType: type => AdminHTTP.call(base + AdminHTTP.query({tipo:type})),
    detail: id => AdminHTTP.call(document(id)),
    create: values => AdminHTTP.call(base, {method:'POST', body:values}),
    edit: (id, values) => AdminHTTP.call(document(id, '/editar'), {method:'POST', body:values}),
    remove: (id, expectedAt) => AdminHTTP.call(document(id, '/eliminar'), {method:'POST', body:{expectedAt}}),
    publish: (id, expectedAt) => AdminHTTP.call(document(id, '/publicar'), {method:'POST', body:{expectedAt}}),
    preview: content => AdminHTTP.call(`${base}/vista-previa`, {method:'POST', body:{content}})
  });
})();

// ── Consentimientos ──
const ConsentService = (() => {
  const base = '/api/admin/consentimientos';
  return Object.freeze({
    list: (filters, page) => AdminHTTP.call(base + AdminHTTP.query({...filters, page})),
    summary: () => AdminHTTP.call(`${base}/resumen`),
    // La exportación es una descarga del navegador, no una llamada: aquí solo se arma su dirección.
    exportUrl: filters => `${base}/exportar${AdminHTTP.query(filters)}`
  });
})();

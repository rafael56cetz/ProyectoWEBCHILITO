// MODELO · Administración: paneles de operación, buzón de consultas, ventas, administradores, textos legales y consentimientos.
// Define: AdminService, InquiryService, AdminHTTP, SalesModel, SalesService, AdminAccessService, LegalAdminService, ConsentService.

// ── Administracion ──
// Los datos de administración en memoria solo contienen respuestas autorizadas por Django.
const AdminService = (() => {
  const results=Object.freeze({solucionado:'Problema solucionado',sin_falla:'Sin falla detectada',sin_respuesta:'Sin respuesta de la persona usuaria',otro:'Otro (explicado en la nota)'});
  // Estado real del aviso: aceptado por SMTP no significa entregado en la bandeja.
  const noticeLabels=Object.freeze({pendiente:'Pendiente de envío',aceptado_smtp:'Aceptado por el servidor de correo',fallido:'Envío fallido; se reintentará'});
  let remote=null,diagnosis=null;
  const incidents=GardenModel.INCIDENTS;
  const statusOf=response=>response.body?.code==='stale-record'?'stale':response.http===403?'forbidden':response.http===401?'unauthenticated':response.http===429?'limited':'error';
  async function request(path,body) {
    try {
      const response=await ChilitoHTTP.request('/api/admin/'+path,body===undefined?{}:{method:'POST',body});
      if(response.http===401)ChilitoHTTP.sessionExpired();
      return [200,201].includes(response.http)?response.body:{status:statusOf(response)};
    }catch{return {status:'error'};}
  }
  async function closeRemote() {
    if(!remote)return {status:'accepted'};
    const prior=remote;
    const result=await request('sesiones/'+encodeURIComponent(prior.id)+'/cerrar',{});
    if(result.status==='accepted'||result.status==='unauthenticated') {if(remote===prior)remote=null;diagnosis=null;}
    return result;
  }
  async function act(ticket,action) {
    if(!remote||remote.ticket!==ticket)return {status:'no-permission'};
    if(remote.expiresAt<=Date.now()){await closeRemote();return {status:'no-permission'};}
    const result=await request('sesiones/'+encodeURIComponent(remote.id)+'/accion',{action});
    if(result.status!=='accepted') {remote=null;diagnosis=null;return result;}
    if(action==='diagnostic')diagnosis={pins:Array.isArray(result.pins)?result.pins:[],logs:Array.isArray(result.logs)?result.logs:[],at:result.at??null};
    return result;
  }
  return {
    results,noticeLabels,
    async snapshot(selectedId=null,screen='flota') {
      const name={flota:'flota',soporte:'soporte'}[screen];
      const result=await request(name);
      if(screen==='soporte'&&result.status==='ready'&&Array.isArray(result.items)) {
        let page=result.page||1;
        while(result.total>result.items.length&&page<100) {
          const next=await request(name+'?page='+(++page));
          if(next.status!=='ready'||!Array.isArray(next.items))return {status:'error'};
          if(!next.items.length)break;result.items.push(...next.items);
        }
      }
      if(result.status!=='ready')return result;
      const data={status:'ready',at:null,nodes:[],tickets:[],selected:null,remote:null,diagnostics:null,trends:{soil:[],humidity:[]},metrics:{},correlations:[],...result};
      if(screen==='soporte') {
        data.tickets=(result.items||[]).map(t=>({...t,incident:incidents[t.incident]||t.incident,status:{active:'Espera validación',expired:'Autorización vencida',revoked:'Autorización revocada',closed:'Sin autorización'}[t.permissionState]||'Sin autorización'}));
        data.selected=data.tickets.find(t=>t.id===selectedId)||null;
        if(remote&&remote.ticket===selectedId) {
          const checked=await act(selectedId,'diagnostic');
          if(checked.status==='accepted'){data.remote={...remote};data.diagnostics=diagnosis;data.selected.status='Diagnóstico autorizado';}
        }
      }
      return data;
    },
    async selectTicket(id){const result=await closeRemote();return result.status==='accepted'?{status:'accepted'}:result;},
    async requestToken(id) {
      if(!id)return {status:'not-found'};
      const closed=await closeRemote();if(closed.status!=='accepted')return closed;
      return request('soporte/'+encodeURIComponent(id)+'/solicitar-token',{});
    },
    // Resolver cierra el caso para siempre: el servidor revoca el permiso y cierra la sesión técnica.
    async resolveCase(id,result,note) {
      if(!id)return {status:'not-found'};
      const closed=await closeRemote();if(closed.status!=='accepted')return closed;
      return request('soporte/'+encodeURIComponent(id)+'/resolver',{result,note});
    },
    async validateToken(id,token) {
      if(!id)return {status:'not-found'};
      if(typeof token!=='string'||!/^[A-Za-z0-9_-]{43}$/.test(token))return {status:'invalid-token'};
      const closed=await closeRemote();if(closed.status!=='accepted')return closed;
      const result=await request('soporte/'+encodeURIComponent(id)+'/abrir',{token});
      if(result.status==='accepted'&&result.session?.id)remote={...result.session,ticket:id};
      return result;
    },
    refreshDiagnostics(id){return act(id,'diagnostic');},
    closeRemote,
    get remote(){return remote?{...remote}:null;},
    reset(){remote=null;diagnosis=null;}
  };
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
  async function call(path, {method = 'GET', body, signal} = {}) {
    if(!path) return {status:'error', code:'invalid-input'};
    try {
      const response = await ChilitoHTTP.request(path, {method, body, signal});
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
  return Object.freeze({
    TYPES: ['terminos', 'aviso_privacidad', 'politica_cookies'],
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

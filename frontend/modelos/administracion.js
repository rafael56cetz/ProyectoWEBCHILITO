// MODELO · Administración: paneles de administración, buzón de consultas y gestión comercial.
// Define: AdminService, InquiryService, CommerceModel.

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

// ── Comercial ──
// Contrato de presentación comercial. Sin red, DOM ni almacenamiento del navegador.
// Cada montaje posee sus borradores; ninguna revisión acredita un pago o autoriza vincular.
const CommerceModel = (() => {
  const availability = Object.freeze({disponible:'Disponible',reservado:'Reservado',no_disponible:'No disponible'});
  const deliveryModes = Object.freeze({domicilio:'Entrega a domicilio',recogida:'Recogida acordada'});
  const tabs = Object.freeze([['equipos','Equipos'],['ventas','Ventas y entregas'],['vinculacion','Vinculación'],['resumen','Resumen económico']]);
  const clean = value => typeof value === 'string' ? value.trim() : '';
  const printable = value => !/[\u0000-\u001f\u007f-\u009f]/u.test(value);
  // Unidades menores enteras: no se multiplica una fracción binaria de JavaScript.
  function amount(raw) {
    const value = clean(raw);
    if(!/^\d{1,9}(?:[.,]\d{1,2})?$/.test(value)) return null;
    const [units,fraction=''] = value.replace(',','.').split('.');
    return Number(units)*100 + Number(fraction.padEnd(2,'0'));
  }
  const money = cents => new Intl.NumberFormat('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2}).format(cents/100);
  const today = () => MaintenanceDates.format(MaintenanceDates.today());
  function identifier(value) {
    return /^[A-Za-z0-9][A-Za-z0-9._:-]{2,79}$/.test(value);
  }
  function equipment(raw) {
    const data = {identifier:clean(raw.identifier),gardenName:clean(raw.gardenName),availability:clean(raw.availability)};
    const errors = {};
    if(!identifier(data.identifier)) errors.identifier = 'Usa de 3 a 80 caracteres: letras, números, punto, guion, dos puntos o guion bajo; empieza por letra o número.';
    if(!data.gardenName || [...data.gardenName].length > 120 || !printable(data.gardenName)) errors.gardenName = 'Escribe un nombre de huerto de 1 a 120 caracteres, sin saltos de línea ni controles.';
    if(!Object.hasOwn(availability,data.availability)) errors.availability = 'Elige la disponibilidad propuesta.';
    return {data,errors};
  }
  function sale(raw, currentDay=today()) {
    const data = Object.fromEntries(['equipment','email','saleDate','total','received','reference','deliveryMode','deliveryDate'].map(key=>[key,clean(raw[key])]));
    const errors = {};
    if(!identifier(data.equipment)) errors.equipment = 'Escribe el identificador del equipo (3 a 80 caracteres, sin espacios).';
    if(!hasEmailFormat(data.email) || !/^[a-z0-9.!#$%&'*+\/=?^_`{|}~-]+$/i.test(data.email.split('@')[0]) || !printable(data.email)) errors.email = 'Escribe un correo válido. Su cuenta y verificación se comprobarán en el servidor.';
    if(!MaintenanceDates.parse(data.saleDate)) errors.saleDate = 'Escribe una fecha de venta válida con formato AAAA-MM-DD.';
    else if(data.saleDate > currentDay) errors.saleDate = 'La fecha de venta no puede ser posterior a hoy.';
    data.totalMinor = amount(data.total); data.receivedMinor = amount(data.received);
    if(data.totalMinor === null || data.totalMinor <= 0) errors.total = 'El precio debe ser mayor que cero, sin miles y con hasta dos decimales (máximo 999999999.99).';
    if(data.receivedMinor === null) errors.received = 'Escribe un importe desde cero, sin miles y con hasta dos decimales (máximo 999999999.99).';
    else if(data.totalMinor !== null && data.receivedMinor > data.totalMinor) errors.received = 'El importe recibido declarado no puede superar el precio total.';
    if([...data.reference].length > 120 || !printable(data.reference)) errors.reference = 'Usa hasta 120 caracteres, sin saltos de línea ni controles.';
    if(!Object.hasOwn(deliveryModes,data.deliveryMode)) errors.deliveryMode = 'Elige entrega a domicilio o recogida acordada.';
    if(data.deliveryDate && !MaintenanceDates.parse(data.deliveryDate)) errors.deliveryDate = 'Escribe una fecha de entrega válida con formato AAAA-MM-DD o déjala por acordar.';
    else if(data.deliveryDate && MaintenanceDates.parse(data.saleDate) && data.deliveryDate < data.saleDate) errors.deliveryDate = 'La fecha de entrega prevista no puede ser anterior a la venta.';
    if(!Object.keys(errors).length) data.balanceMinor = data.totalMinor-data.receivedMinor;
    return {data,errors};
  }
  function period(raw) {
    const errors = {};
    for(const key of ['since','until']) if(raw[key] && !MaintenanceDates.parse(raw[key])) errors[key] = 'Escribe una fecha válida con formato AAAA-MM-DD.';
    if(!errors.since && !errors.until && raw.since && raw.until && raw.until < raw.since) errors.until = 'Hasta debe ser igual o posterior a Desde.';
    return errors;
  }
  function periodPreset(value) {
    if(value === 'all') return {since:'',until:''};
    const now = MaintenanceDates.today();
    const start = MaintenanceDates.make(now.getUTCFullYear(),now.getUTCMonth()-(value === 'previous' ? 1 : 0),1);
    const end = value === 'previous' ? MaintenanceDates.shift(MaintenanceDates.make(now.getUTCFullYear(),now.getUTCMonth(),1),-1) : now;
    return {since:MaintenanceDates.format(start),until:MaintenanceDates.format(end)};
  }
  function create() {
    let state = {
      tab:'equipos',equipment:{identifier:'',gardenName:'',availability:''},
      sale:{equipment:'',email:'',saleDate:'',total:'',received:'',reference:'',deliveryMode:'',deliveryDate:''},
      equipmentReview:null,saleReview:null
    };
    return Object.freeze({
      read:()=>structuredClone(state),
      select(tab) { if(tabs.some(([key])=>key===tab)) state.tab=tab; },
      edit(kind, values) {
        if(!['equipment','sale'].includes(kind)) return;
        for(const key of Object.keys(state[kind])) if(Object.hasOwn(values,key)) state[kind][key]=String(values[key]);
        state[kind+'Review']=null;
      },
      review(kind) {
        const result = kind === 'equipment' ? equipment(state.equipment) : sale(state.sale);
        state[kind+'Review'] = Object.keys(result.errors).length ? null : result.data;
        return result;
      },
      dispose() { state={tab:'equipos',equipment:{},sale:{},equipmentReview:null,saleReview:null}; }
    });
  }
  return Object.freeze({tabs,availability,deliveryModes,amount,money,today,equipment,sale,period,periodPreset,create});
})();

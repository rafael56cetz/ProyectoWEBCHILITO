// Frontend contract with empty service data. No network or physical actuation.
// The future backend must enforce roles, report scope, expiry and auditing independently.
const AdminService = (() => {
  let authorize = () => false;
  let remote = null, validated = null, audit = [], releases = [];
  let knowledgeVersion = null;
  let knowledge = '';
  const activeVersion = null;
  const releaseTypes = Object.freeze({weights:'Actualizar pesos del modelo',math:'Publicar modelo matemático nuevo',rollback:'Revertir a versión estable'});
  const at = null;
  const nodes = [];
  let tickets = [];
  const trends = {soil:[],humidity:[]};
  const metrics = {reporting:null,total:null,availability:null,soilHumidity:null,evaporation:null,hardwareAlerts:null,priorityAlerts:null,perliteEvaporation:null,sensorLife:null,pumpOrders:null};
  const correlations = [];
  function addAudit(action,detail,status='Registrado') {
    audit.unshift({id:crypto.randomUUID(),at:new Date().toISOString(),action,detail,status});
  }
  function sync() {
    const permission=UserGardenService.permission();
    for(const report of UserGardenService.supportReports()) {
      let ticket=tickets.find(t=>t.id===report.ticket);
      if(!ticket) {
        ticket={id:report.ticket,device:report.device||null,user:report.user||null,incident:report.incident,status:'Espera validación',createdAt:new Date(report.createdAt).toISOString(),consent:true,expiresAt:report.expiresAt};
        tickets.unshift(ticket);
      }
      if(report.permissionState!=='active')ticket.status=report.permissionState==='expired'?'Autorización vencida':'Autorización revocada';
    }
    if(remote && (!permission || permission.ticket!==remote.ticket || permission.expiresAt!==remote.expiresAt)) {
      closeRemote('autorización no vigente');
    }
    return permission;
  }
  function closeRemote(reason='') {
    if(!remote)return;
    const ticket=find(remote.ticket);
    if(ticket?.status==='Diagnóstico autorizado')ticket.status='Espera validación';
    addAudit('Sesión técnica cerrada',remote.ticket+(reason?' · '+reason:''));
    remote=null;
  }
  const permitted = () => authorize()===true;
  const find = id => tickets.find(t=>t.id===id);
  function diagnostics() {
    return {
      at:null,
      pins:[
        ['GPIO 25 · Bomba A',null],['GPIO 26 · Bomba B',null],
        ['GPIO 27 · Lámpara',null],['I²C · SHT31',null],
        ['ADC · Humedad',null],['Flotador · Nivel',null]
      ],
      logs:[]
    };
  }
  function draftOf(raw={}) {
    return {type:String(raw.type||''),version:String(raw.version||'').trim(),notes:String(raw.notes||'').trim()};
  }
  function draftKey(raw) { return JSON.stringify(draftOf(raw)); }
  return {
    releaseTypes,
    configure({isAdmin}) { authorize=isAdmin; },
    snapshot(selectedId=null) {
      if(!permitted()) return {status:'forbidden'};
      sync();
      const selected=find(selectedId);
      const unlocked=!!(selected && remote?.ticket===selected.id);
      return structuredClone({
        status:'ready',at,nodes,tickets,selected:selected||null,
        remote:unlocked?{ticket:remote.ticket,expiresAt:remote.expiresAt}:null,
        diagnostics:unlocked?diagnostics(selected):null,
        trends,metrics,correlations,activeVersion,knowledgeVersion,knowledge,audit,releases
      });
    },
    selectTicket(id) {
      if(!permitted()) return {status:'forbidden'};
      sync();
      if(!find(id)) return {status:'not-found'};
      closeRemote('cambio de reporte');
      return {status:'accepted'};
    },
    requestToken(id) {
      if(!permitted()) return {status:'forbidden'};
      sync();
      const ticket=find(id);
      if(!ticket) return {status:'not-found'};
      closeRemote('solicitud de token');
      ticket.status='Token solicitado';
      addAudit('Solicitud de token',id+' · sin acceso concedido');
      return {status:'accepted'};
    },
    validateToken(id,token) {
      if(!permitted()) return {status:'forbidden'};
      const permission=sync(),ticket=find(id);
      closeRemote('nueva validación');
      if(!ticket) return {status:'not-found'};
      if(!permission) return {status:'no-permission'};
      if(permission.ticket!==id) return {status:'wrong-report'};
      if(typeof token!=='string'||token.trim().toUpperCase()!==permission.token) return {status:'invalid-token'};
      remote={ticket:id,expiresAt:permission.expiresAt};
      ticket.status='Diagnóstico autorizado';
      addAudit('Acceso técnico autorizado',id+' · alcance limitado al incidente');
      return {status:'accepted'};
    },
    refreshDiagnostics(id) {
      if(!permitted()) return {status:'forbidden'};
      sync();
      if(!remote || remote.ticket!==id) return {status:'no-permission'};
      addAudit('Consulta de diagnóstico',id+' · GPIO y errores recientes');
      return {status:'accepted'};
    },
    restartNode(id) {
      if(!permitted()) return {status:'forbidden'};
      sync();
      if(!remote || remote.ticket!==id) return {status:'no-permission'};
      addAudit('Solicitud de reinicio de nodo',id,'Sin confirmación del dispositivo');
      return {status:'accepted'};
    },
    closeRemote,
    validateRelease(raw) {
      if(!permitted()) return {status:'forbidden'};
      validated=null;
      const draft=draftOf(raw);
      if(!Object.hasOwn(releaseTypes,draft.type) || !/^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$/.test(draft.version)) return {status:'invalid-version'};
      if(draft.version===activeVersion) return {status:'same-version'};
      if(draft.notes.length>2000) return {status:'invalid-notes'};
      validated=draftKey(draft);
      addAudit('Versión validada en la interfaz',draft.version+' · '+releaseTypes[draft.type]);
      return {status:'accepted'};
    },
    requestRelease(raw) {
      if(!permitted()) return {status:'forbidden'};
      const draft=draftOf(raw);
      if(!validated || draftKey(draft)!==validated) return {status:'validation-required'};
      releases.unshift({...draft,at:new Date().toISOString(),status:'Sin confirmación del servicio'});
      addAudit(draft.type==='rollback'?'Solicitud de reversión':'Solicitud de publicación',draft.version+' · '+releaseTypes[draft.type],'Sin confirmación del servicio');
      validated=null;
      return {status:'accepted'};
    },
    saveKnowledge(raw) {
      if(!permitted()) return {status:'forbidden'};
      const text=String(raw||'').trim();
      if(text.length<20 || text.length>10000) return {status:'invalid-knowledge'};
      knowledge=text;knowledgeVersion=(knowledgeVersion||0)+1;
      addAudit('Base de conocimientos guardada','KB-'+knowledgeVersion+' · borrador local');
      return {status:'accepted'};
    },
    restartPlatform() {
      if(!permitted()) return {status:'forbidden'};
      addAudit('Solicitud de reinicio de plataforma','Mantenimiento y aplicación de parches','Sin confirmación del servicio');
      return {status:'accepted'};
    }
  };
})();

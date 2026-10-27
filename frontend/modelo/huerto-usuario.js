// Frontend state and UI contract. Replace the configured reader with the future backend adapter.
// Registration of an order never confirms physical actuation. No persistent storage is used here.
const UserGardenService = (() => {
  let reader = async () => ({ garden: { status:'error' } });
  let supportProvider=null;
  const hasSupport=()=>typeof supportProvider?.issuePermission==='function'&&typeof supportProvider?.revokePermission==='function';
  let maintenance = [], commands = [], reports = [], permission = null, lastPermissionState = 'closed';
  let lampRequest = null;
  const tasks = Object.freeze({refill:'Recarga del depósito',substrate:'Revisión de sustrato y perlita',germination:'Germinación externa',harvest:'Cosecha',inspection:'Inspección visual de conexiones'});
  const incidents = Object.freeze({pump:'La bomba no responde',humidity:'Lectura de humedad inconsistente',lamp:'La lámpara no enciende',connection:'Conexión inestable',other:'Otro problema de hardware'});
  const expiry = () => {
    if (permission && Date.now() >= permission.expiresAt) {
      const report=reports.find(r=>r.ticket===permission.ticket);if(report)report.permissionState='expired';
      permission = null; lastPermissionState = 'expired';
    }
  };
  return {
    tasks, incidents,
    configure(read,{support=null}={}) { reader=read;supportProvider=support; },
    get supportAvailable() { return hasSupport(); },
    permission() { expiry(); return permission ? {...permission} : null; },
    supportReports() { expiry(); return structuredClone(reports); },
    async load(range='1h', {signal}={}) {
      if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
      const source = await reader(range, {signal});
      if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
      expiry();
      return { ...source, garden:AppModel.garden(source.garden), range,
        soil:{adc:Number.isInteger(source.soil?.adc)&&source.soil.adc>=0&&source.soil.adc<=4095?source.soil.adc:null,moisture:AppModel.reading(source.soil?.moisture)},
        maintenance:structuredClone(maintenance), commands:structuredClone(commands),
        permission:permission ? {...permission} : null, permissionState:lastPermissionState, lampRequest, supportAvailable:hasSupport() };
    },
    recordTask(task) {
      if (!Object.hasOwn(tasks,task)) return {status:'error'};
      maintenance.unshift({id:crypto.randomUUID(),task,label:tasks[task],at:new Date().toISOString()});
      return {status:'accepted',label:tasks[task]};
    },
    async command(action, snapshot) {
      if (!['lamp-off','lamp-auto','water'].includes(action)) return {status:'error'};
      if (!snapshot?.connection?.wifi || !snapshot?.connection?.mqtt || snapshot?.garden?.status!=='ready') return {status:'offline'};
      if (action==='water' && snapshot.garden.tank.state!=='not-low') return {status:'low-water'};
      const label={water:'Solicitud de riego puntual','lamp-off':'Solicitud de apagado de lámpara','lamp-auto':'Restaurar control de lámpara'}[action];
      commands.unshift({id:crypto.randomUUID(),at:new Date().toISOString(),actuator:action==='water'?'Bomba de riego':'Lámpara',action:label,origin:'Usuario',status:'Sin confirmación'});
      if (action!=='water') lampRequest=action;
      return {status:'accepted'};
    },
    // Only the configured service can issue an authorization. No browser token generator.
    async issuePermission(incident,consent,{signal}={}) {
      if(!consent||!Object.hasOwn(incidents,incident))return {status:'invalid'};
      if(!hasSupport())return {status:'unavailable'};
      if(signal?.aborted)return {status:'cancelled'};
      const provider=supportProvider;
      let response;
      try{response=await provider.issuePermission({incident,consent:true},{signal});}
      catch{return {status:'unavailable'};}
      if(signal?.aborted||provider!==supportProvider)return {status:'cancelled'};
      if(response?.status!=='accepted')return {status:'unavailable'};
      const raw=response.permission;
      if(!raw||typeof raw.token!=='string'||!raw.token.trim()||raw.token.length>512
        ||typeof raw.ticket!=='string'||!raw.ticket.trim()||raw.ticket.length>128
        ||!Number.isFinite(raw.createdAt)||!Number.isFinite(raw.expiresAt)
        ||raw.expiresAt<=Date.now()||raw.expiresAt<=raw.createdAt
        ||raw.expiresAt-raw.createdAt>86400000)return {status:'error'};
      if(permission){const previous=reports.find(r=>r.ticket===permission.ticket);if(previous)previous.permissionState='revoked';}
      permission={token:raw.token,ticket:raw.ticket,incident:incidents[incident],createdAt:raw.createdAt,expiresAt:raw.expiresAt};
      const report={ticket:permission.ticket,incident:permission.incident,createdAt:permission.createdAt,expiresAt:permission.expiresAt,permissionState:'active'};
      for(const key of ['device','user'])if(typeof raw[key]==='string'&&raw[key].trim()&&raw[key].length<=128)report[key]=raw[key];
      const index=reports.findIndex(r=>r.ticket===report.ticket);
      if(index>=0)reports[index]=report;else reports.unshift(report);
      lastPermissionState='active';return {status:'accepted'};
    },
    async revokePermission({signal}={}) {
      expiry();
      if(!hasSupport())return {status:'unavailable'};
      if(!permission)return {status:'not-found'};
      if(signal?.aborted)return {status:'cancelled'};
      const provider=supportProvider,previous=permission;
      let response;
      try{response=await provider.revokePermission({ticket:previous.ticket},{signal});}
      catch{return {status:'unavailable'};}
      if(signal?.aborted||provider!==supportProvider)return {status:'cancelled'};
      if(response?.status!=='accepted')return {status:'unavailable'};
      const report=reports.find(r=>r.ticket===previous.ticket);if(report)report.permissionState='revoked';
      if(permission===previous){permission=null;lastPermissionState='revoked';}
      return {status:'accepted'};
    },
    reset() { maintenance=[]; commands=[]; reports=[]; permission=null; lampRequest=null; lastPermissionState='closed'; }
  };
})();

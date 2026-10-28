// Same-origin persisted user operations. Cached data only presents server responses.
const UserGardenService = (() => {
  const base='/api/huertos/actual';
  const tasks=Object.freeze({refill:'Recarga del depósito',substrate:'Revisión de sustrato y perlita',germination:'Germinación externa',harvest:'Cosecha',inspection:'Inspección visual de conexiones'});
  const incidents=Object.freeze({pump:'La bomba no responde',humidity:'Lectura de humedad inconsistente',lamp:'La lámpara no enciende',connection:'Conexión inestable',other:'Otro problema de hardware'});
  let active=null,reports=[];
  const failure=response=>response.http===401?'unauthenticated':response.http===403?'forbidden':response.http===429?'limited':'error';
  async function read(path,signal) {
    const response=await ChilitoHTTP.request(path,{signal});
    if(response.http!==200) {
      if(response.http===401)window.dispatchEvent(new Event('chilito:session-expired'));
      throw new Error(response.body?.code||'unavailable');
    }
    const body=response.body;
    if(Array.isArray(body.items)) {
      // All persisted history is fetched in bounded pages; never fabricate entries.
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
      if(response.http===401)window.dispatchEvent(new Event('chilito:session-expired'));
      return [200,201].includes(response.http)&&response.body.status==='accepted'?response.body:{status:failure(response)};
    }catch{return {status:'error'};}
  }
  function permission() {
    return active&&active.expiresAt>Date.now()?{...active}:null;
  }
  return {
    tasks,incidents,get supportAvailable(){return true;},permission,
    supportReports(){return structuredClone(reports);},
    async load(range='1h',{signal}={}) {
      const raw=await ChilitoHTTP.request(base,{signal});
      if(raw.http===401)window.dispatchEvent(new Event('chilito:session-expired'));
      if(raw.http!==200)return {garden:AppModel.garden({status:raw.body?.code==='garden-unassigned'?'unassigned':'error'})};
      const g=raw.body.garden||raw.body;
      const [maintenance,commands,support]=await Promise.all([read(base+'/mantenimiento',signal),read(base+'/solicitudes',signal),read('/api/soporte',signal)]);
      reports=support.items||[];
      const latest=reports.find(r=>r.permissionState==='active'&&r.expiresAt>Date.now());
      if(!latest)active=null;
      else active={ticket:latest.id,incident:incidents[latest.incident]||latest.incident,createdAt:Date.parse(latest.createdAt),expiresAt:latest.expiresAt,token:active?.ticket===latest.id?active.token:null};
      const records=(maintenance.items||[]).map(r=>({id:r.id,task:r.type,label:tasks[r.type]||r.type,at:r.at}));
      const orders=(commands.items||[]).map(r=>({id:r.id,at:r.at,actuator:r.type==='water'?'Bomba de riego':'Lámpara',action:{water:'Solicitud de riego puntual','lamp-off':'Solicitud de apagado de lámpara','lamp-auto':'Restaurar control de lámpara'}[r.type],origin:'Usuario',status:'Sin confirmación'}));
      const lamp=(commands.items||[]).find(r=>r.type==='lamp-off'||r.type==='lamp-auto');
      return {garden:AppModel.garden(g),range,soil:{adc:null,moisture:{value:null,quality:'missing',at:null}},connection:{wifi:null,mqtt:null},diagnosis:null,history:{soil:[],temperature:[],humidity:[]},maintenance:records,commands:orders,permission:permission(),permissionState:latest?'active':reports[0]?.permissionState||'closed',supportAvailable:true,reports:structuredClone(reports),lampRequest:lamp?.type||null};
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
    reset(){active=null;reports=[];}
  };
})();

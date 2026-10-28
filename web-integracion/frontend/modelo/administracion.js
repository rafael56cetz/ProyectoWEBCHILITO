// Administrative presentation caches contain only authorized Django responses.
const AdminService = (() => {
  const releaseTypes=Object.freeze({weights:'Actualizar pesos del modelo',math:'Publicar modelo matemático nuevo',rollback:'Revertir a versión estable'});
  let remote=null,validated=null,diagnosis=null;
  const incidents=UserGardenService.incidents;
  const auditLabels=Object.freeze({maintenance:'Mantenimiento registrado','support-granted':'Autorización de soporte otorgada','support-revoked':'Autorización de soporte revocada','token-requested':'Token de soporte solicitado','technical-opened':'Sesión técnica abierta','technical-closed':'Sesión técnica cerrada','diagnostic-requested':'Diagnóstico solicitado','request-recorded':'Solicitud registrada','version-validated':'Versión validada','knowledge-saved':'Revisión de conocimientos guardada'});
  const statusOf=response=>response.http===403?'forbidden':response.http===401?'unauthenticated':response.http===429?'limited':response.body?.code==='validation-required'?'validation-required':'error';
  async function request(path,body) {
    try {
      const response=await ChilitoHTTP.request('/api/admin/'+path,body===undefined?{}:{method:'POST',body});
      if(response.http===401)window.dispatchEvent(new Event('chilito:session-expired'));
      return [200,201].includes(response.http)?response.body:{status:statusOf(response)};
    }catch{return {status:'error'};}
  }
  const draftOf=raw=>({type:String(raw?.type||''),version:String(raw?.version||'').trim(),notes:String(raw?.notes||'').trim()});
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
    releaseTypes,
    async snapshot(selectedId=null,screen='flota') {
      const name={flota:'flota',soporte:'soporte',gobernanza:'gobernanza',despliegues:'cambios'}[screen];
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
      const data={status:'ready',at:null,nodes:[],tickets:[],selected:null,remote:null,diagnostics:null,trends:{soil:[],humidity:[]},metrics:{},correlations:[],activeVersion:null,knowledgeVersion:null,knowledge:'',audit:[],releases:[],...result};
      if(screen==='soporte') {
        data.tickets=(result.items||[]).map(t=>({...t,incident:incidents[t.incident]||t.incident,status:{active:'Espera validación',expired:'Autorización vencida',revoked:'Autorización revocada',closed:'Sin autorización'}[t.permissionState]||'Sin autorización'}));
        data.selected=data.tickets.find(t=>t.id===selectedId)||null;
        if(remote&&remote.ticket===selectedId) {
          const checked=await act(selectedId,'diagnostic');
          if(checked.status==='accepted'){data.remote={...remote};data.diagnostics=diagnosis;data.selected.status='Diagnóstico autorizado';}
        }
      }
      if(screen==='despliegues') {
        data.releases=(result.releases||[]).map(r=>({...r,status:'Sin confirmación del servicio'}));
        data.audit=(result.audit||[]).map(a=>({...a,actionCode:a.action,action:auditLabels[a.action]||'Evento registrado',detail:a.permissionId?'Permiso '+a.permissionId:'Actor '+a.actor,status:a.status==='pending'?'Sin confirmación':'Registrado'}));
      }
      return data;
    },
    async selectTicket(id){const result=await closeRemote();return result.status==='accepted'?{status:'accepted'}:result;},
    async requestToken(id) {
      if(!id)return {status:'not-found'};
      const closed=await closeRemote();if(closed.status!=='accepted')return closed;
      return request('soporte/'+encodeURIComponent(id)+'/solicitar-token',{});
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
    restartNode(id){return act(id,'restart-node');},
    closeRemote,
    async validateRelease(raw) {
      validated=null;const draft=draftOf(raw);
      if(!Object.hasOwn(releaseTypes,draft.type)||!/^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$/.test(draft.version))return {status:'invalid-version'};
      if(draft.notes.length>2000)return {status:'invalid-notes'};
      const result=await request('validaciones',draft);
      if(result.status==='accepted'&&result.validation?.id)validated={id:result.validation.id,key:JSON.stringify(draft)};
      return result;
    },
    async requestRelease(raw) {
      if(!validated||validated.key!==JSON.stringify(draftOf(raw)))return {status:'validation-required'};
      const result=await request('despliegues',{validationId:validated.id});
      if(result.status==='accepted')validated=null;
      return result;
    },
    async saveKnowledge(content) {
      if(typeof content!=='string'||Array.from(content).length<20||Array.from(content).length>10000)return {status:'invalid-knowledge'};
      return request('conocimiento',{content});
    },
    restartPlatform(){return request('reinicio',{});},
    get remote(){return remote?{...remote}:null;},
    reset(){remote=null;validated=null;diagnosis=null;}
  };
})();

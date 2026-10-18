// Synthetic metadata and operations only. No browser credential/device API or storage.
FrontendDevelopment.createSecurity = (selected=()=>FrontendDevelopment.scenarios.security) => {
  const date = '2026-10-17T16:00:00Z';
  let items = [], sequence = 0;
  const operations = new Map();
  const wait = (signal,scenario=selected())=>new Promise((resolve,reject)=>{
    if(signal?.aborted) { reject(new DOMException('Cancelled','AbortError')); return; }
    const abort=()=>{clearTimeout(timer);reject(new DOMException('Cancelled','AbortError'));};
    const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},scenario==='slow'?2200:500);
    signal?.addEventListener('abort',abort,{once:true});
  });
  function reset() {
    items = ['revoke-rejected','invalid-response','populated'].includes(selected()) ? [
      {id:'key-1',name:'Llave de acceso principal',createdAt:date,lastUsedAt:date},
      {id:'key-2',name:'Llave de respaldo',createdAt:null,lastUsedAt:null}
    ] : [];
    sequence=0;operations.clear();
  }
  async function request(action,payload={}, {signal}={}) {
    const scenario=selected();
    await wait(signal,scenario);
    for(const [id,operation] of operations) if(operation.expiresAt<=Date.now()) operations.delete(id);
    if(['unavailable','unauthenticated','reauthentication-required','recovery-required','verification-required'].includes(scenario)) return {status:scenario};
    if(action==='passkey-list') return scenario==='list-error'?{status:'error'}:{status:'ready',items:structuredClone(items)};
    if(action.endsWith('-begin')) {
      if(scenario==='not-supported') return {status:'not-supported'};
      const purpose=action==='passkey-login-begin'?'login':'register';
      const operationId=`demo-operation-${++sequence}`,expiresAt=Date.now()+60000;
      operations.set(operationId,{purpose,expiresAt});
      return {status:'ready',operationId,expiresAt:new Date(expiresAt).toISOString(),publicKeyOptions:null};
    }
    if(action.endsWith('-finish')) {
      const operation=operations.get(payload.operationId);
      const purpose=action==='passkey-login-finish'?'login':'register';
      if(!operation || operation.purpose!==purpose || payload.response?.demonstration!==true || payload.response.operationId!==payload.operationId) return {status:'invalid-response'};
      operations.delete(payload.operationId);
      if(scenario==='error')return {status:'error'};
      if(scenario==='invalid-response')return purpose==='login'?{status:'authenticated'}:{status:'created',credential:{name:'Ejemplo incompleto'}};
      if(purpose==='login')return {status:'authenticated',sessionConfirmed:true};
      const credential={id:`key-${sequence}`,name:'Llave de acceso del dispositivo',createdAt:date,lastUsedAt:null};
      items.push(credential);
      return {status:'created',credential:structuredClone(credential)};
    }
    if(action==='passkey-revoke') {
      if(scenario==='revoke-rejected')return {status:'rejected'};
      if(scenario==='invalid-response')return {status:'revoked'};
      if(!items.some(item=>item.id===payload.id))return {status:'rejected'};
      items=items.filter(item=>item.id!==payload.id);
      return {status:'revoked',id:payload.id};
    }
    return {status:'unavailable'};
  }
  async function interact({operationId,purpose,signal}) {
    const scenario=selected();
    await wait(signal,scenario);
    if(!operations.has(operationId))return {status:'expired-operation'};
    if(scenario==='cancelled') {operations.delete(operationId);return {status:'cancelled'};}
    if(scenario==='expired-operation') {operations.delete(operationId);return {status:'expired-operation'};}
    return {status:'completed',response:{demonstration:true,operationId,purpose}};
  }
  reset();
  return Object.freeze({request,interact,reset});
};

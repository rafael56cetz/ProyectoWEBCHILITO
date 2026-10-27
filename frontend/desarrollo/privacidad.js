// Development adapter: starts empty for clean empty state.
FrontendDevelopment.createPrivacy = (selected=()=>FrontendDevelopment.scenarios.privacy) => {
  const date = '2026-10-17T16:00:00Z';
  let sequence = 0;
  const items = [];
  const pause = (delay,signal) => new Promise((resolve,reject)=>{
    if(signal?.aborted) { reject(new DOMException('Cancelled','AbortError')); return; }
    const abort = () => { clearTimeout(timer); reject(new DOMException('Cancelled','AbortError')); };
    const timer = setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},delay);
    signal?.addEventListener('abort',abort,{once:true});
  });
  return Object.freeze({
    async request(action,payload={}, {signal}={}) {
      const scenario = selected();
      await pause(scenario==='slow'?5000:650,signal);
      if(['unavailable','unauthenticated','forbidden','not-found'].includes(scenario)) return {status:scenario};
      if(action==='arco-list') return {status:'ready',items:structuredClone(scenario==='empty'?[]:items)};
      if(action==='arco-detail') {
        let item = items.find(item=>item.id===payload.id);
        if(!item && payload.id==='arco-1') {
          item = {
            id:'arco-1',reference:'ARCO-001',right:'rectification',state:'received',receivedAt:date,updatedAt:date,
            publicSummary:'Solicitud registrada por el usuario.',
            history:[{state:'received',at:date,publicMessage:'Recepción confirmada.'}],
            informationRequest:null
          };
          items.push(item);
        }
        if(!item && payload.id==='demo-informacion') {
          item = {
            id:'demo-informacion',reference:'ARCO-002',right:'access',state:'awaiting-information',receivedAt:date,updatedAt:date,
            publicSummary:'Solicitud de acceso a datos personales.',
            history:[{state:'received',at:date,publicMessage:'Recepción confirmada.'},{state:'awaiting-information',at:date,publicMessage:'Se requiere información adicional.'}],
            informationRequest:{id:'info-1',message:'Especifica los periodos o registros requeridos.',canRespond:true}
          };
          items.push(item);
        }
        if(!item) return {status:'not-found'};
        const request = structuredClone(item);
        if(scenario==='read-only' && request.informationRequest) request.informationRequest.canRespond = false;
        return {status:'ready',request};
      }
      if(scenario==='validation-error') return {status:'validation-error',fieldErrors:action==='arco-create'?{description:'Añade una descripción más clara.'}:{message:'Aclara la información solicitada.'}};
      if(action==='arco-create') {
        const fieldErrors = PrivacyModel.validate(payload);
        if(Object.keys(fieldErrors).length) return {status:'validation-error',fieldErrors};
        if(scenario==='invalid-receipt') return {status:'accepted',receipt:{reference:'ARCO-INCOMPLETO'}};
        const id = `arco-${++sequence}`;
        const ref = `ARCO-${String(sequence).padStart(3, '0')}`;
        const request = {id,reference:ref,right:payload.right,state:'received',receivedAt:new Date().toISOString(),updatedAt:new Date().toISOString(),
          publicSummary:'Solicitud registrada por el usuario.',history:[{state:'received',at:new Date().toISOString(),publicMessage:'Recepción confirmada.'}],informationRequest:null};
        items.push(request);
        return {status:'accepted',receipt:{id,reference:request.reference,receivedAt:request.receivedAt,state:'received'}};
      }
      if(action==='arco-add-info') {
        const request = items.find(item=>item.id===payload.id);
        if(!request) return {status:'not-found'};
        if(scenario==='read-only' || !request.informationRequest?.canRespond || request.informationRequest.id!==payload.informationRequestId) return {status:'forbidden'};
        if(!payload.message?.trim()) return {status:'validation-error',fieldErrors:{message:'Escribe una aclaración.'}};
        request.informationRequest.canRespond = false;
        request.history.push({state:request.state,at:new Date().toISOString(),publicMessage:'Se recibió la aclaración solicitada.'});
        return {status:'accepted',request:structuredClone(request)};
      }
      return {status:'unavailable'};
    }
  });
};

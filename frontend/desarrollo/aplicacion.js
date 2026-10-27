// No measured values are invented. All garden readings keep waiting for data.
FrontendDevelopment.appService=Object.freeze({
  async request(action,payload={}, {signal}={}){
    if(signal?.aborted)throw new DOMException('Cancelled','AbortError');
    if(action==='garden')return {status:'waiting'};
    if(action==='profile')return {status:'ready',email:null,verified:null};
    if(action==='notices')return {status:'ready',items:[]};
    return {status:'unavailable'};
  }
});

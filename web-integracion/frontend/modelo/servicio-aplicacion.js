// Persisted account/garden/notice data from the same origin. No fallback collections.
const AppService = Object.freeze({
  async request(action, payload={}, {signal}={}) {
    if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
    if (action === 'logout') return AuthService.logout({signal});
    const base='/api/huertos/actual';
    const path={profile:'/api/cuenta',garden:base,notices:base+'/avisos'}[action];
    if(['notice','mark-read'].includes(action) && !AppModel.idValid(payload.id)) return {status:'not-found'};
    const endpoint=path || (action === 'notice' ? base+'/avisos/'+encodeURIComponent(payload.id)
      : action === 'mark-read' ? base+'/avisos/'+encodeURIComponent(payload.id)+'/lectura' : null);
    if(!endpoint) return {status:'unavailable'};
    const response=await ChilitoHTTP.request(endpoint,{signal,
      ...(action === 'mark-read' ? {method:'POST',body:{}} : {})});
    if(response.http === 401 || response.body?.code === 'verification-required') {
      AuthService.forgetSession();
      window.dispatchEvent(new Event('chilito:session-expired'));
      return {status:'unauthenticated'};
    }
    if(response.http === 403 && response.body?.code === 'garden-unassigned') return {status:'unassigned'};
    if(response.http === 404) return {status:'not-found'};
    if(![200,201].includes(response.http)) return {status:'error'};
    if(action === 'profile') return AppModel.profile(response.body);
    if(action === 'garden') return AppModel.garden(response.body.garden || response.body);
    if(action === 'notices') {
      const items=[...(response.body.items||[])];let page=response.body.page||1;
      while(response.body.total>items.length&&page<100) {
        const next=await ChilitoHTTP.request(endpoint+'?page='+(++page),{signal});
        if(next.http!==200||!Array.isArray(next.body.items))return {status:'error',items:[]};
        if(!next.body.items.length)break;items.push(...next.body.items);
      }
      return AppModel.notices({...response.body,items});
    }
    if(action === 'notice') {
      const item=AppModel.notice((response.body?.item || response.body?.notice));
      return response.body?.status === 'ready' && item?.id === payload.id ? {status:'ready',items:[item]} : {status:'error'};
    }
    if(action === 'mark-read') {
      const item=AppModel.notice((response.body?.item || response.body?.notice));
      return response.body?.status === 'accepted' && response.body.id === payload.id
        && response.body.read === true && item?.id === payload.id && item.read === true
        ? {status:'accepted',id:item.id,item} : {status:'error'};
    }
    return {status:'error'};
  }
});

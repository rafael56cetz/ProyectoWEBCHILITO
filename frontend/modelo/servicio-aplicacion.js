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
      ...(action === 'mark-read' ? {method:'PUT',body:{}} : {})});
    if(response.http === 401 || response.body?.code === 'verification-required') {
      AuthService.forgetSession();
      window.dispatchEvent(new Event('chilito:session-expired'));
      return {status:'unauthenticated'};
    }
    if(response.http === 403 && response.body?.code === 'garden-unassigned') return {status:'unassigned'};
    if(response.http === 404 && response.body?.code === 'notice-not-found') return {status:'not-found'};
    if(response.http !== 200) return {status:'error'};
    if(action === 'profile') return AppModel.profile(response.body);
    if(action === 'garden') return AppModel.garden(response.body);
    if(action === 'notices') return AppModel.notices(response.body);
    if(action === 'notice') {
      const item=AppModel.notice(response.body?.item);
      return response.body?.status === 'ready' && item?.id === payload.id ? {status:'ready',items:[item]} : {status:'error'};
    }
    if(action === 'mark-read') {
      const item=AppModel.notice(response.body?.item);
      return response.body?.status === 'accepted' && response.body.id === payload.id
        && response.body.read === true && item?.id === payload.id && item.read === true
        ? {status:'accepted',id:item.id,item} : {status:'error'};
    }
    return {status:'error'};
  }
});

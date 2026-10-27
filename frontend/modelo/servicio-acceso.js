// Same-origin browser transport. Session authority and secrets stay in Django/allauth.
const ChilitoHTTP = (() => {
  let bootstrap = null;
  const csrf = () => document.cookie.split(';').map(item => item.trim()).find(item => item.startsWith('csrftoken='))?.slice(10) || '';
  async function request(path, {method='GET', body, signal, headers={}} = {}) {
    if (!path.startsWith('/api/') && !path.startsWith('/_allauth/browser/v1/')) throw new Error('Unsupported endpoint');
    if (method !== 'GET' && !csrf()) await configure(signal);
    const response = await fetch(path, {
      method, credentials:'same-origin', cache:'no-store', redirect:'error', signal,
      headers:{Accept:'application/json', ...(body ? {'Content-Type':'application/json'} : {}),
        ...(method !== 'GET' ? {'X-CSRFToken':decodeURIComponent(csrf())} : {}), ...headers},
      ...(body ? {body:JSON.stringify(body)} : {})
    });
    let data = {};
    try { data = await response.json(); } catch { /* Never interpret an HTML error as success. */ }
    return {http:response.status, body:data};
  }
  async function configure(signal) {
    const response = await request('/api/acceso/configuracion', {signal});
    if (response.http !== 200 || typeof response.body.registrationAllowed !== 'boolean') throw new Error('Configuration unavailable');
    bootstrap = response.body;
    return bootstrap;
  }
  return Object.freeze({request,configure,get configuration(){return bootstrap;}});
})();

const AuthService = (() => {
  const prefix = '/_allauth/browser/v1/';
  let session = {status:'unknown'}, version = 0;
  const authenticated = result => result.body?.meta?.is_authenticated === true;
  const pending = result => result.body?.data?.flows?.some(flow => flow.id === 'verify_email' && flow.is_pending === true);
  const errors = result => Array.isArray(result.body?.errors) ? result.body.errors : [];
  function failure(result) {
    if (result.http === 429 || errors(result).some(error=>error.code === 'too_many_login_attempts')) return {status:'limited',retryAfterSeconds:60};
    if (result.body?.code === 'csrf-failed') return {status:'csrf-failed'};
    if (result.http >= 500) return {status:'unavailable'};
    return null;
  }
  async function verificationContext({signal}={}) {
    const result = await ChilitoHTTP.request('/api/acceso/verificacion', {signal});
    if (result.http === 200 && typeof result.body?.email === 'string') {
      return {status:'verification-required',email:result.body.email,expiresAt:result.body.expiresAt};
    }
    return failure(result) || {status:'verification-expired'};
  }
  async function restore({signal}={}) {
    const id = ++version;
    const result = await ChilitoHTTP.request(prefix+'auth/session',{signal});
    let next;
    if (result.http === 200 && authenticated(result)) {
      const profile = await ChilitoHTTP.request('/api/cuenta',{signal});
      next = profile.http === 200 && profile.body.status === 'ready' && profile.body.verified === true
        ? {status:'authenticated',profile:profile.body}
        : failure(profile) || {status:'unauthenticated'};
    } else if (result.http === 401 && pending(result)) {
      next = await verificationContext({signal});
    } else {
      next = failure(result) || {status:'unauthenticated'};
    }
    if (id === version) session = next;
    return next;
  }
  async function request(action, payload={}, {signal}={}) {
    if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
    const options = {method:'POST',signal};
    let result;
    if (action === 'login') {
      result = await ChilitoHTTP.request(prefix+'auth/login', {...options,body:{email:payload.email,password:payload.password}});
      if (failure(result)) return failure(result);
      if ((result.http === 200 && authenticated(result)) || result.http === 409) {
        const restored = await restore({signal});
        return restored.status === 'authenticated' ? {status:'authenticated',sessionConfirmed:true} : restored;
      }
      if (result.http === 401 && pending(result)) return verificationContext({signal});
      return result.http === 400 ? {status:'invalid-credentials'} : {status:'unavailable'};
    }
    if (action === 'register') {
      result = await ChilitoHTTP.request(prefix+'auth/signup', {...options,body:{
        email:payload.email,password:payload.password,termsAccepted:payload.termsAccepted}});
      if (result.body?.code === 'email-not-authorized') return {status:'email-not-authorized'};
      if (result.body?.code === 'mail-unavailable') return {status:'mail-unavailable'};
      if (result.body?.code === 'terms-required') return {status:'terms-required'};
      if (result.body?.code === 'registration-disabled') return {status:'registration-disabled'};
      if (failure(result)) return failure(result);
      if (result.http === 401 && pending(result)) {
        const next = await verificationContext({signal});
        return next.status === 'verification-required' ? {status:'accepted',expiresAt:next.expiresAt,resendAfterSeconds:60} : next;
      }
      if (result.http === 400) {
        const invalid = errors(result);
        if (invalid.some(error=>error.param === 'password')) return {status:'password-rejected'};
        if (invalid.some(error=>error.param === 'termsAccepted')) return {status:'terms-required'};
        return {status:'invalid-registration'};
      }
      if (result.http === 409) return {status:'unauthenticated'};
      return {status:'unavailable'};
    }
    if (action === 'verify' || action === 'resend') {
      result = await ChilitoHTTP.request(prefix+(action === 'verify' ? 'auth/email/verify' : 'auth/email/verify/resend'),
        {...options,body:action === 'verify' ? {key:payload.code} : {}});
      if (failure(result)) return failure(result);
      if (action === 'verify' && [200,401].includes(result.http) && result.body.status === result.http && typeof result.body.meta?.is_authenticated === 'boolean') {
        const restored = await restore({signal});
        return {status:'verified',sessionConfirmed:restored.status === 'authenticated'};
      }
      if (action === 'resend' && result.http === 200 && result.body.status === 200) return {status:'accepted',resendAfterSeconds:60};
      if (result.http === 409 || result.http === 410) return {status:'verification-expired'};
      if (action === 'resend' && result.http === 403) return {status:'verification-expired'};
      return action === 'verify' && result.http === 400 ? {status:'incorrect-code'} : {status:'unavailable'};
    }
    if (action === 'request-reset') {
      result = await ChilitoHTTP.request(prefix+'auth/password/request', {...options,body:{email:payload.email}});
      return failure(result) || {status:result.http === 200 && result.body.status === 200 ? 'accepted' : 'unavailable'};
    }
    if (action === 'inspect-reset') {
      result = await ChilitoHTTP.request(prefix+'auth/password/reset', {signal,headers:{'X-Password-Reset-Key':payload.token}});
      return failure(result) || {status:result.http === 200 && result.body.status === 200 && typeof result.body.data?.user?.email === 'string' ? 'reset-valid' : result.http === 400 ? 'invalid-link' : 'unavailable'};
    }
    if (action === 'reset' || action === 'change-password') {
      result = await ChilitoHTTP.request(prefix+(action === 'reset' ? 'auth/password/reset' : 'account/password/change'),
        {...options,body:action === 'reset' ? {key:payload.token,password:payload.password} : {
          current_password:payload.currentPassword,new_password:payload.password}});
      if (failure(result)) return failure(result);
      if ([200,401].includes(result.http) && result.body.status === result.http && typeof result.body.meta?.is_authenticated === 'boolean' && (action === 'reset' || authenticated(result))) {
        if (action === 'change-password') await restore({signal});
        return {status:action === 'reset' ? 'reset-complete' : 'password-changed'};
      }
      if (result.http === 400) {
        const invalid = errors(result);
        if (invalid.some(error=>error.param === 'key')) return {status:'invalid-link'};
        if (invalid.some(error=>error.param === 'current_password')) return {status:'incorrect-current-password'};
        return {status:'password-rejected'};
      }
      if (result.http === 401 || result.body.code === 'verification-required') return {status:'unauthenticated'};
      return {status:'unavailable'};
    }
    // Passkeys are deferred: no browser device interaction or synthetic success.
    return {status:'unavailable'};
  }
  function forgetSession() {
    version++; session = {status:'unauthenticated'};
  }
  async function logout({signal}={}) {
    const result = await ChilitoHTTP.request(prefix+'auth/session',{method:'DELETE',signal});
    if (result.http === 401 && result.body.status === 401 && result.body?.meta?.is_authenticated === false) {
      forgetSession();
      return {status:'accepted'};
    }
    return failure(result) || {status:'unavailable'};
  }
  return Object.freeze({request,restore,verificationContext,logout,forgetSession,passkeysAvailable:false,get session(){return session;}});
})();

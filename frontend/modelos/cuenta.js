// MODELO · Cuenta: validación de formularios y comunicación con el servidor para el acceso y el segundo factor.
// Define: ChilitoHTTP (todas las peticiones), AuthConfig, AuthModel, AuthService, MfaService.
// Debe cargarse primero: los demás modelos usan ChilitoHTTP.

// ── Acceso ──
// Solo valida el formato. Django/allauth valida las credenciales y los permisos.
function hasEmailFormat(value) {
  const parts = value.split('@');
  if (parts.length !== 2 || value.length > 254) return false;
  const [local, domain] = parts;
  return local.length > 0 && local.length <= 64 && !local.startsWith('.') && !local.endsWith('.') && !local.includes('..')
    && domain.includes('.') && domain.split('.').every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}

// Política de presentación de respaldo; la configuración vigente se carga desde Django.
const AuthConfig = Object.freeze({
  registrationAllowed: false,
  password: Object.freeze({ minLength: null, maxLength: null, requirements: [] }),
  code: Object.freeze({ length: null, pattern: null, inputMode: 'text', expiresAfterSeconds: null, resendAfterSeconds: null }),
  requestTimeoutMs: 20000
});
const AuthModel = Object.freeze({
  screens: ['acceso', 'registro', 'verificar', 'recuperar', 'restablecer'],
  // Cuenta puntos de código, igual que len(str) de Python, sin alterar el texto.
  passwordLength(value) { return Array.from(value).length; },
  consumeResetLink(currentLocation, browserHistory) {
    const [path,query='']=currentLocation.hash.slice(1).split('?');
    if(path!=='restablecer')return '';
    const parameters=new URLSearchParams(query);
    const token=parameters.get('key')||parameters.get('token')||'';
    if(token)browserHistory.replaceState(null,'',currentLocation.pathname+currentLocation.search+'#restablecer');
    return token;
  },
  // Recomendaciones para orientar: no bloquean el envío ni son reglas del servidor.
  passwordHints(password, email = '') {
    const simple = value => value.toLowerCase().replace(/[^\p{L}\p{Nd}]/gu,'');
    const account = simple(email.split('@')[0] || '');
    return {cases:/\p{Lu}/u.test(password) && /\p{Ll}/u.test(password),number:/\p{Nd}/u.test(password),
      symbol:/[^\p{L}\p{Nd}\s]/u.test(password),usesEmail:account.length >= 3 && simple(password).includes(account),emailKnown:account.length >= 3};
  },
  passwordProgress(password, confirmation = '', config = AuthConfig, email = '') {
    const length = this.passwordLength(password);
    const {minLength, maxLength} = config.password;
    const hasMinimum = Number.isInteger(minLength) && minLength > 0;
    const hasMaximum = Number.isInteger(maxLength) && maxLength > 0;
    return {length, minLength, maxLength, meetsMinimum:hasMinimum && length >= minLength,
      range:hasMaximum && length > maxLength ? 'over-maximum' : hasMinimum ? length < minLength ? 'below-minimum' : 'within-range' : 'unavailable',
      numericOnly:/^\p{Nd}+$/u.test(password),hints:this.passwordHints(password,email),
      confirmation:!confirmation ? 'empty' : password === confirmation ? 'matches' : 'differs'};
  },
  // Lo que solo sabe el servidor se explica al rechazar; la contraseña nunca sale de este envío.
  passwordRejection(code) {
    return {password_pwned:'Esa contraseña aparece en filtraciones conocidas. Elige otra que no uses en ningún otro sitio.',
      password_too_common:'Esa contraseña es demasiado común. Prueba con una frase larga que solo tú recuerdes.',
      password_too_similar:'Se parece demasiado a tu correo o a los datos de tu cuenta. Elige una distinta.',
      password_entirely_numeric:'No puede tener solo números. Añade palabras o letras.',
      password_too_short:'Es demasiado corta. Revisa el mínimo de caracteres.'}[code] || 'El servidor no aceptó esta contraseña. Elige otra distinta.';
  },
  validate(screen, values, config = AuthConfig) {
    const errors = {};
    if (['acceso', 'registro', 'verificar', 'recuperar'].includes(screen)) {
      const email = (values.email || '').trim();
      if (!email || /\s/.test(email) || !hasEmailFormat(email)) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
    }
    if (['acceso', 'registro', 'restablecer', 'cambiar'].includes(screen)) {
      const password = values.password || '';
      if (!password) errors.password = 'Escribe tu contraseña.';
      else if (screen !== 'acceso') {
        const policy = config.password;
        if (policy.minLength && this.passwordLength(password) < policy.minLength) errors.password = `Usa al menos ${policy.minLength} caracteres.`;
        if (policy.maxLength && this.passwordLength(password) > policy.maxLength) errors.password = `Usa como máximo ${policy.maxLength} caracteres.`;
      }
    }
    if (screen === 'cambiar' && !(values.currentPassword || '')) errors.currentPassword = 'Escribe tu contraseña actual.';
    if (['registro', 'restablecer', 'cambiar'].includes(screen)) {
      if (!values.confirmation) errors.confirmation = 'Confirma tu contraseña.';
      else if (values.confirmation !== values.password) errors.confirmation = 'Las contraseñas no coinciden.';
    }
    if (screen === 'registro' && values.termsAccepted !== true) errors.termsAccepted = 'Debes aceptar los Términos y condiciones para continuar';
    if (screen === 'registro' && values.privacyRead !== true) errors.privacyRead = 'Debes confirmar que leíste el Aviso de privacidad para continuar';
    if (screen === 'verificar') {
      const code = (values.code || '').trim();
      if (!code) errors.code = 'Escribe el código de verificación.';
      else if (config.code.length && code.length !== config.code.length) errors.code = `El código debe tener ${config.code.length} caracteres.`;
      else if (config.code.pattern && !new RegExp(config.code.pattern).test(code)) errors.code = 'Revisa el formato del código.';
    }
    return errors;
  },
  secondsLeft(deadline, now = Date.now()) {
    return Number.isFinite(deadline) ? Math.max(0, Math.ceil((deadline - now) / 1000)) : 0;
  },
  deadline(seconds, now = Date.now()) {
    return Number.isFinite(seconds) && seconds > 0 ? now + Math.min(seconds, 86400) * 1000 : 0;
  },
  expiry(value) {
    const time = typeof value === 'string' ? Date.parse(value) : value;
    return Number.isFinite(time) && time > 0 ? time : 0;
  },
  duration(seconds) {
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  }
});

// Transporte del navegador al mismo origen. La autoridad de la sesión y los secretos se quedan en Django/allauth.
const ChilitoHTTP = (() => {
  let bootstrap = null;
  const pendingWrites = new Map();
  let onExpired = () => {};
  // En el sitio publicado la cookie lleva el prefijo __Host- (no la puede fijar un subdominio); en local, el nombre de Django.
  const CSRF_COOKIES = ['__Host-csrftoken=', 'csrftoken='];
  const csrf = () => { const items = document.cookie.split(';').map(item => item.trim());
    for(const name of CSRF_COOKIES) { const found = items.find(item => item.startsWith(name)); if(found) return found.slice(name.length); }
    return ''; };
  async function request(path, {method='GET', body, signal, headers={}} = {}) {
    if (!path.startsWith('/api/') && !path.startsWith('/_allauth/browser/v1/')) throw new Error('Unsupported endpoint');
    if (method !== 'GET' && !csrf()) await configure(signal);
    // Un formulario con archivo solo se transforma en el servidor (no escribe datos): no lleva recibo de idempotencia.
    const form = globalThis.FormData !== undefined && body instanceof FormData;
    const write = method === 'POST' && path.startsWith('/api/') && !form;
    const fingerprint = write ? method+' '+path+' '+JSON.stringify(body ?? {}) : null;
    // Conserva la clave tras un resultado incierto del transporte o del servidor, para reintentar con seguridad.
    const key = write ? pendingWrites.get(fingerprint) || crypto.randomUUID() : null;
    if (write) pendingWrites.set(fingerprint,key);
    const response = await fetch(path, {
      method, credentials:'same-origin', cache:'no-store', redirect:'error', signal,
      headers:{Accept:'application/json', ...(body && !form ? {'Content-Type':'application/json'} : {}),
        ...(method !== 'GET' ? {'X-CSRFToken':decodeURIComponent(csrf())} : {}), ...(key ? {'Idempotency-Key':key} : {}), ...headers},
      ...(body ? {body:form ? body : JSON.stringify(body)} : {})
    });
    let data = {};
    try { data = await response.json(); } catch { /* Never interpret an HTML error as success. */ }
    if(write && response.status < 500 && response.status !== 429) pendingWrites.delete(fingerprint);
    // 400 con «field» y «message» (reglas de los campos): la vista lo pone junto al campo.
    if(response.status === 400 && typeof data?.field === 'string' && typeof data?.message === 'string' && typeof CustomEvent === 'function')
      window.dispatchEvent(new CustomEvent('chilito:campo', {detail:{field:data.field, code:data.code, message:data.message}}));
    return {http:response.status, body:data};
  }
  async function configure(signal) {
    const response = await request('/api/acceso/configuracion', {signal});
    if (response.http !== 200 || typeof response.body.registrationAllowed !== 'boolean') throw new Error('Configuration unavailable');
    bootstrap = response.body;
    return bootstrap;
  }
  return Object.freeze({request,configure,sessionExpired:()=>onExpired(),onSessionExpired(handler){onExpired=handler;},clearPending:()=>pendingWrites.clear(),get configuration(){return bootstrap;}});
})();

const AuthService = (() => {
  const prefix = '/_allauth/browser/v1/';
  let session = {status:'unknown'}, version = 0;
  const authenticated = result => result.body?.meta?.is_authenticated === true;
  const pending = result => result.body?.data?.flows?.some(flow => flow.id === 'verify_email' && flow.is_pending === true);
  const errors = result => Array.isArray(result.body?.errors) ? result.body.errors : [];
  const secondStep = result => result.http === 401 && result.body?.data?.flows?.some(flow => ['login_by_code','mfa_authenticate'].includes(flow.id) && flow.is_pending === true);
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
      const profile = await ChilitoHTTP.request('/api/cuenta',{signal,headers:{'X-Chilito-Sondeo':'1'}});
      next = profile.http === 200 && profile.body.status === 'ready' && profile.body.verified === true
        ? {status:'authenticated',sessionConfirmed:true,profile:profile.body,role:profile.body.session?.role || profile.body.role || 'user',capabilities:profile.body.session?.capabilities || profile.body.capabilities || []}
        : failure(profile) || {status:'unauthenticated'};
    } else if (result.http === 401 && pending(result)) {
      next = await verificationContext({signal});
    } else if (secondStep(result)) {
      next = {status:'second-step'};
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
      if (secondStep(result)) return {status:'second-step'};
      return result.http === 400 ? {status:'invalid-credentials'} : {status:'unavailable'};
    }
    if (action === 'register') {
      result = await ChilitoHTTP.request(prefix+'auth/signup', {...options,body:{
        email:payload.email,password:payload.password,termsAccepted:payload.termsAccepted,privacyRead:payload.privacyRead}});
      if (result.body?.code === 'email-not-authorized') return {status:'email-not-authorized'};
      if (result.body?.code === 'mail-unavailable') return {status:'mail-unavailable'};
      if (result.body?.code === 'terms-required') return {status:'terms-required'};
      if (result.body?.code === 'privacy-required') return {status:'privacy-required'};
      if (result.body?.code === 'registration-disabled') return {status:'registration-disabled'};
      if (result.body?.code === 'legal-no-publicado') return {status:'legal-not-published'};
      if (failure(result)) return failure(result);
      if (result.http === 401 && pending(result)) {
        const next = await verificationContext({signal});
        return next.status === 'verification-required' ? {status:'accepted',expiresAt:next.expiresAt,resendAfterSeconds:60} : next;
      }
      if (result.http === 400) {
        const invalid = errors(result);
        const rejected = invalid.find(error=>error.param === 'password');
        if (rejected) return {status:'password-rejected',reason:rejected.code};
        if (invalid.some(error=>error.param === 'termsAccepted')) return {status:'terms-required'};
        if (invalid.some(error=>error.param === 'privacyRead')) return {status:'privacy-required'};
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
        if (restored.status === 'second-step') return restored;
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
      if ([200,401].includes(result.http) && result.body.status === result.http && errors(result).length === 0 && typeof result.body.meta?.is_authenticated === 'boolean' && (action === 'reset' || authenticated(result))) {
        if (action === 'change-password') await restore({signal});
        return {status:action === 'reset' ? 'reset-complete' : 'password-changed'};
      }
      if (result.http === 400) {
        const invalid = errors(result);
        if (invalid.some(error=>error.param === 'key')) return {status:'invalid-link'};
        if (invalid.some(error=>error.param === 'current_password')) return {status:'incorrect-current-password'};
        return {status:'password-rejected',reason:invalid.find(error=>['password','new_password'].includes(error.param))?.code};
      }
      if (result.http === 401 || result.body.code === 'verification-required') return {status:'unauthenticated'};
      return {status:'unavailable'};
    }
    return {status:'unavailable'};
  }
  function forgetSession() {
    version++; session = {status:'unauthenticated'};
  }
  // La sesión terminó en el servidor (cierre de sesión o cuenta eliminada): se olvida todo lo de la cuenta en el navegador.
  function sessionEnded() {
    forgetSession();
    ChilitoHTTP.clearPending();
    GardenModel.reset();
  }
  // El servidor cierra la sesión técnica de soporte al cerrar la sesión de la cuenta.
  async function logout({signal}={}) {
    const result = await ChilitoHTTP.request(prefix+'auth/session',{method:'DELETE',signal});
    if (result.http === 401 && result.body.status === 401 && result.body?.meta?.is_authenticated === false) {
      sessionEnded();
      return {status:'accepted'};
    }
    return failure(result) || {status:'unavailable'};
  }
  return Object.freeze({request,restore,verificationContext,logout,forgetSession,sessionEnded,get session(){return session;}});
})();

// ── Segundo factor ──
// Segundo factor. La criptografía y las reglas viven en allauth; aquí solo se transporta.
const MfaService = (() => {
  const p = '/_allauth/browser/v1/';
  const a = p+'account/authenticators';
  function outcome(r) {
    if(r.http === 429 || r.body?.errors?.some(e => e.code === 'too_many_login_attempts')) return {status:'limited'};
    if(r.http === 401 && r.body?.data?.flows?.some(f => ['reauthenticate','mfa_reauthenticate'].includes(f.id))) return {status:'reauthentication-required'};
    if(r.http === 401 && r.body?.meta?.is_authenticated === false && !r.body?.data?.flows?.some(f => f.is_pending)) return {status:'unauthenticated'};
    if(r.http === 400) return {status:'invalid'};
    if(r.http === 409) return {status:'conflict'};
    if(r.http === 404) return {status:'not-found',meta:r.body?.meta};
    if(r.http === 200 || r.http === 401) return {status:'ok',data:r.body?.data,meta:r.body?.meta};
    return {status:'unavailable'};
  }
  async function call(path, method = 'GET', body) {
    try { return outcome(await ChilitoHTTP.request(path, {method, ...(body ? {body} : {})})); }
    catch { return {status:'unavailable'}; }
  }
  const pendingStep = data => data?.flows?.find(flow => flow.is_pending === true && ['login_by_code','mfa_authenticate'].includes(flow.id));
  // Con un correo, abre el mensaje ya redactado. Nunca pide contraseñas ni códigos.
  function supportContact(contact) {
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) return {text:'Contacto: '+contact};
    const body = 'Perdí el acceso a mi cuenta de YouGarden.\n\nCorreo de mi cuenta:\nQué perdí (app, llave, códigos):\nFecha aproximada en que me registré:\n\nNo incluyas tu contraseña ni códigos.';
    return {text:'Escribir a soporte: '+contact, href:'mailto:'+contact+'?subject='+encodeURIComponent('Recuperar acceso a YouGarden')+'&body='+encodeURIComponent(body)};
  }
  return Object.freeze({
    supportContact,
    async pending() {
      const result = await call(p+'auth/session');
      const flow = pendingStep(result.data);
      return flow ? {kind:flow.id,types:flow.types || []} : null;
    },
    finished: result => result.status === 'ok' && result.meta?.is_authenticated === true,
    confirmCode: code => call(p+'auth/code/confirm','POST',{code}),
    authenticate: code => call(p+'auth/2fa/authenticate','POST',{code}),
    webauthnRequest: () => call(p+'auth/webauthn/authenticate'),
    webauthnAuthenticate: credential => call(p+'auth/webauthn/authenticate','POST',{credential}),
    list: () => call(a),
    reauthenticate: password => call(p+'auth/reauthenticate','POST',{password}),
    totpStart: () => call(a+'/totp'),
    async totpImage() {
      try { const r = await ChilitoHTTP.request('/api/cuenta/seguridad/totp-qr'); return r.http === 200 ? r.body.image : null; }
      catch { return null; }
    },
    totpActivate: code => call(a+'/totp','POST',{code}),
    totpDisable: () => call(a+'/totp','DELETE',{}),
    recoveryView: () => call(a+'/recovery-codes'),
    recoveryRegenerate: () => call(a+'/recovery-codes','POST',{}),
    webauthnOptions: () => call(a+'/webauthn'),
    webauthnAdd: (name,credential) => call(a+'/webauthn','POST',{name,credential}),
    webauthnRemove: ids => call(a+'/webauthn','DELETE',{authenticators:ids})
  });
})();

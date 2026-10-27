// Format validation only. Django/allauth validates credentials and permissions.
function hasEmailFormat(value) {
  const parts = value.split('@');
  if (parts.length !== 2 || value.length > 254) return false;
  const [local, domain] = parts;
  return local.length > 0 && local.length <= 64 && !local.startsWith('.') && !local.endsWith('.') && !local.includes('..')
    && domain.includes('.') && domain.split('.').every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}

// Fallback presentation policy; the active configuration is loaded from Django.
const AuthConfig = Object.freeze({
  registrationAllowed: false,
  password: Object.freeze({ minLength: null, maxLength: null, requirements: [] }),
  code: Object.freeze({ length: null, pattern: null, inputMode: 'text', expiresAfterSeconds: null, resendAfterSeconds: null }),
  requestTimeoutMs: 20000
});
const AuthModel = Object.freeze({
  screens: ['acceso', 'registro', 'verificar', 'recuperar', 'restablecer'],
  // Count code points, matching Python len(str), without altering the input.
  passwordLength(value) { return Array.from(value).length; },
  passwordProgress(password, confirmation = '', config = AuthConfig) {
    const length = this.passwordLength(password);
    const {minLength, maxLength} = config.password;
    const hasMinimum = Number.isInteger(minLength) && minLength > 0;
    const hasMaximum = Number.isInteger(maxLength) && maxLength > 0;
    return {length, minLength, maxLength, meetsMinimum:hasMinimum && length >= minLength,
      range:hasMaximum && length > maxLength ? 'over-maximum' : hasMinimum ? length < minLength ? 'below-minimum' : 'within-range' : 'unavailable',
      confirmation:!confirmation ? 'empty' : password === confirmation ? 'matches' : 'differs'};
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

// Metadata and presentation contracts only. No WebAuthn or device API is used.
const PasskeyModel = (() => {
  const hasText = value => typeof value === 'string' && value.trim().length > 0;
  const validId = value => hasText(value) && !/[\s\u0000-\u001f\u007f]/.test(value);
  function metadata(raw) {
    if(!raw || !validId(raw.id)) return null;
    const result = {id:raw.id};
    for(const key of ['name','createdAt','lastUsedAt']) {
      const value = raw[key];
      if(value == null || value === '') result[key] = null;
      else if(typeof value !== 'string' || (key !== 'name' && !Number.isFinite(Date.parse(value)))) return null;
      else result[key] = key === 'name' ? value.trim() || null : value;
    }
    return result;
  }
  const failure = response => ['error','unavailable','unauthenticated','reauthentication-required','recovery-required','verification-required','cancelled','not-supported','expired-operation','rejected'].includes(response?.status) ? response.status : 'error';
  function list(response) {
    if(response?.status !== 'ready') return {status:failure(response)};
    if(!Array.isArray(response.items)) return {status:'error'};
    const items = response.items.map(metadata);
    if(items.some(item=>!item) || new Set(items.map(item=>item.id)).size !== items.length) return {status:'error'};
    return {status:items.length ? 'ready' : 'empty',items};
  }
  function operation(response, now=Date.now()) {
    if(response?.status !== 'ready' || !validId(response.operationId) || !hasText(response.expiresAt)) return null;
    const expiresAt = Date.parse(response.expiresAt);
    return Number.isFinite(expiresAt) && expiresAt > now ? {id:response.operationId,expiresAt} : null;
  }
  return Object.freeze({metadata,list,failure,operation,
    sessionConfirmed:response=>response?.status === 'authenticated' && response.sessionConfirmed === true,
    offerAllowed:response=>response?.status === 'verified' && response.sessionConfirmed === true,
    created:response=>response?.status === 'created' ? metadata(response.credential) : null,
    revoked:(response,id)=>response?.status === 'revoked' && response.id === id
  });
})();

// Format validation only. Existence and credentials must be checked by the future backend.
function hasEmailFormat(value) {
  const parts = value.split('@');
  if (parts.length !== 2 || value.length > 254) return false;
  const [local, domain] = parts;
  return local.length > 0 && local.length <= 64 && !local.startsWith('.') && !local.endsWith('.') && !local.includes('..')
    && domain.includes('.') && domain.split('.').every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}

// Proposed integration settings. Null means that the backend policy is not yet agreed.
const AuthConfig = Object.freeze({
  password: Object.freeze({ minLength: null, maxLength: null, requirements: [] }),
  code: Object.freeze({ length: null, pattern: null, inputMode: 'text', expiresAfterSeconds: null, resendAfterSeconds: null }),
  requestTimeoutMs: 20000
});
const AuthModel = Object.freeze({
  screens: ['acceso', 'registro', 'verificar', 'recuperar', 'restablecer'],
  validate(screen, values, config = AuthConfig) {
    const errors = {};
    if (['acceso', 'registro', 'verificar', 'recuperar'].includes(screen)) {
      const email = (values.email || '').trim();
      if (!email || /\s/.test(email) || !hasEmailFormat(email)) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
    }
    if (['acceso', 'registro', 'restablecer', 'cambiar'].includes(screen)) {
      const password = values.password || '';
      if (!password.trim()) errors.password = 'Escribe tu contraseña.';
      else if (screen !== 'acceso') {
        const policy = config.password;
        if (policy.minLength && password.length < policy.minLength) errors.password = `Usa al menos ${policy.minLength} caracteres.`;
        if (policy.maxLength && password.length > policy.maxLength) errors.password = `Usa como máximo ${policy.maxLength} caracteres.`;
      }
    }
    if (screen === 'cambiar' && !(values.currentPassword || '').trim()) errors.currentPassword = 'Escribe tu contraseña actual.';
    if (['registro', 'restablecer', 'cambiar'].includes(screen)) {
      if (!values.confirmation) errors.confirmation = 'Confirma tu contraseña.';
      else if (values.confirmation !== values.password) errors.confirmation = 'Las contraseñas no coinciden.';
    }
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

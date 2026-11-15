// MODELO · Equipos: vinculación de huertos y ayuda por correo para vincular.
// Define: BindingService, BindingHelp.

// ── Vinculacion ──
// Vinculación de huertos. Solo transporta y adapta: valida, decide y vincula el servidor.
// El código nunca se guarda en el navegador (ni localStorage ni sessionStorage).
const BindingService = (() => {
  const ALPHABET = /^[0-9A-HJKMNP-TV-Z]{26}$/;
  const statusOf = response => response.http===401?'unauthenticated'
    :response.body?.code==='reauthentication-required'?'reauthenticate'
    :response.body?.code==='stale-record'?'stale'
    :response.http===403?'forbidden':response.http===429?'busy':response.http===400?'invalid':'error';
  async function call(path, options = {}) {
    try {
      const response = await ChilitoHTTP.request(path, options);
      if(response.http===401) ChilitoHTTP.sessionExpired();
      return response.http===200 ? response.body : {status:statusOf(response)};
    } catch { return {status:'network'}; }
  }
  // Misma normalización que el servidor, solo para avisar antes de enviar; el servidor vuelve a validar.
  function normalize(text) {
    const clean = String(text || '').replace(/[\s\-‐-―]/g,'').toUpperCase().replace(/O/g,'0').replace(/[IL]/g,'1');
    return ALPHABET.test(clean) ? clean : null;
  }
  const mailStates = Object.freeze({
    no_aplica:'Entrega presencial', pendiente:'Envío en curso',
    aceptado_smtp:'El servidor de correo aceptó el mensaje. Esto no confirma que haya llegado al buzón.',
    rechazado:'No se envió. El código quedó anulado.',
    incierto:'No pudimos confirmar el envío. El código quedó anulado: si el correo llega después, ya no servirá.'});
  const states = Object.freeze({pendiente:'Pendiente', expired:'Vencido', consumido:'Usado', revocado:'Revocado',
    reemplazado:'Reemplazado', bloqueado:'Bloqueado por intentos'});
  const refusals = Object.freeze({
    'invalid-delivery':'Elige cómo se entregará el código.',
    'garden-unavailable':'Ese huerto no existe o no tiene un equipo registrado.',
    'account-not-eligible':'No hay una cuenta activa y verificada con ese correo.',
    'account-has-garden':'Esa cuenta ya tiene un huerto vinculado.',
    'garden-occupied':'Ese huerto ya está vinculado a otra cuenta.',
    'previous-membership':'Esa cuenta ya tuvo este huerto. Reactivarlo no se hace desde aquí.',
    'mail-requires-in-person':'El envío por correo solo se permite después de una emisión presencial de ese huerto para esa cuenta.'});
  return Object.freeze({
    normalize, mailStates, states, refusals,
    consume(code) {
      const clean = normalize(code);
      return clean ? call('/api/vinculacion', {method:'POST', body:{code:clean}}) : Promise.resolve({status:'format'});
    },
    panel: () => call('/api/admin/vinculacion'),
    issue: (garden, email, delivery) => call('/api/admin/vinculacion/emitir', {method:'POST', body:{garden:String(garden), email:String(email).trim(), delivery}}),
    revoke: id => call('/api/admin/vinculacion/'+encodeURIComponent(id)+'/revocar', {method:'POST', body:{}}),
    dateText(value) {
      const date = new Date(value);
      return Number.isFinite(date.getTime()) ? date.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin fecha';
    },
    timeText(value) {
      const date = new Date(value);
      return Number.isFinite(date.getTime()) ? date.toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}) : '';
    }
  });
})();

// Ayuda para quien no puede vincular: solo redacta un borrador de correo.
// No envía nada, no crea casos, no genera códigos y no acredita la propiedad del huerto.
const BindingHelp = (() => {
  const SUBJECT = '[El Chilito] Ayuda con la vinculación';
  const OPENING = 'Hola, necesito ayuda para vincular mi huerto.';
  const EXTRA = 'Información adicional (opcional; no incluyas códigos, contraseñas, tu domicilio ni otros secretos):';
  const MAX_DETAIL = 300;
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const CODE_DASH = '\\-\u2010-\u2015';
  // Aviso previo, no una barrera de seguridad: la persona revisa el mensaje antes de enviarlo.
  const SECRET_LIKE = Object.freeze([
    new RegExp(`(?:[0-9a-z][${CODE_DASH}]?){26}`, 'i'),        // Código de vinculación, con o sin guiones
    new RegExp(`(?:[0-9A-Z][\\s${CODE_DASH}]?){26}`),          // El mismo código, agrupado con espacios
    /(?<!\d)\d{6}(?!\d)/]);                                    // Código de 6 dígitos (2FA o verificación)
  const reasons = new Map([
    ['expired', {text:'El código que recibí venció antes de completar la vinculación. Quisiera solicitar orientación para obtener uno nuevo.'}],
    ['lost', {text:'Perdí o no encuentro el código de vinculación. Quisiera solicitar orientación para obtener uno nuevo.'}],
    ['rejected', {text:'El código que recibí no funciona al intentar vincular mi huerto. Quisiera solicitar orientación para resolverlo.'}],
    ['other', {needsDetail:true}]]);
  // Sin sustitutos sueltos (encodeURIComponent los rechaza) ni caracteres de control, salvo el salto de línea.
  const clean = text => String(text ?? '').replace(/\p{Cs}/gu, '\uFFFD').replace(/\r\n?/g, '\n').replace(/[^\P{Cc}\n]/gu, ' ').trim();
  // La dirección también se codifica: un valor mal configurado no puede añadir cabeceras al correo.
  const encodeAddress = address => address.split('@').map(encodeURIComponent).join('@');
  const encodeBody = text => encodeURIComponent(text.replace(/\n/g, '\r\n'));
  function contact() {
    const value = ChilitoHTTP.configuration?.supportContact;
    const address = typeof value === 'string' ? value.trim() : '';
    return address.length <= 254 && EMAIL.test(address) ? address : null;
  }
  function explanation(reason, detail) {
    return reason.needsDetail ? `No he podido completar la vinculación por este motivo: ${detail} Quisiera solicitar orientación para resolverlo.` : reason.text;
  }
  function draft(reasonId, rawDetail) {
    const address = contact();
    if(!address) return {status:'unavailable'};
    const reason = reasons.get(reasonId);
    if(!reason) return {status:'need-reason'};
    const detail = reason.needsDetail ? clean(rawDetail) : '';
    if(reason.needsDetail && !detail) return {status:'need-detail'};
    if(detail.length > MAX_DETAIL) return {status:'too-long'};
    if(SECRET_LIKE.some(pattern => pattern.test(detail))) return {status:'secret'};
    const body = `${OPENING} ${explanation(reason, detail)}\n\n${EXTRA}\n\n`;
    const href = `mailto:${encodeAddress(address)}?subject=${encodeURIComponent(SUBJECT)}&body=${encodeBody(body)}`;
    const text = `Para: ${address}\nAsunto: ${SUBJECT}\n\nMensaje:\n${body.trimEnd()}\n`;
    return {status:'ready', address, subject:SUBJECT, body, href, text};
  }
  return Object.freeze({contact, draft, MAX_DETAIL});
})();

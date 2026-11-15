// MODELO · Equipos: emisión de códigos de vinculación por el operador.
// Define: BindingService.

// ── Vinculacion ──
// Vinculación de huertos. Solo transporta y adapta: valida, decide y vincula el servidor.
// El código nunca se guarda en el navegador (ni localStorage ni sessionStorage).
const BindingService = (() => {
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
    mailStates, states, refusals,
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

// Provisional UI contract. Identity, authorization and legal decisions belong to the service.
const PrivacyModel = (() => {
  const rights = Object.freeze({access:'Acceso',rectification:'Rectificación',cancellation:'Cancelación',opposition:'Oposición',unsure:'No sé cuál corresponde'});
  const states = Object.freeze({received:'Recibida','awaiting-information':'Pendiente de información','in-review':'En revisión',responded:'Respondida'});
  const fields = ['requesterName','contactEmail','right','description','accountRelation','requestedCorrection'];
  const text = value => typeof value === 'string' && value.trim().length > 0;
  // Opaque transport identifiers only; this is not an identity or authorization check.
  const validId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
  const validDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value));
  function values(raw) {
    const result = Object.fromEntries(fields.map(key => [key,typeof raw[key] === 'string' ? raw[key].trim() : '']));
    if(result.right !== 'rectification') result.requestedCorrection = '';
    return result;
  }
  function validate(raw) {
    const data = values(raw), errors = {};
    if(!data.requesterName) errors.requesterName = 'Escribe el nombre de la persona solicitante.';
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.contactEmail)) errors.contactEmail = 'Escribe un correo de contacto válido.';
    if(!Object.hasOwn(rights,data.right)) errors.right = 'Elige un tipo de solicitud.';
    if(!data.description) errors.description = 'Describe lo que deseas solicitar.';
    if(data.right === 'rectification' && !data.requestedCorrection) errors.requestedCorrection = 'Describe la corrección que solicitas.';
    return errors;
  }
  function receipt(raw) {
    if(!raw || !validId(raw.id) || !text(raw.reference) || !validDate(raw.receivedAt) || raw.state !== 'received') return null;
    return {id:raw.id,reference:raw.reference,receivedAt:raw.receivedAt,state:raw.state};
  }
  function summary(raw) {
    if(!raw || !validId(raw.id) || !text(raw.reference) || !Object.hasOwn(rights,raw.right) || !Object.hasOwn(states,raw.state) || !validDate(raw.receivedAt) || !validDate(raw.updatedAt)) return null;
    return {id:raw.id,reference:raw.reference,right:raw.right,state:raw.state,receivedAt:raw.receivedAt,updatedAt:raw.updatedAt,publicSummary:typeof raw.publicSummary === 'string' ? raw.publicSummary : ''};
  }
  function detail(raw, id) {
    const item = summary(raw);
    if(!item || item.id !== id || !Array.isArray(raw.history) || !raw.history.length) return null;
    const history = [];
    for(const entry of raw.history) {
      if(!entry || !Object.hasOwn(states,entry.state) || !validDate(entry.at) || !text(entry.publicMessage)) return null;
      history.push({state:entry.state,at:entry.at,publicMessage:entry.publicMessage});
    }
    let informationRequest = null;
    if(raw.informationRequest != null) {
      const info = raw.informationRequest;
      if(!validId(info.id) || !text(info.message) || typeof info.canRespond !== 'boolean') return null;
      informationRequest = {id:info.id,message:info.message,canRespond:item.state === 'awaiting-information' && info.canRespond};
    }
    return {...item,history,informationRequest};
  }
  function failure(response) {
    return ['unauthenticated','forbidden','not-found'].includes(response?.status) ? response.status : 'unavailable';
  }
  function list(response) {
    if(response?.status !== 'ready' || !Array.isArray(response.items)) return {status:failure(response)};
    const items = response.items.map(summary);
    if(items.some(item => !item) || new Set(items.map(item=>item.id)).size !== items.length) return {status:'unavailable'};
    return {status:items.length ? 'ready' : 'empty',items};
  }
  function fieldErrors(response, allowed = fields) {
    return Object.fromEntries(Object.entries(response?.fieldErrors || {}).filter(([key,value])=>allowed.includes(key) && text(value)));
  }
  return Object.freeze({rights,states,fields,values,validate,receipt,detail,list,failure,fieldErrors,validId,
  registrationAllowed: false,
  documents: Object.freeze({
    terminos: Object.freeze({title:'Términos y condiciones', state:'pending', version:null}),
    privacidad: Object.freeze({title:'Aviso de privacidad', state:'pending', version:null})
  })
  });
})();

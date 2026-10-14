// Presentation contracts only; freshness, calibration and permissions belong to the server.
const AppModel = (() => {
  const destinations = [
    {id:'huerto',label:'Mi huerto',icon:'grid'}, {id:'avisos',label:'Avisos',icon:'bell'},
    {id:'asistente',label:'Asistente',icon:'sparkle'}, {id:'cuenta',label:'Mi cuenta',icon:'user'}
  ];
  const states = {
    waiting:['Esperando las primeras lecturas','Las mediciones aparecerán cuando estén disponibles.','clock'],
    ready:['Datos disponibles','Consulta la fecha de cada lectura.','wifi'],
    stale:['Datos desactualizados','Las últimas lecturas se conservan como referencia; no describen necesariamente el estado actual.','clock'],
    offline:['Dispositivo sin conexión','No se están recibiendo nuevas lecturas. Se conserva la última información disponible.','off'],
    error:['No se pudo consultar el huerto','Inténtalo de nuevo para consultar su estado.','info'],
    invalid:['Hay una lectura inválida','Revisa el sensor indicado. Las otras lecturas mantienen su propia fecha y validez.','info'],
    unassigned:['Sin huerto asignado','Tu cuenta todavía no tiene un huerto asignado.','leaf']
  };
  function reading(raw, kind = 'humidity') {
    if (raw?.quality === 'invalid') return {value:null,quality:'invalid',at:raw.at || null};
    if (raw?.value == null) return {value:null,quality:'missing',at:raw?.at || null};
    const valid = typeof raw.value === 'number' && Number.isFinite(raw.value) && (kind !== 'humidity' || raw.value >= 0 && raw.value <= 100);
    return {value:valid ? raw.value : null,quality:valid ? 'valid' : 'invalid',at:raw.at || null};
  }
  function garden(data = {}) {
    const status = Object.hasOwn(states,data.status) ? data.status : 'error';
    return {
      status,name:typeof data.name === 'string' && data.name.trim() ? data.name : 'Mi huerto de habanero',
      updatedAt:data.updatedAt || null,
      plants:[1,2,3].map(id=>({id,name:`Planta ${id}`,reading:reading((Array.isArray(data.plants) ? data.plants : []).find(p=>p?.id===id)?.reading)})),
      temperature:reading(data.temperature,'temperature'),humidity:reading(data.humidity),
      tank:{state:['low','not-low'].includes(data.tank?.state) ? data.tank.state : 'unknown',at:data.tank?.at || null}
    };
  }
  function notices(data = {}) {
    if (!['ready','empty','loading','error'].includes(data.status)) return {status:'error',items:[]};
    const items = Array.isArray(data.items) ? data.items.filter(item=>item && typeof item.id === 'string').map(item=>({
      id:item.id,title:String(item.title || 'Aviso'),description:String(item.description || ''),
      recommendation:String(item.recommendation || 'Consulta el estado del huerto.'),zone:String(item.zone || 'Huerto'),
      createdAt:item.createdAt || null,resolvedAt:item.resolvedAt || null,
      importance:['high','medium','info'].includes(item.importance) ? item.importance : 'info',
      condition:item.condition === 'resolved' ? 'resolved' : 'active',read:item.read === true
    })) : [];
    return {status:data.status==='ready' && !items.length ? 'empty' : data.status,items};
  }
  return {
    destinations,states,garden,notices,reading,
    filterNotices(items,filter) { return items.filter(item=>filter==='all' || item.condition===filter); },
    profile(data={}) { return {email:typeof data.email==='string'?data.email:null,verified:typeof data.verified==='boolean'?data.verified:null,status:data.status==='ready'?'ready':'error'}; },
    date(value) { const d = new Date(value); return value && Number.isFinite(d.getTime()) ? d.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin registro'; },
    number(value) { return new Intl.NumberFormat('es-MX',{maximumFractionDigits:1}).format(value); }
  };
})();

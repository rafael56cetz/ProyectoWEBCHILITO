// Presentation contracts only; authorization and persisted state belong to Django.
const AppModel = (() => {
  const destinations = [
    {id:'huerto',label:'Mi huerto',icon:'grid'},
    {id:'telemetria',label:'Panel técnico',icon:'activity'},
    {id:'mantenimiento',label:'Mantenimiento',icon:'tool'},
    {id:'soporte',label:'Soporte técnico',icon:'support'},
    {id:'avisos',label:'Avisos',icon:'bell'},
    {id:'cuenta',label:'Mi cuenta',icon:'user'}
  ];
  const adminDestinations = [
    {id:'admin/flota',label:'Telemetría de flota',icon:'grid'},
    {id:'admin/soporte',label:'Consola remota',icon:'support'},
    {id:'admin/gobernanza',label:'Gobernanza de datos',icon:'shield'},
    {id:'admin/despliegues',label:'Despliegues y parámetros',icon:'activity'}
  ];
  const adminCapabilities={'admin/flota':'ver_flota','admin/soporte':'atender_soporte','admin/gobernanza':'ver_gobernanza','admin/despliegues':'gestionar_cambios'};
  const allowedAdmin=(session=AuthService.session)=>adminDestinations.filter(item=>(session.capabilities||[]).includes(adminCapabilities[item.id]));
  const states = {
    loading:['Consultando el huerto','Espera un momento.','clock'],
    waiting:['Sin mediciones','Las mediciones aparecerán cuando estén disponibles.','clock'],
    ready:['Datos disponibles','Consulta la fecha de cada lectura.','wifi'],
    stale:['Datos desactualizados','Las últimas lecturas se conservan como referencia; no describen necesariamente el estado actual.','clock'],
    offline:['Dispositivo sin conexión','No se están recibiendo nuevas lecturas. Se conserva la última información disponible.','off'],
    error:['No se pudo consultar el huerto','Inténtalo de nuevo para consultar su estado.','info'],
    invalid:['Hay una lectura inválida','Revisa el sensor indicado. Las otras lecturas mantienen su propia fecha y validez.','info'],
    unassigned:['Sin huerto asignado','Tu cuenta todavía no tiene un huerto asignado.','leaf']
  };
  const text = value => typeof value === 'string' && value.trim().length > 0;
  const dateValid = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value));
  const idValid = value => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value);
  function validReading(raw, kind='humidity') {
    if(!raw || !['missing','valid','invalid'].includes(raw.quality) || raw.at !== null && !dateValid(raw.at)) return false;
    if(raw.quality === 'missing') return raw.value === null && raw.at === null;
    if(raw.quality === 'invalid') return raw.value === null;
    return typeof raw.value === 'number' && Number.isFinite(raw.value) && dateValid(raw.at)
      && (kind !== 'humidity' || raw.value >= 0 && raw.value <= 100);
  }
  function reading(raw, kind='humidity') {
    if (!validReading(raw,kind)) return {value:null,quality:'invalid',at:null};
    return {value:raw.value,quality:raw.quality,at:raw.at};
  }
  function garden(data={}) {
    let status = Object.hasOwn(states,data.status) ? data.status : 'error';
    if(!['loading','error','unassigned'].includes(status)) {
      const plants = data.plants;
      if(!text(data.name) || data.updatedAt !== null && !dateValid(data.updatedAt)
        || !Array.isArray(plants) || plants.length !== 3 || ![1,2,3].every(id=>plants.filter(p=>p?.id===id).length===1)
        || plants.some(p=>!text(p.name) || !validReading(p.reading))
        || !validReading(data.temperature,'temperature') || !validReading(data.humidity)
        || !data.tank || !['low','not-low','unknown'].includes(data.tank.state)
        || data.tank.at !== null && !dateValid(data.tank.at)
        || data.tank.state === 'unknown' && data.tank.at !== null
        || data.tank.state !== 'unknown' && !dateValid(data.tank.at)) status = 'error';
    }
    const usable = !['loading','error','unassigned'].includes(status);
    const missing = () => ({value:null,quality:'missing',at:null});
    return {
      status,name:usable ? data.name : 'Mi huerto',
      updatedAt:usable ? data.updatedAt : null,
      plants:[1,2,3].map(id=>{ const plant=usable ? data.plants.find(p=>p.id===id) : null;
        return {id,zoneId:plant?.zoneId || null,name:plant?.name || `Planta ${id}`,crop:plant?.crop || '',reading:plant ? reading(plant.reading) : missing()}; }),
      temperature:usable ? reading(data.temperature,'temperature') : missing(),humidity:usable ? reading(data.humidity) : missing(),
      tank:usable ? {state:data.tank.state,at:data.tank.at} : {state:'unknown',at:null}
    };
  }
  function notice(raw) {
    if(!raw || !idValid(raw.id) || !text(raw.title) || !text(raw.description) || !text(raw.zone)
      || typeof raw.recommendation !== 'string' || !dateValid(raw.createdAt)
      || !['high','medium','info'].includes(raw.importance) || !['active','resolved'].includes(raw.condition)
      || typeof raw.read !== 'boolean') return null;
    if(raw.condition === 'active' && raw.resolvedAt !== null) return null;
    if(raw.condition === 'resolved' && (!dateValid(raw.resolvedAt) || Date.parse(raw.resolvedAt) < Date.parse(raw.createdAt))) return null;
    return {id:raw.id,title:raw.title,description:raw.description,recommendation:raw.recommendation,
      zone:raw.zone,createdAt:raw.createdAt,resolvedAt:raw.resolvedAt,importance:raw.importance,condition:raw.condition,read:raw.read};
  }
  function notices(data={}) {
    if(['loading','error','unassigned','not-found'].includes(data.status)) return {status:data.status,items:[]};
    if(!['ready','empty'].includes(data.status) || !Array.isArray(data.items)) return {status:'error',items:[]};
    const items=data.items.map(notice);
    if(items.some(item=>!item) || new Set(items.map(item=>item.id)).size !== items.length
      || data.status==='empty' && items.length) return {status:'error',items:[]};
    return {status:items.length ? 'ready' : 'empty',items};
  }
  return {
    destinations,adminDestinations,adminCapabilities,allowedAdmin,adminHome:(session)=>allowedAdmin(session)[0]?.id||'huerto',states,garden,notices,notice,reading,idValid,
    isPrivate(screen) { return screen === 'admin' || destinations.some(item=>item.id===screen); },
    filterNotices(items,filter) { return items.filter(item=>filter==='all' || item.condition===filter); },
    profile(data={}) { return data.status==='ready' && text(data.email) && data.verified===true
      ? {email:data.email,verified:true,status:'ready'} : {email:null,verified:null,status:'error'}; },
    date(value) { const d = new Date(value); return value && Number.isFinite(d.getTime()) ? d.toLocaleString('es-MX',{dateStyle:'medium',timeStyle:'short'}) : 'Sin registro'; },
    number(value) { return new Intl.NumberFormat('es-MX',{maximumFractionDigits:1}).format(value); }
  };
})();

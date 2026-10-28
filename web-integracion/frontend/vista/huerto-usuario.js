const UserGardenViews = (() => {
  const esc = authEscape;
  const num = value => Number.isFinite(value) ? AppModel.number(value) : '—';
  const date = value => AppViews.date(value);
  const value = (reading,unit='') => reading?.value==null ? '—' : `${esc(num(reading.value))}${unit?`<small>${unit}</small>`:''}`;
  const button=(action,label,primary=false,attrs='')=>`<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-user-action="${action}" ${attrs}>${label}</button>`;
  const intro=(title,text)=>AppViews.heading(title,text);
  const section=(title,copy='')=>`<div class="user-section-heading"><div><h2>${title}</h2>${copy?`<p>${copy}</p>`:''}</div></div>`;
  const actions='<div id="user-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>';
  const dialog='<dialog class="bento-panel app-dialog user-dialog" aria-labelledby="user-dialog-title" aria-describedby="user-dialog-copy"><div data-user-dialog-content></div></dialog>';
  function emptyState(data) {
    if(data.garden.status==='loading')return AppViews.state('Consultando el huerto','Espera un momento.',true);
    if(data.garden.status==='error')return `<section class="bento-panel user-empty"><h2>No se pudo consultar el huerto</h2><p>Inténtalo de nuevo para consultar sus lecturas y acciones.</p>${button('refresh','Reintentar',true)}</section>`;
    if(data.garden.status==='unassigned')return AppViews.state('Sin huerto asignado','Asocia tu equipo a tu cuenta para consultar sus mediciones.')+AppViews.gardenLink();
    return '';
  }
  function statusLine(data) {
    const g=data.garden;
    return `<div class="user-status-line"><p>${esc(AppModel.states[g.status]?.[0]||'Sin información')}</p><p>Última lectura: ${g.updatedAt?date(g.updatedAt):'Sin registros'}</p></div>${['offline','stale','invalid'].includes(g.status)?`<p class="user-data-warning" role="status">${esc(AppModel.states[g.status][1])}</p>`:''}`;
  }
  const tankText=data=>data.garden.tank.state==='low'?'Nivel bajo':data.garden.tank.state==='not-low'?'Nivel adecuado':'Sin lectura';
  const lampText=data=>data.connection?.wifi==null||data.connection?.mqtt==null?'Sin información':data.garden.status==='offline'?'Sin conexión':data.lampRequest==='lamp-off'?'Apagado solicitado':data.lampRequest==='lamp-auto'?'Control solicitado':data.connection?.wifi&&data.connection?.mqtt?'En línea':'Sin conexión';
  function summary(data) {
    const problem=emptyState(data);if(problem)return intro('Mi huerto','El cuidado de tu huerto, en un mismo lugar.')+problem;
    const empty = reading => reading.value == null && reading.quality === 'missing';
    const note = reading => empty(reading) ? '' : `<p class="reading-note">${AppViews.readingNote(reading)}</p>`;
    const quality = reading => reading.quality === 'invalid' ? 'Lectura inválida' : 'Lectura registrada';
    const g=data.garden, canControl=!['error','unassigned','loading'].includes(g.status), diagnosis=data.garden.status==='ready'?(data.diagnosis||{}):{}, moisture=data.soil?.moisture;
    return `${intro('Mi huerto','El cuidado de tu huerto, en un mismo lugar.')}${statusLine(data)}
      <section class="user-summary-metrics" aria-label="Resumen del huerto">
        <article class="bento-panel user-metric"><span class="user-metric-icon">${icon('tank')}</span><h2>Depósito de agua</h2><strong class="user-status-value">${tankText(data)}</strong><p>Capacidad del depósito: 19 L</p></article>
        <article class="bento-panel user-metric"><span class="user-metric-icon">${icon('drop')}</span><h2>Humedad del sustrato</h2><strong>${value(moisture,'%')}</strong><p>${moisture?.value==null?'Aún no hay lecturas disponibles.':'Lectura calibrada del sensor'}</p></article>
        <article class="bento-panel user-metric"><span class="user-metric-icon">${icon('temp')}</span><h2>Ambiente</h2><strong>${value(g.temperature,'°C')}</strong><p>Humedad relativa: ${value(g.humidity,'%')}</p></article>
        <article class="bento-panel user-metric"><span class="user-metric-icon">${icon('wifi')}</span><h2>Circuito y actuadores</h2><strong class="user-status-value">${lampText(data)}</strong><p>${data.lampRequest?'Esperando confirmación del equipo.':'Bombas y lámpara'}</p></article>
      </section>
    <section aria-labelledby="plants-title"><div class="panel-heading"><h2 id="plants-title">Tus tres plantas</h2><p>Humedad del sustrato por planta</p></div><div class="plant-grid">
      ${g.plants.map(plant=>`<article class="plant-card">${empty(plant.reading) ? '' : `<div class="card-top">${badge(quality(plant.reading))}</div>`}<div class="plant-name"><div><h3>${authEscape(plant.name)}</h3><p>${esc(plant.crop||'Cultivo sin registrar')}</p></div><div class="plant-pedestal">${plantDrawing(plant.id)}</div></div><div class="plant-reading"><span>${icon('drop')}Humedad del sustrato</span>${AppViews.reading(plant.reading,'%')}<div class="sensor-track" aria-hidden="true">${plant.reading.value == null ? '' : `<span style="width:${plant.reading.value}%"></span>`}</div></div>${note(plant.reading)}</article>`).join('')}
    </div></section>
      <section class="bento-panel user-diagnosis" aria-labelledby="diagnosis-title"><div class="user-diagnosis-mark">${icon('sparkle')}</div><div class="user-diagnosis-copy"><h2 id="diagnosis-title">Diagnóstico inteligente</h2><h3>${esc(diagnosis.title||'Sin diagnóstico disponible')}</h3><p>${esc(diagnosis.text||'Las recomendaciones aparecerán aquí cuando estén disponibles las lecturas de tu huerto.')}</p>${diagnosis.next?`<div class="user-next-action"><span>Próxima acción estimada</span><strong>${esc(diagnosis.next)}</strong></div>`:''}</div></section>
      ${section('Acciones a tu alcance','Registra los cuidados que realizas en tu huerto.')}
      <section class="user-care-grid" aria-label="Cuidados del huerto">
        ${care('tank','Rellenar depósito','Añade agua limpia cuando el nivel sea bajo y registra la recarga al terminar.',button('record-refill','Registrar recarga'))}
        ${care('leaf','Revisar sustrato','Comprueba el drenaje y el estado de la mezcla con perlita.','<a class="button btn-liquid-light" href="#mantenimiento/sustrato">Ver guía de cuidado</a>')}
        ${care('leaf','Germinación y cosecha','Germina fuera del sistema y cosecha los frutos maduros con utensilios limpios.',button('record-harvest','Registrar cosecha'))}
      </section>
      <section class="bento-panel user-operating"><div><h2>Control de lámpara</h2><p>${data.lampRequest==='lamp-off'?'Hay una solicitud de apagado. Puedes restablecer el control habitual de la lámpara.':'Solicita el apagado de la lámpara cuando necesites intervenir en el huerto.'}</p></div>${button(data.lampRequest==='lamp-off'?'lamp-auto':'lamp-off',data.lampRequest==='lamp-off'?'Restaurar control':'Apagar lámpara',false,canControl?'':'disabled')}</section>
      ${!canControl?'<p class="user-small-copy">Control remoto no disponible. Esperando conexión del equipo.</p>':''}<p class="user-safety-copy">El control remoto depende de Wi-Fi y MQTT. Ante una emergencia, utiliza el paro físico del equipo.</p>
      <section class="user-support-callout"><div>${icon('shield')}<div><h2>¿Algo no responde como debería?</h2><p>Reporta un problema y autoriza el diagnóstico técnico de tu huerto.</p></div></div><a class="button btn-liquid-brand" href="#soporte">Solicitar soporte técnico</a></section>`;
  }
  function care(ico,title,copy,action) {return `<article class="bento-panel user-care"><span class="icon-medallion">${icon(ico)}</span><h3>${title}</h3><p>${copy}</p>${action}</article>`;}
  function chart(title,readings,unit,range,id) {
    const points=Array.isArray(readings)?readings.filter(r=>Number.isFinite(r.value)&&Number.isFinite(Date.parse(r.at))).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)):[];
    if(points.length<2)return `<article class="bento-panel user-chart"><h2>${title}</h2><div class="user-chart-empty"><p>Aún no hay registros para este periodo.</p></div></article>`;
    const vals=points.map(x=>x.value);const min=Math.min(...vals),max=Math.max(...vals),spread=max-min||1,lo=min-spread*.18,hi=max+spread*.18;
    const x=i=>56+i/(points.length-1)*530,y=v=>180-(v-lo)/(hi-lo)*144;
    const grid=[0,.5,1].map(t=>{const yy=36+144*t;return `<line x1="56" y1="${yy}" x2="586" y2="${yy}"/><text x="44" y="${yy+4}" text-anchor="end">${esc(num(hi-(hi-lo)*t))}</text>`;}).join('');
    const labels=range==='1h'?['Hace 1 h','Hace 30 min','Ahora']:range==='24h'?['Hace 24 h','Hace 12 h','Ahora']:['Hace 7 días','Hace 3 días','Ahora'];
    return `<article class="bento-panel user-chart"><div class="user-chart-heading"><h2>${title}</h2><p>${esc(num(vals[vals.length-1]))}<span> ${unit}</span></p></div><svg class="user-history-chart" viewBox="0 0 620 228" role="img" aria-labelledby="chart-${id}-title chart-${id}-desc"><title id="chart-${id}-title">${title}</title><desc id="chart-${id}-desc">${points.length} registros en ${range==='7d'?'los últimos 7 días':range==='24h'?'las últimas 24 horas':'la última hora'}. Último valor: ${esc(num(vals[vals.length-1]))} ${unit}.</desc><g class="user-chart-grid">${grid}</g><polyline class="user-chart-line" points="${points.map((p,i)=>`${x(i)},${y(p.value)}`).join(' ')}"/><circle class="user-chart-dot" cx="${x(points.length-1)}" cy="${y(vals[vals.length-1])}" r="4"/><g class="user-chart-labels">${labels.map((l,i)=>`<text x="${[56,321,586][i]}" y="216" text-anchor="${['start','middle','end'][i]}">${l}</text>`).join('')}</g></svg></article>`;
  }
  function technical(data) {
    const problem=emptyState(data);if(problem)return intro('Panel técnico','Lecturas, conectividad e historial de tu huerto.')+problem;
    const g=data.garden,h=data.history||{};
    return `${intro('Panel técnico','Lecturas, conectividad e historial de tu huerto.')}${statusLine(data)}
    <section class="user-technical-metrics" aria-label="Lecturas técnicas">
      <article class="bento-panel user-metric"><h2>Sensor capacitivo v1.2</h2><strong>${num(data.soil?.adc)}<small> ADC</small></strong><p>Lectura analógica bruta · escala 0–4095</p></article>
      <article class="bento-panel user-metric"><h2>Humedad calibrada</h2><strong>${value(data.soil?.moisture,'%')}</strong><p>Humedad del sustrato</p></article>
      <article class="bento-panel user-metric"><h2>Ambiente · SHT31</h2><strong>${value(g.temperature,'°C')}</strong><p>Humedad relativa: ${value(g.humidity,'%')}</p></article>
    </section>
    <div class="user-chart-toolbar"><h2>Histórico de lecturas</h2><div class="user-range-control" role="group" aria-label="Periodo del histórico">${[['1h','1 h'],['24h','24 h'],['7d','7 días']].map(([r,l])=>button('range',l,data.range===r,`data-range="${r}" aria-pressed="${data.range===r}"`)).join('')}</div></div>
    <section class="user-chart-grid-layout" aria-label="Gráficas de sensores">${chart('Humedad del sustrato · ADC',h.soil,'ADC',data.range,'soil')}${chart('Temperatura ambiental',h.temperature,'°C',data.range,'temperature')}${chart('Humedad relativa',h.humidity,'%',data.range,'humidity')}
    <article class="bento-panel user-connectivity"><h2>Depósito y conectividad</h2><dl class="user-facts"><div><dt>Flotador</dt><dd>${tankText(data)}</dd></div><div><dt>Capacidad del depósito</dt><dd>19 L</dd></div><div><dt>Wi-Fi</dt><dd>${data.connection?.wifi==null?'Sin información':data.connection.wifi?'Conectado':'Sin conexión'}</dd></div><div><dt>Mosquitto / MQTT</dt><dd>${data.connection?.mqtt==null?'Sin información':data.connection.mqtt?'Disponible':'No disponible'}</dd></div></dl><p>El flotador detecta nivel bajo; no mide el volumen de agua.</p></article></section>
    ${section('Lecturas por planta','Humedad del sustrato en cada uno de los tres compartimentos.')}
    <section class="bento-panel user-plant-readings" aria-label="Humedad por planta">${g.plants.map(p=>`<div><h3>${esc(p.name)}</h3><strong>${value(p.reading,'%')}</strong><p>${p.reading.at?date(p.reading.at):'Sin lecturas'}</p></div>`).join('')}</section>
    <div class="user-section-heading"><div><h2>Bitácora de actuadores</h2><p>Órdenes, resultados y origen de cada acción.</p></div>${button('refresh','Actualizar bitácora')}</div>
    <section class="bento-panel user-log-panel">${commandLog(data)}</section>
    <section class="bento-panel user-operating"><div><h2>Solicitar riego puntual</h2><p>Registra la solicitud y consulta su estado en la bitácora. El equipo debe confirmar la operación antes de considerarla realizada.</p></div>${button('water','Solicitar riego',true,!['error','unassigned','loading'].includes(g.status)?'':'disabled')}</section><p class="user-safety-copy">Una solicitud no confirma que la bomba se haya activado. Ante una emergencia, utiliza el paro físico del equipo.</p>`;
  }
  function commandLog(data) {
    if(!data.commands?.length)return '<div class="user-empty-inline"><p>No hay órdenes registradas.</p><p>Las solicitudes y la respuesta del equipo aparecerán aquí.</p></div>';
    return `<div class="user-table-scroll" tabindex="0" role="region" aria-label="Historial de órdenes"><table class="user-table"><thead><tr><th scope="col">Fecha y hora</th><th scope="col">Actuador</th><th scope="col">Orden / resultado</th><th scope="col">Origen</th><th scope="col">Estado</th></tr></thead><tbody>${data.commands.map(e=>`<tr><td>${date(e.at)}</td><td>${esc(e.actuator)}</td><td>${esc(e.action)}</td><td>${esc(e.origin)}</td><td>${esc(e.status)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function maintenance(data) {
    const problem=emptyState(data);if(problem)return intro('Mantenimiento del huerto','Registra los cuidados que realizas y consulta tu historial.')+problem;
    return `${intro('Mantenimiento del huerto','Registra los cuidados que realizas y consulta tu historial.')}
    <section class="user-maintenance-grid" aria-label="Tareas de mantenimiento"><h2 class="sr-only">Tareas de mantenimiento</h2>
      ${care('tank','Nivel de agua',`Estado del depósito: ${tankText(data).toLowerCase()}. Rellena con agua limpia y registra la recarga al terminar.`,button('record-refill','Ya rellené el depósito',true))}
      ${care('leaf','Sustrato y perlita','Comprueba el drenaje y evita que la mezcla quede compactada.',`<details class="user-care-guide" id="user-substrate-guide"><summary>Ver guía de cuidado</summary><p>Revisa si el agua drena con facilidad. Si notas compactación, malos olores o acumulación de sales, revisa la mezcla antes de volver a regar. La perlita ayuda a conservar la aireación.</p></details>${button('record-substrate','Marcar revisión hecha')}`)}
      ${care('leaf','Germinación externa','Germina las semillas fuera del sistema. Trasplanta cuando las plántulas sean resistentes.',button('record-germination','Registrar germinación'))}
      ${care('leaf','Cosecha','Revisa la madurez del fruto y cosecha con guantes y utensilios limpios.',button('record-harvest','Registrar cosecha'))}
      ${care('shield','Inspección visual','Comprueba que cables y conexiones estén secos, que no haya fugas y que la lámpara esté estable.',button('record-inspection','Registrar inspección'))}
      <article class="bento-panel user-care"><span class="icon-medallion">${icon('clock')}</span><h3>Registro reciente</h3><p>${data.maintenance?.length?`${esc(data.maintenance[0].label)} · ${date(data.maintenance[0].at)}`:'Aún no has registrado tareas de mantenimiento.'}</p><a class="button btn-liquid-light" href="#mantenimiento/historial">Ver historial</a></article>
    </section>${section('Historial de mantenimiento')}
    <section class="bento-panel user-maintenance-history" id="user-maintenance-history" tabindex="-1">${data.maintenance?.length?`<ol class="user-history-list">${data.maintenance.map(e=>`<li><span>${icon('check')}</span><div><h3>${esc(e.label)}</h3><p>${date(e.at)}</p></div></li>`).join('')}</ol>`:'<p>No hay tareas registradas. Al completar un cuidado, regístralo para conservar su fecha.</p>'}</section>`;
  }
  function support(data) {
    const problem=emptyState(data);if(problem)return intro('Soporte técnico','Reporta un problema y controla el acceso técnico a tu huerto.')+problem;
    const p=data.permission;
    const permissionTitle=p?'Autorización activa':data.permissionState==='revoked'?'Autorización revocada':data.permissionState==='expired'?'Autorización vencida':'Sin autorización activa';
    return `${intro('Soporte técnico','Reporta un problema y controla el acceso técnico a tu huerto.')}
    <div class="user-support-layout"><section class="bento-panel user-support-form"><h2>Reportar un incidente</h2><p>Selecciona el problema que presenta tu huerto.</p><form data-user-support-form><label for="user-incident">Tipo de problema</label><select id="user-incident" name="incident" required>${Object.entries(UserGardenService.incidents).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join('')}</select><p>La autorización permite consultar estados de GPIO, errores de MQTT y solicitar el reinicio del microcontrolador durante 24 horas.</p><button type="submit" class="button btn-liquid-brand" ${data.supportAvailable?'':'disabled aria-describedby="support-service-status"'}>Reportar y generar token temporal</button>${data.supportAvailable?'':'<p class="user-small-copy" id="support-service-status">Emisión de tokens no disponible.</p>'}</form>
    ${p?`<section class="user-token" aria-labelledby="support-token-title"><h3 id="support-token-title">Tu token de soporte</h3>${p.token?`<p class="user-token-code">${esc(p.token)}</p>`:'<p>El token solo se mostró al emitir esta autorización. No se recupera desde el historial. Si no lo conservas, revoca y genera una autorización nueva.</p>'}<p>Reporte ${esc(p.ticket)} · ${esc(p.incident)}</p><p>Vence el ${date(new Date(p.expiresAt).toISOString())}.</p>${p.token?button('copy-token','Copiar token'):''}<p class="user-small-copy">Compártelo únicamente con el personal que atenderá tu reporte.</p></section>`:''}</section>
    <section class="bento-panel user-permission"><span class="icon-medallion">${icon('shield')}</span><h2>Estado de la autorización</h2><h3>${permissionTitle}</h3><p>${p?'La autorización está vigente para este reporte. Puedes revocarlo cuando quieras.':'El acceso técnico permanece cerrado hasta que lo autorices expresamente.'}</p><dl class="user-facts"><div><dt>Duración del permiso</dt><dd>24 horas</dd></div><div><dt>Alcance</dt><dd>Diagnóstico del incidente</dd></div><div><dt>Datos personales y ubicación</dt><dd>Fuera del alcance</dd></div></dl>${button('revoke','Revocar autorización',false,`data-danger="true" ${!p||!data.supportAvailable?'disabled':''}`)}</section></div>${section('Historial de reportes')}<section class="bento-panel user-maintenance-history">${data.reports?.length?`<ol class="user-history-list">${data.reports.map(r=>`<li><span>${icon('support')}</span><div><h3>${esc(UserGardenService.incidents[r.incident]||r.incident)}</h3><p>Reporte ${esc(r.id)}</p><p>${date(r.createdAt)} · ${esc({active:'Autorización activa',revoked:'Autorización revocada',expired:'Autorización vencida',closed:'Sin autorización'}[r.permissionState]||'Sin autorización')}</p></div></li>`).join('')}</ol>`:'<p>No hay reportes registrados.</p>'}</section>`;
  }
  function confirmation(action) {
    if(action==='support')return `<h2 id="user-dialog-title">Autorizar soporte técnico</h2><p id="user-dialog-copy">El token permite consultar los estados de GPIO, los errores MQTT y solicitar el reinicio del microcontrolador durante 24 horas. Puedes revocarlo antes de su vencimiento.</p><label class="user-consent"><input type="checkbox" id="user-support-consent"><span>Autorizo expresamente el diagnóstico remoto de este incidente con el alcance indicado.</span></label><div class="app-dialog-actions">${button('cancel-dialog','Cancelar')}${button('confirm-dialog','Confirmar y generar token',true,'disabled')}</div>`;
    const titles={water:'¿Solicitar riego puntual?','lamp-off':'¿Solicitar el apagado de la lámpara?','lamp-auto':'¿Restaurar el control habitual de la lámpara?'};
    return `<h2 id="user-dialog-title">${titles[action]}</h2><p id="user-dialog-copy">Se registrará una solicitud para tu huerto. La ejecución depende del servicio del equipo. El estado permanecerá sin confirmar hasta recibir la respuesta del equipo.</p><div class="app-dialog-actions">${button('cancel-dialog','Cancelar')}${button('confirm-dialog',action==='water'?'Solicitar riego':action==='lamp-off'?'Solicitar apagado':'Restaurar control',true)}</div>`;
  }
  return { chart,render(screen,data) {return actions+({huerto:summary,telemetria:technical,mantenimiento:maintenance,soporte:support}[screen]||summary)(data)+dialog;},confirmation };
})();

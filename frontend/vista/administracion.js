const AdminViews = (() => {
  const esc=authEscape, date=AppViews.date;
  const button=(action,label,primary=false,attrs='')=>`<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-admin-action="${action}" ${attrs}>${label}</button>`;
  const heading=AppViews.heading;
  const available=(value,missing='Sin lectura')=>value===null||value===undefined||value===''?missing:esc(String(value));
  const metricValue=value=>value===null||value===undefined?'—':esc(AppModel.number(value));
  const section=(title,copy='')=>`<div class="user-section-heading"><div><h2>${title}</h2>${copy?`<p>${copy}</p>`:''}</div></div>`;
  const metric=(label,value,unit,copy,ico='activity')=>`<article class="bento-panel user-metric"><span class="user-metric-icon">${icon(ico)}</span><h2>${label}</h2><strong>${value}<small>${unit}</small></strong><p>${copy}</p></article>`;
  const table=(label,headers,rows)=>`<div class="user-table-scroll" tabindex="0" role="region" aria-label="${esc(label)}"><table class="user-table admin-table"><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}">Sin registros disponibles.</td></tr>`}</tbody></table></div>`;
  const fact=(label,value)=>`<div><dt>${label}</dt><dd>${value}</dd></div>`;
  const note=text=>`<p class="admin-service-note">${text}</p>`;
  const messages='<div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>';
  const dialog='<dialog class="bento-panel app-dialog admin-dialog" aria-labelledby="admin-dialog-title" aria-describedby="admin-dialog-copy"><div data-admin-dialog-content></div></dialog>';
  function fleet(data) {
    const series=values=>Array.isArray(values)?values.filter(reading=>reading&&Number.isFinite(reading.value)&&Number.isFinite(Date.parse(reading.at))):[];
    const metrics=data.metrics||{};
    return heading('Telemetría de flota','Indicadores agregados y estado operativo de los dispositivos vinculados.')+
    `<div class="user-status-line"><p>Vista agregada de la plataforma</p><p>${data.at?`Última consulta: ${date(data.at)}`:'Sin lecturas disponibles'}</p></div>
    <section class="user-summary-metrics" aria-label="Estado de la flota">
      ${metric('Nodos reportando',metricValue(metrics.reporting),metrics.total==null?'':'/ '+metricValue(metrics.total),'Sin información de disponibilidad','wifi')}
      ${metric('Humedad media',metricValue(metrics.soilHumidity),metrics.soilHumidity==null?'':'%','Sin lecturas disponibles','drop')}
      ${metric('Evaporación estimada',metricValue(metrics.evaporation),metrics.evaporation==null?'':'mm/día','Sin estimación disponible','sun')}
      ${metric('Alertas de hardware',metricValue(metrics.hardwareAlerts),'','Sin información disponible','info')}
    </section>
    ${section('Tendencias ambientales agregadas','Últimos 7 días. Sin series de un hogar individual.')}
    <section class="user-chart-grid-layout" aria-label="Tendencias agregadas">
      ${UserGardenViews.chart('Humedad media del sustrato',series(data.trends.soil),'%','7d','fleet-soil')}
      ${UserGardenViews.chart('Humedad relativa media',series(data.trends.humidity),'%','7d','fleet-rh')}
    </section>
    <div class="user-section-heading"><div><h2>Identidades y dispositivos vinculados</h2><p>Identificadores operativos y conexión al broker Mosquitto.</p></div>${button('refresh','Actualizar dispositivos')}</div>
    <section class="bento-panel admin-table-panel">${table('Dispositivos vinculados',['Device_ID','User_ID','Mosquitto','Último heartbeat'],data.nodes.map(n=>`<tr><th scope="row">${esc(n.device)}</th><td>${esc(n.user)}</td><td><span class="admin-connection ${n.connected?'online':'offline'}">${n.connected?'En línea':'Sin conexión'}</span></td><td>${esc(n.heartbeat)}</td></tr>`))}<p class="admin-caption">Se muestra el vínculo operativo mínimo. No se incluyen contraseñas ni ubicación.</p></section>
    ${section('Telemetría para evaluación de IA','Patrones agregados para evaluar el riego predictivo y el desgaste del hardware.')}
    <section class="user-technical-metrics" aria-label="Indicadores de evaluación">
      ${metric('Evaporación · mezcla con perlita',metricValue(metrics.perliteEvaporation),metrics.perliteEvaporation==null?'':'mm/día','Sin estimación disponible','sun')}
      ${metric('Vida mediana del sensor capacitivo v1.2',metricValue(metrics.sensorLife),metrics.sensorLife==null?'':'meses','Sin estimación disponible','activity')}
      ${metric('Órdenes de mini bombas',metricValue(metrics.pumpOrders),metrics.pumpOrders==null?'':'/ huerto / día','Sin registros disponibles','drop')}
    </section>
    ${section('Correlaciones por temperatura','Ventanas ambientales utilizadas para evaluar el modelo.')}
    <section class="bento-panel admin-table-panel">${table('Correlaciones agregadas',['Temperatura media','Evaporación estimada','Órdenes de bomba','Uso en el modelo'],(data.correlations||[]).map(row=>`<tr>${row.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`))}<p class="admin-caption">La evaluación utiliza agregados. Las correlaciones lumínicas requieren una medición verificable de luz.</p></section>`;
  }
  function remote(data) {
    const ticket=data.selected;
    return heading('Consola remota','Atiende cada reporte con la autorización temporal de la persona usuaria.')+
    `<div class="user-section-heading"><div><h2>Buzón de reportes</h2><p>Los registros técnicos se abren únicamente con el token del caso seleccionado.</p></div>${button('refresh','Actualizar reportes')}</div>
    <section class="bento-panel admin-table-panel">${data.tickets.length?table('Reportes de soporte',['Reporte','Device_ID','Incidente','Estado','Acción'],data.tickets.map(t=>`<tr${ticket?.id===t.id?' class="admin-selected-row"':''}><th scope="row">${esc(t.id)}</th><td>${available(t.device,'Sin dispositivo asignado')}</td><td>${esc(t.incident)}</td><td>${esc(t.status)}</td><td>${button('open-ticket','Abrir',false,`data-ticket="${esc(t.id)}" aria-label="Abrir reporte ${esc(t.id)}"`)}</td></tr>`)):'<p>No hay reportes registrados.</p>'}</section>
    ${section('Detalle y autorización')}
    <section class="bento-panel admin-ticket-detail" tabindex="-1" id="admin-ticket-detail">
      ${ticket?`<h2>Reporte ${esc(ticket.id)}</h2><dl class="user-facts admin-ticket-facts">${fact('Device_ID',available(ticket.device,'Sin dispositivo asignado'))}${fact('User_ID',available(ticket.user,'Sin identificador disponible'))}${fact('Incidente',esc(ticket.incident))}${fact('Creado',date(ticket.createdAt))}</dl><p>El diagnóstico queda limitado a este incidente. El token de otro reporte no concede acceso.</p>
      ${button('request-token','Solicitar token temporal')}
      <form data-admin-token-form class="admin-token-form"><label for="admin-token">Token compartido por la persona usuaria</label><div class="admin-input-row"><input id="admin-token" name="token" type="text" required maxlength="80" autocomplete="off" spellcheck="false" autocapitalize="characters"><button class="button btn-liquid-brand" type="submit">Validar token</button></div></form>
      <p class="admin-access-state">${data.remote?`Acceso autorizado hasta el ${date(new Date(data.remote.expiresAt).toISOString())}.`:'Acceso técnico bloqueado. Valida una autorización vigente para continuar.'}</p>`:'<h2>Selecciona un reporte</h2><p>Abre un caso del buzón para consultar su detalle y validar el token correspondiente.</p>'}
    </section>
    ${data.remote?diagnostics(data):''}
    ${section('Alcance del acceso remoto')}
    <section class="bento-panel admin-governance-list"><dl class="admin-policy-list">
      ${fact('Inspeccionar GPIO','Estados eléctricos relevantes para bomba, sensores y lámpara.')}
      ${fact('Revisar errores MQTT','Registros técnicos recientes del dispositivo autorizado.')}
      ${fact('Solicitar reinicio','Requiere una autorización vigente y confirmación de la operación.')}
      ${fact('Fuera del alcance','Acceso permanente, contraseñas, ubicación e historial de cultivo.')}
    </dl></section>`;
  }
  function diagnostics(data) {
    return `${section('Diagnóstico del nodo autorizado',available(data.selected.device,'Sin dispositivo asignado')+' · '+esc(data.selected.id))}
    <section class="bento-panel admin-diagnostics"><h2>Estados de GPIO y sensores</h2><dl class="admin-gpio-grid">${data.diagnostics.pins.map(([k,v])=>fact(esc(k),available(v))).join('')}</dl><h3>Registros recientes MQTT</h3>${data.diagnostics.logs.length?`<pre class="admin-logs" tabindex="0" aria-label="Registros técnicos del reporte"><code>${esc(data.diagnostics.logs.join('\n'))}</code></pre>`:'<p>No hay registros técnicos disponibles.</p>'}<div class="app-actions">${button('refresh-diagnostics','Actualizar diagnóstico')}${button('restart-node','Reiniciar microcontrolador',false,'data-danger="true"')}${button('close-remote','Cerrar sesión remota')}</div>${note('Lecturas de hardware sin servicio conectado. Una solicitud de reinicio requiere la confirmación del dispositivo.')}</section>`;
  }
  function governance() {
    return heading('Gobernanza de datos','Alcance de la telemetría, el consentimiento y el acceso técnico.')+
    `<div class="admin-two-columns"><section class="bento-panel admin-governance-list"><h2>Principios de acceso y telemetría</h2><dl class="admin-policy-list">
      ${fact('Minimización de datos','Solo métricas técnicas relevantes. La analítica utiliza datos agregados y anonimizados.')}
      ${fact('Consentimiento granular','El soporte requiere una autorización explícita para un reporte y un dispositivo.')}
      ${fact('Caducidad y revocación','El token dura 24 horas y la persona usuaria puede revocarlo antes.')}
      ${fact('Trazabilidad','Cada acceso y operación debe conservar actor, permiso, fecha y resultado.')}
      ${fact('Evaluación responsable de IA','Los modelos utilizan patrones agregados. Los identificadores de hogares quedan fuera de sus características.')}
    </dl></section><section class="bento-panel admin-governance-list"><span class="icon-medallion">${icon('shield')}</span><h2>Modelo de acceso</h2><dl class="user-facts">
      ${fact('Acceso por defecto','Denegado')}${fact('Duración del token','24 horas')}${fact('Datos de flota','Agregados')}${fact('Soporte remoto','Solo con consentimiento')}
    </dl>${note('La autorización y la auditoría definitivas requieren validación en el servidor.')}</section></div>`;
  }
  function deployments(data) {
    return heading('Despliegues y parámetros','Versiones del modelo, conocimiento del asistente y mantenimiento de plataforma.')+
    `<div class="admin-two-columns"><section class="bento-panel admin-release"><h2>Modelo de aprendizaje automático</h2><dl class="user-facts">${fact('Versión en servicio',available(data.activeVersion,'Sin versión disponible'))}</dl>
      <form data-admin-release-form><label for="admin-release-type">Tipo de actualización</label><select id="admin-release-type" name="type">${Object.entries(AdminService.releaseTypes).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select>
      <label for="admin-release-version">Versión destino</label><input id="admin-release-version" name="version" type="text" required minlength="3" maxlength="64" pattern="[a-zA-Z0-9][a-zA-Z0-9._\\-]{2,63}" autocomplete="off" spellcheck="false">
      <label for="admin-release-notes">Notas del despliegue</label><textarea id="admin-release-notes" name="notes" rows="4" maxlength="2000"></textarea>
      <div class="app-actions"><button type="submit" class="button btn-liquid-light">Validar versión</button>${button('publish','Publicar modelo',true,'disabled')}</div><p id="admin-release-state" class="admin-inline-status" role="status">Valida la versión antes de solicitar su publicación.</p></form>
      ${note('Servicio de despliegue sin conexión. Las solicitudes no alteran la versión en servicio.')}
    </section><div><section class="bento-panel admin-knowledge"><h2>Base de conocimientos</h2><form data-admin-knowledge-form><label for="admin-knowledge">Contenido del asistente y metadatos globales</label><textarea id="admin-knowledge" name="knowledge" rows="8" minlength="20" maxlength="10000" required>${esc(data.knowledge)}</textarea><dl class="user-facts">${fact('Versión del borrador',data.knowledgeVersion?'KB-'+data.knowledgeVersion:'Sin versión disponible')}${fact('Caracteres editados','<span id="admin-knowledge-count">'+data.knowledge.length+'</span>')}</dl><button class="button btn-liquid-brand" type="submit">Guardar metadatos</button></form></section>
    <section class="bento-panel admin-platform"><h2>Mantenimiento de plataforma</h2><p>Solicita un reinicio controlado para aplicar parches o mantenimiento.</p>${button('restart-platform','Solicitar reinicio',false,'data-danger="true"')}${note('La solicitud queda sin confirmación mientras el servicio esté desconectado.')}</section></div></div>
    ${data.releases.length?section('Solicitudes de publicación')+`<section class="bento-panel admin-table-panel">${table('Solicitudes de publicación',['Fecha','Versión','Tipo','Estado'],data.releases.map(r=>`<tr><td>${date(r.at)}</td><td>${esc(r.version)}</td><td>${esc(AdminService.releaseTypes[r.type])}</td><td>${esc(r.status)}</td></tr>`))}</section>`:''}
    ${section('Registro de cambios y auditoría')}
    <section class="bento-panel admin-audit">${data.audit.length?`<ol class="user-history-list">${data.audit.map(a=>`<li><span>${icon(a.status==='Registrado'?'check':'clock')}</span><div><h3>${esc(a.action)}</h3><p>${esc(a.detail)}</p><p>${date(a.at)} · ${esc(a.status)}</p></div></li>`).join('')}</ol>`:'<p>Todavía no hay acciones administrativas registradas.</p>'}</section>`;
  }
  function confirmation(action,version='') {
    const content={
      'restart-node':['¿Solicitar el reinicio del microcontrolador?','La operación interrumpe temporalmente el huerto. Solo se admite con un token vigente para este reporte. El reinicio permanecerá sin confirmar hasta recibir respuesta del dispositivo.','Solicitar reinicio'],
      'restart-platform':['¿Solicitar un reinicio de plataforma?','Registra la solicitud de mantenimiento. El servicio deberá autorizar la operación y confirmar su resultado.','Registrar solicitud'],
      publish:['¿Solicitar la publicación de '+version+'?','Se registrará la versión validada y sus notas. La versión en servicio se conserva hasta que el despliegue sea confirmado.','Solicitar publicación']
    }[action];
    return `<h2 id="admin-dialog-title">${esc(content[0])}</h2><p id="admin-dialog-copy">${content[1]}</p><div class="app-dialog-actions">${button('cancel-dialog','Cancelar')}${button('confirm-dialog',content[2],true)}</div>`;
  }
  return {
    confirmation,
    render(screen,data) {
      if(data.status!=='ready')return messages+heading('Administración')+AppViews.state(data.status==='loading'?'Consultando la plataforma':'No se pudo consultar la plataforma',data.status==='loading'?'Espera un momento.':'Comprueba tu acceso e inténtalo de nuevo.',data.status==='loading')+button('refresh','Reintentar')+dialog;
      return messages+({flota:fleet,soporte:remote,gobernanza:governance,despliegues:deployments}[screen]||fleet)(data)+dialog;
    }
  };
})();

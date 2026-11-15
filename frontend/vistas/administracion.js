// VISTA · Administración: paneles de administración, buzón de consultas y gestión comercial.
// Define: AdminViews, InquiryViews, CommerceViews.

// ── Administracion ──
const AdminViews = (() => {
  const date=AppViews.date;
  const button=(action,label,primary=false,attrs='')=>`<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-admin-action="${action}" ${attrs}>${label}</button>`;
  const heading=AppViews.heading;
  const available=(value,missing='Sin lectura')=>value===null||value===undefined||value===''?missing:escaparHTML(String(value));
  const metricValue=value=>value===null||value===undefined?'—':escaparHTML(AppModel.number(value));
  const section=(title,copy='')=>`<div class="user-section-heading"><div><h2>${title}</h2>${copy?`<p>${copy}</p>`:''}</div></div>`;
  const metric=(label,value,unit,copy,ico='activity')=>`<article class="bento-panel user-metric"><span class="user-metric-icon">${icon(ico)}</span><h2>${label}</h2><strong>${value}<small>${unit}</small></strong><p>${copy}</p></article>`;
  const table=(label,headers,rows)=>`<div class="user-table-scroll" tabindex="0" role="region" aria-label="${escaparHTML(label)}"><table class="user-table admin-table"><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}">Sin registros disponibles.</td></tr>`}</tbody></table></div>`;
  const fact=(label,value)=>`<div><dt>${label}</dt><dd>${value}</dd></div>`;
  const notice=state=>AdminService.noticeLabels[state]||'Sin aviso registrado';
  const note=text=>`<p class="admin-service-note">${text}</p>`;
  const messages='<div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>';
  function fleet(data,access={}) {
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
    <div class="user-section-heading"><div><h2>Identidades y dispositivos vinculados</h2><p>Identificadores operativos y conexión al broker Mosquitto.</p></div>${button('refresh',icon('refresh')+'<span>Actualizar dispositivos</span>')}</div>
    <section class="bento-panel admin-table-panel">${table('Dispositivos vinculados',['Device_ID','User_ID','Mosquitto','Último heartbeat'],data.nodes.map(n=>`<tr><th scope="row">${escaparHTML(n.device)}</th><td>${available(n.user,'Sin vínculo de usuario en esta proyección')}</td><td><span class="admin-connection ${n.connected?'online':'offline'}">${n.connected==null?'Sin información':n.connected?'En línea':'Sin conexión'}</span></td><td>${available(n.heartbeat,'Sin registro')}</td></tr>`))}<p class="admin-caption">Se muestra el vínculo operativo mínimo. No se incluyen contraseñas ni ubicación.</p></section>
    ${section('Telemetría para evaluación de IA','Patrones agregados para evaluar el riego predictivo y el desgaste del hardware.')}
    <section class="user-technical-metrics" aria-label="Indicadores de evaluación">
      ${metric('Evaporación · mezcla con perlita',metricValue(metrics.perliteEvaporation),metrics.perliteEvaporation==null?'':'mm/día','Sin estimación disponible','sun')}
      ${metric('Vida mediana del sensor capacitivo v1.2',metricValue(metrics.sensorLife),metrics.sensorLife==null?'':'meses','Sin estimación disponible','activity')}
      ${metric('Órdenes de mini bombas',metricValue(metrics.pumpOrders),metrics.pumpOrders==null?'':'/ huerto / día','Sin registros disponibles','drop')}
    </section>
    ${section('Correlaciones por temperatura','Ventanas ambientales utilizadas para evaluar el modelo.')}
    <section class="bento-panel admin-table-panel">${table('Correlaciones agregadas',['Temperatura media','Evaporación estimada','Órdenes de bomba','Uso en el modelo'],(data.correlations||[]).map(row=>`<tr>${row.map(c=>`<td>${escaparHTML(c)}</td>`).join('')}</tr>`))}<p class="admin-caption">La evaluación utiliza agregados. Las correlaciones lumínicas requieren una medición verificable de luz.</p></section>`+management(access);
  }
  // Accesos de gestión: los registros existen en Mantenimientos; las solicitudes del producto aún no.
  // `access` lo prepara el controlador a partir de las capacidades de la sesión; la vista solo pinta.
  function management({records=false,inbox=false}={}) {
    return `<section class="bento-panel admin-management" aria-labelledby="admin-management-title"><div class="admin-management-copy"><h2 id="admin-management-title">Gestión administrativa</h2><p>Acceso a los registros de mantenimiento y a las solicitudes del producto.</p></div>
      <div class="admin-management-actions">${records?`<a class="button btn-liquid-light" href="#admin/mantenimientos">${icon('list')}<span>Gestión de registros</span></a>`:''}${AppModel.supportMailUrl()?`<a class="button btn-liquid-light" href="${escaparHTML(AppModel.supportMailUrl())}" target="_blank" rel="noopener noreferrer">${icon('mail')}<span>Abrir correo de soporte</span><span class="sr-only">(se abre en otra pestaña)</span></a>`:''}${inbox?`<a class="button btn-liquid-light" href="#admin/solicitudes">${icon('inbox')}<span>Solicitudes del producto</span></a>`:''}</div>
      <p class="admin-service-note">Las consultas de «Consíguelo» se guardan en el buzón y generan un aviso al correo de soporte. Responde desde tu correo.</p></section>`;
  }
  function remote(data) {
    const ticket=data.selected;
    return heading('Consola remota','Atiende cada reporte con la autorización temporal de la persona usuaria.')+
    `<div class="user-section-heading"><div><h2>Buzón de reportes</h2><p>Los registros técnicos se abren únicamente con el token del caso seleccionado.</p></div>${button('refresh','Actualizar reportes')}</div>
    <section class="bento-panel admin-table-panel">${data.tickets.length?table('Reportes de soporte',['Folio','Device_ID','Incidente','Atención','Autorización','Acción'],data.tickets.map(t=>`<tr${ticket?.id===t.id?' class="admin-selected-row"':''}><th scope="row">${escaparHTML(t.folio||t.id)}</th><td>${available(t.device,'Sin dispositivo asignado')}</td><td>${escaparHTML(t.incident)}</td><td>${t.caseState==='resolved'?'Resuelto':'Abierto'}</td><td>${escaparHTML(t.status)}</td><td>${button('open-ticket','Abrir',false,`data-ticket="${escaparHTML(t.id)}" aria-label="Abrir caso ${escaparHTML(t.folio||t.id)}"`)}</td></tr>`)):'<p>No hay reportes registrados.</p>'}</section>
    ${section('Detalle y autorización')}
    <section class="bento-panel admin-ticket-detail" tabindex="-1" id="admin-ticket-detail">
      ${ticket?`<h2>Caso ${escaparHTML(ticket.folio||ticket.id)}</h2><dl class="user-facts admin-ticket-facts">${fact('Device_ID',available(ticket.device,'Sin dispositivo asignado'))}${fact('User_ID',available(ticket.user,'Sin identificador disponible'))}${fact('Incidente',escaparHTML(ticket.incident))}${fact('Creado',date(ticket.createdAt))}${fact('Atención',ticket.caseState==='resolved'?'Resuelto':'Abierto')}${fact('Autorización',escaparHTML(ticket.status))}${fact('Aviso de caso nuevo',escaparHTML(notice(ticket.notices?.newCase)))}${fact('Token solicitado',ticket.tokenRequestedAt?`${date(ticket.tokenRequestedAt)} · ${escaparHTML(notice(ticket.notices?.tokenRequest))}`:'No')}</dl><p>El diagnóstico queda limitado a este caso. El token de otro caso no concede acceso. Vencer o revocar la autorización no resuelve el caso.</p>
      ${ticket.caseState==='resolved'?`<p class="admin-access-state">Resuelto el ${date(ticket.resolution.at)} · ${escaparHTML(AdminService.results[ticket.resolution.result]||ticket.resolution.result)}${ticket.resolution.note?` · ${escaparHTML(ticket.resolution.note)}`:''}. El permiso está revocado y el token ya no abre acceso.</p>`:`${button('request-token','Solicitar token a la persona usuaria')}
      <form data-admin-token-form class="admin-token-form"><label for="admin-token">Token compartido por la persona usuaria</label><div class="admin-input-row"><input id="admin-token" name="token" type="text" required minlength="43" maxlength="43" pattern="[A-Za-z0-9_-]{43}" autocomplete="off" spellcheck="false" autocapitalize="off"><button class="button btn-liquid-brand" type="submit">Validar token</button></div></form>
      <p class="admin-access-state">${data.remote?`Acceso autorizado hasta el ${date(new Date(data.remote.expiresAt).toISOString())}.`:'Acceso técnico bloqueado. Valida una autorización vigente para continuar.'}</p>
      <form data-admin-resolve-form class="admin-resolve-form"><h3>Resolver caso</h3><label for="admin-resolve-result">Resultado de la atención</label><select id="admin-resolve-result" name="result" required>${Object.entries(AdminService.results).map(([v,l])=>`<option value="${v}">${escaparHTML(l)}</option>`).join('')}</select><label for="admin-resolve-note">Nota (obligatoria si eliges «Otro»)</label><textarea id="admin-resolve-note" name="note" rows="3" maxlength="500"></textarea><p class="admin-service-note">Resolver es definitivo: revoca la autorización vigente y cierra el acceso técnico de este caso.</p><div class="app-actions"><button class="button btn-liquid-brand" type="submit">Resolver caso</button></div></form>`}`:'<h2>Selecciona un reporte</h2><p>Abre un caso del buzón para consultar su detalle y validar el token correspondiente.</p>'}
    </section>
    ${data.remote?diagnostics(data):''}
    ${section('Alcance del acceso remoto')}
    <section class="bento-panel admin-governance-list"><dl class="admin-policy-list">
      ${fact('Sesión de diagnóstico','Se abre con el token vigente del caso. El diagnóstico remoto del dispositivo todavía no está conectado.')}
      ${fact('Duración','Máximo 24 horas desde que se emite; usar el token no la renueva.')}
      ${fact('Cierre del acceso','Revocación de la persona usuaria, vencimiento o resolución del caso.')}
      ${fact('Fuera del alcance','Acceso permanente, contraseñas, ubicación e historial de cultivo.')}
    </dl></section>`;
  }
  function diagnostics(data) {
    // El servicio de diagnóstico del dispositivo no está conectado: se dice, sin simular lecturas.
    const connected=data.diagnostics.pins.length>0||data.diagnostics.logs.length>0;
    return `${section('Sesión de diagnóstico',available(data.selected.device,'Sin dispositivo asignado')+' · '+escaparHTML(data.selected.folio||data.selected.id))}
    <section class="bento-panel admin-diagnostics"><h2>Diagnóstico del dispositivo</h2>${connected?`<dl class="admin-gpio-grid">${data.diagnostics.pins.map(([k,v])=>fact(escaparHTML(k),available(v))).join('')}</dl>${data.diagnostics.logs.length?`<pre class="admin-logs" tabindex="0" aria-label="Registros técnicos del caso"><code>${escaparHTML(data.diagnostics.logs.join('\n'))}</code></pre>`:''}`:'<p>Servicio de diagnóstico remoto no conectado. La sesión está abierta con la autorización del caso, pero todavía no hay lecturas del dispositivo.</p>'}<div class="app-actions">${button('refresh-diagnostics','Consultar de nuevo')}${button('close-remote','Cerrar sesión técnica')}</div></section>`;
  }
  const errors={
    'forbidden':'Tu cuenta no tiene acceso a esta operación.',
    'stale':'El caso ya está resuelto o cambió. Actualiza la consola.',
    'not-found':'Selecciona un reporte disponible antes de continuar.',
    'no-permission':'No hay una autorización vigente para este reporte. Solicita un token nuevo a la persona usuaria.',
    'wrong-report':'El token corresponde a otro reporte. Utiliza la autorización específica de este caso.',
    'invalid-token':'El token es incorrecto. Comprueba el código compartido por la persona usuaria.'};
  const errorText=status=>errors[status]||'No se pudo completar la operación. Inténtalo de nuevo.';
  return {
    errorText,
    // Operaciones de presentación que coordina AdminController.
    paint(root,screen,data,access) { root.innerHTML=this.render(screen,data,access); },
    feedback(root,message,error=false) {
      const el=root.querySelector('#admin-feedback');
      if(!el)return;
      el.hidden=false;el.textContent=message;el.setAttribute('role',error?'alert':'status');el.focus();
    },
    focusDetail(root) { root.querySelector('#admin-ticket-detail')?.focus(); },
    render(screen,data,access={}) {
      if(data.status!=='ready')return messages+heading('Administración')+AppViews.state(data.status==='loading'?'Consultando la plataforma':'Esta sección se está actualizando.',data.status==='loading'?'Espera un momento.':'Vuelve a intentarlo más tarde.',data.status==='loading')+button('refresh','Reintentar');
      return messages+({flota:fleet,soporte:remote}[screen]||fleet)(data,access);
    }
  };
})();

// ── Consultas ──
// Buzón de consultas: estructura fija con plantilla y datos del servidor siempre como texto.
const InquiryViews = (() => {
  const filters = [['','Todas'],['nueva','Nuevas'],['atendida','Atendidas'],['archivada','Archivadas']];
  function shell() {
    return `${AppViews.heading('Solicitudes del producto','Consultas recibidas desde «Consíguelo». Responde desde tu correo y registra aquí su atención.')}
      <div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>
      <nav class="account-tabs inquiry-filters" aria-label="Filtrar consultas">${filters.map(([value,label]) => `<button type="button" class="button btn-liquid-light" data-inq-filter="${value}" aria-pressed="false">${label}</button>`).join('')}</nav>
      <p class="inquiry-status" data-inq-status role="status"></p>
      <div class="inquiry-list" data-inq-list></div>
      <nav class="inquiry-pager" aria-label="Páginas del buzón" data-inq-pager hidden><button type="button" class="button btn-liquid-light" data-inq-page="-1">Anterior</button><span class="inquiry-page" data-inq-page-label></span><button type="button" class="button btn-liquid-light" data-inq-page="1">Siguiente</button></nav>`;
  }
  const el = (tag, className, text) => Object.assign(document.createElement(tag), className ? {className} : {}, text !== undefined ? {textContent:text} : {});
  function item(row, service) {
    const card = el('article', 'bento-panel inquiry-item');
    const head = el('div', 'inquiry-head');
    head.append(el('strong', 'inquiry-folio', row.folio), el('span', 'inquiry-state is-'+row.state, service.states[row.state] || row.state),
      Object.assign(el('time', 'inquiry-date', service.dateText(row.receivedAt)), {dateTime: row.receivedAt}));
    const who = el('p', 'inquiry-who');
    who.append(el('strong', '', row.name || 'Sin nombre'), document.createTextNode(' · '), el('span', '', row.email));
    const message = el('p', 'inquiry-message', row.message);
    const meta = el('p', 'inquiry-meta', [service.attentionText(row), service.notices[row.notice] || 'Sin aviso registrado'].join(' · '));
    const actions = el('div', 'app-actions');
    const href = service.replyHref(row);
    if(href) {
      const reply = Object.assign(el('a', 'button btn-liquid-light', 'Responder en Gmail'), {href, target:'_blank', rel:'noopener noreferrer'});
      reply.setAttribute('aria-label', `Responder a ${row.email} en Gmail (abre una pestaña nueva)`);
      actions.append(reply);
    }
    if(row.state !== 'atendida') actions.append(Object.assign(el('button', 'button btn-liquid-brand', 'Marcar como atendida'), {type:'button'}));
    if(row.state !== 'archivada') actions.append(Object.assign(el('button', 'button btn-liquid-light', 'Archivar'), {type:'button'}));
    actions.querySelectorAll('button').forEach(button => { button.dataset.inqId = row.id; button.dataset.inqState = button.textContent === 'Archivar' ? 'archivada' : 'atendida'; });
    card.append(head, who, message, meta, actions);
    return card;
  }
  const messages = {forbidden:'Tu cuenta no tiene la capacidad para atender consultas.', stale:'No se guardó el cambio: ese paso no está permitido o la consulta ya había cambiado. Se actualizó la lista.', limited:'Demasiadas operaciones seguidas. Espera un momento.'};
  // Monta el buzón y devuelve las operaciones de presentación que coordina el controlador.
  function mount(root) {
    root.innerHTML = shell();
    const list = root.querySelector('[data-inq-list]'), status = root.querySelector('[data-inq-status]'), feedback = root.querySelector('#admin-feedback');
    const pager = root.querySelector('[data-inq-pager]');
    function feedbackText(text, error = false) { feedback.hidden = !text; feedback.textContent = text; feedback.setAttribute('role', error ? 'alert' : 'status'); }
    return {
      list,
      clearFeedback() { feedbackText(''); },
      loading() { status.textContent = 'Consultando el buzón…'; },
      filter(state) {
        root.querySelectorAll('[data-inq-filter]').forEach(button => {
          button.setAttribute('aria-pressed', String(button.dataset.inqFilter === state));
          button.classList.toggle('active', button.dataset.inqFilter === state);
        });
      },
      failed(code) { list.replaceChildren(); pager.hidden = true; status.textContent = messages[code] || 'No se pudo consultar el buzón. Inténtalo de nuevo.'; },
      show(items, total, page, service) {
        list.replaceChildren(...items.map(row => item(row, service)));
        status.textContent = total ? `${total} consulta${total === 1 ? '' : 's'}` : 'No hay consultas en este filtro.';
        // Con una sola página no hay nada que paginar: los botones solo aparecen cuando sirven.
        const pages = Math.max(1, Math.ceil(total / 25));
        pager.hidden = pages <= 1;
        root.querySelector('[data-inq-page-label]').textContent = `Página ${page} de ${pages}`;
        root.querySelector('[data-inq-page="-1"]').disabled = page <= 1;
        root.querySelector('[data-inq-page="1"]').disabled = page >= pages;
      },
      scrollToTop() { list.firstElementChild?.scrollIntoView({block:'nearest'}); },
      busy(button) { button.disabled = true; },
      advanced(code, targetState) {
        if(code === 'accepted') feedbackText(targetState === 'archivada' ? 'Consulta archivada.' : 'Consulta marcada como atendida.');
        else feedbackText(messages[code] || 'No se pudo actualizar la consulta.', true);
      }
    };
  }
  return Object.freeze({shell, item, mount});
})();

// ── Comercial ──
// Vistas comerciales: markup fijo y datos variables por textContent/value. Sin red.
const CommerceViews = (() => {
  const el = (tag, props={}, ...children) => { const node=Object.assign(document.createElement(tag),props); node.append(...children); return node; };
  const hint = (id,text) => `<p class="commerce-hint" id="${id}">${text}</p>`;
  const field = (kind,name,label,attrs='',help='') => {
    const id=`commerce-${kind}-${name}`;
    return `<div class="commerce-field"><label for="${id}">${label}</label><input id="${id}" name="${name}" ${attrs} aria-describedby="${id}-error${help?' '+id+'-help':''}">${help?hint(id+'-help',help):''}<span class="commerce-error" id="${id}-error" data-error="${name}" hidden></span></div>`;
  };
  function select(kind,name,label,entries,blank='Todos') {
    const id=`commerce-${kind}-${name}`;
    return `<div class="commerce-field"><label for="${id}">${label}</label><select id="${id}" name="${name}" aria-describedby="${id}-error"><option value="">${blank}</option>${Object.entries(entries).map(([key,text])=>`<option value="${key}">${escaparHTML(text)}</option>`).join('')}</select><span class="commerce-error" id="${id}-error" data-error="${name}" hidden></span></div>`;
  }
  function dateField(kind,name,label,required=false) {
    const id=`commerce-${kind}-${name}`;
    return `<div class="commerce-field maint-date-control"><label for="${id}">${label}</label><div class="maint-date-field"><input id="${id}" type="text" name="${name}" placeholder="AAAA-MM-DD" maxlength="10" autocomplete="off" spellcheck="false" ${required?'required':''} aria-describedby="commerce-date-help ${id}-error"><button type="button" data-date-open="${name}" data-date-label="${label}" aria-label="Abrir calendario: ${label}" aria-controls="maint-calendar" aria-haspopup="dialog" aria-expanded="false">${icon('calendar')}</button></div><span class="commerce-error" id="${id}-error" data-error="${name}" hidden></span></div>`;
  }
  const errors = kind => `<p class="commerce-errors" data-errors="${kind}" role="alert" tabindex="-1" hidden></p>`;
  const review = kind => `<section class="bento-panel commerce-review" data-review="${kind}" aria-labelledby="commerce-${kind}-review-title" hidden><div data-review-content></div><div class="app-actions"><button class="button btn-liquid-light" type="button" data-edit="${kind}">Seguir editando</button></div></section>`;
  function table(headers,message) {
    return `<div class="user-table-scroll" tabindex="0" role="region" aria-label="${headers[0]==='Equipo'?'Listado de equipos':'Listado de ventas'}"><table class="user-table admin-table"><thead><tr>${headers.map(text=>`<th scope="col">${text}</th>`).join('')}</tr></thead><tbody><tr><td colspan="${headers.length}">${message}</td></tr></tbody></table></div>`;
  }
  function equipmentPanel() {
    return `<section class="bento-panel" aria-labelledby="commerce-inventory"><div class="commerce-section-head"><div><h2 id="commerce-inventory">Equipos registrados</h2><p>Identidad del equipo y disponibilidad comercial.</p></div>${icon('grid')}</div>
      <form data-commerce-form="inventoryFilter" class="commerce-form commerce-filter" novalidate>${field('inventoryFilter','query','Buscar equipo o huerto','type="search" maxlength="120"')}${select('inventoryFilter','availability','Disponibilidad',CommerceModel.availability)}<div class="commerce-field commerce-filter-action"><button class="button btn-liquid-light" type="submit">Aplicar filtros</button></div></form>
      <p data-filter-status="inventoryFilter" class="commerce-hint" role="status">La consulta del inventario todavía no está disponible.</p>
      ${table(['Equipo','Huerto','Disponibilidad','Vinculación','Conexión','Detalle'],'Listado pendiente de servicio. Los borradores no son equipos registrados.')}
      </section><section class="bento-panel" aria-labelledby="commerce-equipment-form-title"><h2 id="commerce-equipment-form-title">Preparar alta de equipo</h2><p>El identificador es visible; no es una contraseña ni acredita conexión.</p>
      <form data-commerce-form="equipment" class="commerce-form" novalidate>${errors('equipment')}
      ${field('equipment','identifier','Identificador del equipo','type="text" required maxlength="80" autocomplete="off" spellcheck="false"','De 3 a 80 caracteres: letras, números, punto, guion, dos puntos o guion bajo.')}
      ${field('equipment','gardenName','Nombre del huerto','type="text" required maxlength="120" autocomplete="off"')}
      ${select('equipment','availability','Disponibilidad propuesta',CommerceModel.availability,'Selecciona una opción')}
      <div class="commerce-form-footer"><button class="button btn-liquid-brand" type="submit">Revisar borrador de equipo</button><p class="commerce-hint">El registro definitivo todavía no está disponible. No se creará ningún dispositivo.</p></div></form></section>${review('equipment')}`;
  }
  function salesPanel() {
    return `<section class="bento-panel" aria-labelledby="commerce-sales-list"><div class="commerce-section-head"><div><h2 id="commerce-sales-list">Ventas y entregas</h2><p>Venta presencial con registro manual; entrega a domicilio o recogida acordada.</p></div>${icon('list')}</div>
      <form data-commerce-form="salesFilter" class="commerce-form commerce-filter" novalidate>${field('salesFilter','query','Equipo o correo','type="search" maxlength="254" autocomplete="off"')}${dateField('salesFilter','since','Desde')}${dateField('salesFilter','until','Hasta')}
      ${select('salesFilter','saleState','Venta',{registrada:'Registrada'})}${select('salesFilter','paymentState','Pago',{pendiente:'Pendiente',completo:'Completo'})}${select('salesFilter','deliveryState','Entrega',{por_acordar:'Por acordar',programada:'Programada',entregada:'Entregada'})}${select('salesFilter','bindingState','Vinculación',{sin_vincular:'Sin vincular',vinculado:'Vinculado'})}
      ${errors('salesFilter')}<div class="commerce-form-footer"><button class="button btn-liquid-light" type="submit">Aplicar filtros</button></div></form>
      <p data-filter-status="salesFilter" class="commerce-hint" role="status">La consulta de ventas todavía no está disponible.</p>
      ${table(['Venta / equipo','Destinatario','Fecha','Precio total','Venta','Pago','Entrega','Vinculación'],'Listado pendiente de servicio. No se incluyen borradores en ventas ni cobros.')}
      </section><section class="bento-panel" aria-labelledby="commerce-sale-form-title"><h2 id="commerce-sale-form-title">Preparar registro de venta</h2><p>El precio corresponde al equipo completo, sin desglose de componentes.</p>
      <form data-commerce-form="sale" class="commerce-form" novalidate>${errors('sale')}
      ${field('sale','equipment','Identificador del equipo','type="text" required maxlength="80" autocomplete="off" spellcheck="false"','La existencia y disponibilidad del equipo se comprobarán en el servidor.')}
      ${field('sale','email','Correo de la cuenta destinataria','type="email" required maxlength="254" autocomplete="off"','La vinculación requiere una cuenta verificada y admite un solo huerto activo por cuenta.')}
      ${dateField('sale','saleDate','Fecha de venta',true)}
      ${field('sale','total','Precio total del equipo','type="text" required inputmode="decimal" maxlength="12" autocomplete="off"','Mayor que cero. Sin separadores de miles y con hasta dos decimales; punto o coma decimal.')}
      ${field('sale','received','Importe recibido declarado','type="text" required inputmode="decimal" maxlength="12" autocomplete="off"','Desde cero y hasta el precio total. Esta revisión no registra movimientos de pago.')}
      ${field('sale','reference','Referencia textual del pago (opcional)','type="text" maxlength="120" autocomplete="off"','La referencia no demuestra recepción bancaria. No incluyas datos bancarios ni documentos.')}
      ${select('sale','deliveryMode','Modalidad de entrega',CommerceModel.deliveryModes,'Selecciona una opción')}${dateField('sale','deliveryDate','Fecha prevista de entrega (opcional)')}
      <p class="commerce-hint commerce-full">La fecha de entrega puede quedar por acordar. Una fecha prevista no confirma que el equipo se entregó. La moneda se definirá para la integración.</p>
      <div class="commerce-form-footer"><button class="button btn-liquid-brand" type="submit">Revisar borrador de venta</button><p class="commerce-hint">El registro definitivo de venta, cobro y entrega todavía no está disponible. El borrador dura solo esta visita y se pierde al recargar.</p></div></form></section>${review('sale')}`;
  }
  function bindingPanel() {
    return `<section class="bento-panel" aria-labelledby="commerce-binding-title"><h2 id="commerce-binding-title">Del equipo a la vinculación</h2><p>Cada paso tiene un estado propio. Un borrador comercial no autoriza la emisión de códigos.</p>
      <ol class="commerce-chain"><li><strong>Equipo</strong><span>Registro y disponibilidad por consultar.</span></li><li><strong>Venta</strong><span>Registro comercial por integrar.</span></li><li><strong>Pago</strong><span>Pago completo: condición futura por validar en Django.</span></li><li><strong>Entrega</strong><span>Modalidad y fecha no acreditan recepción física.</span></li><li><strong>Vinculación</strong><span>Cuenta verificada, un huerto activo y controles actuales del servidor.</span></li></ol>
      <div data-binding-context class="commerce-context" aria-live="polite"></div>
      <div class="app-actions"><a class="button btn-liquid-light" href="#admin/vinculacion">Abrir Vinculación de huertos ${icon('arrow')}</a></div><p class="commerce-hint">Abre el apartado existente. No transfiere el borrador ni emite un código. La comprobación comercial del pago sigue pendiente de integración.</p></section>`;
  }
  function summaryPanel() {
    return `<section class="bento-panel" aria-labelledby="commerce-summary-title"><h2 id="commerce-summary-title">Resumen por periodo</h2><form data-commerce-form="summaryFilter" class="commerce-form commerce-filter" novalidate>
      ${select('summaryFilter','preset','Periodo',{current:'Mes actual hasta hoy',previous:'Mes anterior',custom:'Personalizado'},'Todo el periodo')}${dateField('summaryFilter','since','Desde')}${dateField('summaryFilter','until','Hasta')}${errors('summaryFilter')}
      <div class="commerce-form-footer"><button class="button btn-liquid-light" type="submit">Consultar periodo</button><p class="commerce-hint">La consulta económica todavía no está disponible.</p></div></form><p data-filter-status="summaryFilter" role="status" class="commerce-hint">Sin datos consultados. Los borradores no forman parte del resumen.</p></section>
      <div class="commerce-metrics">${[['Cantidad de ventas','Requiere ventas registradas.'],['Importe vendido','Requiere moneda y ventas confirmadas.'],['Cobros','Requiere registros y fechas de cobro.'],['Saldo','Requiere contrato de ventas y cobros.']].map(([title,note])=>`<section class="bento-panel"><h3>${title}</h3><p class="commerce-metric-value" aria-label="Sin datos consultados">—</p><p class="commerce-hint">${note}</p></section>`).join('')}</div>
      <section class="bento-panel"><h2>Ganancias</h2><p>Pendientes de definir costos y gastos. El precio de venta por sí solo no permite calcularlas.</p></section>`;
  }
  function shell() {
    const panels={equipos:equipmentPanel,ventas:salesPanel,vinculacion:bindingPanel,resumen:summaryPanel};
    return `<div class="commerce-workspace">${AppViews.heading('Equipos y ventas','Inventario, venta presencial y preparación de entregas.')}
      <div class="account-tabs commerce-tabs" role="tablist" aria-label="Equipos y ventas">${CommerceModel.tabs.map(([key,label],index)=>`<button id="commerce-tab-${key}" type="button" role="tab" class="button ${index?'btn-liquid-light':'btn-liquid-brand active'}" data-commerce-tab="${key}" aria-controls="commerce-panel-${key}" aria-selected="${!index}" tabindex="${index?-1:0}">${label}</button>`).join('')}</div>
      <p class="sr-only" id="commerce-date-help">Escribe la fecha como año-mes-día. Flecha abajo abre el calendario; Escape lo cierra.</p>
      ${CommerceModel.tabs.map(([key],index)=>`<div id="commerce-panel-${key}" role="tabpanel" aria-labelledby="commerce-tab-${key}" tabindex="0" ${index?'hidden':''}>${panels[key]()}</div>`).join('')}</div>`;
  }
  function activate(root,key) {
    root.querySelectorAll('[data-commerce-tab]').forEach(button=>{
      const active=button.dataset.commerceTab===key;
      button.setAttribute('aria-selected',String(active)); button.tabIndex=active?0:-1;
      button.classList.toggle('active',active); button.classList.toggle('btn-liquid-brand',active); button.classList.toggle('btn-liquid-light',!active);
      root.querySelector('#'+button.getAttribute('aria-controls')).hidden=!active;
    });
  }
  function formErrors(form,issues) {
    for(const field of form.querySelectorAll('input,select')) {
      const message=issues[field.name] || '';
      field.setCustomValidity(message);
      if(message) field.setAttribute('aria-invalid','true'); else field.removeAttribute('aria-invalid');
      const error=form.querySelector(`[data-error="${field.name}"]`);
      if(error) { error.textContent=message; error.hidden=!message; }
    }
    const summary=form.querySelector('[data-errors]');
    if(summary) { summary.textContent=Object.keys(issues).length?'Revisa los campos señalados antes de continuar.':''; summary.hidden=!summary.textContent; }
  }
  function facts(entries) {
    return el('dl',{className:'commerce-facts'},...entries.map(([label,value])=>el('div',{},el('dt',{textContent:label}),el('dd',{textContent:value}))));
  }
  function renderReview(root,kind,data) {
    const section=root.querySelector(`[data-review="${kind}"]`);
    section.hidden=!data;
    if(!data) { section.querySelector('[data-review-content]').replaceChildren(); return; }
    const title=el('h2',{id:`commerce-${kind}-review-title`,tabIndex:-1,textContent:kind==='equipment'?'Detalle del equipo · borrador':'Revisión de venta · borrador'});
    const entries=kind==='equipment'?[
      ['Equipo',data.identifier],['Huerto',data.gardenName],['Disponibilidad propuesta',CommerceModel.availability[data.availability]],['Registro','Sin registrar'],['Vinculación','Sin consultar'],['Conexión','Sin datos de conexión']
    ]:[
      ['Equipo',data.equipment],['Correo destinatario',data.email],['Cuenta verificada','Sin consultar'],['Fecha de venta',data.saleDate],['Precio total declarado',CommerceModel.money(data.totalMinor)],['Importe recibido declarado',CommerceModel.money(data.receivedMinor)],['Saldo aritmético del borrador',CommerceModel.money(data.balanceMinor)],['Referencia',data.reference||'Sin referencia'],['Venta','Borrador sin registrar'],['Pago',data.balanceMinor===0?'El importe declarado cubre el total; sin confirmar':'El importe declarado es inferior al total; sin confirmar'],['Entrega',CommerceModel.deliveryModes[data.deliveryMode]+' · '+(data.deliveryDate||'Fecha por acordar')+' · Sin confirmar'],['Vinculación','Sin consultar; el borrador no autoriza emitir']
    ];
    const content=[title,facts(entries),el('p',{className:'commerce-hint',textContent:kind==='equipment'?'Revisión local. No comprueba unicidad ni crea un huerto, zonas o dispositivo. Se pierde al recargar.':'Revisión local, sin moneda acordada ni comprobación bancaria. No registra venta, cobro o entrega y no comprueba la elegibilidad para vincular.'})];
    if(kind==='equipment') { const use=el('button',{className:'button btn-liquid-light',type:'button',textContent:'Usar identificador en borrador de venta'}); use.dataset.useEquipment=''; content.push(use); }
    section.querySelector('[data-review-content]').replaceChildren(...content);
  }
  function bindingContext(root,state) {
    const host=root.querySelector('[data-binding-context]');
    const sale=state.saleReview;
    host.replaceChildren(el('h3',{textContent:'Relación preparada en esta visita'}));
    if(!sale) { host.append(el('p',{textContent:'Revisa un borrador de venta para ver aquí el equipo, destinatario e importes propuestos. No se consultan ni confirman estados reales.'})); return; }
    host.append(facts([['Equipo propuesto',sale.equipment],['Cuenta destinataria propuesta',sale.email],['Venta','Borrador sin registrar'],['Pago','Importe declarado: '+CommerceModel.money(sale.receivedMinor)+' de '+CommerceModel.money(sale.totalMinor)+'; sin confirmar'],['Entrega propuesta',CommerceModel.deliveryModes[sale.deliveryMode]+' · '+(sale.deliveryDate||'Por acordar')],['Vinculación','Sin consultar; sin autorización comercial']]));
  }
  function fill(form,values) { for(const [key,value] of Object.entries(values)) { const field=form.elements.namedItem(key); if(field) field.value=value; } }
  function read(form) { return Object.fromEntries(new FormData(form)); }
  function focusReview(root,kind) { root.querySelector(`#commerce-${kind}-review-title`)?.focus(); }
  function unavailable(root) {
    root.innerHTML=AppViews.heading('Equipos y ventas')+AppViews.state('Apartado no disponible','Tu sesión no tiene habilitado este destino administrativo.');
  }
  function mount(root) {
    root.innerHTML=shell();
    return {workspace:root.querySelector('.commerce-workspace'), tablist:root.querySelector('[role=tablist]'),
      forms:Object.fromEntries([...root.querySelectorAll('[data-commerce-form]')].map(form=>[form.dataset.commerceForm,form]))};
  }
  function focusTab(root,key) { root.querySelector(`[data-commerce-tab="${key}"]`).focus(); }
  const filterTexts={changed:'Filtro modificado. La consulta todavía no está disponible.',
    ready:'Filtros preparados. La consulta todavía no está disponible; no se han consultado registros.'};
  function filterStatus(root,kind,state) { root.querySelector(`[data-filter-status="${kind}"]`).textContent=filterTexts[state]; }
  function customPeriod(form) { form.elements.preset.value='custom'; }
  function focusInvalid(form) { form.querySelector('[aria-invalid=true]')?.focus(); }
  function focusFirstInput(form) { form.querySelector('input')?.focus(); }
  function setEquipment(form,identifier) { form.elements.equipment.value=identifier; }
  function focusEquipment(form) { form.elements.equipment.focus(); }
  return Object.freeze({shell,activate,formErrors,renderReview,bindingContext,fill,read,focusReview,
    unavailable,mount,focusTab,filterStatus,customPeriod,focusInvalid,focusFirstInput,setEquipment,focusEquipment});
})();

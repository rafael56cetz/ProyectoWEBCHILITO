// VISTA · Administración: paneles de operación, buzón de consultas, ventas, administradores, textos legales y consentimientos.
// Define: AdminViews, InquiryViews, SalesViews, AdminAccessViews, LegalAdminViews, ConsentViews.

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
      ${GardenViews.chart('Humedad media del sustrato',series(data.trends.soil),'%','7d','fleet-soil')}
      ${GardenViews.chart('Humedad relativa media',series(data.trends.humidity),'%','7d','fleet-rh')}
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

// ── Ventas ──
// Ventas de equipos (5.6). Los importes y fechas llegan del servidor como texto; todo se escapa.
const SalesViews = (() => {
  const T = AdminTableViews;
  const {tag} = GardenViews;
  const PAYMENTS = {pendiente:['Pendiente', 'rojo'], parcial:['Parcial', 'ambar'], completo:['Completo', 'verde']};
  const METHODS = {domicilio:'Entrega a domicilio', recogida:'Recogida acordada'};
  const ERRORS = {'equipo-vendido':'Ese equipo ya tiene una venta vigente.', 'importe-no-valido':'El importe recibido no puede bajar ni superar el precio.', 'venta-cancelada':'Esta venta está cancelada y ya no cambia.',
    'venta-entregada':'Esta venta ya se marcó como entregada.', 'fecha-no-valida':'La entrega debe caer entre la fecha de venta y hoy.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.') => ERRORS[code] || fallback;
  const options = (items, selected = '') => items.map(([value, label]) => `<option value="${escaparHTML(value)}"${value === selected ? ' selected' : ''}>${escaparHTML(label)}</option>`).join('');
  const today = () => MaintenanceDates.format(MaintenanceDates.today());

  function filters(values, municipalities) {
    return `<form class="care-filters" data-admin-form="sales-filter" novalidate>
      <div><label for="sale-search">Buscar</label><input id="sale-search" name="busqueda" type="search" maxlength="60" placeholder="Comprador, correo o equipo" value="${escaparHTML(values.busqueda || '')}"></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}
      <div><label for="sale-payment">Pago</label><select id="sale-payment" name="pago">${options([['', 'Todos'], ...Object.entries(PAYMENTS).map(([value, [label]]) => [value, label])], values.pago)}</select></div>
      <div><label for="sale-delivery">Entrega</label><select id="sale-delivery" name="entrega">${options([['', 'Todas'], ['por_entregar', 'Por entregar'], ['entregada', 'Entregada']], values.entrega)}</select></div>
      <div><label for="sale-municipality">Municipio</label><select id="sale-municipality" name="municipio">${options([['', 'Todos'], ...municipalities.map(name => [name, name])], values.municipio)}</select></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button>${T.button('clear', 'Limpiar')}</div></form>`;
  }

  function row(sale) {
    const delivery = sale.delivery === 'entregada' ? tag('Entregada', 'verde') : `${tag('Por entregar', 'ambar')}${sale.plannedDelivery ? ` <small>${T.day(sale.plannedDelivery)}</small>` : ''}`;
    return `<tr><td>${escaparHTML(sale.device.identifier)}</td><td>${escaparHTML(sale.buyer)}</td><td>${escaparHTML(sale.municipality)}</td><td>${T.day(sale.soldAt)}</td><td>${T.money(sale.price)}</td>
      <td>${tag(...PAYMENTS[sale.payment])}<br><small>${T.money(sale.received)} de ${T.money(sale.price)}</small></td><td>${delivery}</td><td>${tag(sale.state === 'vigente' ? 'Vigente' : 'Cancelada', sale.state === 'vigente' ? 'verde' : 'gris')}</td>
      <td>${T.button('sale', 'Ver', 'light', `data-id="${sale.id}"`)}</td></tr>`;
  }

  function salesTab(state) {
    const {list, catalog} = state;
    const body = list.items.length ? T.table('Ventas', ['Equipo', 'Comprador', 'Municipio', 'Fecha', 'Precio', 'Pago', 'Entrega', 'Estado', ''], list.items.map(row))
      : '<div class="user-empty-inline"><p>No hay ventas con estos filtros.</p></div>';
    return `<div class="app-actions">${T.button('create', '+ Registrar venta', 'brand')}</div><section class="bento-panel">${filters(state.filters, catalog.municipalities)}${body}${T.pager(list)}</section>`;
  }

  function summaryTab(state) {
    const {summary, preset} = state;
    const periods = [['month', 'Este mes'], ['previous', 'Mes anterior'], ['all', 'Todo'], ['custom', 'Personalizado']];
    const tiles = [['Ventas', summary.sales], ['Importe vendido', T.money(summary.sold)], ['Cobrado', T.money(summary.collected)], ['Por cobrar', T.money(summary.pending)]]
      .map(([label, value]) => `<article class="bento-panel user-metric"><h2>${label}</h2><strong>${value}</strong></article>`).join('');
    const rows = summary.byMunicipality.map(item => `<tr><td>${escaparHTML(item.municipality)}</td><td>${item.sales}</td><td>${T.money(item.sold)}</td><td>${T.money(item.collected)}</td><td>${T.money(item.pending)}</td></tr>`);
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="sales-period" novalidate><div><label for="sale-preset">Periodo</label><select id="sale-preset" name="preset">${options(periods, preset)}</select></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}<div class="app-actions"><button class="button btn-liquid-brand" type="submit">Aplicar</button></div></form></section>
      <section class="user-summary-metrics" aria-label="Resumen de ventas">${tiles}</section>
      <section class="bento-panel"><h2>Por municipio</h2>${rows.length ? T.table('Ventas por municipio', ['Municipio', 'Ventas', 'Vendido', 'Cobrado', 'Por cobrar'], rows) : '<p>No hay ventas en este periodo.</p>'}</section>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    return `${AppViews.heading('Ventas', 'Registra ventas, pagos y entregas de equipos.')}${T.tabs([['ventas', 'Ventas'], ['resumen', 'Resumen']], state.tab)}${state.tab === 'resumen' ? summaryTab(state) : salesTab(state)}${T.dialog}`;
  }

  function createForm(catalog) {
    return `<h2 id="admin-dialog-title">Registrar venta</h2><form data-admin-form="sale-create" novalidate>
      <label for="sc-device">Equipo</label><select id="sc-device" name="device" required>${options([['', 'Elige un equipo'], ...catalog.sellable.map(item => [item.id, item.identifier])])}</select>
      <label for="sc-buyer">Nombre del comprador</label><input id="sc-buyer" name="buyer" type="text" maxlength="120" required>
      <label for="sc-email">Correo del comprador</label><input id="sc-email" name="email" type="email" maxlength="254" required>
      <label for="sc-municipality">Municipio</label><select id="sc-municipality" name="municipality" required>${options([['', 'Elige un municipio'], ...catalog.municipalities.map(name => [name, name])])}</select>
      <label for="sc-price">Precio total (MXN)</label><input id="sc-price" name="price" type="text" inputmode="decimal" placeholder="3500.00" required>
      <label for="sc-received">Importe recibido (MXN)</label><input id="sc-received" name="received" type="text" inputmode="decimal" value="0">
      <label for="sc-reference">Referencia del pago</label><input id="sc-reference" name="reference" type="text" maxlength="120">
      <label for="sc-method">Modalidad de entrega</label><select id="sc-method" name="method">${options(Object.entries(METHODS))}</select>
      <label for="sc-sold">Fecha de venta</label><input id="sc-sold" name="soldAt" type="date" max="${today()}" value="${today()}" required>
      <label for="sc-planned">Fecha prevista de entrega (opcional)</label><input id="sc-planned" name="plannedDelivery" type="date">
      <label for="sc-note">Nota (opcional)</label><textarea id="sc-note" name="note" maxlength="500" rows="3"></textarea>
      <div class="app-dialog-actions">${T.button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Registrar venta</button></div></form>`;
  }

  function detail(sale) {
    const open = sale.state === 'vigente';
    const facts = [['Equipo', escaparHTML(sale.device.identifier)], ['Comprador', `${escaparHTML(sale.buyer)} · ${escaparHTML(sale.email)}${sale.accountLinked ? ' · con cuenta' : ''}`], ['Municipio', escaparHTML(sale.municipality)],
      ['Precio', T.money(sale.price)], ['Recibido', `${T.money(sale.received)} · ${PAYMENTS[sale.payment][0]}`], ['Referencia del pago', sale.reference ? escaparHTML(sale.reference) : '—'],
      ['Entrega', `${METHODS[sale.method]}${sale.deliveredAt ? ` · entregada el ${T.day(sale.deliveredAt)}` : sale.plannedDelivery ? ` · prevista ${T.day(sale.plannedDelivery)}` : ''}`],
      ['Fecha de venta', T.day(sale.soldAt)], ['Estado', open ? 'Vigente' : `Cancelada el ${T.day(sale.cancelledAt)}`], ['Nota', sale.note ? escaparHTML(sale.note) : '—']];
    const forms = !open ? '' : `<form data-admin-form="sale-payment" data-id="${sale.id}" novalidate><h3>Registrar pago</h3><label for="sp-received">Importe recibido acumulado (MXN)</label><input id="sp-received" name="received" type="text" inputmode="decimal" value="${sale.received}">
        <label for="sp-reference">Referencia (opcional)</label><input id="sp-reference" name="reference" type="text" maxlength="120"><button class="button btn-liquid-light" type="submit">Registrar pago</button></form>
      ${sale.deliveredAt ? '' : `<form data-admin-form="sale-delivery" data-id="${sale.id}" novalidate><h3>Marcar entregada</h3><label for="sd-date">Fecha de entrega</label><input id="sd-date" name="deliveredAt" type="date" min="${sale.soldAt}" max="${today()}" value="${today()}" required><button class="button btn-liquid-light" type="submit">Marcar entregada</button></form>`}
      <form data-admin-form="sale-note" data-id="${sale.id}" novalidate><h3>Nota</h3><label for="sn-note" class="sr-only">Nota</label><textarea id="sn-note" name="note" maxlength="500" rows="3">${escaparHTML(sale.note || '')}</textarea><button class="button btn-liquid-light" type="submit">Guardar nota</button></form>`;
    return `<h2 id="admin-dialog-title">Venta de ${escaparHTML(sale.device.identifier)}</h2><dl class="user-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl>${forms}
      <div class="app-dialog-actions">${open ? T.button('cancel-sale', 'Cancelar venta', 'light', `data-danger="true" data-id="${sale.id}"`) : ''}${T.button('close-dialog', 'Cerrar')}</div>`;
  }

  const confirmations = {cancel:sale => ({titulo:`¿Cancelar la venta de ${sale.device.identifier}?`, texto:'La venta quedará cancelada y el equipo volverá a poder venderse. No se puede deshacer.', accion:'Cancelar venta', peligro:true})};

  return Object.freeze({screen, createForm, detail, confirmations, errorText,
    resetFilters: root => root.querySelector('[data-admin-form="sales-filter"]').reset(),
    periodDates(root, dates) { const form = root.querySelector('[data-admin-form="sales-period"]'); form.elements.since.value = dates.desde; form.elements.until.value = dates.hasta; }});
})();

// ── Administradores ──
// Quién tiene qué capacidad (5.10). La capacidad de super administrador no se ofrece: solo se asigna desde la base.
const AdminAccessViews = (() => {
  const T = AdminTableViews;
  const {tag} = GardenViews;
  const GROUPS = [['Operación', [['ver_flota', 'Flota'], ['atender_soporte', 'Soporte'], ['gestionar_mantenimientos', 'Mantenimientos']]],
    ['Gestión', [['atender_consultas', 'Consultas'], ['gestionar_dispositivos', 'Equipos'], ['gestionar_ventas', 'Ventas'], ['gestionar_guias', 'Guías']]],
    ['Legal', [['gestionar_legales', 'Textos legales'], ['ver_consentimientos', 'Consentimientos']]]];
  const LABELS = Object.fromEntries(GROUPS.flatMap(([, items]) => items).concat([['gestionar_administradores', 'Super administrador']]));
  const ACTIONS = {cambiar_capacidades:'Cambió capacidades', publicar_legal:'Publicó un texto legal', crear_borrador_legal:'Creó un borrador legal', editar_borrador_legal:'Editó un borrador legal',
    eliminar_borrador_legal:'Eliminó un borrador legal', exportar_consentimientos:'Exportó consentimientos', alta_equipo:'Dio de alta un equipo', rotar_credencial:'Rotó una credencial',
    retirar_equipo:'Retiró un equipo', desvincular_dispositivo:'Desvinculó un equipo', registrar_venta:'Registró una venta', registrar_pago:'Registró un pago', entregar_venta:'Marcó una entrega',
    editar_nota_venta:'Editó la nota de una venta', cancelar_venta:'Canceló una venta'};
  const ERRORS = {'capacidad-reservada':'La capacidad de super administrador solo se asigna desde la base de datos.', 'capacidad-propia':'No puedes cambiar tus propias capacidades.',
    'cuenta-no-encontrada':'No hay una cuenta con ese correo.', 'cuenta-no-elegible':'La cuenta debe estar activa y con el correo verificado.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.') => ERRORS[code] || fallback;
  const label = code => LABELS[code] || code;
  const action = name => ACTIONS[name] || name;
  const chips = list => list.length ? list.map(code => tag(label(code), code === 'gestionar_administradores' ? 'ambar' : 'gris')).join(' ') : '—';

  function adminsTab(state) {
    const rows = state.admins.items.map(item => `<tr><td>${escaparHTML(item.email)}${item.superAdmin ? ' ★' : ''}</td><td>${item.name ? escaparHTML(item.name) : '—'}</td><td>${chips(item.capabilities)}</td>
      <td>${item.secondFactor ? '✔' : '✖'}</td><td>${item.lastAccess ? T.merida(item.lastAccess) : '—'}</td><td>${item.email === state.ownEmail ? '<small>Tu cuenta</small>' : T.button('edit', 'Editar', 'light', `data-email="${escaparHTML(item.email)}"`)}</td></tr>`);
    return `<div class="app-actions">${T.button('grant', '+ Dar acceso a una cuenta', 'brand')}</div><section class="bento-panel">${rows.length ? T.table('Administradores', ['Correo', 'Nombre', 'Capacidades', 'Segundo factor', 'Último acceso', ''], rows) : '<p>No hay administradores.</p>'}${T.pager(state.admins)}</section>`;
  }

  function historyTab(state) {
    const rows = state.history.items.map(item => `<tr><td>${T.merida(item.at)}</td><td>${escaparHTML(item.account)}</td><td>${escaparHTML(label(item.capability))}</td><td>${tag(item.action === 'concedida' ? 'Concedida' : 'Retirada', item.action === 'concedida' ? 'verde' : 'rojo')}</td><td>${escaparHTML(item.by)}</td><td>${item.reason ? escaparHTML(item.reason) : '—'}</td></tr>`);
    const capabilities = [['', 'Todas'], ...GROUPS.flatMap(([, items]) => items).concat([['gestionar_administradores', 'Super administrador']])];
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="history-filter" novalidate><div><label for="ah-account">Cuenta</label><input id="ah-account" name="cuenta" type="search" maxlength="60" value="${escaparHTML(state.filters.cuenta || '')}"></div>
      <div><label for="ah-capability">Capacidad</label><select id="ah-capability" name="capacidad">${capabilities.map(([value, text]) => `<option value="${value}"${value === (state.filters.capacidad || '') ? ' selected' : ''}>${text}</option>`).join('')}</select></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}<div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button></div></form>
      ${rows.length ? T.table('Historial de capacidades', ['Fecha y hora', 'Cuenta', 'Capacidad', 'Acción', 'Por', 'Motivo'], rows) : '<p>No hay cambios con estos filtros.</p>'}${T.pager(state.history)}</section>`;
  }

  function activityTab(state) {
    const rows = state.activity.items.map(item => `<tr><td>${T.merida(item.at)}</td><td>${item.actor ? escaparHTML(item.actor) : '—'}</td><td>${escaparHTML(action(item.action))}</td><td>${item.entity ? escaparHTML(item.entity) : '—'}</td><td>${item.result === 'exito' ? 'Éxito' : 'Rechazado'}</td></tr>`);
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="activity-filter" novalidate><div><label for="aa-account">Administrador (correo)</label><input id="aa-account" name="cuenta" type="search" maxlength="60" value="${escaparHTML(state.filters.cuenta || '')}"></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button></div></form>
      ${rows.length ? T.table('Actividad de administradores', ['Fecha y hora', 'Administrador', 'Acción', 'Sobre qué', 'Resultado'], rows) : '<p>No hay actividad registrada.</p>'}${T.pager(state.activity)}</section>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const tab = {administradores:adminsTab, historial:historyTab, actividad:activityTab}[state.tab](state);
    return `${AppViews.heading('Administradores', 'Quién puede qué en el panel.')}${T.tabs([['administradores', 'Administradores'], ['historial', 'Historial'], ['actividad', 'Actividad']], state.tab)}${tab}${T.dialog}`;
  }

  function accessForm({email = '', capabilities = [], editing = false}) {
    const boxes = GROUPS.map(([group, items]) => `<fieldset class="legal-card"><legend>${group}</legend>${items.map(([code, text]) => `<label class="legal-check"><input type="checkbox" name="capability" value="${code}"${capabilities.includes(code) ? ' checked' : ''}><span>${text}</span></label>`).join('')}</fieldset>`).join('');
    return `<h2 id="admin-dialog-title">${editing ? 'Editar acceso' : 'Dar acceso a una cuenta'}</h2><form data-admin-form="access" novalidate>
      <label for="ac-email">Correo de la cuenta</label><input id="ac-email" name="email" type="email" maxlength="254" value="${escaparHTML(email)}"${editing ? ' readonly' : ''} required>
      ${boxes}<p class="user-small-copy">La capacidad de super administrador solo se asigna desde la base de datos.</p>
      <label for="ac-reason">Motivo</label><input id="ac-reason" name="reason" type="text" maxlength="300" required>
      <div class="app-dialog-actions">${T.button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Guardar cambios</button></div></form>`;
  }

  function summaryText(granted, revoked) {
    const names = list => list.length ? list.map(label).join(', ') : 'nada';
    return `Darás: ${names(granted)}. Quitarás: ${names(revoked)}. ¿Continuar?`;
  }
  const confirmation = (granted, revoked) => ({titulo:'¿Cambiar las capacidades de esta cuenta?', texto:summaryText(granted, revoked), accion:'Continuar'});

  return Object.freeze({screen, accessForm, confirmation, errorText});
})();

// ── Legales ──
// Textos legales (5.8). El HTML de la vista previa y de las versiones lo devuelve el servidor ya saneado; aquí no se genera.
const LegalAdminViews = (() => {
  const T = AdminTableViews;
  const {tag} = GardenViews;
  const TYPES = {terminos:'Términos y condiciones', aviso_privacidad:'Aviso de privacidad', politica_cookies:'Política de cookies'};
  const ERRORS = {'version-no-mayor':'La versión debe ser mayor que la vigente.', 'version-existente':'Ya existe esa versión de este documento.', 'documento-publicado':'Una versión publicada no se edita ni se borra: crea una nueva.',
    'stale-record':'Alguien cambió este borrador. Vuelve a abrirlo para ver la versión nueva.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.') => ERRORS[code] || fallback;
  const sha = value => escaparHTML(value.slice(0, 8));

  function listScreen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const {current, drafts, history} = state.data;
    const currentBlock = current ? `<p>Versión vigente: <strong>${escaparHTML(current.version)}</strong> · publicada el ${T.merida(current.publishedAt)}${current.publishedBy ? ` por ${escaparHTML(current.publishedBy)}` : ''} · huella ${sha(current.sha256)}… <a href="#admin/legales/${current.id}">Ver</a></p>` : '<p>Aún no hay una versión publicada.</p>';
    const draftRows = drafts.map(item => `<li><div><strong>${escaparHTML(item.version)}</strong> · ${escaparHTML(item.title)} <small>editado ${T.merida(item.updatedAt)}</small></div>
      <div class="app-actions"><a class="button btn-liquid-light compact" href="#admin/legales/${item.id}">Editar</a>${T.button('preview', 'Vista previa', 'light', `data-id="${item.id}"`)}${T.button('publish', 'Publicar', 'brand', `data-id="${item.id}" data-at="${escaparHTML(item.updatedAt)}" data-version="${escaparHTML(item.version)}"`)}${T.button('remove', 'Eliminar', 'light', `data-danger="true" data-id="${item.id}" data-at="${escaparHTML(item.updatedAt)}"`)}</div></li>`).join('');
    const historyRows = history.map(item => `<li><span>${escaparHTML(item.version)} · ${T.merida(item.publishedAt)}${item.publishedBy ? ` · ${escaparHTML(item.publishedBy)}` : ''}</span> <a href="#admin/legales/${item.id}">Ver</a></li>`).join('');
    return `${AppViews.heading('Textos legales', 'Redacta, previsualiza y publica nuevas versiones.')}${T.tabs(Object.entries(TYPES), state.type)}
      <section class="bento-panel">${currentBlock}</section>
      <section class="bento-panel"><div class="user-section-heading"><div><h2>Borradores</h2></div><a class="button btn-liquid-brand" href="#admin/legales/nuevo-${state.type}">+ Nueva versión</a></div>${draftRows ? `<ul class="legal-list">${draftRows}</ul>` : '<p>No hay borradores.</p>'}</section>
      <section class="bento-panel"><h2>Historial de versiones publicadas</h2>${historyRows ? `<ul class="legal-list">${historyRows}</ul>` : '<p>Sin versiones publicadas.</p>'}</section>${T.dialog}`;
  }

  function editorScreen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const doc = state.document, published = doc && doc.state === 'publicada';
    const title = published ? `${TYPES[doc.type]} · versión ${doc.version}` : doc ? `Editar borrador ${doc.version}` : `Nueva versión · ${TYPES[state.type]}`;
    const back = `<a class="garden-back" href="#admin/legales">← Textos legales</a>`;
    const facts = published ? `<p>${tag('Publicada', 'verde')} ${T.merida(doc.publishedAt)}${doc.publishedBy ? ` · ${escaparHTML(doc.publishedBy)}` : ''} · huella ${sha(doc.sha256)}…</p>` : '';
    const toolbar = published ? '' : `<div class="legal-toolbar" role="group" aria-label="Formato">${[['h2', 'Título'], ['ul', 'Lista'], ['strong', 'Negrita'], ['a', 'Enlace']].map(([tagName, text]) => T.button('tag', text, 'light', `data-tag="${tagName}"`)).join('')}</div>`;
    const form = `<form data-admin-form="legal" novalidate><label for="lg-version">Versión (formato 1.2)</label><input id="lg-version" name="version" type="text" maxlength="11" placeholder="1.2" value="${escaparHTML(doc?.version || '')}"${published ? ' readonly' : ''} required>
      <label for="lg-title">Título</label><input id="lg-title" name="title" type="text" maxlength="120" value="${escaparHTML(doc?.title || TYPES[state.type] || '')}"${published ? ' readonly' : ''} required>
      <label for="lg-content">Contenido</label>${toolbar}<textarea id="lg-content" name="content" rows="18" maxlength="28000"${published ? ' readonly' : ''} required>${escaparHTML(doc?.content || '')}</textarea>
      ${published ? '' : `<div class="app-actions"><button class="button btn-liquid-brand" type="submit">Guardar borrador</button>${T.button('preview-editor', 'Vista previa')}${doc ? T.button('publish-editor', 'Publicar', 'brand') : ''}</div>`}</form>`;
    return `${back}${AppViews.heading(title)}${facts}<div class="legal-editor"><section class="bento-panel">${form}</section><section class="bento-panel"><h2>Vista previa</h2><div class="legal-preview" data-legal-preview>${doc ? doc.html : '<p>Pulsa «Vista previa» para ver el texto como lo verá el público.</p>'}</div></section></div>${T.dialog}`;
  }

  const confirmations = {
    publish:(type, version) => ({titulo:`¿Publicar la versión ${version} de ${TYPES[type]}?`,
      texto:`Todas las cuentas recibirán un aviso y deberán ${type === 'politica_cookies' ? 'volver a decidir sobre cookies' : 'aceptarla al entrar'}. Una versión publicada no se puede editar ni borrar.`, accion:'Publicar'}),
    remove:{titulo:'¿Eliminar este borrador?', texto:'No se puede deshacer.', accion:'Eliminar', peligro:true}};

  // El HTML ya viene saneado del servidor; el navegador solo lo coloca.
  function showPreview(root, html) { root.querySelector('[data-legal-preview]').innerHTML = html; }
  function previewDialog(html) { return `<h2 id="admin-dialog-title">Vista previa</h2><div class="legal-preview">${html}</div><div class="app-dialog-actions">${T.button('close-dialog', 'Cerrar')}</div>`; }
  // Inserta una etiqueta en el texto seleccionado del contenido.
  function insertTag(root, name) {
    const area = root.querySelector('[name=content]'), start = area.selectionStart, end = area.selectionEnd, picked = area.value.slice(start, end);
    const wrapped = {h2:`<h2>${picked || 'Título'}</h2>`, strong:`<strong>${picked || 'texto'}</strong>`, ul:`<ul>\n  <li>${picked || 'elemento'}</li>\n</ul>`, a:`<a href="https://">${picked || 'enlace'}</a>`}[name];
    area.setRangeText(wrapped, start, end, 'end');
    area.focus();
  }

  return Object.freeze({listScreen, editorScreen, confirmations, errorText, showPreview, previewDialog, insertTag});
})();

// ── Consentimientos ──
// Bitácora de consentimientos (5.9): solo lectura. La IP ya viene recortada de la base.
const ConsentViews = (() => {
  const T = AdminTableViews;
  const {tag} = GardenViews;
  const options = (items, selected = '') => items.map(([value, label]) => `<option value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`).join('');
  const share = ({accepted, accounts, version}) => version ? `${accepted} de ${accounts} cuentas (versión ${escaparHTML(version)})` : 'Sin versión publicada';

  function filters(values) {
    return `<form class="care-filters" data-admin-form="consent-filter" novalidate>
      <div><label for="cs-document">Documento</label><select id="cs-document" name="documento">${options([['', 'Todos'], ['terminos', 'Términos'], ['aviso', 'Aviso'], ['cookies', 'Cookies']], values.documento)}</select></div>
      <div><label for="cs-decision">Decisión</label><select id="cs-decision" name="decision">${options([['', 'Todas'], ['acepto', 'Aceptó'], ['rechazo', 'Rechazó']], values.decision)}</select></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}
      <div><label for="cs-account">Buscar correo</label><input id="cs-account" name="cuenta" type="search" maxlength="60" value="${escaparHTML(values.cuenta || '')}"></div>
      <div><label for="cs-version">Versión</label><input id="cs-version" name="version" type="text" maxlength="11" placeholder="1.1" value="${escaparHTML(values.version || '')}"></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button>${T.button('clear', 'Limpiar')}</div></form>`;
  }

  // La exportación es una descarga: si el filtro rebasa el tope del servidor, se avisa aquí en lugar de descargar un error.
  function exportAction({exportUrl, list, exportLimit}) {
    if(list.total > exportLimit) return `<div><button class="button btn-liquid-light" type="button" disabled>Exportar CSV</button><p class="user-small-copy">Acota el filtro: se exportan hasta ${exportLimit} filas.</p></div>`;
    return `<a class="button btn-liquid-light" href="${escaparHTML(exportUrl)}" download="consentimientos.csv">Exportar CSV</a>`;
  }

  function row(item) {
    return `<tr><td>${T.merida(item.at)}</td><td>${escaparHTML(item.account)}</td><td>${escaparHTML(item.what)}</td><td>${escaparHTML(item.version)}</td><td>${tag(item.decision, item.decision === 'Aceptó' ? 'verde' : 'rojo')}</td><td>${item.ip ? escaparHTML(item.ip) : '—'}</td><td>${item.browser ? escaparHTML(item.browser) : '—'}</td><td>${T.button('row', 'Ver', 'light', `data-id="${item.id}"`)}</td></tr>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const {summary, list} = state;
    const stats = summary.statistics.percent === null ? 'Sin navegadores' : `${summary.statistics.percent}% (${summary.statistics.accepted} de ${summary.statistics.browsers})`;
    const cards = [['Términos vigentes aceptados', share(summary.terms)], ['Aviso vigente aceptado', share(summary.privacy)], ['Navegadores con estadísticas', stats]]
      .map(([label, value]) => `<article class="bento-panel user-metric"><h2>${label}</h2><strong class="consent-figure">${value}</strong></article>`).join('');
    const body = list.items.length ? T.table('Bitácora de consentimientos', ['Fecha y hora (Mérida)', 'Cuenta', 'Qué', 'Versión', 'Decisión', 'IP', 'Navegador', ''], list.items.map(row)) : '<div class="user-empty-inline"><p>No hay registros con estos filtros.</p></div>';
    return `<div class="page-heading"><div><h1>Bitácora de consentimientos</h1><p>Quién aceptó qué, cuándo y desde dónde.</p></div>${exportAction(state)}</div>
      <section class="user-summary-metrics" aria-label="Resumen de consentimientos">${cards}</section><section class="bento-panel">${filters(state.filters)}${body}${T.pager(list)}</section>${T.dialog}`;
  }

  function detail(item) {
    const facts = [['Fecha y hora (Mérida)', T.merida(item.at)], ['Cuenta', escaparHTML(item.account)], ['Ámbito', escaparHTML(item.scope)], ['Qué', escaparHTML(item.what)], ['Versión', escaparHTML(item.version)],
      ['Decisión', escaparHTML(item.decision)], ['Finalidad', item.purpose ? escaparHTML(item.purpose) : '—'], ['IP (recortada)', item.ip ? escaparHTML(item.ip) : '—'], ['Navegador', item.browser ? escaparHTML(item.browser) : '—']];
    const history = item.scope === 'cuenta' && item.account.includes('@') ? T.button('account-history', 'Ver historial de esta cuenta', 'light', `data-account="${escaparHTML(item.account)}"`) : '';
    return `<h2 id="admin-dialog-title">Registro de consentimiento</h2><dl class="user-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl><div class="app-dialog-actions">${history}${T.button('close-dialog', 'Cerrar')}</div>`;
  }

  return Object.freeze({screen, detail,
    resetFilters: root => root.querySelector('[data-admin-form="consent-filter"]').reset()});
})();

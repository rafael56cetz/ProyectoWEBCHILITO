// VISTA · Administración: flota, consola remota, buzón de consultas, ventas, administradores, textos legales y consentimientos.
// Define: FleetViews, ConsoleViews, InquiryViews, SalesViews, AdminAccessViews, LegalAdminViews, ConsentViews.

// ── Administracion ──
// Telemetría de flota (5.1). Todo dato del servidor entra escapado.
const FleetViews = (() => {
  const T = AdminTableViews, {tag, chart} = GardenViews;
  const STATES = {disponible:'Disponible', vinculado:'Vinculado', retirado:'Retirado'};
  const LINKS = {nunca:['Sin conexión aún', 'gris'], en_linea:['En línea', 'verde'], desconectado:['Desconectado', 'rojo']};
  const PROBLEMS = {diagnostic:'Autodiagnóstico con fallas', order:'Orden fallida', offline:'Sin conexión por más de 24 horas'};
  const when = value => value ? AppViews.date(value) : 'Sin datos';
  const none = value => value ? escaparHTML(value) : '—';
  const options = (items, selected = '') => items.map(([value, label]) => `<option value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`).join('');
  const tile = AppViews.kpi;

  function filters(values) {
    return `<form class="care-filters" data-admin-form="fleet-filter" novalidate>
      <div><label for="fleet-search">Buscar</label><input id="fleet-search" name="busqueda" type="search" maxlength="60" placeholder="Identificador, MAC o correo" value="${escaparHTML(values.busqueda || '')}"></div>
      <div><label for="fleet-state">Estado</label><select id="fleet-state" name="estado">${options([['', 'Todos'], ...Object.entries(STATES)], values.estado || '')}</select></div>
      <div><label for="fleet-link">Conexión</label><select id="fleet-link" name="conexion">${options([['', 'Todas'], ...Object.entries(LINKS).map(([value, [label]]) => [value, label])], values.conexion || '')}</select></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button>${T.button('clear', 'Limpiar')}</div></form>`;
  }

  // Con la capacidad de inventario la fila abre la ficha del equipo; sin ella, un panel de solo lectura.
  function row(item, access) {
    const open = access.inventory ? `<a class="button btn-liquid-light compact" href="#admin/equipos/${escaparHTML(item.id)}">Ver<span class="sr-only"> ${escaparHTML(item.identifier)}</span></a>`
      : T.button('peek', 'Ver', 'light', `data-id="${escaparHTML(item.id)}"`);
    return `<tr><td><strong>${escaparHTML(item.identifier)}</strong></td><td>${none(item.garden)}</td><td>${none(item.owner)}</td><td>${tag(...LINKS[item.connection])}</td>
      <td>${when(item.lastReadingAt)}</td><td>${none(item.firmware)}</td><td>${item.lastReviewAt ? when(item.lastReviewAt) : 'Sin revisión'}</td><td>${open}</td></tr>`;
  }

  function problem(item) {
    const order = item.detail ? ` · ${escaparHTML(item.detail)}` : '';
    return `<li><span>${icon('alert')}</span><div><p>${PROBLEMS[item.type] || 'Problema'}${order}</p><small>${escaparHTML(item.identifier)} · ${when(item.at)}</small></div></li>`;
  }

  function screen(state, access) {
    if(state.status !== 'ready') return T.status(state.status);
    const {totals, trends, problems, items, page, total} = state.data;
    const body = items.length ? T.table('Equipos de la flota', ['Identificador', 'Huerto', 'Dueño', 'Conexión', 'Última lectura', 'Firmware', 'Última revisión', ''], items.map(item => row(item, access)))
      : AppViews.empty('No hay equipos con estos filtros', 'Cambia o limpia los filtros para ver más.');
    return `<div class="page-heading"><div><h1>Telemetría de flota</h1><p>Equipos vinculados, su conexión y los problemas de las últimas 24 horas.</p></div>${T.button('refresh', `${icon('refresh')}<span>Actualizar</span>`)}</div>
      <section class="user-summary-metrics" aria-label="Estado de la flota">${tile('Equipos vinculados', totals.linked)}${tile('En línea', totals.online)}${tile('Desconectados', totals.offline)}${tile('Problemas (24 h)', totals.problems)}</section>
      <section class="user-chart-grid-layout" aria-label="Tendencias de 7 días">${chart('Humedad media del sustrato · 7 días', trends.moisture, '%', '7d', 'fleet-soil')}${chart('Temperatura media · 7 días', trends.temperature, '°C', '7d', 'fleet-temp')}</section>
      <section class="bento-panel"><h2>Equipos</h2>${filters(state.filters)}${body}${T.pager({page, total})}</section>
      <section class="bento-panel"><h2>Problemas recientes</h2>${problems.length ? `<ol class="user-history-list">${problems.map(problem).join('')}</ol>` : AppViews.empty('No hay problemas', 'Ningún equipo reportó fallas en las últimas 24 horas.')}</section>${T.dialog}`;
  }

  function peek(item) {
    const facts = [['Identificador', escaparHTML(item.identifier)], ['Estado', STATES[item.state] || '—'], ['Conexión', tag(...LINKS[item.connection])], ['Huerto', none(item.garden)],
      ['Dueño', none(item.owner)], ['Firmware', none(item.firmware)], ['Última conexión', when(item.lastConnectionAt)], ['Última lectura', when(item.lastReadingAt)],
      ['Última revisión', item.lastReviewAt ? when(item.lastReviewAt) : 'Sin revisión']];
    return `<h2 id="admin-dialog-title">${escaparHTML(item.identifier)}</h2><dl class="user-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl>
      <div class="app-dialog-actions">${T.button('close-dialog', 'Cerrar')}</div>`;
  }

  return Object.freeze({screen, peek, paint: (root, html) => T.paint(root, html), openDialog: (root, html) => T.open(root, html), closeDialog: root => T.dismiss(root),
    resetFilters(root) { root.querySelector('[data-admin-form="fleet-filter"]').reset(); }});
})();

// Consola remota (5.2). Bandeja en #admin/soporte y cada caso en su pantalla, #admin/soporte/<folio>. Atiende una cuenta y solo ella
// se conecta; la sesión técnica se ve en vivo mientras la persona no la revoque.
const ConsoleViews = (() => {
  const T = AdminTableViews, {tag, orderCard} = GardenViews, act = (...args) => T.button(...args);
  const TABS = [['abierto', 'Nuevos'], ['en_atencion', 'En atención'], ['resuelto', 'Resueltos']];
  const CASE_STATES = {abierto:['Nuevo', 'ambar'], en_atencion:['En atención', 'verde'], resuelto:['Resuelto', 'gris']};
  const AUTHORIZATION = {vigente:['Vigente', 'verde'], revocada:['Revocada', 'rojo'], vencida:['Vencida', 'gris']};
  const CLOSINGS = {revocada:'La persona revocó el acceso. La sesión se cerró.', vencida:'La autorización venció. La sesión se cerró.',
    caso_cerrado:'El caso se cerró. La sesión terminó.', manual:'La sesión técnica se cerró.', cierre_sesion:'La sesión técnica se cerró.'};
  const ERRORS = {'caso-ya-atendido':'Este caso ya lo atiende otra persona o ya está cerrado.', 'caso-no-tuyo':'Solo quien atiende el caso puede conectarse, dar órdenes o resolverlo.',
    'autorizacion-no-vigente':'La persona ya no autoriza el acceso o la autorización venció.', 'sesion-abierta':'Ya tienes una sesión técnica abierta. Ciérrala antes de conectarte a otro caso.',
    'sesion-cerrada':'La sesión técnica ya se cerró o la persona retiró su autorización.', 'caso-cerrado':'Este caso ya está cerrado.',
    'orden-en-curso':'Ya hay una orden igual esperando la respuesta del equipo.', 'not-found':'Ese caso o esa sesión ya no existe.',
    'access-denied':'Tu cuenta no tiene acceso a esta operación.', 'rate-limited':'Demasiadas operaciones seguidas. Espera un momento.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Inténtalo de nuevo.') => ERRORS[code] || fallback;
  const closingText = reason => CLOSINGS[reason] || CLOSINGS.manual;
  const when = value => AppViews.date(value);
  const none = value => value ? escaparHTML(value) : '—';
  const incident = value => GardenModel.INCIDENTS[value] || escaparHTML(value);
  const number = value => Number.isFinite(value) ? AppModel.number(value) : null;
  const plantOptions = [1, 2, 3].map(plant => `<option value="${plant}">Planta ${plant}</option>`).join('');
  const secondOptions = Array.from({length:ConsoleService.bombSeconds.max - ConsoleService.bombSeconds.min + 1}, (_, index) => `<option value="${ConsoleService.bombSeconds.min + index}">${ConsoleService.bombSeconds.min + index} s</option>`).join('');

  function authorization(caso) {
    const [label, tone] = AUTHORIZATION[caso.authorization];
    return `${tag(label, tone)}${caso.authorization === 'vigente' ? ` vence en ${GardenModel.lapse(caso.authorizedUntil)}` : ''}`;
  }

  function item(caso) {
    const remaining = caso.state === 'resuelto' ? (ConsoleService.results[caso.result] || '—') : caso.authorization === 'vigente' ? `${GardenModel.lapse(caso.authorizedUntil)} restantes` : AUTHORIZATION[caso.authorization][0];
    return `<li><button type="button" class="console-item" data-admin-action="open-case" data-folio="${escaparHTML(caso.folio)}">
      <span class="console-item-title"><strong>${escaparHTML(caso.folio)}</strong> · ${incident(caso.incident)}</span><small>${when(caso.createdAt)}</small>
      <small>${escaparHTML(caso.email)} · ${escaparHTML(caso.device)} · ${escaparHTML(remaining)}</small></button></li>`;
  }

  function inbox(state) {
    const {items, page, total} = state.inbox;
    return `<section class="bento-panel console-inbox" aria-label="Bandeja">${items.length ? `<ul class="console-list">${items.map(item).join('')}</ul>` : AppViews.empty('No hay casos en esta pestaña', 'Cuando llegue uno aparecerá aquí.')}${T.pager({page, total})}</section>`;
  }

  const confirmations = {
    reboot:{titulo:'¿Reiniciar el equipo?', texto:'El equipo dejará de responder unos segundos.', accion:'Reiniciar equipo', peligro:true},
    pump:(plant, seconds) => ({titulo:`¿Probar la bomba de la planta ${plant}?`, texto:`La bomba funcionará ${seconds} s y moverá agua de verdad.`, accion:'Probar bomba'}),
    resolve:{titulo:'¿Resolver el caso?', texto:'Se cerrará el caso y terminará el acceso. No se puede deshacer.', accion:'Resolver caso', peligro:true}};

  // Una orden igual (tipo y planta) en curso bloquea su botón: la base no admite dos a la vez.
  const IN_FLIGHT = ['pendiente', 'enviado'];
  const busyKeys = orders => new Set(orders.filter(order => IN_FLIGHT.includes(order.state)).map(order => `${order.type}:${order.plant || 0}`));
  function lockOrders(root, orders) {
    const busy = busyKeys(orders), names = [];
    for(const button of root.querySelectorAll('[data-admin-action="order"]')) {
      button.disabled = busy.has(`${button.dataset.type}:0`);
      if(button.disabled) names.push(button.textContent.trim());
    }
    const pump = root.querySelector('[data-admin-form="pump"]');
    if(pump) {
      const plant = pump.elements.plant.value, submit = pump.querySelector('[type=submit]');
      submit.disabled = busy.has(`probar_bomba:${plant}`);
      if(submit.disabled) names.push(`Probar bomba · planta ${plant}`);
    }
    const note = root.querySelector('[data-console-busy]');
    if(!note) return;
    note.hidden = !names.length;
    note.textContent = names.length ? `En curso: ${names.join(', ')}. Espera a que el equipo responda o a que la orden expire para enviar otra igual.` : '';
  }

  const sessionActions = () => `<p class="user-small-copy" id="console-busy" data-console-busy role="status" hidden></p><div class="console-actions" role="group" aria-label="Acciones del equipo" aria-describedby="console-busy">
      ${act('order', 'Pedir lectura', 'light', 'data-type="lectura_inmediata"')}${act('order', 'Revisar equipo', 'light', 'data-type="autodiagnostico"')}
      ${act('order', 'Apagar lámpara', 'light', 'data-type="lampara_apagar"')}${act('order', 'Restaurar lámpara', 'light', 'data-type="lampara_automatico"')}
      ${act('order', 'Encender ventilador', 'light', 'data-type="ventilador_encender"')}${act('order', 'Apagar ventilador', 'light', 'data-type="ventilador_apagar"')}
      ${act('order', 'Reiniciar equipo', 'light', 'data-type="reiniciar" data-danger="true"')}</div>
    <form class="console-pump" data-admin-form="pump" novalidate><div><label for="pump-plant">Planta</label><select id="pump-plant" name="plant">${plantOptions}</select></div>
      <div><label for="pump-seconds">Duración</label><select id="pump-seconds" name="seconds">${secondOptions}</select></div><button class="button btn-liquid-light" type="submit">Probar bomba</button></form>`;

  // Marco de la sesión técnica: lo que cambia cada 10 s va en los tres espacios `data-console-*` y se rellena con `live`.
  function sessionFrame(caso, session) {
    return `<section class="bento-panel console-session" aria-labelledby="console-session-title"><div class="console-session-head"><h2 id="console-session-title">Sesión técnica · ${escaparHTML(caso.device)}</h2>
        <p>Abierta ${GardenModel.ago(session.startedAt) || ''}</p>${act('close-session', 'Cerrar sesión técnica', 'light')}</div>
      <div data-console-live><p>Consultando el equipo…</p></div>${sessionActions()}
      <h3>Eventos del equipo · últimas 24 h</h3><div data-console-events></div></section>`;
  }

  // Todas las órdenes de soporte del caso, de cualquier sesión, con su estado: una pendiente se sigue viendo al volver.
  const orderList = (orders, diagnostic = null) => (orders.length ? orders.map(orderCard).join('') : '<p>Todavía no hay órdenes en este caso.</p>') + SupportViews.diagnosticPanel(diagnostic);
  const ordersPanel = orders => `<section class="bento-panel" aria-labelledby="console-orders-title"><h2 id="console-orders-title">Órdenes del caso</h2><div data-console-orders>${orderList(orders)}</div></section>`;

  function readings(data) {
    if(!data) return '<p>El equipo todavía no envía lecturas.</p>';
    const read = (value, unit) => number(value) === null ? 'Sin lectura' : `${number(value)}${unit}`;
    const tank = data.tankHasWater === null ? 'Sin dato' : data.tankHasWater ? 'Con agua' : 'Sin agua';
    const plants = data.plants.map(plant => `<div><dt>Planta ${plant.number}</dt><dd>${read(plant.moisture, ' %')}${plant.adc === null ? '' : ` · ADC ${plant.adc}`}</dd></div>`).join('');
    return `<dl class="user-facts"><div><dt>Ambiente</dt><dd>${read(data.temperature, ' °C')} / ${read(data.airHumidity, ' %')}</dd></div><div><dt>Luz</dt><dd>${read(data.light, ' lx')}</dd></div>
      <div><dt>Depósito</dt><dd>${tank}</dd></div>${plants}<div><dt>Lectura de</dt><dd>${when(data.measuredAt)}</dd></div></dl>`;
  }

  function events(items) {
    if(!items.length) return '<p>Sin eventos en las últimas 24 horas.</p>';
    return `<ol class="user-history-list">${items.map(event => `<li><span>${icon('clock')}</span><div><p>${escaparHTML(TechnicalViews.eventLabel(event.type))}${event.detail ? ` · ${escaparHTML(event.detail)}` : ''}</p><small>${when(event.at)}</small></div></li>`).join('')}</ol>`;
  }

  function live(data) {
    const link = GardenModel.connection(data.device);
    return {live:`<p class="console-status">${tag(link.text.split(' · ')[0], link.tone)} ${escaparHTML(link.text.split(' · ').slice(1).join(' · '))}</p>${readings(data.readings)}`,
      orders:orderList(data.orders, data.diagnostic),
      events:events(data.events)};
  }

  function resolution(caso) {
    return `<section class="bento-panel"><form data-admin-form="resolve" novalidate><h2>Resolver el caso</h2><label for="console-result">Resultado</label>
      <select id="console-result" name="result">${Object.entries(ConsoleService.results).map(([value, label]) => `<option value="${value}">${escaparHTML(label)}</option>`).join('')}</select>
      <label for="console-note">Nota (obligatoria con «Otro»)</label><textarea id="console-note" name="note" rows="3" maxlength="500"></textarea>
      <p class="user-small-copy">Resolver termina el acceso de la persona y cierra la sesión técnica.</p><button class="button btn-liquid-brand" type="submit">Resolver caso</button></form></section>`;
  }

  function detail(state) {
    const {case: caso, diagnostic, session, orders} = state.detail;
    const [label, tone] = CASE_STATES[caso.state];
    const facts = [['Persona', none(caso.person)], ['Correo', escaparHTML(caso.email)], ['Huerto', escaparHTML(caso.garden)], ['Equipo', escaparHTML(caso.device)],
      ['Problema', incident(caso.incident)], ['Nota', none(caso.note)], ['Autorización', authorization(caso)], ['Atiende', none(caso.attendedBy)]];
    const closed = caso.state === 'resuelto' ? `<p>Resuelto el ${when(caso.closedAt)} · ${escaparHTML(ConsoleService.results[caso.result] || '—')}${caso.resolutionNote ? ` · ${escaparHTML(caso.resolutionNote)}` : ''}</p>` : '';
    const action = caso.state === 'abierto' ? act('attend', 'Atender', 'brand')
      : caso.state === 'en_atencion' && !caso.mine ? `<p>Lo atiende ${escaparHTML(caso.attendedBy)}.</p>`
      : caso.state === 'en_atencion' && !session ? act('connect', 'Conectar', 'brand', caso.authorization === 'vigente' ? '' : 'disabled') : '';
    const mine = caso.state === 'en_atencion' && caso.mine;
    return `<section class="bento-panel console-detail"><h2>Caso <span class="folio">${escaparHTML(caso.folio)}</span> ${tag(label, tone)}</h2>
        <dl class="user-facts">${facts.map(([name, value]) => `<div><dt>${name}</dt><dd>${value}</dd></div>`).join('')}</dl>${closed}
        ${diagnostic ? `<h3>Autodiagnóstico adjunto</h3>${SupportViews.diagnosticPanel(diagnostic)}` : ''}<div class="app-actions">${action}</div></section>
      ${mine && session ? sessionFrame(caso, session) : ''}${orders.length || mine ? ordersPanel(orders) : ''}${mine ? resolution(caso) : ''}`;
  }

  const heading = () => `<div class="page-heading"><div><h1>Consola remota</h1><p>Atiende los casos con la autorización de la persona. Todo queda en la auditoría.</p></div>${act('refresh', `${icon('refresh')}<span>Actualizar</span>`)}</div>`;

  function inboxScreen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const tabs = TABS.map(([id, name]) => [id, `${name} (${state.counts[id]})`]);
    return `${heading()}${T.tabs(tabs, state.tab)}${inbox(state)}`;
  }

  function caseScreen(state) {
    const back = '<a class="garden-back" href="#admin/soporte">← Volver a la bandeja</a>';
    if(state.status === 'not-found') return `${back}${heading()}<section class="bento-panel">${AppViews.empty('Este caso no existe', 'Revisa el folio o vuelve a la bandeja.')}</section>`;
    if(state.status !== 'ready') return back + T.status(state.status);
    return `${back}${heading()}<div class="console-side">${detail(state)}</div>`;
  }

  return Object.freeze({inboxScreen, caseScreen, confirmations, errorText, closingText, lockOrders,
    paint: (root, html) => T.paint(root, html),
    paintLive(root, data) {
      const parts = live(data);
      for(const [name, html] of Object.entries(parts)) { const slot = root.querySelector(`[data-console-${name}]`); if(slot) slot.innerHTML = html; }
      lockOrders(root, data.orders);
    }});
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
  const confirmations = {archive:{titulo:'¿Archivar esta consulta?', texto:'Saldrá de la lista de pendientes. La verás en «Archivadas».', accion:'Archivar'}};
  return Object.freeze({shell, item, mount, confirmations});
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
      : AppViews.empty('No hay ventas con estos filtros', 'Cambia o limpia los filtros para ver más.');
    return `<section class="bento-panel">${filters(state.filters, catalog.municipalities)}${body}${T.pager(list)}</section>`;
  }

  function summaryTab(state) {
    const {summary, preset} = state;
    const periods = [['month', 'Este mes'], ['previous', 'Mes anterior'], ['all', 'Todo'], ['custom', 'Personalizado']];
    const tiles = [['Ventas', summary.sales], ['Importe vendido', T.money(summary.sold)], ['Cobrado', T.money(summary.collected)], ['Por cobrar', T.money(summary.pending)]]
      .map(([label, value]) => AppViews.kpi(label, value)).join('');
    const rows = summary.byMunicipality.map(item => `<tr><td>${escaparHTML(item.municipality)}</td><td>${item.sales}</td><td>${T.money(item.sold)}</td><td>${T.money(item.collected)}</td><td>${T.money(item.pending)}</td></tr>`);
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="sales-period" novalidate><div><label for="sale-preset">Periodo</label><select id="sale-preset" name="preset">${options(periods, preset)}</select></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}<div class="app-actions"><button class="button btn-liquid-brand" type="submit">Aplicar</button></div></form></section>
      <section class="user-summary-metrics" aria-label="Resumen de ventas">${tiles}</section>
      <section class="bento-panel"><h2>Por municipio</h2>${rows.length ? T.table('Ventas por municipio', ['Municipio', 'Ventas', 'Vendido', 'Cobrado', 'Por cobrar'], rows) : AppViews.empty('No hay ventas en este periodo')}</section>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    return `${AppViews.heading('Ventas', 'Registra ventas, pagos y entregas de equipos.')}${T.tabs([['ventas', 'Ventas'], ['resumen', 'Resumen']], state.tab, state.tab === 'ventas' ? T.button('create', '+ Registrar venta', 'brand') : '')}${state.tab === 'resumen' ? summaryTab(state) : salesTab(state)}${T.dialog}`;
  }

  function createForm(catalog) {
    return `<h2 id="admin-dialog-title">Registrar venta</h2><form data-admin-form="sale-create" novalidate>
      <label for="sc-device">Equipo</label><select id="sc-device" name="device" required>${options([['', 'Elige un equipo'], ...catalog.sellable.map(item => [item.id, item.identifier])])}</select>
      <label for="sc-buyer">Nombre del comprador</label><input id="sc-buyer" name="buyer" type="text" maxlength="60" autocomplete="off" required data-campo="persona">
      <label for="sc-email">Correo del comprador</label><input id="sc-email" name="email" type="email" maxlength="254" required>
      <label for="sc-municipality">Municipio</label><select id="sc-municipality" name="municipality" required>${options([['', 'Elige un municipio'], ...catalog.municipalities.map(name => [name, name])])}</select>
      <label for="sc-price">Precio total (MXN)</label><input id="sc-price" name="price" type="text" inputmode="decimal" maxlength="11" autocomplete="off" placeholder="3500.00" required data-campo="dinero">
      <label for="sc-received">Importe recibido (MXN)</label><input id="sc-received" name="received" type="text" inputmode="decimal" maxlength="11" autocomplete="off" value="0" data-campo="dinero">
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
    const forms = !open ? '' : `<form data-admin-form="sale-payment" data-id="${sale.id}" novalidate><h3>Registrar pago</h3><label for="sp-received">Importe recibido acumulado (MXN)</label><input id="sp-received" name="received" type="text" inputmode="decimal" maxlength="11" autocomplete="off" value="${sale.received}" data-campo="dinero">
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
  // El super administrador tiene todas las capacidades: una sola insignia. Los demás, hasta 3 y «+N» con la lista completa como título.
  const MAX_CHIPS = 3;
  function chips(list, superAdmin = false) {
    if(superAdmin) return tag('Super administrador · todas', 'ambar');
    if(!list.length) return '—';
    const extra = list.slice(MAX_CHIPS);
    const more = extra.length ? `<span class="badge tone-gris" title="${escaparHTML(list.map(label).join(', '))}">+${extra.length}</span>` : '';
    return list.slice(0, MAX_CHIPS).map(code => tag(label(code), 'gris')).join(' ') + (more && ` ${more}`);
  }

  function adminsTab(state) {
    const rows = state.admins.items.map(item => `<tr><td>${escaparHTML(item.email)}${item.superAdmin ? ' ★' : ''}</td><td>${item.name ? escaparHTML(item.name) : '—'}</td><td>${chips(item.capabilities, item.superAdmin)}</td>
      <td>${item.secondFactor ? tag('Activado', 'verde') : tag('Sin activar', 'rojo')}</td><td>${item.lastAccess ? T.merida(item.lastAccess) : '—'}</td><td>${item.email === state.ownEmail ? '<span class="cell-note">Tu cuenta</span>' : T.button('edit', 'Editar', 'light', `data-email="${escaparHTML(item.email)}"`)}</td></tr>`);
    return `<section class="bento-panel">${rows.length ? T.table('Administradores', ['Correo', 'Nombre', 'Capacidades', 'Segundo factor', 'Último acceso', ''], rows) : '<p>No hay administradores.</p>'}${T.pager(state.admins)}</section>`;
  }

  function historyTab(state) {
    const rows = state.history.items.map(item => `<tr><td>${T.merida(item.at)}</td><td>${escaparHTML(item.account)}</td><td>${escaparHTML(label(item.capability))}</td><td>${tag(item.action === 'concedida' ? 'Concedida' : 'Retirada', item.action === 'concedida' ? 'verde' : 'rojo')}</td><td>${escaparHTML(item.by)}</td><td>${item.reason ? escaparHTML(item.reason) : '—'}</td></tr>`);
    const capabilities = [['', 'Todas'], ...GROUPS.flatMap(([, items]) => items).concat([['gestionar_administradores', 'Super administrador']])];
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="history-filter" novalidate><div><label for="ah-account">Cuenta</label><input id="ah-account" name="cuenta" type="search" maxlength="60" value="${escaparHTML(state.filters.cuenta || '')}"></div>
      <div><label for="ah-capability">Capacidad</label><select id="ah-capability" name="capacidad">${capabilities.map(([value, text]) => `<option value="${value}"${value === (state.filters.capacidad || '') ? ' selected' : ''}>${text}</option>`).join('')}</select></div>
      ${T.dateField('since', 'Desde')}${T.dateField('until', 'Hasta')}<div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button></div></form>
      ${rows.length ? T.table('Historial de capacidades', ['Fecha y hora', 'Cuenta', 'Capacidad', 'Acción', 'Por', 'Motivo'], rows) : AppViews.empty('No hay cambios con estos filtros')}${T.pager(state.history)}</section>`;
  }

  function activityTab(state) {
    const rows = state.activity.items.map(item => `<tr><td>${T.merida(item.at)}</td><td>${item.actor ? escaparHTML(item.actor) : '—'}</td><td>${escaparHTML(action(item.action))}</td><td>${item.entity ? escaparHTML(item.entity) : '—'}</td><td>${item.result === 'exito' ? 'Éxito' : 'Rechazado'}</td></tr>`);
    return `<section class="bento-panel"><form class="care-filters" data-admin-form="activity-filter" novalidate><div><label for="aa-account">Administrador (correo)</label><input id="aa-account" name="cuenta" type="search" maxlength="60" value="${escaparHTML(state.filters.cuenta || '')}"></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button></div></form>
      ${rows.length ? T.table('Actividad de administradores', ['Fecha y hora', 'Administrador', 'Acción', 'Sobre qué', 'Resultado'], rows) : AppViews.empty('No hay actividad registrada')}${T.pager(state.activity)}</section>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const tab = {administradores:adminsTab, historial:historyTab, actividad:activityTab}[state.tab](state);
    return `${AppViews.heading('Administradores', 'Quién puede qué en el panel.')}${T.tabs([['administradores', 'Administradores'], ['historial', 'Historial'], ['actividad', 'Actividad']], state.tab, state.tab === 'administradores' ? T.button('grant', '+ Dar acceso a una cuenta', 'brand') : '')}${tab}${T.dialog}`;
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
    'stale-record':'Alguien cambió este borrador. Vuelve a abrirlo para ver la versión nueva.', 'documento-no-docx':'Sube un documento de Word guardado como .docx.',
    'documento-ilegible':'No se pudo leer el documento. Ábrelo en Word y guárdalo de nuevo como .docx.', 'documento-grande':'El documento pasa de 2 MB.',
    'request-too-large':'Es demasiado grande: un .docx puede pesar hasta 2 MB y el texto del borrador hasta 256 KB.', 'pegado-grande':'Lo que pegaste pasa de 256 KB. Pégalo por partes o sube el .docx.', 'documento-largo':'El texto pasa de 200 000 caracteres. Divide el documento.'};
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
    const upload = published ? '' : `<div class="legal-upload">${T.button('upload', `${icon('document')}<span>Subir documento (.docx)</span>`, 'accent', 'aria-describedby="lg-upload-help"')}
      <p class="user-small-copy" id="lg-upload-help">Sube tu Word y se conserva el formato.</p>
      <input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" data-legal-file hidden></div>`;
    const form = `<form data-admin-form="legal" novalidate><label for="lg-version">Versión (formato 1.2)</label><input id="lg-version" name="version" type="text" inputmode="decimal" maxlength="11" placeholder="1.2" data-campo="version" value="${escaparHTML(doc?.version || '')}"${published ? ' readonly' : ''} required>
      <label for="lg-title">Título</label><input id="lg-title" name="title" type="text" maxlength="120" value="${escaparHTML(doc?.title || TYPES[state.type] || '')}"${published ? ' readonly' : ''} required>
      ${upload}<label for="lg-content">Contenido</label>${toolbar}<textarea id="lg-content" name="content" rows="18" maxlength="200000"${published ? ' readonly' : ''} required${published ? '' : ' aria-describedby="lg-content-help"'}>${escaparHTML(doc?.content || '')}</textarea>
      ${published ? '' : `<p class="user-small-copy" id="lg-content-help">Puedes pegar desde Word: el formato se limpia en el servidor. El borrador se guarda solo cada 10 segundos.</p>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Guardar borrador</button>${T.button('preview-editor', 'Vista previa')}${T.button('publish-editor', 'Publicar', 'brand', doc ? '' : 'hidden')}</div>
      <p class="user-small-copy" data-legal-saved role="status"></p>`}</form>`;
    return `${back}${AppViews.heading(title)}${facts}<div class="legal-editor"><section class="bento-panel">${form}</section><section class="bento-panel"><h2>Vista previa</h2><div class="legal-preview" data-legal-preview>${doc ? doc.html : '<p>Pulsa «Vista previa» para ver el texto como lo verá el público.</p>'}</div></section></div>${T.dialog}`;
  }

  const confirmations = {
    publish:(type, version) => ({titulo:`¿Publicar la versión ${version} de ${TYPES[type]}?`,
      texto:`Todas las cuentas recibirán un aviso y deberán ${type === 'politica_cookies' ? 'volver a decidir sobre cookies' : 'aceptarla al entrar'}. Una versión publicada no se puede editar ni borrar.`, accion:'Publicar'}),
    remove:{titulo:'¿Eliminar este borrador?', texto:'No se puede deshacer.', accion:'Eliminar', peligro:true},
    replace:{titulo:'¿Reemplazar el contenido?', texto:'El texto actual del borrador se sustituirá por el del documento.', accion:'Reemplazar'}};

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

  // Pegado y documento subido: el texto es el HTML que devolvió el servidor, y entra como valor del campo, no como HTML de la página.
  function insertText(root, text, start, end) {
    const area = root.querySelector('[name=content]');
    area.setRangeText(text, start, end, 'end');
    area.focus();
  }
  function replaceContent(root, text) { root.querySelector('[name=content]').value = text; }
  function chooseFile(root) { const input = root.querySelector('[data-legal-file]'); input.value = ''; input.click(); }
  function saved(root, at) {
    const line = root.querySelector('[data-legal-saved]'), publish = root.querySelector('[data-admin-action="publish-editor"]');
    // Un borrador nuevo ya guardado se puede publicar.
    if(at && publish) publish.hidden = false;
    if(line) line.textContent = at ? `Guardado · ${at.toLocaleTimeString('es-MX', {hour:'2-digit', minute:'2-digit', timeZone:'America/Merida'})}` : 'No se pudo guardar automáticamente. Usa «Guardar borrador» para ver el motivo.';
  }

  return Object.freeze({listScreen, editorScreen, confirmations, errorText, showPreview, previewDialog, insertTag, insertText, replaceContent, chooseFile, saved});
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
      <div><label for="cs-version">Versión</label><input id="cs-version" name="version" type="text" inputmode="decimal" maxlength="11" placeholder="1.1" data-campo="version" value="${escaparHTML(values.version || '')}"></div>
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
      .map(([label, value]) => AppViews.kpi(label, value, ' class="consent-figure"')).join('');
    const body = list.items.length ? T.table('Bitácora de consentimientos', ['Fecha y hora (Mérida)', 'Cuenta', 'Qué', 'Versión', 'Decisión', 'IP', 'Navegador', ''], list.items.map(row)) : AppViews.empty('No hay registros con estos filtros', 'Cambia o limpia los filtros para ver más.');
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

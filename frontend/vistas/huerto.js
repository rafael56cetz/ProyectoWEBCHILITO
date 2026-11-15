// VISTA · Huerto: Mi huerto y sus pantallas, panel técnico y soporte, guías de cuidado y mantenimientos.
// Define: GardenViews, UserGardenViews, CareGuideViews, MaintenanceViews.

// ── Huerto ──
// Mi huerto, crear huerto, vincular equipo, ficha de planta y Mis huertos. Todo dato del servidor entra con escaparHTML.
const GardenViews = (() => {
  const STAGES = {sin_sembrar:'Sin sembrar', germinacion:'Germinación', plantula:'Plántula', crecimiento:'Crecimiento', floracion:'Floración', fructificacion:'Fructificación'};
  const ORDER_TITLES = {regar:'Riego', lampara_apagar:'Apagar la lámpara', lampara_automatico:'Restaurar la lámpara automática', autodiagnostico:'Revisión del equipo'};
  const ORDER_STATES = {pendiente:['Pendiente','ambar'], enviado:['Enviada','ambar'], confirmado:['Confirmada','verde'], fallido:['Falló','rojo'], expirado:['Sin respuesta','gris']};
  const ERRORS = {
    'huerto-limite':'Ya tienes 3 huertos. Archiva uno para crear otro.',
    'huerto-sin-equipo':'Ya tienes un huerto sin equipo. Vincúlalo antes de crear otro.',
    'huerto-con-equipo':'Desvincula el equipo antes de archivar este huerto.',
    'equipo-no-vinculado':'Este huerto no tiene un equipo vinculado.',
    'rate-limited':'Demasiados intentos. Espera un momento.'};
  const errorText = (code, fallback = 'No se pudo completar la solicitud. Inténtalo de nuevo.') => ERRORS[code] || fallback;
  const tag = (text, tone = 'gris') => `<span class="badge tone-${tone}">${escaparHTML(text)}</span>`;
  const withGarden = (path, id) => `#${path}${id ? `?h=${encodeURIComponent(id)}` : ''}`;
  const number = value => Number.isFinite(value) ? AppModel.number(value) : null;
  const reading = (value, unit) => number(value) === null ? 'Sin lectura' : `${number(value)}${unit}`;
  const button = (action, label, kind = 'light', attrs = '') => `<button type="button" class="button btn-liquid-${kind}" data-garden-action="${action}" ${attrs}>${label}</button>`;
  const line = (size = '') => `<span class="skeleton-line ${size}" aria-hidden="true"></span>`;
  const failed = `<section class="bento-panel user-empty" role="alert"><h2>No pudimos cargar tu huerto.</h2><p>Revisa tu conexión e inténtalo de nuevo.</p>${button('reload', 'Reintentar', 'brand')}</section>`;
  const loading = `<p class="sr-only" role="status">Cargando la información de tu huerto.</p><div class="garden-welcome" aria-hidden="true"><h1>${line()}</h1><p>${line('short')}</p></div><section class="user-summary-metrics" aria-hidden="true">${[1, 2, 3, 4].map(() => `<article class="bento-panel user-metric">${line('heading')}<strong>${line('value')}</strong><p>${line()}</p></article>`).join('')}</section>`;

  function welcome(name, gardenName = '') {
    const {phrase} = AppModel.gardenGreeting(name);
    const title = name ? ['Hola, ' + name, gardenName].filter(Boolean).join(' · ') : gardenName || 'Te damos la bienvenida a El Chilito';
    const lead = name && !gardenName ? '<p class="garden-welcome-lead">Te damos la bienvenida a El Chilito.</p>' : '';
    return `<div class="garden-welcome"><h1>${escaparHTML(title)}</h1>${lead}<p class="garden-welcome-phrase">${escaparHTML(phrase)}</p></div>`;
  }

  function deviceTag(device) {
    if(!device) return tag('Sin equipo');
    return {en_linea:tag('En línea', 'verde'), desconectado:tag('Desconectado', 'rojo'), nunca:tag('Esperando conexión')}[device.connection];
  }
  // Solo con 2 o más huertos. «Crear otro» se desactiva con su motivo (3.1).
  function selector(gardens, current) {
    if(gardens.length < 2) return '';
    const reason = gardens.length >= 3 ? 'Máximo 3 huertos' : gardens.some(item => !item.device) ? 'Primero vincula tu huerto sin equipo' : '';
    const items = gardens.map(item => `<li><a href="${withGarden('huerto', item.id)}"${item.id === current.id ? ' aria-current="true"' : ''}><span>${escaparHTML(item.name)}</span>${deviceTag(item.device)}</a></li>`).join('');
    const create = reason ? `<li><span class="garden-selector-off">+ Crear otro huerto · ${reason}</span></li>` : '<li><a href="#huerto/nuevo">+ Crear otro huerto</a></li>';
    return `<details class="garden-selector"><summary>${icon('leaf')}<span>${escaparHTML(current.name)}</span></summary><ul>${items}${create}</ul></details>`;
  }

  function statusLine(device) {
    const status = GardenModel.connection(device);
    return status ? `<div class="user-status-line"><p>${tag(status.text, status.tone)}</p></div>` : '';
  }

  const emptyGarden = name => `${welcome(name)}
    <section class="bento-panel garden-empty"><div class="garden-empty-art" aria-hidden="true">${[1, 2, 3].map(plantDrawing).join('')}</div>
      <h2>Aún no tienes un huerto</h2>
      <p>Crea tu huerto en la página y después conecta tu equipo El Chilito con el código que te daremos.</p>
      <a class="button btn-liquid-brand" href="#huerto/nuevo">Crear mi huerto</a>
      <a class="garden-empty-link" href="#consiguelo">¿Todavía no tienes tu equipo? Conoce El Chilito${icon('external')}</a></section>
    <section class="bento-panel user-care"><span class="icon-medallion">${icon('leaf')}</span><h3>Guías de cuidado</h3><p>Aprende cómo cuidar tus plantas de habanero antes de empezar.</p><a class="button btn-liquid-light" href="#mantenimiento/guias">Ver guías</a></section>`;

  function plantCard(plant, gardenId) {
    const dry = Number.isFinite(plant.moisture) && plant.moisture < 35;
    const sown = plant.daysSown === null ? 'Sin fecha de siembra' : `Sembrada hace ${plant.daysSown} días`;
    const moisture = Number.isFinite(plant.moisture) ? `<strong>${number(plant.moisture)}<small>%</small></strong><div class="sensor-track" aria-hidden="true"><span style="width:${plant.moisture}%"></span></div>` : '<strong class="absent">Sin lectura</strong>';
    return `<article class="plant-card"><div class="card-top">${tag(STAGES[plant.stage] || plant.stage)}${dry ? tag('Seca', 'ambar') : ''}</div>
      <div class="plant-name"><div><h3>${escaparHTML(plant.name)}</h3><p>${sown}</p></div><div class="plant-pedestal">${plantDrawing(plant.number)}</div></div>
      <div class="plant-reading"><span>${icon('drop')}Humedad del sustrato</span>${moisture}</div>
      <a class="button btn-liquid-light" href="${withGarden(`huerto/plantas/${plant.number}`, gardenId)}">Ver planta<span class="sr-only">: ${escaparHTML(plant.name)}</span></a></article>`;
  }
  const plantsSection = (detail, title) => `<section aria-labelledby="plants-title"><div class="panel-heading"><h2 id="plants-title">${title}</h2></div><div class="plant-grid">${detail.plants.map(plant => plantCard(plant, detail.garden.id)).join('')}</div></section>`;

  function connectCard(garden) {
    return `<section class="bento-panel garden-connect"><h2>Conecta tu equipo</h2>
      <ol class="garden-steps"><li><strong>1. Genera tu código</strong><span>Vence en 10 minutos y solo sirve una vez.</span></li>
      <li><strong>2. Conéctate a la red Huerto-Setup de tu equipo</strong><span>Desde tu celular o computadora.</span></li>
      <li><strong>3. Escribe tu Wi-Fi y el código</strong><span>Después verás aquí cuando tu equipo quede conectado.</span></li></ol>
      <a class="button btn-liquid-brand" href="${withGarden('huerto/vincular', garden.id)}">Vincular equipo</a></section>`;
  }

  function metrics(detail) {
    const {metrics: m, lamp, plants} = detail;
    const average = GardenModel.averageMoisture(plants);
    const tank = m?.tankHasWater === true ? 'Con agua' : m?.tankHasWater === false ? 'Nivel bajo' : 'Sin lectura';
    const lampState = {on:'Encendida', off:'Apagada'}[lamp?.state] || 'Sin lectura';
    const card = (ico, title, main, note) => `<article class="bento-panel user-metric"><span class="user-metric-icon">${icon(ico)}</span><h2>${title}</h2><strong>${main}</strong><p>${note}</p></article>`;
    return `<section class="user-summary-metrics" aria-label="Resumen del huerto">
      ${card('tank', 'Depósito de agua', tank, 'Depósito de 19 L · el flotador solo detecta nivel bajo')}
      ${card('drop', 'Humedad media del sustrato', average === null ? 'Sin lectura' : `${number(average)}<small>%</small>`, 'Promedio de las plantas con lectura')}
      ${card('temp', 'Ambiente', reading(m?.temperature, '°C'), `Humedad relativa: ${reading(m?.airHumidity, '%')}`)}
      ${card('sun', 'Lámpara', lampState, lamp?.mode === 'manual-off' ? 'Apagado manual' : 'Automático')}</section>`;
  }

  function deviceNote(device) {
    if(device.connection === 'desconectado') return '<p class="user-data-warning" role="status">Tu equipo está desconectado. Revisa su corriente y tu Wi-Fi.</p>';
    if(!device.lastReadingAt) return '<p class="user-data-warning" role="status">Esperando la primera lectura de tu equipo.</p>';
    return '';
  }

  const summaryCard = summary => `<section class="bento-panel user-diagnosis" aria-labelledby="diagnosis-title"><div class="user-diagnosis-mark">${icon('sparkle')}</div><div class="user-diagnosis-copy"><h2 id="diagnosis-title">Resumen de tu huerto</h2>
    ${summary ? `<p>${escaparHTML(summary.content)}</p><p class="user-diagnosis-meta">Generado con IA · no sustituye tu revisión · ${AppViews.date(summary.generatedAt)}</p>${button('summaries', 'Ver anteriores')}`
      : '<p>El resumen aparecerá cuando tu equipo haya enviado lecturas.</p>'}<div data-summaries></div></div></section>`;

  function summaryList(items) {
    if(!items.length) return '<p class="user-diagnosis-meta">No hay resúmenes en los últimos 30 días.</p>';
    return `<ol class="user-history-list">${items.map(item => `<li><div><p>${escaparHTML(item.content)}</p><p class="user-diagnosis-meta">${AppViews.date(item.generatedAt)}</p></div></li>`).join('')}</ol>`;
  }

  function quickActions(detail) {
    const off = detail.lamp?.mode === 'manual-off';
    return `<div class="user-section-heading"><div><h2>Acciones rápidas</h2></div></div>
      <section class="user-quick-actions" aria-label="Acciones rápidas">
        ${button('refill', 'Registrar recarga')}
        <a class="button btn-liquid-light" href="#mantenimiento">Registrar un cuidado</a>
        ${button('order', 'Revisar mi equipo', 'light', 'data-type="autodiagnostico"')}
        ${button('order-confirm', off ? 'Restaurar automático' : 'Apagar lámpara', 'light', `data-type="${off ? 'lampara_automatico' : 'lampara_apagar'}"`)}
        <a class="button btn-liquid-brand" href="#soporte">Solicitar revisión técnica</a></section>
      <div data-order-card></div>
      <p class="user-safety-copy">Ante una emergencia, utiliza el paro físico del equipo.</p>
      <p class="user-small-copy">¿Algo no responde? <a href="#soporte">Solicitar revisión técnica</a></p>`;
  }

  // Mi huerto en sus tres versiones: A sin huerto, B sin equipo, C con equipo.
  function summary({status, gardens, detail}, name) {
    if(status === 'loading') return loading;
    if(status === 'error') return failed;
    if(!gardens.length) return emptyGarden(name);
    const head = selector(gardens, detail.garden);
    if(!detail.garden.device) return `${head}${AppViews.heading(detail.garden.name)}${connectCard(detail.garden)}${plantsSection(detail, 'Tus tres plantas')}`;
    return `${head}${welcome(name, detail.garden.name)}${statusLine(detail.garden.device)}${deviceNote(detail.garden.device)}${metrics(detail)}${plantsSection(detail, 'Tus tres plantas')}${summaryCard(detail.summary)}${quickActions(detail)}`;
  }

  // Tarjeta de orden 3.3: el estado lo confirma el equipo, no esta pantalla.
  function orderCard(order) {
    const [label, tone] = ORDER_STATES[order.state] || ['Sin respuesta', 'gris'];
    const detail = order.type === 'regar' ? ` · planta ${order.plant} · ${order.duration} s` : '';
    return `<article class="bento-panel order-card${order.state === 'enviado' ? ' is-sending' : ''}" role="status"><div><h3>${ORDER_TITLES[order.type] || 'Orden'}${detail}</h3>
      ${order.state === 'fallido' && order.error ? `<p>${escaparHTML(order.error)}</p>` : ''}</div>${tag(label, tone)}</article>`;
  }

  function newGarden() {
    return `${AppViews.heading('Crea tu huerto')}<section class="bento-panel garden-form"><p>Ponle un nombre para reconocerlo. Podrás cambiarlo después.</p>
      <form data-garden-form="create" novalidate><label for="garden-name">Nombre del huerto (opcional)</label><input id="garden-name" name="name" type="text" maxlength="60" autocomplete="off" placeholder="Mi huerto">
      <p class="user-small-copy">Tu huerto tendrá 3 plantas de chile habanero. Disponible solo en Yucatán.</p>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Crear huerto</button><a class="button btn-liquid-light" href="#huerto">Cancelar</a></div></form></section>`;
  }

  const progress = step => `<ol class="link-progress" aria-label="Pasos">${['Código', 'Conecta tu equipo', 'Listo'].map((label, index) => `<li${index + 1 === step ? ' aria-current="step"' : ''}>${index + 1}. ${label}</li>`).join('')}</ol>`;
  const codeBox = (code, seconds) => `<div class="link-code-box"><p class="link-code" aria-label="Tu código de vinculación">${escaparHTML(GardenModel.groupCode(code))}</p>
    <p class="user-small-copy">Vence en <span data-countdown>${GardenModel.clock(seconds)}</span> · Solo se muestra ahora.</p>${button('copy-code', 'Copiar')}</div>`;

  // Asistente 4.3. `wizard.step`: 1 código, 2 conexión, 3 listo; `wizard.code` solo existe mientras se muestra.
  function linkWizard(wizard) {
    const {garden, step, code, seconds, expired, device} = wizard;
    const head = AppViews.heading('Vincular equipo', garden.name) + progress(step);
    if(step === 3) return `${head}<section class="bento-panel garden-form"><span class="icon-medallion">${icon('check')}</span><h2>¡Tu equipo quedó vinculado!</h2><p>Equipo: ${escaparHTML(device.identifier)}</p><a class="button btn-liquid-brand" href="${withGarden('huerto', garden.id)}">Ir a mi huerto</a></section>`;
    if(step === 1) return `${head}<section class="bento-panel garden-form"><h2>Genera tu código</h2><p>Genera el código que escribirás en tu equipo. Vence en 10 minutos y solo sirve una vez.</p>${button('generate', 'Generar código', 'brand')}<a class="button btn-liquid-light" href="${withGarden('huerto', garden.id)}">Cancelar</a></section>`;
    const waiting = expired ? '<p role="alert">El código venció. Genera otro.</p>'
      : `<p role="status" class="link-waiting">Esperando a tu equipo… (vence en <span data-countdown>${GardenModel.clock(seconds)}</span>)</p>`;
    return `${head}<section class="bento-panel garden-form">${code ? codeBox(code, seconds) : ''}
      <ol class="garden-steps"><li>Enchufa tu equipo El Chilito. Si ya lo habías configurado, mantén presionado su botón de configuración hasta que la pantalla lo indique.</li>
      <li>En tu celular o computadora, conéctate a la red Wi-Fi <strong>Huerto-Setup-XXXX</strong> con la contraseña de la etiqueta del equipo.</li>
      <li>Abre <strong>192.168.4.1</strong> en tu navegador.</li><li>Escribe el nombre y la contraseña de tu Wi-Fi y el código que ves arriba.</li><li>Vuelve aquí: veremos cuando tu equipo quede conectado.</li></ol>
      ${waiting}<div class="app-actions">${button('generate', 'Generar otro código', 'brand')}<a class="button btn-liquid-light" href="${withGarden('huerto', garden.id)}">Cancelar</a></div>
      <details class="link-help"><summary>¿Problemas para conectar?</summary><p>Tu equipo no pudo usar el código. Revisa que lo escribiste bien o genera otro. Comprueba también que la red Wi-Fi sea de 2.4 GHz y que esté cerca del equipo.</p><a href="#soporte">Pedir ayuda a soporte</a></details></section>`;
  }

  const dialog = '<dialog class="bento-panel app-dialog garden-dialog" aria-labelledby="garden-dialog-title"><div data-garden-dialog-content></div></dialog>';
  const today = () => MaintenanceDates.format(MaintenanceDates.today());

  function plantDialogs(plant, hasDevice) {
    return {
      edit: `<h2 id="garden-dialog-title">Editar planta</h2><form data-garden-form="plant" novalidate>
        <label for="plant-name">Nombre de la planta</label><input id="plant-name" name="name" type="text" maxlength="40" required value="${escaparHTML(plant.name)}">
        <label for="plant-date">Fecha de siembra</label><input id="plant-date" name="sowingDate" type="date" max="${today()}" value="${escaparHTML(plant.sowingDate || '')}">
        <label for="plant-stage">Etapa</label><select id="plant-stage" name="stage">${GardenModel.STAGES.map(stage => `<option value="${stage}"${stage === plant.stage ? ' selected' : ''}>${STAGES[stage]}</option>`).join('')}</select>
        <p class="user-small-copy">Al cambiar la etapa, guardamos la fecha de hoy en su línea de vida.</p>
        <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Guardar</button></div></form>`,
      water: `<h2 id="garden-dialog-title">Regar esta planta</h2><form data-garden-form="water" novalidate>
        <label for="water-seconds">Duración del riego</label><select id="water-seconds" name="duration">${GardenModel.WATERING_SECONDS.map(seconds => `<option value="${seconds}"${seconds === 8 ? ' selected' : ''}>${seconds} segundos</option>`).join('')}</select>
        <p class="user-small-copy">Si el depósito no tiene agua, tu equipo no regará.</p>
        <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit"${hasDevice ? '' : ' disabled'}>Regar</button></div></form>`};
  }

  function plantPage({garden, plant, stages, series, range, care, lastWatering, hasDevice}) {
    const since = plant.stageSince ? ` (desde el ${AppViews.date(plant.stageSince)})` : '';
    const sown = plant.sowingDate ? `Sembrada el ${AppViews.date(plant.sowingDate)}${plant.daysSown === null ? '' : ` (hace ${plant.daysSown} días)`}` : 'Sin fecha de siembra';
    const careLabels = {rellenar_deposito:'Recarga del depósito', sustrato:'Sustrato y perlita', germinacion:'Germinación', cosecha:'Cosecha', inspeccion:'Inspección'};
    const watering = lastWatering ? `Último riego: ${{automatico:'automático', usuario:'tuyo', soporte:'de soporte'}[lastWatering.origin] || lastWatering.origin}, ${lastWatering.duration ?? '—'} s, ${GardenModel.ago(lastWatering.at)}` : 'Sin riegos registrados';
    return `<a class="garden-back" href="${withGarden('huerto', garden.id)}">← Mi huerto</a>
      <div class="page-heading"><div><h1>Planta ${plant.number} · «${escaparHTML(plant.name)}»</h1><p>${STAGES[plant.stage] || plant.stage}${escaparHTML(since)} · ${escaparHTML(sown)}</p></div>${button('edit', 'Editar')}</div>
      <div class="user-chart-toolbar"><h2>Humedad del sustrato</h2><div class="user-range-control" role="group" aria-label="Periodo">${GardenModel.RANGES.map(value => button('range', {'1h':'1 h', '24h':'24 h', '7d':'7 días', '30d':'30 días'}[value], range === value ? 'brand' : 'light', `data-range="${value}" aria-pressed="${range === value}"`)).join('')}</div></div>
      ${UserGardenViews.chart('Humedad del sustrato', series, '%', range, 'plant')}
      <section class="bento-panel"><h2>Línea de vida</h2>${stages.length ? `<ol class="user-history-list">${stages.map(item => `<li><span>${icon('leaf')}</span><div><h3>${STAGES[item.stage] || item.stage}</h3><p>${AppViews.date(item.since)}</p></div></li>`).join('')}</ol>` : '<p>Aún no hay etapas registradas.</p>'}</section>
      <section class="bento-panel"><h2>Cuidados de esta planta</h2>${care.length ? `<ol class="user-history-list">${care.map(item => `<li><span>${icon('check')}</span><div><h3>${careLabels[item.type] || item.type}</h3><p>${AppViews.date(item.doneAt)}</p></div></li>`).join('')}</ol>` : '<p>No hay cuidados registrados para esta planta.</p>'}<a class="button btn-liquid-light" href="#mantenimiento">Registrar cuidado</a></section>
      <section class="bento-panel user-operating"><div><h2>Riego</h2><p>${escaparHTML(watering)}</p></div>${hasDevice ? button('water', 'Regar esta planta', 'brand') : '<p class="user-small-copy">Vincula tu equipo para regar desde aquí.</p>'}</section>
      <div data-order-card></div>${dialog}`;
  }

  const deviceFacts = device => device
    ? `<dl class="user-facts"><div><dt>Equipo</dt><dd>${escaparHTML(device.identifier)}</dd></div><div><dt>Estado</dt><dd>${deviceTag(device)}</dd></div><div><dt>Vinculado</dt><dd>${AppViews.date(device.linkedAt)}</dd></div></dl>`
    : '<p>Sin equipo vinculado.</p>';

  function myGardens({status, gardens}) {
    const tabs = AppViews.accountTabs('huertos');
    const head = AppViews.heading('Mis huertos') + tabs;
    if(status === 'loading') return head + AppViews.state('Cargando tus huertos', 'Consultando tu cuenta.', true);
    if(status === 'error') return head + AppViews.state('No pudimos cargar tus huertos', 'Inténtalo de nuevo.', false, true);
    const reason = gardens.length >= 3 ? 'Máximo 3 huertos' : gardens.some(item => !item.device) ? 'Primero vincula tu huerto sin equipo' : '';
    const cards = gardens.map(item => `<article class="bento-panel my-garden" data-garden-id="${escaparHTML(item.id)}"><h2>${escaparHTML(item.name)}</h2>${deviceFacts(item.device)}
      <div class="app-actions">${button('rename', 'Renombrar')}${item.device ? button('unlink', 'Desvincular equipo', 'light', 'data-danger="true"') : button('archive', 'Archivar huerto', 'light', 'data-danger="true"')}</div></article>`).join('');
    const create = reason ? `<button type="button" class="button btn-liquid-light" disabled>Crear otro huerto</button><p class="user-small-copy">${reason}</p>` : '<a class="button btn-liquid-brand" href="#huerto/nuevo">Crear otro huerto</a>';
    return head + (cards || '<section class="bento-panel user-empty"><h2>Aún no tienes huertos</h2><p>Crea tu primer huerto para empezar.</p></section>') + `<div class="app-actions">${gardens.length ? create : '<a class="button btn-liquid-brand" href="#huerto/nuevo">Crear mi huerto</a>'}</div>${dialog}`;
  }

  const renameDialog = garden => `<h2 id="garden-dialog-title">Renombrar huerto</h2><form data-garden-form="rename" data-garden-id="${escaparHTML(garden.id)}" novalidate><label for="rename-name">Nombre del huerto</label><input id="rename-name" name="name" type="text" maxlength="60" required value="${escaparHTML(garden.name)}">
    <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Guardar</button></div></form>`;

  const confirmations = {
    lampara_apagar:{titulo:'¿Apagar la lámpara?', texto:'Se enviará la orden a tu equipo. Volverá a encenderse según su horario cuando restaures el modo automático.', accion:'Apagar lámpara'},
    lampara_automatico:{titulo:'¿Restaurar el modo automático?', texto:'Se enviará la orden a tu equipo. La lámpara volverá a seguir su horario.', accion:'Restaurar automático'},
    desvincular: identifier => ({titulo:`¿Desvincular el equipo ${identifier}?`, texto:'Dejará de enviar lecturas a este huerto. Para volver a usarlo tendrás que vincularlo de nuevo.', accion:'Desvincular equipo', peligro:true}),
    archivar: name => ({titulo:`¿Archivar ${name}?`, texto:'Dejarás de verlo. Su historial se conserva.', accion:'Archivar huerto', peligro:true})};

  return Object.freeze({
    errorText, summary, summaryList, orderCard, newGarden, linkWizard, plantPage, plantDialogs, myGardens, renameDialog, confirmations, failed,
    paint(root, html) { root.innerHTML = html; },
    fillSlot(root, selector, html) { const slot = root.querySelector(selector); if(slot) slot.innerHTML = html; },
    countdown(root, seconds) { root.querySelectorAll('[data-countdown]').forEach(node => { node.textContent = GardenModel.clock(seconds); }); },
    dialog: root => root.querySelector('.garden-dialog'),
    openDialog(root, html) {
      const box = root.querySelector('.garden-dialog');
      box.querySelector('[data-garden-dialog-content]').innerHTML = html;
      box.showModal();
      box.querySelector('input,select,button')?.focus();
    },
    closeDialog(root) { const box = root.querySelector('.garden-dialog'); if(box?.open) box.close(); }
  });
})();

// ── Huerto usuario ──
const UserGardenViews = (() => {
  const num = value => Number.isFinite(value) ? AppModel.number(value) : '—';
  const date = value => AppViews.date(value);
  const value = (reading,unit='') => reading?.value==null ? '—' : `${escaparHTML(num(reading.value))}${unit?`<small>${unit}</small>`:''}`;
  const button=(action,label,primary=false,attrs='')=>`<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-user-action="${action}" ${attrs}>${label}</button>`;
  const intro=(title,text)=>AppViews.heading(title,text);
  const section=(title,copy='')=>`<div class="user-section-heading"><div><h2>${title}</h2>${copy?`<p>${copy}</p>`:''}</div></div>`;
  const actions='<div id="user-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>';
  const dialog='<dialog class="bento-panel app-dialog user-dialog" aria-labelledby="user-dialog-title" aria-describedby="user-dialog-copy"><div data-user-dialog-content></div></dialog>';
  const line=(size='')=>`<span class="skeleton-line ${size}" aria-hidden="true"></span>`;
  const loadingNote='<p class="sr-only" role="status">Cargando la información de tu huerto.</p>';
  const failed=`<section class="bento-panel user-empty" role="alert"><h2>Esta sección se está actualizando.</h2><p>Vuelve a intentarlo más tarde.</p>${button('refresh','Reintentar',true)}</section>`;
  // Esqueleto de una pantalla con tarjetas: solo existe mientras hay una consulta en curso.
  const loadingCards=(count,gridClass)=>`${loadingNote}<section class="${gridClass}" aria-hidden="true">${Array.from({length:count},()=>`<article class="bento-panel user-metric">${line('heading')}<strong>${line('value')}</strong><p>${line()}</p></article>`).join('')}</section>`;
  // La carga y el error sustituyen a la pantalla.
  function emptyState(data,gridClass) {
    if(data.garden.status==='loading')return loadingCards(3,gridClass);
    if(data.garden.status==='error')return failed;
    return '';
  }
  function statusLine(data) {
    const g=data.garden;
    return `<div class="user-status-line"><p>${escaparHTML(AppModel.states[g.status]?.[0]||'Sin información')}</p><p>Última lectura: ${g.updatedAt?date(g.updatedAt):'Sin registros'}</p></div>${['offline','stale','invalid'].includes(g.status)?`<p class="user-data-warning" role="status">${escaparHTML(AppModel.states[g.status][1])}</p>`:''}`;
  }
  const tankText=data=>data.garden.tank.state==='low'?'Nivel bajo':data.garden.tank.state==='not-low'?'Nivel adecuado':'Sin lectura';
  function care(ico,title,copy,action) {return `<article class="bento-panel user-care"><span class="icon-medallion">${icon(ico)}</span><h3>${title}</h3><p>${copy}</p>${action}</article>`;}
  function chart(title,readings,unit,range,id) {
    const points=Array.isArray(readings)?readings.filter(r=>Number.isFinite(r.value)&&Number.isFinite(Date.parse(r.at))).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)):[];
    const labels={'1h':['Hace 1 h','Hace 30 min','Ahora'],'24h':['Hace 24 h','Hace 12 h','Ahora'],'7d':['Hace 7 días','Hace 3 días','Ahora'],'30d':['Hace 30 días','Hace 15 días','Ahora']}[range]||['Hace 7 días','Hace 3 días','Ahora'];
    // Sin datos se dibuja el marco de la gráfica (ejes y cuadrícula) sin ninguna serie: nunca valores inventados.
    if(points.length<2)return `<article class="bento-panel user-chart is-empty"><div class="user-chart-heading"><h2>${title}</h2><p>—<span> ${unit}</span></p></div><div class="user-chart-frame"><svg class="user-history-chart" viewBox="0 0 620 228" aria-hidden="true">${[0,.5,1].map(t=>{const yy=36+144*t;return `<line x1="56" y1="${yy}" x2="586" y2="${yy}"/><text x="44" y="${yy+4}" text-anchor="end">—</text>`;}).join('')}<g class="user-chart-labels">${labels.map((l,i)=>`<text x="${56+i*265}" y="214" text-anchor="${['start','middle','end'][i]}">${l}</text>`).join('')}</g></svg><p class="user-chart-empty-note">Aún no hay registros para este periodo.</p></div></article>`;
    const vals=points.map(x=>x.value);const min=Math.min(...vals),max=Math.max(...vals),spread=max-min||1,lo=min-spread*.18,hi=max+spread*.18;
    const x=i=>56+i/(points.length-1)*530,y=v=>180-(v-lo)/(hi-lo)*144;
    const grid=[0,.5,1].map(t=>{const yy=36+144*t;return `<line x1="56" y1="${yy}" x2="586" y2="${yy}"/><text x="44" y="${yy+4}" text-anchor="end">${escaparHTML(num(hi-(hi-lo)*t))}</text>`;}).join('');
    return `<article class="bento-panel user-chart"><div class="user-chart-heading"><h2>${title}</h2><p>${escaparHTML(num(vals[vals.length-1]))}<span> ${unit}</span></p></div><svg class="user-history-chart" viewBox="0 0 620 228" role="img" aria-labelledby="chart-${id}-title chart-${id}-desc"><title id="chart-${id}-title">${title}</title><desc id="chart-${id}-desc">${points.length} registros en ${{'7d':'los últimos 7 días','30d':'los últimos 30 días','24h':'las últimas 24 horas'}[range]||'la última hora'}. Último valor: ${escaparHTML(num(vals[vals.length-1]))} ${unit}.</desc><g class="user-chart-grid">${grid}</g><polyline class="user-chart-line" points="${points.map((p,i)=>`${x(i)},${y(p.value)}`).join(' ')}"/><circle class="user-chart-dot" cx="${x(points.length-1)}" cy="${y(vals[vals.length-1])}" r="4"/><g class="user-chart-labels">${labels.map((l,i)=>`<text x="${[56,321,586][i]}" y="216" text-anchor="${['start','middle','end'][i]}">${l}</text>`).join('')}</g></svg></article>`;
  }
  function technical(data,name) {
    const head=intro('Panel técnico',AppModel.addressed(name,'Lecturas, conectividad e historial de tu huerto.'));
    const problem=emptyState(data,'user-technical-metrics');if(problem)return head+problem;
    const g=data.garden,h=data.history||{};
    return `${head}${statusLine(data)}
    <section class="user-technical-metrics" aria-label="Lecturas técnicas">
      <article class="bento-panel user-metric"><h2>Sensor capacitivo v1.2</h2><strong>${num(data.soil?.adc)}<small> ADC</small></strong><p>Lectura analógica bruta · escala 0–4095</p></article>
      <article class="bento-panel user-metric"><h2>Humedad calibrada</h2><strong>${value(data.soil?.moisture,'%')}</strong><p>Humedad del sustrato</p></article>
      <article class="bento-panel user-metric"><h2>Ambiente · SHT31</h2><strong>${value(g.temperature,'°C')}</strong><p>Humedad relativa: ${value(g.humidity,'%')}</p></article>
    </section>
    <div class="user-chart-toolbar"><h2>Histórico de lecturas</h2><div class="user-range-control" role="group" aria-label="Periodo del histórico">${[['1h','1 h'],['24h','24 h'],['7d','7 días']].map(([r,l])=>button('range',l,data.range===r,`data-range="${r}" aria-pressed="${data.range===r}"`)).join('')}</div></div>
    <section class="user-chart-grid-layout" aria-label="Gráficas de sensores">${chart('Humedad del sustrato · ADC',h.soil,'ADC',data.range,'soil')}${chart('Temperatura ambiental',h.temperature,'°C',data.range,'temperature')}${chart('Humedad relativa',h.humidity,'%',data.range,'humidity')}
    <article class="bento-panel user-connectivity"><h2>Depósito y conectividad</h2><dl class="user-facts"><div><dt>Flotador</dt><dd>${tankText(data)}</dd></div><div><dt>Capacidad del depósito</dt><dd>19 L</dd></div><div><dt>Wi-Fi</dt><dd>${data.connection?.wifi==null?'Sin información':data.connection.wifi?'Conectado':'Sin conexión'}</dd></div><div><dt>Mosquitto / MQTT</dt><dd>${data.connection?.mqtt==null?'Sin información':data.connection.mqtt?'Disponible':'No disponible'}</dd></div></dl><p>El flotador detecta nivel bajo; no mide el volumen de agua.</p></article></section>
    ${section('Lecturas por planta','Humedad del sustrato en cada uno de los tres compartimentos.')}
    <section class="bento-panel user-plant-readings" aria-label="Humedad por planta">${g.plants.map(p=>`<div><h3>${escaparHTML(p.name)}</h3><strong>${value(p.reading,'%')}</strong><p>${p.reading.at?date(p.reading.at):'Sin lecturas'}</p></div>`).join('')}</section>
    <div class="user-section-heading"><div><h2>Bitácora de actuadores</h2><p>Órdenes, resultados y origen de cada acción.</p></div>${button('refresh','Actualizar bitácora')}</div>
    <section class="bento-panel user-log-panel">${commandLog(data)}</section>
    <section class="bento-panel user-operating"><div><h2>Solicitar riego puntual</h2><p>Registra la solicitud y consulta su estado en la bitácora. El equipo debe confirmar la operación antes de considerarla realizada.</p></div>${button('water','Solicitar riego',true,!['error','unassigned','loading'].includes(g.status)?'':'disabled')}</section><p class="user-safety-copy">Una solicitud no confirma que la bomba se haya activado. Ante una emergencia, utiliza el paro físico del equipo.</p>`;
  }
  function commandLog(data) {
    if(!data.commands?.length)return '<div class="user-empty-inline"><p>No hay órdenes registradas.</p><p>Las solicitudes y la respuesta del equipo aparecerán aquí.</p></div>';
    return `<div class="user-table-scroll" tabindex="0" role="region" aria-label="Historial de órdenes"><table class="user-table"><thead><tr><th scope="col">Fecha y hora</th><th scope="col">Actuador</th><th scope="col">Orden / resultado</th><th scope="col">Origen</th><th scope="col">Estado</th></tr></thead><tbody>${data.commands.map(e=>`<tr><td>${date(e.at)}</td><td>${escaparHTML(e.actuator)}</td><td>${escaparHTML(e.action)}</td><td>${escaparHTML(e.origin)}</td><td>${escaparHTML(e.status)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function maintenance(data,name) {
    const head=intro('Mantenimiento del huerto',AppModel.addressed(name,'Registra los cuidados que realizas y consulta tu historial.'));
    const problem=emptyState(data,'user-maintenance-grid');if(problem)return head+problem+careGuides();
    return `${head}
    <section class="user-maintenance-grid" aria-label="Tareas de mantenimiento"><h2 class="sr-only">Tareas de mantenimiento</h2>
      ${care('tank','Nivel de agua',`Estado del depósito: ${tankText(data).toLowerCase()}. Rellena con agua limpia y registra la recarga al terminar.`,button('record-refill','Ya rellené el depósito',true))}
      ${care('leaf','Sustrato y perlita','Comprueba el drenaje y evita que la mezcla quede compactada.',`<a class="button btn-liquid-light user-care-guide-link" href="#mantenimiento/sustrato" data-care-guide-link="${CareGuideService.SUBSTRATE_KEY}">Ver guía de cuidado</a>${button('record-substrate','Marcar revisión hecha')}`)}
      ${care('leaf','Germinación externa','Germina las semillas fuera del sistema. Trasplanta cuando las plántulas sean resistentes.',`<a class="button btn-liquid-light user-care-guide-link" href="#mantenimiento/germinacion" data-care-guide-link="${CareGuideService.GERMINATION_KEY}">Ver guía de germinación</a>${button('record-germination','Registrar germinación')}`)}
      ${care('leaf','Cosecha','Usa guantes, revisa el grado de madurez y evita tocar ojos o piel sensible después de manipular los frutos.',button('record-harvest','Registrar cosecha'))}
      ${care('shield','Inspección visual','Verifica que cables y conexiones estén secos, que el depósito no tenga fugas y que la lámpara esté estable.',button('record-inspection','Registrar inspección'))}
      <article class="bento-panel user-care"><span class="icon-medallion">${icon('clock')}</span><h3>Registro reciente</h3><p>${data.maintenance?.length?`${escaparHTML(data.maintenance[0].label)} · ${date(data.maintenance[0].at)}`:'Aún no has registrado tareas de mantenimiento.'}</p><a class="button btn-liquid-light" href="#mantenimiento/historial">Ver historial</a></article>
    </section>${section('Historial de mantenimiento')}
    <section class="bento-panel user-maintenance-history" id="user-maintenance-history" tabindex="-1">${data.maintenance?.length?`<ol class="user-history-list">${data.maintenance.map(e=>`<li><span>${icon('check')}</span><div><h3>${escaparHTML(e.label)}</h3><p>${date(e.at)}</p></div></li>`).join('')}</ol>`:'<p>No hay tareas registradas. Al completar un cuidado, regístralo para conservar su fecha.</p>'}</section>${careGuides()}`;
  }
  function support(data,name) {
    const head=intro('Soporte técnico',AppModel.addressed(name,'Reporta un problema y controla el acceso técnico a tu huerto.'));
    const problem=emptyState(data,'user-support-layout');if(problem)return head+problem;
    const p=data.permission;
    const mail=p?UserGardenService.supportMail(p.folio):null;
    const permissionTitle=p?'Autorización activa':data.permissionState==='revoked'?'Autorización revocada':data.permissionState==='expired'?'Autorización vencida':'Sin autorización activa';
    return `${head}
    <div class="user-support-layout"><section class="bento-panel user-support-form"><h2>Reportar un incidente</h2><p>Selecciona el problema que presenta tu huerto.</p><form data-user-support-form><label for="user-incident">Tipo de problema</label><select id="user-incident" name="incident" required>${Object.entries(UserGardenService.incidents).map(([k,v])=>`<option value="${k}">${escaparHTML(v)}</option>`).join('')}</select><p>La autorización permite al equipo de soporte abrir una sesión de diagnóstico de este caso durante un máximo de 24 horas, sin renovarse al usarla. El diagnóstico remoto del equipo todavía no está conectado: hoy sirve para revisar tu caso con tu permiso.</p><button type="submit" class="button btn-liquid-brand" ${data.supportAvailable?'':'disabled aria-describedby="support-service-status"'}>Reportar y generar token temporal</button>${data.supportAvailable?'':'<p class="user-small-copy" id="support-service-status">Emisión de tokens no disponible.</p>'}</form>
    ${p?`<section class="user-token" aria-labelledby="support-token-title"><h3 id="support-token-title">Tu token de soporte</h3>${p.token?`<p class="user-token-code">${escaparHTML(p.token)}</p>`:'<p>El token solo se mostró al emitir esta autorización. No se recupera desde el historial. Si no lo conservas, revoca y genera una autorización nueva.</p>'}<dl class="user-facts"><div><dt>Folio</dt><dd>${escaparHTML(p.folio||'Sin folio')}</dd></div><div><dt>Incidente</dt><dd>${escaparHTML(p.incident)}</dd></div><div><dt>Vence</dt><dd>${date(new Date(p.expiresAt).toISOString())}</dd></div></dl>
      <div class="app-actions">${p.token?button('copy-token','Copiar token',true):''}${mail?`<a class="button btn-liquid-light" href="${escaparHTML(mail.href)}">${icon('mail')}<span>Escribir a soporte</span></a>`:''}</div>
      <ol class="user-token-steps"><li>Copia el token.</li><li>Escribe a ${mail?`<strong>${escaparHTML(mail.address)}</strong>`:'soporte'} con el folio en el asunto.</li><li>Pega el token en el mensaje. Nunca envíes tu contraseña ni tus códigos.</li></ol>
      <p class="user-small-copy">El token solo se muestra al emitirlo y no se puede recuperar. Si lo pierdes, revoca esta autorización y genera una nueva.</p></section>`:''}</section>
    <section class="bento-panel user-permission"><span class="icon-medallion">${icon('shield')}</span><h2>Estado de la autorización</h2><h3>${permissionTitle}</h3><p>${p?'La autorización está vigente para este reporte. Puedes revocarlo cuando quieras.':'El acceso técnico permanece cerrado hasta que lo autorices expresamente.'}</p><dl class="user-facts"><div><dt>Duración del permiso</dt><dd>24 horas</dd></div><div><dt>Alcance</dt><dd>Diagnóstico del incidente</dd></div><div><dt>Datos personales y ubicación</dt><dd>Fuera del alcance</dd></div></dl>${button('revoke','Revocar autorización',false,`data-danger="true" ${!p||!data.supportAvailable?'disabled':''}`)}</section></div>${section('Historial de reportes')}<section class="bento-panel user-maintenance-history">${data.reports?.length?`<ol class="user-history-list">${data.reports.map(r=>`<li><span>${icon('support')}</span><div><h3>${escaparHTML(UserGardenService.incidents[r.incident]||r.incident)}</h3><p>Folio ${escaparHTML(r.folio||r.id)} · ${r.caseState==='resolved'?'Caso resuelto':'Caso abierto'}</p><p>${date(r.createdAt)} · ${escaparHTML({active:'Autorización activa',revoked:'Autorización revocada',expired:'Autorización vencida',closed:'Sin autorización'}[r.permissionState]||'Sin autorización')}</p>${r.tokenRequestedAt&&r.caseState!=='resolved'?`<p>Soporte pidió tu token el ${date(r.tokenRequestedAt)}.</p>`:''}</div></li>`).join('')}</ol>`:'<p>No hay reportes registrados.</p>'}</section>`;
  }
  function confirmation(action) {
    if(action==='support')return `<h2 id="user-dialog-title">Autorizar soporte técnico</h2><p id="user-dialog-copy">La autorización permite al equipo de soporte abrir una sesión de diagnóstico de este caso durante un máximo de 24 horas, sin renovarse al usarla. El diagnóstico remoto del equipo todavía no está conectado: hoy sirve para revisar tu caso con tu permiso. Puedes revocarla antes de su vencimiento.</p><label class="user-consent"><input type="checkbox" id="user-support-consent"><span>Autorizo expresamente el diagnóstico remoto de este incidente con el alcance indicado.</span></label><div class="app-dialog-actions">${button('cancel-dialog','Cancelar')}${button('confirm-dialog','Confirmar y generar token',true,'disabled')}</div>`;
    const titles={water:'¿Solicitar riego puntual?','lamp-off':'¿Solicitar el apagado de la lámpara?','lamp-auto':'¿Restaurar el control habitual de la lámpara?'};
    return `<h2 id="user-dialog-title">${titles[action]}</h2><p id="user-dialog-copy">Se registrará una solicitud para tu huerto. La ejecución depende del servicio del equipo. El estado permanecerá sin confirmar hasta recibir la respuesta del equipo.</p><div class="app-dialog-actions">${button('cancel-dialog','Cancelar')}${button('confirm-dialog',action==='water'?'Solicitar riego':action==='lamp-off'?'Solicitar apagado':'Restaurar control',true)}</div>`;
  }
  const careGuides=()=>CareGuideViews.slot();
  return { chart,render(screen,data,name='') {
    const html=({telemetria:technical,mantenimiento:maintenance,soporte:support}[screen]||technical)(data,name);
    return actions+html+dialog;
  },confirmation,
  // Operaciones de presentación que coordina UserGardenController.
  paint(root,screen,data,name='') { root.innerHTML=this.render(screen,data,name); },
  dialog:root=>root.querySelector('.user-dialog'),
  feedback(root,text,error=false) {
    const node=root.querySelector('#user-feedback');if(!node)return;
    node.hidden=false;node.textContent=text;node.setAttribute('role',error?'alert':'status');node.focus();
  },
  openDialog(dialog,action) {
    dialog.querySelector('[data-user-dialog-content]').innerHTML=confirmation(action);
    dialog.showModal();dialog.querySelector('[data-user-action="cancel-dialog"]').focus();
  },
  closeDialog(dialog,origin) {
    if(dialog?.open)dialog.close();
    if(origin?.isConnected)origin.focus();
  },
  lockDialog(dialog) { dialog.querySelectorAll('button').forEach(b=>b.disabled=true); },
  consentChanged(dialog,checked) { dialog.querySelector('[data-user-action="confirm-dialog"]').disabled=!checked; },
  focusRange(root,range) { root.querySelector(`[data-range="${range}"]`)?.focus(); },
  focusHistory(root) { const list=root.querySelector('#user-maintenance-history');list?.scrollIntoView({block:'start'});list?.focus(); } };
})();

// ── Guias ──
// Guías de cuidado: plantillas fijas. Todo el contenido del servidor se inserta como texto, nunca como HTML.
const CareGuideViews = (() => {
  const el = (tag, className, text) => Object.assign(document.createElement(tag), className ? {className} : {}, text !== undefined ? {textContent:text} : {});

  // Persona usuaria ------------------------------------------------------------------------------
  function slot() {
    return `<section class="care-guides" data-care-guides aria-labelledby="care-guides-title">
      <div class="user-section-heading"><div><h2 id="care-guides-title" tabindex="-1">Guía de cuidado y preguntas frecuentes</h2><p>Consulta cada etapa: germinación, trasplante, crecimiento y cosecha.</p></div></div>
      <p class="care-guides-notice" data-care-guides-notice role="status" hidden></p>
      <div data-care-guides-body></div>
    </section>`;
  }
  function item(guide, isOpen) {
    const details = el('details', 'bento-panel care-guide');
    details.dataset.guideKey = guide.key; details.open = isOpen;
    const answer = el('div', 'care-guide-answer');
    answer.append(...guide.paragraphs.map(text => el('p', '', text)));
    if(guide.source) answer.append(source(guide.source));
    details.append(el('summary', '', guide.question), answer);
    return details;
  }
  function source({name, url}) {
    const line = el('p', 'care-guide-source', 'Fuente: ');
    if(!url) { line.append(name); return line; }
    const link = el('a', '', name);
    link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    line.append(link, el('span', 'sr-only', ' (se abre en otra pestaña)'));
    return line;
  }
  function problem() {
    const box = el('div', 'bento-panel care-guides-problem');
    box.setAttribute('role', 'alert');
    const retry = el('button', 'button btn-liquid-light', 'Reintentar');
    retry.type = 'button'; retry.dataset.careGuideRetry = '';
    box.append(el('p', '', 'No se pudieron consultar las guías. El resto de la página sigue disponible.'), retry);
    return box;
  }
  function paint(section, state, opened) {
    const body = section.querySelector('[data-care-guides-body]');
    section.setAttribute('aria-busy', String(state.status === 'loading'));
    if(state.status === 'loading') { const note = el('p', 'care-guides-state', 'Consultando las guías…'); note.setAttribute('role', 'status'); body.replaceChildren(note); return; }
    if(state.status === 'error') { body.replaceChildren(problem()); return; }
    if(!state.items.length) { body.replaceChildren(el('p', 'bento-panel care-guides-state', 'Todavía no hay guías publicadas.')); return; }
    const list = el('div', 'care-guide-list');
    list.append(...state.items.map(guide => item(guide, opened.has(guide.key))));
    body.replaceChildren(list);
  }
  function openItem(section, key) {
    const details = [...section.querySelectorAll('[data-guide-key]')].find(node => node.dataset.guideKey === key);
    if(!details) return false;
    setNotice(section, '');
    details.open = true;
    details.scrollIntoView({block:'center'});
    details.querySelector('summary').focus();
    return true;
  }
  function setNotice(section, text) {
    const notice = section.querySelector('[data-care-guides-notice]');
    notice.hidden = !text; notice.textContent = text;
  }
  function focusSection(section, text) {
    setNotice(section, text);
    const title = section.querySelector('#care-guides-title');
    title.scrollIntoView({block:'start'});
    title.focus();
  }

  // Administración -------------------------------------------------------------------------------
  function field(id, name, label, control, help = '') {
    return `<div class="care-admin-field"><label for="${id}">${label}</label>${control}${help ? `<p class="binding-help" id="${id}-help">${help}</p>` : ''}</div>`;
  }
  function adminShell(limits) {
    const filter = (value, label, active = false) => `<button type="button" class="button compact btn-liquid-light${active ? ' active' : ''}" data-guide-filter="${value}" aria-pressed="${active}">${label}</button>`;
    return `${AppViews.heading('Guías de cuidado','Crea, edita y publica las preguntas que ven las personas en Mantenimiento. Las fichas son compartidas: no dependen de quién las creó.')}
      <div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>
      <div class="care-admin-toolbar">
        <div class="care-admin-filters" role="group" aria-label="Filtrar por estado">${filter('','Todas',true)}${filter('publicada','Publicadas')}${filter('borrador','Borradores')}${filter('retirada','Retiradas')}</div>
        <button type="button" class="button btn-liquid-brand" data-guide-new>Nueva ficha</button>
      </div>
      <section class="bento-panel care-admin-editor" data-guide-editor aria-labelledby="care-admin-editor-title" hidden>
        <h2 id="care-admin-editor-title" tabindex="-1" data-guide-editor-title></h2>
        <p class="care-admin-hint" data-guide-editor-hint></p>
        <form class="care-admin-form" data-guide-form novalidate>
          ${field('care-question','question','Pregunta',`<input id="care-question" name="question" maxlength="${limits.question}" required autocomplete="off">`)}
          ${field('care-answer','answer','Respuesta',`<textarea id="care-answer" name="answer" rows="9" maxlength="${limits.answer}" required aria-describedby="care-answer-help"></textarea>`,'Solo texto. Deja una línea en blanco para separar párrafos.')}
          ${field('care-order','order','Orden',`<input id="care-order" name="order" inputmode="numeric" maxlength="4" required autocomplete="off" aria-describedby="care-order-help">`,'Número de 1 a 9999. Se muestra de menor a mayor.')}
          ${field('care-source-name','sourceName','Nombre de la fuente (opcional)',`<input id="care-source-name" name="sourceName" maxlength="${limits.sourceName}" autocomplete="off">`)}
          ${field('care-source-url','sourceUrl','Enlace de la fuente (opcional)',`<input id="care-source-url" name="sourceUrl" type="url" inputmode="url" maxlength="${limits.sourceUrl}" autocomplete="off" spellcheck="false" aria-describedby="care-source-url-help">`,'Solo http:// o https://.')}
          <p class="binding-status" data-guide-form-status role="status" tabindex="-1" hidden></p>
          <div class="care-admin-actions">
            <button type="submit" class="button btn-liquid-brand" data-guide-save></button>
            <button type="button" class="button btn-liquid-light" data-guide-cancel>Cancelar</button>
            <button type="button" class="button btn-liquid-light" data-guide-reload hidden>Cargar la versión actual (descarta lo escrito)</button>
          </div>
        </form>
      </section>
      <p class="care-guides-state" data-guide-summary role="status"></p>
      <div class="care-admin-list" data-guide-list></div>`;
  }
  function actionButton(label, data, value, question, primary = false) {
    const button = el('button', `button compact ${primary ? 'btn-liquid-brand' : 'btn-liquid-light'}`, label);
    button.type = 'button'; button.dataset[data] = value;
    button.setAttribute('aria-label', `${label}: ${question}`);
    return button;
  }
  function adminRow(guide, service) {
    const row = el('article', 'bento-panel care-admin-row');
    const main = el('div', 'care-admin-row-main');
    const state = el('span', `care-admin-state is-${guide.state}`, service.stateLabels[guide.state] || guide.state);
    const author = guide.updatedBy || 'Carga inicial';
    main.append(state, el('h3', '', guide.question), el('p', 'care-admin-meta', `Orden ${guide.order} · Última edición: ${author}, ${service.dateText(guide.updatedAt)}`));
    const actions = el('div', 'care-admin-row-actions');
    actions.append(actionButton('Editar', 'guideEdit', guide.id, guide.question));
    if(guide.state === 'borrador') actions.append(actionButton('Publicar', 'guidePublish', guide.id, guide.question, true));
    if(guide.state === 'retirada') actions.append(actionButton('Volver a publicar', 'guidePublish', guide.id, guide.question, true));
    if(guide.state === 'publicada') actions.append(actionButton('Retirar', 'guideWithdraw', guide.id, guide.question));
    row.append(main, actions);
    return row;
  }
  function adminList(host, summary, guides, service, filterName) {
    summary.textContent = guides.length ? `${guides.length} ficha${guides.length === 1 ? '' : 's'}` : (filterName ? 'No hay fichas en este filtro.' : 'Todavía no hay fichas.');
    host.replaceChildren(...guides.map(guide => adminRow(guide, service)));
  }
  function adminError(host, summary, text) {
    summary.textContent = '';
    const box = el('div', 'bento-panel care-guides-problem');
    box.setAttribute('role', 'alert');
    const retry = el('button', 'button btn-liquid-light', 'Reintentar');
    retry.type = 'button'; retry.dataset.guideRetry = '';
    box.append(el('p', '', text), retry);
    host.replaceChildren(box);
  }
  function setFilter(root, value) {
    root.querySelectorAll('[data-guide-filter]').forEach(button => {
      const active = button.dataset.guideFilter === value;
      button.setAttribute('aria-pressed', String(active)); button.classList.toggle('active', active);
    });
  }
  function fillEditor(editor, guide, texts) {
    const form = editor.querySelector('[data-guide-form]');
    form.reset();
    const v = guide || {};
    Object.assign(form.elements.question, {value:v.question || ''});
    Object.assign(form.elements.answer, {value:v.answer || ''});
    Object.assign(form.elements.order, {value:v.order ? String(v.order) : ''});
    Object.assign(form.elements.sourceName, {value:v.sourceName || ''});
    Object.assign(form.elements.sourceUrl, {value:v.sourceUrl || ''});
    editorLabels(editor, texts);
    markInvalid(form, null);
    formStatus(editor, '');
    staleOption(editor, false);
    editor.hidden = false;
  }
  function editorLabels(editor, texts) {
    editor.querySelector('[data-guide-editor-title]').textContent = texts.title;
    editor.querySelector('[data-guide-editor-hint]').textContent = texts.hint;
    editor.querySelector('[data-guide-save]').textContent = texts.save;
  }
  function readEditor(editor) {
    const f = editor.querySelector('[data-guide-form]').elements;
    return {question:f.question.value, answer:f.answer.value, order:f.order.value.trim(), sourceName:f.sourceName.value, sourceUrl:f.sourceUrl.value.trim()};
  }
  function markInvalid(form, name) {
    for(const control of form.querySelectorAll('input,textarea')) control.setAttribute('aria-invalid', String(control.name === name));
    if(name) form.elements[name].focus();
  }
  function formStatus(editor, text, {error = false, focus = error} = {}) {
    const node = editor.querySelector('[data-guide-form-status]');
    node.setAttribute('role', error ? 'alert' : 'status');
    node.hidden = !text; node.textContent = text;
    if(text && focus) node.focus();
  }
  function saving(editor, busy) {
    const form = editor.querySelector('[data-guide-form]');
    form.setAttribute('aria-busy', String(busy));
    form.querySelectorAll('button').forEach(button => { button.disabled = busy; });
  }
  function staleOption(editor, visible) { editor.querySelector('[data-guide-reload]').hidden = !visible; }
  function closeEditor(editor) { editor.hidden = true; }
  function focusEditor(editor) { const title = editor.querySelector('[data-guide-editor-title]'); title.scrollIntoView({block:'start'}); editor.querySelector('[name=question]').focus(); }
  // Recibe el panel ya insertado: esta vista no interpreta HTML (frontend/pruebas/pruebas.cjs, suite de guías).
  function mountAdmin(root) {
    const editor = root.querySelector('[data-guide-editor]');
    return {editor, form: editor.querySelector('[data-guide-form]'), list: root.querySelector('[data-guide-list]'),
      summary: root.querySelector('[data-guide-summary]'), feedback: root.querySelector('#admin-feedback')};
  }
  function adminFeedback(feedback, text, error = false) {
    feedback.setAttribute('role', error ? 'alert' : 'status');
    feedback.hidden = !text; feedback.textContent = text;
    if(text) feedback.focus();
  }
  function adminLoading(summary) { summary.textContent = 'Consultando las fichas…'; }
  function adminApplying(list, summary) {
    list.querySelectorAll('button').forEach(button => { button.disabled = true; });
    summary.textContent = 'Aplicando el cambio…';
  }
  function focusNew(root) { root.querySelector('[data-guide-new]').focus(); }
  return Object.freeze({slot, paint, openItem, focusSection, adminShell, mountAdmin, adminFeedback, adminLoading, adminApplying, focusNew, adminList, adminError, setFilter, fillEditor, readEditor, markInvalid, formStatus, saving, staleOption, closeEditor, focusEditor});
})();

// ── Mantenimientos ──
// Pantalla de mantenimientos. Datos del servidor solo por textContent y value.
const MaintenanceViews = (() => {
  const el = (tag, props = {}, ...children) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  };
  const options = (select, entries, blank) => {
    select.replaceChildren(...(blank ? [el('option',{value:'',textContent:blank})] : []),
      ...entries.map(([value,label]) => el('option',{value:String(value),textContent:label})));
  };
  const taskEntries = () => Object.entries(MaintenanceService.tasks);
  const months = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  const weekdays = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo'];
  function dateField(name, label) {
    return `<div class="maint-date-control"><label for="maint-${name}">${label}</label>
      <div class="maint-date-field"><input type="text" name="${name}" id="maint-${name}" placeholder="aaaa-mm-dd" maxlength="10" autocomplete="off" spellcheck="false" aria-describedby="maint-date-format">
      <button type="button" data-date-open="${name}" aria-label="Abrir calendario: ${label}" aria-controls="maint-calendar" aria-expanded="false" aria-haspopup="dialog">${icon('calendar')}</button></div></div>`;
  }
  function shell() {
    return `${AppViews.heading('Mantenimientos','Registra, corrige y anula intervenciones de los huertos asignados.')}
      <div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>
      <section class="bento-panel" aria-labelledby="mant-alta"><h2 id="mant-alta">Registrar intervención</h2>
        <form data-maint-create class="maint-form"><label>Huerto<select name="garden" required></select></label>
        <label>Tipo<select name="task" required></select></label>
        <button class="button btn-liquid-brand" type="submit">Registrar</button></form></section>
      <section class="bento-panel" aria-labelledby="mant-lista"><h2 id="mant-lista">Registros</h2>
        <form data-maint-filter class="maint-form"><label>Huerto<select name="garden"></select></label>
        <label>Estado<select name="state"><option value="">Todos</option><option value="active">Vigentes</option><option value="voided">Anulados</option></select></label>
        <label>Tipo<select name="task"></select></label>
        ${dateField('since','Desde')}${dateField('until','Hasta')}
        <p class="sr-only" id="maint-date-format">Escribe la fecha en formato año-mes-día, por ejemplo 2026-11-07. Usa flecha abajo para abrir el calendario.</p></form>
        <div class="user-table-scroll" tabindex="0" role="region" aria-label="Registros de mantenimiento">
        <table class="user-table admin-table"><thead><tr><th scope="col">Fecha</th><th scope="col">Huerto</th><th scope="col">Tipo</th><th scope="col">Estado</th><th scope="col">Acción</th></tr></thead><tbody data-maint-rows></tbody></table></div>
        <p data-maint-status role="status"></p></section>
      <dialog class="bento-panel app-dialog" data-maint-dialog aria-labelledby="mant-dialogo"><h2 id="mant-dialogo">Registro</h2><button class="maint-dialog-close" type="button" data-maint-close aria-label="Cerrar registro">${icon('close')}</button>
        <div data-maint-history></div>
        <form data-maint-revise><label data-maint-task>Tipo correcto<select name="task"></select></label>
        <label>Motivo<textarea name="reason" rows="3" maxlength="500" required></textarea></label>
        <p data-maint-error role="alert" hidden></p>
        <div class="app-actions maint-dialog-actions"><button class="button btn-liquid-brand" type="submit" name="action" value="correct">Guardar corrección</button>
        <button class="button btn-liquid-light" type="button" data-maint-close>Cerrar</button>
        <button class="button btn-liquid-light" type="submit" name="action" value="void" data-danger="true">Anular registro</button></div></form></dialog>`;
  }
  function fillForms(root, gardens) {
    const entries = gardens.map(item => [item.id,item.name]);
    options(root.querySelector('[data-maint-create] [name=garden]'),entries);
    options(root.querySelector('[data-maint-filter] [name=garden]'),entries,'Todos');
    options(root.querySelector('[data-maint-create] [name=task]'),taskEntries());
    options(root.querySelector('[data-maint-filter] [name=task]'),taskEntries(),'Todos');
    options(root.querySelector('[data-maint-revise] [name=task]'),taskEntries());
  }
  function rows(host, items) {
    host.replaceChildren(...items.map(item => {
      const open = el('button',{type:'button',className:'button btn-liquid-light',textContent:'Ver'});
      open.dataset.maintOpen = item.id;
      const when = new Date(item.at).toLocaleString('es-MX');
      return el('tr',{},...[when,item.garden,MaintenanceService.tasks[item.type]||item.type,item.state==='voided'?'Anulado':'Vigente'].map(text=>el('td',{textContent:text})),el('td',{},open));
    }));
  }
  function history(host, record, revisions) {
    const lines = [`Original: ${MaintenanceService.tasks[record.originalType]||record.originalType}`];
    for(const item of revisions) lines.push(`${new Date(item.at).toLocaleString('es-MX')} · ${item.kind==='anulacion'?'Anulación':'Corrección a '+(MaintenanceService.tasks[item.correctedType]||item.correctedType)}: ${item.reason}`);
    host.replaceChildren(el('ol',{className:'user-history-list'},...lines.map(text=>el('li',{textContent:text}))));
  }
  function datePicker() {
    const picker = el('div',{id:'maint-calendar',className:'maint-calendar',hidden:true});
    picker.setAttribute('popover','manual');
    picker.setAttribute('role','dialog');
    picker.setAttribute('aria-labelledby','maint-calendar-title');
    picker.setAttribute('aria-describedby','maint-calendar-help');
    picker.innerHTML = `<div class="maint-calendar-header"><h2 id="maint-calendar-title">Calendario</h2>
      <button type="button" data-date-action="close" aria-label="Cerrar calendario">${icon('close')}</button></div>
      <div class="maint-calendar-navigation"><button type="button" data-date-action="prev" aria-label="Mes anterior">${icon('arrow')}</button>
      <select data-date-month aria-label="Mes"></select><input type="number" data-date-year min="1" max="9999" step="1" aria-label="Año" inputmode="numeric">
      <button type="button" data-date-action="next" aria-label="Mes siguiente">${icon('arrow')}</button></div>
      <h3 id="maint-calendar-month" data-date-heading aria-live="polite" aria-atomic="true"></h3>
      <p id="maint-calendar-help" class="sr-only">Usa las flechas para recorrer los días, Inicio y Fin para la semana, Re Pág y Av Pág para cambiar de mes, y Mayús para cambiar de año. Pulsa Intro para seleccionar y Escape para cerrar.</p>
      <div data-date-grid></div><div class="maint-calendar-footer"><button type="button" data-date-action="today">Hoy</button><button type="button" data-date-action="clear">Limpiar</button></div>`;
    options(picker.querySelector('[data-date-month]'),months.map((month,index)=>[index,month]));
    return picker;
  }
  function renderCalendar(picker, {year,month,days,selected,today,focused}) {
    picker.querySelector('[data-date-month]').value = String(month);
    picker.querySelector('[data-date-year]').value = String(year);
    picker.querySelector('[data-date-heading]').textContent = `${months[month]} de ${year}`;
    picker.querySelector('[data-date-action=prev]').disabled = year === 1 && month === 0;
    picker.querySelector('[data-date-action=next]').disabled = year === 9999 && month === 11;
    const table = el('table',{className:'maint-calendar-grid'});
    table.setAttribute('role','grid');
    table.setAttribute('aria-labelledby','maint-calendar-month');
    const head = el('tr');
    weekdays.forEach((day,index) => {
      const cell = el('th',{scope:'col',textContent:['L','M','X','J','V','S','D'][index]});
      cell.setAttribute('aria-label',day);
      head.append(cell);
    });
    const body = el('tbody');
    days.forEach(week => {
      const row = el('tr');
      week.forEach((date,index) => {
        const cell = el('td');
        cell.setAttribute('role','gridcell');
        if(date) {
          cell.setAttribute('aria-selected',String(date.value === selected));
          const button = el('button',{type:'button',textContent:String(date.day),tabIndex:date.value === focused ? 0 : -1});
          button.dataset.dateValue = date.value;
          button.setAttribute('aria-label',`${weekdays[index]}, ${date.day} de ${months[month].toLowerCase()} de ${year}`);
          if(date.value === today) button.setAttribute('aria-current','date');
          cell.append(button);
        }
        row.append(cell);
      });
      body.append(row);
    });
    table.append(el('thead',{},head),body);
    picker.querySelector('[data-date-grid]').replaceChildren(table);
  }
  const messages = {stale:'Otra persona cambió este registro. Revísalo de nuevo antes de continuar.',forbidden:'Tu cuenta no tiene acceso a este huerto.',invalid:'Revisa los datos e inténtalo de nuevo.',limited:'Demasiadas operaciones. Espera un momento.'};
  const textOf = status => messages[status] || 'Esta sección se está actualizando.';
  // Monta el panel y devuelve las operaciones de presentación que coordina MaintenanceController.
  function mount(root) {
    root.innerHTML = shell();
    const dialog = root.querySelector('[data-maint-dialog]'), status = root.querySelector('[data-maint-status]');
    const revise = root.querySelector('[data-maint-revise]'), error = root.querySelector('[data-maint-error]');
    const showError = code => { error.textContent = code === 'reason' ? 'Escribe el motivo.' : textOf(code); error.hidden = false; };
    return {dialog, revise, filter: root.querySelector('[data-maint-filter]'), create: root.querySelector('[data-maint-create]'),
      closers: root.querySelectorAll('[data-maint-close]'),
      notify(code, failed = false) {
        const box = root.querySelector('#admin-feedback');
        box.hidden = false; box.textContent = {created:'Intervención registrada.',voided:'Registro anulado.',corrected:'Corrección guardada.'}[code] || textOf(code);
        box.setAttribute('role',failed?'alert':'status'); box.focus();
      },
      statusText(text) { status.textContent = text; },
      loading() { status.textContent = 'Cargando registros…'; },
      failed(code) { status.textContent = textOf(code); },
      show(result, first) {
        if(first) fillForms(root,result.gardens);
        rows(root.querySelector('[data-maint-rows]'),result.items);
        status.textContent = result.gardens.length ? `${result.total} registros.` : 'Tu cuenta no tiene huertos asignados.';
        root.querySelector('[data-maint-create] button').disabled = !result.gardens.length;
      },
      openDetail(record, revisions) {
        history(root.querySelector('[data-maint-history]'),record,revisions);
        revise.reset(); error.hidden = true;
        revise.hidden = record.state === 'voided';
        revise.elements.task.value = record.type;
        dialog.showModal();
      },
      closeDetail() { if(dialog.open) dialog.close(); },
      showError};
  }
  return {shell,fillForms,rows,history,datePicker,renderCalendar,mount};
})();

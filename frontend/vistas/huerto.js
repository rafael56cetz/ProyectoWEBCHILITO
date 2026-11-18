// VISTA · Huerto: Mi huerto y sus pantallas, panel técnico, mantenimiento y soporte, guías de cuidado y mantenimientos del operador.
// Define: GardenViews, TechnicalViews, CareViews, SupportViews, CareGuideViews, MaintenanceViews.

// ── Huerto ──
// Mi huerto, crear huerto, vincular equipo, ficha de planta y Mis huertos. Todo dato del servidor entra con escaparHTML.
const GardenViews = (() => {
  const STAGES = {sin_sembrar:'Sin sembrar', germinacion:'Germinación', plantula:'Plántula', crecimiento:'Crecimiento', floracion:'Floración', fructificacion:'Fructificación'};
  const ORDER_TITLES = {regar:'Riego', lampara_apagar:'Apagar la lámpara', lampara_automatico:'Restaurar la lámpara automática', autodiagnostico:'Revisión del equipo',
    probar_bomba:'Prueba de bomba', ventilador_encender:'Encender el ventilador', ventilador_apagar:'Apagar el ventilador', reiniciar:'Reinicio del equipo', lectura_inmediata:'Lectura inmediata'};
  const TIMED_ORDERS = ['regar', 'probar_bomba'];
  const ORDER_STATES = {pendiente:['Pendiente','ambar'], enviado:['Enviada','ambar'], confirmado:['Confirmada','verde'], fallido:['Falló','rojo'], expirado:['Sin respuesta','gris']};
  const ERRORS = {
    'huerto-limite':'Ya tienes 3 huertos. Archiva uno para crear otro.',
    'huerto-sin-equipo':'Ya tienes un huerto sin equipo. Vincúlalo antes de crear otro.',
    'huerto-con-equipo':'Desvincula el equipo antes de archivar este huerto.',
    'equipo-no-vinculado':'Este huerto no tiene un equipo vinculado.',
    'deposito-con-agua':'Tu depósito tiene agua desde tu última recarga. Podrás registrar otra cuando el flotador marque nivel bajo.',
    'deposito-repetida':'Ya registraste esta recarga: no hace falta registrar otra.',
    'deposito-resuelta':'Esta recarga detectada ya se confirmó, se descartó o quedó sin confirmar.',
    'deposito-espera':'Ya registraste una recarga hace menos de 12 horas.',
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
    // Mismo texto que «Hola, alias · huerto», con un peso distinto para cada parte.
    const garden = gardenName ? `<span class="garden-welcome-garden">${name ? '<span class="garden-welcome-dot"> · </span>' : ''}${escaparHTML(gardenName)}</span>` : '';
    const title = name ? `<span class="garden-welcome-hello">Hola, </span><span class="garden-welcome-name">${escaparHTML(name)}</span>${garden}` : garden || 'Te damos la bienvenida a El Chilito';
    const lead = name && !gardenName ? '<p class="garden-welcome-lead">Te damos la bienvenida a El Chilito.</p>' : '';
    return `<div class="garden-welcome"><h1>${title}</h1>${lead}<p class="garden-welcome-phrase">${escaparHTML(phrase)}</p></div>`;
  }
  // Título de Panel técnico, Mantenimiento y Soporte con la misma tipografía del saludo: pantalla y, debajo, el huerto.
  const screenTitle = (title, gardenName, intro = '') => `<div class="garden-welcome"><h1><span class="garden-welcome-name">${title}</span><span class="garden-welcome-garden"><span class="garden-welcome-dot"> · </span>${escaparHTML(gardenName)}</span></h1>${intro ? `<p class="garden-welcome-phrase">${intro}</p>` : ''}</div>`;

  function deviceTag(device) {
    if(!device) return tag('Sin equipo');
    return {en_linea:tag('En línea', 'verde'), desconectado:tag('Desconectado', 'rojo'), nunca:tag('Esperando conexión')}[device.connection];
  }
  // Solo con 2 o más huertos. «Crear otro» se desactiva con su motivo (3.1).
  function selector(gardens, current, screen = 'huerto') {
    if(gardens.length < 2) return '';
    const reason = gardens.length >= 3 ? 'Máximo 3 huertos' : gardens.some(item => !item.device) ? 'Primero vincula tu huerto sin equipo' : '';
    const items = gardens.map(item => `<li><a href="${withGarden(screen, item.id)}"${item.id === current.id ? ' aria-current="true"' : ''}><span>${escaparHTML(item.name)}</span>${deviceTag(item.device)}</a></li>`).join('');
    const create = reason ? `<li><span class="garden-selector-off">+ Crear otro huerto · ${reason}</span></li>` : '<li><a href="#huerto/nuevo">+ Crear otro huerto</a></li>';
    return `<details class="garden-selector"><summary>${icon('leaf')}<span>${escaparHTML(current.name)}</span></summary><ul>${items}${create}</ul></details>`;
  }

  function statusLine(device) {
    const status = GardenModel.connection(device);
    return status ? `<div class="user-status-line tone-${status.tone}"><span class="user-status-mark" aria-hidden="true">${icon(status.tone === 'rojo' ? 'off' : 'wifi')}</span><p>${escaparHTML(status.text)}</p></div>` : '';
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
    return `<article class="plant-card plant-photo-${plant.number}${dry ? ' is-dry' : ''}"><div class="card-top">${tag(STAGES[plant.stage] || plant.stage)}${dry ? tag('Seca', 'ambar') : ''}</div>
      <div class="plant-name"><h3>${escaparHTML(plant.name)}</h3><p>${sown}</p></div>
      <div class="plant-reading"><span>${icon('drop')}Humedad del sustrato</span>${moisture}</div>
      <a class="button btn-liquid-light" href="${withGarden(`huerto/plantas/${plant.number}`, gardenId)}">Ver planta<span class="sr-only">: ${escaparHTML(plant.name)}</span></a></article>`;
  }
  const plantsSection = (detail, title) => `<section aria-labelledby="plants-title"><div class="panel-heading"><h2 id="plants-title">${title}</h2></div><div class="plant-grid">${detail.plants.map(plant => plantCard(plant, detail.garden.id)).join('')}</div></section>`;

  function connectCard(garden) {
    return `<section class="bento-panel garden-connect"><h2>Conecta tu equipo</h2>
      <ol class="garden-steps"><li><strong>Genera tu código</strong><span>Vence en 10 minutos y solo sirve una vez.</span></li>
      <li><strong>Conéctate a la red Huerto-Setup de tu equipo</strong><span>Desde tu celular o computadora.</span></li>
      <li><strong>Escribe tu Wi-Fi y el código</strong><span>Después verás aquí cuando tu equipo quede conectado.</span></li></ol>
      <a class="button btn-liquid-brand" href="${withGarden('huerto/vincular', garden.id)}">Vincular equipo</a></section>`;
  }

  // Celda del bloque de resumen; la usan Mi huerto y el Panel técnico.
  const stat = (ico, title, main, note, tone = '') => `<div class="garden-stat${tone}"><h2>${icon(ico)}${title}</h2><strong>${main}</strong><p>${note}</p></div>`;

  // Ficha Depósito de Mi huerto: el estado y una sola línea, como las demás cifras. Lo que haya por hacer (rellenar, confirmar
  // una recarga detectada) vive en Mantenimiento; aquí solo una insignia que lleva allí.
  function tankStat(tank, fallbackHasWater, gardenId = '') {
    const data = tank || (fallbackHasWater == null ? null : {hasWater:fallbackHasWater});
    const info = GardenModel.tankBrief(data);
    const badge = GardenModel.tankPending(data) ? `<a class="tank-badge" href="${withGarden('mantenimiento', gardenId)}">Revisar en Mantenimiento →</a>` : '';
    return `<div class="garden-stat garden-tank${info.tone}"><h2>${icon('tank')}Depósito de agua</h2><strong>${info.status}</strong><p>${escaparHTML(info.line)}</p>${badge}</div>`;
  }
  // Botón de recarga manual: desactivado cuando el servidor no la permite, con el motivo a la vista.
  function refillButton(action, content, tank, extraClass = '', attrs = '', tone = 'light') {
    const {allowed, reason} = GardenModel.refillState(tank);
    const id = `${action}-reason`;
    const html = button(action, content, tone, `${attrs}${allowed ? '' : ` disabled aria-describedby="${id}"`}`);
    return {button:extraClass ? html.replace('class="button ', `class="button ${extraClass} `) : html,
      reason:allowed ? '' : `<p class="refill-reason user-small-copy" id="${id}" data-refill-reason>${escaparHTML(reason)}</p>`};
  }
  const tankPanel = (tank, gardenId) => `<section class="bento-panel garden-stats garden-tank-panel" aria-label="Depósito de agua">${tankStat(tank, null, gardenId)}</section>`;

  function metrics(detail) {
    const {metrics: m, lamp, plants} = detail;
    const average = GardenModel.averageMoisture(plants);
    const lampState = {on:'Encendida', off:'Apagada'}[lamp?.state] || 'Sin lectura';
    return `<section class="bento-panel garden-stats" aria-label="Resumen del huerto">
      ${tankStat(detail.tank, m?.tankHasWater, detail.garden.id)}
      ${stat('drop', 'Humedad media del sustrato', average === null ? 'Sin lectura' : `${number(average)}<small>%</small>`, 'Promedio de las plantas con lectura')}
      ${stat('temp', 'Ambiente', reading(m?.temperature, '°C'), `Humedad relativa: ${reading(m?.airHumidity, '%')}`)}
      ${stat('sun', 'Lámpara', lampState, lamp?.mode === 'manual-off' ? 'Apagado manual' : 'Automático')}</section>`;
  }

  function deviceNote(device) {
    if(device.connection === 'desconectado') return '<p class="user-data-warning" role="status">Tu equipo está desconectado. Revisa su corriente y tu Wi-Fi.</p>';
    if(!device.lastReadingAt) return '<p class="user-data-warning" role="status">Esperando la primera lectura de tu equipo.</p>';
    return '';
  }

  const summaryCard = summary => `<section class="bento-panel user-diagnosis" aria-labelledby="diagnosis-title"><div class="user-diagnosis-head"><span class="user-diagnosis-mark">${icon('sparkle')}</span><h2 id="diagnosis-title">Resumen de tu huerto</h2></div><div class="user-diagnosis-copy">
    ${summary ? `<p>${escaparHTML(summary.content)}</p><p class="user-diagnosis-meta">Generado con IA · no sustituye tu revisión · ${AppViews.date(summary.generatedAt)}</p>${button('summaries', 'Ver anteriores')}`
      : '<p>El resumen aparecerá cuando tu equipo haya enviado lecturas.</p>'}<div data-summaries></div></div></section>`;

  function summaryList(items) {
    if(!items.length) return '<p class="user-diagnosis-meta">No hay resúmenes en los últimos 30 días.</p>';
    return `<ol class="user-history-list">${items.map(item => `<li><div><p>${escaparHTML(item.content)}</p><p class="user-diagnosis-meta">${AppViews.date(item.generatedAt)}</p></div></li>`).join('')}</ol>`;
  }

  function quickActions(detail) {
    const off = detail.lamp?.mode === 'manual-off';
    const tile = (ico, label) => `${icon(ico)}<span>${label}</span>`;
    // La recarga del depósito vive en Mantenimiento («Depósito de agua»); la ficha solo enlaza allí cuando hay algo pendiente.
    return `<div class="user-section-heading"><div><h2>Acciones rápidas</h2></div></div>
      <section class="user-quick-actions garden-actions" aria-label="Acciones rápidas">
        <a class="button btn-liquid-light" href="#mantenimiento">${tile('check', 'Registrar un cuidado')}</a>
        ${button('order', tile('activity', 'Revisar mi equipo'), 'light', 'data-type="autodiagnostico"')}
        ${button('order-confirm', tile('sun', off ? 'Restaurar automático' : 'Apagar lámpara'), 'light', `data-type="${off ? 'lampara_automatico' : 'lampara_apagar'}"`)}
        <a class="button btn-liquid-light is-featured" href="#soporte">${tile('support', 'Solicitar revisión técnica')}</a></section>
      <div data-order-card></div>
      <p class="user-safety-copy">Ante una emergencia, utiliza el paro físico del equipo.</p>`;
  }

  // Mi huerto en sus tres versiones: A sin huerto, B sin equipo, C con equipo.
  function summary({status, gardens, detail}, name) {
    if(status === 'loading') return loading;
    if(status === 'error') return failed;
    if(!gardens.length) return emptyGarden(name);
    const head = selector(gardens, detail.garden);
    if(!detail.garden.device) return `${head}${welcome(name, detail.garden.name)}${connectCard(detail.garden)}${detail.tank ? tankPanel(detail.tank, detail.garden.id) : ''}${plantsSection(detail, 'Tus tres plantas')}`;
    return `${head}<div class="home-head">${welcome(name, detail.garden.name)}${statusLine(detail.garden.device)}</div>${deviceNote(detail.garden.device)}${metrics(detail)}${plantsSection(detail, 'Tus tres plantas')}${summaryCard(detail.summary)}${quickActions(detail)}`;
  }

  // Tarjeta de orden 3.3: el estado lo confirma el equipo, no esta pantalla.
  function orderCard(order) {
    const [label, tone] = ORDER_STATES[order.state] || ['Sin respuesta', 'gris'];
    const detail = TIMED_ORDERS.includes(order.type) ? ` · planta ${order.plant} · ${order.duration} s` : '';
    return `<article class="bento-panel order-card${order.state === 'enviado' ? ' is-sending' : ''}" role="status"><div><h3>${ORDER_TITLES[order.type] || 'Orden'}${detail}</h3>
      ${order.state === 'fallido' && order.error ? `<p>${escaparHTML(order.error)}</p>` : ''}</div>${tag(label, tone)}</article>`;
  }

  function newGarden() {
    return `${AppViews.heading('Crea tu huerto')}<section class="bento-panel garden-form"><p>Ponle un nombre para reconocerlo. Podrás cambiarlo después.</p>
      <form data-garden-form="create" novalidate><label for="garden-name">Nombre del huerto (opcional)</label><input id="garden-name" name="name" type="text" maxlength="60" autocomplete="off" data-campo="cosa" placeholder="Mi huerto">
      <p class="user-small-copy">Tu huerto tendrá 3 plantas de chile habanero. Disponible solo en Yucatán.</p>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Crear huerto</button><a class="button btn-liquid-light" href="#huerto">Cancelar</a></div></form></section>`;
  }

  const progress = step => `<ol class="link-progress" aria-label="Pasos">${['Código', 'Conecta tu equipo', 'Listo'].map((label, index) => `<li${index + 1 === step ? ' aria-current="step"' : index + 1 < step ? ' class="is-done"' : ''}>${label}</li>`).join('')}</ol>`;
  // Componente 3.8: el secreto en grande, con «Copiar». Con `seconds` muestra además cuánto falta para que venza.
  const codeBox = (code, {seconds = null, label = 'Tu código de vinculación'} = {}) => `<div class="link-code-box"><p class="link-code${code.length > 12 ? ' is-long' : ''}" aria-label="${label}">${escaparHTML(GardenModel.groupCode(code))}</p>
    <p class="user-small-copy">${seconds === null ? '' : `Vence en <span data-countdown>${GardenModel.clock(seconds)}</span> · `}Solo se muestra ahora.</p>${button('copy-code', 'Copiar')}</div>`;

  // Asistente 4.3. `wizard.step`: 1 código, 2 conexión, 3 listo; `wizard.code` solo existe mientras se muestra.
  function linkWizard(wizard) {
    const {garden, step, code, seconds, expired, device} = wizard;
    const head = screenTitle('Vincular equipo', garden.name) + progress(step);
    if(step === 3) return `${head}<section class="bento-panel garden-form"><span class="icon-medallion">${icon('check')}</span><h2>¡Tu equipo quedó vinculado!</h2><p>Equipo: ${escaparHTML(device.identifier)}</p><a class="button btn-liquid-brand" href="${withGarden('huerto', garden.id)}">Ir a mi huerto</a></section>`;
    if(step === 1) return `${head}<section class="bento-panel garden-form"><h2>Genera tu código</h2><p>Genera el código que escribirás en tu equipo. Vence en 10 minutos y solo sirve una vez.</p><div class="app-actions">${button('generate', 'Generar código', 'brand')}<a class="button btn-liquid-light" href="${withGarden('huerto', garden.id)}">Cancelar</a></div></section>`;
    const waiting = expired ? '<p role="alert">El código venció. Genera otro.</p>'
      : `<p role="status" class="link-waiting">Esperando a tu equipo… (vence en <span data-countdown>${GardenModel.clock(seconds)}</span>)</p>`;
    return `${head}<section class="bento-panel garden-form">${code ? codeBox(code, {seconds}) : ''}
      <ol class="garden-steps"><li>Enchufa tu equipo El Chilito. Si ya lo habías configurado, mantén presionado su botón de configuración hasta que la pantalla lo indique.</li>
      <li>En tu celular o computadora, conéctate a la red Wi-Fi <strong>Huerto-Setup-XXXX</strong> con la contraseña de la etiqueta del equipo.</li>
      <li>Abre <strong>192.168.4.1</strong> en tu navegador.</li><li>Escribe el nombre y la contraseña de tu Wi-Fi y el código que ves arriba.</li><li>Vuelve aquí: veremos cuando tu equipo quede conectado.</li></ol>
      ${waiting}<div class="app-actions">${button('generate', 'Generar otro código', 'brand')}<a class="button btn-liquid-light" href="${withGarden('huerto', garden.id)}">Cancelar</a></div>
      <details class="link-help"><summary>¿Problemas para conectar?</summary><p>Tu equipo no pudo usar el código. Revisa que lo escribiste bien o genera otro. Comprueba también que la red Wi-Fi sea de 2.4 GHz y que esté cerca del equipo.</p><a href="#soporte">Pedir ayuda a soporte</a></details></section>`;
  }


  const CHART_LABELS = {'1h':['Hace 1 h', 'Hace 30 min', 'Ahora'], '24h':['Hace 24 h', 'Hace 12 h', 'Ahora'], '7d':['Hace 7 días', 'Hace 3 días', 'Ahora'],
    '30d':['Hace 30 días', 'Hace 15 días', 'Ahora']};
  const CHART_PERIODS = {'1h':'la última hora', '24h':'las últimas 24 horas', '7d':'los últimos 7 días', '30d':'los últimos 30 días'};
  const chartNumber = value => Number.isFinite(value) ? AppModel.number(value) : '—';

  // Sin datos se dibuja solo el marco (ejes y cuadrícula): nunca valores inventados.
  function emptyChart(title, unit, labels) {
    const grid = [0, .5, 1].map(step => { const y = 36 + 144 * step; return `<line x1="56" y1="${y}" x2="586" y2="${y}"/><text x="44" y="${y + 4}" text-anchor="end">—</text>`; }).join('');
    return `<article class="bento-panel user-chart is-empty"><div class="user-chart-heading"><h2>${escaparHTML(title)}</h2><p>—<span> ${unit}</span></p></div><div class="user-chart-frame"><svg class="user-history-chart" viewBox="0 0 620 228" aria-hidden="true">${grid}<g class="user-chart-labels">${labels.map((label, index) => `<text x="${56 + index * 265}" y="214" text-anchor="${['start', 'middle', 'end'][index]}">${label}</text>`).join('')}</g></svg><p class="user-chart-empty-note">Aún no hay registros para este periodo.</p></div></article>`;
  }

  // Una o varias series con puntos {at, value, min, max}. Con una sola serie y min/max se dibuja su banda.
  // Lecturas crudas → un punto por intervalo (promedio; la banda conserva el mínimo y el máximo), para que la línea sea legible.
  const CHART_BUCKET_MS = {'1h':60e3, '24h':600e3, '7d':3600e3, '30d':6 * 3600e3};
  function aggregate(points, range) {
    const size = CHART_BUCKET_MS[range];
    if(!size) return points;
    const groups = new Map();
    points.forEach(point => {
      const key = Math.floor(Date.parse(point.at) / size);
      groups.set(key, [...(groups.get(key) || []), point]);
    });
    const mean = values => values.reduce((sum, value) => sum + value, 0) / values.length;
    return [...groups.entries()].map(([key, group]) => {
      const bands = group.filter(point => Number.isFinite(point.min) && Number.isFinite(point.max));
      return {at:new Date((key + .5) * size).toISOString(), value:mean(group.map(point => point.value)),
        ...(bands.length ? {min:Math.min(...bands.map(point => point.min)), max:Math.max(...bands.map(point => point.max))} : {})};
    });
  }
  function lineChart({title, series, unit, range, id}) {
    const labels = CHART_LABELS[range] || CHART_LABELS['7d'];
    const drawn = series.map(item => ({name:item.name, points:aggregate((Array.isArray(item.points) ? item.points : [])
      .filter(point => Number.isFinite(point.value) && Number.isFinite(Date.parse(point.at))), range).sort((a, b) => Date.parse(a.at) - Date.parse(b.at))}));
    const all = drawn.flatMap(item => item.points);
    if(!all.length) return emptyChart(title, unit, labels);
    const times = all.map(point => Date.parse(point.at)), first = Math.min(...times), last = Math.max(...times);
    const banded = point => Number.isFinite(point.min) && Number.isFinite(point.max);
    const extent = all.flatMap(point => banded(point) ? [point.value, point.min, point.max] : [point.value]);
    const low = Math.min(...extent), high = Math.max(...extent), spread = high - low || 1, lo = low - spread * .18, hi = high + spread * .18;
    const x = point => 56 + (Date.parse(point.at) - first) / ((last - first) || 1) * 530, y = value => 180 - (value - lo) / (hi - lo) * 144;
    const grid = [0, .5, 1].map(step => { const row = 36 + 144 * step; return `<line x1="56" y1="${row}" x2="586" y2="${row}"/><text x="44" y="${row + 4}" text-anchor="end">${escaparHTML(chartNumber(hi - (hi - lo) * step))}</text>`; }).join('');
    const single = drawn.length === 1 ? drawn[0].points : [];
    const withBand = single.filter(banded);
    const band = withBand.length > 1 ? `<polygon class="user-chart-band" points="${[...withBand.map(point => `${x(point)},${y(point.max)}`), ...withBand.map(point => `${x(point)},${y(point.min)}`).reverse()].join(' ')}"/>` : '';
    const lines = drawn.map((item, index) => item.points.length > 1 ? `<polyline class="user-chart-line is-${index}" points="${item.points.map(point => `${x(point)},${y(point.value)}`).join(' ')}"/>` : '').join('');
    // Con una sola serie, un área que se desvanece hacia la base ayuda a leer el nivel; con varias se omite para no mezclar colores.
    const area = single.length > 1 ? `<defs><linearGradient id="chart-${id}-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="user-chart-fill-top"/><stop offset="1" class="user-chart-fill-bottom"/></linearGradient></defs><polygon class="user-chart-area" fill="url(#chart-${id}-fill)" points="${x(single[0])},180 ${single.map(point => `${x(point)},${y(point.value)}`).join(' ')} ${x(single[single.length - 1])},180"/>` : '';
    const latest = single.length ? single[single.length - 1] : null;
    const dot = latest ? `<circle class="user-chart-dot" cx="${x(latest)}" cy="${y(latest.value)}" r="4"/>` : '';
    const legend = drawn.length > 1 ? `<ul class="user-chart-legend">${drawn.map((item, index) => `<li class="is-${index}"><svg viewBox="0 0 28 8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4"/></svg>${escaparHTML(item.name)}</li>`).join('')}</ul>` : '';
    const summary = latest ? `${escaparHTML(chartNumber(latest.value))}<span> ${unit}</span>` : '';
    return `<article class="bento-panel user-chart"><div class="user-chart-heading"><h2>${escaparHTML(title)}</h2><p>${summary}</p></div>${legend}<svg class="user-history-chart" viewBox="0 0 620 228" role="img" aria-labelledby="chart-${id}-title chart-${id}-desc"><title id="chart-${id}-title">${escaparHTML(title)}</title><desc id="chart-${id}-desc">${all.length} registros en ${CHART_PERIODS[range] || CHART_PERIODS['7d']}.${latest ? ` Último valor: ${escaparHTML(chartNumber(latest.value))} ${unit}.` : ''}</desc><g class="user-chart-grid">${grid}</g>${area}${band}${lines}${dot}<g class="user-chart-labels">${labels.map((label, index) => `<text x="${[56, 321, 586][index]}" y="216" text-anchor="${['start', 'middle', 'end'][index]}">${label}</text>`).join('')}</g></svg></article>`;
  }
  const chart = (title, readings, unit, range, id) => lineChart({title, series:[{name:title, points:readings}], unit, range, id});

  const noGarden = title => `${AppViews.heading(title)}<section class="bento-panel garden-empty"><h2>Aún no tienes un huerto</h2><p>Crea tu huerto para usar esta pantalla.</p><a class="button btn-liquid-brand" href="#huerto/nuevo">Crear mi huerto</a></section>`;
  const noDevice = (gardens, garden, title, screen) => `${selector(gardens, garden, screen)}${screenTitle(title, garden.name)}<section class="bento-panel garden-empty"><h2>Tu huerto aún no tiene equipo</h2><p>Vincula tu equipo para usar esta pantalla.</p><a class="button btn-liquid-brand" href="${withGarden('huerto/vincular', garden.id)}">Vincular equipo</a></section>`;
  const orderTitle = order => `${ORDER_TITLES[order.type] || 'Orden'}${TIMED_ORDERS.includes(order.type) ? ` · planta ${order.plant} · ${order.duration} s` : ''}`;
  const orderStateTag = state => { const [label, tone] = ORDER_STATES[state] || ['Sin respuesta', 'gris']; return tag(label, tone); };

  const dialog = '<dialog class="bento-panel app-dialog garden-dialog" aria-labelledby="garden-dialog-title"><div data-garden-dialog-content></div></dialog>';
  const today = () => MaintenanceDates.format(MaintenanceDates.today());

  function plantDialogs(plant, hasDevice) {
    return {
      edit: `<h2 id="garden-dialog-title">Editar planta</h2><form class="dialog-form" data-garden-form="plant" novalidate>
        <div class="dialog-field is-wide"><label for="plant-name">Nombre de la planta</label><input id="plant-name" name="name" type="text" maxlength="40" required data-campo="cosa" value="${escaparHTML(plant.name)}"></div>
        <div class="dialog-field"><label for="plant-date">Fecha de siembra</label><input id="plant-date" name="sowingDate" type="date" max="${today()}" value="${escaparHTML(plant.sowingDate || '')}"></div>
        <div class="dialog-field"><label for="plant-stage">Etapa</label><select id="plant-stage" name="stage">${GardenModel.STAGES.map(stage => `<option value="${stage}"${stage === plant.stage ? ' selected' : ''}>${STAGES[stage]}</option>`).join('')}</select></div>
        <p class="user-small-copy dialog-note">${icon('info')}<span>Al cambiar la etapa, guardamos la fecha de hoy en su línea de vida.</span></p>
        <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Guardar</button></div></form>`,
      water: `<h2 id="garden-dialog-title">Regar esta planta</h2><form class="dialog-form" data-garden-form="water" novalidate>
        <div class="dialog-field is-wide"><label for="water-seconds">Duración del riego</label><select id="water-seconds" name="duration">${GardenModel.WATERING_SECONDS.map(seconds => `<option value="${seconds}"${seconds === 8 ? ' selected' : ''}>${seconds} segundos</option>`).join('')}</select></div>
        <p class="user-small-copy dialog-note">${icon('info')}<span>Si el depósito no tiene agua, tu equipo no regará.</span></p>
        <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit"${hasDevice ? '' : ' disabled'}>Regar</button></div></form>`};
  }

  function plantPage({garden, plant, stages, series, range, care, lastWatering, hasDevice}) {
    const since = plant.stageSince ? ` (desde el ${AppViews.date(plant.stageSince)})` : '';
    const sown = plant.sowingDate ? `Sembrada el ${AppViews.date(plant.sowingDate)}${plant.daysSown === null ? '' : ` (hace ${plant.daysSown} días)`}` : 'Sin fecha de siembra';
    const careLabels = {rellenar_deposito:'Recarga del depósito', sustrato:'Sustrato y perlita', germinacion:'Germinación', cosecha:'Cosecha', inspeccion:'Inspección'};
    const watering = lastWatering ? `Último riego: ${{automatico:'automático', usuario:'tuyo', soporte:'de soporte'}[lastWatering.origin] || escaparHTML(lastWatering.origin)}, ${lastWatering.duration ?? '—'} s, ${GardenModel.ago(lastWatering.at)}` : 'Sin riegos registrados';
    return `<div class="plant-hero plant-photo-${plant.number}"><a class="garden-back" href="${withGarden('huerto', garden.id)}">← Mi huerto</a>
      <div class="page-heading"><div><h1>Planta ${plant.number}${plant.name === `Planta ${plant.number}` ? '' : ` · ${escaparHTML(plant.name)}`}</h1><p>${escaparHTML(STAGES[plant.stage] || plant.stage)}${since} · ${sown}</p></div>${button('edit', 'Editar')}</div></div>
      <div class="user-chart-toolbar"><h2>Humedad del sustrato</h2><div class="user-range-control" role="group" aria-label="Periodo">${GardenModel.RANGES.map(value => button('range', {'1h':'1 h', '24h':'24 h', '7d':'7 días', '30d':'30 días'}[value], range === value ? 'brand' : 'light', `data-range="${value}" aria-pressed="${range === value}"`)).join('')}</div></div>
      ${chart('Humedad del sustrato', series, '%', range, 'plant')}
      <div class="plant-columns"><section class="bento-panel"><h2>Línea de vida</h2>${stages.length ? `<ol class="user-history-list">${stages.map(item => `<li><span>${icon('leaf')}</span><div><h3>${STAGES[item.stage] || item.stage}</h3><p>${AppViews.date(item.since)}</p></div></li>`).join('')}</ol>${stages.length === 1 ? '<p class="user-small-copy">Cambia la etapa en Editar para ir llenando su línea de vida.</p>' : ''}` : '<p>Aún no hay etapas registradas.</p>'}</section>
      <section class="bento-panel"><h2>Cuidados de esta planta</h2>${care.length ? `<ol class="user-history-list">${care.map(item => `<li><span>${icon('check')}</span><div><h3>${careLabels[item.type] || item.type}</h3><p>${AppViews.date(item.doneAt)}</p></div></li>`).join('')}</ol>` : '<p>No hay cuidados registrados para esta planta.</p>'}<a class="button btn-liquid-light" href="#mantenimiento">Registrar cuidado</a></section></div>
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

  const renameDialog = garden => `<h2 id="garden-dialog-title">Renombrar huerto</h2><form data-garden-form="rename" data-garden-id="${escaparHTML(garden.id)}" novalidate><label for="rename-name">Nombre del huerto</label><input id="rename-name" name="name" type="text" maxlength="60" required data-campo="cosa" value="${escaparHTML(garden.name)}">
    <div class="app-dialog-actions">${button('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Guardar</button></div></form>`;

  const confirmations = {
    lampara_apagar:{titulo:'¿Apagar la lámpara?', texto:'Se enviará la orden a tu equipo. Volverá a encenderse según su horario cuando restaures el modo automático.', accion:'Apagar lámpara'},
    lampara_automatico:{titulo:'¿Restaurar el modo automático?', texto:'Se enviará la orden a tu equipo. La lámpara volverá a seguir su horario.', accion:'Restaurar automático'},
    desvincular: identifier => ({titulo:`¿Desvincular el equipo ${identifier}?`, texto:'Dejará de enviar lecturas a este huerto. Para volver a usarlo tendrás que vincularlo de nuevo.', accion:'Desvincular equipo', peligro:true}),
    archivar: name => ({titulo:`¿Archivar ${name}?`, texto:'Dejarás de verlo. Su historial se conserva.', accion:'Archivar huerto', peligro:true}),
    refill:{titulo:'¿Confirmas que ya rellenaste el depósito?', texto:'Registraremos la recarga con la hora de ahora.', accion:'Sí, ya lo rellené'},
    'refill-discard':{titulo:'¿No fue una recarga?', texto:'Descartaremos esta detección y no se registrará ninguna recarga. No se puede deshacer.', accion:'No fue una recarga', peligro:true}};

  return Object.freeze({
    tag, button, stat, selector, screenTitle, statusLine, loading, noGarden, codeBox, noDevice, orderTitle, orderStateTag, lineChart, chart,
    errorText, refillButton, summary, summaryList, orderCard, newGarden, linkWizard, plantPage, plantDialogs, myGardens, renameDialog, confirmations, failed,
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

// ── Operacion ──
// Panel técnico, Mantenimiento y Soporte del huerto elegido. Todo dato del servidor entra con escaparHTML.
const TechnicalViews = (() => {
  const {button, stat, selector, screenTitle, statusLine, noGarden, noDevice, orderTitle, orderStateTag, lineChart, loading, failed} = GardenViews;
  const ORIGINS = {usuario:'Tú', soporte:'Soporte', automatico:'Automático'};
  const EVENTS = {alta:'Alta del equipo', vinculado:'Vinculado', desvinculado:'Desvinculado', conectado:'Conectado', desconectado:'Desconectado',
    error:'Error', reinicio:'Reinicio', credencial_rotada:'Credencial renovada', firmware_actualizado:'Firmware actualizado', retirado:'Retirado'};
  const ACTUATORS = {bomba:'Bomba', lampara:'Lámpara', ventilador:'Ventilador'};
  const LOG_TABS = [['ordenes', 'Órdenes'], ['actuaciones', 'Actuaciones'], ['eventos', 'Eventos']];
  const PAGE_SIZE = 25;
  const number = value => Number.isFinite(value) ? AppModel.number(value) : null;
  const reading = (value, unit) => number(value) === null ? 'Sin lectura' : `${number(value)}<small>${unit}</small>`;
  const when = value => AppViews.date(value);

  function cards(data) {
    const {latest, garden} = data, device = garden.device;
    const tank = latest?.tankHasWater === true ? 'Con agua' : latest?.tankHasWater === false ? 'Nivel bajo' : 'Sin lectura';
    const tankTone = latest?.tankHasWater === true ? ' is-ok' : latest?.tankHasWater === false ? ' is-low' : '';
    const link = {en_linea:'En línea', desconectado:'Desconectado', nunca:'Sin conexión aún'}[device.connection];
    return `<section class="bento-panel garden-stats${data.hasLight ? '' : ' is-3'}" aria-label="Lecturas técnicas">
      ${stat('temp', 'Ambiente · SHT31', reading(latest?.temperature, '°C'), `Humedad relativa: ${number(latest?.airHumidity) === null ? 'sin lectura' : `${number(latest.airHumidity)} %`}`)}
      ${data.hasLight ? stat('sun', 'Luz · BH1750', reading(latest?.light, ' lux'), 'Luz sobre las plantas') : ''}
      ${stat('tank', 'Flotador', tank, 'Depósito de 19 L · el flotador solo detecta nivel bajo', tankTone)}
      ${stat('wifi', 'Conexión', link, `Última conexión: ${when(device.lastConnectionAt)}${device.firmware ? ` · Firmware ${escaparHTML(device.firmware)}` : ''}`)}</section>`;
  }

  function charts(data) {
    const {series, range, plants} = data;
    const names = new Map(plants.map(plant => [plant.number, plant.name]));
    return `<section class="user-chart-grid-layout" aria-label="Gráficas de sensores">
      ${lineChart({title:'Humedad del sustrato', series:series.plants.map(item => ({name:names.get(item.number) || `Planta ${item.number}`, points:item.points})), unit:'%', range, id:'soil'})}
      ${lineChart({title:'Temperatura ambiental', series:[{name:'Temperatura', points:series.temperature}], unit:'°C', range, id:'temperature'})}
      ${lineChart({title:'Humedad relativa', series:[{name:'Humedad relativa', points:series.humidity}], unit:'%', range, id:'humidity'})}
      ${data.hasLight ? lineChart({title:'Luz', series:[{name:'Luz', points:series.light}], unit:'lux', range, id:'light'}) : ''}</section>`;
  }

  const plantTable = plants => `<section class="bento-panel"><h2>Lecturas por planta</h2><div class="user-table-scroll" tabindex="0" role="region" aria-label="Lecturas por planta"><table class="user-table is-readings"><thead><tr><th scope="col">Planta</th><th scope="col">Humedad %</th><th scope="col">ADC (0–4095)</th><th scope="col">Hora</th></tr></thead><tbody>${plants.map(plant => `<tr><td>${escaparHTML(plant.name)}</td><td>${number(plant.moisture) === null ? 'Sin lectura' : number(plant.moisture)}</td><td>${plant.adc ?? 'Sin lectura'}</td><td>${plant.measuredAt ? when(plant.measuredAt) : 'Sin lectura'}</td></tr>`).join('')}</tbody></table></div></section>`;

  const waterCard = plants => `<section class="bento-panel user-operating"><div><h2>Regar una planta</h2><p>Si el depósito no tiene agua, tu equipo no regará.</p></div>
    <form class="user-water-form" data-garden-form="water" novalidate><label for="water-plant">Planta</label><select id="water-plant" name="plant">${plants.map(plant => `<option value="${plant.number}">${escaparHTML(plant.name)}</option>`).join('')}</select>
    <label for="water-seconds">Duración</label><select id="water-seconds" name="duration">${GardenModel.WATERING_SECONDS.map(seconds => `<option value="${seconds}"${seconds === 8 ? ' selected' : ''}>${seconds} segundos</option>`).join('')}</select>
    <button class="button btn-liquid-brand" type="submit">Regar</button></form></section><div data-order-card></div>`;

  function logTable(log) {
    if(log.status === 'error') return '<p role="alert">No pudimos cargar la bitácora.</p>';
    if(!log.items.length) return AppViews.empty('Aún no hay registros');
    const rows = {
      ordenes:item => `<tr><td>${when(item.createdAt)}</td><td>${escaparHTML(orderTitle(item))}</td><td>${ORIGINS[item.origin] || escaparHTML(item.origin)}</td><td>${orderStateTag(item.state)}</td></tr>`,
      actuaciones:item => `<tr><td>${when(item.at)}</td><td>${ACTUATORS[item.actuator] || escaparHTML(item.actuator)}${item.plant ? ` · planta ${item.plant}` : ''}</td><td>${item.action === 'encendido' ? 'Encendido' : 'Apagado'}${item.duration ? ` · ${item.duration} s` : ''}</td><td>${ORIGINS[item.origin] || escaparHTML(item.origin)}</td></tr>`,
      eventos:item => `<tr><td>${when(item.at)}</td><td>${EVENTS[item.type] || escaparHTML(item.type)}</td><td>${item.detail ? escaparHTML(item.detail) : '—'}</td></tr>`};
    const heads = {ordenes:['Fecha y hora', 'Orden', 'Origen', 'Estado'], actuaciones:['Fecha y hora', 'Actuador', 'Acción', 'Origen'], eventos:['Fecha y hora', 'Evento', 'Detalle']};
    return `<div class="user-table-scroll" tabindex="0" role="region" aria-label="Bitácora del equipo"><table class="user-table"><thead><tr>${heads[log.type].map(head => `<th scope="col">${head}</th>`).join('')}</tr></thead><tbody>${log.items.map(rows[log.type]).join('')}</tbody></table></div>${pager(log)}`;
  }

  function pager({page, total}) {
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if(pages < 2) return '';
    return `<nav class="user-pager" aria-label="Páginas de la bitácora">${button('log-page', 'Anterior', 'light', `data-page="${page - 1}"${page <= 1 ? ' disabled' : ''}`)}<span>Página ${page} de ${pages}</span>${button('log-page', 'Siguiente', 'light', `data-page="${page + 1}"${page >= pages ? ' disabled' : ''}`)}</nav>`;
  }

  const logPanel = log => `<div class="user-section-heading"><div><h2>Bitácora del equipo</h2><p>Órdenes, actuaciones y eventos de tu equipo.</p></div></div>
    <section class="bento-panel user-log-panel"><div class="user-range-control" role="group" aria-label="Tipo de registro">${LOG_TABS.map(([type, label]) => button('log-tab', label, log.type === type ? 'brand' : 'light', `data-log="${type}" aria-pressed="${log.type === type}"`)).join('')}</div><div data-log-body>${logTable(log)}</div></section>`;

  function screen(state) {
    if(state.status === 'loading') return loading;
    if(state.status === 'error') return failed;
    if(!state.gardens.length) return noGarden('Panel técnico');
    const {garden, data, range, log} = state;
    if(!garden.device) return noDevice(state.gardens, garden, 'Panel técnico', 'telemetria');
    const toolbar = `<div class="user-chart-toolbar"><div class="toolbar-title"><h2>Histórico de lecturas</h2>${button('reload', `${icon('refresh')}<span class="sr-only">Actualizar</span>`, 'light', 'aria-label="Actualizar" title="Actualizar"')}</div><div class="user-range-control" role="group" aria-label="Periodo del histórico">${GardenModel.RANGES.map(value => button('range', {'1h':'1 h', '24h':'24 h', '7d':'7 días', '30d':'30 días'}[value], range === value ? 'brand' : 'light', `data-range="${value}" aria-pressed="${range === value}"`)).join('')}</div></div>`;
    return `${selector(state.gardens, garden, 'telemetria')}<div class="home-head">${screenTitle('Panel técnico', garden.name)}${statusLine(garden.device)}</div>${cards(data)}${toolbar}${charts(data)}${plantTable(data.plants)}${waterCard(data.plants)}<div data-log-panel>${logPanel(log)}</div>`;
  }

  const waterConfirmation = (plant, seconds) => ({titulo:`¿Regar ${plant}?`, texto:`Se enviará la orden a tu equipo para regar ${seconds} segundos. Si el depósito no tiene agua, no regará.`, accion:'Regar'});

  const eventLabel = type => EVENTS[type] || type;

  return Object.freeze({screen, logPanel, waterConfirmation, eventLabel});
})();

const CareViews = (() => {
  const {tag, button, selector, screenTitle, noGarden, loading, failed, refillButton} = GardenViews;
  const TYPES = {rellenar_deposito:'Rellenar depósito', sustrato:'Revisar sustrato', germinacion:'Germinación', cosecha:'Cosecha', inspeccion:'Inspección'};
  // Solo presentación: el ícono de cada tipo en los chips y en el historial.
  const CARE_ICONS = {rellenar_deposito:'drop', sustrato:'layers', germinacion:'sprout', cosecha:'leaf', inspeccion:'eye'};
  const PAGE_SIZE = 25;
  const dateField = (name, label, hint = '', pickOnly = false) => `<div class="maint-date-control"><label for="care-${name}">${label}</label>
    <div class="maint-date-field"><input type="text" name="${name}" id="care-${name}" placeholder="${pickOnly ? 'Elegir en el calendario' : 'aaaa-mm-dd'}" maxlength="10" autocomplete="off" spellcheck="false"${hint ? ' aria-describedby="care-when-hint"' : ''}${pickOnly ? ` readonly data-garden-action="care-date" data-date="${name}"` : ''}>
    <button type="button" data-date-open="${name}" data-date-label="${label}" aria-label="Abrir calendario: ${label}" aria-controls="maint-calendar" aria-expanded="false" aria-haspopup="dialog">${icon('calendar')}</button></div>${hint ? `<p id="care-when-hint" class="user-small-copy">${hint}</p>` : ''}</div>`;
  const plantOptions = (plants, whole) => `<option value="">${whole ? 'Todo el huerto' : '—'}</option>${plants.map(plant => `<option value="${plant.number}">${escaparHTML(plant.name)}</option>`).join('')}`;
  const typeOptions = selected => Object.entries(TYPES).map(([value, label]) => `<option value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`).join('');
  // Chips del tipo: muestran el <select id="care-type"> (que sigue en el formulario) y lo cambian con su mismo evento «change».
  const chip = (action, content, attrs) => button(action, content, 'light', attrs).replace('class="button ', 'class="button care-chip ');
  // En «Registrar un cuidado» no se ofrece la recarga del depósito: vive en la sección «Depósito de agua».
  const FORM_TYPES = Object.fromEntries(Object.entries(TYPES).filter(([value]) => value !== 'rellenar_deposito'));
  const FORM_DEFAULT = 'sustrato';
  const formTypeOptions = selected => Object.entries(FORM_TYPES).map(([value, label]) => `<option value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`).join('');
  const typeChips = selected => `<div class="care-chips care-type-chips" role="group" aria-labelledby="care-type-label">${Object.entries(FORM_TYPES).map(([value, label]) => chip('care-type', `${icon(CARE_ICONS[value])}<span>${label}</span>`, `data-type="${value}" aria-pressed="${value === selected}"`)).join('')}</div>`;
  // Planta como botones: cada uno pone su valor en el <select id="care-plant"> (que sigue en el formulario). «Todo el huerto» solo en inspección.
  const plantName = plant => escaparHTML(plant.name || `Planta ${plant.number}`);
  const plantChips = plants => `<div class="care-chips care-plant-chips" role="group" aria-labelledby="care-plant-label">${chip('care-plant', '<span>Todo el huerto</span>', 'data-plant="" data-whole aria-pressed="false" hidden')}${plants.map(plant => chip('care-plant', `<span>${plantName(plant)}</span>`, `data-plant="${escaparHTML(String(plant.number))}" aria-pressed="false"`)).join('')}</div>`;
  // «¿Cuándo?» en pestañas: Ahora deja el campo vacío, Ayer escribe la fecha de ayer y Elegir día abre el calendario del mismo campo.
  const WHEN = [['now', 'Ahora', 'clock'], ['yesterday', 'Ayer', 'refresh'], ['pick', 'Elegir día', 'calendar']];
  const whenTabs = () => `<div class="care-chips care-when-chips" role="group" aria-labelledby="care-when-label">${WHEN.map(([value, label, mark]) => chip('care-when', `${icon(mark)}<span>${label}</span>`, `data-when="${value}" aria-pressed="${value === 'now'}"`)).join('')}</div>`;
  const WHEN_HINT = {field:'Déjalo vacío para registrar ahora, o escribe un día de hasta 7 días atrás.', pick:'Puedes elegir un día de hasta 7 días atrás.'};

  function form(plants) {
    return `<section class="bento-panel garden-form care-register" aria-labelledby="care-title"><h2 id="care-title">Registrar un cuidado</h2>
      <form data-garden-form="care" novalidate>
        <div class="care-type-field"><label for="care-type" id="care-type-label">¿Qué hiciste?</label>${typeChips(FORM_DEFAULT)}<select id="care-type" name="type" class="care-hidden-select" tabindex="-1" aria-hidden="true">${formTypeOptions(FORM_DEFAULT)}</select></div>
        <div class="care-field care-plant-field" data-care-plant><span class="care-label" id="care-plant-label">¿En qué planta?</span>${plantChips(plants)}<select id="care-plant" name="plant" class="care-hidden-select" tabindex="-1" aria-hidden="true">${plantOptions(plants, false)}</select></div>
        <div class="care-fields">
          <div class="care-when" data-care-when data-when-mode="now"><span class="care-label care-when-label" id="care-when-label">¿Cuándo?</span>${whenTabs()}
            <div class="care-when-date" data-care-when-date hidden>${dateField('when', '¿Cuándo?', WHEN_HINT.pick)}</div></div>
          <div class="care-field" data-care-chiles hidden><label for="care-chiles">Chiles cosechados (opcional)</label>
            <div class="care-stepper">${button('care-chiles', icon('minus'), 'light', 'data-step="-1" aria-label="Quitar un chile" aria-controls="care-chiles"').replace('class="button ', 'class="button care-step ')}<input id="care-chiles" name="chiles" type="text" inputmode="numeric" maxlength="3" autocomplete="off" placeholder="0" data-campo="entero" data-min="0" data-max="999">${button('care-chiles', icon('plus'), 'light', 'data-step="1" aria-label="Agregar un chile" aria-controls="care-chiles"').replace('class="button ', 'class="button care-step ')}</div>
            <p class="care-stepper-live sr-only" aria-live="polite" data-care-chiles-live></p></div>
        </div>
        <div class="care-register-footer">
          <p class="care-register-help">¿Dudas sobre cómo revisar el sustrato? <a class="care-guide-link" href="#mantenimiento/sustrato" data-care-guide-link="${CareGuideService.SUBSTRATE_KEY}">Ver guía de sustrato</a></p>
          <div class="care-register-actions"><button class="button btn-liquid-brand care-submit" type="submit">Registrar</button></div>
        </div></form></section>`;
  }

  // Fila de estado (solo lectura): el último registro no anulado de cada tipo. Lo da el servidor («latest», sin depender de la
  // página); si no viene, se toma del historial ya cargado. Las horas se muestran en la zona del navegador: la app supone
  // que la persona está en Yucatán (el depósito usa America/Merida explícitamente).
  const STATUS_CARDS = [['rellenar_deposito', 'Último relleno de depósito'], ['cosecha', 'Última cosecha'], ['sustrato', 'Última revisión de sustrato'], ['inspeccion', 'Última inspección']];
  const plain = text => String(text).replace(/[\u00a0\u202f]/g, ' ');
  function stamp(value) {
    const moment = new Date(value);
    if(!Number.isFinite(moment.getTime())) return '—';
    const day = d => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime(), now = new Date();
    const diff = Math.round((day(now) - day(moment)) / 864e5);
    const hour = plain(moment.toLocaleTimeString('es-MX', {hour:'numeric', minute:'2-digit', hour12:true})).replace(/\s*([ap])\.?\s?m\.?$/i, (_, x) => ` ${x.toLowerCase()}. m.`);
    const date = diff === 0 ? 'Hoy' : diff === 1 ? 'Ayer'
      : plain(moment.toLocaleDateString('es-MX', {day:'numeric', month:'short', ...(moment.getFullYear() !== now.getFullYear() ? {year:'numeric'} : {})})).replace(/\./g, '');
    return `<time datetime="${escaparHTML(moment.toISOString())}">${escaparHTML(`${date}, ${hour}`)}</time>`;
  }
  function status(cares = null, plants = []) {
    const ready = cares?.status === 'ready';
    const plantName = number => { const found = plants.find(plant => Number(plant.number) === Number(number)); return found ? escaparHTML(found.name) : `Planta ${escaparHTML(String(number))}`; };
    const card = ([type, label]) => {
      const last = !ready ? null : cares.latest ? cares.latest[type] || null : cares.items.filter(item => item.type === type && !item.voided).sort((a, b) => new Date(b.doneAt) - new Date(a.doneAt))[0];
      const value = !cares ? 'Cargando…' : !ready ? 'No disponible' : last ? stamp(last.doneAt) : 'Sin registros';
      // El depósito no es de una planta: en vez de «Todo el huerto» solo se dice si lo detectó el equipo.
      const detail = !last ? '' : type === 'rellenar_deposito' ? (last.origin === 'equipo' ? escaparHTML(GardenModel.detectedLabel(last)) : '')
        : `${last.plant ? plantName(last.plant) : 'Todo el huerto'}${last.chiles != null ? ` · ${escaparHTML(String(last.chiles))} chiles` : ''}`;
      return `<li class="care-status-card"><p class="care-status-label">${label}</p><p class="care-status-value">${value}</p>${detail ? `<p class="care-status-detail">${detail}</p>` : ''}</li>`;
    };
    return `<ul class="care-status-grid">${STATUS_CARDS.map(card).join('')}</ul>`;
  }

  function filters(plants) {
    return `<section class="bento-panel care-history" aria-labelledby="care-history-title"><h2 id="care-history-title">Historial de cuidados</h2>
      <form class="care-filters" data-garden-form="care-filter" novalidate>
        <div><label for="filter-plant">Planta</label><select id="filter-plant" name="planta"><option value="">Todas</option><option value="huerto">Todo el huerto</option>${plants.map(plant => `<option value="${plant.number}">${escaparHTML(plant.name)}</option>`).join('')}</select></div>
        <div><label for="filter-type">Tipo</label><select id="filter-type" name="tipo"><option value="">Todos</option>${typeOptions('')}</select></div>
        <div><label for="filter-period">Periodo</label><select id="filter-period" data-care-period><option value="">Todo el historial</option><option value="hoy">Hoy</option><option value="7d">Últimos 7 días</option><option value="rango">Elegir fechas</option></select></div>
        <div class="care-range" data-care-range hidden>${dateField('since', 'Desde', '', true)}</div><div class="care-range" data-care-range hidden>${dateField('until', 'Hasta', '', true)}</div>
        <div class="app-actions"><button class="button btn-liquid-brand care-filter-submit" type="submit">Filtrar</button>${button('care-clear', 'Limpiar').replace('class="button ', 'class="button care-filter-clear ')}</div></form>
      <div data-care-list></div></section>`;
  }

  function row(item) {
    const detail = item.chiles != null ? ` · ${item.chiles} chiles` : '';
    const where = item.plant ? `planta ${item.plant}` : 'todo el huerto';
    const title = TYPES[item.type] || escaparHTML(item.type);
    const marks = `${item.origin === 'equipo' ? tag(GardenModel.detectedLabel(item), 'verde') : ''}${item.voided ? tag('Anulado', 'rojo') : ''}${item.corrected ? tag('Corregido por soporte', 'ambar') : ''}`;
    const reason = item.reason ? `<details><summary>Motivo</summary><p>${escaparHTML(item.reason)}</p></details>` : '';
    const mark = item.voided ? 'close' : item.corrected ? 'pencil' : CARE_ICONS[item.type] || 'check';
    return `<li class="care-row${item.voided ? ' is-voided' : ''}${item.corrected ? ' is-corrected' : ''}"><span class="care-row-icon">${icon(mark)}</span><div class="care-row-main"><h3>${item.voided ? `<s>${title}</s>` : title}</h3><p>${when(item.doneAt)} · ${where}${detail}</p></div>${marks ? `<div class="care-row-marks">${marks}</div>` : ''}${reason ? `<div class="care-row-reason">${reason}</div>` : ''}</li>`;
  }
  const when = value => AppViews.date(value);

  function list(cares) {
    if(cares.status === 'error') return '<p role="alert">No pudimos cargar el historial.</p>';
    if(!cares.items.length) return AppViews.empty('No hay cuidados con estos filtros', 'Al completar un cuidado, regístralo para conservar su fecha.');
    const pages = Math.max(1, Math.ceil(cares.total / PAGE_SIZE));
    const pager = pages < 2 ? '' : `<nav class="user-pager" aria-label="Páginas del historial">${button('care-page', 'Anterior', 'light', `data-page="${cares.page - 1}"${cares.page <= 1 ? ' disabled' : ''}`)}<span>Página ${cares.page} de ${pages}</span>${button('care-page', 'Siguiente', 'light', `data-page="${cares.page + 1}"${cares.page >= pages ? ' disabled' : ''}`)}</nav>`;
    return `<ol class="user-history-list">${cares.items.map(row).join('')}</ol>${pager}`;
  }

  function screen(state) {
    if(state.status === 'loading') return loading;
    if(state.status === 'error') return failed;
    if(!state.gardens.length) return noGarden('Mantenimiento');
    const {garden, plants} = state;
    return `${selector(state.gardens, garden, 'mantenimiento')}<div class="home-head">${screenTitle('Mantenimiento', garden.name, 'Registra los cuidados que realizas y consulta tu historial.')}</div><section class="care-status" aria-label="Últimos cuidados" data-care-status>${status()}</section><div data-care-tank>${tankSection(state.tank)}</div>${form(plants)}${filters(plants)}${CareGuideViews.slot()}`;
  }

  // Sección «Depósito de agua» (arriba de Mantenimiento): estado, lo que toca hacer según la fase que decide el servidor
  // (rellenar, responder a una detección, revisar el flotador), última recarga, duración, estimación e historial de cargas.
  const TANK_NOTE = 'Cuánto dura cada carga cambia con el calor y con la etapa de tus plantas: en floración y fructificación beben más, y en los días calurosos el agua se acaba antes.';
  function tankNotice(tank) {
    const notice = GardenModel.tankNotice(tank);
    if(!notice || notice.kind === 'detected') return '';
    if(notice.kind === 'refill') return `<p class="tank-call" role="status">${icon('drop')}<span>${escaparHTML(notice.title)}</span></p>`;
    return `<p class="tank-note${notice.kind === 'warning' ? ' is-warning' : ''}" role="status">${icon(notice.kind === 'warning' ? 'info' : 'clock')}<span>${escaparHTML(notice.text)}</span></p>`;
  }
  // Acciones según la fase: «Ya lo rellené» con nivel bajo (o sin equipo), la pregunta de una detección real o nada.
  function tankActions(tank) {
    const stage = GardenModel.tankStage(tank);
    if(stage === 'detectada') {
      const notice = GardenModel.tankNotice(tank);
      if(!notice) return '';
      const id = escaparHTML(tank.pendingRefill.id);
      return `<div class="tank-pending" role="group" aria-labelledby="tank-pending-title"><p class="tank-pending-title" id="tank-pending-title">${icon('drop')}<span>${escaparHTML(notice.title)}</span></p>
      <p class="tank-pending-copy">${escaparHTML(notice.text)} Solo las recargas que registras o confirmas cuentan para calcular cuánto dura tu depósito.</p>
      <div class="tank-actions">${button('refill-confirm', `${icon('check')}<span>Sí, ya lo rellené</span>`, 'brand', `data-detection="${id}"`)}${button('refill-discard', 'No fue una recarga', 'light', `data-detection="${id}"`)}</div></div>`;
    }
    if(stage !== 'rellenar' && stage !== 'sin_equipo') return '';
    const refill = refillButton('refill', `${icon('tank')}<span>Ya lo rellené</span>`, tank, '', '', 'brand');
    return `<div class="tank-actions">${refill.button}</div>${refill.reason}`;
  }
  // Icono con su nombre accesible (title para el puntero, aria-label para el lector de pantalla).
  const mark = item => `<span class="tank-mark" role="img" aria-label="${escaparHTML(item.label)}" title="${escaparHTML(item.label)}">${icon(item.icon)}</span>`;
  const TANK_VISIBLE_LOADS = 3;
  // Historial compacto: fecha · duración (o «En curso») · iconos; solo las 3 últimas y «Ver todo» despliega el resto.
  function tankLoads(tank, loads) {
    if(!tank.hasDevice) return '';
    const item = load => `<li class="tank-load${load.lowAt ? '' : ' is-open'}"><span class="tank-load-date">${escaparHTML(GardenModel.meridaShort(load.refilledAt))}</span>
      <span class="tank-load-length">${load.lowAt ? escaparHTML(GardenModel.humanDuration(load.seconds)) : 'En curso'}</span><span class="tank-load-marks">${GardenModel.refillMarks(load).map(mark).join('')}</span></li>`;
    const visible = loads.slice(0, TANK_VISIBLE_LOADS), rest = loads.slice(TANK_VISIBLE_LOADS);
    const more = rest.length ? `<details class="tank-more"><summary>Ver todo <span class="tank-more-count">(${rest.length} más)</span></summary><ol class="tank-load-list">${rest.map(item).join('')}</ol></details>` : '';
    const list = loads.length ? `<ol class="tank-load-list">${visible.map(item).join('')}</ol>${more}` : '<p class="tank-empty">Aún no hay recargas registradas.</p>';
    return `<div class="tank-loads"><h3 id="tank-history-title">Historial del depósito</h3>${list}</div>`;
  }
  // Las tres fichas: «Última recarga», «Dura en promedio» (o «Sueles rellenar cada» sin equipo) y «Necesitará agua».
  function tankFacts(tank) {
    const facts = GardenModel.tankFacts(tank);
    const fact = (label, data, extra = '') => `<li class="tank-fact${data.value === '—' ? ' is-empty' : ''}"><span class="tank-fact-label">${escaparHTML(label)}</span>
      <strong class="tank-fact-value">${escaparHTML(data.value)}${extra}</strong>${data.text ? `<span class="tank-fact-text">${escaparHTML(data.text)}</span>` : ''}</li>`;
    return `<ul class="tank-facts" aria-label="Resumen del depósito">${fact('Última recarga', facts.last, facts.last.marks.length ? `<span class="tank-fact-marks">${facts.last.marks.map(mark).join('')}</span>` : '')}${fact(facts.average.label, facts.average)}${fact('Necesitará agua', facts.next)}</ul>`;
  }
  // ⓘ: la capacidad y la nota del calor y las etapas, a un toque y no como párrafos.
  const tankInfo = tank => `<details class="tank-info"><summary aria-label="Sobre el depósito" title="Sobre el depósito">${icon('info')}</summary>
    <div class="tank-info-body"><p>${tank.hasDevice ? 'Depósito de 19 L · el flotador solo detecta nivel bajo' : 'Depósito de 19 L'}</p>${tank.hasDevice ? `<p>${TANK_NOTE}</p>` : ''}</div></details>`;
  function tankSection(data) {
    if(!data || data.status !== 'ready') return '';
    const {tank, loads = []} = data;
    const info = GardenModel.tankSummary(tank);
    const tone = tank.hasWater === true ? 'verde' : tank.hasWater === false ? 'ambar' : 'gris';
    const since = info.lowSince ? `<p class="tank-since">Nivel bajo desde ${escaparHTML(info.lowSince)}</p>` : '';
    return `<section class="bento-panel tank-history tank-section${info.tone}" aria-labelledby="tank-section-title"><div class="tank-head"><h2 id="tank-section-title">${icon('tank')}Depósito de agua</h2>
      <span class="badge tone-${tone} tank-state">${escaparHTML(info.status)}</span>${tankInfo(tank)}</div>${since}${tankNotice(tank)}${tankActions(tank)}${tankFacts(tank)}${tankLoads(tank, loads)}</section>`;
  }
  // Tras registrar o recargar el estado: vuelve a pintar la sección «Depósito de agua».
  function syncTank(root, data) {
    const box = root.querySelector('[data-care-tank]');
    if(box) box.innerHTML = tankSection(data);
  }

  // Reglas del formulario: depósito sin planta; sustrato, germinación y cosecha con planta; inspección, de una planta o de todo el huerto.
  // (También la usa el formulario de administración: lo que no exista allí se omite.)
  function adjust(root, type) {
    const plant = root.querySelector('[data-care-plant]'), chiles = root.querySelector('[data-care-chiles]'), select = plant.querySelector('select');
    plant.hidden = type === 'rellenar_deposito';
    chiles.hidden = type !== 'cosecha';
    const first = select.options[0];
    first.textContent = type === 'inspeccion' ? 'Todo el huerto' : '—';
    if(type === 'rellenar_deposito') select.value = '';
    root.querySelectorAll('.care-type-chips [data-type]').forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.type === type)));
    syncPlants(root, type);
    syncWhen(root, type);
  }
  function syncPlants(root, type = root.querySelector('#care-type')?.value) {
    const select = root.querySelector('#care-plant');
    root.querySelectorAll('.care-plant-chips [data-plant]').forEach(chip => {
      if(chip.hasAttribute('data-whole')) chip.hidden = type !== 'inspeccion';
      chip.setAttribute('aria-pressed', String(!chip.hidden && !!select && select.value === chip.dataset.plant));
    });
  }
  // Un chip pone su tipo en el <select> y lanza el mismo «change» que ya escucha el controlador.
  function pickType(root, type) {
    const select = root.querySelector('#care-type');
    if(!select || !(type in TYPES)) return;
    select.value = type;
    select.dispatchEvent(new Event('change', {bubbles:true}));
  }
  function pickPlant(root, value) {
    const select = root.querySelector('#care-plant');
    if(!select) return;
    select.value = value;
    syncPlants(root);
  }
  // «¿Cuándo?»: el depósito conserva el campo de fecha de siempre; los demás tipos usan Ahora / Ayer / Elegir día sobre el mismo campo.
  const dayText = (offset = 0) => MaintenanceDates.format(MaintenanceDates.shift(MaintenanceDates.today(), offset));
  function syncWhen(root, type = root.querySelector('#care-type')?.value) {
    const box = root.querySelector('[data-care-when]');
    if(!box) return;
    const value = box.querySelector('#care-when').value.trim();
    const mode = type === 'rellenar_deposito' ? 'field'
      : box.dataset.whenMode === 'pick' ? 'pick' : !value || value === dayText() ? 'now' : value === dayText(-1) ? 'yesterday' : 'pick';
    box.dataset.whenMode = mode;
    box.querySelector('[data-care-when-date]').hidden = !['field', 'pick'].includes(mode);
    box.querySelectorAll('.care-when-chips [data-when]').forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.when === mode)));
    const hint = box.querySelector('#care-when-hint');
    if(hint) hint.textContent = mode === 'field' ? WHEN_HINT.field : WHEN_HINT.pick;
  }
  function pickWhen(root, which) {
    const box = root.querySelector('[data-care-when]');
    if(!box) return;
    const input = box.querySelector('#care-when');
    if(which === 'now') input.value = '';
    else if(which === 'yesterday') input.value = dayText(-1);
    box.dataset.whenMode = which;
    input.dispatchEvent(new Event('input', {bubbles:true}));
    syncWhen(root);
    if(which === 'pick') box.querySelector('[data-date-open="when"]')?.click();
  }
  // Chiles con − y +: sin número es «sin contar» (no se envía), igual que el campo vacío de antes.
  function stepChiles(root, step) {
    const input = root.querySelector('#care-chiles');
    if(!input) return;
    const next = Math.min(999, Math.max(0, (Number(input.value) || 0) + Number(step)));
    input.value = next ? String(next) : '';
    const live = root.querySelector('[data-care-chiles-live]');
    if(live) live.textContent = `${next} ${next === 1 ? 'chile' : 'chiles'}`;
  }
  // Campos de fecha de solo lectura: tocarlos abre su calendario.
  function openDate(root, name) {
    root.querySelector(`[data-date-open="${name}"]`)?.click();
  }
  // Periodo del historial: llena Desde y Hasta (los mismos campos que envía «Filtrar»); «Elegir fechas» los muestra para el calendario.
  function period(root, value) {
    const form = root.querySelector('[data-garden-form="care-filter"]');
    if(!form) return;
    const since = form.elements.since, until = form.elements.until;
    if(value === 'hoy') { since.value = dayText(); until.value = dayText(); }
    else if(value === '7d') { since.value = dayText(-6); until.value = dayText(); }
    else if(value === '') { since.value = ''; until.value = ''; }
    form.querySelectorAll('[data-care-range]').forEach(field => { field.hidden = value !== 'rango'; });
    [since, until].forEach(field => field.dispatchEvent(new Event('input', {bubbles:true})));
  }

  function reset(root) {
    root.querySelector('[data-garden-form="care"]').reset();
    const box = root.querySelector('[data-care-when]');
    if(box) box.dataset.whenMode = 'now';
    adjust(root, FORM_DEFAULT);
  }
  function resetFilters(root) {
    root.querySelector('[data-garden-form="care-filter"]').reset();
    period(root, '');
  }

  return Object.freeze({screen, list, status, tankSection, syncTank, adjust, pickType, pickPlant, pickWhen, stepChiles, openDate, period, reset, resetFilters, types:TYPES});
})();

const SupportViews = (() => {
  const {tag, button, selector, screenTitle, noGarden, noDevice, loading, failed, orderTitle, orderStateTag} = GardenViews;
  const STATES = {abierto:['En espera', 'ambar'], en_atencion:['En revisión', 'verde']};
  const RESULTS = {solucionado:'Problema solucionado', sin_falla:'No se encontró ninguna falla', sin_respuesta:'Sin respuesta', otro:'Otro resultado'};
  const CHECKS = {conexion:'Conexión', sensor_ambiente:'Sensor de ambiente (SHT31)', sensor_luz:'Sensor de luz', sensor_sustrato_1:'Sustrato planta 1',
    sensor_sustrato_2:'Sustrato planta 2', sensor_sustrato_3:'Sustrato planta 3', flotador:'Flotador del depósito', bomba_1:'Bomba 1', bomba_2:'Bomba 2',
    bomba_3:'Bomba 3', lampara:'Lámpara', ventilador:'Ventilador'};
  const CHECK_RESULTS = {correcto:['✔ Correcto', 'verde'], falla:['✖ Falla', 'rojo'], sin_respuesta:['⏱ Sin respuesta', 'ambar'], no_instalado:['— No instalado', 'gris']};
  const when = value => AppViews.date(value);

  // Revisión del equipo para administración (y la lista simple de componentes): sin cambios de diseño.
  function diagnosticPanel(diagnostic) {
    if(!diagnostic) return '';
    const failures = GardenModel.problems(diagnostic.checks);
    const overall = diagnostic.state === 'en_curso' ? 'Revisando tu equipo…' : diagnostic.state === 'sin_respuesta' ? 'Tu equipo no respondió a la revisión.'
      : failures === 0 ? 'Todo funciona' : `Encontramos ${failures} problema${failures === 1 ? '' : 's'}`;
    const items = (diagnostic.checks || []).map(check => { const [label, tone] = CHECK_RESULTS[check.result] || ['—', 'gris']; return `<li><span>${CHECKS[check.component] || escaparHTML(check.component)}</span>${tag(label, tone)}${check.detail ? `<small>${escaparHTML(check.detail)}</small>` : ''}</li>`; }).join('');
    return `<article class="bento-panel diagnostic-card" aria-live="polite"><h3>${overall}</h3><p class="user-small-copy">Revisión del ${when(diagnostic.startedAt)}</p>${items ? `<ul class="diagnostic-list">${items}</ul>` : ''}</article>`;
  }

  // ── Ficha «Revisa tu equipo» (solo presentación): estado general, botón y componentes agrupados. ──
  const GROUPS = [['Conexión', ['conexion']], ['Sensores', ['sensor_ambiente', 'sensor_luz', 'sensor_sustrato_1', 'sensor_sustrato_2', 'sensor_sustrato_3', 'flotador']],
    ['Actuadores', ['bomba_1', 'bomba_2', 'bomba_3', 'lampara', 'ventilador']]];
  const BADGES = {correcto:['Correcto', 'is-ok', 'check'], no_instalado:['No instalado', 'is-neutral', 'minus'], falla:['Falla', 'is-alert', 'close'], sin_respuesta:['Sin respuesta', 'is-alert', 'alert']};
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  // Conteo por resultado: «6 correctos · 1 no instalado · 1 con falla».
  function tally(checks) {
    const count = result => checks.filter(check => check.result === result).length;
    return {ok:count('correcto'), absent:count('no_instalado'), failed:count('falla'), silent:count('sin_respuesta'), total:checks.length};
  }
  const extras = t => [t.absent ? `${t.absent} no instalado${t.absent === 1 ? '' : 's'}` : '', t.failed ? `${t.failed} con falla` : '', t.silent ? `${t.silent} sin respuesta` : ''].filter(Boolean);
  const overallCount = t => [t.ok ? plural(t.ok, 'correcto', 'correctos') : '', ...extras(t)].filter(Boolean).join(' · ');
  const groupCount = t => t.ok === t.total ? `${t.ok} de ${t.total} correcto${t.total === 1 ? '' : 's'}` : [`${t.ok} de ${t.total}`, ...extras(t)].join(' · ');
  function badge(result) {
    const [label, tone, mark] = BADGES[result] || ['Sin dato', 'is-neutral', 'minus'];
    return `<span class="support-badge ${tone}">${icon(mark)}<span>${label}</span></span>`;
  }
  function groups(checks) {
    const known = GROUPS.flatMap(([, items]) => items);
    const sets = [...GROUPS.map(([name, items]) => [name, checks.filter(check => items.includes(check.component))
      .sort((a, b) => items.indexOf(a.component) - items.indexOf(b.component))]), ['Otros', checks.filter(check => !known.includes(check.component))]]
      .filter(([, items]) => items.length);
    return sets.map(([name, items]) => `<section class="support-group" aria-label="${name}"><div class="support-group-head"><h4>${name}</h4><p>${groupCount(tally(items))}</p></div>
      <ul class="support-components">${items.map(check => `<li><span class="support-component-name">${CHECKS[check.component] || escaparHTML(check.component)}</span>${badge(check.result)}${check.detail ? `<small>${escaparHTML(check.detail)}</small>` : ''}</li>`).join('')}</ul></section>`).join('');
  }
  // Ocupa el hueco [data-diagnostic]: lo vuelve a pintar el controlador al revisar el equipo.
  function diagnosticCard(diagnostic) {
    const checks = diagnostic?.checks || [];
    const failures = diagnostic ? GardenModel.problems(checks) : 0;
    const [tone, mark, title] = !diagnostic ? ['is-pending', 'activity', 'Aún no has revisado tu equipo']
      : diagnostic.state === 'en_curso' ? ['is-pending', 'clock', 'Revisando tu equipo…']
      : diagnostic.state === 'sin_respuesta' ? ['is-alert', 'alert', 'Tu equipo no respondió a la revisión.']
      : failures === 0 ? ['is-ok', 'check', 'Todo funciona'] : ['is-alert', 'close', `Encontramos ${failures} problema${failures === 1 ? '' : 's'}`];
    const ago = diagnostic ? GardenModel.ago(diagnostic.startedAt) : null;
    const whenLine = !diagnostic ? 'Comprueba sensores, bombas, lámpara y conexión.'
      : `${diagnostic.state === 'en_curso' ? 'Iniciada' : 'Última revisión'}: ${when(diagnostic.startedAt)}${ago ? ` · ${ago}` : ''}`;
    const count = checks.length ? overallCount(tally(checks)) : '';
    return `<div class="support-check-result" aria-live="polite"><div class="support-status ${tone}"><span class="support-status-mark" aria-hidden="true">${icon(mark)}</span>
      <div class="support-status-text"><h3>${title}</h3><p class="support-status-when">${whenLine}</p>${count ? `<p class="support-status-count">${count}</p>` : ''}</div>
      ${button('diagnose', `${icon('activity')}<span>Revisar mi equipo</span>`, 'brand').replace('class="button ', 'class="button support-primary ')}</div>
      ${checks.length ? `<div class="support-groups">${groups(checks)}</div>` : ''}</div>`;
  }

  function check(data, diagnostic) {
    return `<section class="bento-panel support-card support-check-card" aria-labelledby="support-check-title"><h2 id="support-check-title">Revisa tu equipo</h2>
      <div data-diagnostic>${diagnosticCard(diagnostic)}</div><div data-order-card></div></section>`;
  }

  // ── Ficha «Solicita una revisión técnica»: radios reales con el mismo name="incident" (el controlador lee form.elements.incident.value). ──
  function requestForm(data) {
    const last = data.lastDiagnostic, attachable = last?.state === 'completado';
    const failures = attachable ? GardenModel.problems(last.checks) : 0;
    const attached = attachable ? `Se enviará: ${when(last.startedAt)} · ${failures === 0 ? 'Todo funciona' : `${failures} problema${failures === 1 ? '' : 's'}`}` : '';
    const options = Object.entries(GardenModel.INCIDENTS).map(([value, label], index) => `<label class="support-option"><input type="radio" name="incident" value="${value}"${index === 0 ? ' checked' : ''}><span class="support-radio" aria-hidden="true">${icon('check')}</span><span>${label}</span></label>`).join('');
    return `<section class="bento-panel support-card support-request-card" aria-labelledby="support-request-title"><h2 id="support-request-title">Solicita una revisión técnica</h2>
      <p class="support-sub">Cuéntanos qué falla y el equipo revisará tu instalación.</p>
      <form data-garden-form="support" class="support-form" novalidate>
      <fieldset class="support-incidents" id="support-incident"><legend class="support-label">¿Qué problema tiene?</legend><div class="support-options">${options}</div></fieldset>
      <div class="support-field"><label class="support-label" for="support-note">Cuéntanos más <span>(opcional)</span></label><textarea id="support-note" name="note" maxlength="500" rows="4"></textarea><p class="support-note-count"><span data-note-count>0</span>/500</p></div>
      ${attachable ? `<label class="support-check support-check-attach"><input type="checkbox" name="attach"><span class="support-check-text"><span>Adjuntar la última revisión de mi equipo</span><small>${escaparHTML(attached)}</small></span></label>` : ''}
      <label class="support-check support-check-consent"><input type="checkbox" name="consent" required><span class="support-check-text"><span>Autorizo al equipo de soporte a revisar mi equipo durante 24 horas</span><small>Puedes revocarlo cuando quieras.</small></span></label>
      <button class="button btn-liquid-brand support-submit" type="submit" disabled>Solicitar revisión</button>
      <p class="support-submit-hint">Marca la autorización para poder enviar la solicitud.</p></form></section>`;
  }

  function activeCase(data) {
    const caso = data.active, [label, tone] = STATES[caso.state] || ['En proceso', 'gris'];
    const authorization = caso.revokedAt ? 'Acceso revocado. Soporte ya no puede ver ni controlar tu equipo.'
      : Date.parse(caso.authorizedUntil) > Date.now() ? `Autorización vigente · vence en ${GardenModel.lapse(caso.authorizedUntil)}` : 'La autorización venció.';
    const orders = data.orders.length ? `<ul class="user-history-list">${data.orders.map(order => `<li><span>${icon('tool')}</span><div><p>${when(order.createdAt)} · ${escaparHTML(orderTitle(order))}</p>${orderStateTag(order.state)}${order.error ? `<small>${escaparHTML(order.error)}</small>` : ''}</div></li>`).join('')}</ul>` : '<p>Soporte todavía no ha hecho nada en tu equipo.</p>';
    return `<section class="bento-panel garden-form" aria-labelledby="support-case-title"><h2 id="support-case-title">Caso <span class="folio">${escaparHTML(caso.folio)}</span> · ${GardenModel.INCIDENTS[caso.incident] || escaparHTML(caso.incident)}</h2>
      <p>${tag(label, tone)}</p><p>${authorization}</p>${caso.state === 'en_atencion' ? `<p>Soporte está revisando tu equipo.</p>` : ''}
      <h3>Lo que soporte ha hecho</h3>${orders}
      <div class="app-actions">${button('revoke', 'Revocar acceso', 'light', `data-danger="true" data-case="${escaparHTML(caso.id)}"${caso.revokedAt ? ' disabled' : ''}`)}${button('cancel-case', 'Cancelar solicitud', 'light', `data-case="${escaparHTML(caso.id)}"`)}</div></section>`;
  }

  function history(items) {
    if(!items.length) return '';
    return `<section class="bento-panel"><h2>Historial de solicitudes</h2><ol class="user-history-list">${items.map(item => `<li><span>${icon('support')}</span><div><h3>${escaparHTML(item.folio)} · ${GardenModel.INCIDENTS[item.incident] || escaparHTML(item.incident)}</h3><p>${when(item.createdAt)} · ${{resuelto:'Resuelto', cancelado:'Cancelado', abierto:'Abierto', en_atencion:'En revisión'}[item.state]}</p>${item.state === 'resuelto' ? `<p>Resultado: ${RESULTS[item.result] || '—'}${item.resolutionNote ? ` · ${escaparHTML(item.resolutionNote)}` : ''}</p>` : ''}</div></li>`).join('')}</ol></section>`;
  }

  function screen(state) {
    if(state.status === 'loading') return loading;
    if(state.status === 'error') return failed;
    if(!state.gardens.length) return noGarden('Soporte técnico');
    const {garden, data, diagnostic} = state;
    if(!data.hasDevice) return noDevice(state.gardens, garden, 'Soporte técnico', 'soporte');
    const head = `${selector(state.gardens, garden, 'soporte')}${screenTitle('Soporte técnico', garden.name)}`;
    return `${head}${data.active ? activeCase(data) : `<div class="support-cards">${check(data, diagnostic)}${requestForm(data)}</div>`}${history(data.history)}`;
  }

  return Object.freeze({screen, diagnosticCard, diagnosticPanel, activeCase,
    confirmations:{
      revoke:{titulo:'¿Revocar el acceso de soporte?', texto:'Soporte dejará de ver y controlar tu equipo de inmediato. Tu caso seguirá abierto.', accion:'Revocar acceso', peligro:true},
      cancel:{titulo:'¿Cancelar tu solicitud?', texto:'Se cerrará el caso y se revocará el acceso. No se puede deshacer.', accion:'Cancelar solicitud', peligro:true}},
    countNote(root, length) { const node = root.querySelector('[data-note-count]'); if(node) node.textContent = String(length); },
    consent(root, allowed) { const button = root.querySelector('[data-garden-form="support"] [type=submit]'); if(button) button.disabled = !allowed; }});
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
          ${field('care-order','order','Orden',`<input id="care-order" name="order" inputmode="numeric" maxlength="4" required autocomplete="off" data-campo="entero" data-min="1" data-max="9999" aria-describedby="care-order-help">`,'Número de 1 a 9999. Se muestra de menor a mayor.')}
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
  const confirmations = {
    publish:{titulo:'¿Publicar esta ficha?', texto:'Será visible para todas las personas usuarias en la guía de cuidado.', accion:'Publicar'},
    withdraw:{titulo:'¿Retirar esta ficha?', texto:'Dejará de verse para las personas usuarias. Podrás volver a publicarla.', accion:'Retirar ficha', peligro:true}};
  return Object.freeze({confirmations, slot, paint, openItem, focusSection, adminShell, mountAdmin, adminFeedback, adminLoading, adminApplying, focusNew, adminList, adminError, setFilter, fillEditor, readEditor, markInvalid, formStatus, saving, staleOption, closeEditor, focusEditor});
})();

// ── Mantenimientos ──
// Mantenimientos de todos los huertos (5.3). Todo dato del servidor entra escapado. Incluye el calendario compartido de los filtros de fecha.
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
  const months = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  const weekdays = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo'];
  const T = AdminTableViews, {tag} = GardenViews;
  const act = (...args) => T.button(...args);
  const when = value => AppViews.date(value);
  const ERRORS = {'stale-record':'Otra persona cambió este registro. Se actualizó la lista.', 'cuidado-anulado':'Este registro ya está anulado y no admite más cambios.',
    'not-found':'No se encontró ese huerto o ese registro.', 'rate-limited':'Demasiadas operaciones seguidas. Espera un momento.', 'access-denied':'Tu cuenta no tiene acceso a esta operación.',
    'deposito-con-agua':'El depósito de ese huerto tiene agua desde su última recarga: se registra otra cuando el flotador marque nivel bajo.',
    'deposito-repetida':'Ya hay una recarga registrada después del último nivel bajo de ese huerto.',
    'deposito-espera':'Ese huerto ya tiene una recarga registrada hace menos de 12 horas.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.') => ERRORS[code] || fallback;
  const STATES = {vigente:'Vigente', corregido:'Corregido', anulado:'Anulado'};
  const plantLabel = plant => plant ? `planta ${plant}` : 'todo el huerto';
  const stateTag = record => record.voided ? tag('Anulado', 'rojo') : record.corrected ? tag('Corregido', 'ambar') : tag('Vigente', 'verde');
  const choices = (items, selected = '') => items.map(([value, label]) => `<option value="${escaparHTML(value)}"${String(value) === String(selected) ? ' selected' : ''}>${escaparHTML(label)}</option>`).join('');
  const typeItems = () => Object.entries(CareViews.types);
  const plantItems = whole => [['', whole ? 'Todo el huerto' : '—'], [1, 'Planta 1'], [2, 'Planta 2'], [3, 'Planta 3']];
  const today = () => MaintenanceDates.format(MaintenanceDates.today());
  // Las reglas de tipo, planta y chiles son las del formulario de la persona usuaria (CareViews.adjust).
  const careFields = (record, whole = false) => `<label for="mant-type">Tipo</label><select id="mant-type" name="type" data-care-type>${choices(typeItems(), record?.type || 'rellenar_deposito')}</select>
    <div data-care-plant hidden><label for="mant-plant">Planta</label><select id="mant-plant" name="plant">${choices(plantItems(whole), record?.plant || '')}</select></div>
    <div data-care-chiles hidden><label for="mant-chiles">Chiles cosechados (opcional)</label><input id="mant-chiles" name="chiles" type="text" inputmode="numeric" maxlength="3" autocomplete="off" data-campo="entero" data-min="0" data-max="999" value="${record?.chiles ?? ''}"></div>`;

  function filters(values) {
    return `<form class="care-filters" data-admin-form="care-filter" novalidate>
      <div><label for="mant-search">Buscar</label><input id="mant-search" name="busqueda" type="search" maxlength="60" placeholder="Correo del dueño o huerto" value="${escaparHTML(values.busqueda || '')}"></div>
      <div><label for="mant-garden">N.º de huerto</label><input id="mant-garden" name="huerto" type="text" inputmode="numeric" maxlength="18" pattern="[0-9]*" data-campo="digitos" value="${escaparHTML(values.huerto || '')}"></div>
      <div><label for="mant-f-plant">Planta</label><select id="mant-f-plant" name="planta">${choices([['', 'Todas'], ['huerto', 'Todo el huerto'], [1, 'Planta 1'], [2, 'Planta 2'], [3, 'Planta 3']], values.planta || '')}</select></div>
      <div><label for="mant-f-type">Tipo</label><select id="mant-f-type" name="tipo">${choices([['', 'Todos'], ...typeItems()], values.tipo || '')}</select></div>
      <div><label for="mant-f-state">Estado</label><select id="mant-f-state" name="estado">${choices([['', 'Todos'], ...Object.entries(STATES)], values.estado || '')}</select></div>
      ${T.dateField('since', 'Desde', values.since)}${T.dateField('until', 'Hasta', values.until)}
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button>${act('clear', 'Limpiar')}</div></form>`;
  }

  function row(item) {
    const chiles = item.chiles != null ? ` · ${item.chiles} chiles` : '';
    return `<tr><td>${when(item.doneAt)}</td><td>${escaparHTML(item.garden)} <small>N.º ${escaparHTML(item.gardenId)}</small></td><td>${escaparHTML(item.owner)}</td>
      <td>${escaparHTML(CareViews.types[item.type] || item.type)} · ${plantLabel(item.plant)}${chiles}</td><td>${stateTag(item)}</td><td>${act('open', 'Ver', 'light', `data-id="${escaparHTML(item.id)}"`)}</td></tr>`;
  }

  function screen(state) {
    if(state.status !== 'ready') return T.status(state.status);
    const {items} = state.list;
    const body = items.length ? T.table('Registros de mantenimiento', ['Fecha', 'Huerto', 'Dueño', 'Cuidado', 'Estado', ''], items.map(row))
      : AppViews.empty('No hay registros con estos filtros');
    return `<div class="page-heading"><div><h1>Mantenimientos</h1><p>Registra, corrige y anula intervenciones de todos los huertos. Cada cambio pide un motivo.</p></div>${act('create', '+ Registrar intervención', 'brand')}</div>
      <section class="bento-panel">${filters(state.filters)}${body}${T.pager(state.list)}</section>${T.dialog}`;
  }

  function createForm() {
    const first = MaintenanceDates.shift(MaintenanceDates.today(), -6);
    return `<h2 id="admin-dialog-title">Registrar intervención</h2><form data-admin-form="care-create" novalidate>
      <label for="mant-new-garden">N.º de huerto</label><input id="mant-new-garden" name="garden" type="text" inputmode="numeric" maxlength="18" pattern="[0-9]*" required data-campo="digitos">
      ${careFields(null, true)}
      <label for="mant-when">¿Cuándo?</label><input id="mant-when" name="when" type="date" min="${MaintenanceDates.format(first)}" max="${today()}">
      <p class="user-small-copy">Déjalo vacío para registrar ahora. Se admiten hasta 6 días atrás.</p>
      <div class="app-dialog-actions">${act('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Registrar</button></div></form>`;
  }

  function history(revisions) {
    if(!revisions.length) return '<p>Sin correcciones: este es el registro original.</p>';
    return `<ol class="user-history-list">${revisions.map(item => `<li><span>${icon('tool')}</span><div><p>${when(item.at)} · ${item.type === 'anulacion' ? 'Anulación'
      : `Corrección a ${escaparHTML(CareViews.types[item.correctedType] || item.correctedType)}, ${plantLabel(item.correctedPlant)}${item.correctedChiles != null ? `, ${item.correctedChiles} chiles` : ''}`}</p>
      <small>${escaparHTML(item.editor)}</small><p>${escaparHTML(item.reason)}</p></div></li>`).join('')}</ol>`;
  }

  function detail(record, revisions) {
    const facts = [['Huerto', `${escaparHTML(record.garden)} · N.º ${escaparHTML(record.gardenId)}`], ['Dueño', escaparHTML(record.owner)], ['Fecha', when(record.doneAt)],
      ['Cuidado', `${escaparHTML(CareViews.types[record.type] || record.type)} · ${plantLabel(record.plant)}${record.chiles != null ? ` · ${record.chiles} chiles` : ''}`], ['Estado', stateTag(record)]];
    const form = record.voided ? '' : `<form data-admin-form="care-revise" novalidate><h3>Corregir o anular</h3>${careFields(record, true)}
      <label for="mant-reason">Motivo (obligatorio)</label><textarea id="mant-reason" name="reason" rows="3" maxlength="500" required></textarea>
      <div class="app-dialog-actions">${act('close-dialog', 'Cerrar')}${act('void', 'Anular registro', 'light', 'data-danger="true"')}<button class="button btn-liquid-brand" type="submit">Guardar corrección</button></div></form>`;
    return `<h2 id="admin-dialog-title">Registro de mantenimiento</h2><dl class="user-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl>
      <h3>Historial</h3>${history(revisions)}${form || `<div class="app-dialog-actions">${act('close-dialog', 'Cerrar')}</div>`}`;
  }

  const confirmations = {void:{titulo:'¿Anular este registro?', texto:'Dejará de contar como un cuidado. El historial conserva el motivo y no se puede deshacer.', accion:'Anular registro', peligro:true}};

  function datePicker() {
    const picker = el('div',{id:'maint-calendar',className:'maint-calendar',hidden:true});
    picker.setAttribute('popover','manual');
    picker.setAttribute('role','dialog');
    picker.setAttribute('aria-labelledby','maint-calendar-title');
    picker.setAttribute('aria-describedby','maint-calendar-help');
    picker.innerHTML = `<div class="maint-calendar-header"><h2 id="maint-calendar-title">Calendario</h2>
      <button type="button" data-date-action="close" aria-label="Cerrar calendario">${icon('close')}</button></div>
      <div class="maint-calendar-navigation"><button type="button" data-date-action="prev" aria-label="Mes anterior">${icon('arrow')}</button>
      <select data-date-month aria-label="Mes"></select><input type="number" data-date-year min="1" max="9999" step="1" aria-label="Año" inputmode="numeric" data-campo="entero" data-min="1" data-max="9999">
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
  return Object.freeze({screen, createForm, detail, confirmations, errorText, datePicker, renderCalendar,
    adjust: (root, type) => CareViews.adjust(root, type), resetFilters(root) { root.querySelector('[data-admin-form="care-filter"]').reset(); }});
})();

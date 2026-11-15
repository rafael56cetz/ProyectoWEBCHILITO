// VISTA · Equipos: inventario de equipos para quien gestiona dispositivos. Todo dato del servidor entra escapado.
// Define: EquipmentViews.

// ── Inventario ──
const EquipmentViews = (() => {
  const {tag, codeBox} = GardenViews;
  const act = (...args) => AdminTableViews.button(...args);
  const STATES = {disponible:['Disponible', 'gris'], vinculado:['Vinculado', 'verde'], retirado:['Retirado', 'rojo']};
  const LINKS = {nunca:['Sin conexión aún', 'gris'], en_linea:['En línea', 'verde'], desconectado:['Desconectado', 'rojo']};
  const ERRORS = {'equipo-duplicado':'Ya existe un equipo con ese identificador o esa MAC.', 'equipo-no-vinculado':'Este equipo no está vinculado a ningún huerto.',
    'equipo-retirado':'Un equipo retirado no recibe credenciales nuevas.', 'equipo-no-disponible':'Solo se retira un equipo disponible. Desvincúlalo primero.',
    'rate-limited':'Demasiados intentos. Espera un momento.'};
  const errorText = (code, fallback = 'No se pudo completar la operación. Inténtalo de nuevo.') => ERRORS[code] || fallback;
  const when = value => AppViews.date(value);
  const none = value => value ? escaparHTML(value) : '—';
  const options = (items, selected) => items.map(([value, label]) => `<option value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`).join('');

  function filters(values) {
    return `<form class="care-filters" data-admin-form="equipment-filter" novalidate>
      <div><label for="eq-search">Buscar</label><input id="eq-search" name="busqueda" type="search" maxlength="60" placeholder="Identificador, MAC o correo" value="${escaparHTML(values.busqueda || '')}"></div>
      <div><label for="eq-state">Estado</label><select id="eq-state" name="estado">${options([['', 'Todos'], ...Object.entries(STATES).map(([value, [label]]) => [value, label])], values.estado || '')}</select></div>
      <div><label for="eq-link">Conexión</label><select id="eq-link" name="conexion">${options([['', 'Todas'], ...Object.entries(LINKS).map(([value, [label]]) => [value, label])], values.conexion || '')}</select></div>
      <div><label for="eq-sold">Vendido</label><select id="eq-sold" name="vendido">${options([['', 'Todos'], ['si', 'Sí'], ['no', 'No']], values.vendido || '')}</select></div>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Filtrar</button>${act('clear', 'Limpiar')}</div></form>`;
  }

  function row(item) {
    return `<tr><td><strong>${escaparHTML(item.identifier)}</strong></td><td>${escaparHTML(item.mac)}</td><td>${tag(...STATES[item.state])}</td><td>${none(item.garden)}</td><td>${none(item.owner)}</td>
      <td>${tag(...LINKS[item.connection])}</td><td>${item.sale ? escaparHTML(item.sale.buyer) : '—'}</td><td><a class="button btn-liquid-light compact" href="#admin/equipos/${item.id}">Ver<span class="sr-only"> ${escaparHTML(item.identifier)}</span></a></td></tr>`;
  }

  function list(state) {
    if(state.status !== 'ready') return AdminTableViews.status(state.status);
    const {counts, items} = state.list;
    const tiles = [['Disponibles', counts.disponible], ['Vinculados', counts.vinculado], ['Retirados', counts.retirado]]
      .map(([label, value]) => `<article class="bento-panel user-metric"><h2>${label}</h2><strong>${value}</strong></article>`).join('');
    const body = items.length ? AdminTableViews.table('Equipos', ['Identificador', 'MAC', 'Estado', 'Huerto', 'Dueño', 'Conexión', 'Venta', ''], items.map(row))
      : '<div class="user-empty-inline"><p>No hay equipos con estos filtros.</p></div>';
    return `<div class="page-heading"><div><h1>Inventario de equipos</h1></div><button type="button" class="button btn-liquid-brand" data-admin-action="create">+ Dar de alta equipo</button></div>
      <section class="user-summary-metrics" aria-label="Resumen del inventario">${tiles}</section>
      <section class="bento-panel">${filters(state.filters)}${body}${AdminTableViews.pager(state.list)}</section>${AdminTableViews.dialog}`;
  }

  const createForm = () => `<h2 id="admin-dialog-title">Dar de alta equipo</h2><form data-admin-form="equipment-create" novalidate>
    <label for="eq-identifier">Identificador</label><input id="eq-identifier" name="identifier" type="text" maxlength="32" placeholder="ESP32-A1B2" autocomplete="off" required>
    <label for="eq-mac">MAC</label><input id="eq-mac" name="mac" type="text" maxlength="17" placeholder="AA:BB:CC:DD:EE:FF" autocomplete="off" required>
    <label for="eq-firmware">Firmware (opcional)</label><input id="eq-firmware" name="firmware" type="text" maxlength="32" placeholder="1.0.0" autocomplete="off">
    <p class="user-small-copy">Al crearlo generaremos su credencial y te la mostraremos una sola vez.</p>
    <div class="app-dialog-actions">${act('close-dialog', 'Cancelar')}<button class="button btn-liquid-brand" type="submit">Crear equipo</button></div></form>`;

  const credential = (identifier, secret) => `<h2 id="admin-dialog-title">Credencial de ${escaparHTML(identifier)}</h2>${codeBox(secret, {label:'Credencial del equipo'})}
    <p>Grábala en el equipo ahora. No se volverá a mostrar.</p><div class="app-dialog-actions"><button class="button btn-liquid-brand" type="button" data-admin-action="close-credential">Ya la grabé</button></div>`;

  const confirmations = {
    unlink:identifier => ({titulo:`¿Desvincular ${identifier}?`, texto:'El equipo dejará de enviar lecturas a este huerto y el huerto quedará sin equipo.', accion:'Desvincular', peligro:true}),
    rotate:identifier => ({titulo:`¿Rotar la credencial de ${identifier}?`, texto:'El equipo dejará de conectarse hasta que grabes la nueva credencial.', accion:'Rotar credencial'}),
    retire:identifier => ({titulo:`¿Retirar ${identifier}?`, texto:'El equipo ya no podrá usarse ni venderse. No se puede deshacer.', accion:'Retirar equipo', peligro:true})};

  function detailScreen(state) {
    if(state.status !== 'ready') return AdminTableViews.status(state.status);
    const {device, events, diagnostics} = state.data;
    const facts = [['Estado', tag(...STATES[device.state])], ['Conexión', tag(...LINKS[device.connection])], ['MAC', escaparHTML(device.mac)],
      ['Firmware', none(device.firmware)], ['Última conexión', device.lastConnectionAt ? when(device.lastConnectionAt) : '—'],
      ['Alta', `${when(device.registeredAt)}${device.registeredBy ? ` · ${escaparHTML(device.registeredBy)}` : ''}`],
      ['Huerto', device.garden ? escaparHTML(device.garden.name) : '—'], ['Dueño', none(device.owner)],
      ['Venta vigente', device.sale ? `<a href="#admin/ventas">${escaparHTML(device.sale.buyer)}</a>` : '—'], ['Retirado', device.retiredAt ? when(device.retiredAt) : '—']];
    const actions = [device.state === 'vinculado' ? act('unlink', 'Desvincular', 'light', 'data-danger="true"') : '', device.state !== 'retirado' ? act('rotate', 'Rotar credencial') : '',
      device.state === 'disponible' ? act('retire', 'Retirar equipo', 'light', 'data-danger="true"') : ''].join('');
    const rows = events.items.map(item => `<tr><td>${when(item.at)}</td><td>${escaparHTML(TechnicalViews.eventLabel(item.type))}</td><td>${none(item.detail)}</td><td>${none(item.actor)}</td></tr>`);
    const diagnosticList = diagnostics.length ? `<ul class="diagnostic-list">${diagnostics.map(item => `<li>${when(item.startedAt)} ${item.overall ? tag(item.overall === 'correcto' ? 'Correcto' : 'Con fallas', item.overall === 'correcto' ? 'verde' : 'rojo') : tag(item.state === 'en_curso' ? 'En curso' : 'Sin respuesta', 'gris')}</li>`).join('')}</ul>` : '<p>Aún no hay autodiagnósticos.</p>';
    return `<a class="garden-back" href="#admin/equipos">← Inventario</a>${AppViews.heading(device.identifier)}
      <section class="bento-panel"><dl class="user-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl><div class="app-actions">${actions}</div></section>
      <section class="bento-panel"><h2>Historial del equipo</h2>${rows.length ? AdminTableViews.table('Historial del equipo', ['Fecha y hora', 'Evento', 'Detalle', 'Por'], rows) : '<p>Sin eventos.</p>'}${AdminTableViews.pager(events)}</section>
      <section class="bento-panel"><h2>Últimos autodiagnósticos</h2>${diagnosticList}</section>${AdminTableViews.dialog}`;
  }

  return Object.freeze({list, detailScreen, createForm, credential, confirmations, errorText,
    paint: (root, html) => AdminTableViews.paint(root, html),
    openDialog: (root, html) => AdminTableViews.open(root, html), closeDialog: root => AdminTableViews.dismiss(root),
    resetFilters(root) { root.querySelector('[data-admin-form="equipment-filter"]').reset(); }});
})();

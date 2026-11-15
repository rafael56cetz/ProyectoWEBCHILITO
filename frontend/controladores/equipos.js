// CONTROLADOR · Equipos: inventario de equipos (lista, alta, detalle y acciones). El servidor confirma; aquí nunca se supone un éxito.
// Define: EquipmentController.

// ── Inventario ──
const EquipmentController = (() => {
  function mount({root, route, service = EquipmentService}) {
    const life = new AbortController();
    const detailId = route.extra || '';
    let state = {status:'loading', list:{items:[], page:1, total:0, counts:{disponible:0, vinculado:0, retirado:0}}, filters:{}, data:null};
    let serial = 0, working = false, secret = null;
    const paint = () => EquipmentViews.paint(root, detailId ? EquipmentViews.detailScreen(state) : EquipmentViews.list(state));
    async function load(page = 1) {
      const id = ++serial;
      const result = await (detailId ? service.detail(detailId, page) : service.list(state.filters, page));
      if(life.signal.aborted || id !== serial) return;
      if(result.status !== 'ready') { state = {...state, status:'error'}; paint(); return; }
      state = detailId ? {...state, status:'ready', data:result} : {...state, status:'ready', list:{items:result.items, page:result.page, total:result.total, counts:result.counts}};
      paint();
    }
    const fail = result => mostrarAviso('error', EquipmentViews.errorText(result.code));
    async function create(form) {
      const values = {identifier:form.elements.identifier.value.trim(), mac:form.elements.mac.value.trim(), firmware:form.elements.firmware.value.trim()};
      const invalid = EquipmentModel.validate(values);
      if(invalid) { mostrarAviso('error', invalid.message); return; }
      const result = await service.create(values);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      secret = result.credential;
      EquipmentViews.openDialog(root, EquipmentViews.credential(values.identifier, secret));
    }
    async function act(kind) {
      const device = state.data.device;
      if(!await confirmar(EquipmentViews.confirmations[kind](device.identifier))) return;
      const result = await service[kind](device.id);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      if(kind === 'rotate') { secret = result.credential; EquipmentViews.openDialog(root, EquipmentViews.credential(device.identifier, secret)); return; }
      mostrarAviso('exito', kind === 'unlink' ? 'Equipo desvinculado.' : 'Equipo retirado.');
      await load(1);
    }
    async function copy() {
      try { await navigator.clipboard.writeText(secret); mostrarAviso('exito', 'Credencial copiada.'); }
      catch { mostrarAviso('error', 'No se pudo copiar. Selecciónala y cópiala a mano.'); }
    }
    root.addEventListener('click', async event => {
      if(event.target.closest('[data-garden-action="copy-code"]')) { await copy(); return; }
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page} = trigger.dataset;
      working = true;
      try {
        if(action === 'page') await load(Number(page));
        else if(action === 'clear') { state.filters = {}; EquipmentViews.resetFilters(root); await load(1); }
        else if(action === 'create') EquipmentViews.openDialog(root, EquipmentViews.createForm());
        else if(action === 'close-dialog') EquipmentViews.closeDialog(root);
        else if(action === 'close-credential') EquipmentViews.closeDialog(root);
        else if(['unlink', 'rotate', 'retire'].includes(action)) await act(action);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const kind = event.target.closest('[data-admin-form]')?.dataset.adminForm;
      if(working) return;
      working = true;
      try {
        if(kind === 'equipment-filter') { state.filters = Object.fromEntries(new FormData(event.target)); await load(1); }
        else if(kind === 'equipment-create') await create(event.target);
      } finally { working = false; }
    }, {signal:life.signal});
    // Al cerrarse el diálogo de la credencial (también con Esc) el secreto se olvida y se vuelve a leer el inventario.
    root.addEventListener('close', () => { if(secret) { secret = null; load(1); } }, {capture:true, signal:life.signal});
    load(1);
    return {redraw() {}, dispose() { secret = null; serial++; life.abort(); }};
  }
  return {mount};
})();

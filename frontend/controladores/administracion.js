// CONTROLADOR · Administración: flota, consola remota, consultas, ventas, administradores, textos legales, consentimientos y el panel general.
// Define: AdminReauthController, FleetController, ConsoleController, InquiryController, SalesController, AdminAccessController, LegalAdminController, ConsentController, AppController.

// ── Administracion ──
// Telemetría de flota: lista, filtros y panel de solo lectura. El servidor decide qué se ve según la capacidad.
const FleetController = (() => {
  function mount({root, service = FleetService} = {}) {
    const life = new AbortController();
    let state = {status:'loading', filters:{}, data:null};
    let serial = 0, working = false;
    const access = () => ({inventory:AppModel.allowedAdmin().some(item => item.id === 'admin/equipos')});
    const paint = () => FleetViews.paint(root, FleetViews.screen(state, access()));
    async function load(page = 1) {
      const id = ++serial;
      const result = await service.load(state.filters, page);
      if(life.signal.aborted || id !== serial) return;
      state = result.status === 'ready' ? {...state, status:'ready', data:result} : {...state, status:'error'};
      paint();
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page, id} = trigger.dataset;
      working = true;
      try {
        if(action === 'page') await load(Number(page));
        else if(action === 'refresh') await load(state.data?.page || 1);
        else if(action === 'clear') { state.filters = {}; FleetViews.resetFilters(root); await load(1); }
        else if(action === 'peek') FleetViews.openDialog(root, FleetViews.peek(state.data.items.find(item => item.id === id)));
        else if(action === 'close-dialog') FleetViews.closeDialog(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      if(working || event.target.closest('[data-admin-form]')?.dataset.adminForm !== 'fleet-filter') return;
      working = true;
      try { state.filters = Object.fromEntries(new FormData(event.target)); await load(1); } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {dispose() { serial++; life.abort(); }};
  }
  return {mount};
})();

// Consola remota: la bandeja y la pantalla de cada caso (#admin/soporte/<folio>). Salir de la pantalla no cierra la sesión técnica:
// al volver se retoma sola. Mientras hay sesión se consulta el servidor cada 10 s para enterarse de una revocación.
const ConsoleController = (() => {
  const POLL_MS = 10000;
  // Pestaña de la bandeja a la que se vuelve desde un caso.
  let inboxTab = 'abierto';
  function mount({root, route, service = ConsoleService} = {}) {
    const life = new AbortController();
    const folio = route?.extra || '';
    let state = {status:'loading', tab:inboxTab, counts:{abierto:0, en_atencion:0, resuelto:0}, inbox:{items:[], page:1, total:0}, detail:null};
    let serial = 0, pollSerial = 0, working = false, poller = null;
    const fail = result => mostrarAviso('error', ConsoleViews.errorText(result.code));
    const caseId = () => state.detail?.case.id || null;
    const sessionId = () => state.detail?.session?.id || null;
    function paint() {
      ConsoleViews.paint(root, folio ? ConsoleViews.caseScreen(state) : ConsoleViews.inboxScreen(state));
      if(state.detail) ConsoleViews.lockOrders(root, state.detail.orders);
    }

    async function loadInbox(page, {quiet = false} = {}) {
      const result = await service.inbox(state.tab, page, {quiet});
      if(life.signal.aborted) return;
      state = result.status === 'ready' ? {...state, status:'ready', counts:result.counts, inbox:{items:result.items, page:result.page, total:result.total}} : {...state, status:'error'};
    }
    async function loadCase({quiet = false} = {}) {
      const result = await service.detail(folio, {quiet});
      if(life.signal.aborted) return;
      state = result.status === 'ready' ? {...state, status:'ready', detail:{case:result.case, diagnostic:result.diagnostic, session:result.session, orders:result.orders}}
        : {...state, status:result.code === 'not-found' || result.code === 'invalid-input' ? 'not-found' : 'error', detail:null};
    }
    async function refresh({page = state.inbox.page, quiet = false} = {}) {
      const id = ++serial;
      await (folio ? loadCase({quiet}) : loadInbox(page, {quiet}));
      if(life.signal.aborted || id !== serial) return;
      paint();
      if(sessionId()) startPolling(); else stopPolling();
    }

    function stopPolling() { clearInterval(poller); poller = null; pollSerial++; }
    function startPolling() {
      if(!poller) poller = setInterval(() => { if(document.visibilityState === 'visible' && !working) pollOnce(); }, POLL_MS);
      pollOnce();
    }
    async function pollOnce() {
      const id = sessionId(), mine = ++pollSerial;
      if(!id) return;
      const result = await service.session(id, life.signal);
      if(life.signal.aborted || mine !== pollSerial || id !== sessionId()) return;
      if(result.code === 'not-found') { await sessionEnded('manual'); return; }
      if(result.status !== 'ready') return;
      if(result.session.state === 'closed') { await sessionEnded(result.session.reason); return; }
      state = {...state, detail:{...state.detail, orders:result.orders}};
      ConsoleViews.paintLive(root, result);
    }
    async function sessionEnded(reason) {
      stopPolling();
      mostrarAviso('info', ConsoleViews.closingText(reason));
      await refresh({quiet:true});
    }

    async function closeSession() {
      stopPolling();
      const result = await service.endSession(sessionId());
      if(life.signal.aborted) return;
      if(result.status === 'accepted' || result.code === 'not-found') mostrarAviso('exito', 'Sesión técnica cerrada.'); else fail(result);
      await refresh();
    }
    async function change(request, message) {
      const result = await request;
      if(life.signal.aborted) return;
      if(result.status === 'accepted') mostrarAviso('exito', message); else fail(result);
      await refresh();
    }
    async function order(body, confirmation) {
      if(confirmation && !await confirmar(confirmation)) return;
      const result = await service.order(sessionId(), body);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') fail(result); else mostrarAviso('exito', 'Orden enviada al equipo.');
      await pollOnce();
    }
    async function resolve(form) {
      const fields = new FormData(form), result = String(fields.get('result') || ''), note = String(fields.get('note') || '').trim();
      if(result === 'otro' && !note) { mostrarAviso('error', 'Escribe una nota cuando el resultado es «Otro».'); return; }
      if(!await confirmar(ConsoleViews.confirmations.resolve)) return;
      stopPolling();
      await change(service.resolve(caseId(), result, note), 'Caso resuelto. El acceso de la persona terminó.');
    }

    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, tab, page, type} = trigger.dataset;
      working = true;
      try {
        if(action === 'tab') { state = {...state, tab}; inboxTab = tab; await refresh({page:1}); }
        else if(action === 'page') await refresh({page:Number(page)});
        else if(action === 'refresh') await refresh();
        else if(action === 'open-case') location.hash = `#admin/soporte/${trigger.dataset.folio}`;
        else if(action === 'attend') await change(service.attend(caseId()), 'El caso quedó a tu nombre.');
        else if(action === 'connect') await change(service.connect(caseId()), 'Sesión técnica abierta.');
        else if(action === 'order') await order({type}, type === 'reiniciar' ? ConsoleViews.confirmations.reboot : null);
        else if(action === 'close-session') await closeSession();
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('change', event => {
      if(event.target.name === 'plant' && state.detail) ConsoleViews.lockOrders(root, state.detail.orders);
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const kind = event.target.closest('[data-admin-form]')?.dataset.adminForm;
      if(working || !kind) return;
      working = true;
      try {
        if(kind === 'pump') {
          const plant = Number(event.target.elements.plant.value), duration = Number(event.target.elements.seconds.value);
          await order({type:'probar_bomba', plant, duration}, ConsoleViews.confirmations.pump(plant, duration));
        } else if(kind === 'resolve') await resolve(event.target);
      } finally { working = false; }
    }, {signal:life.signal});
    document.addEventListener('visibilitychange', () => { if(document.visibilityState === 'visible' && !working) pollOnce(); }, {signal:life.signal});
    refresh({page:1});
    return {dispose() { serial++; stopPolling(); life.abort(); }};
  }
  return {mount};
})();

// ── Consultas ──
// Coordina filtro, páginas y avance de atención del buzón de consultas.
const InquiryController = (() => {
  function mount({root, service = InquiryService} = {}) {
    const life = new AbortController();
    const view = InquiryViews.mount(root);
    let state = '', page = 1, busy = false;
    const REFRESH_MS = 30000;
    let shown = '';
    const signature = result => JSON.stringify([result.total, result.items.map(row => [row.id, row.state, row.notice])]);
    // Solo redibuja si llegó algo nuevo, para no mover el foco de quien está leyendo.
    async function refresh() {
      if(busy || document.visibilityState !== 'visible') return;
      const result = await service.list(state, page, {background:true});
      // La recarga también va como sondeo: una consulta nueva no alarga la sesión de quien no está tocando la consola.
      if(!life.signal.aborted && !busy && result.status === 'ready' && signature(result) !== shown) await load({quiet:true});
    }
    async function load({quiet = false} = {}) {
      view.loading();
      const result = await service.list(state, page, {background:quiet});
      if(life.signal.aborted) return;
      view.filter(state);
      if(result.status !== 'ready') { view.failed(result.status); return; }
      shown = signature(result);
      view.show(result.items, result.total, page, service);
    }
    root.addEventListener('click', async event => {
      const filter = event.target.closest('[data-inq-filter]');
      if(filter) { state = filter.dataset.inqFilter; page = 1; view.clearFeedback(); await load(); return; }
      const pager = event.target.closest('[data-inq-page]');
      if(pager) { page = Math.max(1, page + Number(pager.dataset.inqPage)); await load(); view.scrollToTop(); return; }
      const action = event.target.closest('[data-inq-id]');
      if(!action || busy) return;
      if(action.dataset.inqState === 'archivada' && !await confirmar(InquiryViews.confirmations.archive)) return;
      busy = true; view.busy(action);
      const result = await service.advance(action.dataset.inqId, action.dataset.inqState);
      busy = false;
      if(life.signal.aborted) return;
      view.advanced(result.status, action.dataset.inqState);
      await load();
    }, {signal: life.signal});
    load();
    const timer = setInterval(refresh, REFRESH_MS);
    document.addEventListener('visibilitychange', refresh, {signal: life.signal});
    return {dispose() { clearInterval(timer); life.abort(); }};
  }
  return Object.freeze({mount});
})();

// ── Ventas ──
// Ventas de equipos: lista, resumen y las operaciones sobre cada venta. El servidor valida y confirma.
const SalesController = (() => {
  function mount({root, service = SalesService}) {
    const life = new AbortController();
    let state = {status:'loading', tab:'ventas', list:{items:[], page:1, total:0}, catalog:{municipalities:[], sellable:[]}, filters:{}, summary:null, preset:'month', period:SalesModel.period('month')};
    let datesLife = null, dates = null, serial = 0, working = false;
    function paint() {
      AdminTableViews.paint(root, SalesViews.screen(state));
      datesLife?.abort();
      if(state.status !== 'ready') return;
      datesLife = new AbortController();
      dates = DateFilterViews.mount(root, datesLife.signal);
      if(state.tab === 'resumen') SalesViews.periodDates(root, state.period);
    }
    async function loadSales(page = 1) {
      const result = await service.list(state.filters, page);
      if(life.signal.aborted) return false;
      if(result.status !== 'ready') return false;
      state = {...state, list:{items:result.items, page:result.page, total:result.total}, catalog:{municipalities:result.municipalities, sellable:result.sellable}};
      return true;
    }
    async function loadSummary() {
      const result = await service.summary(state.period);
      if(life.signal.aborted || result.status !== 'ready') return false;
      state = {...state, summary:result};
      return true;
    }
    async function load(page = 1) {
      const id = ++serial;
      const ready = state.tab === 'resumen' ? await loadSummary() : await loadSales(page);
      if(life.signal.aborted || id !== serial) return;
      state = {...state, status:ready ? 'ready' : 'error'};
      paint();
    }
    const fail = result => mostrarAviso('error', SalesViews.errorText(result.code));
    function openSale(id) {
      const sale = state.list.items.find(item => item.id === id);
      if(sale) AdminTableViews.open(root, SalesViews.detail(sale));
    }
    async function afterChange(result, message) {
      if(result.status !== 'accepted') { fail(result); return; }
      mostrarAviso('exito', message);
      state = {...state, list:{...state.list, items:state.list.items.map(item => item.id === result.sale.id ? result.sale : item)}};
      AdminTableViews.open(root, SalesViews.detail(result.sale));
      await loadSales(state.list.page);
      paint();
    }
    function saleValues(form) {
      const read = name => form.elements[name].value.trim();
      const values = {device:read('device'), buyer:read('buyer'), email:read('email'), municipality:read('municipality'), price:read('price'), received:read('received') || '0',
        reference:read('reference'), method:read('method'), soldAt:read('soldAt'), note:read('note'), ...(read('plannedDelivery') ? {plannedDelivery:read('plannedDelivery')} : {})};
      return SalesModel.amount(values.price) && SalesModel.amount(values.received) ? values : null;
    }
    async function create(form) {
      const values = saleValues(form);
      if(!values) { mostrarAviso('error', 'Escribe los importes con hasta 2 decimales, por ejemplo 3500.00.'); return; }
      const result = await service.create(values);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      AdminTableViews.dismiss(root);
      mostrarAviso('exito', result.sale.accountLinked ? 'Venta registrada. Cuenta encontrada: la venta quedó enlazada.' : 'Venta registrada.');
      await load(1);
    }
    async function filter(form) {
      const invalid = dates.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const values = Object.fromEntries(new FormData(form));
      state.filters = {busqueda:values.busqueda, desde:values.since, hasta:values.until, pago:values.pago, entrega:values.entrega, municipio:values.municipio};
      await load(1);
    }
    async function period(form) {
      const invalid = dates.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const preset = form.elements.preset.value;
      state = {...state, preset, period:preset === 'custom' ? {desde:form.elements.since.value.trim(), hasta:form.elements.until.value.trim()} : SalesModel.period(preset)};
      await load(1);
    }
    async function cancel(id) {
      const sale = state.list.items.find(item => item.id === id);
      if(!sale || !await confirmar(SalesViews.confirmations.cancel(sale))) return;
      await afterChange(await service.cancel(id), 'Venta cancelada.');
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page, tab, id} = trigger.dataset;
      working = true;
      try {
        if(action === 'tab') { state = {...state, tab}; await load(1); }
        else if(action === 'page') await load(Number(page));
        else if(action === 'clear') { state.filters = {}; SalesViews.resetFilters(root); await load(1); }
        else if(action === 'create') AdminTableViews.open(root, SalesViews.createForm(state.catalog));
        else if(action === 'sale') openSale(id);
        else if(action === 'cancel-sale') await cancel(id);
        else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-admin-form]');
      if(!form || working) return;
      const {adminForm: kind, id} = form.dataset;
      const read = name => form.elements[name]?.value.trim();
      working = true;
      try {
        if(kind === 'sales-filter') await filter(form);
        else if(kind === 'sales-period') await period(form);
        else if(kind === 'sale-create') await create(form);
        else if(kind === 'sale-payment') await afterChange(await service.pay(id, read('received'), read('reference')), 'Pago registrado.');
        else if(kind === 'sale-delivery') await afterChange(await service.deliver(id, read('deliveredAt')), 'Venta marcada como entregada.');
        else if(kind === 'sale-note') await afterChange(await service.note(id, read('note')), 'Nota guardada.');
      } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {redraw() {}, dispose() { serial++; datesLife?.abort(); life.abort(); }};
  }
  return {mount};
})();

// ── Administradores ──
// Quién puede qué en el panel. La base y el servidor rechazan lo prohibido; aquí solo se arma la petición y se pide confirmación.
const AdminAccessController = (() => {
  function mount({root, service = AdminAccessService}) {
    const life = new AbortController();
    const ownEmail = (AuthService.session?.profile?.email || '').toLowerCase();
    const empty = () => ({items:[], page:1, total:0});
    let state = {status:'loading', tab:'administradores', admins:{...empty(), editable:[]}, history:empty(), activity:empty(), filters:{historial:{}, actividad:{}}, ownEmail};
    let datesLife = null, dates = null, serial = 0, working = false;
    function paint() {
      AdminTableViews.paint(root, AdminAccessViews.screen({...state, filters:state.filters[state.tab] || {}}));
      datesLife?.abort();
      if(state.status === 'ready' && state.tab === 'historial') { datesLife = new AbortController(); dates = DateFilterViews.mount(root, datesLife.signal); }
    }
    async function fetchTab(page) {
      const filters = state.filters[state.tab] || {};
      if(state.tab === 'administradores') return service.list(page);
      return state.tab === 'historial' ? service.history(filters, page) : service.activity(filters, page);
    }
    async function load(page = 1) {
      const id = ++serial;
      const result = await fetchTab(page);
      if(life.signal.aborted || id !== serial) return;
      if(result.status !== 'ready') { state = {...state, status:'error'}; paint(); return; }
      const section = state.tab === 'administradores' ? 'admins' : state.tab;
      state = {...state, status:'ready', [section]:{items:result.items, page:result.page, total:result.total, ...(result.editable ? {editable:result.editable} : {})}};
      paint();
    }
    const currentOf = email => state.admins.items.find(item => item.email.toLowerCase() === email.toLowerCase())?.capabilities.filter(code => code !== 'gestionar_administradores') || [];
    async function change(form) {
      const email = form.elements.email.value.trim(), reason = form.elements.reason.value.trim();
      const wanted = new FormData(form).getAll('capability'), current = currentOf(email);
      if(!email || !reason) { mostrarAviso('error', 'Escribe el correo y el motivo.'); return; }
      const granted = wanted.filter(code => !current.includes(code)), revoked = current.filter(code => !wanted.includes(code));
      if(!granted.length && !revoked.length) { mostrarAviso('error', 'No hay cambios que guardar.'); return; }
      if(!await confirmar(AdminAccessViews.confirmation(granted, revoked))) return;
      const result = await service.change(email, wanted, reason);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', AdminAccessViews.errorText(result.code)); return; }
      AdminTableViews.dismiss(root);
      mostrarAviso('exito', 'Capacidades actualizadas.');
      await load(1);
    }
    async function filter(kind, form) {
      if(kind === 'historial') {
        const invalid = dates.validate();
        if(invalid) { mostrarAviso('error', invalid); return; }
        const values = Object.fromEntries(new FormData(form));
        state.filters.historial = {cuenta:values.cuenta, capacidad:values.capacidad, desde:values.since, hasta:values.until};
      } else state.filters.actividad = {cuenta:form.elements.cuenta.value.trim()};
      await load(1);
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page, tab, email} = trigger.dataset;
      working = true;
      try {
        if(action === 'tab') { state = {...state, tab}; await load(1); }
        else if(action === 'page') await load(Number(page));
        else if(action === 'grant') AdminTableViews.open(root, AdminAccessViews.accessForm({}));
        else if(action === 'edit') AdminTableViews.open(root, AdminAccessViews.accessForm({email, capabilities:currentOf(email), editing:true}));
        else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-admin-form]');
      if(!form || working) return;
      working = true;
      try {
        if(form.dataset.adminForm === 'access') await change(form);
        else if(form.dataset.adminForm === 'history-filter') await filter('historial', form);
        else if(form.dataset.adminForm === 'activity-filter') await filter('actividad', form);
      } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {redraw() {}, dispose() { serial++; datesLife?.abort(); life.abort(); }};
  }
  return {mount};
})();

// ── Legales ──
// Textos legales: lista por tipo y editor. El HTML que se muestra lo devuelve el servidor ya saneado, también el de un .docx
// subido o el de lo pegado desde Word. El borrador se guarda solo cada 10 s si cambió, para no perder trabajo si la sesión vence.
const LegalAdminController = (() => {
  const NEW_PREFIX = 'nuevo-', AUTOSAVE_MS = 10000;
  function mount({root, route, service = LegalAdminService}) {
    const life = new AbortController();
    let creating = route.extra?.startsWith(NEW_PREFIX), documentId = creating ? '' : route.extra || '';
    const newType = creating && service.TYPES.includes(route.extra.slice(NEW_PREFIX.length)) ? route.extra.slice(NEW_PREFIX.length) : 'terminos';
    let state = {status:'loading', type:'terminos', data:null, document:null, preview:null};
    let serial = 0, working = false, autosave = null, lastSaved = '';
    const paint = () => AdminTableViews.paint(root, route.extra ? LegalAdminViews.editorScreen({...state, type:newType}) : LegalAdminViews.listScreen(state));
    const fail = result => mostrarAviso('error', LegalAdminViews.errorText(result.code));
    const editorForm = () => root.querySelector('[data-admin-form="legal"]');
    async function load() {
      const id = ++serial;
      const result = await (route.extra ? (creating ? Promise.resolve({status:'ready', document:null}) : service.detail(documentId)) : service.byType(state.type));
      if(life.signal.aborted || id !== serial) return;
      state = result.status !== 'ready' ? {...state, status:'error'} : route.extra ? {...state, status:'ready', document:result.document} : {...state, status:'ready', data:result};
      paint();
      if(route.extra && state.status === 'ready' && state.document?.state !== 'publicada') startAutosave();
    }
    const fields = form => ({version:form.elements.version.value.trim(), title:form.elements.title.value.trim(), content:form.elements.content.value});
    async function persist(values) {
      const result = await (creating ? service.create({type:newType, ...values}) : service.edit(documentId, {expectedAt:state.document.updatedAt, ...values}));
      if(!life.signal.aborted && result.status === 'accepted') { state = {...state, document:result.document}; lastSaved = JSON.stringify(values); }
      return result;
    }
    async function save(form) {
      const result = await persist(fields(form));
      if(life.signal.aborted) return null;
      if(result.status !== 'accepted') { fail(result); return null; }
      if(creating) { location.hash = `#admin/legales/${result.document.id}`; return result.document; }
      LegalAdminViews.showPreview(root, result.document.html);
      return result.document;
    }

    function startAutosave() {
      clearInterval(autosave);
      lastSaved = JSON.stringify(fields(editorForm()));
      autosave = setInterval(autosaveOnce, AUTOSAVE_MS);
    }
    async function autosaveOnce() {
      const form = editorForm();
      if(working || !form) return;
      const values = fields(form);
      if(JSON.stringify(values) === lastSaved || !service.VERSION.test(values.version) || !values.title || !values.content.trim()) return;
      working = true;
      try {
        const wasCreating = creating, result = await persist(values);
        if(life.signal.aborted) return;
        if(result.status !== 'accepted') {
          if(result.code === 'stale-record') { clearInterval(autosave); fail(result); } else LegalAdminViews.saved(root, null);
          return;
        }
        // Un borrador nuevo ya existe: la dirección cambia sin volver a montar el editor, para no perder el cursor.
        if(wasCreating) { creating = false; documentId = result.document.id; history.replaceState(null, '', `#admin/legales/${documentId}`); }
        LegalAdminViews.saved(root, new Date());
        LegalAdminViews.showPreview(root, result.document.html);
      } finally { working = false; }
    }

    async function importDocx(file) {
      const problem = service.fileProblem(file);
      if(problem) { fail({code:problem}); return; }
      if(editorForm().elements.content.value.trim() && !await confirmar(LegalAdminViews.confirmations.replace)) return;
      const result = await service.importDocx(file);
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { fail(result); return; }
      LegalAdminViews.replaceContent(root, result.html);
      LegalAdminViews.showPreview(root, result.html);
      mostrarAviso('exito', 'Documento convertido. Revisa la vista previa antes de guardar.');
    }
    async function paste(area, html) {
      const start = area.selectionStart, end = area.selectionEnd;
      const result = await service.sanitize(html);
      if(life.signal.aborted) return;
      if(result.status === 'ready') LegalAdminViews.insertText(root, result.html, start, end); else fail(result);
    }
    async function previewOf(id) {
      const result = await service.detail(id);
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { fail(result); return; }
      AdminTableViews.open(root, LegalAdminViews.previewDialog(result.document.html));
    }
    async function publish(id, expectedAt, type, version) {
      if(!await confirmar(LegalAdminViews.confirmations.publish(type, version))) return false;
      const result = await service.publish(id, expectedAt);
      if(life.signal.aborted) return false;
      if(result.status !== 'accepted') { fail(result); return false; }
      mostrarAviso('exito', `Versión ${version} publicada. Se avisó a ${result.notified} cuentas.`);
      if(type === 'politica_cookies') CookieController.refresh();
      return true;
    }
    async function publishFromEditor(form) {
      const type = state.document.type, version = form.elements.version.value.trim();
      if(!await confirmar(LegalAdminViews.confirmations.publish(type, version))) return;
      const saved = await save(form);
      if(!saved) return;
      const result = await service.publish(saved.id, saved.updatedAt);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      mostrarAviso('exito', `Versión ${version} publicada. Se avisó a ${result.notified} cuentas.`);
      if(type === 'politica_cookies') CookieController.refresh();
      location.hash = '#admin/legales';
    }
    async function remove(id, expectedAt) {
      if(!await confirmar(LegalAdminViews.confirmations.remove)) return;
      const result = await service.remove(id, expectedAt);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      mostrarAviso('exito', 'Borrador eliminado.');
      await load();
    }
    async function previewEditor(form) {
      const result = await service.preview(form.elements.content.value);
      if(life.signal.aborted) return;
      if(result.status === 'ready') LegalAdminViews.showPreview(root, result.html); else fail(result);
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, tab, id, at, version} = trigger.dataset;
      working = true;
      try {
        if(action === 'tab') { state = {...state, type:tab}; await load(); }
        else if(action === 'preview') await previewOf(id);
        else if(action === 'publish' && await publish(id, at, state.type, version)) await load();
        else if(action === 'remove') await remove(id, at);
        else if(action === 'tag') LegalAdminViews.insertTag(root, trigger.dataset.tag);
        else if(action === 'upload') LegalAdminViews.chooseFile(root);
        else if(action === 'preview-editor') await previewEditor(root.querySelector('[data-admin-form="legal"]'));
        else if(action === 'publish-editor') await publishFromEditor(root.querySelector('[data-admin-form="legal"]'));
        else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      if(working || event.target.closest('[data-admin-form]')?.dataset.adminForm !== 'legal') return;
      working = true;
      try {
        const wasCreating = creating;
        if(await save(event.target) && !wasCreating) mostrarAviso('exito', 'Borrador guardado.');
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('change', async event => {
      const file = event.target.matches('[data-legal-file]') ? event.target.files[0] : null;
      if(!file || working) return;
      working = true;
      try { await importDocx(file); } finally { working = false; }
    }, {signal:life.signal});
    // Pegar desde Word: el HTML del portapapeles nunca entra tal cual; lo sanea el servidor. Sin HTML, el pegado es el normal.
    root.addEventListener('paste', async event => {
      const area = event.target.closest('[name=content]');
      if(!area || area.readOnly || !event.clipboardData?.types.includes('text/html')) return;
      event.preventDefault();
      if(working) return;
      working = true;
      try { await paste(area, event.clipboardData.getData('text/html')); } finally { working = false; }
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { serial++; clearInterval(autosave); life.abort(); }};
  }
  return {mount};
})();

// ── Consentimientos ──
// Bitácora de solo lectura con resumen y exportación, y padrón de cuentas. Cada vista guarda sus filtros al alternar;
// cambiar de vista o pulsar «Actualizar» vuelve a consultar al servidor, así una cuenta eliminada desaparece de inmediato.
// El nombre del rango rápido («hoy», «7»…) solo vive aquí: al servidor viajan desde/hasta, que es lo que su lista blanca acepta.
const ConsentController = (() => {
  function mount({root, service = ConsentService}) {
    const life = new AbortController();
    const emptyList = () => ({items:[], page:1, total:0});
    let state = {status:'loading', tab:'bitacora', summary:null, list:emptyList(), filters:{}, range:'todo', exportUrl:service.exportUrl({}), exportLimit:Infinity,
      accounts:{status:'loading', list:emptyList(), totals:{total:0, activas:0, inactivas:0}, filters:{estado:'todas'}, range:'todo'}};
    let datesLife = null, dates = null, serial = 0, working = false;
    function paint() {
      AdminTableViews.paint(root, ConsentViews.screen(state));
      datesLife?.abort(); dates = null;
      if(state.tab === 'bitacora' && state.status === 'ready') { datesLife = new AbortController(); dates = DateFilterViews.mount(root, datesLife.signal); }
    }
    // Bitácora: el resumen se pide la primera vez y cada vez que se pulsa «Actualizar».
    async function loadLog(page, fresh) {
      const id = ++serial;
      const [list, summary] = await Promise.all([service.list(state.filters, page), state.summary && !fresh ? Promise.resolve({status:'ready', ...state.summary}) : service.summary()]);
      if(life.signal.aborted || id !== serial) return;
      if(list.status !== 'ready' || summary.status !== 'ready') { state = {...state, status:'error'}; paint(); return; }
      state = {...state, status:'ready', summary, list:{items:list.items, page:list.page, total:list.total}, exportLimit:list.exportLimit, exportUrl:service.exportUrl(state.filters)};
      paint();
    }
    async function loadAccounts(page) {
      const id = ++serial;
      const result = await service.accounts(state.accounts.filters, page);
      if(life.signal.aborted || id !== serial) return;
      const accounts = result.status === 'ready'
        ? {...state.accounts, status:'ready', list:{items:result.items, page:result.page, total:result.total}, totals:result.totals}
        : {...state.accounts, status:'error'};
      state = {...state, accounts};
      paint();
    }
    const load = (page = 1, fresh = false) => state.tab === 'cuentas' ? loadAccounts(page) : loadLog(page, fresh);
    // Rango rápido de la vista abierta: fija desde/hasta y conserva los demás filtros.
    function quickRange(preset) {
      const {desde, hasta} = service.range(preset);
      if(state.tab === 'cuentas') state = {...state, accounts:{...state.accounts, range:preset, filters:{...state.accounts.filters, desde, hasta}}};
      else state = {...state, range:preset, filters:{...state.filters, desde, hasta}};
    }
    // Si las fechas escritas coinciden con un rango rápido, ese botón queda marcado; si no, ninguno.
    function rangeOf({desde = '', hasta = ''}) {
      return ['todo', 'hoy', '7', '30'].find(preset => { const range = service.range(preset); return range.desde === desde && range.hasta === hasta; }) || 'personalizado';
    }
    async function filter(form) {
      const invalid = dates?.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const values = Object.fromEntries(new FormData(form));
      state.filters = {documento:values.documento, decision:values.decision, desde:values.since.trim(), hasta:values.until.trim(), cuenta:values.cuenta.trim(), version:values.version.trim()};
      state.range = rangeOf(state.filters);
      await load(1);
    }
    async function clear() {
      if(state.tab === 'cuentas') state = {...state, accounts:{...state.accounts, filters:{estado:'todas'}, range:'todo'}};
      else state = {...state, filters:{}, range:'todo'};
      await load(1);
    }
    // La búsqueda de la bitácora admite 60 caracteres; un correo más largo se busca por su inicio (coincide igual).
    const byAccount = email => String(email || '').slice(0, 60);
    async function act(action, data) {
      // Al cambiar de vista se pinta en el acto (con lo último que se vio, o «Cargando») y luego se consulta de nuevo.
      if(action === 'tab') { if(['bitacora', 'cuentas'].includes(data.tab) && data.tab !== state.tab) { state = {...state, tab:data.tab}; paint(); await load(1, true); } }
      else if(action === 'refresh') await load(1, true);
      else if(action === 'page' || action === 'accounts-page') await load(Number(data.page));
      else if(action === 'quick-document') { state = {...state, filters:{...state.filters, documento:data.value}}; await load(1); }
      else if(action === 'quick-status') { state = {...state, accounts:{...state.accounts, filters:{...state.accounts.filters, estado:data.value}}}; await load(1); }
      else if(action === 'quick-range') { quickRange(data.value); await load(1); }
      else if(action === 'clear') await clear();
      else if(action === 'row') AdminTableViews.open(root, ConsentViews.detail(state.list.items.find(item => item.id === data.id)));
      else if(action === 'account-history') { AdminTableViews.dismiss(root); state = {...state, filters:{cuenta:byAccount(data.account)}, range:'todo'}; await load(1); }
      else if(action === 'account-consents') { state = {...state, tab:'bitacora', filters:{cuenta:byAccount(data.email)}, range:'todo'}; paint(); await load(1, true); }
      else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      else if(action === 'export') await exportCsv();
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working || trigger.disabled) return;
      working = true;
      try { await act(trigger.dataset.adminAction, trigger.dataset); } finally { working = false; }
    }, {signal:life.signal});
    // Exportar exige contraseña reciente (M-2): el modelo la pide y reintenta; aquí solo se guarda el archivo o se avisa.
    async function exportCsv() {
      const result = await service.download(state.filters);
      if(life.signal.aborted) return;
      if(result.status === 'ready') AdminTableViews.saveFile(result.blob, 'consentimientos.csv');
      else mostrarAviso('error', {'reauthentication-required':'Confirma tu contraseña para exportar.', 'rate-limited':'Demasiadas exportaciones seguidas. Espera un minuto.'}[result.code] || 'No se pudo exportar. Inténtalo de nuevo.');
    }
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-admin-form]')?.dataset.adminForm;
      if(working || !['consent-filter', 'accounts-filter'].includes(form)) return;
      working = true;
      try {
        if(form === 'consent-filter') await filter(event.target);
        else { state = {...state, accounts:{...state.accounts, filters:{...state.accounts.filters, busqueda:event.target.elements.busqueda.value.trim()}}}; await load(1); }
      } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {redraw() {}, dispose() { serial++; datesLife?.abort(); life.abort(); }};
  }
  return {mount};
})();

// ── Reautenticacion ──
// Acciones críticas del panel (M-2): cuando el servidor pide confirmar la contraseña, se pide aquí y se confirma con allauth.
const AdminReauthController = (() => {
  let installed = false;
  function install({http = AdminHTTP, mfa = MfaService, ask = pedirContrasena} = {}) {
    if(installed) return;
    installed = true;
    http.onReauthentication(async () => {
      const password = await ask();
      if(!password) return false;
      const result = await mfa.reauthenticate(password);
      if(result.status === 'ok') return true;
      mostrarAviso('error', 'La contraseña no es correcta. Inténtalo de nuevo.');
      return false;
    });
  }
  return {install};
})();

// ── Panel ──
const AppController = (() => {
  const BELL_MIN_MS = 5000;
  // Compartido entre montajes: varias cargas seguidas no repiten la consulta.
  let bellPending = false, bellAskedAt = 0;
  // Qué destinos ve esta sesión: decisión de coordinación (la autorización real sigue en el servidor).
  function navigation(route, session) {
    const isAdmin = route.screen==='admin' || session?.role==='admin';
    const account = AppModel.destinations.find(item=>item.id==='cuenta');
    const links = isAdmin ? [...AppModel.allowedAdmin(session), account] : AppModel.destinations.filter(item=>item.id!=='avisos');
    return {isAdmin, links, groups:isAdmin ? AppModel.adminMenu(session) : [], account};
  }
  // Preferencia de esta visita: no se guarda en el navegador ni en el servidor.
  function mount(route, {root, service = AppService, authService = AuthService, config = AuthConfig, review = false, onLogout} = {}) {
    if(authService.session?.role === 'admin') AdminReauthController.install();
    const view = AppViews.frame(root, route, navigation(route, authService.session));
    WelcomeController.offer(root,authService.session,() => personalize());
    const lifetime = new AbortController();
    let pageLifetime = new AbortController(), loadingTimer = null;
    const {page} = view;
    let adminPanel = null, userGarden = null, auth = null, privacy = null, security = null, gardens = null, filter = 'todos', noticePage = 1, data = null, sequence = 0, busy = false;
    async function request(action, payload = {}) {
      const controller = new AbortController();
      const abort = () => controller.abort();
      const scope = pageLifetime;
      scope.signal.addEventListener('abort', abort, {once:true});
      let timeout, rejectAbort;
      try {
        return await Promise.race([
          service.request(action, payload, {signal:controller.signal}),
          new Promise((_, reject) => {
            rejectAbort = () => reject(new DOMException('Cancelled', 'AbortError'));
            controller.signal.addEventListener('abort', rejectAbort, {once:true});
            timeout = setTimeout(abort, config.requestTimeoutMs);
          })
        ]);
      } catch { return {status:'error'}; }
      finally {
        clearTimeout(timeout);
        controller.signal.removeEventListener('abort', rejectAbort);
        scope.signal.removeEventListener('abort', abort);
      }
    }
    function draw() {
      const profileHost = view.draw(route.screen, data, filter, route.detail, AppModel.alias(authService.session));
      if(profileHost) ProfileController.mount(profileHost,data,{onSaved:showGreeting});
    }
    // El alias guardado se refleja en la pantalla actual sin cerrar sesión.
    function showGreeting(session) {
      view.greeting(session?.profile?.profile?.greeting);
    }
    function personalize() {
      if(userGarden) userGarden.redraw();
      else if(route.screen === 'avisos' && data) draw();
      else if(route.screen === 'cuenta' && !route.detail) load();
    }
    async function load() {
      const id = ++sequence;
      view.hideMessage();
      clearTimeout(loadingTimer);
      view.pageBusy(false);
      if(route.screen==='admin') {
        const screens = {flota:() => FleetController.mount({root:page}), soporte:() => ConsoleController.mount({root:page,route}), mantenimientos:() => MaintenanceController.mount({root:page}), solicitudes:() => InquiryController.mount({root:page}), guias:() => CareGuideAdminController.mount({root:page}),
          equipos:() => EquipmentController.mount({root:page,route}), ventas:() => SalesController.mount({root:page}), legales:() => LegalAdminController.mount({root:page,route}),
          consentimientos:() => ConsentController.mount({root:page}), administradores:() => AdminAccessController.mount({root:page})};
        adminPanel = screens[route.detail]();
        return;
      }
      if(route.screen==='huerto') {
        userGarden = GardenController.mount({root:page,route});
        return;
      }
      if(['telemetria','mantenimiento','soporte'].includes(route.screen)) {
        userGarden = GardenSectionController.mount(route.screen,{root:page,route});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'huertos') {
        gardens = MyGardensController.mount({root:page});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'seguridad') {
        security?.dispose();
        if(route.invalidSecurity) { view.securityUnavailable(); return; }
        security = MfaController.mount({root:page});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'privacidad') {
        privacy?.dispose();
        privacy = PrivacyController.mount({root:page,onDeletion:accountDeleted});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'contrasena') {
        auth = AuthController.mount('cambiar', {root:page, service:authService, config, embedded:true, review});
        return;
      }
      data = {status:'loading', items:[]};
      view.pageBusy(true);
      // Si la respuesta es rápida se reemplaza el contenido directamente; si tarda, se muestra el estado de carga.
      if(view.isEmpty()) draw();
      else loadingTimer = setTimeout(() => { if(id === sequence && !lifetime.signal.aborted) draw(); }, 200);
      noticePage = 1;
      const response = await request(route.screen === 'avisos' ? (route.detail ? 'notice' : 'notices') : 'profile', route.detail ? {id:route.detail} : {filter, page:1});
      if(lifetime.signal.aborted || id !== sequence) return;
      clearTimeout(loadingTimer);
      view.pageBusy(false);
      data = route.screen === 'avisos' ? response : AppModel.profile(response);
      draw();
      if(route.screen === 'avisos' && route.detail && data.status === 'ready' && !data.item.read) { await request('mark-read', {id:route.detail}); refreshBell(true); }
    }
    // Contador de la campana (3.4): una vez al cargar cada pantalla y cada 60 s en segundo plano.
    // Tras leer avisos se fuerza, porque el número cambió.
    async function refreshBell(forced = false) {
      if(!forced && (bellPending || Date.now() - bellAskedAt < BELL_MIN_MS)) return;
      bellPending = true;
      bellAskedAt = Date.now();
      let response;
      try { response = await request('counter'); } finally { bellPending = false; }
      if(!lifetime.signal.aborted && response.status === 'ready') view.bell(response.unread);
    }
    async function openNotice(row) {
      const {noticeOpen: noticeId, noticeLink: link} = row.dataset;
      busy = true;
      await request('mark-read', {id:noticeId});
      busy = false;
      if(lifetime.signal.aborted) return;
      refreshBell(true);
      location.hash = link || `#avisos/${noticeId}`;
    }
    async function markAllRead() {
      busy = true;
      const response = await request('mark-all-read');
      busy = false;
      if(lifetime.signal.aborted) return;
      if(response.status !== 'accepted') { mostrarAviso('error', 'No se pudieron marcar los avisos como leídos.'); return; }
      mostrarAviso('exito', 'Avisos marcados como leídos.');
      await load();
      refreshBell(true);
    }
    async function loadMore() {
      busy = true;
      const response = await request('notices', {filter, page:noticePage + 1});
      busy = false;
      if(lifetime.signal.aborted) return;
      if(!['ready', 'empty'].includes(response.status)) { mostrarAviso('error', 'No se pudieron cargar más avisos.'); return; }
      noticePage += 1;
      data = {...data, items:[...data.items, ...response.items], total:response.total};
      draw();
    }
    async function resolveNotice() {
      busy = true;
      const response = await request('mark-resolved', {id:route.detail});
      busy = false;
      if(lifetime.signal.aborted) return;
      if(response.status !== 'accepted') { mostrarAviso('error', 'No se pudo marcar el aviso como resuelto.'); return; }
      data = {status:'ready', item:response.item};
      draw();
      mostrarAviso('exito', 'Aviso marcado como resuelto.');
    }
    // La cuenta ya no existe y el servidor cerró la sesión: se olvida aquí también y se vuelve al inicio público.
    function accountDeleted() {
      authService.sessionEnded();
      CookieController.refresh();
      location.hash = '#inicio';
    }
    async function logout() {
      if(busy || !await confirmar(AppViews.confirmaciones.cerrarSesion)) return;
      const id = sequence;
      busy = true;
      const response = await request('logout');
      if(lifetime.signal.aborted || id !== sequence) return;
      busy = false;
      if(response.status === 'accepted') { onLogout?.(); return; }
      view.logoutFailed();
    }
    function releasePage() {
      sequence++;
      clearTimeout(loadingTimer);
      pageLifetime.abort();
      pageLifetime = new AbortController();
      adminPanel?.dispose(); adminPanel=null;
      userGarden?.dispose(); userGarden = null;
      auth?.dispose(); auth = null;
      privacy?.dispose(); privacy = null;
      security?.dispose(); security = null;
      gardens?.dispose(); gardens = null;
      busy = false;
    }
    function update(nextRoute) {
      setMenuOpen(false);
      releasePage();
      route = nextRoute;
      filter = 'todos';
      view.markCurrent('#' + (route.screen==='admin'?'admin/'+route.detail:route.screen));
      load();
      refreshBell();
    }
    root.addEventListener('click', async event => {
      const row = event.target.closest('[data-notice-open]');
      if(row && !busy) { event.preventDefault(); await openNotice(row); return; }
      const target = event.target.closest('[data-filter],[data-app-action]');
      if(!target || busy) return;
      if(target.dataset.filter) {
        filter = target.dataset.filter;
        await load();
        view.focusFilter(filter);
        return;
      }
      const action = target.dataset.appAction;
      if(action === 'toggle-menu') { setMenuOpen(!menuOpen); return; }
      if(action === 'close-menu') { setMenuOpen(false,true); return; }
      if(action === 'reload') { await load(); if(!lifetime.signal.aborted) view.focusMain(); return; }
      if(action === 'logout') { await logout(); return; }
      if(action === 'more') { await loadMore(); return; }
      if(action === 'mark-all-read') { await markAllRead(); return; }
      if(action === 'mark-resolved') await resolveNotice();
    }, {signal:lifetime.signal});
    const nav = view.sidebar, toggle = view.toggle;
    const mobileScreen=matchMedia('(max-width:1024px)');
    let menuOpen=false;
    const isUserMobile=()=>Boolean(toggle)&&mobileScreen.matches;
    // El panel está siempre visible en escritorio; en móvil manda el menú desplegable.
    function setMenuOpen(open,returnFocus=false) {
      menuOpen=Boolean(open&&isUserMobile());
      view.menu(menuOpen);
      view.sidebarHidden(isUserMobile()&&!menuOpen);
      if(returnFocus&&isUserMobile())view.focusToggle();
    }
    function syncMenuMode() {
      const wasInNav=nav.contains(document.activeElement);
      const wasOnToggle=document.activeElement===toggle;
      setMenuOpen(false,isUserMobile()&&wasInNav);
      if(!isUserMobile()&&wasOnToggle)view.focusCurrentLink();
    }
    nav.addEventListener('click',event=>{
      const link=event.target.closest('a');if(!link||!isUserMobile())return;
      setMenuOpen(false);
      if(link.getAttribute('href')===location.hash)view.focusMain({preventScroll:true});
    },{signal:lifetime.signal});
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&menuOpen&&!document.querySelector('dialog[open]')){event.preventDefault();setMenuOpen(false,true);}
    },{signal:lifetime.signal});
    document.addEventListener('click',event=>{
      if(menuOpen&&!event.target.closest('dialog')&&!nav.contains(event.target)&&!toggle.contains(event.target)&&!document.querySelector('dialog[open]'))setMenuOpen(false);
    },{signal:lifetime.signal});
    document.addEventListener('focusin',event=>{
      if(menuOpen&&!event.target.closest('dialog')&&!nav.contains(event.target)&&!toggle.contains(event.target)&&!document.querySelector('dialog[open]'))setMenuOpen(false);
    },{signal:lifetime.signal});
    mobileScreen.addEventListener('change',syncMenuMode,{signal:lifetime.signal});
    syncMenuMode();
    const keepFieldVisible = () => view.keepVisible(document.activeElement);
    root.addEventListener('focusin', keepFieldVisible, {signal:lifetime.signal});
    window.visualViewport?.addEventListener('resize', keepFieldVisible);
    load();
    refreshBell();
    const bellTimer = setInterval(() => { if(!document.hidden) refreshBell(); }, 60000);
    return {update, dispose() {
      clearInterval(bellTimer);
      setMenuOpen(false);
      view.sidebarHidden(false);
      releasePage();
      pageLifetime.abort();
      lifetime.abort();
      window.visualViewport?.removeEventListener('resize', keepFieldVisible);
    }};
  }
  return {mount};
})();

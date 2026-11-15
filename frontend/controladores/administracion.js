// CONTROLADOR · Administración: paneles de operación, consultas, ventas, administradores, textos legales, consentimientos y el panel general.
// Define: AdminController, InquiryController, SalesController, AdminAccessController, LegalAdminController, ConsentController, AppController.

// ── Administracion ──
const AdminController = (() => {
  function mount(screen,{root,service=AdminService}={}) {
    const life=new AbortController();
    let selected=null, data={status:'loading'}, disposed=false,working=false,serial=0;
    const feedback=(message,error=false)=>AdminViews.feedback(root,message,error);
    const errorText=AdminViews.errorText;
    // Punto de acceso por capacidades: lo decide el controlador; la vista recibe el resultado.
    function access() {
      const allowed=AppModel.allowedAdmin();
      return {records:allowed.some(item=>item.id==='admin/mantenimientos'),inbox:allowed.some(item=>item.id==='admin/solicitudes')};
    }
    const render=()=>AdminViews.paint(root,screen,data,access());
    async function load({message='',error=false,focusDetail=false}={}) {
      if(disposed)return;
      const id=++serial;
      try {data=await service.snapshot(selected,screen);}catch {data={status:'error'};}
      if(disposed||id!==serial)return;
      render();
      if(focusDetail)AdminViews.focusDetail(root);
      if(message)feedback(message,error);
    }
    async function result(response,message) {
      await load({message:response.status==='accepted'?message:errorText(response.status),error:response.status!=='accepted'});
    }
    root.addEventListener('click',async event=>{
      const trigger=event.target.closest('[data-admin-action]');if(!trigger||working)return;
      const action=trigger.dataset.adminAction;
      if(action==='refresh'){await load({message:'Consulta actualizada.'});return;}
      if(action==='open-ticket'){
        working=true;let response;try{response=await service.selectTicket(trigger.dataset.ticket);}finally{working=false;}
        if(disposed)return;
        if(response.status!=='accepted'){feedback(errorText(response.status),true);return;}
        selected=trigger.dataset.ticket;await load({focusDetail:true});return;
      }
      if(action==='request-token'){
        const response=await service.requestToken(selected);
        await result(response,response.repeated?'Ya se pidió el token de este caso hace menos de 10 minutos. No se envió otro aviso.':'Solicitud registrada. Se avisará a la persona usuaria por correo, sin el token; el estado del aviso aparece en el detalle.');return;
      }
      if(action==='close-remote'){await result(await service.closeRemote(),'Sesión técnica cerrada. Los registros vuelven a estar bloqueados.');return;}
      if(action==='refresh-diagnostics'){await result(await service.refreshDiagnostics(selected),'Consulta de diagnóstico registrada.');return;}
    },{signal:life.signal});
    root.addEventListener('submit',async event=>{
      const form=event.target;
      if(form.matches('[data-admin-resolve-form]')){
        event.preventDefault();
        const fields=new FormData(form);
        await result(await service.resolveCase(selected,String(fields.get('result')||''),String(fields.get('note')||'').trim()),'Caso resuelto. El permiso quedó revocado y el acceso técnico cerrado.');
        return;
      }
      if(!form.matches('[data-admin-token-form]'))return;
      event.preventDefault();if(working||!form.reportValidity())return;
      const fields=Object.fromEntries(new FormData(form));
      await result(await service.validateToken(selected,fields.token),'Token válido para este reporte. El diagnóstico autorizado está disponible.');
    },{signal:life.signal});
    const checkExpiry=()=>{
      if(disposed||!data.remote||data.remote.expiresAt>Date.now())return;
      service.closeRemote();data.remote=null;data.diagnostics=null;
      render();feedback('La autorización ha vencido. El acceso técnico se cerró.');
    };
    const timer=setInterval(checkExpiry,1000);
    document.addEventListener('visibilitychange',checkExpiry,{signal:life.signal});
    render();load();
    return {dispose(){disposed=true;serial++;clearInterval(timer);if(screen==='soporte')service.closeRemote();life.abort();}};
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
      if(!life.signal.aborted && !busy && result.status === 'ready' && signature(result) !== shown) await load();
    }
    async function load() {
      view.loading();
      const result = await service.list(state, page);
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
// Textos legales: lista por tipo y editor. El HTML que se muestra lo devuelve el servidor ya saneado.
const LegalAdminController = (() => {
  const NEW_PREFIX = 'nuevo-';
  function mount({root, route, service = LegalAdminService}) {
    const life = new AbortController();
    const creating = route.extra?.startsWith(NEW_PREFIX), documentId = creating ? '' : route.extra || '';
    const newType = creating && service.TYPES.includes(route.extra.slice(NEW_PREFIX.length)) ? route.extra.slice(NEW_PREFIX.length) : 'terminos';
    let state = {status:'loading', type:'terminos', data:null, document:null, preview:null};
    let serial = 0, working = false;
    const paint = () => AdminTableViews.paint(root, route.extra ? LegalAdminViews.editorScreen({...state, type:newType}) : LegalAdminViews.listScreen(state));
    const fail = result => mostrarAviso('error', LegalAdminViews.errorText(result.code));
    async function load() {
      const id = ++serial;
      const result = await (route.extra ? (creating ? Promise.resolve({status:'ready', document:null}) : service.detail(documentId)) : service.byType(state.type));
      if(life.signal.aborted || id !== serial) return;
      state = result.status !== 'ready' ? {...state, status:'error'} : route.extra ? {...state, status:'ready', document:result.document} : {...state, status:'ready', data:result};
      paint();
    }
    const fields = form => ({version:form.elements.version.value.trim(), title:form.elements.title.value.trim(), content:form.elements.content.value});
    async function save(form) {
      const values = fields(form);
      const result = await (creating ? service.create({type:newType, ...values}) : service.edit(documentId, {expectedAt:state.document.updatedAt, ...values}));
      if(life.signal.aborted) return null;
      if(result.status !== 'accepted') { fail(result); return null; }
      if(creating) { location.hash = `#admin/legales/${result.document.id}`; return result.document; }
      state = {...state, document:result.document};
      LegalAdminViews.showPreview(root, result.document.html);
      return result.document;
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
        if(await save(event.target) && !creating) mostrarAviso('exito', 'Borrador guardado.');
      } finally { working = false; }
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { serial++; life.abort(); }};
  }
  return {mount};
})();

// ── Consentimientos ──
// Bitácora de solo lectura con resumen y exportación. La exportación es una descarga del navegador, no una llamada de aquí.
const ConsentController = (() => {
  function mount({root, service = ConsentService}) {
    const life = new AbortController();
    let state = {status:'loading', summary:null, list:{items:[], page:1, total:0}, filters:{}, exportUrl:service.exportUrl({}), exportLimit:Infinity};
    let datesLife = null, dates = null, serial = 0, working = false;
    function paint() {
      AdminTableViews.paint(root, ConsentViews.screen(state));
      datesLife?.abort();
      if(state.status === 'ready') { datesLife = new AbortController(); dates = DateFilterViews.mount(root, datesLife.signal); }
    }
    async function load(page = 1) {
      const id = ++serial;
      const [list, summary] = await Promise.all([service.list(state.filters, page), state.summary ? Promise.resolve({status:'ready', ...state.summary}) : service.summary()]);
      if(life.signal.aborted || id !== serial) return;
      if(list.status !== 'ready' || summary.status !== 'ready') { state = {...state, status:'error'}; paint(); return; }
      state = {...state, status:'ready', summary, list:{items:list.items, page:list.page, total:list.total}, exportLimit:list.exportLimit, exportUrl:service.exportUrl(state.filters)};
      paint();
    }
    async function filter(form) {
      const invalid = dates.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const values = Object.fromEntries(new FormData(form));
      state.filters = {documento:values.documento, decision:values.decision, desde:values.since, hasta:values.until, cuenta:values.cuenta.trim(), version:values.version.trim()};
      await load(1);
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page, id, account} = trigger.dataset;
      working = true;
      try {
        if(action === 'page') await load(Number(page));
        else if(action === 'clear') { state.filters = {}; ConsentViews.resetFilters(root); await load(1); }
        else if(action === 'row') AdminTableViews.open(root, ConsentViews.detail(state.list.items.find(item => item.id === id)));
        else if(action === 'account-history') { AdminTableViews.dismiss(root); state.filters = {cuenta:account}; await load(1); }
        else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      if(working || event.target.closest('[data-admin-form]')?.dataset.adminForm !== 'consent-filter') return;
      working = true;
      try { await filter(event.target); } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {redraw() {}, dispose() { serial++; datesLife?.abort(); life.abort(); }};
  }
  return {mount};
})();

// ── Panel ──
const AppController = (() => {
  // Qué destinos ve esta sesión: decisión de coordinación (la autorización real sigue en el servidor).
  function navigation(route, session) {
    const isAdmin = route.screen==='admin' || session?.role==='admin';
    const account = AppModel.destinations.find(item=>item.id==='cuenta');
    const links = isAdmin ? [...AppModel.allowedAdmin(session), account] : AppModel.destinations.filter(item=>item.id!=='avisos');
    return {isAdmin, links, groups:isAdmin ? AppModel.adminMenu(session) : [], account};
  }
  // Preferencia de esta visita: no se guarda en el navegador ni en el servidor.
  function mount(route, {root, service = AppService, authService = AuthService, config = AuthConfig, review = false, onLogout} = {}) {
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
        const screens = {mantenimientos:() => MaintenanceController.mount({root:page}), solicitudes:() => InquiryController.mount({root:page}), guias:() => CareGuideAdminController.mount({root:page}),
          equipos:() => EquipmentController.mount({root:page,route}), ventas:() => SalesController.mount({root:page}), legales:() => LegalAdminController.mount({root:page,route}),
          consentimientos:() => ConsentController.mount({root:page}), administradores:() => AdminAccessController.mount({root:page})};
        adminPanel = (screens[route.detail] || (() => AdminController.mount(route.detail,{root:page})))();
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
        privacy = PrivacyController.mount({root:page,onDeletion:refreshDeletion});
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
      if(route.screen === 'avisos' && route.detail && data.status === 'ready' && !data.item.read) { await request('mark-read', {id:route.detail}); refreshBell(); }
    }
    // Contador de la campana (3.4): al cargar cada pantalla y cada 60 s en segundo plano.
    async function refreshBell() {
      const response = await request('counter');
      if(!lifetime.signal.aborted && response.status === 'ready') view.bell(response.unread);
    }
    async function openNotice(row) {
      const {noticeOpen: noticeId, noticeLink: link} = row.dataset;
      busy = true;
      await request('mark-read', {id:noticeId});
      busy = false;
      if(lifetime.signal.aborted) return;
      refreshBell();
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
      refreshBell();
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
    // Aviso fijo de eliminación pendiente (4.9): sale de la sesión y se vuelve a leer tras cada cambio.
    const showDeletion = () => view.deletion(AppModel.deletionDate(authService.session));
    async function refreshDeletion() {
      await authService.restore();
      if(!lifetime.signal.aborted) showDeletion();
    }
    async function cancelDeletion() {
      if(!await confirmar(AppViews.confirmaciones.cancelarEliminacion)) return;
      const response = await request('cancel-deletion');
      if(lifetime.signal.aborted) return;
      if(response.status !== 'accepted') { mostrarAviso('error', 'No se pudo cancelar la eliminación. Inténtalo de nuevo.'); return; }
      await refreshDeletion();
      mostrarAviso('exito', 'Eliminación cancelada. Tu cuenta se conserva.');
      if(route.screen === 'cuenta' && route.detail === 'privacidad') await load();
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
      if(action === 'cancel-deletion') { await cancelDeletion(); return; }
      if(action === 'more') { await loadMore(); return; }
      if(action === 'mark-all-read') { await markAllRead(); return; }
      if(action === 'mark-resolved') await resolveNotice();
    }, {signal:lifetime.signal});
    const nav = view.sidebar, toggle = view.toggle;
    const mobileScreen=matchMedia('(max-width:768px)');
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
    showDeletion();
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

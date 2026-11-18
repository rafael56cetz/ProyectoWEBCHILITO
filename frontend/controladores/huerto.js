// CONTROLADOR · Huerto: Mi huerto y sus pantallas, panel técnico, mantenimiento y soporte, guías de cuidado y mantenimientos del operador.
// Define: GardenContext, GardenOrderCard, GardenSummaryController, GardenCreateController, GardenLinkController, PlantController, GardenController, MyGardensController, TechnicalController, CareController, SupportController, GardenSectionController, CareGuideUserController, CareGuideAdminController, MaintenanceController.

// ── Huerto ──
// Mi huerto y sus pantallas. El servidor confirma cada operación; aquí nunca se supone un éxito.
// Qué huerto se muestra: el de ?h=, si no el último elegido en la visita, si no el primero.
const GardenContext = Object.freeze({
  async resolve({service, route, signal}) {
    const list = await service.list(signal);
    if(list.status !== 'ready') return {ok:false};
    const garden = GardenModel.pick(list.items, route.gardenId);
    if(garden) GardenModel.remember(garden.id);
    return {ok:true, gardens:list.items, garden};
  }
});

const GardenOrderCard = (() => {
  const POLL_MS = 5000;
  const POLL_LIMIT_MS = 10 * 60 * 1000;
  // Pinta la tarjeta de la orden y la consulta cada 5 s, en segundo plano, hasta que el equipo responda o pasen 10 minutos.
  function track({root, order, service, signal, onResolved = () => {}}) {
    const started = Date.now();
    GardenViews.fillSlot(root, '[data-order-card]', GardenViews.orderCard(order));
    if(GardenModel.FINAL_ORDER_STATES.includes(order.state)) return {stop() {}};
    const timer = setInterval(async () => {
      if(Date.now() - started > POLL_LIMIT_MS) { clearInterval(timer); return; }
      const result = await service.orderState(order.id, signal);
      if(signal.aborted || result.status !== 'ready') return;
      GardenViews.fillSlot(root, '[data-order-card]', GardenViews.orderCard(result.command));
      if(!GardenModel.FINAL_ORDER_STATES.includes(result.command.state)) return;
      clearInterval(timer);
      mostrarAviso(result.command.state === 'confirmado' ? 'exito' : 'error', result.command.state === 'confirmado' ? 'Tu equipo confirmó la orden.' : 'Tu equipo no completó la orden.');
      onResolved(result.command);
    }, POLL_MS);
    return {stop() { clearInterval(timer); }};
  }
  return {track};
})();

const GardenSummaryController = (() => {
  const LOAD_TIMEOUT_MS = 20000;
  function mount({root, route, service}) {
    const life = new AbortController();
    let state = {status:'loading', gardens:[], detail:null}, tracker = null, working = false, serial = 0;
    const name = () => AppModel.alias(AuthService.session);
    const paint = () => GardenViews.paint(root, GardenViews.summary(state, name()));
    async function fetchState() {
      const request = new AbortController();
      const abort = () => request.abort();
      life.signal.addEventListener('abort', abort, {once:true});
      const timeout = setTimeout(abort, LOAD_TIMEOUT_MS);
      try {
        const context = await GardenContext.resolve({service, route, signal:request.signal});
        if(!context.ok) return {status:'error', gardens:[], detail:null};
        if(!context.garden) return {status:'ready', gardens:[], detail:null};
        const detail = await service.detail(context.garden.id, request.signal);
        if(detail.status !== 'ready') return {status:'error', gardens:[], detail:null};
        return {status:'ready', gardens:context.gardens, detail};
      } finally { clearTimeout(timeout); life.signal.removeEventListener('abort', abort); }
    }
    async function load() {
      const id = ++serial;
      tracker?.stop();
      state = {status:'loading', gardens:[], detail:null};
      paint();
      const next = await fetchState().catch(() => ({status:'error', gardens:[], detail:null}));
      if(life.signal.aborted || id !== serial) return;
      state = next;
      paint();
    }
    async function runOrder(values) {
      working = true;
      try {
        const result = await service.order(state.detail.garden.id, values);
        if(life.signal.aborted) return;
        if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
        tracker?.stop();
        tracker = GardenOrderCard.track({root, order:result.command, service, signal:life.signal, onResolved:refreshQuietly});
      } finally { working = false; }
    }
    // Tras una orden resuelta se vuelve a leer el huerto (p. ej. el estado de la lámpara) sin borrar la tarjeta.
    async function refreshQuietly(order) {
      const detail = await service.detail(state.detail.garden.id, life.signal);
      if(life.signal.aborted || detail.status !== 'ready') return;
      state = {...state, detail};
      paint();
      GardenViews.fillSlot(root, '[data-order-card]', GardenViews.orderCard(order));
    }
    async function confirmOrder(type) {
      if(await confirmar(GardenViews.confirmations[type])) await runOrder({type});
    }
    async function recordRefill() {
      const result = await service.care(state.detail.garden.id, {type:'rellenar_deposito'});
      mostrarAviso(result.status === 'accepted' ? 'exito' : 'error', result.status === 'accepted' ? 'Recarga registrada.' : GardenViews.errorText(result.code));
    }
    async function showSummaries() {
      const result = await service.summaries(state.detail.garden.id, 1);
      if(life.signal.aborted) return;
      if(result.status === 'ready') GardenViews.fillSlot(root, '[data-summaries]', GardenViews.summaryList(result.items));
      else mostrarAviso('error', GardenViews.errorText(result.code));
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger) return;
      const {gardenAction: action, type} = trigger.dataset;
      if(action === 'reload') await load();
      else if(action === 'summaries') await showSummaries();
      else if(action === 'refill') await recordRefill();
      else if(action === 'order' && !working) await runOrder({type});
      else if(action === 'order-confirm' && !working) await confirmOrder(type);
    }, {signal:life.signal});
    load();
    return {redraw() { if(state.status === 'ready') paint(); }, dispose() { serial++; tracker?.stop(); life.abort(); }};
  }
  return {mount};
})();

const GardenCreateController = (() => {
  function mount({root, service}) {
    const life = new AbortController();
    GardenViews.paint(root, GardenViews.newGarden());
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-garden-form="create"]');
      if(!form || form.dataset.busy) return;
      form.dataset.busy = 'true';
      const result = await service.create(form.elements.name.value.trim());
      delete form.dataset.busy;
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code, 'No se pudo crear el huerto. Revisa el nombre e inténtalo de nuevo.')); return; }
      GardenModel.remember(result.garden.id);
      location.hash = `#huerto/vincular?h=${result.garden.id}`;
    }, {signal:life.signal});
    return {redraw() {}, dispose() { life.abort(); }};
  }
  return {mount};
})();

const GardenLinkController = (() => {
  const POLL_MS = 5000;
  function mount({root, route, service}) {
    const life = new AbortController();
    let wizard = null, polling = null, ticking = null;
    const stop = () => { clearInterval(polling); clearInterval(ticking); polling = ticking = null; };
    const paint = () => GardenViews.paint(root, GardenViews.linkWizard(wizard));
    const secondsLeft = () => wizard.expiresAt ? GardenModel.remainingSeconds(wizard.expiresAt) : 0;
    function expire() {
      stop();
      wizard = {...wizard, code:null, expired:true, seconds:0};
      paint();
    }
    function linked(device) {
      stop();
      wizard = {...wizard, step:3, code:null, device};
      paint();
      mostrarAviso('exito', 'Tu equipo quedó vinculado.');
    }
    async function check() {
      const state = await service.linkState(wizard.garden.id, life.signal);
      if(life.signal.aborted || state.status !== 'ready') return;
      if(state.linked) linked(state.device);
      else if(['expirado', 'cancelado'].includes(state.codeState)) expire();
    }
    function startWaiting() {
      stop();
      ticking = setInterval(() => {
        const seconds = secondsLeft();
        if(seconds <= 0) { expire(); return; }
        GardenViews.countdown(root, seconds);
      }, 1000);
      polling = setInterval(check, POLL_MS);
    }
    async function generate() {
      const result = await service.generateCode(wizard.garden.id);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted' || !result.code) { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      wizard = {...wizard, step:2, code:result.code, expiresAt:result.expiresAt, expired:false, seconds:GardenModel.remainingSeconds(result.expiresAt)};
      paint();
      startWaiting();
    }
    async function copyCode() {
      try { await navigator.clipboard.writeText(wizard.code); mostrarAviso('exito', 'Código copiado.'); }
      catch { mostrarAviso('error', 'No se pudo copiar. Escríbelo a mano.'); }
    }
    async function start() {
      const {garden} = await GardenContext.resolve({service, route, signal:life.signal});
      if(life.signal.aborted) return;
      if(!garden) { location.hash = '#huerto'; return; }
      wizard = {garden, step:garden.device ? 3 : 1, code:null, expiresAt:null, seconds:0, expired:false, device:garden.device};
      paint();
    }
    root.addEventListener('click', event => {
      const action = event.target.closest('[data-garden-action]')?.dataset.gardenAction;
      if(action === 'generate') generate();
      else if(action === 'copy-code') copyCode();
    }, {signal:life.signal});
    start();
    return {redraw() {}, dispose() { stop(); life.abort(); }};
  }
  return {mount};
})();

const PlantController = (() => {
  function mount({root, route, service}) {
    const life = new AbortController();
    let gardenId = null, data = null, range = '24h', tracker = null;
    const paint = () => GardenViews.paint(root, GardenViews.plantPage({...data, garden:{id:gardenId}, range}));
    async function load() {
      if(!gardenId) {
        const {garden} = await GardenContext.resolve({service, route, signal:life.signal});
        if(life.signal.aborted) return;
        if(!garden) { location.hash = '#huerto'; return; }
        gardenId = garden.id;
      }
      const result = await service.plant(gardenId, route.extra, range);
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { GardenViews.paint(root, GardenViews.failed); return; }
      data = result;
      paint();
    }
    async function save(form) {
      const values = {name:form.elements.name.value.trim(), sowingDate:form.elements.sowingDate.value || null, stage:form.elements.stage.value};
      const result = await service.editPlant(gardenId, route.extra, values);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code, 'Revisa el nombre, la fecha y la etapa e inténtalo de nuevo.')); return; }
      GardenViews.closeDialog(root);
      mostrarAviso('exito', 'Planta actualizada.');
      await load();
    }
    async function water(form) {
      const result = await service.order(gardenId, {type:'regar', plant:Number(route.extra), duration:Number(form.elements.duration.value)});
      if(life.signal.aborted) return;
      GardenViews.closeDialog(root);
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      tracker?.stop();
      tracker = GardenOrderCard.track({root, order:result.command, service, signal:life.signal});
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger || !data) return;
      const dialogs = GardenViews.plantDialogs(data.plant, data.hasDevice);
      const action = trigger.dataset.gardenAction;
      if(action === 'range') { range = trigger.dataset.range; await load(); }
      else if(action === 'edit') GardenViews.openDialog(root, dialogs.edit);
      else if(action === 'water') GardenViews.openDialog(root, dialogs.water);
      else if(action === 'close-dialog') GardenViews.closeDialog(root);
    }, {signal:life.signal});
    root.addEventListener('submit', event => {
      event.preventDefault();
      const kind = event.target.closest('[data-garden-form]')?.dataset.gardenForm;
      if(kind === 'plant') save(event.target);
      else if(kind === 'water') water(event.target);
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { tracker?.stop(); life.abort(); }};
  }
  return {mount};
})();

const GardenController = (() => {
  function mount({root, route, service = GardenService}) {
    if(route.detail === 'nuevo') return GardenCreateController.mount({root, service});
    if(route.detail === 'vincular') return GardenLinkController.mount({root, route, service});
    if(route.detail === 'plantas') return PlantController.mount({root, route, service});
    return GardenSummaryController.mount({root, route, service});
  }
  return {mount};
})();

const MyGardensController = (() => {
  function mount({root, service = GardenService}) {
    const life = new AbortController();
    let state = {status:'loading', gardens:[]};
    const paint = () => GardenViews.paint(root, GardenViews.myGardens(state));
    async function load() {
      state = {status:'loading', gardens:[]};
      paint();
      const list = await service.list(life.signal);
      if(life.signal.aborted) return;
      state = list.status === 'ready' ? {status:'ready', gardens:list.items} : {status:'error', gardens:[]};
      paint();
    }
    async function finish(result, success) {
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      GardenViews.closeDialog(root);
      mostrarAviso('exito', success);
      await load();
    }
    async function unlink(garden) {
      const confirmation = GardenViews.confirmations.desvincular(garden.device.identifier);
      if(await confirmar(confirmation)) await finish(await service.unlink(garden.id), 'Equipo desvinculado.');
    }
    async function archive(garden) {
      if(await confirmar(GardenViews.confirmations.archivar(garden.name))) await finish(await service.archive(garden.id), 'Huerto archivado.');
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger) return;
      const garden = state.gardens.find(item => item.id === trigger.closest('[data-garden-id]')?.dataset.gardenId);
      const action = trigger.dataset.gardenAction;
      if(action === 'reload') await load();
      else if(action === 'close-dialog') GardenViews.closeDialog(root);
      else if(action === 'rename' && garden) GardenViews.openDialog(root, GardenViews.renameDialog(garden));
      else if(action === 'unlink' && garden) await unlink(garden);
      else if(action === 'archive' && garden) await archive(garden);
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-garden-form="rename"]');
      if(form) await finish(await service.rename(form.dataset.gardenId, form.elements.name.value.trim()), 'Nombre actualizado.');
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { life.abort(); }};
  }
  return {mount};
})();

// ── Operacion ──
// Panel técnico, Mantenimiento y Soporte del huerto elegido. El servidor confirma cada operación; aquí nunca se supone un éxito.
const TechnicalController = (() => {
  function mount({root, route, service}) {
    const life = new AbortController();
    let state = {status:'loading', gardens:[], garden:null, data:null, range:'24h', log:{type:'ordenes', status:'loading', items:[], page:1, total:0}};
    let tracker = null, serial = 0;
    const paint = () => GardenViews.paint(root, TechnicalViews.screen(state));
    const paintLog = () => GardenViews.fillSlot(root, '[data-log-panel]', TechnicalViews.logPanel(state.log));
    async function loadLog(type, page) {
      const result = await service.log(state.garden.id, type, page);
      if(life.signal.aborted) return;
      state.log = result.status === 'ready' ? {type, status:'ready', items:result.items, page:result.page, total:result.total} : {type, status:'error', items:[], page:1, total:0};
    }
    async function loadData() {
      const [telemetry] = await Promise.all([service.telemetry(state.garden.id, state.range, life.signal), loadLog(state.log.type, 1)]);
      if(life.signal.aborted) return false;
      if(telemetry.status !== 'ready') return false;
      state.data = telemetry;
      return true;
    }
    async function load() {
      const id = ++serial;
      state = {...state, status:'loading'};
      paint();
      const context = await GardenContext.resolve({service, route, signal:life.signal});
      if(life.signal.aborted || id !== serial) return;
      state = {...state, status:context.ok ? 'ready' : 'error', gardens:context.gardens || [], garden:context.garden || null};
      if(state.status === 'ready' && state.garden?.device && !await loadData()) state.status = 'error';
      if(life.signal.aborted || id !== serial) return;
      paint();
    }
    async function water(form) {
      const plant = Number(form.elements.plant.value), duration = Number(form.elements.duration.value);
      const name = state.data.plants.find(item => item.number === plant)?.name || `Planta ${plant}`;
      if(!await confirmar(TechnicalViews.waterConfirmation(name, duration))) return;
      const result = await service.order(state.garden.id, {type:'regar', plant, duration});
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      tracker?.stop();
      tracker = GardenOrderCard.track({root, order:result.command, service, signal:life.signal, onResolved:async () => { await loadLog(state.log.type, 1); paintLog(); }});
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger) return;
      const {gardenAction: action, range, log, page} = trigger.dataset;
      if(action === 'reload') await load();
      else if(action === 'range') { state.range = range; if(await loadData()) paint(); else mostrarAviso('error', 'No se pudo cargar el periodo.'); }
      else if(action === 'log-tab') { await loadLog(log, 1); paintLog(); }
      else if(action === 'log-page') { await loadLog(state.log.type, Number(page)); paintLog(); }
    }, {signal:life.signal});
    root.addEventListener('submit', event => {
      event.preventDefault();
      const form = event.target.closest('[data-garden-form="water"]');
      if(form) water(form);
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { serial++; tracker?.stop(); life.abort(); }};
  }
  return {mount};
})();

const CareController = (() => {
  function mount({root, route, service}) {
    const life = new AbortController();
    let state = {status:'loading', gardens:[], garden:null, plants:[]}, cares = {status:'loading', items:[], page:1, total:0}, filters = {}, dates = null, guides = null, serial = 0;
    async function loadCares(page = 1) {
      const result = await service.cares(state.garden.id, filters, page);
      if(life.signal.aborted) return;
      cares = result.status === 'ready' ? {status:'ready', items:result.items, page:result.page, total:result.total} : {status:'error', items:[], page:1, total:0};
      GardenViews.fillSlot(root, '[data-care-list]', CareViews.list(cares));
      // Fila de estado (solo lectura): se pinta con esta misma respuesta cuando es el historial sin filtros, página 1.
      if(cares.page === 1 && !Object.values(filters).some(Boolean)) GardenViews.fillSlot(root, '[data-care-status]', CareViews.status(cares, state.plants));
    }
    async function load() {
      const id = ++serial;
      state = {...state, status:'loading'};
      GardenViews.paint(root, CareViews.screen(state));
      const context = await GardenContext.resolve({service, route, signal:life.signal});
      const detail = context.garden ? await service.detail(context.garden.id, life.signal) : {status:'ready', plants:[]};
      if(life.signal.aborted || id !== serial) return;
      state = {status:context.ok && detail.status === 'ready' ? 'ready' : 'error', gardens:context.gardens || [], garden:context.garden || null, plants:detail.plants || []};
      GardenViews.paint(root, CareViews.screen(state));
      if(state.status !== 'ready' || !state.garden) return;
      dates = DateFilterViews.mount(root, life.signal);
      guides = CareGuideUserController.attach({root, signal:life.signal, screen:'mantenimiento', detail:route.detail});
      guides.paint(true);
      await loadCares(1);
    }
    async function register(values) {
      const result = await service.care(state.garden.id, values);
      if(life.signal.aborted) return false;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code, 'Revisa los datos del cuidado e inténtalo de nuevo.')); return false; }
      mostrarAviso('exito', 'Cuidado registrado.');
      await loadCares(1);
      return true;
    }
    async function submitCare(form) {
      const invalid = dates.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const type = form.elements.type.value, plant = form.elements.plant.value, chiles = form.elements.chiles.value;
      const moment = GardenModel.careMoment(form.elements.when.value.trim());
      if(!moment.valid) { mostrarAviso('error', 'Elige un día de hasta 7 días atrás, sin fechas futuras.'); return; }
      if(GardenModel.CARE_NEEDS_PLANT.includes(type) && !plant) { mostrarAviso('error', 'Elige en qué planta lo hiciste.'); return; }
      const values = {type, ...(plant ? {plant:Number(plant)} : {}), ...(type === 'cosecha' && chiles !== '' ? {chiles:Number(chiles)} : {}), ...(moment.at ? {doneAt:moment.at} : {})};
      if(await register(values)) CareViews.reset(root);
    }
    async function submitFilter(form) {
      const invalid = dates.validate();
      if(invalid) { mostrarAviso('error', invalid); return; }
      const values = Object.fromEntries(new FormData(form));
      filters = {planta:values.planta, tipo:values.tipo, desde:values.since, hasta:values.until};
      await loadCares(1);
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger) return;
      const {gardenAction: action, type, page} = trigger.dataset;
      if(action === 'reload') await load();
      else if(action === 'care-type') CareViews.pickType(root, type);
      else if(action === 'care-plant') CareViews.pickPlant(root, trigger.dataset.plant);
      else if(action === 'care-when') CareViews.pickWhen(root, trigger.dataset.when);
      else if(action === 'care-chiles') CareViews.stepChiles(root, trigger.dataset.step);
      else if(action === 'care-date') CareViews.openDate(root, trigger.dataset.date);
      else if(action === 'care-quick' && type === 'rellenar_deposito') await register({type});
      else if(action === 'care-quick') CareViews.prepare(root, type);
      else if(action === 'care-page') await loadCares(Number(page));
      else if(action === 'care-clear') { filters = {}; CareViews.resetFilters(root); await loadCares(1); }
    }, {signal:life.signal});
    root.addEventListener('submit', event => {
      event.preventDefault();
      const kind = event.target.closest('[data-garden-form]')?.dataset.gardenForm;
      if(kind === 'care') submitCare(event.target);
      else if(kind === 'care-filter') submitFilter(event.target);
    }, {signal:life.signal});
    root.addEventListener('change', event => {
      if(event.target.id === 'care-type') CareViews.adjust(root, event.target.value);
      else if(event.target.id === 'filter-period') CareViews.period(root, event.target.value);
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { serial++; life.abort(); }};
  }
  return {mount};
})();

const SupportController = (() => {
  const POLL_MS = 15000;
  const POLL_LIMIT_MS = 10 * 60 * 1000;
  function mount({root, route, service}) {
    const life = new AbortController();
    let state = {status:'loading', gardens:[], garden:null, data:null, diagnostic:null}, tracker = null, poller = null, serial = 0, working = false;
    const paint = () => GardenViews.paint(root, SupportViews.screen(state));
    // Con un caso activo se vuelve a consultar en segundo plano, hasta 10 minutos, para ver lo que soporte va haciendo.
    function watchCase() {
      clearInterval(poller);
      if(!state.data?.active) return;
      const started = Date.now();
      poller = setInterval(async () => {
        if(Date.now() - started > POLL_LIMIT_MS) { clearInterval(poller); return; }
        const result = await service.support(state.garden.id, {signal:life.signal, quiet:true});
        if(life.signal.aborted || result.status !== 'ready' || working) return;
        state.data = result;
        paint();
        if(!result.active) clearInterval(poller);
      }, POLL_MS);
    }
    async function load() {
      const id = ++serial;
      state = {...state, status:'loading'};
      paint();
      const context = await GardenContext.resolve({service, route, signal:life.signal});
      const data = context.garden ? await service.support(context.garden.id, {signal:life.signal}) : null;
      if(life.signal.aborted || id !== serial) return;
      const ready = context.ok && (!data || data.status === 'ready');
      state = {status:ready ? 'ready' : 'error', gardens:context.gardens || [], garden:context.garden || null, data, diagnostic:data?.lastDiagnostic || null};
      paint();
      watchCase();
    }
    async function showDiagnostic(command) {
      const result = command.diagnosticId ? await service.diagnostic(command.diagnosticId, life.signal) : {status:'error'};
      if(life.signal.aborted || result.status !== 'ready') return;
      state.diagnostic = result.diagnostic;
      GardenViews.fillSlot(root, '[data-diagnostic]', SupportViews.diagnosticCard(result.diagnostic));
    }
    async function diagnose() {
      const result = await service.order(state.garden.id, {type:'autodiagnostico'});
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      GardenViews.fillSlot(root, '[data-diagnostic]', SupportViews.diagnosticCard({state:'en_curso', startedAt:result.command.createdAt, checks:[]}));
      tracker?.stop();
      tracker = GardenOrderCard.track({root, order:result.command, service, signal:life.signal, onResolved:showDiagnostic});
    }
    async function openCase(form) {
      const values = {incident:form.elements.incident.value, consent:form.elements.consent.checked,
        ...(form.elements.note.value.trim() ? {note:form.elements.note.value.trim()} : {}),
        ...(form.elements.attach?.checked && state.diagnostic?.state === 'completado' ? {diagnostic:state.diagnostic.id} : {})};
      const result = await service.openCase(state.garden.id, values);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code, 'No se pudo enviar la solicitud. Revisa los datos e inténtalo de nuevo.')); return; }
      mostrarAviso('exito', 'Solicitud enviada. Soporte revisará tu equipo.');
      await load();
    }
    async function closeCase(kind, caseId) {
      if(!await confirmar(SupportViews.confirmations[kind])) return;
      const result = await (kind === 'revoke' ? service.revokeCase(caseId) : service.cancelCase(caseId));
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { mostrarAviso('error', GardenViews.errorText(result.code)); return; }
      mostrarAviso('exito', kind === 'revoke' ? 'Acceso revocado.' : 'Solicitud cancelada.');
      await load();
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-garden-action]');
      if(!trigger || working) return;
      const {gardenAction: action, case: caseId} = trigger.dataset;
      working = true;
      try {
        if(action === 'reload') await load();
        else if(action === 'diagnose') await diagnose();
        else if(action === 'revoke' || action === 'cancel-case') await closeCase(action === 'revoke' ? 'revoke' : 'cancel', caseId);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.target.closest('[data-garden-form="support"]');
      if(!form || working || !form.elements.consent.checked) return;
      working = true;
      try { await openCase(form); } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('input', event => {
      if(event.target.name === 'note') SupportViews.countNote(root, event.target.value.length);
    }, {signal:life.signal});
    root.addEventListener('change', event => {
      if(event.target.name === 'consent') SupportViews.consent(root, event.target.checked);
    }, {signal:life.signal});
    load();
    return {redraw() {}, dispose() { serial++; clearInterval(poller); tracker?.stop(); life.abort(); }};
  }
  return {mount};
})();

const GardenSectionController = (() => {
  const screens = {telemetria:TechnicalController, mantenimiento:CareController, soporte:SupportController};
  function mount(screen, {root, route, service = GardenService}) {
    return screens[screen].mount({root, route, service});
  }
  return {mount};
})();

// ── Guias ──
// Guías de cuidado: eventos y coordinación. El servidor confirma; aquí nunca se supone un éxito.
const CareGuideUserController = (() => {
  const LOAD_TIMEOUT_MS = 20000;
  const MISSING = 'Esa ficha ya no está publicada. Aquí tienes las guías disponibles.';
  // Devuelve paint: la pantalla de Mantenimiento se redibuja con cada carga del huerto.
  function attach({root, signal, screen, detail = '', service = CareGuideService}) {
    if(screen !== 'mantenimiento') return {paint() {}};
    const targets = new Map([['sustrato', service.SUBSTRATE_KEY], ['germinacion', service.GERMINATION_KEY], ['guias', null]]);
    const opened = new Set();
    let state = {status:'loading', items:[]}, serial = 0, settled = false;
    let pending = targets.has(detail) ? {key:targets.get(detail)} : null;
    const section = () => root.querySelector('[data-care-guides]');
    function reveal() {
      const node = section();
      if(!pending || !node || state.status === 'loading') return;
      const {key} = pending; pending = null;
      if(key && state.status === 'ready' && CareGuideViews.openItem(node, key)) { opened.add(key); return; }
      CareGuideViews.focusSection(node, key && state.status === 'ready' ? MISSING : '');
    }
    function paint(gardenSettled = settled) {
      settled = gardenSettled;
      const node = section();
      if(!node) return;
      CareGuideViews.paint(node, state, opened);
      if(settled) reveal();
    }
    async function load({focus = false} = {}) {
      const id = ++serial;
      // El foco se aplica cuando termine la carga y también la del huerto, que redibuja la pantalla.
      if(focus) pending = {key:null};
      state = {status:'loading', items:[]}; paint();
      const request = new AbortController(), abort = () => request.abort();
      signal.addEventListener('abort', abort, {once:true});
      const timeout = setTimeout(abort, LOAD_TIMEOUT_MS);
      const result = await service.published({signal:request.signal});
      clearTimeout(timeout); signal.removeEventListener('abort', abort);
      if(signal.aborted || id !== serial) return;
      state = result.status === 'ready' ? {status:'ready', items:result.items} : {status:'error', items:[]};
      paint();
    }
    root.addEventListener('toggle', event => {
      const key = event.target.dataset?.guideKey;
      if(key) { if(event.target.open) opened.add(key); else opened.delete(key); }
    }, {signal, capture:true});
    root.addEventListener('click', event => {
      if(event.target.closest('[data-care-guide-retry]')) { load({focus:true}); return; }
      const link = event.target.closest('[data-care-guide-link]');
      if(!link) return;
      // Ya en esta pantalla: se abre directamente, también si la ruta no cambia.
      event.preventDefault();
      pending = {key:link.dataset.careGuideLink};
      reveal();
    }, {signal});
    load();
    return {paint};
  }
  return Object.freeze({attach});
})();

const CareGuideAdminController = (() => {
  const failures = {
    forbidden:'Tu cuenta no tiene la capacidad para gestionar guías.',
    mfa:'Activa tu app autenticadora o una llave de acceso para gestionar guías.',
    limited:'Demasiadas operaciones seguidas. Espera un momento.',
    invalid:'Revisa los datos: alguna longitud, número o enlace no es válido.',
    conflict:'No se pudo guardar por un conflicto. Inténtalo de nuevo.'};
  const UNCERTAIN = 'No pudimos confirmar el resultado. Vuelve a intentarlo sin cambiar nada: no se duplicará.';
  const STALE_LIST = 'Otra persona cambió esa ficha. Se actualizó la lista: revísala antes de repetir la acción.';
  const STALE_FORM = 'Otra persona cambió esta ficha mientras la editabas. No se guardó nada y tu texto sigue aquí. Cópialo si lo necesitas y carga la versión actual.';
  const DIRTY = 'Tienes cambios sin guardar en el formulario. Guárdalos o pulsa Cancelar antes de continuar.';
  const uncertain = status => status === 'network' || status === 'error';
  function mount({root, service = CareGuideService} = {}) {
    const life = new AbortController();
    // Excepción MVC documentada (frontend/pruebas/pruebas.cjs, suite MVC): plantilla fija; la vista de guías tiene prohibido innerHTML.
    root.innerHTML = CareGuideViews.adminShell(service.LIMITS);
    const {editor, form, list, summary, feedback} = CareGuideViews.mountAdmin(root);
    let guides = [], filter = '', editing = null, dirty = false, busy = false;   // editing: null cerrado, {} nueva, o la ficha
    const say = (text, error = false) => CareGuideViews.adminFeedback(feedback, text, error);
    const failureText = (status, fallback) => uncertain(status) ? UNCERTAIN : failures[status] || fallback;
    const findGuide = id => guides.find(guide => guide.id === id);
    const editingState = () => editing?.state || 'nueva';
    function open(guide) {
      editing = guide || {}; dirty = false;
      CareGuideViews.fillEditor(editor, guide, service.editorTexts[editingState()]);
      CareGuideViews.focusEditor(editor);
    }
    function close() { editing = null; dirty = false; CareGuideViews.closeEditor(editor); }
    function paintList() {
      CareGuideViews.setFilter(root, filter);
      CareGuideViews.adminList(list, summary, filter ? guides.filter(guide => guide.state === filter) : guides, service, filter);
    }
    async function load() {
      CareGuideViews.adminLoading(summary);
      const result = await service.panel();
      if(life.signal.aborted) return false;
      if(result.status !== 'ready') { CareGuideViews.adminError(list, summary, failures[result.status] || 'No se pudieron consultar las fichas.'); return false; }
      guides = result.guides;
      paintList();
      // Sin cambios propios, el formulario sigue a la versión más reciente de la ficha.
      if(editing?.id && !dirty) { const fresh = findGuide(editing.id); if(fresh) { editing = fresh; CareGuideViews.fillEditor(editor, fresh, service.editorTexts[fresh.state]); } }
      return true;
    }
    async function save() {
      const values = CareGuideViews.readEditor(editor);
      const problem = service.check(values);
      if(problem) { CareGuideViews.markInvalid(form, problem.field); CareGuideViews.formStatus(editor, problem.message, {error:true, focus:false}); return; }
      CareGuideViews.markInvalid(form, null);
      busy = true; CareGuideViews.saving(editor, true);
      CareGuideViews.formStatus(editor, 'Guardando…');
      const wasState = editingState();
      const result = editing.id ? await service.update(editing.id, editing.version, values) : await service.create(values);
      busy = false; if(life.signal.aborted) return;
      CareGuideViews.saving(editor, false);
      if(result.status === 'accepted') {
        close();
        await load();
        say(wasState === 'publicada' ? 'Cambios guardados y visibles para las personas usuarias.' : wasState === 'retirada' ? 'Cambios guardados. La ficha sigue retirada.' : 'Borrador guardado. Todavía no es visible para las personas usuarias.');
        return;
      }
      if(result.status === 'stale') {
        CareGuideViews.staleOption(editor, true);
        CareGuideViews.formStatus(editor, STALE_FORM, {error:true});
        await load();
        return;
      }
      CareGuideViews.formStatus(editor, failureText(result.status, 'No se pudo guardar la ficha.'), {error:true});
    }
    async function changeState(action, guideId, done, fallback) {
      const guide = findGuide(guideId);
      if(!guide || busy) return;
      if(dirty) { say(DIRTY, true); return; }
      busy = true;
      CareGuideViews.adminApplying(list, summary);
      const result = await action(guide.id, guide.version);
      busy = false; if(life.signal.aborted) return;
      await load();
      if(result.status === 'accepted') say(done);
      else say(result.status === 'stale' ? STALE_LIST : failureText(result.status, fallback), true);
    }
    async function confirmedChange(kind, action, guideId, done, fallback) {
      if(busy) return;
      if(dirty) { say(DIRTY, true); return; }
      if(!await confirmar(CareGuideViews.confirmations[kind])) return;
      await changeState(action, guideId, done, fallback);
    }
    root.addEventListener('click', event => {
      const target = event.target;
      const filterButton = target.closest('[data-guide-filter]');
      if(filterButton) { filter = filterButton.dataset.guideFilter; paintList(); return; }
      if(target.closest('[data-guide-retry]')) { load(); return; }
      if(target.closest('[data-guide-cancel]')) { if(!busy) { close(); say(''); CareGuideViews.focusNew(root); } return; }
      if(target.closest('[data-guide-reload]')) {
        const fresh = editing && findGuide(editing.id);
        if(fresh && !busy) { dirty = false; open(fresh); }
        return;
      }
      if(target.closest('[data-guide-new]') || target.closest('[data-guide-edit]')) {
        if(busy) return;
        if(dirty) { say(DIRTY, true); return; }
        say('');
        const edit = target.closest('[data-guide-edit]');
        open(edit ? findGuide(edit.dataset.guideEdit) : null);
        return;
      }
      const publish = target.closest('[data-guide-publish]');
      if(publish) { confirmedChange('publish', service.publish, publish.dataset.guidePublish, 'Ficha publicada. Ya es visible para las personas usuarias.', 'No se pudo publicar la ficha.'); return; }
      const withdraw = target.closest('[data-guide-withdraw]');
      if(withdraw) confirmedChange('withdraw', service.withdraw, withdraw.dataset.guideWithdraw, 'Ficha retirada. Ya no es visible; puedes consultarla en Retiradas.', 'No se pudo retirar la ficha.');
    }, {signal:life.signal});
    form.addEventListener('input', () => { dirty = true; }, {signal:life.signal});
    form.addEventListener('submit', event => {
      event.preventDefault();
      if(!busy && editing) save();
    }, {signal:life.signal});
    load();
    return {dispose() { life.abort(); }};
  }
  return Object.freeze({mount});
})();

// ── Mantenimientos ──
// Cuidados de todos los huertos: lista con filtros, registro y la corrección o anulación de cada uno. El servidor confirma.
const MaintenanceController = (() => {
  function mount({root, service = MaintenanceService} = {}) {
    const life = new AbortController();
    let state = {status:'loading', filters:{}, list:{items:[], page:1, total:0}};
    let datesLife = null, dates = null, serial = 0, working = false, current = null;
    function paint() {
      AdminTableViews.paint(root, MaintenanceViews.screen(state));
      datesLife?.abort();
      if(state.status !== 'ready') return;
      datesLife = new AbortController();
      dates = DateFilterViews.mount(root, datesLife.signal);
    }
    async function load(page = 1) {
      const id = ++serial;
      const result = await service.list(state.filters, page);
      if(life.signal.aborted || id !== serial) return;
      state = result.status === 'ready' ? {...state, status:'ready', list:{items:result.items, page:result.page, total:result.total}} : {...state, status:'error'};
      paint();
    }
    const fail = result => mostrarAviso('error', MaintenanceViews.errorText(result.code));
    async function open(id) {
      const result = await service.detail(id);
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { fail(result); return; }
      current = result.record;
      AdminTableViews.open(root, MaintenanceViews.detail(result.record, result.revisions));
      MaintenanceViews.adjust(root, result.record.type);
    }
    function careValues(form) {
      const plant = form.elements.plant.value, chiles = form.elements.chiles.value;
      return {type:form.elements.type.value, plant:plant ? Number(plant) : null, chiles:chiles !== '' && !form.querySelector('[data-care-chiles]').hidden ? Number(chiles) : null};
    }
    async function create(form) {
      const today = MaintenanceDates.format(MaintenanceDates.today());
      const doneAt = service.moment(form.elements.when.value, today);
      const values = {garden:form.elements.garden.value.trim(), ...careValues(form), ...(doneAt ? {doneAt} : {})};
      if(!AdminHTTP.validId(values.garden)) { mostrarAviso('error', 'Escribe el número del huerto, solo con dígitos.'); return; }
      const result = await service.create(values);
      if(life.signal.aborted) return;
      if(result.status !== 'accepted') { fail(result); return; }
      AdminTableViews.dismiss(root);
      mostrarAviso('exito', 'Intervención registrada.');
      await load(1);
    }
    // Una vez que el servidor responde, el diálogo se cierra y la lista se vuelve a leer: nunca se supone un éxito.
    async function finish(result, message) {
      if(life.signal.aborted) return;
      if(result.status === 'accepted') mostrarAviso('exito', message); else fail(result);
      if(result.status === 'accepted' || ['stale-record', 'cuidado-anulado', 'not-found'].includes(result.code)) { AdminTableViews.dismiss(root); await load(state.list.page); }
    }
    async function revise(form, voiding) {
      const reason = form.elements.reason.value.trim();
      if(!reason) { mostrarAviso('error', 'Escribe el motivo del cambio.'); return; }
      if(voiding) {
        if(!await confirmar(MaintenanceViews.confirmations.void)) return;
        await finish(await service.void(current.id, {revision:current.revision, reason}), 'Registro anulado.');
        return;
      }
      await finish(await service.correct(current.id, {revision:current.revision, ...careValues(form), reason}), 'Corrección guardada.');
    }
    root.addEventListener('click', async event => {
      const trigger = event.target.closest('[data-admin-action]');
      if(!trigger || working) return;
      const {adminAction: action, page, id} = trigger.dataset;
      working = true;
      try {
        if(action === 'page') await load(Number(page));
        else if(action === 'clear') { state.filters = {}; MaintenanceViews.resetFilters(root); await load(1); }
        else if(action === 'create') { AdminTableViews.open(root, MaintenanceViews.createForm()); MaintenanceViews.adjust(root, 'rellenar_deposito'); }
        else if(action === 'open') await open(id);
        else if(action === 'void') await revise(trigger.closest('form'), true);
        else if(action === 'close-dialog') AdminTableViews.dismiss(root);
      } finally { working = false; }
    }, {signal:life.signal});
    root.addEventListener('change', event => { if(event.target.matches('[data-care-type]')) MaintenanceViews.adjust(root, event.target.value); }, {signal:life.signal});
    root.addEventListener('submit', async event => {
      event.preventDefault();
      const kind = event.target.closest('[data-admin-form]')?.dataset.adminForm;
      if(working) return;
      working = true;
      try {
        if(kind === 'care-filter') {
          const invalid = dates.validate();
          if(invalid) { mostrarAviso('error', invalid); return; }
          state.filters = Object.fromEntries(new FormData(event.target));
          await load(1);
        } else if(kind === 'care-create') await create(event.target);
        else if(kind === 'care-revise') await revise(event.target, false);
      } finally { working = false; }
    }, {signal:life.signal});
    load(1);
    return {dispose() { serial++; datesLife?.abort(); life.abort(); }};
  }
  return {mount};
})();

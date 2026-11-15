// CONTROLADOR · Huerto: Mi huerto y sus pantallas, panel técnico y soporte, guías de cuidado y mantenimientos.
// Define: GardenOrderCard, GardenSummaryController, GardenCreateController, GardenLinkController, PlantController, GardenController, MyGardensController, UserGardenController, CareGuideUserController, CareGuideAdminController, MaintenanceController.

// ── Huerto ──
// Mi huerto y sus pantallas. El servidor confirma cada operación; aquí nunca se supone un éxito.
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
        const list = await service.list(request.signal);
        if(list.status !== 'ready') return {status:'error', gardens:[], detail:null};
        const current = GardenModel.pick(list.items, route.gardenId);
        if(!current) return {status:'ready', gardens:[], detail:null};
        const detail = await service.detail(current.id, request.signal);
        if(detail.status !== 'ready') return {status:'error', gardens:[], detail:null};
        GardenModel.remember(current.id);
        return {status:'ready', gardens:list.items, detail};
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
      const list = await service.list(life.signal);
      if(life.signal.aborted) return;
      const garden = list.status === 'ready' ? GardenModel.pick(list.items, route.gardenId) : null;
      if(!garden) { location.hash = '#huerto'; return; }
      GardenModel.remember(garden.id);
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
        const list = await service.list(life.signal);
        const garden = list.status === 'ready' ? GardenModel.pick(list.items, route.gardenId) : null;
        if(life.signal.aborted) return;
        if(!garden) { location.hash = '#huerto'; return; }
        gardenId = garden.id;
        GardenModel.remember(gardenId);
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

// ── Huerto usuario ──
const UserGardenController = (() => {
  const LOAD_TIMEOUT_MS=20000;
  function mount(screen,{root,service=UserGardenService,detail='',onData=()=>{}}={}) {
    const life = new AbortController();
    let data={garden:AppModel.garden({status:'loading'})},range='1h',serial=0,pending=null,origin=null,disposed=false,working=false;
    const current=()=>UserGardenViews.dialog(root);
    const feedback=(text,error=false)=>UserGardenViews.feedback(root,text,error);
    function closeDialog() {
      UserGardenViews.closeDialog(current(),origin);
      pending=null;origin=null;
    }
    function render() {
      UserGardenViews.paint(root,screen,data,AppModel.alias(AuthService.session));
      const dialog=current();
      dialog?.addEventListener('cancel',e=>{e.preventDefault();if(!working)closeDialog();},{signal:life.signal});
      guides.paint(data.garden.status!=='loading');
    }
    async function load({message='',error=false,focusRange=false}={}) {
      const id=++serial;
      // Sin respuesta en el plazo es un error: el esqueleto no debe quedarse para siempre.
      const request=new AbortController();
      const abort=()=>request.abort();
      life.signal.addEventListener('abort',abort,{once:true});
      const timeout=setTimeout(abort,LOAD_TIMEOUT_MS);
      try {
        const response=await service.load(range,{signal:request.signal});
        if(disposed||id!==serial)return;
        data=response;onData(response);render();
        if(message)feedback(message,error);
        else if(focusRange)UserGardenViews.focusRange(root,range);
        else if(detail==='historial')UserGardenViews.focusHistory(root);
      }catch {
        if(disposed||id!==serial)return;
        data={garden:AppModel.garden({status:'error'})};render();
      } finally {
        clearTimeout(timeout);
        life.signal.removeEventListener('abort',abort);
      }
    }
    function openDialog(action,trigger) {
      const dialog=current();if(!dialog||dialog.open)return;
      origin=trigger;pending=action;
      UserGardenViews.openDialog(dialog,action);
    }
    async function confirm() {
      if(!pending||working)return;
      const selected=pending;
      const consent=root.querySelector('#user-support-consent');
      if(selected==='support'&&!consent?.checked)return;
      working=true;
      UserGardenViews.lockDialog(current());
      try {
        const response=selected==='support'?await service.issuePermission(data.selectedIncident,consent.checked,{signal:life.signal}):await service.command(selected,data,{signal:life.signal});
        if(disposed)return;
        closeDialog();
        if(response.status==='accepted')await load({message:selected==='support'?(response.tokenAvailable?'Tu token de soporte está disponible. Puedes copiarlo o revocar la autorización.':'La autorización está registrada. El token solo se entrega una vez; si no lo conservas, revoca y genera otra autorización.'):'Solicitud registrada. Esperando confirmación del dispositivo.'});
        else feedback(response.status==='unavailable'?'La emisión de tokens de soporte no está disponible en este momento.':response.status==='offline'?'No se envió la solicitud. Revisa la conexión Wi-Fi y MQTT del huerto.':response.status==='low-water'?'No se solicitó el riego. Revisa el nivel del depósito antes de continuar.':'No se pudo completar la solicitud. Inténtalo de nuevo.',true);
      } catch {
        if(!disposed){closeDialog();feedback('No se pudo completar la solicitud. Inténtalo de nuevo.',true);}
      } finally {working=false;}
    }
    root.addEventListener('click',async e=>{
      const trigger=e.target.closest('[data-user-action]');if(!trigger||working)return;
      const action=trigger.dataset.userAction;
      if(action==='cancel-dialog'){closeDialog();return;}
      if(action==='confirm-dialog'){await confirm();return;}
      if(action==='range'){range=trigger.dataset.range;await load({focusRange:true});return;}
      if(action==='refresh'){
        if(data.garden.status==='error'){data={garden:AppModel.garden({status:'loading'})};render();await load();return;}
        await load({message:'Información actualizada.'});return;
      }
      if(action.startsWith('record-')){
        working=true;let response;try{response=await service.recordTask(action.slice(7),{signal:life.signal});}catch{response={status:'error'};}finally{working=false;}
        if(disposed)return;
        await load({message:response.status==='accepted'?`${response.label} registrada.`:'No se pudo registrar la tarea.',error:response.status!=='accepted'});return;
      }
      if(['water','lamp-off','lamp-auto'].includes(action)){openDialog(action,trigger);return;}
      if(action==='revoke'){const response=await service.revokePermission({signal:life.signal});if(disposed)return;await load({message:response.status==='accepted'?'Autorización revocada. El acceso técnico permanece cerrado.':'No se pudo confirmar la revocación. Inténtalo de nuevo.',error:response.status!=='accepted'});return;}
      if(action==='copy-token'){
        const permission=service.permission();
        if(!permission||typeof permission.token!=='string'){await load({message:'El token solo se entrega al emitir la autorización. Si no lo conservas, revoca y genera una nueva.',error:true});return;}
        try{await navigator.clipboard.writeText(permission.token);if(!disposed)feedback('Token copiado. Compártelo únicamente con el personal de soporte.');}
        catch{if(!disposed)feedback('No se pudo copiar automáticamente. Selecciona y copia el código que aparece en pantalla.',true);}return;
      }
    },{signal:life.signal});
    root.addEventListener('submit',e=>{
      if(!e.target.matches('[data-user-support-form]'))return;
      e.preventDefault();if(!e.target.reportValidity())return;
      if(!service.supportAvailable){feedback('La emisión de tokens de soporte no está disponible en este momento.',true);return;}
      data.selectedIncident=new FormData(e.target).get('incident');
      openDialog('support',e.target.querySelector('button[type="submit"]'));
    },{signal:life.signal});
    root.addEventListener('change',e=>{
      if(e.target.id==='user-support-consent')UserGardenViews.consentChanged(current(),e.target.checked);
    },{signal:life.signal});
    const checkPermission=()=>{
      if(screen!=='soporte'||disposed||!data.permission)return;
      if(!service.permission())load({message:'La autorización ha vencido. El acceso técnico permanece cerrado.'});
    };
    const timer=setInterval(checkPermission,1000);
    document.addEventListener('visibilitychange',checkPermission,{signal:life.signal});
    const guides=CareGuideUserController.attach({root,signal:life.signal,screen,detail});
    render();load();
    return {redraw:render,dispose(){disposed=true;serial++;clearInterval(timer);closeDialog();life.abort();}};
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
      if(publish) { changeState(service.publish, publish.dataset.guidePublish, 'Ficha publicada. Ya es visible para las personas usuarias.', 'No se pudo publicar la ficha.'); return; }
      const withdraw = target.closest('[data-guide-withdraw]');
      if(withdraw) changeState(service.withdraw, withdraw.dataset.guideWithdraw, 'Ficha retirada. Ya no es visible; puedes consultarla en Retiradas.', 'No se pudo retirar la ficha.');
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
const MaintenanceController = (() => {
  function mount({root, service = MaintenanceService} = {}) {
    const life = new AbortController();
    const view = MaintenanceViews.mount(root);
    const {revise, filter} = view;
    const dateFilters = DateFilterViews.mount(filter,life.signal);
    let current = null, ready = false;
    async function load() {
      const invalid = dateFilters.validate();
      if(invalid) { view.statusText(invalid); return; }
      view.loading();
      const result = await service.list(Object.fromEntries(new FormData(filter)));
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { view.failed(result.status); return; }
      view.show(result, !ready); ready = true;
    }
    async function open(id) {
      const result = await service.detail(id);
      if(result.status !== 'ready') { view.notify(result.status,true); return; }
      current = result.record;
      view.openDetail(result.record, result.revisions);
    }
    root.addEventListener('click',event => {
      const opener = event.target.closest('[data-maint-open]');
      if(opener) open(opener.dataset.maintOpen);
    },{signal:life.signal});
    view.closers.forEach(button => button.addEventListener('click',view.closeDetail,{signal:life.signal}));
    filter.addEventListener('change',load,{signal:life.signal});
    filter.addEventListener('submit',event => { event.preventDefault(); load(); },{signal:life.signal});
    view.create.addEventListener('submit',async event => {
      event.preventDefault();
      const values = new FormData(event.target);
      const result = await service.create(Number(values.get('garden')),values.get('task'));
      if(result.status === 'accepted') { view.notify('created'); load(); } else view.notify(result.status,true);
    },{signal:life.signal});
    revise.addEventListener('submit',async event => {
      event.preventDefault();
      const reason = revise.elements.reason.value.trim();
      if(!reason) { view.showError('reason'); return; }
      const voiding = event.submitter?.value === 'void';
      const result = voiding ? await service.void(current.id,reason,current.revision)
        : await service.correct(current.id,revise.elements.task.value,reason,current.revision);
      if(result.status === 'accepted') { view.closeDetail(); view.notify(voiding?'voided':'corrected'); load(); return; }
      view.showError(result.status);
      if(result.status === 'stale') { view.closeDetail(); view.notify('stale',true); load(); }
    },{signal:life.signal});
    load();
    return {dispose(){life.abort(); view.closeDetail();}};
  }
  return {mount};
})();

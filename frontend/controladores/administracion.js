// CONTROLADOR · Administración: paneles de administración, consultas, comercial y el panel general.
// Define: AdminController, InquiryController, CommerceController, AppController.

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

// ── Comercial ──
// Coordinación local exclusivamente. No tiene transporte ni acceso al servicio de emisión.
const CommerceController = (() => {
  function mount({root,session=AuthService.session}={}) {
    // Visibilidad provisional; no sustituye autorización del servidor para futuras operaciones.
    if(!AppModel.allowedAdmin(session).some(item=>item.id==='admin/comercial')) {
      CommerceViews.unavailable(root);
      return {dispose(){}};
    }
    const life=new AbortController(), model=CommerceModel.create();
    const {workspace,tablist,forms}=CommerceViews.mount(root);
    const calendars=DateFilterViews.mount(workspace,life.signal);
    function activate(key,focus=false) {
      calendars.close(false);
      model.select(key); CommerceViews.activate(root,key);
      if(focus) CommerceViews.focusTab(root,key);
    }
    function reviewChanged(kind) {
      CommerceViews.renderReview(root,kind,null);
      CommerceViews.bindingContext(root,model.read());
    }
    function edit(event) {
      const form=event.target.closest('[data-commerce-form]');
      const kind=form?.dataset.commerceForm;
      if(kind==='sale' || kind==='equipment') {
        model.edit(kind,CommerceViews.read(form)); reviewChanged(kind);
        // Al corregir, retira solo el error de ese campo; los demás siguen visibles.
        const issues=Object.fromEntries([...form.querySelectorAll('[aria-invalid=true]')]
          .filter(field=>field!==event.target).map(field=>[field.name,field.validationMessage]));
        CommerceViews.formErrors(form,issues);
      } else if(kind==='salesFilter' || kind==='summaryFilter') {
        if(kind==='summaryFilter' && event.target.name==='preset') {
          const value=event.target.value;
          if(value!=='custom') CommerceViews.fill(form,CommerceModel.periodPreset(value||'all'));
        } else if(kind==='summaryFilter' && ['since','until'].includes(event.target.name)) CommerceViews.customPeriod(form);
        CommerceViews.formErrors(form,CommerceModel.period(CommerceViews.read(form)));
        CommerceViews.filterStatus(root,kind,'changed');
      }
    }
    root.addEventListener('input',edit,{signal:life.signal});
    root.addEventListener('change',edit,{signal:life.signal});
    root.addEventListener('submit',event=>{
      const form=event.target.closest('[data-commerce-form]');
      if(!form) return;
      event.preventDefault();
      const kind=form.dataset.commerceForm;
      if(kind==='equipment' || kind==='sale') {
        model.edit(kind,CommerceViews.read(form));
        const result=model.review(kind);
        CommerceViews.formErrors(form,result.errors);
        CommerceViews.renderReview(root,kind,Object.keys(result.errors).length?null:result.data);
        CommerceViews.bindingContext(root,model.read());
        if(Object.keys(result.errors).length) { CommerceViews.focusInvalid(form); return; }
        calendars.close(false); CommerceViews.focusReview(root,kind);
      } else {
        const issues=kind==='inventoryFilter'?{}:CommerceModel.period(CommerceViews.read(form));
        CommerceViews.formErrors(form,issues);
        if(Object.keys(issues).length) { CommerceViews.focusInvalid(form); return; }
        CommerceViews.filterStatus(root,kind,'ready');
      }
    },{signal:life.signal});
    root.addEventListener('click',event=>{
      const tab=event.target.closest('[data-commerce-tab]');
      if(tab) { activate(tab.dataset.commerceTab); return; }
      const editor=event.target.closest('[data-edit]');
      if(editor) { CommerceViews.focusFirstInput(forms[editor.dataset.edit]); return; }
      if(event.target.closest('[data-use-equipment]')) {
        const equipment=model.read().equipmentReview;
        if(!equipment) return;
        CommerceViews.setEquipment(forms.sale,equipment.identifier);
        model.edit('sale',CommerceViews.read(forms.sale)); reviewChanged('sale');
        CommerceViews.formErrors(forms.sale,{});
        activate('ventas'); CommerceViews.focusEquipment(forms.sale);
      }
    },{signal:life.signal});
    tablist.addEventListener('keydown',event=>{
      const tab=event.target.closest('[data-commerce-tab]');
      if(!tab || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault();
      const keys=CommerceModel.tabs.map(([key])=>key), current=keys.indexOf(tab.dataset.commerceTab);
      const index=event.key==='Home'?0:event.key==='End'?keys.length-1:(current+(event.key==='ArrowRight'?1:-1)+keys.length)%keys.length;
      activate(keys[index],true);
    },{signal:life.signal});
    CommerceViews.bindingContext(root,model.read());
    return {dispose(){life.abort(); model.dispose();}};
  }
  return Object.freeze({mount});
})();

// ── Panel ──
const AppController = (() => {
  // Qué destinos ve esta sesión: decisión de coordinación (la autorización real sigue en el servidor).
  function navigation(route, session) {
    const isAdmin = route.screen==='admin' || session?.role==='admin';
    const account = AppModel.destinations.find(item=>item.id==='cuenta');
    const links = isAdmin ? [...AppModel.allowedAdmin(session), account] : AppModel.destinations.filter(item=>item.id!=='avisos');
    return {isAdmin, links, account};
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
        adminPanel=route.detail==='comercial'?CommerceController.mount({root:page,session:authService.session}):route.detail==='mantenimientos'?MaintenanceController.mount({root:page}):route.detail==='solicitudes'?InquiryController.mount({root:page}):route.detail==='vinculacion'?BindingAdminController.mount({root:page}):route.detail==='guias'?CareGuideAdminController.mount({root:page}):AdminController.mount(route.detail,{root:page});
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

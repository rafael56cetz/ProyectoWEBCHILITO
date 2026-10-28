const AppController = (() => {
  function mount(route, {root, service = AppService, authService = AuthService, privacyService = PrivacyService, passkeyInteraction = null, config = AuthConfig, review = false, onLogout} = {}) {
    root.innerHTML = AppViews.shell(route);
    const lifetime = new AbortController();
    let pageLifetime = new AbortController(), loadingTimer = null, logoutOrigin = null;
    const logoutDialog = root.querySelector('.logout-dialog');
    const linkDialog = root.querySelector('.garden-link-dialog');
    let linkOrigin = null;
    const page = root.querySelector('#app-page');
    const feedback = root.querySelector('#app-feedback');
    let adminPanel = null, userGarden = null, auth = null, privacy = null, security = null, filter = 'all', data = null, sequence = 0, busy = false;
    const message = (text, error = false) => {
      feedback.hidden = false;
      feedback.textContent = text;
      feedback.setAttribute('role', error ? 'alert' : 'status');
      feedback.focus();
    };
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
      const focusedFilter = page.contains(document.activeElement) ? document.activeElement.dataset.filter : null;
      if(route.screen === 'huerto') page.innerHTML = garden(data);
      if(route.screen === 'avisos') page.innerHTML = AppViews.notices(data, filter, route.detail);
      if(route.screen === 'cuenta') page.innerHTML = AppViews.account(data);
      if(focusedFilter) page.querySelector(`[data-filter="${focusedFilter}"]`)?.focus();
    }
    async function load() {
      const id = ++sequence;
      feedback.hidden = true;
      clearTimeout(loadingTimer);
      page.inert = false;
      page.removeAttribute('aria-busy');
      if(route.screen==='admin') {
        adminPanel=AdminController.mount(route.detail,{root:page});
        return;
      }
      if(['huerto','telemetria','mantenimiento','soporte'].includes(route.screen)) {
        userGarden = UserGardenController.mount(route.screen,{root:page,detail:route.detail,onData:next=>{data=next.garden;}});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'seguridad') {
        security?.dispose();
        if(route.invalidSecurity) { page.innerHTML = AppViews.heading('Página no disponible')+'<p><a href="#cuenta/seguridad">Seguridad de mi cuenta</a></p>'; return; }
        security = SecurityController.mount('account',{root:page,service:authService,config,review,interaction:passkeyInteraction});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'privacidad') {
        privacy?.dispose();
        privacy = PrivacyController.mount(route,{root:page,service:privacyService,config,review});
        return;
      }
      if(route.screen === 'cuenta' && route.detail === 'contrasena') {
        auth = AuthController.mount('cambiar', {root:page, service:authService, config, embedded:true, review});
        return;
      }
      data = route.screen === 'huerto' ? AppModel.garden({status:'loading'}) : {status:'loading', items:[]};
      page.inert = true;
      page.setAttribute('aria-busy','true');
      // Fast requests replace the content directly; slow ones still have a loading state.
      if(!page.hasChildNodes()) draw();
      else loadingTimer = setTimeout(() => { if(id === sequence && !lifetime.signal.aborted) draw(); }, 200);
      const response = await request(route.screen === 'avisos' && route.detail ? 'notice' : {huerto:'garden', avisos:'notices', cuenta:'profile'}[route.screen], route.detail ? {id:route.detail} : {});
      if(lifetime.signal.aborted || id !== sequence) return;
      clearTimeout(loadingTimer);
      page.inert = false;
      page.removeAttribute('aria-busy');
      data = route.screen === 'huerto' ? AppModel.garden(response) : route.screen === 'avisos' ? AppModel.notices(response) : AppModel.profile(response);
      draw();
    }
    function closeLink(returnFocus = true) {
      linkDialog.querySelector('form').reset();
      if(linkDialog.open) linkDialog.close();
      if(returnFocus && linkOrigin?.isConnected) linkOrigin.focus({preventScroll:true});
      linkOrigin = null;
    }
    function openLink(trigger) {
      if(route.screen !== 'huerto' || data?.status !== 'unassigned' || linkDialog.open) return;
      linkOrigin = trigger;
      linkDialog.showModal();
      linkDialog.querySelector('input').focus();
    }
    linkDialog.addEventListener('cancel', event => { event.preventDefault(); closeLink(); }, {signal:lifetime.signal});
    linkDialog.addEventListener('close', () => linkDialog.querySelector('form').reset(), {signal:lifetime.signal});
    linkDialog.querySelector('form').addEventListener('submit', event => event.preventDefault(), {signal:lifetime.signal});
    function closeLogout(returnFocus = true) {
      if(logoutDialog.open) logoutDialog.close();
      if(returnFocus) {
        const visibleOrigin=logoutOrigin?.isConnected&&logoutOrigin.getClientRects().length;
        const fallback=isUserMobile()?toggle:root.querySelector('.site-header [data-app-action="logout"]');
        (visibleOrigin?logoutOrigin:fallback)?.focus({preventScroll:true});
      }
      logoutOrigin = null;
    }
    function openLogout(trigger) {
      if(logoutDialog.open) return;
      logoutOrigin = trigger;
      const error = logoutDialog.querySelector('.logout-error');
      error.hidden = true; error.textContent = '';
      logoutDialog.showModal();
      logoutDialog.querySelector('[data-app-action="cancel-logout"]').focus();
    }
    async function confirmLogout() {
      if(busy || !logoutDialog.open) return;
      const id = sequence;
      busy = true;
      logoutDialog.setAttribute('aria-busy','true');
      const confirm = logoutDialog.querySelector('[data-app-action="confirm-logout"]');
      const error = logoutDialog.querySelector('.logout-error');
      error.hidden = true; error.textContent = '';
      logoutDialog.querySelectorAll('button').forEach(button => { button.disabled = true; });
      confirm.textContent = 'Cerrando sesión…';
      const response = await request('logout');
      if(lifetime.signal.aborted || id !== sequence) return;
      busy = false;
      logoutDialog.removeAttribute('aria-busy');
      logoutDialog.querySelectorAll('button').forEach(button => { button.disabled = false; });
      confirm.textContent = 'Cerrar sesión';
      if(response.status === 'accepted') { closeLogout(false); onLogout?.(); return; }
      error.hidden = false;
      error.textContent = 'No se pudo cerrar la sesión. Inténtalo de nuevo.';
      error.focus();
    }
    logoutDialog.addEventListener('cancel', event => {
      event.preventDefault();
      if(!busy) closeLogout();
    }, {signal:lifetime.signal});
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
      closeLogout(false);
      closeLink(false);
      busy = false;
      logoutDialog.removeAttribute('aria-busy');
      logoutDialog.querySelectorAll('button').forEach(button => { button.disabled = false; });
      logoutDialog.querySelector('[data-app-action="confirm-logout"]').textContent = 'Cerrar sesión';
    }
    function update(nextRoute) {
      setMenuOpen(false);
      releasePage();
      route = nextRoute;
      filter = 'all';
      root.querySelectorAll('.private-nav a').forEach(link => {
        if(link.getAttribute('href') === '#' + (route.screen==='admin'?'admin/'+route.detail:route.screen)) link.setAttribute('aria-current','page');
        else link.removeAttribute('aria-current');
      });
      load();
    }
    root.addEventListener('click', async event => {
      const target = event.target.closest('[data-filter],[data-app-action]');
      if(!target || busy) return;
      if(target.dataset.filter) {
        filter = target.dataset.filter;
        draw();
        page.querySelector(`[data-filter="${filter}"]`)?.focus();
        return;
      }
      const action = target.dataset.appAction;
      if(action === 'toggle-menu') { setMenuOpen(!menuOpen); return; }
      if(action === 'close-menu') { setMenuOpen(false,true); return; }
      if(action === 'reload') { await load(); if(!lifetime.signal.aborted) root.querySelector('main')?.focus(); return; }
      if(action === 'open-link') { openLink(target); return; }
      if(action === 'cancel-link') { closeLink(); return; }
      if(action === 'logout') { openLogout(target); return; }
      if(action === 'cancel-logout') { closeLogout(); return; }
      if(action === 'confirm-logout') { await confirmLogout(); return; }
      if(action !== 'mark-read') return;
      const id = sequence;
      busy = true;
      target.disabled = true;
      target.setAttribute('aria-busy','true');
      const response = await request(action, action === 'mark-read' ? {id:target.dataset.id} : {});
      if(lifetime.signal.aborted || id !== sequence) return;
      busy = false;
      target.disabled = false;
      target.removeAttribute('aria-busy');
      if(response.status === 'unassigned' || response.status === 'not-found') {
        data = AppModel.notices(response);
        draw();
        return;
      }
      if(response.status !== 'accepted') { message('No se pudo completar la solicitud. Inténtalo de nuevo.', true); return; }
      // Reading a notice never changes its active/resolved condition.
      data.items = data.items.map(item => item.id === response.id ? response.item : item);
      draw();
      message('Aviso marcado como leído. Su condición no ha cambiado.');
    }, {signal:lifetime.signal});
    const nav = root.querySelector('.sidebar');
    const toggle=root.querySelector('.private-menu-toggle');
    const shade=root.querySelector('.private-menu-shade');
    const mobileScreen=matchMedia('(max-width:768px)');
    let menuOpen=false;
    const isUserMobile=()=>Boolean(toggle)&&mobileScreen.matches;
    function setMenuOpen(open,returnFocus=false) {
      menuOpen=Boolean(open&&isUserMobile());
      nav.dataset.open=String(menuOpen);
      nav.inert=isUserMobile()&&!menuOpen;
      if(nav.inert)nav.setAttribute('aria-hidden','true');else nav.removeAttribute('aria-hidden');
      toggle?.setAttribute('aria-expanded',String(menuOpen));
      toggle?.setAttribute('aria-label',menuOpen?'Cerrar menú de navegación':'Abrir menú de navegación');
      if(shade)shade.hidden=!menuOpen;
      document.body.classList.toggle('private-menu-open',menuOpen);
      if(returnFocus&&isUserMobile())toggle.focus({preventScroll:true});
    }
    function syncMenuMode() {
      const wasInNav=nav.contains(document.activeElement);
      const wasOnToggle=document.activeElement===toggle;
      setMenuOpen(false,isUserMobile()&&wasInNav);
      if(!isUserMobile()&&wasOnToggle)nav.querySelector('[aria-current="page"]')?.focus();
    }
    nav.addEventListener('click',event=>{
      const link=event.target.closest('a');if(!link||!isUserMobile())return;
      setMenuOpen(false);
      if(link.getAttribute('href')===location.hash)root.querySelector('main')?.focus({preventScroll:true});
    },{signal:lifetime.signal});
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&menuOpen&&!logoutDialog.open&&!linkDialog.open){event.preventDefault();setMenuOpen(false,true);}
    },{signal:lifetime.signal});
    document.addEventListener('click',event=>{
      if(menuOpen&&!event.target.closest('dialog')&&!nav.contains(event.target)&&!toggle.contains(event.target)&&!logoutDialog.open&&!linkDialog.open)setMenuOpen(false);
    },{signal:lifetime.signal});
    document.addEventListener('focusin',event=>{
      if(menuOpen&&!event.target.closest('dialog')&&!nav.contains(event.target)&&!toggle.contains(event.target)&&!logoutDialog.open&&!linkDialog.open)setMenuOpen(false);
    },{signal:lifetime.signal});
    mobileScreen.addEventListener('change',syncMenuMode,{signal:lifetime.signal});
    syncMenuMode();
    const isMobileNav = () => route.screen==='admin' && getComputedStyle(nav).position === 'fixed' && window.innerWidth <= 768;
    const sizeNav = () => {
      document.documentElement.style.setProperty('--private-nav-height', isMobileNav() ? `${nav.getBoundingClientRect().height}px` : '0px');
    };
    const observer = new ResizeObserver(sizeNav);
    observer.observe(nav);
    window.addEventListener('resize', sizeNav, {signal:lifetime.signal});
    const keepFieldVisible = () => {
      const focused = document.activeElement;
      if(!page.contains(focused) || focused.closest('.account-tabs') || !focused.matches('input,select,textarea,button,a')) return;
      const available = window.visualViewport ? window.visualViewport.height + window.visualViewport.offsetTop : innerHeight;
      const bottom = Math.min(available, isMobileNav() ? nav.getBoundingClientRect().top : available);
      if(focused.getBoundingClientRect().bottom > bottom - 16) focused.scrollIntoView({block:'center'});
    };
    root.addEventListener('focusin', keepFieldVisible, {signal:lifetime.signal});
    window.visualViewport?.addEventListener('resize', keepFieldVisible);
    sizeNav();
    load();
    return {update, dispose() {
      setMenuOpen(false);
      nav.inert=false;nav.removeAttribute('aria-hidden');
      releasePage();
      pageLifetime.abort();
      lifetime.abort();
      observer.disconnect();
      window.visualViewport?.removeEventListener('resize', keepFieldVisible);
      document.documentElement.style.setProperty('--private-nav-height','0px');
    }};
  }
  return {mount};
})();

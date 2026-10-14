const AppController = (() => {
  function mount(route, {root, service = AppService, authService = AuthService, config = AuthConfig, onLogout} = {}) {
    root.innerHTML = AppViews.shell(route);
    const lifetime = new AbortController();
    const page = root.querySelector('#app-page');
    const feedback = root.querySelector('#app-feedback');
    let auth = null, filter = 'all', data = null, sequence = 0, busy = false;
    const message = (text, error = false) => {
      feedback.hidden = false;
      feedback.textContent = text;
      feedback.setAttribute('role', error ? 'alert' : 'status');
      feedback.focus();
    };
    async function request(action, payload = {}) {
      const controller = new AbortController();
      const abort = () => controller.abort();
      lifetime.signal.addEventListener('abort', abort, {once:true});
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
        lifetime.signal.removeEventListener('abort', abort);
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
      if(route.screen === 'asistente') { page.innerHTML = AppViews.assistant(); return; }
      if(route.screen === 'cuenta' && route.detail === 'contrasena') {
        auth = AuthController.mount('cambiar', {root:page, service:authService, config, embedded:true});
        return;
      }
      data = route.screen === 'huerto' ? AppModel.garden({status:'waiting'}) : {status:'loading', items:[]};
      draw();
      const response = await request({huerto:'garden', avisos:'notices', cuenta:'profile'}[route.screen]);
      if(lifetime.signal.aborted || id !== sequence) return;
      data = route.screen === 'huerto' ? AppModel.garden(response) : route.screen === 'avisos' ? AppModel.notices(response) : AppModel.profile(response);
      draw();
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
      if(action === 'reload') { await load(); if(!lifetime.signal.aborted) root.querySelector('main')?.focus(); return; }
      if(!['logout','mark-read'].includes(action)) return;
      busy = true;
      target.disabled = true;
      target.setAttribute('aria-busy','true');
      const response = await request(action, action === 'mark-read' ? {id:target.dataset.id} : {});
      if(lifetime.signal.aborted) return;
      busy = false;
      target.disabled = false;
      target.removeAttribute('aria-busy');
      if(response.status !== 'accepted') { message('No se pudo completar la solicitud. Inténtalo de nuevo.', true); return; }
      if(action === 'logout') { onLogout?.(); return; }
      // Reading a notice never changes its active/resolved condition.
      data.items = data.items.map(item => item.id === target.dataset.id ? {...item, read:true} : item);
      draw();
      message('Aviso marcado como leído. Su condición no ha cambiado.');
    }, {signal:lifetime.signal});
    const nav = root.querySelector('.sidebar');
    const sizeNav = () => {
      const fixed = getComputedStyle(nav).position === 'fixed';
      document.documentElement.style.setProperty('--private-nav-height', fixed ? `${nav.getBoundingClientRect().height}px` : '0px');
    };
    const observer = new ResizeObserver(sizeNav);
    observer.observe(nav);
    window.addEventListener('resize', sizeNav, {signal:lifetime.signal});
    const keepFieldVisible = () => {
      const focused = document.activeElement;
      if(!page.contains(focused) || !focused.matches('input,button,a')) return;
      const available = window.visualViewport ? window.visualViewport.height + window.visualViewport.offsetTop : innerHeight;
      const bottom = Math.min(available, getComputedStyle(nav).position === 'fixed' ? nav.getBoundingClientRect().top : available);
      if(focused.getBoundingClientRect().bottom > bottom - 16) focused.scrollIntoView({block:'center'});
    };
    root.addEventListener('focusin', keepFieldVisible, {signal:lifetime.signal});
    window.visualViewport?.addEventListener('resize', keepFieldVisible);
    sizeNav();
    load();
    return {dispose() {
      sequence++;
      lifetime.abort();
      auth?.dispose();
      observer.disconnect();
      window.visualViewport?.removeEventListener('resize', keepFieldVisible);
      document.documentElement.style.setProperty('--private-nav-height','0px');
    }};
  }
  return {mount};
})();

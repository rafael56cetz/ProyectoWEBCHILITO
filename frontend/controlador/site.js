// One router with a server-confirmed session guard.
const SiteController = (() => {
  function start({authService = AuthService, appService = AppService, privacyService = PrivacyService, passkeyInteraction = null, config = AuthConfig, assets = '', review = false, canEnter = options => authService.restore(options)} = {}) {
    const sections = ['inicio','el-proyecto','prototipo','como-funciona'];
    const app = document.getElementById('app');
    let current = {}, controller = null, authContext = {}, renderId = 0, navigationRequest = null;
    function routeFromHash() {
      const [path, query = ''] = location.hash.slice(1).split('?');
      const [part, encodedDetail] = path.split('/');
      let detail;
      try { detail = decodeURIComponent(encodedDetail || ''); } catch { detail = ''; }
      if(part==='admin') return {screen:'admin',detail:['flota','soporte','gobernanza','despliegues'].includes(detail)?detail:'flota'};
      if(path === 'derechos-arco') return {screen:'derechos-arco'};
      if(part === 'cuenta' && detail === 'seguridad') return {screen:'cuenta',detail:'seguridad',invalidSecurity:path.split('/').length !== 2};
      if(part === 'cuenta' && detail === 'privacidad') {
        const segments = path.split('/');
        if(segments.length === 2) return {screen:'cuenta',detail:'privacidad',privacyView:'list'};
        let requestId = '';
        try { requestId = decodeURIComponent(segments[3] || ''); } catch { /* Invalid identifiers never reach the service. */ }
        return {screen:'cuenta',detail:'privacidad',privacyView:segments.length === 4 && segments[2] === 'solicitudes' && PrivacyModel.validId(requestId) ? 'detail' : 'invalid',requestId};
      }
      if(part === 'asistente') { history.replaceState(null,'',location.pathname + location.search + '#huerto'); return {screen:'huerto'}; }
      if(part === 'huerto' && detail === 'avisos') {
        history.replaceState(null,'',location.pathname + location.search + '#avisos');
        return {screen:'avisos',detail:''};
      }
      if(part === 'restablecer') {
        const token = new URLSearchParams(query).get('token');
        if(token) {
          authContext = {resetToken:token};
          history.replaceState(null,'',location.pathname + location.search + '#restablecer');
        }
      }
      if(AuthModel.screens.includes(part)) return {screen:part};
      if(Object.hasOwn(PrivacyModel.documents, part) && !encodedDetail) return {screen:part};
      if(AppModel.destinations.some(item => item.id === part)) return {screen:part,detail};
      return {screen:'inicio',anchor:sections.includes(part) ? part : null};
    }
    async function render() {
      const id = ++renderId;
      navigationRequest?.abort();
      navigationRequest = null;
      app.removeAttribute('aria-busy');
      let route = routeFromHash();
      const requestedPrivate = AppModel.isPrivate(route.screen);
      if(requestedPrivate) {
        // Keep the last authorized view and its navigation while checking the next route.
        if(!controller?.update || !AppModel.isPrivate(current.screen)) {
          controller?.dispose(); controller = null;
          app.innerHTML = AuthViews.sessionChecking();
        }
        app.setAttribute('aria-busy','true');
        const guard = new AbortController();
        navigationRequest = guard;
        const timeout = setTimeout(() => guard.abort(), config.requestTimeoutMs);
        let session;
        try { session = await canEnter({signal:guard.signal}); } catch { session = {status:'unavailable'}; }
        finally {
          clearTimeout(timeout);
          if(id === renderId) { navigationRequest = null; app.removeAttribute('aria-busy'); }
        }
        if(id !== renderId) return;
        if(session?.status !== 'authenticated') {
          const verifying = session?.status === 'verification-required';
          const destination = verifying ? 'verificar' : 'acceso';
          authContext = verifying ? {email:session.email,expiresAt:AuthModel.expiry(session.expiresAt)} : {feedback:session?.status === 'unavailable' ? 'No podemos comprobar tu sesión. Inténtalo de nuevo.' : 'Inicia sesión para continuar.'};
          history.replaceState(null,'',location.pathname + location.search + '#' + destination);
          route = {screen:destination};
        } else if((session.role==='admin') !== (route.screen==='admin')) {
          route=session.role==='admin'?{screen:'admin',detail:'flota'}:{screen:'huerto'};
          history.replaceState(null,'',location.pathname+location.search+'#'+(route.screen==='admin'?'admin/flota':'huerto'));
        }
      }
      if(route.screen === 'verificar' && !authContext.email) {
        let verification;
        try { verification = await authService.verificationContext(); } catch { verification = {status:'unavailable'}; }
        if(id !== renderId) return;
        if(verification.status === 'verification-required') authContext = {email:verification.email,expiresAt:AuthModel.expiry(verification.expiresAt)};
        else {
          authContext = {feedback:'Inicia sesión para continuar la verificación de tu correo.'};
          history.replaceState(null,'',location.pathname + location.search + '#acceso');
          route = {screen:'acceso'};
        }
      }
      const isPrivate = AppModel.isPrivate(route.screen);
      const changed = route.screen !== current.screen || route.detail !== current.detail || route.privacyView !== current.privacyView || route.requestId !== current.requestId || route.invalidSecurity !== current.invalidSecurity;
      const reuseShell = isPrivate && (route.screen==='admin')===(current.screen==='admin') && Boolean(controller?.update) && AppModel.isPrivate(current.screen);
      if(!reuseShell) { controller?.dispose(); controller = null; }
      current = route;
      document.body.dataset.screen = route.screen;
      document.body.dataset.private = String(isPrivate);
      document.body.dataset.role = route.screen==='admin'?'admin':'user';
      if(AuthModel.screens.includes(route.screen)) {
        document.title = AuthViews.title(route.screen) + ' · El Chilito';
        controller = AuthController.mount(route.screen, {
          root:app, service:authService, config, assets, context:authContext, review, passkeyInteraction,
          onNavigate(screen, context) { authContext = context; location.hash = '#' + screen; },
          async onSessionConfirmed() { authContext = {}; const session=await authService.restore(); location.hash=session.role==='admin'?'#admin/flota':'#huerto'; }
        });
        delete authContext.resetToken;
      } else if(route.screen === 'derechos-arco') {
        authContext = {};
        document.title = 'Derechos ARCO · El Chilito';
        controller = PrivacyController.mount(route,{root:app,service:privacyService,config,review});
      } else if(Object.hasOwn(PrivacyModel.documents, route.screen)) {
        authContext = {};
        const legalDocument = PrivacyModel.documents[route.screen];
        document.title = legalDocument.title + ' · El Chilito';
        app.innerHTML = LegalViews.render(legalDocument, route.screen);
      } else if(isPrivate) {
        authContext = {};
        document.title = (route.screen==='admin' ? AppModel.adminDestinations.find(item=>item.id==='admin/'+route.detail).label : route.screen === 'cuenta' && route.detail === 'contrasena' ? 'Cambiar contraseña' : route.screen === 'avisos' && route.detail ? 'Detalle del aviso' : AppModel.destinations.find(item=>item.id===route.screen).label) + ' · El Chilito';
        if(route.privacyView) document.title = (route.privacyView === 'list' ? 'Privacidad' : route.privacyView === 'invalid' ? 'Solicitud no disponible' : 'Solicitud ARCO') + ' · El Chilito';
        if(route.detail === 'seguridad') document.title = (route.invalidSecurity?'Página no disponible':'Seguridad') + ' · El Chilito';
        if(reuseShell) controller.update(route);
        else controller = AppController.mount(route, {root:app,service:appService,authService,privacyService,passkeyInteraction,config,review,onLogout() {location.hash = '#acceso';}});
      } else {
        authContext = {};
        document.title = 'Tu huerto de habanero, dentro de casa · El Chilito';
        app.innerHTML = landing(assets);
      }
      if(!reuseShell) window.bindNavigation();
      if(changed) { window.scrollTo(0,0); document.getElementById('contenido')?.focus({preventScroll:true}); }
      if(route.anchor && route.anchor !== 'inicio') requestAnimationFrame(() => {
        const target = document.getElementById(route.anchor);
        if(target) { target.tabIndex = -1; target.focus({preventScroll:true}); target.scrollIntoView(); }
      });
      else if(route.screen === 'inicio') window.scrollTo(0,0);
    }
    document.querySelector('.skip-link')?.addEventListener('click', event => {
      event.preventDefault(); document.getElementById('contenido')?.focus();
    });
    window.addEventListener('hashchange', render);
    window.addEventListener('pagehide', () => { renderId++; navigationRequest?.abort(); controller?.dispose(); controller = null; });
    window.addEventListener('chilito:session-expired', () => {
      renderId++; navigationRequest?.abort();
      authContext = {feedback:'Tu sesión ha vencido. Inicia sesión de nuevo.'};
      if(location.hash === '#acceso') render(); else location.hash = '#acceso';
    });
    window.addEventListener('pageshow', event => { if(event.persisted) render(); });
    render();
    return {refresh:render};
  }
  return {start};
})();

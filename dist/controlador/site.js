// The same router runs with normal adapters or an explicitly injected review adapter.
const SiteController = (() => {
  function start({authService = AuthService, appService = AppService, config = AuthConfig, assets = '', canEnter = () => true} = {}) {
    const sections = ['inicio','el-proyecto','prototipo','como-funciona'];
    const app = document.getElementById('app');
    let current = {}, controller = null, authContext = {};
    function routeFromHash() {
      const [path, query = ''] = location.hash.slice(1).split('?');
      const [part, encodedDetail] = path.split('/');
      let detail;
      try { detail = decodeURIComponent(encodedDetail || ''); } catch { detail = ''; }
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
      if(AppModel.destinations.some(item => item.id === part)) return {screen:part,detail};
      return {screen:'inicio',anchor:sections.includes(part) ? part : null};
    }
    function render() {
      let route = routeFromHash();
      if(AppModel.destinations.some(item => item.id === route.screen) && !canEnter()) {
        history.replaceState(null,'',location.pathname + location.search + '#acceso');
        route = {screen:'acceso'};
      }
      const isPrivate = AppModel.destinations.some(item => item.id === route.screen);
      const changed = route.screen !== current.screen || route.detail !== current.detail;
      controller?.dispose();
      controller = null;
      current = route;
      document.body.dataset.screen = route.screen;
      document.body.dataset.private = String(isPrivate);
      if(AuthModel.screens.includes(route.screen)) {
        document.title = AuthViews.title(route.screen) + ' · El Chilito';
        controller = AuthController.mount(route.screen, {
          root:app, service:authService, config, assets, context:authContext,
          onNavigate(screen, context) { authContext = context; location.hash = '#' + screen; },
          onSessionConfirmed() { authContext = {}; location.hash = '#huerto'; }
        });
        delete authContext.resetToken;
      } else if(isPrivate) {
        authContext = {};
        document.title = (route.screen === 'cuenta' && route.detail === 'contrasena' ? 'Cambiar contraseña' : route.screen === 'avisos' && route.detail ? 'Detalle del aviso' : AppModel.destinations.find(item=>item.id===route.screen).label) + ' · El Chilito';
        controller = AppController.mount(route, {root:app,service:appService,authService,config,onLogout() {location.hash = '#acceso';}});
      } else {
        authContext = {};
        document.title = 'Tu huerto de habanero, dentro de casa · El Chilito';
        app.innerHTML = landing(assets);
      }
      window.bindNavigation();
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
    window.addEventListener('pagehide', () => controller?.dispose());
    window.addEventListener('pageshow', event => { if(event.persisted) render(); });
    render();
    return {refresh:render};
  }
  return {start};
})();

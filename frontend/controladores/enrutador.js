// CONTROLADOR · Enrutador: navegación entre pantallas y comprobación de sesión. Se carga el último y arranca la página.
// Define: SiteController.

// Un solo enrutador, con comprobación de sesión confirmada por el servidor.
const SiteController = (() => {
  function start({authService = AuthService, appService = AppService, config = AuthConfig, assets = '', review = false, canEnter = options => authService.restore(options)} = {}) {
    const sections = ['inicio','el-proyecto','prototipo','consiguelo','como-funciona'];
    const app = document.getElementById('app');
    let current = {}, controller = null, authContext = {}, renderId = 0, navigationRequest = null, heroShown = false, currentMenuKey = null, legalTarget = '#huerto', legalReminded = false;
    const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const replaceHash = hash => history.replaceState(null,'',location.pathname + location.search + hash);
    // Rutas del huerto: la ficha de planta pide su número (1 a 3); el huerto elegido viaja en ?h=.
    function gardenRoute(detail, extra, query) {
      const gardenId = new URLSearchParams(query).get('h');
      if(detail === 'plantas' && !['1','2','3'].includes(extra)) { replaceHash('#huerto'); return {screen:'huerto',detail:'',gardenId}; }
      // La ficha de planta no muestra el número del huerto: si llega en la dirección, se usa una vez y se quita.
      if(detail === 'plantas' && gardenId) replaceHash(`#huerto/plantas/${extra}`);
      return {screen:'huerto',detail,extra:detail === 'plantas' ? extra : '',gardenId};
    }
    function routeFromHash() {
      const [path, query = ''] = location.hash.slice(1).split('?');
      const [part, encodedDetail, encodedExtra] = path.split('/');
      let detail, extra;
      try { detail = decodeURIComponent(encodedDetail || ''); extra = decodeURIComponent(encodedExtra || ''); } catch { detail = extra = ''; }
      if(part==='admin') {
        const target = AppModel.adminRedirects[detail] || detail;
        return {screen:'admin',detail:AppModel.adminDestinations.some(item=>item.id==='admin/'+target)?target:'flota',extra};
      }
      // La pantalla de solicitudes se retiró: el Aviso explica estos derechos y sus medios.
      if(path === 'derechos-arco') { replaceHash('#privacidad'); return {screen:'privacidad'}; }
      if(part === 'cuenta' && detail === 'seguridad') return {screen:'cuenta',detail:'seguridad',invalidSecurity:path.split('/').length !== 2};
      if(part === 'aceptar-legales') return {screen:'aceptar-legales'};
      if(part === 'huerto' && ['nuevo','vincular','plantas'].includes(detail)) return gardenRoute(detail,extra,query);
      if(part === 'cuenta' && detail === 'huertos') return {screen:'cuenta',detail:'huertos'};
      if(part === 'cuenta' && detail === 'privacidad') {
        if(path.split('/').length !== 2) replaceHash('#cuenta/privacidad');
        return {screen:'cuenta',detail:'privacidad'};
      }
      if(part === 'asistente') { history.replaceState(null,'',location.pathname + location.search + '#huerto'); return {screen:'huerto'}; }
      if(part === 'huerto' && detail === 'avisos') {
        history.replaceState(null,'',location.pathname + location.search + '#avisos');
        return {screen:'avisos',detail:''};
      }
      if(part === 'segundo-paso') return {screen:'segundo-paso'};
      if(path === 'sin-acceso') return {screen:'sin-acceso'};
      if(part === 'restablecer') {
        const token = AuthModel.consumeResetLink(location,history);
        if(token) {
          authContext = {resetToken:token};
        }
      }
      if(AuthModel.screens.includes(part)) return {screen:part};
      if(Object.hasOwn(PrivacyModel.documents, part) && !encodedDetail) return {screen:part};
      if(AppModel.destinations.some(item => item.id === part)) return {screen:part,detail,gardenId:new URLSearchParams(query).get('h')};
      return {screen:'inicio',anchor:sections.includes(part) ? part : null};
    }
    // La sesión conocida evita el parpadeo; la del servidor decide. Quien está en el segundo paso no cuenta.
    async function offerAccount(id) {
      const known = authService.session?.status === 'authenticated';
      if(known) showAccountAccess(app,AppModel.panelHome(authService.session));
      let session;
      try { session = await canEnter({}); } catch { return; }
      if(id !== renderId) return;
      if(session?.status === 'authenticated') showAccountAccess(app,AppModel.panelHome(session));
      else if(known) render();
    }
    async function leaveAccessScreen(id) {
      let session;
      try { session = await canEnter({}); } catch { return; }
      if(id !== renderId || session?.status !== 'authenticated') return;
      replaceHash(AppModel.panelHome(session));
      render();
    }
    async function render() {
      const id = ++renderId;
      navigationRequest?.abort();
      navigationRequest = null;
      SiteViews.busy(app,false);
      let route = routeFromHash();
      const requestedPrivate = AppModel.isPrivate(route.screen) || route.screen === 'aceptar-legales';
      if(requestedPrivate) {
        // Mantiene la última vista autorizada y su navegación mientras se comprueba la siguiente ruta.
        if(!controller?.update || !AppModel.isPrivate(current.screen)) {
          controller?.dispose(); controller = null;
          SiteViews.checking(app);
        }
        SiteViews.busy(app,true);
        const guard = new AbortController();
        navigationRequest = guard;
        const timeout = setTimeout(() => guard.abort(), config.requestTimeoutMs);
        let session;
        try { session = await canEnter({signal:guard.signal}); } catch { session = {status:'unavailable'}; }
        finally {
          clearTimeout(timeout);
          if(id === renderId) { navigationRequest = null; SiteViews.busy(app,false); }
        }
        if(id !== renderId) return;
        const pendingLegal = session?.profile?.pendingLegal?.length > 0;
        const legalExempt = pendingLegal && session?.status === 'authenticated' && AppModel.legalGateExempt(session);
        if(legalExempt && route.screen !== 'aceptar-legales' && !legalReminded) {
          legalReminded = true;
          mostrarAviso('info', 'Tienes textos legales nuevos por aceptar. Puedes hacerlo cuando quieras desde la campana de avisos.');
        }
        if(session?.status === 'authenticated' && route.screen === 'aceptar-legales' && !pendingLegal) {
          replaceHash(AppModel.panelHome(session));
          return render();
        }
        if(session?.status !== 'authenticated') {
          const verifying = session?.status === 'verification-required';
          const destination = session?.status === 'second-step' ? 'segundo-paso' : verifying ? 'verificar' : 'acceso';
          authContext = verifying ? {email:session.email,expiresAt:AuthModel.expiry(session.expiresAt)} : {feedback:session?.status === 'unavailable' ? 'No podemos comprobar tu sesión. Inténtalo de nuevo.' : 'Inicia sesión para continuar.'};
          history.replaceState(null,'',location.pathname + location.search + '#' + destination);
          route = {screen:destination};
        } else if(pendingLegal && !legalExempt) {
          // Con textos nuevos sin aceptar, solo se puede aceptarlos o cerrar sesión.
          if(route.screen !== 'aceptar-legales') legalTarget = location.hash || '#huerto';
          route = {screen:'aceptar-legales'};
          replaceHash('#aceptar-legales');
        } else if((session.role==='admin') !== (route.screen==='admin') && !(session.role==='admin' && ['cuenta','avisos',...(legalExempt ? ['aceptar-legales'] : [])].includes(route.screen))) {
          route=session.role==='admin'?{screen:'admin',detail:AppModel.adminHome(session).split('/')[1]}:{screen:'huerto'};
          history.replaceState(null,'',location.pathname+location.search+'#'+(route.screen==='admin'?'admin/'+route.detail:'huerto'));
        }
        // Sin método fuerte, el servidor niega el panel: se lleva a la pantalla donde activarlo.
        if(session?.status==='authenticated'&&session.profile?.mfaRequired===true&&route.screen==='admin') {
          route={screen:'cuenta',detail:'seguridad',invalidSecurity:false};
          history.replaceState(null,'',location.pathname+location.search+'#cuenta/seguridad');
        }
        if(session?.status==='authenticated'&&route.screen==='admin'&&!AppModel.allowedAdmin(session).some(item=>item.id==='admin/'+route.detail)) {
          route={screen:'admin',detail:AppModel.adminHome(session).split('/')[1]};
          history.replaceState(null,'',location.pathname+location.search+'#admin/'+route.detail);
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
      const changed = route.screen !== current.screen || route.detail !== current.detail || route.extra !== current.extra || route.invalidSecurity !== current.invalidSecurity;
      const sectionChanged = PrivacyModel.sectionOf(route) !== PrivacyModel.sectionOf(current);
      const stayOnLanding = route.screen === 'inicio' && current.screen === 'inicio' && Boolean(app.querySelector('.home'));
      // Una nueva respuesta de sesión puede cambiar los destinos: reconstruir también el menú.
      const menuKey = isPrivate ? JSON.stringify([authService.session?.role,AppModel.allowedAdmin(authService.session).map(item=>item.id)]) : null;
      const reuseShell = isPrivate && menuKey === currentMenuKey && (route.screen==='admin')===(current.screen==='admin') && Boolean(controller?.update) && AppModel.isPrivate(current.screen);
      if(!reuseShell) { controller?.dispose(); controller = null; }
      const fromAccessScreen = AuthModel.screens.includes(current.screen);
      current = route;
      currentMenuKey = menuKey;
      SiteViews.screen(app,{screen:route.screen,isPrivate,admin:isPrivate && authService.session?.role==='admin'});
      if(route.screen === 'segundo-paso') {
        authContext = {};
        SiteViews.title('Confirma tu acceso');
        controller = SecondStepController.mount({root:app,assets,async onDone() { const session=await authService.restore(); CookieController.refresh(); location.hash=session.role==='admin'?(session.profile?.mfaRequired?'#cuenta/seguridad':'#'+AppModel.adminHome(session)):'#huerto'; },onCancel() { location.hash='#acceso'; }});
      } else if(AuthModel.screens.includes(route.screen)) {
        SiteViews.title(AuthViews.title(route.screen));
        controller = AuthController.mount(route.screen, {
          root:app, service:authService, config, assets, context:authContext, review,
          onNavigate(screen, context) { authContext = context; location.hash = '#' + screen; },
          async onSessionConfirmed() { authContext = {}; const session=await authService.restore(); CookieController.refresh(); location.hash=session.role==='admin'?'#'+AppModel.adminHome(session):'#huerto'; }
        });
        delete authContext.resetToken;
        // Entre pantallas de acceso el panel de la foto no cambia: solo se anima al llegar.
        if(!fromAccessScreen && !reducedMotion()) SiteViews.revealHeading(app,'.auth-quote h2');
        if(['acceso','registro'].includes(route.screen)) leaveAccessScreen(id);
      } else if(route.screen === 'aceptar-legales') {
        authContext = {};
        SiteViews.title('Actualizamos nuestros documentos');
        controller = LegalAcceptController.mount({root:app,assets,pending:authService.session.profile.pendingLegal,
          async onDone() { await authService.restore(); CookieController.refresh(); location.hash = legalTarget; },
          async onLogout() { await authService.logout(); CookieController.refresh(); location.hash = '#acceso'; }});
      } else if(route.screen === 'sin-acceso') {
        authContext = {};
        SiteViews.title('Sin acceso a tu segundo paso');
        const contact = ChilitoHTTP.configuration?.supportContact;
        SiteViews.accessHelp(app,assets,contact ? MfaService.supportContact(contact) : null);
      } else if(Object.hasOwn(PrivacyModel.documents, route.screen)) {
        authContext = {};
        const legalDocument = PrivacyModel.documents[route.screen];
        SiteViews.title(legalDocument.title);
        const legalText = SiteViews.legal(app, legalDocument, route.screen);
        PrivacyData.document(route.screen).then(result => { if(id === renderId) LegalViews.fill(legalText,result); });
        offerAccount(id);
      } else if(isPrivate) {
        authContext = {};
        let title = route.screen==='admin' ? AppModel.adminDestinations.find(item=>item.id==='admin/'+route.detail).label : route.screen === 'cuenta' && route.detail === 'contrasena' ? 'Cambiar contraseña' : route.screen === 'avisos' && route.detail ? 'Detalle del aviso' : AppModel.destinations.find(item=>item.id===route.screen).label;
        if(route.screen === 'huerto') title = {nuevo:'Crear huerto',vincular:'Vincular equipo',plantas:'Ficha de planta'}[route.detail] || title;
        if(route.detail === 'huertos') title = 'Mis huertos';
        if(route.detail === 'privacidad') title = 'Privacidad';
        if(route.detail === 'seguridad') title = route.invalidSecurity?'Página no disponible':'Seguridad';
        SiteViews.title(title);
        if(reuseShell) controller.update(route);
        else controller = AppController.mount(route, {root:app,service:appService,authService,config,review,onLogout() { CookieController.refresh(); location.hash = '#acceso'; }});
      } else {
        authContext = {};
        SiteViews.title('Tu huerto de habanero, dentro de casa');
        // Entre secciones de la portada no se reconstruye: el indicador del menú debe poder deslizarse.
        if(!stayOnLanding) {
          SiteViews.landing(app,assets);
          ContactController.mount(app,config);
          offerAccount(id);
          if(!heroShown && !route.anchor && !reducedMotion()) SiteViews.revealHeading(app,'.hero h1');
          heroShown = true;
        }
      }
      if(!reuseShell && !stayOnLanding) window.bindNavigation();
      if(sectionChanged) CookieController.visit(route);
      if(changed) { SiteViews.toTop(); SiteViews.focusMain({preventScroll:true}); }
      if(route.anchor && route.anchor !== 'inicio') requestAnimationFrame(() => SiteViews.focusAnchor(route.anchor));
      else if(route.screen === 'inicio') SiteViews.toTop();
    }
    document.querySelector('.skip-link')?.addEventListener('click', event => {
      event.preventDefault(); SiteViews.focusMain();
    });
    // Reglas de los campos (filtro de teclado y pegado, mensajes en línea) para toda la aplicación.
    CamposVista.instalar(document);
    window.addEventListener('hashchange', render);
    window.addEventListener('pagehide', () => { renderId++; navigationRequest?.abort(); controller?.dispose(); controller = null; });
    ChilitoHTTP.onSessionExpired(() => {
      renderId++; navigationRequest?.abort();
      authService.forgetSession();
      CookieController.refresh();
      authContext = {feedback:'Tu sesión ha vencido. Inicia sesión de nuevo.'};
      if(location.hash === '#acceso') render(); else location.hash = '#acceso';
    });
    window.addEventListener('pageshow', event => { if(event.persisted) render(); });
    render();
    return {refresh:render};
  }
  return {start};
})();

// Única composición activa: sesión real del navegador, sin adaptadores de desarrollo inyectados.
(async () => {
  let config = AuthConfig;
  try {
    const policy = await ChilitoHTTP.configure(AbortSignal.timeout(10000));
    config = Object.freeze({registrationAllowed:policy.registrationAllowed,password:policy.password,code:policy.code,requestTimeoutMs:20000});
  } catch { /* Si el servidor no responde, cada acción sigue fallando por el lado seguro (se niega). */ }
  SiteController.start({config,canEnter:options => AuthService.restore(options)});
  CookieController.start();
})();

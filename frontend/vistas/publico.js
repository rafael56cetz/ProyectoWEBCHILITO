// VISTA · Público: portada, encabezado y pie, formulario de preguntas, textos legales y aviso de cookies.
// Define: SiteViews, ContactViews, LegalViews, CookieViews y las piezas de la portada.

// ── Pagina publica ──
const badge=(text,type='neutral',name)=>`<span class="badge ${type}">${name?icon(name):''}${text}</span>`;
const brandLogoBadge = `<span class="brand-logo-badge" aria-hidden="true"><svg viewBox="0 0 64 64" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="leafGlass" x1="12" y1="10" x2="52" y2="54" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#9BE3B1" stop-opacity="0.92" /><stop offset="100%" stop-color="#3E7B52" stop-opacity="0.78" /></linearGradient><linearGradient id="habaneroGrad" x1="32" y1="22" x2="32" y2="45" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FF9436" /><stop offset="55%" stop-color="#F25C19" /><stop offset="100%" stop-color="#C83506" /></linearGradient><filter id="habaneroGlow" x="-25%" y="-25%" width="150%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#F25C19" flood-opacity="0.45" /></filter></defs><path d="M31 9C23 14 17 23 17 31C23 28 28 21 31 9Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.55)" stroke-width="1.1" stroke-linejoin="round" /><path d="M33 9C41 14 47 23 47 31C41 28 36 21 33 9Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.55)" stroke-width="1.1" stroke-linejoin="round" /><path d="M12 49C13 39 18 33 25 32C24 40 19 46 12 49Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.5)" stroke-width="1.1" stroke-linejoin="round" /><path d="M52 49C51 39 46 33 39 32C40 40 45 46 52 49Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.5)" stroke-width="1.1" stroke-linejoin="round" /><path d="M14 51C21 47 27 47 31 51C25 53 19 53 14 51Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.45)" stroke-width="1" stroke-linejoin="round" /><path d="M50 51C43 47 37 47 33 51C39 53 45 53 50 51Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.45)" stroke-width="1" stroke-linejoin="round" /><path d="M32 25C32 21.5 33.8 19.2 35.5 18.5" stroke="#B6E8A7" stroke-width="2" stroke-linecap="round" /><path filter="url(#habaneroGlow)" d="M32 25.2C27.2 24.6 24.5 27.8 25 32.8C25.4 37.2 28.5 41.8 32 43.8C35.5 41.8 38.6 37.2 39 32.8C39.5 27.8 36.8 24.6 32 25.2Z" fill="url(#habaneroGrad)" stroke="rgba(255,220,180,0.55)" stroke-width="0.9" /><path d="M32 25.8C29.8 29.5 29.8 37.5 32 43.2" stroke="rgba(255,255,255,0.28)" stroke-width="1" stroke-linecap="round" /><path d="M32 25.8C34.2 29.5 34.2 37.5 32 43.2" stroke="rgba(140,30,0,0.28)" stroke-width="1" stroke-linecap="round" /><circle cx="32" cy="25.2" r="1.6" fill="#FFF3B0" /></svg></span>`;
const brand=(href='#inicio', label='El Chilito, inicio', extra='')=>`<a class="brand brand-mark ${extra}" href="${href}" aria-label="${label}">${brandLogoBadge}<span class="brand-name">El Chilito</span></a>`;
// Con sesión completa, «Iniciar sesión» se convierte en el acceso al panel de esa sesión.
const showAccountAccess = (root, panel) => root.querySelectorAll('a[href="#acceso"]').forEach(link => {
  link.setAttribute('href',panel);
  if(link.closest('.header-actions')) {
    link.innerHTML = icon('user');
    link.classList.add('account-icon-link');
    link.setAttribute('aria-label','Ir a mi panel');
    link.title = 'Ir a mi panel';
  } else if(link.matches('.public-menu-login')) link.lastElementChild.textContent = 'Ir a mi panel';
  else link.textContent = 'Ir a mi panel';
});
// Entrada de un título letra por letra. Su texto es fijo y al terminar se devuelve intacto.
function revealTitle(title) {
  const lines = [...title.children];
  const originals = lines.map(line => line.textContent);
  title.setAttribute('aria-label',originals.join(' '));
  let index = 0, last = null;
  lines.forEach(line => {
    line.setAttribute('aria-hidden','true');
    const words = line.textContent.split(' ');
    line.replaceChildren();
    words.forEach((text,position) => {
      if(position) line.append(' ');
      const word = Object.assign(document.createElement('span'),{className:'reveal-word'});
      for(const character of text) {
        last = Object.assign(document.createElement('span'),{className:'reveal-letter',textContent:character});
        last.style.setProperty('--letter',index++);
        word.append(last);
      }
      line.append(word);
    });
  });
  title.classList.add('is-revealing');
  last.addEventListener('animationend',() => {
    lines.forEach((line,position) => { line.textContent = originals[position]; line.removeAttribute('aria-hidden'); });
    title.removeAttribute('aria-label');
    title.classList.remove('is-revealing');
  },{once:true});
}
const publicFooter = () => `<footer class="site-footer">
  <div class="site-footer__container">
    <div class="site-footer__grid">
      <!-- Columna 1: Marca y Propósito -->
      <div class="site-footer__col">
        <a href="#inicio" class="site-footer__brand brand-mark" aria-label="El Chilito, inicio">${brandLogoBadge}<span class="brand-name">El Chilito</span></a>
        <p class="site-footer__desc">
          Estación doméstica inteligente para el cultivo interior de chile habanero (Capsicum chinense), con riego automatizado por tiempos, iluminación LED programada y monitoreo IoT.
        </p>
        <div class="site-footer__tech-pill">
          Control local ESP32 · 5 sensores · Asistente IA previsto
        </div>
      </div>

      <!-- Columna 2: Navegación de Retorno (Doormat Navigation) -->
      <div class="site-footer__col">
        <h4 class="site-footer__heading">Navegación</h4>
        <ul class="site-footer__list">
          <li><a href="#inicio" class="site-footer__link">Inicio</a></li>
          <li><a href="#el-proyecto" class="site-footer__link">El proyecto</a></li>
          <li><a href="#prototipo" class="site-footer__link">Conoce el prototipo</a></li>
          <li><a href="#como-funciona" class="site-footer__link">El cuidado del huerto</a></li>
        </ul>
      </div>

      <!-- Columna 3: Plataforma y Legal -->
      <div class="site-footer__col">
        <h4 class="site-footer__heading">Plataforma y Legal</h4>
        <ul class="site-footer__list">
          <li><a href="#acceso" class="site-footer__link">Iniciar sesión en el panel</a></li>
          <li><a href="#terminos" class="site-footer__link">Términos y condiciones</a></li>
          <li><a href="#privacidad" class="site-footer__link">Aviso de privacidad</a></li>
          <li><a href="#cookies" class="site-footer__link">Política de cookies</a></li>
          <li><button type="button" class="site-footer__link" data-cookie-settings>Configurar cookies</button></li>
        </ul>
      </div>
    </div>

    <!-- Barra Inferior de Cierre -->
    <div class="site-footer__bottom">
      <span>© 2026 El Chilito. Todos los derechos reservados.</span>
      <div class="site-footer__legal-links">
        <span>Yucatán, México</span>
        <a href="#terminos" class="site-footer__link">Términos y condiciones</a>
        <a href="#privacidad" class="site-footer__link">Privacidad</a>
      </div>
    </div>
  </div>
</footer>`;
const menuToggle = id => `<button class="button compact btn-liquid-nav nav-toggle public-menu-toggle" type="button" data-nav-toggle aria-controls="${id}" aria-expanded="false" aria-label="Abrir menú de navegación"><span class="public-menu-open-icon">${icon('menu')}</span><span class="public-menu-close-icon">${icon('close')}</span><span>Menú</span></button>`;
function siteHeader({ navigation = '', action = '', brandHref = '#inicio', brandLabel = 'El Chilito, inicio', panelId = '', extra = '' }) {
  return `<header class="site-header ${extra}"><div class="header-inner container">${brand(brandHref, brandLabel)}${navigation}<div class="header-actions">${action}${panelId ? menuToggle(panelId) : ''}</div></div></header>`;
}
// Encabezado de la portada. Las páginas legales usan el mismo para no cambiar de navegación.
const publicHeader = () => siteHeader({navigation:`<nav class="header-nav" id="public-navigation" aria-label="Navegación principal"><span class="nav-lamp" aria-hidden="true"></span><a class="button compact btn-liquid-nav" href="#inicio" data-section=".hero"><span class="public-menu-icon">${icon('home')}</span><span>Inicio</span></a><a class="button compact btn-liquid-nav" href="#el-proyecto" data-section="#el-proyecto"><span class="public-menu-icon">${icon('leaf')}</span><span>El proyecto</span></a><a class="button compact btn-liquid-nav" href="#prototipo" data-section="#prototipo"><span class="public-menu-icon">${icon('grid')}</span><span>Ver prototipo</span></a><a class="button compact btn-liquid-nav" href="#consiguelo" data-section="#consiguelo"><span class="public-menu-icon">${icon('sparkle')}</span><span>Consíguelo</span></a><a class="button compact btn-liquid-nav" href="#como-funciona" data-section="#como-funciona"><span class="public-menu-icon">${icon('info')}</span><span>Cómo funciona</span></a><a class="button compact btn-liquid-nav public-menu-login" href="#acceso"><span class="public-menu-icon">${icon('user')}</span><span>Iniciar sesión</span></a></nav>`,action:'<a class="button compact btn-liquid-primary public-header-login" href="#acceso">Iniciar sesión</a>',panelId:'public-navigation',extra:'public-header header-glass-dark'});
function landing(assets = ''){return `
<div class="home">
  ${publicHeader()}
  <div class="public-menu-shade" data-public-menu-shade aria-hidden="true" hidden></div>
  <section class="hero" aria-labelledby="hero-title"><img class="hero-photo" src="${assets}vistas/imagenes/habanero-fondo.webp" alt="Ambientación ilustrativa: hojas de habanero y frutos anaranjados junto a una luz suave de interior." width="1896" height="830" fetchpriority="high"><div class="hero-shade" aria-hidden="true"></div>
    <main class="hero-content container" id="contenido" tabindex="-1"><div class="hero-text"><h1 id="hero-title"><span>Tu huerto de</span><span>habanero,</span><span>dentro de casa.</span></h1><p class="hero-description">Un huerto urbano para interiores que reúne tres plantas de habanero y una forma más cercana de cuidar lo que cultivas.</p></div></main>
  </section>
  <!-- SECCIÓN 1: EL PROYECTO -->
  <section class="project-section" id="el-proyecto" aria-labelledby="project-title">
    <div class="container">
      <div class="project-header-grid">
        <div class="project-header-left">
          <h2 id="project-title">Un pequeño huerto.<br>Una nueva conexión.</h2>
        </div>
        <div class="project-header-right">
          <h3>Cultivar habanero en casa, sin depender de un patio ni de tu agenda.</h3>
          <p>Falta de espacio exterior, lluvias intensas o poco tiempo libre suelen impedir tener un cultivo propio. El Chilito reúne tres plantas de chile habanero (<em>Capsicum chinense</em>) en una estación interior de madera con drenaje seguro y bandeja recolectora que protege la oxigenación de las raíces.</p>
          <p>El sistema automatiza el riego por tiempos programados y los ciclos de iluminación LED, mientras sus sensores monitorean el cultivo y te informan desde tu celular o computadora.</p>
        </div>
      </div>
      <div class="bento-stats-grid">
        <article class="bento-stat-card">
          <div class="bento-stat-number">03</div>
          <h4>Plantas en producción</h4>
          <p>Cultivo en sustrato y composta con drenaje independiente y bandeja recolectora para evitar saturación en las raíces.</p>
        </article>
        <article class="bento-stat-card">
          <div class="bento-stat-number">05</div>
          <h4>Sensores en tiempo real</h4>
          <p>Tres sensores de humedad en sustrato, un sensor de clima ambiental y un detector de nivel de agua conectados vía ESP32.</p>
        </article>
        <article class="bento-stat-card">
          <div class="bento-stat-number">100%</div>
          <h4>Riego y luz por tiempos</h4>
          <p>Ciclos automáticos programados con bloqueo inteligente de la bomba cuando el depósito requiere recarga de agua.</p>
        </article>
      </div>
    </div>
  </section>

  <!-- SECCIÓN 2: VITRINA DEL PROTOTIPO -->
  <section class="prototype-section" id="prototipo" aria-labelledby="prototype-title">
    <div class="container">
      <div class="prototype-section-heading">
        <div>
          <h2 id="prototype-title">Conoce el prototipo</h2>
        </div>
        <p class="prototype-subtitle">Tres plantas. Un mismo espacio autónomo.</p>
      </div>
      <div class="prototype-bento-showcase">
        <div class="prototype-visual-wrap">
          <img src="${assets}vistas/imagenes/prototipo-estacion.jpg" width="1024" height="1024" loading="lazy" alt="Prototipo del huerto urbano inteligente El Chilito en el hogar">
        </div>
        <div class="anatomy-cards-column">
          <article class="anatomy-glass-card">
            <div class="anatomy-card-header">
              <span class="anatomy-badge">01</span>
              <h4>Iluminación LED programada</h4>
            </div>
            <p>Cobertura superior con ciclos automáticos de encendido y apagado y altura ajustable manualmente según el crecimiento.</p>
          </article>
          <article class="anatomy-glass-card">
            <div class="anatomy-card-header">
              <span class="anatomy-badge">02</span>
              <h4>Distribución triangular con drenaje</h4>
            </div>
            <p>Tres compartimentos con sustrato y composta que evitan el estancamiento de agua y cuidan la salud de la raíz.</p>
          </article>
          <article class="anatomy-glass-card">
            <div class="anatomy-card-header">
              <span class="anatomy-badge">03</span>
              <h4>Controlador IoT ESP32</h4>
            </div>
            <p>Módulo lateral con conectividad Wi-Fi que ejecuta las reglas locales de riego y envía lecturas cifradas a la plataforma web.</p>
          </article>
          <article class="anatomy-glass-card">
            <div class="anatomy-card-header">
              <span class="anatomy-badge">04</span>
              <h4>Depósito frontal con protección</h4>
            </div>
            <p>Reserva inferior accesible de frente con sensor de nivel bajo que detiene la bomba automáticamente para proteger el equipo.</p>
          </article>
        </div>
      </div>
    </div>
  </section>

  <!-- CONSÍGUELO: preguntas sobre el producto. Precio y disponibilidad aún sin definir. -->
  <section class="get-section" id="consiguelo" aria-labelledby="get-title">
    <div class="container">
      <div class="get-panel">
        <h2 id="get-title">Sé de los primeros en tener tu Chilito.</h2>
        <p>Será un equipo completo, sin planes ni suscripciones. Pregúntanos por el precio y la disponibilidad, o pide que te avisemos cuando salga la primera versión.</p>
        <button class="button btn-liquid-primary get-open" type="button" data-contact-open>Quiero más información</button>
      </div>
    </div>
  </section>
  ${ContactViews.dialog()}

  <!-- SECCIÓN 3: VIDA REAL + ECOSISTEMA INTELIGENTE -->
  <section class="functions-section" id="como-funciona" aria-labelledby="functions-title">
    <div class="container">
      <div class="lifestyle-bento-banner">
        <div class="lifestyle-content">
          <h2 id="functions-title">El cuidado del huerto, pensado para convivir contigo.</h2>
          <p>Diseñado para integrarse de forma limpia en interiores. Supervisa la humedad del sustrato, la temperatura ambiental y el nivel del depósito desde tu celular o computadora. Más adelante, un asistente de IA generativa ayudará a interpretar las lecturas.</p>
          <a class="button btn-liquid-primary" href="#acceso">Iniciar sesión en el panel</a>
        </div>
        <div class="lifestyle-image-wrap">
          <img src="${assets}vistas/imagenes/el-chilito-convivir.jpg" alt="Huerto urbano inteligente El Chilito conviviendo en el hogar" loading="lazy">
        </div>
      </div>
      <div class="dark-glass-features-grid">
        <article class="dark-glass-feature-card">
          <div class="dark-feature-icon-wrap">${icon('clock')}</div>
          <h4>Riego automatizado por tiempos</h4>
          <p>Ciclos de riego programados desde el depósito inferior con límites seguros de operación y bloqueo automático ante nivel bajo de agua.</p>
        </article>
        <article class="dark-glass-feature-card">
          <div class="dark-feature-icon-wrap">${icon('leaf')}</div>
          <h4>Monitoreo con 5 sensores</h4>
          <p>Tres sensores de humedad en sustrato, un sensor de temperatura y humedad ambiental, y un detector de nivel en el depósito.</p>
        </article>
        <article class="dark-glass-feature-card">
          <div class="dark-feature-icon-wrap">${icon('sparkle')}</div>
          <h4>Asistente de IA generativa <span class="feature-planned">Previsto</span></h4>
          <p>La arquitectura prevista procesa las lecturas en Google Cloud y muestra los resultados en tu dashboard. Aún no está conectado y no controla el dispositivo.</p>
        </article>
        <article class="dark-glass-feature-card">
          <div class="dark-feature-icon-wrap">${icon('shield')}</div>
          <h4>Iluminación LED y control local</h4>
          <p>Fotoperiodos LED programados y operación local continua mediante ESP32 con acceso web protegido y comunicación cifrada.</p>
        </article>
      </div>
    </div>
  </section>
  ${publicFooter()}
</div>`}
function plantDrawing(n){return `<svg class="plant-drawing plant-${n}" viewBox="0 0 90 110" aria-hidden="true"><path d="M45 89V23m0 43L26 48m19 3 19-17" fill="none" stroke="currentColor" stroke-width="2"/><path d="M43 59C26 62 17 50 18 38c14 0 26 7 25 21Zm3-14c0-17 9-26 25-27 1 16-9 27-25 27Zm0-14C34 25 34 12 40 4c11 7 13 17 6 27Z" fill="currentColor"/><path d="M28 83h35l-5 24H33Z" fill="#a68e68"/><ellipse cx="45.5" cy="83" rx="17.5" ry="4" fill="#756040"/><path d="M63 40c-6-5-9 2-6 8s7 7 10 2 1-12-4-10" fill="#da9564"/></svg>`}

// Presentación del enrutador principal: el controlador (enrutador.js) decide la ruta; aquí se pinta.
const SiteViews = Object.freeze({
  busy(app, on) { if(on) app.setAttribute('aria-busy','true'); else app.removeAttribute('aria-busy'); },
  checking(app) { app.innerHTML = AuthViews.sessionChecking(); },
  title(text) { document.title = text + ' · El Chilito'; },
  screen(app, {screen, isPrivate, admin}) {
    document.body.dataset.screen = screen;
    document.body.dataset.private = String(isPrivate);
    document.body.dataset.role = admin ? 'admin' : 'user';
  },
  accessHelp(app, assets, contact) {
    app.innerHTML = AuthViews.layout('Sin acceso a tu segundo paso','Si no tienes tu app, tus llaves ni tus códigos, el equipo puede ayudarte. Cambiar la contraseña no quita este paso.',LegalViews.accessHelp(),assets);
    if(contact) MfaViews.supportContact(app.querySelector('[data-step-contact]'),contact);
  },
  legal(app, legalDocument, screen) {
    app.innerHTML = LegalViews.render(legalDocument, screen);
    return app.querySelector('[data-legal-text]');
  },
  landing(app, assets) { app.innerHTML = landing(assets); },
  revealHeading(app, selector) { revealTitle(app.querySelector(selector)); },
  toTop() { window.scrollTo(0,0); },
  focusMain({preventScroll = false} = {}) { document.getElementById('contenido')?.focus({preventScroll}); },
  focusAnchor(id) {
    const target = document.getElementById(id);
    if(target) { target.tabIndex = -1; target.focus({preventScroll:true}); target.scrollIntoView(); }
  }
});

// ── Contacto ──
const ContactViews = Object.freeze({
  dialog() {
    return `<dialog class="contact-screen" data-contact aria-labelledby="contact-title">
      <button class="button compact btn-liquid-nav account-icon-link contact-close" type="button" data-contact-close aria-label="Cerrar">${icon('close')}</button>
      <div class="contact-layout">
        <div class="contact-copy">
          <h2 id="contact-title">Cuéntanos qué quieres saber</h2>
          <p>Escríbenos sobre El Chilito y te responderemos a tu correo.</p>
          <ul><li>${icon('check')}<span>Pregunta por el precio y la disponibilidad.</span></li>
          <li>${icon('check')}<span>Pide que te avisemos cuando salga la primera versión.</span></li></ul>
          <p class="contact-direct" data-contact-direct hidden></p>
        </div>
        <form class="contact-form" data-contact-form novalidate>
          <label><span>Nombre <small>(opcional)</small></span><input name="name" maxlength="100" autocomplete="name"></label>
          <label>Correo electrónico<input name="email" type="email" maxlength="254" autocomplete="email" required></label>
          <label>Tu mensaje<textarea name="message" rows="5" maxlength="2000" required></textarea></label>
          <label class="contact-trap" aria-hidden="true">Sitio web<input name="website" tabindex="-1" autocomplete="off"></label>
          <p class="contact-note">Usaremos tu correo solo para responderte. Consulta el <a href="#privacidad">Aviso de privacidad</a>.</p>
          <p class="contact-status" data-contact-status role="status" hidden></p>
          <button class="button btn-liquid-primary" type="submit">Enviar mensaje</button>
        </form>
      </div>
    </dialog>`;
  },
  // Presentación del diálogo ya insertado: el controlador solo decide cuándo abrir, cerrar o avisar.
  screen(root) {
    const messages = {accepted:'Recibimos tu mensaje. Te responderemos a tu correo.',invalid:'Revisa tu correo y tu mensaje.',limited:'Enviaste varios mensajes seguidos. Inténtalo más tarde.',unavailable:'No se pudo enviar. Inténtalo más tarde o escríbenos por correo.'};
    const dialog = root.querySelector('[data-contact]');
    const trigger = root.querySelector('[data-contact-open]');
    const form = dialog.querySelector('[data-contact-form]');
    const status = dialog.querySelector('[data-contact-status]');
    const submit = form.querySelector('[type=submit]');
    const say = code => { status.textContent = messages[code] || ''; status.hidden = !status.textContent; };
    return {dialog, trigger, form, closeButton: dialog.querySelector('[data-contact-close]'), say,
      showDirect(contact) { if(contact) ContactViews.direct(dialog.querySelector('[data-contact-direct]'), contact); },
      open() {
        const area = trigger.getBoundingClientRect();
        dialog.style.setProperty('--from',`inset(${area.top}px ${innerWidth-area.right}px ${innerHeight-area.bottom}px ${area.left}px round 999px)`);
        say('');
        dialog.showModal();
      },
      close() {
        if(!dialog.open) return;
        if(matchMedia('(prefers-reduced-motion: reduce)').matches) { dialog.close(); return; }
        dialog.classList.add('is-closing');
        dialog.addEventListener('animationend',() => dialog.close(),{once:true});
      },
      closeNow() { dialog.close(); },
      // El navegador puede cerrar sin esperar la animación: el estado se restablece siempre aquí.
      closed() { dialog.classList.remove('is-closing'); trigger.focus({preventScroll:true}); },
      isBusy: () => submit.disabled,
      busy(on) { submit.disabled = on; submit.textContent = on ? 'Enviando…' : 'Enviar mensaje'; },
      reset() { form.reset(); }};
  },
  direct(host, contact) {
    const link = Object.assign(document.createElement('a'),{href:'mailto:'+contact,textContent:contact});
    host.replaceChildren('También puedes escribirnos a ',link,'.');
    host.hidden = false;
  }
});

// ── Legales ──
const LegalViews = Object.freeze({
  // El servidor limita el HTML editable. El texto anterior sigue siendo compatible.
  fill(host, result) {
    if(!host) return;
    host.replaceChildren();
    host.removeAttribute('role');
    if(result.status !== 'ready') {
      const message = document.createElement('p');
      message.textContent = 'No se pudo cargar el documento. Inténtalo de nuevo.';
      host.append(message);
      return;
    }
    // El servidor ya sanea el HTML con su lista blanca; el navegador solo lo coloca.
    const template = document.createElement('template');
    template.innerHTML = typeof result.html === 'string' ? result.html : '';
    const nodes = template.content.textContent.trim() ? [...template.content.childNodes] : [];
    // Archivo vacío: se dice que está en redacción, nunca se inventa texto.
    const pending = !nodes.length ? '[PENDIENTE: documento en redacción]' :
      !result.registered ? '[PENDIENTE: borrador en edición, sin versión registrada]' : '';
    if(pending) {
      const message = document.createElement('p');
      message.textContent = pending;
      nodes.unshift(message);
    }
    for(const node of nodes) {
      if(node.nodeType === 1 && node.textContent.startsWith('[PENDIENTE')) node.classList.add('legal-pending');
      host.append(node);
    }
  },
  // Pasos para quien perdió su app, sus llaves y sus códigos. El contacto se añade por separado.
  accessHelp() {
    const steps = ['Escribe a soporte desde el correo de tu cuenta. Así podemos saber que el mensaje viene de ti.',
      'Dinos qué perdiste y la fecha aproximada en que te registraste. Nunca envíes tu contraseña ni códigos.',
      'Comprobaremos tu identidad. Si coincide, retiraremos los métodos de tu cuenta y te avisaremos.',
      'Entra con tu correo y tu contraseña: recibirás un código por correo. Después vuelve a activar tu método en Seguridad.'];
    return `<ol class="access-help-steps">${steps.map(step => `<li>${escaparHTML(step)}</li>`).join('')}</ol>
      <p class="access-help-contact" data-step-contact hidden></p>
      <a class="button btn-liquid-brand full" href="#segundo-paso">Volver al inicio de sesión</a>`;
  },
  // Página de documento: título, entradilla y texto a lo ancho de lectura, sin fichas.
  // Al final, enlaces de texto a los demás documentos; no hay «Volver»: el encabezado es el de la portada y ya lleva a ella o al panel.
  render(document, route) {
    const title = document.title;
    const leads = {privacidad:'Qué datos personales tratamos, para qué los usamos y cómo puedes ejercer tus derechos.',
      terminos:'Condiciones de uso de la plataforma El Chilito y de sus servicios.',
      cookies:'Qué cookies usamos, para qué sirven y cómo cambiar tu elección.'};
    const related = Object.entries(PrivacyModel.documents).filter(([id]) => id !== route)
      .map(([id,item]) => `<li><a href="#${id}">${escaparHTML(item.title)}</a></li>`).join('');
    return `${publicHeader()}
      <main class="legal-page" id="contenido" tabindex="-1">
        <div class="legal-hero"><div class="legal-wrap">
          <p class="legal-eyebrow">Documentos legales · El Chilito</p>
          <h1>${escaparHTML(title)}</h1>
          <p class="legal-lead">${escaparHTML(leads[route] || '')}</p>
        </div></div>
        <div class="legal-wrap legal-body">
          <article class="legal-prose" aria-label="${escaparHTML(title)}"><div data-legal-text role="status"><p>Cargando documento…</p></div></article>
          <nav class="legal-related" aria-labelledby="legal-related-title">
            <h2 id="legal-related-title">Documentos relacionados</h2>
            <ul>${related}${route === 'cookies' ? '<li><button class="legal-link" type="button" data-cookie-settings>Configurar cookies</button></li>' : ''}</ul>
          </nav>
        </div>
      </main>${publicFooter()}`;
  }
});

// ── Cookies ──
// Aviso de cookies, ventana de preferencias y confirmación. Solo contenido fijo: ningún dato del servidor.
const CookieViews = (() => {
  const button = (action,label,type='button') => `<button class="cookies-boton" type="${type}"${action ? ` data-cookies-accion="${action}"` : ''}>${label}</button>`;
  const error = () => '<p class="cookies-error" data-cookies-error role="alert" hidden></p>';
  const markup = `<div class="cookies-aviso" data-cookies-aviso role="region" aria-labelledby="cookies-aviso-titulo" hidden>
      <div class="cookies-aviso-texto">
        <h2 id="cookies-aviso-titulo">Tu privacidad y las cookies</h2>
        <p>Usamos cookies necesarias para mantener tu sesión, proteger tus acciones y recordar tus preferencias. Si lo autorizas, también utilizaremos cookies para obtener estadísticas internas de navegación y mejorar la web. Puedes rechazar estas estadísticas y seguir utilizando el sitio.</p>
        <a class="cookies-enlace" href="#cookies">Leer la política de cookies</a>
        ${error()}
      </div>
      <div class="cookies-acciones">${button('aceptar','Aceptar')}${button('rechazar','Rechazar')}${button('configurar','Configurar')}</div>
    </div>
    <dialog class="cookies-panel" data-cookies-panel aria-labelledby="cookies-panel-titulo" aria-describedby="cookies-panel-texto">
      <form data-cookies-form>
        <h2 id="cookies-panel-titulo">Configurar cookies</h2>
        <p id="cookies-panel-texto">Elige si quieres permitir las estadísticas opcionales. Puedes cambiar tu decisión cuando quieras desde «Configurar cookies», al pie de la página.</p>
        <button class="cookies-cerrar" type="button" data-cookies-accion="cerrar" aria-label="Cerrar sin guardar">${icon('close')}</button>
        <section class="cookies-categoria" aria-labelledby="cookies-necesarias">
          <div class="cookies-categoria-fila">
            <div><h3 id="cookies-necesarias">Cookies necesarias</h3>
            <p>Permiten mantener tu sesión, proteger las solicitudes que haces a la web y recordar tu elección de cookies.</p></div>
            <span class="cookies-fijo">Siempre activas</span>
          </div>
          <details class="cookies-detalle"><summary>Ver detalles</summary><ul>
            <li><code>sessionid</code>: mantiene la sesión iniciada.</li>
            <li><code>csrftoken</code>: ayuda a proteger tus acciones frente a solicitudes enviadas desde otros sitios.</li>
            <li><code>chilito_preferencia</code>: recuerda tu elección de cookies durante un máximo de 180 días.</li>
          </ul></details>
        </section>
        <section class="cookies-categoria" aria-labelledby="cookies-estadisticas">
          <div class="cookies-categoria-fila">
            <div><h3 id="cookies-estadisticas">Estadísticas opcionales</h3>
            <p id="cookies-estadisticas-texto">Nos ayudan a conocer cuántas visitas reciben las secciones para mejorar la web. Puedes desactivarlas sin perder acceso a tu cuenta ni a tu huerto.</p></div>
            <label class="cookies-interruptor"><input type="checkbox" role="switch" name="statistics" aria-labelledby="cookies-estadisticas" aria-describedby="cookies-estadisticas-texto"><span></span></label>
          </div>
          <details class="cookies-detalle"><summary>Ver detalles</summary>
            <p>Utilizan la cookie <code>chilito_estadistica</code>, con una duración máxima de 30 minutos. Los totales de visitas no incluyen tu nombre ni tu correo electrónico.</p>
          </details>
        </section>
        ${error()}
        <div class="cookies-acciones cookies-acciones--panel">${button('','Guardar preferencias','submit')}${button('rechazar','Rechazar estadísticas')}</div>
      </form>
    </dialog>`;
  return Object.freeze({
    root() {
      const node = document.createElement('div');
      node.className = 'cookies';
      node.innerHTML = markup;
      return node;
    },
    busy(root, busy) {
      root.toggleAttribute('aria-busy',busy);
      root.querySelectorAll('button,input').forEach(control => { control.disabled = busy; });
    },
    // Inserta el aviso en la página y devuelve sus operaciones de presentación.
    screen() {
      const root = CookieViews.root();
      const banner = root.querySelector('[data-cookies-aviso]');
      const dialog = root.querySelector('[data-cookies-panel]');
      const form = root.querySelector('[data-cookies-form]');
      document.body.append(root);
      // Un aviso fijo no debe tapar el elemento que recibe el foco.
      const reserveSpace = () => { document.documentElement.style.scrollPaddingBottom = banner.hidden ? '' : `${banner.offsetHeight + 32}px`; };
      const showError = (failed = false) => {
        root.querySelectorAll('[data-cookies-error]').forEach(node => {
          node.textContent = failed ? 'No pudimos guardar tu elección. Inténtalo de nuevo' : '';
          node.hidden = !failed;
        });
      };
      return {form, reserveSpace, showError,
        busy: on => CookieViews.busy(root,on),
        banner(visible) { banner.hidden = !visible; reserveSpace(); },
        statisticsChoice: () => form.elements.statistics.checked,
        openPreferences(statistics) {
          form.elements.statistics.checked = statistics;
          showError();
          if(!dialog.open) dialog.showModal();
        },
        closePreferences() { if(dialog.open) dialog.close(); },
        saved() {
          const aviso = mostrarAviso('exito','Preferencias guardadas');
          // Si el foco estaba en el aviso que acaba de ocultarse, no se pierde al inicio de la página.
          const active = document.activeElement;
          if(active === document.body || banner.contains(active)) aviso.focus({preventScroll:true});
        }};
    }
  });
})();

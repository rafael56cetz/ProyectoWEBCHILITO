const badge=(text,type='neutral',name)=>`<span class="badge ${type}">${name?icon(name):''}${text}</span>`;
const brandLogoBadge = `<span class="brand-logo-badge" aria-hidden="true"><svg viewBox="0 0 64 64" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="leafGlass" x1="12" y1="10" x2="52" y2="54" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#9BE3B1" stop-opacity="0.92" /><stop offset="100%" stop-color="#3E7B52" stop-opacity="0.78" /></linearGradient><linearGradient id="habaneroGrad" x1="32" y1="22" x2="32" y2="45" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FF9436" /><stop offset="55%" stop-color="#F25C19" /><stop offset="100%" stop-color="#C83506" /></linearGradient><filter id="habaneroGlow" x="-25%" y="-25%" width="150%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#F25C19" flood-opacity="0.45" /></filter></defs><path d="M31 9C23 14 17 23 17 31C23 28 28 21 31 9Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.55)" stroke-width="1.1" stroke-linejoin="round" /><path d="M33 9C41 14 47 23 47 31C41 28 36 21 33 9Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.55)" stroke-width="1.1" stroke-linejoin="round" /><path d="M12 49C13 39 18 33 25 32C24 40 19 46 12 49Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.5)" stroke-width="1.1" stroke-linejoin="round" /><path d="M52 49C51 39 46 33 39 32C40 40 45 46 52 49Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.5)" stroke-width="1.1" stroke-linejoin="round" /><path d="M14 51C21 47 27 47 31 51C25 53 19 53 14 51Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.45)" stroke-width="1" stroke-linejoin="round" /><path d="M50 51C43 47 37 47 33 51C39 53 45 53 50 51Z" fill="url(#leafGlass)" stroke="rgba(255,255,255,0.45)" stroke-width="1" stroke-linejoin="round" /><path d="M32 25C32 21.5 33.8 19.2 35.5 18.5" stroke="#B6E8A7" stroke-width="2" stroke-linecap="round" /><path filter="url(#habaneroGlow)" d="M32 25.2C27.2 24.6 24.5 27.8 25 32.8C25.4 37.2 28.5 41.8 32 43.8C35.5 41.8 38.6 37.2 39 32.8C39.5 27.8 36.8 24.6 32 25.2Z" fill="url(#habaneroGrad)" stroke="rgba(255,220,180,0.55)" stroke-width="0.9" /><path d="M32 25.8C29.8 29.5 29.8 37.5 32 43.2" stroke="rgba(255,255,255,0.28)" stroke-width="1" stroke-linecap="round" /><path d="M32 25.8C34.2 29.5 34.2 37.5 32 43.2" stroke="rgba(140,30,0,0.28)" stroke-width="1" stroke-linecap="round" /><circle cx="32" cy="25.2" r="1.6" fill="#FFF3B0" /></svg></span>`;
const brand=(href='#inicio', label='El Chilito, inicio', extra='')=>`<a class="brand brand-mark ${extra}" href="${href}" aria-label="${label}">${brandLogoBadge}<span class="brand-name">El Chilito</span></a>`;
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
          Control local ESP32 · 5 sensores activos · Asistente IA
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
          <li><a href="#derechos-arco" class="site-footer__link">Derechos ARCO</a></li>
          <li><a href="#seguridad" class="site-footer__link">Seguridad y protección de datos</a></li>
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
const menuToggle = id => `<button class="button compact btn-liquid-nav nav-toggle" type="button" data-nav-toggle aria-controls="${id}" aria-expanded="false">Menú</button>`;
function siteHeader({ navigation = '', action = '', brandHref = '#inicio', brandLabel = 'El Chilito, inicio', panelId = '', extra = '' }) {
  return `<header class="site-header ${extra}"><div class="header-inner container">${brand(brandHref, brandLabel)}${navigation}<div class="header-actions">${action}${panelId ? menuToggle(panelId) : ''}</div></div></header>`;
}
function landing(assets = ''){return `
<div class="home">
  ${siteHeader({navigation:'<nav class="header-nav" id="public-navigation" aria-label="Navegación principal"><a class="button compact btn-liquid-nav" href="#el-proyecto">El proyecto</a><a class="button compact btn-liquid-nav" href="#prototipo">Ver prototipo</a><a class="button compact btn-liquid-nav" href="#como-funciona">Cómo funciona</a></nav>',action:'<a class="button compact btn-liquid-primary" href="#acceso">Iniciar sesión</a>',panelId:'',extra:'public-header header-glass-dark'})}
  <section class="hero" aria-labelledby="hero-title"><img class="hero-photo" src="${assets}vista/img/habanero-editorial.png" alt="Ambientación ilustrativa: hojas de habanero y frutos anaranjados junto a una luz suave de interior." width="1902" height="827" fetchpriority="high"><div class="hero-shade" aria-hidden="true"></div>
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
          <img src="${assets}vista/img/prototipo-estacion.jpg" width="1024" height="1024" loading="lazy" alt="Prototipo del huerto urbano inteligente El Chilito en el hogar">
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

  <!-- SECCIÓN 3: VIDA REAL + ECOSISTEMA INTELIGENTE -->
  <section class="functions-section" id="como-funciona" aria-labelledby="functions-title">
    <div class="container">
      <div class="lifestyle-bento-banner">
        <div class="lifestyle-content">
          <h2 id="functions-title">El cuidado del huerto, pensado para convivir contigo.</h2>
          <p>Diseñado para integrarse de forma limpia en interiores. Supervisa la humedad del sustrato, la temperatura ambiental y el nivel del depósito desde tu celular o computadora, con el respaldo de un asistente de IA generativa que interpreta las lecturas por ti.</p>
          <a class="button btn-liquid-primary" href="#acceso">Iniciar sesión en el panel</a>
        </div>
        <div class="lifestyle-image-wrap">
          <img src="${assets}vista/img/el-chilito-convivir.jpg" alt="Huerto urbano inteligente El Chilito conviviendo en el hogar" loading="lazy">
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
          <h4>Asistente de IA generativa</h4>
          <p>Interpreta las lecturas registradas, explica las alertas en lenguaje claro y sugiere revisiones preventivas basadas en guías documentadas.</p>
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

function garden(data) {
  const [status, explanation, symbol] = AppModel.states[data.status];
  const heading = AppViews.heading(data.name, 'El cuidado de tus tres plantas, en un mismo lugar.');
  if (['loading','error'].includes(data.status)) return heading + AppViews.state(status, explanation, data.status === 'loading', data.status === 'error');
  const empty = reading => reading.value == null && reading.quality === 'missing';
  const note = reading => empty(reading) ? '' : `<p class="reading-note">${AppViews.readingNote(reading)}</p>`;
  const quality = reading => reading.quality === 'invalid' ? 'Lectura inválida' : 'Lectura registrada';
  const tank = {low:['Nivel bajo','Revisa el depósito antes de continuar con el riego.'], 'not-low':['Nivel bajo no detectado','El flotador no detecta nivel bajo. No mide el volumen de agua.']}[data.tank.state];
  const hasMeasurements = data.plants.some(plant => !empty(plant.reading)) || !empty(data.temperature) || !empty(data.humidity) || data.tank.state !== 'unknown';
  return `${heading}<div class="connection-strip"><div class="telemetry-cell"><span><small>Estado del huerto</small>${status}</span></div><div class="telemetry-cell telemetry-cell-second"><span><small>Última actualización</small>${data.updatedAt ? AppViews.date(data.updatedAt) : '—'}</span></div>${data.status !== 'unassigned' && (hasMeasurements || data.status === 'waiting') ? `<p class="connection-note">${explanation}</p>` : ''}</div>
    ${data.status === 'unassigned' ? AppViews.gardenLink() : ''}
    <section aria-labelledby="plants-title"><div class="panel-heading"><h2 id="plants-title">Tus tres plantas</h2><p>Humedad del sustrato por planta</p></div><div class="plant-grid">
      ${data.plants.map(plant=>`<article class="plant-card">${empty(plant.reading) ? '' : `<div class="card-top">${badge(quality(plant.reading))}</div>`}<div class="plant-name"><div><h3>${authEscape(plant.name)}</h3><p>Chile habanero</p></div><div class="plant-pedestal">${plantDrawing(plant.id)}</div></div><div class="plant-reading"><span>${icon('drop')}Humedad del sustrato</span>${AppViews.reading(plant.reading,'%')}<div class="sensor-track" aria-hidden="true">${plant.reading.value == null ? '' : `<span style="width:${plant.reading.value}%"></span>`}</div></div>${note(plant.reading)}</article>`).join('')}
    </div></section>
    <section aria-labelledby="ambient-title"><div class="panel-heading"><h2 id="ambient-title">Ambiente del huerto</h2><p>Condiciones compartidas por las tres plantas</p></div><div class="metrics-grid">
      ${[['temp','Temperatura ambiental',data.temperature,'°C'],['drop','Humedad ambiental',data.humidity,'%']].map(([ico,title,reading,unit])=>`<article class="metric"><span class="metric-symbol">${icon(ico)}</span><h3>${title}</h3>${AppViews.reading(reading,unit)}${note(reading)}</article>`).join('')}
    </div></section>
    <section class="water-panel garden-tank" aria-labelledby="tank-title"><div class="panel-title"><span class="icon-medallion">${icon('tank')}</span><h2 id="tank-title">Depósito de agua</h2></div>${tank ? `${badge(tank[0])}<p>${tank[1]}</p><p class="reading-note">Última lectura: ${AppViews.date(data.tank.at)}</p>` : '<strong class="tank-reading absent">—</strong>'}</section>`;
}

// VISTA · Navegación: menú y encabezado. Se ejecuta al cargar y define window.bindNavigation.
// Va después de los controladores y antes del enrutador.

/* Navegación compartida: enlaces normales, orden natural de Tab y sin atrapar el foco. */
(() => {
  const smallScreen = matchMedia('(max-width: 768px)');
  let cleanup = () => {};
  // Indicador del menú de la portada en escritorio: sigue al enlace elegido y a la sección visible.
  function bindLamp() {
    const nav = document.getElementById('public-navigation');
    const lamp = nav?.querySelector('.nav-lamp');
    if (!lamp) return () => {};
    const links = [...nav.querySelectorAll('a[data-section]')];
    // Fuera de la portada (páginas legales) ninguna sección es la actual: sin indicador.
    if (!links.some(link => document.querySelector(link.dataset.section))) { lamp.style.display = 'none'; return () => {}; }
    let active = links[0];
    const place = () => {
      lamp.style.width = `${active.offsetWidth}px`;
      lamp.style.transform = `translateX(${active.offsetLeft}px)`;
    };
    const select = link => {
      active = link;
      links.forEach(item => { if (item === link) item.setAttribute('aria-current', 'location'); else item.removeAttribute('aria-current'); });
      place();
    };
    const click = event => { const link = event.target.closest('a[data-section]'); if (link) select(link); };
    const sections = new Map(links.map(link => [document.querySelector(link.dataset.section), link]));
    const watch = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting && sections.has(entry.target)) select(sections.get(entry.target)); });
    }, { rootMargin: '-45% 0px -54% 0px' });
    sections.forEach((_, section) => { if (section) watch.observe(section); });
    const size = new ResizeObserver(place);
    size.observe(nav);
    nav.addEventListener('click', click);
    select(active);
    document.fonts?.ready.then(() => { if (nav.isConnected) place(); });
    requestAnimationFrame(() => lamp.classList.add('is-ready'));
    return () => { watch.disconnect(); size.disconnect(); nav.removeEventListener('click', click); };
  }
  window.bindNavigation = () => {
    cleanup();
    const header = document.querySelector('.site-header');
    document.documentElement.style.setProperty('--header-height', '0px');
    cleanup = () => {};
    if (!header) return;
    const hero = document.querySelector('.hero');
    let headerHeight = 0;
    const updateAppearance = () => {
      header.classList.toggle('is-scrolled', Boolean(hero && hero.getBoundingClientRect().bottom <= headerHeight));
    };
    const updateHeader = () => {
      const height = header.getBoundingClientRect().height;
      if (height !== headerHeight) {
        headerHeight = height;
        document.documentElement.style.setProperty('--header-height', `${height}px`);
      }
      updateAppearance();
    };
    const resize = new ResizeObserver(updateHeader);
    resize.observe(header);
    window.addEventListener('scroll', updateAppearance, { passive: true });
    const keepFocusVisible = event => {
      const target = event.target;
      if (!(target instanceof HTMLElement) || header.contains(target) || target.closest('.account-tabs') || target.matches('.skip-link,[tabindex="-1"]')) return;
      const bounds = target.getBoundingClientRect();
      if (bounds.top < header.getBoundingClientRect().bottom + 12) target.scrollIntoView({ block: 'start' });
    };
    document.addEventListener('focusin', keepFocusVisible);
    const stopLamp = bindLamp();
    const cleanupHeader = () => {
      stopLamp();
      resize.disconnect();
      window.removeEventListener('scroll', updateAppearance);
      document.removeEventListener('focusin', keepFocusVisible);
    };
    cleanup = cleanupHeader;
    updateHeader();
    const toggle = document.querySelector('[data-nav-toggle]');
    if (!toggle) return;
    const panel = document.getElementById(toggle.getAttribute('aria-controls'));
    if (!panel) return;
    const shade=document.querySelector('[data-public-menu-shade]');
    const setOpen = (open, returnFocus = false) => {
      if (returnFocus) toggle.focus();
      panel.hidden = smallScreen.matches && !open;
      toggle.setAttribute('aria-expanded', String(smallScreen.matches && open));
      const expanded=smallScreen.matches&&open;
      toggle.setAttribute('aria-label',expanded?'Cerrar menú de navegación':'Abrir menú de navegación');
      if(shade)shade.hidden=!expanded;
      document.body.classList.toggle('public-menu-open',expanded);
      updateHeader();
    };
    const sync = () => {
      const focusInPanel = panel.contains(document.activeElement);
      if (!smallScreen.matches && document.activeElement === toggle) panel.querySelector('a')?.focus();
      setOpen(false, smallScreen.matches && focusInPanel);
    };
    const outside = event => {
      if(smallScreen.matches&&toggle.getAttribute('aria-expanded')==='true'&&!panel.contains(event.target)&&!toggle.contains(event.target))setOpen(false);
    };
    const shadeClick = () => setOpen(false,true);
    const leavePanel = event => {
      if(smallScreen.matches&&toggle.getAttribute('aria-expanded')==='true'&&!panel.contains(event.target)&&!toggle.contains(event.target))setOpen(false);
    };
    const click = () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      setOpen(open);
      if (open) panel.querySelector('a')?.focus();
    };
    const escape = event => {
      if (event.key === 'Escape' && smallScreen.matches && toggle.getAttribute('aria-expanded') === 'true') {
        event.preventDefault();
        setOpen(false, true);
      }
    };
    const select = event => {
      if (smallScreen.matches && event.target.closest('a')) setOpen(false, true);
    };
    toggle.addEventListener('click', click);
    panel.addEventListener('click', select);
    document.addEventListener('keydown', escape);
    document.addEventListener('click',outside);
    document.addEventListener('focusin',leavePanel);
    shade?.addEventListener('click',shadeClick);
    smallScreen.addEventListener('change', sync);
    cleanup = () => {
      cleanupHeader();
      toggle.removeEventListener('click', click);
      panel.removeEventListener('click', select);
      document.removeEventListener('keydown', escape);
      document.removeEventListener('click',outside);
      document.removeEventListener('focusin',leavePanel);
      shade?.removeEventListener('click',shadeClick);
      document.body.classList.remove('public-menu-open');
      smallScreen.removeEventListener('change', sync);
    };
    sync();
  };
  window.bindNavigation();
})();

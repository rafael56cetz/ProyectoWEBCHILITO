/* Shared disclosure navigation: ordinary links, natural Tab order, no focus trap. */
(() => {
  const smallScreen = matchMedia('(max-width: 900px)');
  let cleanup = () => {};
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
    const cleanupHeader = () => {
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
    const setOpen = (open, returnFocus = false) => {
      if (returnFocus) toggle.focus();
      panel.hidden = smallScreen.matches && !open;
      toggle.setAttribute('aria-expanded', String(smallScreen.matches && open));
      toggle.textContent = open && smallScreen.matches ? 'Cerrar' : 'Menú';
      updateHeader();
    };
    const sync = () => {
      const focusInPanel = panel.contains(document.activeElement);
      if (!smallScreen.matches && document.activeElement === toggle) panel.querySelector('a')?.focus();
      setOpen(false, smallScreen.matches && focusInPanel);
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
    smallScreen.addEventListener('change', sync);
    cleanup = () => {
      cleanupHeader();
      toggle.removeEventListener('click', click);
      panel.removeEventListener('click', select);
      document.removeEventListener('keydown', escape);
      smallScreen.removeEventListener('change', sync);
    };
    sync();
  };
  window.bindNavigation();
})();

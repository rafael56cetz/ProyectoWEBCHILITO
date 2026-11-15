// CONTROLADOR · Público: aviso de cookies y formulario de preguntas.
// Define: CookieController, ContactController.

// ── Cookies ──
// Solo un botón guarda una decisión: cerrar la ventana o ignorar el aviso no es consentir.
// La decisión vive en el servidor y en una cookie firmada; nunca en localStorage.
const CookieController = (() => {
  const listeners = new Set();
  let state = null, view = null;
  let pending = null, saving = null, loadId = 0, failed = false;
  const notify = () => listeners.forEach(listener => listener());
  // Sin respuesta del servidor la decisión es desconocida: se vuelve a preguntar, nunca se presume.
  function paint() {
    view.banner(failed || (state !== null && !state.decided));
  }
  async function save(statistics) {
    const id = loadId;
    view.showError();
    view.busy(true);
    const result = await PrivacyData.decide(statistics);
    view.busy(false);
    if(result.status !== 'accepted') { view.showError(true); return false; }
    // Si la identidad cambió mientras se guardaba, manda la consulta posterior del servidor.
    if(id === loadId) { state = {...state,decided:true,statistics}; failed = false; paint(); notify(); }
    return true;
  }
  // Una sola decisión a la vez: varias en curso podrían terminar fuera de orden.
  async function decide(statistics) {
    if(saving) return false;
    saving = save(statistics);
    try { return await saving; } finally { saving = null; }
  }
  async function choose(statistics) {
    if(!await decide(statistics)) return;
    view.closePreferences();
    view.saved();
  }
  function openPreferences() {
    view.openPreferences(state?.statistics === true);
  }
  function act(action) {
    if(action === 'aceptar') choose(true);
    if(action === 'rechazar') choose(false);
    if(action === 'configurar') openPreferences();
    if(action === 'cerrar') view.closePreferences();
  }
  function send(route) {
    const section = PrivacyModel.sectionOf(route);
    if(section) PrivacyData.section(section);
  }
  // Mientras no se conoce la decisión de esta identidad, las visitas esperan y no se cuentan.
  async function load() {
    const id = ++loadId;
    state = null;
    failed = false;
    paint();
    notify();
    await saving;
    if(id !== loadId) return;
    const result = await PrivacyData.cookies();
    if(id !== loadId) return;
    if(result.status !== 'ready') { failed = true; paint(); notify(); return; }
    state = result;
    paint();
    notify();
    if(pending && state.statistics) send(pending);
    pending = null;
  }
  function mount() {
    view = CookieViews.screen();
    view.form.addEventListener('submit',event => {
      event.preventDefault();
      choose(view.statisticsChoice());
    });
    document.addEventListener('click',event => {
      if(event.target.closest('[data-cookie-settings]')) { openPreferences(); return; }
      const action = event.target.closest('[data-cookies-accion]')?.dataset.cookiesAccion;
      if(action) act(action);
    });
    window.addEventListener('resize',view.reserveSpace);
  }
  function start() {
    mount();
    return load();
  }
  // Tras iniciar o cerrar sesión la decisión vigente puede ser otra.
  function refresh() {
    view?.closePreferences();
    return load();
  }
  function visit(route) {
    if(state === null) pending = route;
    else if(state.statistics) send(route);
  }
  function onChange(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }
  return Object.freeze({start,refresh,visit,decide,onChange,
    get status(){return state ? {status:'ready',decided:state.decided === true,statistics:state.statistics === true} : {status:failed ? 'error' : 'loading',decided:false,statistics:false};}});
})();

// ── Contacto ──
// Pantalla de preguntas: coordina eventos y envío. La presentación vive en ContactViews.screen.
const ContactController = (() => {
  function mount(root) {
    const view = ContactViews.screen(root);
    view.showDirect(ChilitoHTTP.configuration?.supportContact);
    view.trigger.addEventListener('click',view.open);
    view.closeButton.addEventListener('click',view.close);
    view.dialog.addEventListener('cancel',event => { event.preventDefault(); view.close(); });
    view.dialog.addEventListener('close',view.closed);
    view.dialog.addEventListener('click',event => { if(event.target.closest('a[href^="#"]')) view.closeNow(); });
    view.form.addEventListener('submit',async event => {
      event.preventDefault();
      if(view.isBusy()) return;
      const values = Object.fromEntries(new FormData(view.form));
      if(!ProductContact.validEmail(values.email.trim()) || !values.message.trim()) { view.say('invalid'); return; }
      view.busy(true);
      const result = await ProductContact.send(values);
      if(!view.form.isConnected) return;
      view.busy(false);
      view.say(result);
      if(result === 'accepted') view.reset();
    });
  }
  return {mount};
})();

// CONTROLADOR · Equipos: emisión de códigos de vinculación por el operador.
// Define: BindingAdminController.

// ── Vinculacion ──
// Vinculación de huertos: eventos y coordinación. El servidor confirma; aquí nunca se supone un éxito.
const BindingAdminController = (() => {
  const messages = {forbidden:'Tu cuenta no tiene la capacidad para vincular huertos.', stale:'Ese código ya estaba cerrado. Se actualizó la lista.',
    busy:'Demasiadas operaciones seguidas. Espera un momento.', invalid:'Revisa los datos del formulario.',
    network:'No se pudo comunicar con el servidor. Inténtalo de nuevo.'};
  function mount({root, service = BindingService, mfa = MfaService} = {}) {
    const life = new AbortController();
    const view = BindingViews.mountAdmin(root);
    const {form, dialog, totpForm} = view, say = view.say;
    let busy = false, waiting = null;
    async function load() {
      const result = await service.panel();
      if(life.signal.aborted) return;
      if(result.status !== 'ready') { say(messages[result.status] || 'No se pudo consultar la vinculación.', true); return; }
      view.panel(result, service);
    }
    // Una operación sensible: si falta la confirmación reciente del segundo factor, se pide y se repite.
    async function sensitive(action, done) {
      const result = await action();
      if(life.signal.aborted) return;
      if(result.status === 'reauthenticate') {
        waiting = {action, done};
        view.askReauth();
        return;
      }
      await done(result);
    }
    async function confirmed(outcome) {
      if(outcome.status !== 'ok') { view.reauthFailed(outcome.status); return; }
      view.closeReauth();
      const next = waiting; waiting = null;
      if(next) await sensitive(next.action, next.done);
    }
    async function issued(result) {
      busy = false; view.issuing(false);
      if(result.status === 'issued') {
        view.issued(result, service);
        say(result.code ? 'Código emitido. Díctalo o cópialo ahora: no se volverá a mostrar.' : 'Código emitido para envío por correo.');
        await load();
        view.focusCode();
        return;
      }
      if(result.status === 'refused') { say(service.refusals[result.reason] || 'No se puede emitir el código.', true); return; }
      say(messages[result.status] || 'No se pudo emitir el código.', true);
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if(busy) return;
      const garden = form.elements.garden.value, email = form.elements.email.value.trim(), delivery = form.elements.delivery.value;
      if(!garden || !email) { say('Elige un huerto y escribe el correo de la cuenta.', true); return; }
      busy = true; view.issuing(true);
      await sensitive(() => service.issue(garden, email, delivery), issued);
      if(waiting) { busy = false; view.issuing(false); }
    }, {signal:life.signal});
    root.addEventListener('click', async event => {
      const copy = event.target.closest('[data-binding-copy]');
      if(copy) {
        try { await navigator.clipboard.writeText(view.codeText()); say('Código copiado.'); }
        catch { say('No se pudo copiar. Selecciona el código y cópialo a mano.', true); }
        return;
      }
      const revoke = event.target.closest('[data-binding-revoke]');
      if(revoke && !busy) {
        busy = true; view.revoking(revoke, true);
        await sensitive(() => service.revoke(revoke.dataset.bindingRevoke), async result => {
          say(result.status === 'revoked' ? 'Código revocado.' : (messages[result.status] || 'No se pudo revocar.'), result.status !== 'revoked');
          await load();
        });
        busy = false; view.revoking(revoke, false);
      }
    }, {signal:life.signal});
    totpForm.addEventListener('submit', async event => {
      event.preventDefault();
      const code = totpForm.elements.code.value.trim();
      if(!/^[0-9]{6}$/.test(code)) { view.reauthFailed('format'); return; }
      await confirmed(await mfa.reauthenticateCode(code));
    }, {signal:life.signal});
    view.passkeyButton.addEventListener('click', async () => {
      if(!WebAuthnBrowser.supported()) { await confirmed({status:'unsupported'}); return; }
      const options = await mfa.webauthnReauthOptions();
      if(options.status !== 'ok' || !options.data?.request_options) { await confirmed({status:'unavailable'}); return; }
      try { await confirmed(await mfa.webauthnReauthenticate(await WebAuthnBrowser.get(options.data.request_options))); }
      catch { await confirmed({status:'cancelled'}); }
    }, {signal:life.signal});
    const cancel = () => { waiting = null; view.closeReauth(); say('Operación cancelada: no se emitió ni revocó nada.'); };
    view.cancelButton.addEventListener('click', cancel, {signal:life.signal});
    dialog.addEventListener('cancel', event => { event.preventDefault(); cancel(); }, {signal:life.signal});
    load();
    return {dispose() { life.abort(); view.closeReauth(); }};
  }
  return Object.freeze({mount});
})();

// VISTA · Equipos: pantalla de vinculación de huertos para el operador.
// Define: BindingViews.

// ── Vinculacion ──
// Vinculación de huertos: plantillas fijas; los datos del servidor se insertan siempre como texto.
const BindingViews = (() => {
  const el = (tag, className, text) => Object.assign(document.createElement(tag), className ? {className} : {}, text !== undefined ? {textContent:text} : {});

  // Operador ------------------------------------------------------------------------------------
  function adminShell() {
    return `${AppViews.heading('Vinculación de huertos','Emite un código para asociar un huerto entregado a la cuenta de su dueño. El código vence a los 10 minutos y solo sirve una vez.')}
      <div id="admin-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>
      <section class="bento-panel binding-issue" aria-labelledby="binding-issue-title">
        <h2 id="binding-issue-title">Emitir código</h2>
        <p>Emítelo cuando la persona ya haya iniciado sesión y esté lista para escribirlo.</p>
        <form class="binding-issue-form" data-binding-issue novalidate>
          <label for="binding-garden">Huerto entregado</label>
          <select id="binding-garden" name="garden" required></select>
          <label for="binding-email">Correo de la cuenta</label>
          <input id="binding-email" name="email" type="email" autocomplete="off" spellcheck="false" maxlength="254" required>
          <fieldset class="binding-delivery">
            <legend>Entrega del código</legend>
            <label><input type="radio" name="delivery" value="presencial" checked> En persona: se muestra aquí una sola vez</label>
            <label><input type="radio" name="delivery" value="correo"> Por correo verificado de la cuenta: tú no lo verás</label>
          </fieldset>
          <p class="binding-help">El envío por correo solo está disponible si antes se emitió un código en persona para este huerto y esta cuenta.</p>
          <button class="button btn-liquid-brand" type="submit">Emitir código</button>
        </form>
        <div class="binding-reveal" data-binding-reveal hidden></div>
      </section>
      <section class="bento-panel binding-list" aria-labelledby="binding-pending-title">
        <h2 id="binding-pending-title">Códigos pendientes</h2>
        <p class="binding-help">Solo datos de control: el código nunca se vuelve a mostrar.</p>
        <div data-binding-pending></div>
      </section>
      <section class="bento-panel binding-list" aria-labelledby="binding-recent-title">
        <h2 id="binding-recent-title">Últimos códigos cerrados</h2>
        <div data-binding-recent></div>
      </section>
      ${reauthDialog()}`;
  }
  function reauthDialog() {
    return `<dialog class="bento-panel app-dialog binding-reauth" aria-labelledby="binding-reauth-title" aria-describedby="binding-reauth-text">
      <h2 id="binding-reauth-title">Confirma tu segundo factor</h2>
      <p id="binding-reauth-text">Para emitir o revocar códigos necesitas haber confirmado tu app autenticadora o tu llave de acceso en los últimos 5 minutos.</p>
      <form data-binding-totp novalidate>
        <label for="binding-totp">Código de tu app autenticadora</label>
        <input id="binding-totp" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}">
        <p class="binding-status" data-reauth-status role="alert" tabindex="-1" hidden></p>
        <div class="app-dialog-actions">
          <button class="button btn-liquid-light" type="button" data-binding-passkey>Usar llave de acceso</button>
          <button class="button btn-liquid-light" type="button" data-binding-cancel>Cancelar</button>
          <button class="button btn-liquid-brand" type="submit">Confirmar</button>
        </div>
      </form>
    </dialog>`;
  }
  function gardenOptions(select, gardens) {
    const empty = el('option', '', gardens.length ? 'Elige un huerto' : 'No hay huertos libres con equipo registrado');
    empty.value = '';
    select.replaceChildren(empty, ...gardens.map(g => Object.assign(el('option', '', `${g.name} · ${g.key} · ${g.device}`), {value:g.id})));
  }
  // Única aparición del código. Al salir de la pantalla desaparece del DOM.
  function reveal(host, result, service) {
    host.replaceChildren();
    const b = result.binding;
    if(result.code) {
      host.append(el('h3', '', 'Código para dictar o copiar'),
        Object.assign(el('p', 'binding-code', result.code), {id:'binding-code-value'}),
        el('p', 'binding-help', `Vence a las ${service.timeText(b.expiresAt).replace(/\.$/,'')}. Solo se muestra ahora; si se pierde, emite otro.`));
      const copy = el('button', 'button btn-liquid-light', 'Copiar código');
      copy.type = 'button'; copy.dataset.bindingCopy = '';
      host.append(copy);
    } else {
      host.append(el('h3', '', `Código ${b.folio} enviado a ${b.account}`), el('p', 'binding-mail-state', service.mailStates[b.mail] || 'Estado del envío desconocido'));
    }
    host.hidden = false;
  }
  function table(rows, service, withAction) {
    if(!rows.length) return el('p', 'binding-empty', 'No hay códigos en esta lista.');
    const wrap = el('div', 'user-table-scroll'), t = el('table', 'user-table admin-table');
    wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', withAction ? 'Códigos pendientes' : 'Últimos códigos cerrados');
    const head = el('tr');
    ['Folio','Huerto','Cuenta','Entrega','Emitido','Vence','Intentos','Estado',...(withAction?['Acción']:[])].forEach(h => head.append(Object.assign(el('th','',h),{scope:'col'})));
    t.append(el('thead'), el('tbody'));
    t.tHead.append(head);
    for(const r of rows) {
      const tr = el('tr');
      [r.folio, r.garden, r.account, r.delivery === 'correo' ? 'Correo' : 'Presencial', service.dateText(r.issuedAt), service.timeText(r.expiresAt),
        String(r.attempts), service.states[r.state] || r.state].forEach(v => tr.append(el('td', '', v)));
      if(r.delivery === 'correo' && r.mail !== 'no_aplica') tr.lastChild.append(el('small', 'binding-row-mail', service.mailStates[r.mail] || ''));
      if(withAction) {
        const cell = el('td');
        if(r.state === 'pendiente') {
          const b = el('button', 'button compact btn-liquid-light', 'Revocar');
          b.type = 'button'; b.dataset.bindingRevoke = r.id;
          b.setAttribute('aria-label', `Revocar el código ${r.folio}`);
          cell.append(b);
        }
        tr.append(cell);
      }
      t.tBodies[0].append(tr);
    }
    wrap.append(t);
    return wrap;
  }
  // Panel de vinculación ya montado: operaciones de presentación que coordina BindingAdminController.
  function mountAdmin(root) {
    root.innerHTML = adminShell();
    const form = root.querySelector('[data-binding-issue]'), revealBox = root.querySelector('[data-binding-reveal]');
    const feedback = root.querySelector('#admin-feedback'), dialog = root.querySelector('.binding-reauth');
    const totpForm = dialog.querySelector('[data-binding-totp]'), reauthStatus = dialog.querySelector('[data-reauth-status]');
    const submit = () => form.querySelector('[type=submit]');
    const reauthText = {limited:'Demasiados intentos. Espera un momento.', format:'Escribe los 6 dígitos de tu app autenticadora.'};
    return {form, dialog, totpForm,
      passkeyButton: dialog.querySelector('[data-binding-passkey]'), cancelButton: dialog.querySelector('[data-binding-cancel]'),
      say(text, error = false) {
        feedback.hidden = !text; feedback.textContent = text;
        feedback.setAttribute('role', error ? 'alert' : 'status');
        if(text) feedback.focus();
      },
      panel(result, service) {
        gardenOptions(form.elements.garden, result.gardens);
        root.querySelector('[data-binding-pending]').replaceChildren(table(result.pending, service, true));
        root.querySelector('[data-binding-recent]').replaceChildren(table(result.recent, service, false));
      },
      askReauth() { reauthStatus.hidden = true; totpForm.reset(); dialog.showModal(); totpForm.elements.code.focus(); },
      reauthFailed(code) {
        reauthStatus.hidden = false;
        reauthStatus.textContent = reauthText[code] || 'No se pudo confirmar. Revisa el código o inténtalo con tu llave.';
        reauthStatus.focus();
      },
      closeReauth() { if(dialog.open) dialog.close(); },
      issuing(on) { submit().disabled = on; if(on) { revealBox.hidden = true; revealBox.replaceChildren(); } },
      issued(result, service) {
        reveal(revealBox, result, service);
        form.elements.email.value = '';
      },
      // El código queda bajo el formulario: se lleva el foco ahí para que se vea y se lea.
      focusCode() {
        const title = revealBox.querySelector('h3');
        if(title) { title.tabIndex = -1; title.focus(); title.scrollIntoView({block:'center'}); }
      },
      codeText: () => root.querySelector('#binding-code-value')?.textContent || '',
      revoking(button, on) { if(button.isConnected) button.disabled = on; }};
  }
  return Object.freeze({adminShell, mountAdmin, gardenOptions, reveal, table});
})();

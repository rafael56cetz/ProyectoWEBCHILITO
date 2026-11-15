// VISTA · Equipos: pantallas de vinculación de huertos y su ayuda.
// Define: BindingViews.

// ── Vinculacion ──
// Vinculación de huertos: plantillas fijas; los datos del servidor se insertan siempre como texto.
const BindingViews = (() => {
  const el = (tag, className, text) => Object.assign(document.createElement(tag), className ? {className} : {}, text !== undefined ? {textContent:text} : {});

  // Ayuda para vincular: la dirección de soporte se escribe como texto al abrir el panel.
  function helpPanel() {
    const reason = (value, text) => `<label><input type="radio" name="reason" value="${value}" required> ${text}</label>`;
    return `<details class="binding-support" data-binding-help>
      <summary>Solicitar ayuda para vincular mi huerto</summary>
      <p class="binding-status" data-binding-help-unavailable role="status" hidden></p>
      <div class="binding-support-body" data-binding-help-ready hidden>
        <form class="binding-support-form" data-binding-help-form novalidate>
          <fieldset class="binding-delivery">
            <legend>¿Qué ocurrió?</legend>
            ${reason('expired','El código venció.')}
            ${reason('lost','Perdí o no encuentro el código.')}
            ${reason('rejected','El código no funciona.')}
            ${reason('other','Otro motivo')}
          </fieldset>
          <div class="binding-support-detail" data-binding-help-detail hidden>
            <label for="binding-help-detail">Explica el motivo (obligatorio)</label>
            <textarea id="binding-help-detail" name="detail" rows="3" maxlength="300" aria-describedby="binding-help-safe"></textarea>
          </div>
          <p id="binding-help-safe" class="binding-help">No escribas el código, contraseñas, códigos de verificación, tu domicilio ni otros secretos. No necesitamos más datos personales.</p>
          <p class="binding-help">«Preparar correo» abre tu aplicación de correo con el mensaje listo: tendrás que revisarlo y enviarlo tú. «Copiar mensaje preparado» solo lo copia, para que lo pegues donde prefieras.</p>
          <div class="binding-support-actions">
            <button class="button btn-liquid-brand" type="submit">Preparar correo</button>
            <button class="button btn-liquid-light" type="button" data-binding-help-copy-message>Copiar mensaje preparado</button>
          </div>
          <p class="binding-status" data-binding-help-status role="status" tabindex="-1" hidden></p>
          <div class="binding-support-detail" data-binding-help-manual hidden>
            <label for="binding-help-manual">Mensaje preparado para copiar a mano</label>
            <textarea id="binding-help-manual" rows="9" readonly spellcheck="false" aria-describedby="binding-help-safe"></textarea>
          </div>
        </form>
        <div class="binding-support-contact">
          <p class="binding-help">Si no tienes una aplicación de correo configurada, escribe a:</p>
          <div class="binding-support-address">
            <strong data-binding-help-address></strong>
            <button class="button compact btn-liquid-light" type="button" data-binding-help-copy>Copiar dirección de soporte</button>
          </div>
        </div>
        <p class="binding-help">Esta solicitud no genera un código nuevo ni acredita que el huerto sea tuyo. El equipo debe verificar tu caso antes de emitir otro.</p>
      </div>
    </details>`;
  }
  function helpSetup(panel, address, unavailableText) {
    const missing = panel.querySelector('[data-binding-help-unavailable]');
    panel.querySelector('[data-binding-help-ready]').hidden = !address;
    panel.querySelector('[data-binding-help-address]').textContent = address || '';
    missing.hidden = Boolean(address);
    missing.textContent = address ? '' : unavailableText;
  }
  function helpDetail(form, visible) {
    form.querySelector('[data-binding-help-detail]').hidden = !visible;
    form.elements.detail.required = visible;
    if(!visible) form.elements.detail.removeAttribute('aria-invalid');
  }
  function helpInvalid(form, invalid) {
    if(!form.elements.detail.required) return;
    form.elements.detail.setAttribute('aria-invalid', String(invalid));
  }
  function helpStatus(panel, text, {error = false, focus = error} = {}) {
    const node = panel.querySelector('[data-binding-help-status]');
    node.setAttribute('role', error ? 'alert' : 'status');
    node.hidden = !text; node.textContent = text;
    if(focus) node.focus();
  }
  // Alternativa si el navegador bloquea el portapapeles: el texto queda seleccionado y listo para copiar.
  function helpManual(panel, text) {
    const box = panel.querySelector('[data-binding-help-manual]'), field = box.querySelector('textarea');
    box.hidden = !text; field.value = text;
    if(text) { field.focus(); field.select(); }
  }
  function openMail(href) { Object.assign(document.createElement('a'), {href}).click(); }

  // Persona usuaria sin huerto: el formulario sustituye al aviso «Sin huerto asignado».
  function userPanel() {
    return `<section class="bento-panel garden-link binding-panel" aria-labelledby="binding-title">
      <span class="icon-medallion">${icon('leaf')}</span>
      <div>
        <h2 id="binding-title">Vincular mi huerto</h2>
        <p>Tu cuenta todavía no tiene un huerto. Escribe o pega el código que te dio el equipo al entregarte el huerto, o el que llegó al correo de tu cuenta. Cada código vence a los 10 minutos y solo sirve una vez.</p>
        <form class="binding-form" data-binding-form novalidate>
          <label for="binding-code">Código de vinculación</label>
          <div class="binding-row">
            <input id="binding-code" name="code" autocomplete="one-time-code" autocapitalize="characters" spellcheck="false" inputmode="text" maxlength="40" aria-describedby="binding-help binding-status" required>
            <button class="button btn-liquid-brand" type="submit">Vincular huerto</button>
          </div>
          <p id="binding-help" class="binding-help">26 caracteres. Puedes pegarlo con o sin guiones.</p>
          <p id="binding-status" class="binding-status" role="status" tabindex="-1" hidden></p>
        </form>
        ${helpPanel()}
      </div>
    </section>`;
  }
  function userStatus(form, text, {error = false, busy = false} = {}) {
    const node = form.querySelector('#binding-status'), input = form.elements.code, button = form.querySelector('[type=submit]');
    node.hidden = !text; node.textContent = text;
    node.setAttribute('role', error ? 'alert' : 'status');
    form.setAttribute('aria-busy', String(busy));
    input.readOnly = busy; button.disabled = busy;
    input.setAttribute('aria-invalid', String(error));
    if(error) { node.focus(); }
  }

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
  return Object.freeze({userPanel, userStatus, helpSetup, helpDetail, helpInvalid, helpStatus, helpManual, openMail, adminShell, mountAdmin, gardenOptions, reveal, table});
})();

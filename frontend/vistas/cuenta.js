// VISTA · Cuenta: pantallas de acceso, segundo factor, perfil y privacidad personal.
// Define: AuthViews, MfaViews, ProfileViews, PrivacyViews, LegalAcceptViews, AccountDataViews.

// ── Acceso ──
const AuthViews = (() => {
  const titles = {
    acceso: ['Inicia sesión', 'Entra a tu espacio para consultar el huerto.'],
    registro: ['Crea tu cuenta', 'Usa tu correo electrónico y elige una contraseña.'],
    verificar: ['Verifica tu correo', 'Escribe el código que recibiste por correo. Puedes pegarlo completo.'],
    recuperar: ['Recupera el acceso', 'Te enviaremos un enlace para elegir una contraseña nueva.'],
    restablecer: ['Elige una contraseña nueva', 'Confirma tu nueva contraseña para recuperar el acceso.'],
    cambiar: ['Cambiar contraseña', 'Confirma tu contraseña actual y elige una nueva.']
  };
  const email = value => `<div class="field"><label for="email">Correo electrónico</label><input id="email" name="email" type="email" value="${escaparHTML(value)}" placeholder="tu@correo.com" autocomplete="email" autocapitalize="none" spellcheck="false" maxlength="254" required aria-describedby="email-error"><span class="field-error" id="email-error" hidden></span></div>`;
  const password = (id, label, autocomplete, descriptions = '', help = '') => `<div class="field"><label for="${id}">${label}</label><div class="password-input-group"><input id="${id}" name="${id}" type="password" autocomplete="${autocomplete}" autocapitalize="none" spellcheck="false" class="password-field-input" required aria-describedby="${id}-error${descriptions ? ' ' + descriptions : ''}"><button type="button" class="password-eye-btn no-glass" data-password-toggle="${id}" aria-controls="${id}" aria-label="Mostrar ${id === 'confirmation' ? 'confirmación de contraseña' : label.toLowerCase()}" aria-pressed="false">${iconEye}</button></div><span class="field-error" id="${id}-error" hidden></span>${help}</div>`;
  const feedback = () => '<div id="auth-feedback" class="auth-feedback" role="status" aria-live="polite" aria-atomic="true" tabindex="-1" hidden></div><p class="sr-only" id="access-errors" role="alert" aria-atomic="true"></p><p id="auth-wait" class="auth-help" aria-live="off" hidden></p>';
  const links = screen => screen === 'acceso'
    ? '<p class="auth-switch">¿Aún no tienes cuenta? <a href="#registro">Crear cuenta</a></p>'
    : screen === 'cambiar' ? '<p class="auth-switch"><a href="#cuenta">Cancelar y regresar a Mi cuenta</a></p>' : '<p class="auth-switch"><a href="#acceso">Iniciar sesión</a></p>';
  function form(screen, config, context, review = false) {
    // El mínimo es obligatorio; lo demás orienta. El servidor decide al guardar.
    const check = id => `<p id="${id}" class="password-check"><span data-password-check-icon aria-hidden="true"></span><span data-password-check-text></span></p>`;
    const requirementBlock = '<p id="password-requirements" class="auth-help">Son recomendaciones. Al guardar se rechazan contraseñas comunes, solo numéricas o parecidas a tu correo.</p>';
    const guidance = `<div class="password-guidance"><div class="password-length"><span class="password-meter" aria-hidden="true"><span data-password-meter></span></span><p id="password-counter" class="password-counter" aria-live="off"></p></div>${check('password-minimum')}<p class="password-tips-title">Para que sea más segura</p><div class="password-tips">${check('password-tip-cases')}${check('password-tip-number')}${check('password-tip-symbol')}${check('password-tip-email')}</div></div>`;
    const newPassword = label => password('password', label, 'new-password', 'password-counter password-minimum password-requirements', guidance + requirementBlock);
    const confirmation = () => password('confirmation', 'Confirmar contraseña', 'new-password', 'confirmation-match', '<p id="confirmation-match" class="password-check"><span data-password-check-icon aria-hidden="true"></span><span data-password-check-text></span></p>');
    let fields = '';
    let label = '';
    if (screen === 'acceso') {
      fields = email(context.email) + password('password', 'Contraseña', 'current-password') + '<a class="auth-text-link auth-forgot" href="#recuperar">¿Olvidaste tu contraseña?</a>';
      label = 'Iniciar sesión';
    } else if (screen === 'registro') {
      fields = email(context.email) + newPassword('Contraseña') + confirmation();
      fields += `<div class="terms-field">
        <label class="terms-label" for="termsAccepted"><input id="termsAccepted" name="termsAccepted" type="checkbox" required aria-describedby="termsAccepted-error terms-required"><span>Acepto los Términos y condiciones de YouGarden</span></label>
        <span class="terms-required" id="terms-required">Obligatorio</span>
        <span class="field-error" id="termsAccepted-error" hidden></span>
        <p><a href="#terminos" target="_blank" rel="noopener">Leer Términos y condiciones<span class="sr-only"> (se abre en otra pestaña)</span></a></p>
        <label class="terms-label terms-second" for="privacyRead"><input id="privacyRead" name="privacyRead" type="checkbox" required aria-describedby="privacyRead-error privacy-required"><span>He leído el Aviso de privacidad</span></label>
        <span class="terms-required" id="privacy-required">Obligatorio</span>
        <span class="field-error" id="privacyRead-error" hidden></span>
        <p><a href="#privacidad" target="_blank" rel="noopener">Leer Aviso de privacidad<span class="sr-only"> (se abre en otra pestaña)</span></a></p>
      </div>`;
      label = 'Crear cuenta';
    } else if (screen === 'verificar') {
      fields = email(context.email).replace('type="email"', 'type="email" readonly') + `<div class="field"><label for="code">Código de verificación</label><input id="code" name="code" class="verification-code" type="text" autocomplete="one-time-code" inputmode="${escaparHTML(config.code.inputMode)}" autocapitalize="none" spellcheck="false"${config.code.length ? ` maxlength="${Number(config.code.length)}"` : ''} required aria-describedby="code-error code-expiry"><span class="field-error" id="code-error" hidden></span><span class="auth-help" id="code-expiry" aria-live="off" hidden></span></div>`;
      fields += '<p class="auth-help">Ingresa el código de verificación de 6 dígitos enviado a tu correo.</p>';
      label = 'Verificar correo';
    } else if (screen === 'recuperar') {
      fields = email(context.email);
      label = 'Enviar enlace de recuperación';
    } else {
      fields = (screen === 'cambiar' ? password('currentPassword', 'Contraseña actual', 'current-password') : '') + newPassword('Nueva contraseña') + confirmation();
      label = 'Guardar contraseña';
    }
    return `<form id="access-form" class="login-form" data-auth-screen="${screen}" novalidate>${fields}${['registro', 'restablecer', 'cambiar'].includes(screen) ? '<p id="password-help-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></p>' : ''}${feedback()}<button class="button btn-liquid-brand full" type="submit" data-submit-label="${label}">${label}</button>${screen === 'verificar' ? '<button class="button btn-liquid-light full auth-resend" type="button" data-auth-action="resend">Reenviar código</button>' : ''}</form>${links(screen)}`;
  }
  function layout(title, intro, content, assets = '') {
    return `<div class="auth-layout auth-flow">${brand('#inicio', 'YouGarden, inicio', 'auth-brand')}<aside class="auth-visual"><img src="${assets}vistas/imagenes/habanero-fondo.webp" alt="Hojas y frutos de habanero en una ambientación conceptual de interior." width="1896" height="830"><div class="auth-visual-shade"></div><div class="auth-quote"><h2><span>Tu huerto,</span><span>más cerca de ti.</span></h2><p>Tres plantas de habanero para cultivar en interiores.</p></div></aside><main class="auth-main" id="contenido" tabindex="-1"><div class="auth-form-wrap auth-bento"><h1 id="auth-title">${escaparHTML(title)}</h1><p class="auth-intro">${escaparHTML(intro)}</p><div id="auth-content">${content}</div></div></main></div>`;
  }
  return {
    layout,
    updatePasswordHelp(root, progress) {
      const counter = root.querySelector('#password-counter');
      if (!counter) return;
      const known = Number.isInteger(progress.minLength) && Number.isInteger(progress.maxLength);
      const minimumText = `Mínimo ${progress.minLength} caracteres`;
      counter.textContent = `${progress.length} ${progress.length === 1 ? 'carácter' : 'caracteres'}`;
      root.querySelector('[data-password-meter]').style.width = known ? `${Math.min(100,progress.length / progress.minLength * 100)}%` : '0%';
      root.querySelector('.password-length').classList.toggle('is-met',progress.range === 'within-range');
      counter.classList.toggle('is-error', progress.range === 'over-maximum');
      const setCheck = (element, met, text) => {
        element.querySelector('[data-password-check-icon]').innerHTML = met ? icon('check') : '';
        element.querySelector('[data-password-check-text]').textContent = text;
        element.classList.toggle('is-met', met);
      };
      const minimum = root.querySelector('#password-minimum');
      const inRange = progress.range === 'within-range';
      minimum.hidden = !known;
      setCheck(minimum, progress.meetsMinimum && inRange, progress.range === 'over-maximum' ? `Supera el máximo de ${progress.maxLength} caracteres` : minimumText);
      minimum.setAttribute('aria-label', `${minimumText}${inRange ? ', cumplido' : ''}`);
      const {hints} = progress;
      setCheck(root.querySelector('#password-tip-cases'), hints.cases, progress.numericOnly ? 'Solo números no se acepta: añade letras' : 'Mayúsculas y minúsculas');
      setCheck(root.querySelector('#password-tip-number'), hints.number, 'Números');
      setCheck(root.querySelector('#password-tip-symbol'), hints.symbol, 'Un símbolo, como ! # $ %');
      const usesEmail = root.querySelector('#password-tip-email');
      usesEmail.hidden = !hints.emailKnown;
      setCheck(usesEmail, progress.length > 0 && !hints.usesEmail, hints.usesEmail ? 'Incluye tu correo: elige otra' : 'No incluye tu correo');
      setCheck(root.querySelector('#confirmation-match'), progress.confirmation === 'matches', 'Las contraseñas coinciden');
    },
    title(screen) { return titles[screen]?.[0] || titles.acceso[0]; },
    render(screen, { config = AuthConfig, context = {}, assets = '', embedded = false, review = false } = {}) {
      if (embedded) return `<div class="auth-flow account-password bento-panel"><h1 id="auth-title">${titles[screen][0]}</h1><p class="auth-intro">${titles[screen][1]}</p><div id="auth-content">${form(screen, config, context)}</div></div>`;
      const previewHelp = '';
      const intro = screen === 'recuperar' ? 'Ingresa tu correo electrónico para enviarte las instrucciones de recuperación.' : titles[screen][1];
      return layout(titles[screen][0], intro, previewHelp + form(screen, config, context, review), assets);
    },
    message(title, text, action = 'Iniciar sesión', href = '#acceso') {
      return `<div class="auth-result" tabindex="-1"><span class="auth-result-icon" aria-hidden="true">${icon(href === '#recuperar' ? 'info' : 'check')}</span><h2>${escaparHTML(title)}</h2><p>${escaparHTML(text)}</p><a class="button btn-liquid-brand full" href="${href}">${escaparHTML(action)}</a></div>`;
    },
    resetChecking() { return '<div class="auth-feedback" role="status">Comprobando el enlace…</div>'; },
    resetUnavailable() { return '<div class="auth-feedback is-error" role="alert" tabindex="-1">No podemos comprobar el enlace en este momento. Inténtalo de nuevo.</div><button class="button btn-liquid-brand full" type="button" data-auth-action="check-reset">Reintentar</button><p class="auth-switch"><a href="#recuperar">Solicitar otro enlace</a></p>'; },
    sessionChecking() { return layout('Comprobando sesión', 'Espera un momento.', '<div class="auth-feedback" role="status">Comprobando tu acceso…</div>'); },
    form,
    // Pantalla de acceso montada: AuthController decide estados y textos; aquí solo se lee y se pinta el DOM.
    screen(root, screen, options) {
      root.innerHTML = this.render(screen, options);
      const find = selector => root.querySelector(selector);
      const content = () => find('#auth-content');
      const secretFields = 'input[name="password"],input[name="currentPassword"],input[name="confirmation"]';
      const fields = () => Array.from(root.querySelectorAll('input[name]'));
      const setError = (name, message = '') => {
        const input = find(`[name="${name}"]`);
        if (!input) return;
        input.setAttribute('aria-invalid', String(Boolean(message)));
        const error = find(`#${name}-error`);
        error.textContent = message;
        error.hidden = !message;
      };
      const auth = {
        values: () => Object.fromEntries(fields().map(input => [input.name, input.type === 'checkbox' ? input.checked : input.value])),
        names: () => fields().map(input => input.name),
        hasPasswordHelp: () => Boolean(find('#password-counter')),
        passwordInputs: () => ({password:find('#password').value, confirmation:find('#confirmation')?.value || '', email:find('#email')?.value || ''}),
        passwordHelp: progress => AuthViews.updatePasswordHelp(root, progress),
        announce(text) { const live = find('#password-help-status'); if (live?.isConnected) live.textContent = text; },
        canAnnounce: () => Boolean(find('#password-help-status')),
        clearPasswords() { root.querySelectorAll(secretFields).forEach(input => { input.value = ''; }); },
        clearSecrets() { root.querySelectorAll('input[type="password"],' + secretFields + ',input[name="code"]').forEach(input => { input.value = ''; }); },
        emailValid: () => { const email = find('#email'); return !email || email.validity.valid; },
        emailValue: () => find('#email').value.trim(),
        setEmail(value) { const field = find('#email'); if (field) field.value = value; },
        isInvalid: name => find(`[name="${name}"]`)?.getAttribute('aria-invalid') === 'true',
        setError,
        summary(text) { const summary = find('#access-errors'); if (summary) summary.textContent = text; },
        focusField(name) { find(`[name="${name}"]`)?.focus(); },
        uncheck(name) { find(`[name="${name}"]`).checked = false; },
        clear(name) { find(`[name="${name}"]`).value = ''; },
        resetForm() { find('form').reset(); },
        show(text, error, focus, busy) {
          const box = find('#auth-feedback');
          if (!box) return;
          box.hidden = false;
          box.textContent = text;
          box.classList.toggle('is-error', error);
          box.classList.toggle('sr-only', busy);
          if (focus && !busy) box.focus({ preventScroll: false });
        },
        timers({submitDisabled, resendDisabled, wait, expiry}) {
          const submit = find('[type="submit"]'), resendButton = find('[data-auth-action="resend"]');
          if (submit) submit.disabled = submitDisabled;
          if (resendButton) resendButton.disabled = resendDisabled;
          const waitBox = find('#auth-wait');
          if (waitBox) { waitBox.hidden = !wait; waitBox.textContent = wait; }
          const expiryBox = find('#code-expiry');
          if (expiryBox && expiry !== null) { expiryBox.hidden = !expiry; expiryBox.textContent = expiry; }
        },
        hasExpiry: () => Boolean(find('#code-expiry')),
        busy(value, pendingLabel, resendLabel) {
          if (!value) {
            const feedback = find('#auth-feedback');
            if (feedback) { feedback.hidden = true; feedback.textContent = ''; feedback.classList.remove('sr-only'); }
          }
          find('form')?.setAttribute('data-busy', String(value));
          root.querySelectorAll('input').forEach(input => {
            if (input.type === 'checkbox') input.disabled = value;
            else input.readOnly = value;
          });
          const submit = find('[type="submit"]');
          if (submit) {
            submit.setAttribute('aria-busy', String(Boolean(value && pendingLabel)));
            if (value && pendingLabel) submit.innerHTML = `<span class="button-spinner" aria-hidden="true"></span>${pendingLabel}`;
            else submit.textContent = submit.dataset.submitLabel;
          }
          const resend = find('[data-auth-action="resend"]');
          if (resend) {
            resend.setAttribute('aria-busy', String(Boolean(value && resendLabel)));
            resend.textContent = value && resendLabel ? resendLabel : 'Reenviar código';
          }
        },
        result(title, text, action, href) {
          content().innerHTML = AuthViews.message(title, text, action, href);
          find('#auth-title').textContent = title;
          find('.auth-intro').hidden = true;
          find('.auth-result h2').hidden = true;
          find('.auth-result').focus();
          document.title = title + ' · YouGarden';
        },
        showResetForm(screenName, config, context) { content().innerHTML = AuthViews.form(screenName, config, context); },
        resetUnavailable() { content().innerHTML = AuthViews.resetUnavailable(); find('[role="alert"]')?.focus(); },
        resetChecking() { content().innerHTML = AuthViews.resetChecking(); },
        togglePassword(toggle) {
          const input = find(`#${toggle.dataset.passwordToggle}`);
          const visible = input.type === 'password';
          input.type = visible ? 'text' : 'password';
          toggle.innerHTML = visible ? iconEyeOff : iconEye;
          const label = input.id === 'confirmation' ? 'confirmación de contraseña' : find(`label[for="${input.id}"]`).textContent.toLowerCase();
          toggle.setAttribute('aria-label', `${visible ? 'Ocultar' : 'Mostrar'} ${label}`);
          toggle.setAttribute('aria-pressed', String(visible));
        },
        keepVisible(input) {
          if (!root.contains(input) || !input.matches('input,button')) return;
          const viewport = window.visualViewport;
          if (viewport && input.getBoundingClientRect().bottom > viewport.height + viewport.offsetTop - 20) input.scrollIntoView({block:'center'});
        }
      };
      return auth;
    }
  };
})();

// ── Mfa ──
// Pantallas de segundo factor. Lo que viene del servidor se pinta con textContent.
const MfaViews = Object.freeze({
  // Textos de las confirmaciones de Mi cuenta › Seguridad (las pinta confirmar()).
  confirmations: Object.freeze({
    totpDisable: {titulo:'¿Desactivar la app autenticadora?',texto:'Ya no se pedirá su código al iniciar sesión. Puedes activarla de nuevo cuando quieras.',accion:'Desactivar',peligro:true},
    keyRemove: name => ({titulo:'¿Quitar esta llave de acceso?',texto:`No podrás entrar con «${name}». No se puede deshacer.`,accion:'Quitar',peligro:true}),
    recoveryRegenerate: {titulo:'¿Generar códigos nuevos?',texto:'Los códigos actuales dejarán de servir. Guarda los nuevos en un lugar seguro. No se puede deshacer.',accion:'Generar códigos'}
  }),
  step(kind) {
    const byMail = kind === 'login_by_code';
    return `<form data-step class="login-form" novalidate><div class="field"><label for="code">${byMail?'Código de 6 dígitos':'Código de tu app o de recuperación'}</label>
      <input id="code" name="code" autocomplete="one-time-code" required ${byMail?'inputmode="numeric" maxlength="6" data-campo="digitos"':'maxlength="64"'}></div>
      <p class="auth-help">${byMail?'Te lo enviamos por correo. Vence en 5 minutos.':'Si perdiste tu app, usa uno de tus códigos de recuperación.'}</p>
      ${byMail?'':'<a class="auth-text-link" href="#sin-acceso">No tengo mi app ni mis códigos</a>'}
      <div data-step-feedback class="auth-feedback is-error" role="alert" hidden></div>
      <div class="step-actions"><button class="button btn-liquid-brand" type="submit">Continuar</button>
      <button class="button btn-liquid-light" type="button" data-step-cancel>Cancelar</button>
      <button class="button btn-liquid-light" type="button" data-step-key hidden>Usar llave de acceso</button></div></form>`;
  },
  account() {
    const tabs = AppViews.accountTabs('seguridad');
    return `${AppViews.heading('Seguridad','Elige cómo confirmas tu identidad al entrar.')}${tabs}
      <div id="mfa-feedback" class="user-feedback" role="status" tabindex="-1" hidden></div>
      <section class="bento-panel" data-mfa-required hidden role="alert"><h2>Activa un método para usar el panel</h2><p>Los administradores necesitan una app autenticadora o una llave de acceso.</p></section>
      <section class="bento-panel" data-mfa-reauth hidden><h2>Confirma tu contraseña</h2><form data-reauth class="maint-form"><label>Contraseña<input type="password" name="password" autocomplete="current-password" required></label><button class="button btn-liquid-brand" type="submit">Confirmar</button></form></section>
      <div class="security-grid">
      <section class="bento-panel security-card"><h2>Código por correo</h2><p data-mail-state></p></section>
      <section class="bento-panel security-card"><h2>App autenticadora</h2><p data-totp-state></p>
        <div class="app-actions"><button class="button btn-liquid-brand" type="button" data-mfa="totp-start" hidden>Activar</button>
        <button class="button btn-liquid-light" type="button" data-mfa="totp-disable" hidden>Desactivar</button></div>
        <form data-totp-form class="maint-form" hidden><img data-totp-image alt="Código QR para tu app autenticadora" width="200" height="200"><p>Clave manual: <code data-totp-secret></code></p>
        <label>Código de la app<input name="code" inputmode="numeric" maxlength="6" autocomplete="one-time-code" required data-campo="digitos"></label><button class="button btn-liquid-brand" type="submit">Confirmar</button></form></section>
      <section class="bento-panel security-card"><h2>Llaves de acceso</h2><p>Usa la huella, el rostro o el PIN de tu dispositivo. Tu PIN y tu biometría nunca salen de él.</p><ul class="security-keys" data-keys aria-label="Llaves registradas"></ul>
        <form data-key-form class="key-form"><label for="key-name">Nombre de la llave</label><div class="key-form-row"><span class="key-form-icon">${icon('key')}</span><input id="key-name" name="name" maxlength="100" required placeholder="Ej. Teléfono personal" autocomplete="off" data-campo="cosa"><button class="button btn-liquid-brand" type="submit">${icon('plus')}<span>Agregar llave</span></button></div></form></section>
      <section class="bento-panel security-card"><h2>Códigos de recuperación</h2><p data-recovery-state></p>
        <div class="app-actions"><button class="button btn-liquid-light" type="button" data-mfa="recovery-regenerate" hidden>Generar códigos nuevos</button></div>
        <div data-recovery-new hidden><p>Guárdalos ahora: no se volverán a mostrar. Cada uno sirve una sola vez.</p><ol data-recovery-list></ol></div></section>
      </div>`;
  },
  // Muestra el contacto que prepara el modelo: enlace si es un correo, texto si no lo es.
  supportContact(host, {text, href}) {
    host.hidden = false;
    if(!href) { host.textContent = text; return; }
    host.replaceChildren(Object.assign(document.createElement('a'),{textContent:text,href}));
  },
  // Una fila por llave: icono fijo, nombre como texto y botón para quitarla.
  methodItem(item) {
    const row = Object.assign(document.createElement('li'),{className:'key-item'});
    const mark = Object.assign(document.createElement('span'),{className:'key-item-icon'});
    mark.innerHTML = icon('key');
    const name = Object.assign(document.createElement('span'),{className:'key-item-name',textContent:item.name || 'Llave de acceso'});
    const remove = Object.assign(document.createElement('button'),{type:'button',className:'button btn-liquid-light key-item-remove',textContent:'Quitar'});
    remove.dataset.keyRemove = item.id;
    remove.setAttribute('aria-label','Quitar '+(item.name || 'llave de acceso'));
    row.append(mark,name,remove);
    return row;
  },
  // Segundo paso del inicio de sesión: operaciones de presentación para SecondStepController.
  secondStep(root, assets) {
    const texts = {invalid:'El código no es válido.',limited:'Demasiados intentos. Espera un momento.',conflict:'El proceso venció. Inicia sesión de nuevo.',unavailable:'No se pudo comprobar. Inténtalo de nuevo.'};
    root.innerHTML = AuthViews.layout('Confirma tu acceso','Falta un paso para entrar.','<div data-step-host role="status">Comprobando…</div>',assets);
    const host = root.querySelector('[data-step-host]');
    return {
      show(kind, keyAvailable) {
        host.removeAttribute('role');
        host.innerHTML = MfaViews.step(kind);
        const form = host.querySelector('[data-step]'), feedback = host.querySelector('[data-step-feedback]');
        const key = host.querySelector('[data-step-key]'), submit = form.querySelector('[type=submit]');
        key.hidden = !keyAvailable;
        return {form, key, cancel: host.querySelector('[data-step-cancel]'),
          code: () => form.elements.code.value.trim(),
          isBusy: () => submit.disabled,
          busy(on) { submit.disabled = on; submit.textContent = on ? 'Comprobando…' : 'Continuar'; },
          fail(status) { feedback.textContent = texts[status] || texts.unavailable; feedback.hidden = false; }};
      }};
  },
  // Métodos de acceso de la cuenta: operaciones de presentación para MfaController.
  accountScreen(root) {
    root.innerHTML = MfaViews.account();
    const q = selector => root.querySelector(selector);
    const texts = {invalid:'Revisa el dato e inténtalo de nuevo.',limited:'Demasiados intentos. Espera un momento.',failed:'No se pudo completar la operación.',
      'list-failed':'No se pudieron consultar tus métodos.','key-removed':'Llave quitada.','totp-disabled':'App autenticadora desactivada.',
      'wrong-password':'Contraseña incorrecta.','totp-enabled':'App autenticadora activada.','no-webauthn':'Este navegador no admite llaves de acceso.',
      'key-not-created':'No se creó la llave.','key-not-saved':'No se pudo guardar la llave.','key-added':'Llave agregada.'};
    return {
      reauthForm: q('[data-reauth]'), totpForm: q('[data-totp-form]'), keyForm: q('[data-key-form]'),
      keyName: button => button.closest('.key-item')?.querySelector('.key-item-name')?.textContent || 'tu llave',
      say(code, failed = false) {
        const box = q('#mfa-feedback');
        box.hidden = false; box.textContent = texts[code] || texts.failed; box.setAttribute('role',failed?'alert':'status'); box.focus();
      },
      clearForm(form) { form.reset(); },
      askPassword() { q('[data-mfa-reauth]').hidden = false; q('[data-reauth] input').focus(); },
      passwordConfirmed() { q('[data-mfa-reauth]').hidden = true; },
      showCodes(codes) {
        q('[data-recovery-list]').replaceChildren(...codes.map(code => Object.assign(document.createElement('li'),{textContent:code})));
        q('[data-recovery-new]').hidden = false;
        q('[data-recovery-new]').scrollIntoView({block:'nearest'});
      },
      methods({totp, keys, recovery, strong, mfaRequired}) {
        q('[data-mfa-required]').hidden = !(mfaRequired && !strong);
        q('[data-mail-state]').textContent = strong ? 'Inactivo: ya confirmas tu acceso con un método más fuerte.' : 'Activo: te enviamos un código cada vez que entras con tu contraseña.';
        q('[data-totp-state]').textContent = totp ? 'Activa.' : 'Sin activar.';
        q('[data-mfa="totp-start"]').hidden = Boolean(totp);
        q('[data-mfa="totp-disable"]').hidden = !totp;
        q('[data-totp-form]').hidden = true;
        q('[data-keys]').replaceChildren(...keys.map(MfaViews.methodItem));
        q('[data-recovery-state]').textContent = recovery ? `Te quedan ${recovery.unused_code_count} de ${recovery.total_code_count}.` : 'Se generan al activar tu primer método.';
        q('[data-mfa="recovery-regenerate"]').hidden = !recovery;
      },
      totpSetup(secret, image) {
        q('[data-totp-secret]').textContent = secret || '';
        q('[data-totp-image]').src = image || '';
        q('[data-totp-form]').hidden = false;
      }};
  }
});

// ── Perfil ──
const ProfileViews = (() => {
  const fields = `<label>Nombre<input name="firstName" maxlength="60" autocomplete="given-name" data-campo="persona"></label>
    <label>Apellido<input name="lastName" maxlength="60" autocomplete="family-name" data-campo="persona"></label>
    <label>Alias<input name="alias" maxlength="64" autocomplete="nickname" data-campo="cosa" aria-describedby="alias-ayuda"><small id="alias-ayuda">Lo usaremos para dirigirnos a ti.</small></label>`;
  const labels = Object.freeze({firstName:'Nombre',lastName:'Apellido',alias:'Alias'});
  return Object.freeze({
    form: `<section class="bento-panel account-profile" aria-labelledby="perfil-titulo"><h2 id="perfil-titulo">Datos personales</h2>
      <p>Son opcionales y puedes cambiarlos cuando quieras.</p>
      <div data-profile-view><dl class="profile-facts" data-profile-facts></dl>
      <div class="app-actions"><button class="button btn-liquid-light" type="button" data-profile-edit>Cambiar datos</button></div></div>
      <form data-profile class="maint-form" hidden>${fields}
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit">Guardar cambios</button>
      <button class="button btn-liquid-light" type="button" data-profile-cancel>Cancelar</button></div></form>
      <p data-profile-state role="status" hidden></p></section>`,
    // Datos de la persona: siempre como texto.
    facts(host, data) {
      host.replaceChildren(...Object.entries(labels).map(([key,label]) => {
        const row = document.createElement('div');
        row.append(Object.assign(document.createElement('dt'),{textContent:label}),Object.assign(document.createElement('dd'),{textContent:data[key] || 'Sin dato'}));
        return row;
      }));
    },
    welcome: `<dialog class="bento-panel app-dialog" data-welcome aria-labelledby="bienvenida-titulo"><h2 id="bienvenida-titulo">Te damos la bienvenida</h2>
      <p>¿Cómo quieres que te llamemos? Usaremos tu alias para dirigirnos a ti. Todos los datos son opcionales.</p>
      <form data-welcome-form method="dialog" class="maint-form">${fields}<p data-profile-state role="alert" hidden></p>
      <div class="app-actions"><button class="button btn-liquid-light" type="button" data-welcome-skip>Ahora no</button>
      <button class="button btn-liquid-brand" type="submit">Guardar</button></div></form></dialog>`,
    myPrivacy: `<section class="bento-panel privacy-panel" aria-labelledby="mis-datos-titulo"><div class="privacy-panel-row"><div><h2 id="mis-datos-titulo">Mis datos</h2>
      <p>Consulta los datos de tu cuenta. Para corregirlos, usa el apartado Perfil.</p></div>
      <button class="button btn-liquid-brand" type="button" data-my-data>Consultar mis datos</button></div>
      <p data-privacy-state role="status" hidden></p><dl class="profile-facts" data-my-data-list hidden></dl></section>
      <section class="bento-panel privacy-panel" aria-labelledby="estadisticas-titulo"><h2 id="estadisticas-titulo">Estadísticas de este navegador</h2>
      <p>Son voluntarias y solo cuentan secciones visitadas. Los totales ya acumulados no permiten localizar una aportación individual.</p>
      <p class="privacy-saved"><span>Decisión guardada:</span> <strong data-statistics-saved>Consultando…</strong></p>
      <form data-statistics-form><fieldset class="privacy-choice"><legend>Tu selección</legend>
      <label class="cookie-option"><input type="radio" name="statistics" value="yes"> Permitir estadísticas en este navegador</label>
      <label class="cookie-option"><input type="radio" name="statistics" value="no"> No permitir estadísticas</label></fieldset>
      <p class="privacy-unsaved" data-statistics-pending hidden>Tienes un cambio sin guardar.</p>
      <div class="app-actions"><button class="button btn-liquid-brand" type="submit" disabled>Guardar preferencias</button></div>
      <p data-statistics-result role="status" hidden></p></form></section>`,
    // Perfil: monta el bloque y devuelve sus operaciones de presentación.
    profileScreen(host) {
      host.innerHTML = this.form;
      const view = host.querySelector('[data-profile-view]'), facts = host.querySelector('[data-profile-facts]');
      const edit = host.querySelector('[data-profile-edit]'), form = host.querySelector('[data-profile]');
      const save = form.querySelector('[type=submit]'), state = host.querySelector('[data-profile-state]');
      const texts = {saving:'Guardando tus cambios…', saved:'Cambios guardados.', limited:'Demasiados intentos. Espera un momento.'};
      return {form, edit, cancel: form.querySelector('[data-profile-cancel]'),
        values: names => Object.fromEntries(names.map(name => [name,form.elements[name].value])),
        fill(names, data) { for(const name of names) form.elements[name].value = data[name] || ''; },
        facts: data => ProfileViews.facts(facts,data),
        say(code = '') { state.textContent = code ? texts[code] || 'No se pudieron guardar los cambios. Revisa los datos e inténtalo de nuevo.' : ''; state.hidden = !code; },
        editing(active) {
          view.hidden = active; form.hidden = !active;
          (active ? form.elements.firstName : edit).focus();
        },
        busy(active) {
          form.setAttribute('aria-busy',String(active));
          form.querySelectorAll('input,button').forEach(control => { control.disabled = active; });
          save.textContent = active ? 'Guardando…' : 'Guardar cambios';
        }};
    },
    welcomeScreen(root) {
      root.insertAdjacentHTML('beforeend',this.welcome);
      const dialog = root.querySelector('[data-welcome]');
      const form = dialog.querySelector('[data-welcome-form]'), state = dialog.querySelector('[data-profile-state]');
      return {form, skip: dialog.querySelector('[data-welcome-skip]'),
        values: names => Object.fromEntries(names.map(name => [name,form.elements[name].value])),
        open() { dialog.showModal(); },
        failed() { state.textContent = 'No se pudo guardar. Inténtalo de nuevo.'; state.hidden = false; },
        close() { dialog.close(); dialog.remove(); }};
    },
    privacyScreen(host) {
      host.innerHTML = this.myPrivacy;
      const list = host.querySelector('[data-my-data-list]'), consult = host.querySelector('[data-my-data]');
      const state = host.querySelector('[data-privacy-state]'), form = host.querySelector('[data-statistics-form]');
      const saved = host.querySelector('[data-statistics-saved]'), pending = host.querySelector('[data-statistics-pending]');
      const result = host.querySelector('[data-statistics-result]'), save = form.querySelector('[type=submit]');
      const radios = [...form.elements.statistics];
      const savedText = current => current.status === 'loading' ? 'Consultando…' : current.status === 'error' ? 'No se pudo consultar. Puedes guardar una decisión nueva.' : !current.decided ? 'Sin decisión guardada' : current.statistics ? 'Estadísticas permitidas' : 'Estadísticas no permitidas';
      const labels = {email:'Correo electrónico',firstName:'Nombre',lastName:'Apellido',alias:'Alias',createdAt:'Cuenta creada',gardens:'Huertos'};
      return {form, consult,
        selected: () => radios.find(radio => radio.checked)?.value || '',
        report(code = '') { result.textContent = {stored:'Preferencia guardada.', failed:'No se pudo guardar tu preferencia. Sigue vigente la decisión anterior.'}[code] || ''; result.hidden = !result.textContent; },
        sync({current, choice, keepSelection, changed, saving}) {
          saved.textContent = savedText(current);
          // Hasta que la persona elija, la selección refleja lo guardado; nunca al revés.
          if(!keepSelection) radios.forEach(radio => { radio.checked = radio.value === choice; });
          pending.hidden = !changed();
          save.disabled = saving || !changed();
        },
        consulting(active) { consult.disabled = active; },
        myDataFailed() { state.textContent = 'No se pudieron consultar tus datos. Inténtalo de nuevo.'; state.hidden = false; },
        myData(data) {
          state.hidden = true;
          list.replaceChildren(...Object.entries(labels).map(([key,label]) => {
            const value = key === 'gardens' ? data.gardens.join(', ') : key === 'createdAt' ? new Date(data.createdAt).toLocaleDateString('es-MX') : data[key];
            const row = document.createElement('div');
            row.append(Object.assign(document.createElement('dt'),{textContent:label}),Object.assign(document.createElement('dd'),{textContent:value || 'Sin dato'}));
            return row;
          }));
          list.hidden = false;
        },
        saving(active) {
          radios.forEach(radio => { radio.disabled = active; });
          save.textContent = active ? 'Guardando…' : 'Guardar preferencias';
        }};
    }
  });
})();

const PrivacyViews = Object.freeze({
  account() {
    const tabs = AppViews.accountTabs('privacidad');
    const documents = '<nav class="doc-links" aria-label="Documentos legales"><span>Documentos legales</span><a href="#privacidad">Aviso de privacidad</a><a href="#cookies">Política de cookies</a><a href="#terminos">Términos y condiciones</a></nav>';
    return `<div class="privacy-flow">${AppViews.heading('Privacidad','Consulta tus datos y decide sobre las estadísticas de este navegador.')}${tabs}<div data-my-privacy></div><div data-account-data></div>${documents}</div>`;
  },
  // Pinta el apartado y devuelve el contenedor donde se monta «Mis datos».
  mount(root) {
    root.innerHTML = PrivacyViews.account();
    return root.querySelector('[data-my-privacy]');
  }
});

// ── Legales ──
// Aceptación de textos legales nuevos (4.0), con el marco del acceso. Los datos del servidor entran escapados.
const LegalAcceptViews = (() => {
  const documents = {
    terminos:{link:'#terminos', accept:version => `Acepto los Términos y condiciones (versión ${version})`},
    aviso_privacidad:{link:'#privacidad', accept:version => `He leído el Aviso de privacidad (versión ${version})`}};
  const card = item => {
    const document = documents[item.type];
    return `<fieldset class="legal-card"><legend>${escaparHTML(item.title)} · versión ${escaparHTML(item.version)}</legend>
      ${document ? `<a class="auth-text-link" href="${document.link}" target="_blank" rel="noopener noreferrer">Leer documento${icon('external')}<span class="sr-only"> (se abre en otra pestaña)</span></a>` : ''}
      <label class="legal-check"><input type="checkbox" name="document" value="${escaparHTML(item.documentId)}" required><span>${escaparHTML(document ? document.accept(item.version) : `Acepto ${item.title} (versión ${item.version})`)}</span></label></fieldset>`;
  };
  function screen(root, assets, pending) {
    const form = `<form data-legal-form novalidate>${pending.map(card).join('')}
      <div data-legal-feedback class="auth-feedback is-error" role="alert" hidden>No pudimos guardar tu aceptación. Inténtalo de nuevo.</div>
      <div class="step-actions"><button class="button btn-liquid-brand" type="submit" disabled>Aceptar y continuar</button>
      <button class="button btn-liquid-light" type="button" data-legal-logout>Cerrar sesión</button></div></form>`;
    root.innerHTML = AuthViews.layout('Actualizamos nuestros documentos', 'Para seguir usando YouGarden, revisa y acepta la versión nueva.', form, assets);
    const host = root.querySelector('[data-legal-form]'), submit = host.querySelector('[type=submit]'), feedback = host.querySelector('[data-legal-feedback]');
    const boxes = () => [...host.querySelectorAll('input[name=document]')];
    return {form:host, logout:host.querySelector('[data-legal-logout]'),
      ids: () => boxes().filter(box => box.checked).map(box => box.value),
      allChecked: () => boxes().every(box => box.checked),
      changed() { submit.disabled = !boxes().every(box => box.checked); feedback.hidden = true; },
      busy(on) { submit.disabled = on || !boxes().every(box => box.checked); submit.textContent = on ? 'Guardando…' : 'Aceptar y continuar'; },
      fail() { feedback.hidden = false; }};
  }
  return Object.freeze({screen});
})();

// ── Eliminacion ──
// «Documentos que aceptaste» y «Eliminar mi cuenta» (4.9). Los datos del servidor entran escapados.
const AccountDataViews = (() => {
  const TYPES = {terminos:'Términos y condiciones', aviso_privacidad:'Aviso de privacidad'};
  const WRONG = {'wrong-password':'La contraseña no es correcta.', limited:'Demasiados intentos. Espera un momento.', unauthenticated:'Tu sesión venció. Inicia sesión de nuevo.',
    unavailable:'No se pudo completar. Inténtalo de nuevo.', 'admin-account':'Tu cuenta tiene capacidades de administración. Pide que te las retiren antes de eliminarla.',
    'admin-history':'Tu cuenta atendió registros de otras personas y no puede eliminarse desde aquí. Escribe a soporte.'};
  const accepted = state => {
    if(state.status === 'error') return '<p role="alert">No se pudieron consultar tus documentos.</p>';
    if(state.status === 'loading') return '<p role="status">Consultando…</p>';
    if(!state.items.length) return '<p>Aún no hay documentos aceptados.</p>';
    return `<ul class="user-history-list">${state.items.map(item => `<li><span>${icon('check')}</span><div><h3>${escaparHTML(TYPES[item.type] || item.type)}</h3><p>Versión ${escaparHTML(item.version)} · ${AppViews.date(item.at)}</p></div></li>`).join('')}</ul>`;
  };
  const deletionPanel = '<h2 id="delete-title">Eliminar mi cuenta</h2><p>Borraremos de inmediato y para siempre tu cuenta y todos sus datos: huertos, historial, avisos y consentimientos. Tus equipos quedarán libres. No hay periodo de espera ni forma de cancelarlo.</p><button class="button btn-liquid-light" type="button" data-danger="true" data-delete-open>Eliminar mi cuenta</button>';

  function mount(host) {
    host.innerHTML = `<section class="bento-panel privacy-panel" aria-labelledby="accepted-title"><h2 id="accepted-title">Documentos que aceptaste</h2><div data-accepted-list></div></section>
      <section class="bento-panel privacy-panel deletion-panel" aria-labelledby="delete-title" data-deletion-panel></section>
      <dialog class="bento-panel app-dialog" aria-labelledby="delete-dialog-title" data-delete-dialog><form data-delete-form novalidate>
        <h2 id="delete-dialog-title">¿Eliminar tu cuenta?</h2><p>Se borrarán tu cuenta, tu historial y tus consentimientos en este momento. No hay periodo de espera ni forma de recuperarla. Escribe tu contraseña para confirmar.</p>
        <label for="delete-password">Contraseña</label><input id="delete-password" name="password" type="password" autocomplete="current-password" required>
        <p class="auth-feedback is-error" role="alert" data-delete-error hidden></p>
        <div class="app-dialog-actions"><button class="button btn-liquid-light" type="button" data-delete-close>Cancelar</button><button class="button" type="submit" data-danger="true">Eliminar definitivamente</button></div></form></dialog>`;
    const list = host.querySelector('[data-accepted-list]'), panel = host.querySelector('[data-deletion-panel]');
    const dialog = host.querySelector('[data-delete-dialog]'), form = host.querySelector('[data-delete-form]'), error = form.querySelector('[data-delete-error]');
    return {panel, dialog, form,
      accepted(state) { list.innerHTML = accepted(state); },
      deletion() { panel.innerHTML = deletionPanel; },
      password: () => form.elements.password.value,
      openDialog() { form.reset(); error.hidden = true; dialog.showModal(); form.elements.password.focus(); },
      closeDialog() { form.reset(); if(dialog.open) dialog.close(); },
      busy(on) { form.querySelector('[type=submit]').disabled = on; },
      fail(code) { error.textContent = WRONG[code] || WRONG.unavailable; error.hidden = false; form.elements.password.focus(); }};
  }
  return Object.freeze({mount});
})();

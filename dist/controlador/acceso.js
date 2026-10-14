const AuthController = (() => {
  const actions = { acceso:'login', registro:'register', verificar:'verify', recuperar:'request-reset', restablecer:'reset', cambiar:'change-password' };
  const pendingLabels = { login:'Iniciando sesión…', register:'Enviando solicitud…', verify:'Verificando…', 'request-reset':'Enviando solicitud…', reset:'Guardando contraseña…', 'change-password':'Guardando contraseña…', resend:'Solicitando reenvío…' };
  function mount(screen, { root = document.getElementById('app'), service = AuthService, config = AuthConfig, context = {}, assets = '', embedded = false, onNavigate, onSessionConfirmed } = {}) {
    const lifetime = new AbortController();
    let request = null;
    let disposed = false;
    let busy = false;
    let serial = 0;
    let retryAt = 0;
    let resendAt = context.resendAt || 0;
    let expiresAt = context.expiresAt || 0;
    let expiredNotified = false;
    let resetToken = context.resetToken || '';
    let challengeId = context.challengeId || '';
    root.innerHTML = AuthViews.render(screen, { config, context, assets, embedded });
    const find = selector => root.querySelector(selector);
    const content = () => find('#auth-content');
    const values = () => Object.fromEntries(Array.from(root.querySelectorAll('input[name]')).map(input => [input.name, input.value]));
    const show = (text, error = false, focus = true) => {
      const box = find('#auth-feedback');
      if (!box) return;
      box.hidden = false;
      box.textContent = text;
      box.classList.toggle('is-error', error);
      box.classList.toggle('sr-only', busy);
      if (focus && !busy) box.focus({ preventScroll: false });
    };
    const setError = (name, message = '') => {
      const input = find(`[name="${name}"]`);
      if (!input) return;
      input.setAttribute('aria-invalid', String(Boolean(message)));
      const error = find(`#${name}-error`);
      error.textContent = message;
      error.hidden = !message;
    };
    function validate(resend = false) {
      const data = values();
      if (data.email !== undefined) {
        data.email = data.email.trim();
        find('#email').value = data.email;
      }
      const errors = AuthModel.validate(resend ? 'recuperar' : screen, data, config);
      const email = find('#email');
      if (email && !email.validity.valid) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
      for (const input of root.querySelectorAll('input[name]')) {
        if (resend && input.name !== 'email') continue;
        setError(input.name, errors[input.name]);
      }
      const first = Array.from(root.querySelectorAll('input[name]')).find(input => errors[input.name])?.name;
      if (first) {
        find('#access-errors').textContent = 'Revisa los campos indicados para continuar.';
        find(`[name="${first}"]`).focus();
        return null;
      }
      find('#access-errors').textContent = '';
      return data;
    }
    function tick() {
      if (disposed) return;
      const retry = AuthModel.secondsLeft(retryAt);
      const resend = AuthModel.secondsLeft(resendAt);
      const submit = find('[type="submit"]');
      const resendButton = find('[data-auth-action="resend"]');
      if (submit) submit.disabled = busy || retry > 0 || (screen === 'verificar' && expiresAt > 0 && Date.now() >= expiresAt);
      if (resendButton) resendButton.disabled = busy || retry > 0 || resend > 0;
      const wait = find('#auth-wait');
      if (wait) {
        wait.hidden = !retry && !resend;
        wait.textContent = retry ? `Inténtalo de nuevo en ${AuthModel.duration(retry)}.` : resend ? `Podrás solicitar otro código en ${AuthModel.duration(resend)}.` : '';
      }
      const expiry = find('#code-expiry');
      if (expiry && expiresAt) {
        const remaining = AuthModel.secondsLeft(expiresAt);
        expiry.hidden = !remaining;
        expiry.textContent = remaining ? `El código vence en ${AuthModel.duration(remaining)}.` : '';
        if (!remaining && !expiredNotified) {
          expiredNotified = true;
          setError('code', 'El código ha vencido. Solicita uno nuevo.');
          show('Solicita un código nuevo para continuar.', true, false);
        }
      }
    }
    function setBusy(value, action) {
      busy = value;
      if (!value) {
        const feedback = find('#auth-feedback');
        if (feedback) { feedback.hidden = true; feedback.textContent = ''; feedback.classList.remove('sr-only'); }
      }
      const form = find('form');
      form?.setAttribute('data-busy', String(value));
      root.querySelectorAll('input').forEach(input => { input.readOnly = value; });
      const submit = find('[type="submit"]');
      if (submit) {
        submit.setAttribute('aria-busy', String(value && action !== 'resend'));
        if (value && action !== 'resend') submit.innerHTML = `<span class="button-spinner" aria-hidden="true"></span>${pendingLabels[action]}`;
        else submit.textContent = submit.dataset.submitLabel;
      }
      const resend = find('[data-auth-action="resend"]');
      if (resend) {
        resend.setAttribute('aria-busy', String(value && action === 'resend'));
        resend.textContent = value && action === 'resend' ? pendingLabels.resend : 'Reenviar código';
      }
      tick();
    }
    function result(title, text, action, href) {
      content().innerHTML = AuthViews.message(title, text, action, href);
      const heading = find('#auth-title');
      heading.textContent = title;
      find('.auth-intro').hidden = true;
      find('.auth-result h2').hidden = true;
      find('.auth-result').focus();
      document.title = title + ' · El Chilito';
    }
    function apply(response = {}, action = actions[screen]) {
      const status = response.status;
      if (action === 'inspect-reset') {
        if (status === 'reset-valid') {
          content().innerHTML = AuthViews.form(screen, config, context);
          find('#password')?.focus();
        } else if (status === 'invalid-link' || status === 'expired-link') {
          resetToken = '';
          result('Este enlace ya no está disponible', 'El enlace no es válido o ha vencido. Solicita uno nuevo para recuperar el acceso.', 'Solicitar otro enlace', '#recuperar');
        } else {
          content().innerHTML = AuthViews.resetUnavailable();
          find('[role="alert"]')?.focus();
        }
        return;
      }
      if (status === 'limited') {
        retryAt = AuthModel.deadline(response.retryAfterSeconds);
        show('Has realizado demasiados intentos. Espera un momento antes de volver a intentarlo.', true);
      } else if (action === 'login' && status === 'invalid-credentials') {
        show('El correo o la contraseña no son correctos. Revisa tus datos e inténtalo de nuevo.', true);
      } else if (['register', 'request-reset'].includes(action) && status === 'accepted') {
        if (action === 'request-reset') {
          result('Revisa tu correo', 'Si existe una cuenta asociada a ese correo, recibirás instrucciones para recuperar el acceso.');
        } else {
          // Same public outcome for both new and existing addresses; only the server knows which applies.
          const next = {
            email: find('#email').value.trim(),
            challengeId: typeof response.challengeId === 'string' ? response.challengeId : '',
            expiresAt: AuthModel.expiry(response.expiresAt) || AuthModel.deadline(config.code.expiresAfterSeconds),
            resendAt: AuthModel.deadline(response.resendAfterSeconds ?? config.code.resendAfterSeconds)
          };
          find('form').reset();
          if (onNavigate) { onNavigate('verificar', next); return; }
        }
      } else if (action === 'verify' && status === 'verified') {
        find('form').reset();
        result('Correo verificado', 'La verificación de tu correo se completó.');
        if (response.sessionConfirmed === true && onSessionConfirmed) onSessionConfirmed(response);
      } else if (action === 'verify' && status === 'incorrect-code') {
        setError('code', 'El código no es correcto. Revísalo e inténtalo de nuevo.');
        show('No pudimos verificar ese código.', true, false);
        find('#code').focus();
      } else if (action === 'verify' && status === 'expired-code') {
        expiresAt = Date.now();
        expiredNotified = false;
      } else if (action === 'resend' && status === 'accepted') {
        if (typeof response.challengeId === 'string') challengeId = response.challengeId;
        resendAt = AuthModel.deadline(response.resendAfterSeconds ?? config.code.resendAfterSeconds);
        expiresAt = AuthModel.expiry(response.expiresAt) || AuthModel.deadline(config.code.expiresAfterSeconds);
        expiredNotified = false;
        setError('code');
        find('#code').value = '';
        show('Si la solicitud puede completarse, recibirás un nuevo código por correo.');
      } else if (action === 'reset' && status === 'reset-complete') {
        find('form').reset();
        resetToken = '';
        result('Contraseña actualizada', 'Ya puedes iniciar sesión con tu nueva contraseña.');
      } else if (action === 'reset' && ['invalid-link', 'expired-link'].includes(status)) {
        resetToken = '';
        result('Este enlace ya no está disponible', 'El enlace no es válido o ha vencido. Solicita uno nuevo para recuperar el acceso.', 'Solicitar otro enlace', '#recuperar');
      } else if (action === 'change-password' && status === 'password-changed') {
        find('form').reset();
        result('Contraseña actualizada', 'El cambio se completó correctamente.', 'Mi cuenta', '#cuenta');
      } else if (action === 'change-password' && status === 'incorrect-current-password') {
        setError('currentPassword', 'La contraseña actual no es correcta. Inténtalo de nuevo.');
        find('#currentPassword').focus();
      } else if (['register', 'reset', 'change-password'].includes(action) && status === 'password-rejected') {
        setError('password', 'La contraseña no cumple los requisitos. Revisa las indicaciones.');
        find('#password').focus();
      } else if (action === 'login' && status === 'authenticated') {
        find('form').reset();
        show('Inicio de sesión confirmado.');
        if (onSessionConfirmed) onSessionConfirmed(response);
      } else {
        show('El servicio no está disponible en este momento. Inténtalo de nuevo más tarde.', true);
      }
      tick();
    }
    async function send(action) {
      if (busy || AuthModel.secondsLeft(retryAt) || (action === 'resend' && AuthModel.secondsLeft(resendAt))) return;
      let payload = action === 'inspect-reset' ? { token: resetToken } : validate(action === 'resend');
      if (!payload) return;
      if (action === 'verify' && expiresAt && Date.now() >= expiresAt) { tick(); return; }
      // Confirmation is a client-side check only, never part of the proposed service payload.
      delete payload.confirmation;
      if (action === 'verify') payload.code = payload.code.trim();
      if (action === 'resend') payload = { email: payload.email };
      if (action === 'verify' || action === 'resend') payload.challengeId = challengeId;
      if (action === 'reset') payload.token = resetToken;
      const id = ++serial;
      request = new AbortController();
      const activeRequest = request;
      const abortRequest = () => activeRequest.abort();
      lifetime.signal.addEventListener('abort', abortRequest, { once: true });
      setBusy(true, action);
      if (action === 'inspect-reset') content().innerHTML = AuthViews.resetChecking();
      else show(pendingLabels[action], false, false);
      let timeout;
      let rejectAborted;
      try {
        const response = await Promise.race([
          service.request(action, payload, { signal: activeRequest.signal }),
          new Promise((_, reject) => {
            rejectAborted = () => reject(new DOMException('Cancelled', 'AbortError'));
            activeRequest.signal.addEventListener('abort', rejectAborted, { once:true });
            timeout = setTimeout(() => activeRequest.abort(), config.requestTimeoutMs);
          })
        ]);
        if (!disposed && id === serial) { setBusy(false, action); apply(response, action); }
      } catch {
        if (!disposed && id === serial) { setBusy(false, action); apply({ status: 'unavailable' }, action); }
      } finally {
        clearTimeout(timeout);
        activeRequest.signal.removeEventListener('abort', rejectAborted);
        lifetime.signal.removeEventListener('abort', abortRequest);
        for (const key of Object.keys(payload)) payload[key] = '';
        payload = null;
        if (!disposed) root.querySelectorAll('input[name="password"],input[name="currentPassword"],input[name="confirmation"]').forEach(input => { input.value = ''; });
      }
    }
    root.addEventListener('submit', event => {
      if (event.target.id !== 'access-form') return;
      event.preventDefault();
      send(actions[screen]);
    }, { signal: lifetime.signal });
    root.addEventListener('click', event => {
      const toggle = event.target.closest('[data-password-toggle]');
      if (toggle) {
        const input = find(`#${toggle.dataset.passwordToggle}`);
        const visible = input.type === 'password';
        input.type = visible ? 'text' : 'password';
        toggle.innerHTML = visible ? iconEyeOff : iconEye;
        const label = input.id === 'confirmation' ? 'confirmación de contraseña' : find(`label[for="${input.id}"]`).textContent.toLowerCase();
        toggle.setAttribute('aria-label', `${visible ? 'Ocultar' : 'Mostrar'} ${label}`);
        toggle.setAttribute('aria-pressed', String(visible));
      }
      const action = event.target.closest('[data-auth-action]')?.dataset.authAction;
      if (action === 'resend') send('resend');
      if (action === 'check-reset') send('inspect-reset');
    }, { signal: lifetime.signal });
    root.addEventListener('input', event => {
      if (!event.target.matches('input[name]')) return;
      const errors = AuthModel.validate(screen, values(), config);
      if (event.target.type === 'email' && !event.target.validity.valid) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
      if (event.target.getAttribute('aria-invalid') === 'true') setError(event.target.name, errors[event.target.name]);
      if (event.target.name === 'password' && find('#confirmation')?.hasAttribute('aria-invalid')) setError('confirmation', errors.confirmation);
      const summary = find('#access-errors');
      if (summary) summary.textContent = '';
    }, { signal: lifetime.signal });
    const keepFieldVisible = () => {
      const input = document.activeElement;
      if (!root.contains(input) || !input.matches('input,button')) return;
      const viewport = window.visualViewport;
      if (viewport && input.getBoundingClientRect().bottom > viewport.height + viewport.offsetTop - 20) input.scrollIntoView({block:'center'});
    };
    window.visualViewport?.addEventListener('resize', keepFieldVisible);
    const interval = setInterval(tick, 1000);
    if (screen === 'restablecer') {
      if (resetToken) send('inspect-reset');
      else apply({ status:'invalid-link' }, 'inspect-reset');
    }
    tick();
    return {
      present: apply,
      dispose() {
        disposed = true;
        serial++;
        lifetime.abort();
        clearInterval(interval);
        window.visualViewport?.removeEventListener('resize', keepFieldVisible);
        resetToken = '';
        root.querySelectorAll('input[type="password"],input[name="password"],input[name="currentPassword"],input[name="confirmation"],input[name="code"]').forEach(input => { input.value = ''; });
      }
    };
  }
  return { mount };
})();

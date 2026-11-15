// CONTROLADOR · Cuenta: acceso, segundo factor, perfil y privacidad personal.
// Define: AuthController, SecondStepController, MfaController, ProfileController, WelcomeController, MyPrivacyController, PrivacyController, WebAuthnBrowser.

// ── Mfa ──
// allauth decide; aquí solo se pide lo que falta y se muestra el resultado.
const WebAuthnBrowser = Object.freeze({
  supported: () => Boolean(window.PublicKeyCredential?.parseCreationOptionsFromJSON),
  async create(options) {
    const publicKey = PublicKeyCredential.parseCreationOptionsFromJSON(options.publicKey);
    return (await navigator.credentials.create({publicKey})).toJSON();
  },
  async get(options) {
    const publicKey = PublicKeyCredential.parseRequestOptionsFromJSON(options.publicKey);
    return (await navigator.credentials.get({publicKey})).toJSON();
  }
});

const SecondStepController = (() => {
  function mount({root, assets = '', onDone, onCancel, service = MfaService}) {
    let alive = true;
    const screen = MfaViews.secondStep(root, assets);
    (async () => {
      const step = await service.pending();
      if(!alive) return;
      if(!step) { onCancel(); return; }
      const view = screen.show(step.kind, step.types.includes('webauthn') && WebAuthnBrowser.supported());
      const fail = status => { view.fail(status); if(['conflict','unauthenticated'].includes(status)) onCancel(); };
      const finish = result => { service.finished(result) ? onDone() : fail(result.status === 'ok' ? 'unavailable' : result.status); };
      view.form.addEventListener('submit',async event => {
        event.preventDefault();
        const code = view.code();
        if(!code || view.isBusy()) return;
        view.busy(true);
        const result = await (step.kind === 'login_by_code' ? service.confirmCode(code) : service.authenticate(code));
        if(!alive) return;
        view.busy(false);
        finish(result);
      });
      view.key.addEventListener('click',async () => {
        const options = await service.webauthnRequest();
        if(options.status !== 'ok') { fail(options.status); return; }
        try { finish(await service.webauthnAuthenticate(await WebAuthnBrowser.get(options.data.request_options))); }
        catch { fail('unavailable'); }
      });
      view.cancel.addEventListener('click',async () => { await AuthService.logout(); onCancel(); });
    })();
    return {dispose() { alive = false; }};
  }
  return {mount};
})();

const MfaController = (() => {
  function mount({root, service = MfaService}) {
    const life = new AbortController();
    const view = MfaViews.accountScreen(root);
    const on = (node, type, fn) => node.addEventListener(type,fn,{signal:life.signal});
    const say = view.say;
    let retry = null;
    async function guarded(action, done) {
      const result = await action();
      if(life.signal.aborted) return;
      if(result.status === 'reauthentication-required') {
        retry = () => guarded(action,done);
        view.askPassword();
        return;
      }
      if(result.status === 'ok' || result.status === 'not-found') await done(result);
      else say(['invalid','limited'].includes(result.status) ? result.status : 'failed',true);
    }
    async function showNewCodes() {
      const codes = await service.recoveryView();
      if(codes.status === 'ok' && codes.data?.unused_codes?.length) view.showCodes(codes.data.unused_codes);
    }
    async function load() {
      const result = await service.list();
      if(life.signal.aborted) return;
      if(result.status === 'unauthenticated') { ChilitoHTTP.sessionExpired(); return; }
      if(result.status !== 'ok') { say('list-failed',true); return; }
      const items = result.data || [];
      const totp = items.find(item => item.type === 'totp');
      const keys = items.filter(item => item.type === 'webauthn');
      const recovery = items.find(item => item.type === 'recovery_codes');
      view.methods({totp, keys, recovery, strong:Boolean(totp || keys.length), mfaRequired:AuthService.session?.profile?.mfaRequired === true});
    }
    on(root,'click',event => {
      const remove = event.target.closest('[data-key-remove]');
      if(remove) guarded(() => service.webauthnRemove([Number(remove.dataset.keyRemove)]),async () => { say('key-removed'); load(); });
      const action = event.target.closest('[data-mfa]')?.dataset.mfa;
      if(action === 'totp-start') guarded(service.totpStart,async result => {
        view.totpSetup(result.meta?.secret, await service.totpImage());
      });
      if(action === 'totp-disable') guarded(service.totpDisable,async () => { say('totp-disabled'); load(); });
      if(action === 'recovery-regenerate') guarded(service.recoveryRegenerate,async result => { view.showCodes(result.data?.unused_codes || []); load(); });
    });
    on(view.reauthForm,'submit',async event => {
      event.preventDefault();
      const result = await service.reauthenticate(event.target.elements.password.value);
      view.clearForm(event.target);
      if(result.status !== 'ok') { say('wrong-password',true); return; }
      view.passwordConfirmed();
      const next = retry; retry = null; next?.();
    });
    on(view.totpForm,'submit',event => {
      event.preventDefault();
      const code = event.target.elements.code.value.trim();
      guarded(() => service.totpActivate(code),async () => {
        say('totp-enabled');
        view.clearForm(event.target);
        await AuthService.restore();
        await load();
        await showNewCodes();
      });
    });
    on(view.keyForm,'submit',event => {
      event.preventDefault();
      const name = event.target.elements.name.value.trim();
      if(!WebAuthnBrowser.supported()) { say('no-webauthn',true); return; }
      guarded(service.webauthnOptions,async options => {
        let credential;
        try { credential = await WebAuthnBrowser.create(options.data.creation_options); }
        catch { say('key-not-created',true); return; }
        const added = await service.webauthnAdd(name,credential);
        if(added.status !== 'ok') { say('key-not-saved',true); return; }
        say('key-added');
        view.clearForm(event.target);
        await AuthService.restore();
        await load();
        if(added.meta?.recovery_codes_generated) await showNewCodes();
      });
    });
    load();
    return {dispose() { life.abort(); }};
  }
  return {mount};
})();

// ── Perfil ──
const ProfileController = (() => {
  const names = ['firstName','lastName','alias'];
  function mount(host, data, {onSaved} = {}) {
    const view = ProfileViews.profileScreen(host);
    let saved = data, busy = false;
    const setBusy = active => { busy = active; view.busy(active); };
    view.facts(saved);
    view.edit.addEventListener('click',() => {
      view.fill(names,saved);
      view.say();
      view.editing(true);
    });
    view.cancel.addEventListener('click',() => {
      if(busy) return;
      view.fill(names,saved);
      view.say();
      view.editing(false);
    });
    view.form.addEventListener('submit',async event => {
      event.preventDefault();
      if(busy) return;
      setBusy(true);
      view.say('saving');
      const written = view.values(names);
      const result = await PrivacyData.saveProfile(written);
      if(result.status === 'unauthenticated') { ChilitoHTTP.sessionExpired(); return; }
      if(result.status !== 'accepted') { setBusy(false); view.say(result.status === 'limited' ? 'limited' : 'failed'); return; }
      const session = await AuthService.restore();
      if(!view.form.isConnected) return;
      const confirmed = session?.profile?.profile;
      saved = confirmed || Object.fromEntries(names.map(name => [name,written[name].trim()]));
      view.facts(saved);
      setBusy(false);
      view.editing(false);
      view.say('saved');
      onSaved?.(session);
    });
  }
  return {mount};
})();

const WelcomeController = (() => {
  function offer(root, session, onDone) {
    if(session?.profile?.profile?.welcomePending !== true) return;
    const view = ProfileViews.welcomeScreen(root);
    async function finish(payload) {
      const result = await PrivacyData.welcome(payload);
      if(result.status !== 'accepted') { view.failed(); return; }
      session.profile.profile.welcomePending = false;
      view.close();
      await AuthService.restore();
      onDone?.();
    }
    view.skip.addEventListener('click',() => finish({}));
    view.form.addEventListener('submit',event => {
      event.preventDefault();
      finish(view.values(['firstName','lastName','alias']));
    });
    view.open();
  }
  return {offer};
})();

const MyPrivacyController = (() => {
  const savedChoice = state => !state.decided ? '' : state.statistics ? 'yes' : 'no';
  function mount(host) {
    const view = ProfileViews.privacyScreen(host);
    let edited = false, saving = false;
    function sync() {
      const current = CookieController.status;
      const choice = savedChoice(current);
      view.sync({current, choice, keepSelection:edited, saving,
        changed: () => view.selected() !== '' && view.selected() !== choice});
    }
    view.consult.addEventListener('click',async () => {
      view.consulting(true);
      const data = await PrivacyData.myData();
      if(!view.consult.isConnected) return;
      view.consulting(false);
      if(data.status !== 'accepted' || !data.data) { view.myDataFailed(); return; }
      view.myData(data.data);
    });
    view.form.addEventListener('change',() => { edited = true; view.report(); sync(); });
    view.form.addEventListener('submit',async event => {
      event.preventDefault();
      if(saving || !view.selected()) return;
      saving = true;
      view.saving(true);
      sync();
      const stored = await CookieController.decide(view.selected() === 'yes');
      if(!view.form.isConnected) return;
      saving = false;
      view.saving(false);
      if(stored) edited = false;
      sync();
      view.report(stored ? 'stored' : 'failed');
    });
    const stop = CookieController.onChange(sync);
    sync();
    return {dispose: stop};
  }
  return {mount};
})();

const PrivacyController = (() => {
  function mount({root}) {
    const mine = MyPrivacyController.mount(PrivacyViews.mount(root));
    return {dispose() { mine.dispose(); }};
  }
  return {mount};
})();

// ── Acceso ──
const AuthController = (() => {
  const actions = { acceso:'login', registro:'register', verificar:'verify', recuperar:'request-reset', restablecer:'reset', cambiar:'change-password' };
  const pendingLabels = { login:'Iniciando sesión…', register:'Enviando solicitud…', verify:'Verificando…', 'request-reset':'Enviando solicitud…', reset:'Guardando contraseña…', 'change-password':'Guardando contraseña…', resend:'Solicitando reenvío…' };
  function mount(screen, { root = document.getElementById('app'), service = AuthService, config = AuthConfig, context = {}, assets = '', embedded = false, review = false, onNavigate, onSessionConfirmed } = {}) {
    const lifetime = new AbortController();
    let request = null;
    let disposed = false;
    let busy = false;
    let serial = 0;
    let retryAt = 0;
    let resendAt = context.resendAt || 0;
    let expiresAt = context.expiresAt || 0;
    let expiredNotified = false;
    let helpState = null, helpAnnouncementTimer;
    let resetToken = context.resetToken || '';
    const view = AuthViews.screen(root, screen, { config, context, assets, embedded, review });
    const values = view.values;
    const clearPasswords = () => {
      view.clearPasswords();
      refreshPasswordHelp();
    };
    const show = (text, error = false, focus = true) => view.show(text, error, focus, busy);
    const setError = view.setError;
    // Solo se avisa de los cambios de límite; el contador visible se sigue actualizando con cada escritura.
    function refreshPasswordHelp(announce = false) {
      if (disposed || !view.hasPasswordHelp()) return;
      const typed = view.passwordInputs();
      const progress = AuthModel.passwordProgress(typed.password, typed.confirmation, config, typed.email || AuthService.session?.profile?.email || '');
      view.passwordHelp(progress);
      const next = {range:progress.range, confirmation:progress.confirmation};
      const live = view.canAnnounce();
      const messages = [];
      if (announce && helpState) {
        if (next.range !== helpState.range) {
          if (next.range === 'within-range') messages.push('Mínimo alcanzado.');
          else if (next.range === 'over-maximum') messages.push(`Supera el máximo de ${progress.maxLength} caracteres.`);
          else if (progress.length > 0 && next.range === 'below-minimum') messages.push('Todavía faltan caracteres para el mínimo.');
        }
        if (next.confirmation !== helpState.confirmation && next.confirmation !== 'empty')
          messages.push(next.confirmation === 'matches' ? 'Las contraseñas coinciden.' : 'Las contraseñas todavía no coinciden.');
      }
      helpState = next;
      if (messages.length && live) {
        clearTimeout(helpAnnouncementTimer);
        view.announce('');
        helpAnnouncementTimer = setTimeout(() => {
          if (!disposed) view.announce(messages.join(' '));
        }, 400);
      } else if (!announce && live) {
        clearTimeout(helpAnnouncementTimer);
        view.announce('');
      }
    }
    function validate(resend = false) {
      const data = values();
      if (!data.email && context.email) {
        data.email = context.email;
      }
      if (data.email !== undefined) {
        data.email = data.email.trim();
        view.setEmail(data.email);
      }
      const errors = AuthModel.validate(resend ? 'recuperar' : screen, data, config);
      if (!view.emailValid()) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
      const names = view.names();
      for (const name of names) {
        if (resend && name !== 'email') continue;
        setError(name, errors[name]);
      }
      const first = names.find(name => errors[name]);
      if (first) {
        view.summary('Revisa los campos indicados para continuar.');
        view.focusField(first);
        return null;
      }
      view.summary('');
      return data;
    }
    function tick() {
      if (disposed) return;
      const retry = AuthModel.secondsLeft(retryAt);
      const resend = AuthModel.secondsLeft(resendAt);
      const tracksExpiry = Boolean(expiresAt) && view.hasExpiry();
      const remaining = tracksExpiry ? AuthModel.secondsLeft(expiresAt) : 0;
      view.timers({
        submitDisabled: busy || retry > 0 || (screen === 'verificar' && expiresAt > 0 && Date.now() >= expiresAt),
        resendDisabled: busy || retry > 0 || resend > 0,
        wait: retry ? `Inténtalo de nuevo en ${AuthModel.duration(retry)}.` : resend ? `Podrás solicitar otro código en ${AuthModel.duration(resend)}.` : '',
        expiry: !tracksExpiry ? null : remaining ? `El código vence en ${AuthModel.duration(remaining)}.` : ''
      });
      if (tracksExpiry && !remaining && !expiredNotified) {
        expiredNotified = true;
        setError('code', 'El código ha vencido. Solicita uno nuevo.');
        show('Solicita un código nuevo para continuar.', true, false);
      }
    }
    function setBusy(value, action) {
      busy = value;
      view.busy(value, action !== 'resend' ? pendingLabels[action] : null, action === 'resend' ? pendingLabels.resend : null);
      tick();
    }
    const result = view.result;
    function apply(response = {}, action = actions[screen]) {
      const status = response.status;
      if (action === 'inspect-reset') {
        if (status === 'reset-valid') {
          view.showResetForm(screen, config, context);
          refreshPasswordHelp();
          view.focusField('password');
        } else if (status === 'invalid-link' || status === 'expired-link') {
          resetToken = '';
          result('Este enlace ya no está disponible', 'El enlace no es válido o ha vencido. Solicita uno nuevo para recuperar el acceso.', 'Solicitar otro enlace', '#recuperar');
        } else {
          view.resetUnavailable();
        }
        return;
      }
      if (status === 'second-step') {
        onNavigate('segundo-paso',{});
      } else if (status === 'limited') {
        retryAt = AuthModel.deadline(response.retryAfterSeconds);
        show('Has realizado demasiados intentos. Espera un momento antes de volver a intentarlo.', true);
      } else if (status === 'csrf-failed') {
        show('La sesión del formulario ha cambiado. Recarga la página e inténtalo de nuevo.', true);
      } else if (status === 'unauthenticated') {
        result('Inicia sesión de nuevo', 'Tu sesión ya no está disponible.', 'Iniciar sesión', '#acceso');
      } else if (status === 'verification-expired') {
        result('Vuelve a iniciar sesión', 'La verificación ha vencido o ya no está disponible. Inicia sesión para solicitar un nuevo código.', 'Iniciar sesión', '#acceso');
      } else if (action === 'login' && status === 'verification-required') {
        onNavigate?.('verificar', {email:response.email,expiresAt:AuthModel.expiry(response.expiresAt)});
      } else if (action === 'login' && status === 'invalid-credentials') {
        show('El correo o la contraseña no son correctos. Revisa tus datos e inténtalo de nuevo.', true);
      } else if (action === 'register' && status === 'registration-disabled') {
        show('El registro no está disponible en este momento.', true);
      } else if (action === 'register' && status === 'email-not-authorized') {
        setError('email', 'Este correo no está autorizado para la prueba local. Revisa que coincida con la dirección que indicaste.');
        view.focusField('email');
      } else if (action === 'register' && status === 'mail-unavailable') {
        show('No fue posible completar el envío a este correo. Inténtalo más tarde o inicia sesión para solicitar otro código.', true);
      } else if (action === 'register' && status === 'invalid-registration') {
        setError('email', 'Revisa el correo y los datos del registro.');
        view.focusField('email');
      } else if (action === 'register' && ['terms-required','legal-version-changed'].includes(status)) {
        view.uncheck('termsAccepted');
        setError('termsAccepted', status === 'terms-required' ? 'Debes aceptar los Términos y condiciones para continuar' : 'Los términos han cambiado. Consulta el documento y vuelve a marcar la casilla para continuar.');
        view.focusField('termsAccepted');
      } else if (action === 'register' && status === 'privacy-required') {
        view.uncheck('privacyRead');
        setError('privacyRead', 'Debes confirmar que leíste el Aviso de privacidad para continuar');
        view.focusField('privacyRead');
      } else if (['register', 'request-reset'].includes(action) && status === 'accepted') {
        if (action === 'request-reset') {
          result('Revisa tu correo', 'Si existe una cuenta asociada a ese correo, recibirás instrucciones para recuperar el acceso.');

        } else {
          // El resultado público es el mismo para direcciones nuevas y existentes; solo el servidor sabe cuál aplica.
          const next = {
            email: view.emailValue(),
            expiresAt: AuthModel.expiry(response.expiresAt) || AuthModel.deadline(config.code.expiresAfterSeconds),
            resendAt: AuthModel.deadline(response.resendAfterSeconds ?? config.code.resendAfterSeconds)
          };
          view.resetForm();
          if (onNavigate) { onNavigate('verificar', next); return; }
        }
      } else if (action === 'verify' && status === 'verified') {
        view.resetForm();
        result('Correo verificado', 'La verificación de tu correo se completó.');
        if (response.sessionConfirmed === true && onSessionConfirmed) {
          result('Correo verificado', 'Tu correo está verificado. Puedes continuar a tu cuenta.', 'Mi huerto', '#huerto');
        }
      } else if (action === 'verify' && status === 'incorrect-code') {
        setError('code', 'El código no es correcto. Revísalo e inténtalo de nuevo.');
        show('No pudimos verificar ese código.', true, false);
        view.focusField('code');
      } else if (action === 'verify' && status === 'expired-code') {
        expiresAt = Date.now();
        expiredNotified = false;
      } else if (action === 'resend' && status === 'accepted') {
        resendAt = AuthModel.deadline(response.resendAfterSeconds ?? config.code.resendAfterSeconds);
        expiresAt = AuthModel.expiry(response.expiresAt) || expiresAt;
        expiredNotified = false;
        setError('code');
        view.clear('code');
        show('Si la solicitud puede completarse, recibirás un nuevo código por correo.');
      } else if (action === 'reset' && status === 'reset-complete') {
        view.resetForm();
        resetToken = '';
        result('Contraseña actualizada', 'Ya puedes iniciar sesión con tu nueva contraseña.');
      } else if (action === 'reset' && ['invalid-link', 'expired-link'].includes(status)) {
        resetToken = '';
        result('Este enlace ya no está disponible', 'El enlace no es válido o ha vencido. Solicita uno nuevo para recuperar el acceso.', 'Solicitar otro enlace', '#recuperar');
      } else if (action === 'change-password' && status === 'password-changed') {
        view.resetForm();
        result('Contraseña actualizada', 'El cambio se completó correctamente.', 'Mi cuenta', '#cuenta');
      } else if (action === 'change-password' && status === 'incorrect-current-password') {
        setError('currentPassword', 'La contraseña actual no es correcta. Inténtalo de nuevo.');
        view.focusField('currentPassword');
      } else if (['register', 'reset', 'change-password'].includes(action) && status === 'password-rejected') {
        setError('password', AuthModel.passwordRejection(response.reason));
        view.focusField('password');
      } else if (action === 'login' && status === 'authenticated') {
        view.resetForm();
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
      if (action === 'register' && config.registrationAllowed !== true) {
        clearPasswords();
        apply({status:'registration-disabled'}, action);
        return;
      }
      if (action === 'verify' && expiresAt && Date.now() >= expiresAt) { tick(); return; }
      // La confirmación solo se comprueba en el navegador y nunca forma parte de lo que se envía al servicio.
      delete payload.confirmation;
      if (action === 'verify') payload.code = payload.code.trim();
      if (action === 'resend') payload = { email: payload.email };
      if (action === 'reset') payload.token = resetToken;
      const id = ++serial;
      request = new AbortController();
      const activeRequest = request;
      const abortRequest = () => activeRequest.abort();
      lifetime.signal.addEventListener('abort', abortRequest, { once: true });
      setBusy(true, action);
      if (action === 'inspect-reset') view.resetChecking();
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
        if (!disposed) clearPasswords();
      }
    }
    root.addEventListener('submit', event => {
      if (event.target.id !== 'access-form') return;
      event.preventDefault();
      send(actions[screen]);
    }, { signal: lifetime.signal });
    root.addEventListener('click', event => {
      const toggle = event.target.closest('[data-password-toggle]');
      if (toggle) view.togglePassword(toggle);
      const action = event.target.closest('[data-auth-action]')?.dataset.authAction;
      if (action === 'resend') send('resend');
      if (action === 'check-reset') send('inspect-reset');

    }, { signal: lifetime.signal });
    root.addEventListener('input', event => {
      if (!event.target.matches('input[name]')) return;
      const errors = AuthModel.validate(screen, values(), config);
      if (event.target.type === 'email' && !event.target.validity.valid) errors.email = 'Escribe un correo válido, como nombre@dominio.com.';
      if (event.target.getAttribute('aria-invalid') === 'true') setError(event.target.name, errors[event.target.name]);
      refreshPasswordHelp(true);
      if (event.target.name === 'password' && view.isInvalid('confirmation')) setError('confirmation', errors.confirmation);
      view.summary('');
    }, { signal: lifetime.signal });
    root.addEventListener('change', () => refreshPasswordHelp(true), { signal: lifetime.signal });
    root.addEventListener('focusin', () => refreshPasswordHelp(), { signal: lifetime.signal });
    root.addEventListener('reset', () => queueMicrotask(() => refreshPasswordHelp()), { signal: lifetime.signal });
    refreshPasswordHelp();
    const keepFieldVisible = () => view.keepVisible(document.activeElement);
    window.visualViewport?.addEventListener('resize', keepFieldVisible);
    const interval = setInterval(tick, 1000);
    if (screen === 'restablecer') {
      if (resetToken) send('inspect-reset');
      else apply({ status:'invalid-link' }, 'inspect-reset');
    }
    if(context.feedback) show(context.feedback, true, false);
    tick();
    return {
      present: apply,
      dispose() {
        disposed = true;
        serial++;
        lifetime.abort();
        clearInterval(interval);
        clearTimeout(helpAnnouncementTimer);
        window.visualViewport?.removeEventListener('resize', keepFieldVisible);
        resetToken = '';
        view.clearSecrets();
      }
    };
  }
  return { mount };
})();

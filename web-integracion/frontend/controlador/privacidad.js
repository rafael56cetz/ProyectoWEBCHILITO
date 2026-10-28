const PrivacyController = (() => {
  function mount(route, {root,service=PrivacyService,config=AuthConfig,review=false} = {}) {
    const lifetime = new AbortController();
    const publicPage = route.screen === 'derechos-arco';
    const isDetail = route.privacyView !== 'list' && !publicPage;
    root.innerHTML = publicPage ? PrivacyViews.publicPage(review) : isDetail ? PrivacyViews.detailShell(review) : PrivacyViews.account(review);
    const content = root.querySelector('[data-privacy-content]');
    const formHost = root.querySelector('[data-form-host]');
    const flow = root.querySelector('.privacy-flow');
    if(service.available !== true) {
      const host = content || formHost;
      if(host) host.insertAdjacentHTML('afterbegin',PrivacyViews.availability());
      root.querySelectorAll('input,select,textarea,button').forEach(control=>{control.disabled=true;});
      return {dispose(){lifetime.abort();}};
    }
    let record = null, sequence = 0, busy = false;

    async function request(action, payload = {}) {
      const operation = new AbortController();
      let timer;
      const abort = () => operation.abort();
      lifetime.signal.addEventListener('abort',abort,{once:true});
      try {
        const cancelled = new Promise((_,reject) => {
          operation.signal.addEventListener('abort',()=>reject(new DOMException('Cancelled','AbortError')),{once:true});
          timer = setTimeout(abort,config.requestTimeoutMs);
        });
        return await Promise.race([service.request(action,payload,{signal:operation.signal}),cancelled]);
      } catch { return {status:'unavailable'}; }
      finally { clearTimeout(timer); lifetime.signal.removeEventListener('abort',abort); }
    }
    function feedback(form,text,error=false) {
      const element = form.querySelector('[data-form-feedback]');
      element.hidden = false;
      element.setAttribute('role',error?'alert':'status');
      element.textContent = text;
      return element;
    }
    function errors(form,messages) {
      for(const field of form.querySelectorAll('input,select,textarea')) {
        const message = messages[field.name];
        field.setAttribute('aria-invalid',String(Boolean(message)));
        const element = form.querySelector(`#arco-${field.name}-error`);
        element.textContent = message || '';
        element.hidden = !message;
      }
      if(Object.keys(messages).length) {
        feedback(form,'Revisa los campos indicados.',true);
        form.querySelector('[aria-invalid="true"]')?.focus();
        return true;
      }
      return false;
    }
    function setBusy(form,value) {
      busy = value;
      form.setAttribute('aria-busy',String(value));
      for(const control of form.querySelectorAll('input,select,textarea,button')) {
        control.disabled = value || (control.name === 'requestedCorrection' && form.querySelector('[name="right"]')?.value !== 'rectification');
      }
      const submit = form.querySelector('[type="submit"]');
      submit.textContent = value ? 'Enviando…' : form.dataset.privacyForm === 'create' ? 'Enviar solicitud' : 'Enviar información';
      submit.setAttribute('aria-busy',String(value));
    }
    async function load() {
      if(!content) return;
      const id = ++sequence;
      record = null;
      if(isDetail && (route.privacyView === 'invalid' || !PrivacyModel.validId(route.requestId))) {
        content.innerHTML = PrivacyViews.state('not-found');
        return;
      }
      content.innerHTML = PrivacyViews.state('loading');
      const result = await request(isDetail?'arco-detail':'arco-list',isDetail?{id:route.requestId}:{});
      if(lifetime.signal.aborted || id !== sequence) return;
      if(isDetail) {
        record = result?.status === 'ready' ? PrivacyModel.detail(result.request,route.requestId) : null;
        content.innerHTML = record ? PrivacyViews.detail(record) : PrivacyViews.state(PrivacyModel.failure(result));
      } else {
        const data = PrivacyModel.list(result);
        content.innerHTML = PrivacyViews.list(data);
        const toggle = flow.querySelector('[data-privacy-action="toggle-form"]');
        toggle.disabled = data.status === 'unauthenticated';
        if(toggle.disabled) { formHost.hidden = true; formHost.innerHTML = PrivacyViews.form(); toggle.setAttribute('aria-expanded','false'); }
      }
    }
    flow.addEventListener('submit',async event => {
      const form = event.target.closest('[data-privacy-form]');
      if(!form) return;
      event.preventDefault();
      if(busy) return;
      const creating = form.dataset.privacyForm === 'create';
      const raw = Object.fromEntries([...form.querySelectorAll('input,select,textarea')].filter(field=>!field.disabled).map(field=>[field.name,field.value]));
      const data = creating ? PrivacyModel.values(raw) : {message:(raw.message || '').trim()};
      const validation = creating ? PrivacyModel.validate(data) : data.message ? {} : {message:'Escribe la información que deseas aportar.'};
      if(errors(form,validation)) return;
      if(!creating && !record?.informationRequest?.canRespond) return;
      const id = record?.id;
      const payload = creating ? data : {id,informationRequestId:record.informationRequest.id,message:data.message};
      feedback(form,'Envío en curso. Espera la respuesta del servicio.');
      setBusy(form,true);
      const result = await request(creating?'arco-create':'arco-add-info',payload);
      if(lifetime.signal.aborted) return;
      setBusy(form,false);
      if(result?.status === 'validation-error') {
        if(!errors(form,PrivacyModel.fieldErrors(result,creating?PrivacyModel.fields:['message']))) feedback(form,'El servicio no validó la solicitud. Revisa la información e inténtalo de nuevo.',true).focus();
        return;
      }
      if(result?.status === 'accepted') {
        if(creating) {
          const receipt = PrivacyModel.receipt(result.receipt);
          if(receipt) {
            form.reset();
            formHost.innerHTML = PrivacyViews.receipt(receipt,review);
            formHost.querySelector('.privacy-receipt').focus();
            if(!publicPage) load();
            return;
          }
        } else {
          const updated = PrivacyModel.detail(result.request,id);
          if(updated) {
            form.reset();
            record = updated;
            content.innerHTML = '<p class="privacy-feedback" tabindex="-1" role="status">El servicio confirmó la recepción de la información.</p>' + PrivacyViews.detail(record);
            content.querySelector('[role="status"]').focus();
            return;
          }
        }
        feedback(form,'No se pudo confirmar la recepción: la respuesta del servicio está incompleta. No se ha mostrado un acuse válido. Comprueba el seguimiento antes de intentar otro envío.',true).focus();
        return;
      }
      const status = PrivacyModel.failure(result);
      if(!creating && ['unauthenticated','forbidden','not-found'].includes(status)) {
        record = null;
        content.innerHTML = PrivacyViews.state(status);
        content.tabIndex = -1; content.focus();
        return;
      }
      const message = status === 'unauthenticated' ? 'Tu sesión venció. Inicia sesión para continuar. El apartado público de derechos ARCO sigue disponible.' : 'El servicio no está disponible. No se ha confirmado la recepción de esta solicitud.';
      feedback(form,message,true).focus();
    },{signal:lifetime.signal});
    flow.addEventListener('change',event=>{
      if(event.target.name !== 'right') return;
      const form = event.target.form, correction = form.querySelector('[data-correction]'), field = form.elements.requestedCorrection;
      correction.hidden = event.target.value !== 'rectification';
      field.disabled = correction.hidden;
      if(correction.hidden) { field.value = ''; field.removeAttribute('aria-invalid'); form.querySelector('#arco-requestedCorrection-error').hidden = true; }
    },{signal:lifetime.signal});
    flow.addEventListener('click',async event=>{
      const target = event.target.closest('[data-privacy-action]');
      if(!target || busy) return;
      const action = target.dataset.privacyAction;
      if(action === 'reload') { await load(); if(!lifetime.signal.aborted) { content.tabIndex = -1; content.focus(); } }
      if(action === 'toggle-form') {
        formHost.hidden = !formHost.hidden;
        target.setAttribute('aria-expanded',String(!formHost.hidden));
        if(!formHost.hidden) formHost.querySelector('h2')?.focus();
      }
      if(action === 'new-form') { formHost.innerHTML = PrivacyViews.form(); formHost.querySelector('h2').focus(); }
    },{signal:lifetime.signal});
    const toggle = flow.querySelector('[data-privacy-action="toggle-form"]');
    if(toggle) { formHost.id = 'privacy-form-host'; toggle.setAttribute('aria-controls',formHost.id); toggle.setAttribute('aria-expanded','false'); }
    const keepVisible = () => {
      const focused = document.activeElement;
      // Safari can focus the surrounding main/section on pointer-down. Scrolling
      // that container before pointer-up would swallow the button's click.
      if(!flow.contains(focused) || focused.closest('.account-tabs') || !focused.matches('input,select,textarea,button,a,.privacy-feedback')) return;
      const viewport = window.visualViewport;
      const top = Math.max(viewport?.offsetTop || 0,root.closest('#app')?.querySelector('header')?.getBoundingClientRect().bottom || 0);
      const available = viewport ? viewport.offsetTop + viewport.height : innerHeight;
      const nav = document.querySelector('.sidebar');
      const isMobileNav = nav && getComputedStyle(nav).position === 'fixed' && window.innerWidth <= 768;
      const bottom = isMobileNav ? Math.min(nav.getBoundingClientRect().top,available) : available;
      const rect = focused.getBoundingClientRect();
      if(rect.top < top + 12 || rect.bottom > bottom - 12) {
        window.scrollBy({top:rect.top-(top+12)-Math.max(0,(bottom-top-24-rect.height)/2),behavior:'instant'});
      }
    };
    flow.addEventListener('focusin',keepVisible,{signal:lifetime.signal});
    window.visualViewport?.addEventListener('resize',keepVisible);
    load();
    return {dispose() {
      lifetime.abort(); sequence++; record = null;
      root.querySelectorAll('[data-privacy-form]').forEach(form=>form.reset());
      window.visualViewport?.removeEventListener('resize',keepVisible);
    }};
  }
  return {mount};
})();

const SecurityController = (() => {
  function mount(mode, {root,service=AuthService,config=AuthConfig,review=false,interaction=null,onBusy=()=>{},onContinue=()=>{},onPassword=()=>{}} = {}) {
    const lifetime = new AbortController();
    const unavailableLogin=mode==='login'&&service.passkeysAvailable!==true;
    root.hidden=unavailableLogin;
    if(unavailableLogin){root.innerHTML='';return {setBlocked(){},dispose(){lifetime.abort();}};}
    root.innerHTML = SecurityViews[mode](review);
    if(service.passkeysAvailable !== true) {
      root.querySelector('[data-key-operation]').innerHTML = SecurityViews.availability();
      root.querySelectorAll('[data-key-action]').forEach(button=>{
        button.disabled = true;
        button.setAttribute('aria-describedby','passkey-availability');
      });
      return {setBlocked(){},dispose(){lifetime.abort();}};
    }
    const flow = root.querySelector('.security-flow');
    const operationHost = flow.querySelector('[data-key-operation]');
    const listHost = flow.querySelector('[data-key-list]');
    let active = null, serial = 0, busy = false, blocked = false, completed = false;
    let data = {status:'loading'}, confirmId = null, confirmedSession = null;
    function controls() {
      for(const button of flow.querySelectorAll('[data-key-action]')) {
        const action = button.dataset.keyAction;
        button.disabled = !['cancel','password','skip','continue'].includes(action) && (busy || blocked);
        if(mode !== 'account' && ['create','login','skip'].includes(action)) button.hidden = completed;
      }
      flow.setAttribute('aria-busy',String(busy));
    }
    function setBusy(value) { busy = value; onBusy(value); controls(); }
    function phase(status,focus=false) {
      operationHost.innerHTML = SecurityViews.state(status,mode,review);
      controls();
      if(focus) operationHost.querySelector('.security-state')?.focus();
    }
    function drawList() { listHost.innerHTML = SecurityViews.list(data,confirmId); controls(); }
    function cancel(show=true) {
      serial++;
      active?.abort(); active = null;
      setBusy(false);
      if(show) phase('cancelled',true);
    }
    async function bounded(work,signal) {
      if(signal.aborted) throw new DOMException('Cancelled','AbortError');
      let timer, abort;
      try {
        const cancelled = new Promise((_,reject)=>{
          abort = ()=>reject(new DOMException('Cancelled','AbortError'));
          signal.addEventListener('abort',abort,{once:true});
          timer = setTimeout(()=>reject(new Error('Service timeout')),config.requestTimeoutMs);
        });
        return await Promise.race([work(),cancelled]);
      } finally { clearTimeout(timer); signal.removeEventListener('abort',abort); }
    }
    async function run(task) {
      if(busy || blocked || lifetime.signal.aborted) return;
      const id = ++serial;
      const controller = new AbortController();
      active = controller;
      const abort = ()=>controller.abort();
      lifetime.signal.addEventListener('abort',abort,{once:true});
      const alive = ()=>!lifetime.signal.aborted && id === serial;
      const request = (action,payload={})=>bounded(()=>service.request(action,payload,{signal:controller.signal}),controller.signal);
      async function load() {
        data = {status:'loading'}; confirmId = null; drawList();
        const response = await request('passkey-list');
        if(alive()) { data = PasskeyModel.list(response); drawList(); }
      }
      setBusy(true);
      try { await task({request,load,alive,signal:controller.signal}); }
      catch {
        if(alive()) {
          if(data.status === 'loading' && listHost) { data={status:'unavailable'}; drawList(); }
          else phase('unavailable',true);
        }
      } finally {
        // Also abort unfinished work after a timeout; late answers are never applied.
        controller.abort();
        lifetime.signal.removeEventListener('abort',abort);
        if(alive()) { active = null; setBusy(false); }
      }
    }
    function loadList() { return run(async({load})=>{ operationHost.innerHTML=''; await load(); }); }
    function begin(purpose) {
      return run(async({request,load,alive,signal})=>{
        phase(purpose==='login'?'preparing':'preparing-create');
        const response = await request(`passkey-${purpose}-begin`);
        if(!alive()) return;
        const operation = PasskeyModel.operation(response);
        if(!operation) {
          phase(response?.status==='ready'?'error':PasskeyModel.failure(response),true); return;
        }
        // No browser device API exists in this delivery. Only the explicit local
        // review may inject this synthetic interaction; URL flags cannot enable it.
        if(!review || typeof interaction !== 'function') { phase('unavailable',true); return; }
        phase('device');
        const result = await bounded(()=>interaction({operationId:operation.id,purpose,signal}),signal);
        if(!alive()) return;
        if(result?.status !== 'completed') { phase(PasskeyModel.failure(result),true); return; }
        if(result.response?.demonstration !== true) { phase('error',true); return; }
        if(Date.now() >= operation.expiresAt) { phase('expired-operation',true); return; }
        phase('checking');
        const finish = await request(`passkey-${purpose}-finish`,{operationId:operation.id,response:result.response});
        if(!alive()) return;
        if(purpose === 'login') {
          if(PasskeyModel.sessionConfirmed(finish)) { confirmedSession=finish; completed=true; phase('authenticated',true); }
          else phase(PasskeyModel.failure(finish),true);
        } else {
          const credential = PasskeyModel.created(finish);
          if(!credential) { phase(PasskeyModel.failure(finish),true); return; }
          completed = mode === 'offer';
          phase('created',true);
          if(mode === 'account') await load();
        }
      });
    }
    function revoke(id) {
      if(!data.items?.some(item=>item.id === id) || confirmId !== id) return;
      return run(async({request,load,alive})=>{
        phase('revoking');
        const response = await request('passkey-revoke',{id});
        if(!alive()) return;
        confirmId = null;
        if(PasskeyModel.revoked(response,id)) { phase('revoked',true); await load(); }
        else { drawList(); phase(PasskeyModel.failure(response),true); }
      });
    }
    flow.addEventListener('click',event=>{
      const button = event.target.closest('[data-key-action]');
      if(!button || button.disabled) return;
      const action = button.dataset.keyAction;
      if(action === 'skip') { cancel(false); onContinue(); return; }
      if(action === 'password') { cancel(false); operationHost.innerHTML=''; onPassword(); return; }
      if(action === 'cancel') { cancel(); return; }
      if(action === 'continue' && completed) { onContinue(confirmedSession); return; }
      if(busy || blocked) return;
      if(action === 'login') begin('login');
      if(action === 'create') begin('register');
      if(action === 'reload') loadList();
      if(action === 'remove' && data.items?.some(item=>item.id === button.dataset.keyId)) {
        confirmId = button.dataset.keyId; drawList(); flow.querySelector('.key-confirmation h4').focus();
      }
      if(action === 'cancel-remove') {
        const id = confirmId; confirmId = null; drawList();
        [...flow.querySelectorAll('[data-key-action="remove"]')].find(button=>button.dataset.keyId === id)?.focus();
      }
      if(action === 'confirm-remove') revoke(button.dataset.keyId);
    },{signal:lifetime.signal});
    const keepVisible = ()=>{
      const focused = document.activeElement;
      if(!flow.contains(focused) || focused.closest('.account-tabs') || !focused.matches('button,a,.security-state')) return;
      const viewport = window.visualViewport;
      const header = document.querySelector('.site-header');
      const top = Math.max(viewport?.offsetTop || 0,header?.getBoundingClientRect().bottom || parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--review-height')) || 0);
      const available = viewport ? viewport.offsetTop+viewport.height : innerHeight;
      const nav = document.querySelector('.sidebar');
      const isMobileNav = nav && getComputedStyle(nav).position === 'fixed' && window.innerWidth <= 768;
      const bottom = isMobileNav ? Math.min(nav.getBoundingClientRect().top,available) : available;
      const rect = focused.getBoundingClientRect();
      if(rect.top < top+12 || rect.bottom > bottom-12) window.scrollBy({top:rect.top-top-12-Math.max(0,(bottom-top-24-rect.height)/2),behavior:'instant'});
    };
    flow.addEventListener('focusin',keepVisible,{signal:lifetime.signal});
    window.visualViewport?.addEventListener('resize',keepVisible);
    if(mode === 'account') loadList();
    return {
      setBlocked(value) { blocked=value; controls(); },
      dispose() {
        lifetime.abort(); serial++; active?.abort(); active=null; data=null; confirmId=null; confirmedSession=null;
        window.visualViewport?.removeEventListener('resize',keepVisible);
      }
    };
  }
  return {mount};
})();

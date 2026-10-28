const AdminController = (() => {
  function mount(screen,{root,service=AdminService}={}) {
    const life=new AbortController();
    let selected=null, data={status:'loading'}, pending=null, origin=null, draft=null, disposed=false,working=false,serial=0;
    const dialog=()=>root.querySelector('.admin-dialog');
    function feedback(message,error=false) {
      const el=root.querySelector('#admin-feedback');
      if(!el)return;
      el.hidden=false;el.textContent=message;el.setAttribute('role',error?'alert':'status');el.focus();
    }
    const errorText=status=>({
      'forbidden':'Tu cuenta no tiene acceso a esta operación.',
      'not-found':'Selecciona un reporte disponible antes de continuar.',
      'no-permission':'No hay una autorización vigente para este reporte. Solicita un token nuevo a la persona usuaria.',
      'wrong-report':'El token corresponde a otro reporte. Utiliza la autorización específica de este caso.',
      'invalid-token':'El token es incorrecto. Comprueba el código compartido por la persona usuaria.',
      'invalid-version':'Introduce una versión válida de 3 a 64 caracteres: letras, números, puntos, guiones o guiones bajos.',
      'same-version':'Esa versión ya está en servicio. Indica una versión destino diferente.',
      'invalid-notes':'Las notas deben tener un máximo de 2000 caracteres.',
      'validation-required':'Valida la versión y sus notas antes de solicitar la publicación.',
      'invalid-knowledge':'El contenido debe tener entre 20 y 10 000 caracteres.'
    }[status]||'No se pudo completar la operación. Inténtalo de nuevo.');
    function closeDialog(returnFocus=true) {
      if(dialog()?.open)dialog().close();
      pending=null;
      if(returnFocus&&origin?.isConnected)origin.focus();
      origin=null;
    }
    function formDraft() {
      const form=root.querySelector('[data-admin-release-form]');
      if(!form)return null;
      return Object.fromEntries(new FormData(form));
    }
    function render(preserve=false) {
      const release=preserve?formDraft():null;
      root.innerHTML=AdminViews.render(screen,data);
      if(release)for(const [key,value]of Object.entries(release)) {
        const input=root.querySelector('[data-admin-release-form]')?.elements.namedItem(key);
        if(input)input.value=value;
      }
      dialog()?.addEventListener('cancel',event=>{event.preventDefault();closeDialog();},{signal:life.signal});
    }
    async function load({message='',error=false,focusDetail=false,preserve=true}={}) {
      if(disposed)return;
      const id=++serial;
      try {data=await service.snapshot(selected,screen);}catch {data={status:'error'};}
      if(disposed||id!==serial)return;
      render(preserve);
      draft=null;
      if(focusDetail)root.querySelector('#admin-ticket-detail')?.focus();
      if(message)feedback(message,error);
    }
    async function result(response,message) {
      await load({message:response.status==='accepted'?message:errorText(response.status),error:response.status!=='accepted'});
    }
    function openDialog(action,trigger) {
      if(dialog()?.open)return;
      if(action==='publish'&&!draft){feedback(errorText('validation-required'),true);return;}
      origin=trigger;pending={action,draft:draft?{...draft}:null,ticket:selected};
      dialog().querySelector('[data-admin-dialog-content]').innerHTML=AdminViews.confirmation(action,draft?.version||'');
      dialog().showModal();dialog().querySelector('[data-admin-action="cancel-dialog"]').focus();
    }
    root.addEventListener('click',async event=>{
      const trigger=event.target.closest('[data-admin-action]');if(!trigger||working)return;
      const action=trigger.dataset.adminAction;
      if(action==='cancel-dialog'){closeDialog();return;}
      if(action==='confirm-dialog'){
        if(!pending)return;
        const request=pending;
        closeDialog(false);
        working=true;
        let response;try{response=await (request.action==='publish'?service.requestRelease(request.draft):request.action==='restart-node'?service.restartNode(request.ticket):service.restartPlatform());}finally{working=false;}
        if(disposed)return;
        await result(response,request.action==='publish'?'Solicitud de publicación registrada. Sin confirmación del servicio.':request.action==='restart-node'?'Solicitud registrada. Sin confirmación del dispositivo.':'Solicitud de mantenimiento registrada. Sin confirmación del servicio.');return;
      }
      if(action==='refresh'){await load({message:'Consulta actualizada.'});return;}
      if(action==='open-ticket'){
        working=true;let response;try{response=await service.selectTicket(trigger.dataset.ticket);}finally{working=false;}
        if(disposed)return;
        if(response.status!=='accepted'){feedback(errorText(response.status),true);return;}
        selected=trigger.dataset.ticket;await load({focusDetail:true});return;
      }
      if(action==='request-token'){
        await result(await service.requestToken(selected),'Solicitud de token registrada. El acceso sigue bloqueado; la persona usuaria debe autorizar este reporte.');return;
      }
      if(action==='close-remote'){await result(await service.closeRemote(),'Sesión técnica cerrada. Los registros vuelven a estar bloqueados.');return;}
      if(action==='refresh-diagnostics'){await result(await service.refreshDiagnostics(selected),'Consulta de diagnóstico registrada.');return;}
      if(['publish','restart-node','restart-platform'].includes(action))openDialog(action,trigger);
    },{signal:life.signal});
    root.addEventListener('submit',async event=>{
      const form=event.target;
      if(!form.matches('[data-admin-token-form],[data-admin-release-form],[data-admin-knowledge-form]'))return;
      event.preventDefault();if(working||!form.reportValidity())return;
      const fields=Object.fromEntries(new FormData(form));
      if(form.matches('[data-admin-token-form]')){
        await result(await service.validateToken(selected,fields.token),'Token válido para este reporte. El diagnóstico autorizado está disponible.');return;
      }
      if(form.matches('[data-admin-knowledge-form]')){
        await result(await service.saveKnowledge(fields.knowledge),'Revisión de conocimientos guardada.');return;
      }
      working=true;let response;try{response=await service.validateRelease(fields);}finally{working=false;}
      if(disposed)return;
      draft=response.status==='accepted'?fields:null;
      const state=root.querySelector('#admin-release-state');
      state.textContent=draft?'Validación guardada en el servidor. Ya puedes solicitar la publicación.':errorText(response.status);
      state.setAttribute('role',draft?'status':'alert');
      root.querySelector('[data-admin-action="publish"]').disabled=!draft;
    },{signal:life.signal});
    root.addEventListener('input',event=>{
      if(event.target.closest('[data-admin-release-form]')){
        draft=null;root.querySelector('[data-admin-action="publish"]').disabled=true;
        root.querySelector('#admin-release-state').textContent='Los datos cambiaron. Valida de nuevo antes de solicitar la publicación.';
      }
      if(event.target.id==='admin-knowledge')root.querySelector('#admin-knowledge-count').textContent=event.target.value.length;
    },{signal:life.signal});
    const checkExpiry=()=>{
      if(disposed||!data.remote||data.remote.expiresAt>Date.now())return;
      closeDialog(false);service.closeRemote();data.remote=null;data.diagnostics=null;
      render(true);feedback('La autorización ha vencido. El acceso técnico se cerró.');
    };
    const timer=setInterval(checkExpiry,1000);
    document.addEventListener('visibilitychange',checkExpiry,{signal:life.signal});
    render();load({preserve:false});
    return {dispose(){disposed=true;serial++;clearInterval(timer);closeDialog(false);if(screen==='soporte')service.closeRemote();life.abort();}};
  }
  return {mount};
})();

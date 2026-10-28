const UserGardenController = (() => {
  function mount(screen,{root,service=UserGardenService,detail='',onData=()=>{}}={}) {
    const life = new AbortController();
    let data={garden:AppModel.garden({status:'loading'})},range='1h',serial=0,pending=null,origin=null,disposed=false,working=false;
    const current=()=>root.querySelector('.user-dialog');
    function feedback(text,error=false) {
      const node=root.querySelector('#user-feedback');if(!node)return;
      node.hidden=false;node.textContent=text;node.setAttribute('role',error?'alert':'status');node.focus();
    }
    function closeDialog() {
      const dialog=current();if(dialog?.open)dialog.close();
      pending=null;
      if(origin?.isConnected)origin.focus();
      origin=null;
    }
    function render() {
      root.innerHTML=UserGardenViews.render(screen,data);
      const dialog=current();
      dialog?.addEventListener('cancel',e=>{e.preventDefault();if(!working)closeDialog();},{signal:life.signal});
    }
    async function load({message='',error=false,focusRange=false}={}) {
      const id=++serial;
      try {
        const response=await service.load(range,{signal:life.signal});
        if(disposed||id!==serial)return;
        data=response;onData(response);render();
        if(message)feedback(message,error);
        else if(focusRange)root.querySelector(`[data-range="${range}"]`)?.focus();
        else if(detail==='sustrato') {
          const guide=root.querySelector('#user-substrate-guide');if(guide){guide.open=true;guide.scrollIntoView({block:'center'});guide.querySelector('summary').focus();}
        } else if(detail==='historial') {
          const list=root.querySelector('#user-maintenance-history');list?.scrollIntoView({block:'start'});list?.focus();
        }
      }catch {
        if(disposed||id!==serial)return;
        data={garden:AppModel.garden({status:'error'})};render();
      }
    }
    function openDialog(action,trigger) {
      const dialog=current();if(!dialog||dialog.open)return;
      origin=trigger;pending=action;
      dialog.querySelector('[data-user-dialog-content]').innerHTML=UserGardenViews.confirmation(action);
      dialog.showModal();dialog.querySelector('[data-user-action="cancel-dialog"]').focus();
    }
    async function confirm() {
      if(!pending||working)return;
      const selected=pending;
      const consent=root.querySelector('#user-support-consent');
      if(selected==='support'&&!consent?.checked)return;
      working=true;
      current().querySelectorAll('button').forEach(b=>b.disabled=true);
      try {
        const response=selected==='support'?await service.issuePermission(data.selectedIncident,consent.checked,{signal:life.signal}):await service.command(selected,data,{signal:life.signal});
        if(disposed)return;
        closeDialog();
        if(response.status==='accepted')await load({message:selected==='support'?(response.tokenAvailable?'Tu token de soporte está disponible. Puedes copiarlo o revocar la autorización.':'La autorización está registrada. El token solo se entrega una vez; si no lo conservas, revoca y genera otra autorización.'):'Solicitud registrada. Esperando confirmación del dispositivo.'});
        else feedback(response.status==='unavailable'?'La emisión de tokens de soporte no está disponible en este momento.':response.status==='offline'?'No se envió la solicitud. Revisa la conexión Wi-Fi y MQTT del huerto.':response.status==='low-water'?'No se solicitó el riego. Revisa el nivel del depósito antes de continuar.':'No se pudo completar la solicitud. Inténtalo de nuevo.',true);
      } catch {
        if(!disposed){closeDialog();feedback('No se pudo completar la solicitud. Inténtalo de nuevo.',true);}
      } finally {working=false;}
    }
    root.addEventListener('click',async e=>{
      const trigger=e.target.closest('[data-user-action]');if(!trigger||working)return;
      const action=trigger.dataset.userAction;
      if(action==='cancel-dialog'){closeDialog();return;}
      if(action==='confirm-dialog'){await confirm();return;}
      if(action==='range'){range=trigger.dataset.range;await load({focusRange:true});return;}
      if(action==='refresh'){await load({message:'Información actualizada.'});return;}
      if(action.startsWith('record-')){
        working=true;let response;try{response=await service.recordTask(action.slice(7),{signal:life.signal});}catch{response={status:'error'};}finally{working=false;}
        if(disposed)return;
        await load({message:response.status==='accepted'?`${response.label} registrada.`:'No se pudo registrar la tarea.',error:response.status!=='accepted'});return;
      }
      if(['water','lamp-off','lamp-auto'].includes(action)){openDialog(action,trigger);return;}
      if(action==='revoke'){const response=await service.revokePermission({signal:life.signal});if(disposed)return;await load({message:response.status==='accepted'?'Autorización revocada. El acceso técnico permanece cerrado.':'No se pudo confirmar la revocación. Inténtalo de nuevo.',error:response.status!=='accepted'});return;}
      if(action==='copy-token'){
        const permission=service.permission();
        if(!permission||typeof permission.token!=='string'){await load({message:'El token solo se entrega al emitir la autorización. Si no lo conservas, revoca y genera una nueva.',error:true});return;}
        try{await navigator.clipboard.writeText(permission.token);if(!disposed)feedback('Token copiado. Compártelo únicamente con el personal de soporte.');}
        catch{if(!disposed)feedback('No se pudo copiar automáticamente. Selecciona y copia el código que aparece en pantalla.',true);}return;
      }
    },{signal:life.signal});
    root.addEventListener('submit',e=>{
      if(!e.target.matches('[data-user-support-form]'))return;
      e.preventDefault();if(!e.target.reportValidity())return;
      if(!service.supportAvailable){feedback('La emisión de tokens de soporte no está disponible en este momento.',true);return;}
      data.selectedIncident=new FormData(e.target).get('incident');
      openDialog('support',e.target.querySelector('button[type="submit"]'));
    },{signal:life.signal});
    root.addEventListener('change',e=>{
      if(e.target.id==='user-support-consent')current().querySelector('[data-user-action="confirm-dialog"]').disabled=!e.target.checked;
    },{signal:life.signal});
    const checkPermission=()=>{
      if(screen!=='soporte'||disposed||!data.permission)return;
      if(!service.permission())load({message:'La autorización ha vencido. El acceso técnico permanece cerrado.'});
    };
    const timer=setInterval(checkPermission,1000);
    document.addEventListener('visibilitychange',checkPermission,{signal:life.signal});
    render();load();
    return {dispose(){disposed=true;serial++;clearInterval(timer);closeDialog();life.abort();}};
  }
  return {mount};
})();

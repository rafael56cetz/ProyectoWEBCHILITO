const SecurityViews = (() => {
  const escape = authEscape;
  const button = (action,label,primary=false,extra='') => `<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-key-action="${action}" ${extra}>${label}</button>`;
  const explanation = () => '<p>Inicia sesión de forma rápida y segura utilizando la huella digital, el reconocimiento facial o el PIN de bloqueo de tu teléfono o computadora.</p><p>Las llaves de acceso se sincronizan de forma segura mediante tu cuenta según tu dispositivo y proveedor.</p>';
  const notice = () => '';
  function account(review) {
    const tabs = '<nav class="account-tabs" aria-label="Apartados de mi cuenta"><a class="button btn-liquid-light" href="#cuenta">Perfil</a><a class="button btn-liquid-brand active" href="#cuenta/seguridad" aria-current="page">Seguridad</a><a class="button btn-liquid-light" href="#cuenta/privacidad">Privacidad</a></nav>';
    return `<div class="security-flow">${AppViews.heading('Seguridad','Administra tus métodos de acceso.')}${tabs}<section class="bento-panel"><h2>Contraseña</h2><p>Puedes seguir entrando con tu correo y contraseña.</p><a class="button btn-liquid-light" href="#cuenta/contrasena">Cambiar contraseña</a></section><section class="bento-panel security-keys" aria-labelledby="security-keys-title"><h2 id="security-keys-title">Llaves de acceso</h2>${explanation()}<div class="security-actions">${button('create','Crear llave de acceso',true)}</div><div data-key-operation></div><div data-key-list></div></section></div>`;
  }
  function login(review) {
    return `<div class="security-flow"><div class="form-divider"><span>o también</span></div><h2 id="passkey-access-title" class="sr-only">Llave de acceso</h2>${button('login', `${icon('key')} Acceder con huella o PIN (Llave de acceso)`, false, 'class="button btn-liquid-light full"')}<div data-key-operation></div></div>`;
  }
  function offer(review) {
    return `<div class="security-flow security-offer"><h2>¿Quieres crear una llave de acceso?</h2><p>Tu correo está verificado y el servicio confirmó una sesión válida. Puedes preparar otra forma de entrar o hacerlo después desde Seguridad.</p>${explanation()}<div class="security-actions">${button('create','Crear llave de acceso',true)}${button('skip','Ahora no')}</div><div data-key-operation></div></div>`;
  }
  function state(status,mode='account',review=false) {
    const copy = {
      loading:['Cargando llaves','Consultando tus métodos de acceso.'],
      empty:['Aún no has vinculado llaves de acceso','Puedes registrar la huella, rostro o PIN de este dispositivo para entrar más rápido.'],
      error:['No se pudo completar la operación','Inténtalo de nuevo o continúa con tu correo y contraseña.'],
      unavailable:['Servicio no disponible','No podemos completar esta consulta u operación en este momento. Puedes intentarlo de nuevo o continuar con tu correo y contraseña.'],
      unauthenticated:['Sesión vencida','Inicia sesión para continuar con la gestión de tus métodos de acceso.'],
      'reauthentication-required':['Verifica tu identidad de nuevo','El servicio requiere volver a verificar tu identidad antes de continuar. Este paso todavía está pendiente de integración.'],
      'recovery-required':['Asegura una vía de recuperación','El servicio requiere asegurar una forma de recuperar el acceso antes de continuar. El procedimiento está pendiente de definición.'],
      'verification-required':['Verificación requerida','El servicio requiere completar la verificación del correo antes de continuar.'],
      cancelled:['Operación cancelada','Puedes intentarlo de nuevo o continuar con tu correo y contraseña. Si un envío ya había comenzado, consulta la lista antes de repetirlo.'],
      'not-supported':['Método no compatible o no disponible','Puedes continuar con tu correo y contraseña.'],
      'expired-operation':['La operación venció','Vuelve a intentarlo para preparar una operación nueva.'],
      rejected:['No se pudo quitar la llave','La operación no fue confirmada. La llave sigue en la lista.'],
      preparing:['Preparando el acceso','Espera mientras se prepara la operación.'],
      'preparing-create':['Preparando la creación','Espera mientras se prepara la operación.'],
      device:['Esperando la interacción con el dispositivo','Confirmando acceso con tu dispositivo...'],
      checking:['Comprobando el resultado','Espera la confirmación del servicio.'],
      revoking:['Quitando la llave','La lista cambiará únicamente si el servicio confirma la operación.'],
      created:['Llave de acceso vinculada','El servicio confirmó la creación.'],
      revoked:['Llave de acceso eliminada','El servicio confirmó que se quitó la llave.'],
      authenticated:['Acceso confirmado','El servicio confirmó una sesión válida.']
    }[status] || ['No se pudo completar la operación','Inténtalo de nuevo.'];
    const pending = ['loading','preparing','preparing-create','device','checking','revoking'].includes(status);
    const success = ['created','revoked','authenticated'].includes(status);
    const error = !pending && !success && status !== 'empty';
    return `<div class="security-state${error?' is-error':''}" role="${error?'alert':'status'}" tabindex="-1" ${pending?'aria-busy="true"':''}><h3>${copy[0]}</h3><p>${copy[1]}</p><div class="security-actions">${pending && status!=='loading'?button('cancel','Cancelar operación'):''}${mode==='login' && !pending && status!=='authenticated'?button('password','Usar correo y contraseña'):''}${status==='authenticated'||(mode==='offer' && status==='created')?button('continue','Continuar a Mi huerto',true):''}${mode==='account' && ['error','unavailable','cancelled','rejected','expired-operation'].includes(status)?button('reload','Consultar lista de nuevo'):''}${mode==='account' && status==='unauthenticated'?'<a class="button btn-liquid-light" href="#acceso">Iniciar sesión</a>':''}</div></div>`;
  }
  const date = (value,missing) => value ? AppViews.date(value) : escape(missing);
  function list(data,confirmId=null) {
    if(data.status !== 'ready') return state(data.status);
    return `<ul class="security-list">${data.items.map((item,index)=>`<li><h3>${item.name?escape(item.name):'Nombre no disponible'}</h3><dl class="security-facts"><div><dt>Creación</dt><dd>${date(item.createdAt,'Fecha no disponible')}</dd></div><div><dt>Último uso</dt><dd>${date(item.lastUsedAt,'Sin información de último uso')}</dd></div></dl>${item.id===confirmId?`<div class="key-confirmation" role="group" aria-labelledby="remove-key-title-${index}"><h4 id="remove-key-title-${index}" tabindex="-1">¿Quitar esta llave de acceso?</h4><p>Dejará de estar disponible para entrar a El Chilito cuando el servicio confirme la operación. El servicio comprobará si necesitas verificar tu identidad o asegurar una vía de recuperación.</p><div class="security-actions">${button('confirm-remove','Quitar llave',true,`data-key-id="${escape(item.id)}"`)}${button('cancel-remove','Conservar llave',false,`data-key-id="${escape(item.id)}"`)}</div></div>`:button('remove','Quitar llave',false,`data-key-id="${escape(item.id)}" aria-label="Quitar llave${item.name?': '+escape(item.name):' sin nombre disponible'}"`)}</li>`).join('')}</ul>`;
  }
  return {account,login,offer,state,list,
    availability() { return '<div class="security-state bento-panel" id="passkey-availability" role="status"><h3>Llaves de acceso aún no disponibles</h3><p>Por ahora, inicia sesión con tu correo y contraseña. La creación de llaves se habilitará más adelante.</p></div>'; }
  };
})();

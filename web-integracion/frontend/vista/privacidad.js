const PrivacyViews = (() => {
  const escape = authEscape;
  const action = (name,label,primary=false) => `<button type="button" class="button ${primary?'btn-liquid-brand':'btn-liquid-light'}" data-privacy-action="${name}">${label}</button>`;
  const pending = () => '';
  const links = () => `<nav class="privacy-actions" aria-label="Información de privacidad" style="display:flex;gap:0.65rem;flex-wrap:wrap;margin:1rem 0;"><a class="button btn-liquid-light" href="#privacidad">Aviso de privacidad</a><a class="button btn-liquid-light" href="#terminos">Términos y condiciones</a><a class="button btn-liquid-light" href="#derechos-arco">Derechos ARCO</a></nav>`;
  function field(name,label,help,control) {
    return `<div class="privacy-field" data-field="${name}"><label for="arco-${name}">${label}</label><p id="arco-${name}-help" class="privacy-help">${help}</p>${control}<p id="arco-${name}-error" class="privacy-error" hidden></p></div>`;
  }
  const attrs = name => `id="arco-${name}" name="${name}" aria-describedby="arco-${name}-help arco-${name}-error"`;
  function form() {
    return `<section class="bento-panel privacy-form-panel" aria-labelledby="arco-form-title"><h2 id="arco-form-title" tabindex="-1">Plantear una solicitud</h2><p id="arco-form-help">Completa los campos requeridos para registrar y dar seguimiento a tu solicitud de derechos ARCO.</p>
      <form data-privacy-form="create" novalidate aria-describedby="arco-form-help">
        ${field('requesterName','Nombre de la persona solicitante','Escribe el nombre tal como deseas presentarlo.',`<input ${attrs('requesterName')} autocomplete="off" required>`)}
        ${field('contactEmail','Correo de contacto','Ingresa el correo electrónico donde recibirás respuesta a tu solicitud.',`<input ${attrs('contactEmail')} type="email" autocomplete="off" inputmode="email" required>`)}
        ${field('right','Tipo de solicitud','Si tienes dudas, elige «No sé cuál corresponde».',`<select ${attrs('right')} required><option value="">Selecciona una opción</option>${Object.entries(PrivacyModel.rights).map(([value,label])=>`<option value="${value}">${escape(label)}</option>`).join('')}</select>`)}
        ${field('description','Descripción de la solicitud','Explica qué deseas conocer, corregir, cancelar o a qué tratamiento deseas oponerte.',`<textarea ${attrs('description')} rows="4" required></textarea>`)}
        <div data-correction hidden>${field('requestedCorrection','Corrección solicitada','Describe qué información consideras incorrecta y cómo debería corregirse.',`<textarea ${attrs('requestedCorrection')} rows="3" required disabled></textarea>`)}</div>
        ${field('accountRelation','Relación con una cuenta (opcional)','Por ejemplo: «Tengo una cuenta» o «No tengo cuenta». No escribas una contraseña.',`<input ${attrs('accountRelation')} autocomplete="off">`)}
        <div class="privacy-feedback" data-form-feedback role="status" tabindex="-1" hidden></div>
        <button class="button btn-liquid-brand" type="submit">Enviar solicitud</button>
      </form></section>`;
  }
  function publicPage(review) {
    const explanations = {access:'Solicitar conocer los datos personales tratados.',rectification:'Solicitar corregirlos.',cancellation:'Solicitar su cancelación.',opposition:'Solicitar oponerse a determinados tratamientos.'};
    return `${siteHeader({extra:'legal-header',action:'<a class="button compact btn-liquid-light" href="#acceso">Iniciar sesión</a>'})}<main class="legal-content container privacy-flow" id="contenido" tabindex="-1"><h1>Derechos ARCO</h1><p>Puedes plantear una solicitud sobre tus datos sin iniciar sesión, crear una cuenta o aceptar los términos del registro.</p>${pending(review)}<div class="privacy-rights">${Object.entries(explanations).map(([key,description])=>`<section class="bento-panel"><h2>${PrivacyModel.rights[key]}</h2><p>${description}</p></section>`).join('')}</div><div data-form-host>${form()}</div>${links()}</main>${publicFooter()}`;
  }
  function account(review) {
    const tabs = '<nav class="account-tabs" aria-label="Apartados de mi cuenta"><a class="button btn-liquid-light" href="#cuenta">Perfil</a><a class="button btn-liquid-light" href="#cuenta/seguridad">Seguridad</a><a class="button btn-liquid-brand active" href="#cuenta/privacidad" aria-current="page">Privacidad</a></nav>';
    return `<div class="privacy-flow">${AppViews.heading('Privacidad','Consulta la información de privacidad y el seguimiento de tus solicitudes.')}${tabs}${pending(review)}<div class="privacy-actions" style="margin-top:1rem">${action('toggle-form','Plantear una solicitud',true)}</div>${links()}<div data-form-host hidden>${form()}</div><section aria-labelledby="privacy-list-title"><h2 id="privacy-list-title">Mis solicitudes</h2><div data-privacy-content></div></section></div>`;
  }
  function detailShell(review) {
    return `<div class="privacy-flow">${AppViews.heading('Solicitud ARCO')}${pending(review)}<nav class="privacy-actions" aria-label="Seguimiento"><a href="#cuenta/privacidad">Todas mis solicitudes</a></nav><div data-privacy-content></div></div>`;
  }
  function state(status) {
    const copy = {
      loading:['Cargando solicitudes','Consultando el servicio.'],
      empty:['No tienes solicitudes registradas','Tus solicitudes de derechos ARCO aparecerán aquí una vez enviadas.'],
      unavailable:['Servicio no disponible','No se pudo consultar el seguimiento. Esto no significa que no tengas solicitudes.'],
      unauthenticated:['Sesión vencida','Inicia sesión para consultar tus solicitudes. El apartado público de derechos ARCO sigue disponible.'],
      forbidden:['Acceso no autorizado','No tienes autorización para consultar esta solicitud.'],
      'not-found':['Solicitud no disponible','No se encontró una solicitud disponible con este identificador.']
    }[status];
    return `<div class="bento-panel privacy-state" role="${['unavailable','unauthenticated','forbidden','not-found'].includes(status)?'alert':'status'}" ${status==='loading'?'aria-busy="true"':''}><h3>${copy[0]}</h3><p>${copy[1]}</p>${status==='unavailable'?action('reload','Reintentar'):status==='unauthenticated'?'<a class="button btn-liquid-brand" href="#acceso">Iniciar sesión</a>':''}</div>`;
  }
  function facts(item) {
    return `<dl class="privacy-facts"><div><dt>Folio</dt><dd>${escape(item.reference)}</dd></div><div><dt>Estado</dt><dd>${escape(PrivacyModel.states[item.state])}</dd></div><div><dt>Recepción</dt><dd>${AppViews.date(item.receivedAt)}</dd></div></dl>`;
  }
  function list(data) {
    if(data.status !== 'ready') return state(data.status);
    return `<p role="status">${data.items.length} solicitudes disponibles.</p><ul class="privacy-list">${data.items.map(item=>`<li class="bento-panel"><h3>${escape(PrivacyModel.rights[item.right])}</h3>${facts(item)}<a class="button btn-liquid-light" href="#cuenta/privacidad/solicitudes/${encodeURIComponent(item.id)}">Consultar solicitud<span class="sr-only"> ${escape(item.reference)}</span></a></li>`).join('')}</ul>`;
  }
  function detail(item) {
    const info = item.informationRequest;
    return `<article class="bento-panel"><h2>${escape(PrivacyModel.rights[item.right])}</h2>${facts(item)}<p>${escape(item.publicSummary)}</p><p>Última actualización: ${AppViews.date(item.updatedAt)}</p><h3>Historial</h3><ol class="privacy-history">${item.history.map(entry=>`<li><strong>${escape(PrivacyModel.states[entry.state])}</strong> · ${AppViews.date(entry.at)}<p>${escape(entry.publicMessage)}</p></li>`).join('')}</ol>${info?`<section class="privacy-information" aria-labelledby="arco-information-title"><h3 id="arco-information-title">Información solicitada</h3><p>${escape(info.message)}</p>${info.canRespond?`<form data-privacy-form="information" novalidate>${field('message','Tu respuesta','Describe la aclaración. No adjuntes documentos ni incluyas información sensible.',`<textarea ${attrs('message')} rows="4" required></textarea>`)}<div class="privacy-feedback" data-form-feedback role="status" tabindex="-1" hidden></div><button class="button btn-liquid-brand" type="submit">Enviar información</button></form>`:'<p>No se admite una respuesta desde este apartado en este momento.</p>'}</section>`:''}</article>`;
  }
  function receipt(item, review = false) {
    return `<section class="bento-panel privacy-receipt" role="status" tabindex="-1"><h2>Solicitud registrada</h2>${facts(item)}<p>Conserva el folio como referencia para consultar el seguimiento de tu solicitud.</p>${action('new-form','Plantear otra solicitud')}</section>`;
  }
  function availability() { return '<div class="bento-panel privacy-state" role="status"><h3>Solicitudes ARCO aún no disponibles</h3><p>El envío y seguimiento de solicitudes se habilitarán más adelante. Puedes consultar el Aviso de privacidad y la información sobre tus derechos.</p></div>'; }
  return {availability,publicPage,account,detailShell,form,state,list,detail,receipt};
})();

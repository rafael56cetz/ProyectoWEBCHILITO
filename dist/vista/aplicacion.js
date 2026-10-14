const AppViews = (() => {
  const escape = authEscape;
  const date = value => `<time${value && Number.isFinite(new Date(value).getTime()) ? ` datetime="${escape(new Date(value).toISOString())}"` : ''}>${escape(AppModel.date(value))}</time>`;
  const heading = (title,intro='') => `<div class="page-heading"><div><h1>${escape(title)}</h1>${intro?`<p>${escape(intro)}</p>`:''}</div></div>`;
  const state = (title,text,loading=false,retry=false) => `<div class="app-state bento-panel" role="${retry?'alert':'status'}"${loading?' aria-busy="true"':''}><span class="icon-medallion">${icon(loading?'clock':'info')}</span><h2>${escape(title)}</h2><p>${escape(text)}</p>${retry?'<button class="button btn-liquid-brand" type="button" data-app-action="reload">Reintentar</button>':''}</div>`;
  function shell(route) {
    const navigation=AppModel.destinations.map(item=>`<a class="button btn-liquid-sidebar" href="#${item.id}"${route.screen===item.id?' aria-current="page"':''}>${icon(item.icon)}<span>${item.label}</span></a>`).join('');
    return `${siteHeader({extra:'app-header',brandHref:'#huerto',brandLabel:'El Chilito, mi huerto',action:'<button class="button compact btn-liquid-light" type="button" data-app-action="logout">Cerrar sesión</button>'})}<div class="private-layout"><aside class="sidebar" id="garden-navigation"><nav class="private-nav" aria-label="Navegación de la aplicación">${navigation}</nav></aside><div class="private-content"><main class="dashboard container" id="contenido" tabindex="-1"><div id="app-feedback" role="status" tabindex="-1" hidden></div><div id="app-page"></div></main></div></div>`;
  }
  function noticeCard(item) {
    const importance={high:'Alta',medium:'Media',info:'Informativa'}[item.importance];
    return `<article class="bento-panel notice-card" data-notice-id="${escape(item.id)}"><div class="notice-meta"><span class="notice-condition ${item.condition}">${item.condition==='active'?'Activo':'Resuelto'}</span><span class="read-state">${item.read?'Leído':'No leído'}</span></div><h2>${escape(item.title)}</h2><p>${escape(item.description)}</p><dl class="notice-facts"><div><dt>Zona</dt><dd>${escape(item.zone)}</dd></div><div><dt>Importancia</dt><dd>${importance}</dd></div><div><dt>Fecha</dt><dd>${date(item.createdAt)}</dd></div></dl><a class="button btn-liquid-light" href="#avisos/${encodeURIComponent(item.id)}">Ver detalle<span class="sr-only">: ${escape(item.title)}</span></a></article>`;
  }
  function notices(data, filter='all', detail=null) {
    if(detail) {
      const item=data.items.find(item=>item.id===detail);
      if(data.status==='loading')return heading('Avisos')+state('Cargando aviso','Consultando su información.',true);
      if(data.status==='error')return heading('Avisos')+state('No se pudo consultar el aviso','Inténtalo de nuevo.',false,true);
      if(!item)return heading('Aviso no disponible')+`<div class="bento-panel"><p>Este aviso no está disponible.</p><a class="button btn-liquid-light" href="#avisos">Todos los avisos</a></div>`;
      return heading('Detalle del aviso')+`<article class="bento-panel notice-detail"><div class="notice-meta"><span class="notice-condition ${item.condition}">${item.condition==='active'?'Activo':'Resuelto'}</span><span class="read-state">${item.read?'Leído':'No leído'}</span></div><h2>${escape(item.title)}</h2><p>${escape(item.description)}</p><dl class="notice-facts"><div><dt>Zona</dt><dd>${escape(item.zone)}</dd></div><div><dt>Importancia</dt><dd>${{high:'Alta',medium:'Media',info:'Informativa'}[item.importance]}</dd></div><div><dt>Fecha</dt><dd>${date(item.createdAt)}</dd></div>${item.resolvedAt?`<div><dt>Resolución</dt><dd>${date(item.resolvedAt)}</dd></div>`:''}</dl><div class="notice-recommendation"><h3>Recomendación</h3><p>${escape(item.recommendation)}</p></div><div class="app-actions">${!item.read?`<button class="button btn-liquid-brand" data-app-action="mark-read" data-id="${escape(item.id)}" type="button">Marcar como leído</button>`:''}<a class="button btn-liquid-light" href="#avisos">Todos los avisos</a></div></article>`;
    }
    const filters=`<div class="notice-filters" role="group" aria-label="Filtrar avisos">${[['all','Todos'],['active','Activos'],['resolved','Resueltos']].map(([id,label])=>`<button class="button ${filter===id?'btn-liquid-brand':'btn-liquid-light'}" type="button" data-filter="${id}" aria-pressed="${filter===id}">${label}</button>`).join('')}</div>`;
    const items=AppModel.filterNotices(data.items,filter);
    let body;
    if(data.status==='loading')body=state('Cargando avisos','Consultando los avisos del huerto.',true);
    else if(data.status==='error')body=state('No se pudieron consultar los avisos','Inténtalo de nuevo para revisar los avisos.',false,true);
    else if(!items.length)body=state(filter==='all'?'No hay avisos para mostrar':'No hay avisos en este filtro','Los avisos de cultivo y comunicación aparecerán aquí cuando estén disponibles.');
    else body=`<div class="notices-grid">${items.map(noticeCard).join('')}</div>`;
    return heading('Avisos','Revisa lo que necesita atención en tu huerto.')+filters+`<p class="sr-only" role="status">${data.status==='ready'?`${items.length} avisos en este filtro.`:''}</p>`+body;
  }
  function account(data) {
    if(data.status==='loading')return heading('Mi cuenta')+state('Cargando cuenta','Consultando la información de tu cuenta.',true);
    if(data.status==='error')return heading('Mi cuenta')+state('No se pudo consultar tu cuenta','Inténtalo de nuevo.',false,true);
    return heading('Mi cuenta','Tu información de acceso.')+`<section class="bento-panel account-profile" aria-labelledby="profile-title"><span class="icon-medallion">${icon('user')}</span><h2 id="profile-title">Datos de la cuenta</h2><dl class="profile-facts"><div><dt>Correo electrónico</dt><dd>${data.email?escape(data.email):'Esperando información de la cuenta'}</dd></div><div><dt>Verificación del correo</dt><dd>${data.verified===true?'Correo verificado':data.verified===false?'Correo sin verificar':'Sin información disponible'}</dd></div></dl><div class="app-actions"><a class="button btn-liquid-brand" href="#cuenta/contrasena">Cambiar contraseña</a><button class="button btn-liquid-light" type="button" data-app-action="logout">Cerrar sesión</button></div></section>`;
  }
  return {shell,heading,state,date,notices,account,
    assistant(){return heading('Asistente')+`<section class="bento-panel assistant-panel" aria-label="Disponibilidad del asistente"><span class="icon-medallion">${icon('sparkle')}</span><p>Aquí podrás consultar orientación para cuidar tu huerto y comprender sus avisos. La asistencia con inteligencia artificial se incorporará en una próxima etapa.</p></section>`;},
    reading(raw,unit){return `<strong class="${raw.value==null?'absent':''}">${raw.value==null?'—':escape(AppModel.number(raw.value))}${raw.value==null?'':`<small>${unit}</small>`}</strong>`;},
    readingNote(raw){return raw.quality==='invalid'?'Lectura inválida. Revisa este sensor.':raw.value==null?'Aún no hay lecturas disponibles.':`Última lectura: ${date(raw.at)}`;}
  };
})();

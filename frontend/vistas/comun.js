// VISTA · Común: iconos, escape de HTML, plantilla del panel y calendario de filtros. Va primero entre las vistas.
// Define: icons, icon, iconEye, iconEyeOff, escaparHTML, mostrarAviso, confirmar, AppViews, DateFilterViews, AdminTableViews.

// ── Componentes ──
const icons={leaf:'<path d="M19 4C9 3 3 8 5 15s14 4 14-11Z"/><path d="M4 21 15 9M7 16h6"/>',drop:'<path d="M12 3C9 8 5 11 5 15a7 7 0 0 0 14 0c0-4-4-7-7-12Z"/><path d="M9 15a3 3 0 0 0 3 3"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',temp:'<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z"/><path d="M12 8v9"/>',bell:'<path d="M5 17h14l-2-4V9a5 5 0 0 0-10 0v4l-2 4Zm5 3h4"/>',user:'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',play:'<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4V8Z"/>',arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',wifi:'<path d="M3 8a15 15 0 0 1 18 0M6 12a10 10 0 0 1 12 0m-9 4a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r=".7"/>',off:'<path d="m3 3 18 18M3 8a15 15 0 0 1 5-2m6-1a15 15 0 0 1 7 3M6 12a10 10 0 0 1 6-2m-3 6a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r=".7"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',tank:'<path d="M6 5h12l2 4v11H4V9l2-4Zm3 0V2h6v3M4 13h16"/>',check:'<path d="m5 12 4 4L19 6"/>',alert:'<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4m0 3v.5"/>',plus:'<path d="M12 4v16M4 12h16"/>',sparkle:'<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/>',shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',key:'<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3M18.5 4.5l3 3"/>',mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',external:'<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',list:'<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r=".8"/><circle cx="4.5" cy="12" r=".8"/><circle cx="4.5" cy="18" r=".8"/>',inbox:'<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5.5 5h13L21 13v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5l2.5-8Z"/>',refresh:'<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 3v5h5"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 21v-5h-5"/>'};
Object.assign(icons, {
 calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h2M12 14h2M7 18h2M12 18h2"/>',
 panel:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>',
 home:'<path d="M3 11.5 12 4l9 7.5M5.5 9.5V20h13V9.5M10 20v-6h4v6"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>',
 logout:'<path d="M10 4H4v16h6M10 12h11m-4-4 4 4-4 4"/>',
 activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
 tool:'<path d="m14.5 6.5 3 3M21 4a6 6 0 0 1-8 7.5L5.5 19a2 2 0 0 1-3-3l7.5-7.5A6 6 0 0 1 17.5 1L14 4.5l2.5 2.5L20 3.5Z"/>',
 support:'<path d="M4 14v-3a8 8 0 0 1 16 0v3M4 12H3v6h4v-6H4Zm16 0h1v6h-4v-6h3ZM20 18v1a3 3 0 0 1-3 3h-4"/>',
 terminal:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>',
 chip:'<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx=".5"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
 tag:'<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
 book:'<path d="M12 6c-2-1.5-5-2-8-2v14c3 0 6 .5 8 2 2-1.5 5-2 8-2V4c-3 0-6 .5-8 2Z"/><path d="M12 6v14"/>',
 document:'<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
 clipboard:'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1Z"/><path d="m9 13 2 2 4-4"/>',
 users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20v-1a6.5 6.5 0 0 1 13 0v1M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14a6.5 6.5 0 0 1 3.5 5.8V20"/>',
 layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
 sprout:'<path d="M12 21v-9"/><path d="M12 12c0-4-3-6-7-6 0 4 3 6 7 6Z"/><path d="M12 14c0-4 3-7 7-7 0 4-3 7-7 7Z"/>',
 eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
 pencil:'<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
 minus:'<path d="M5 12h14"/>'
});
const icon=name=>`<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.leaf}</svg>`;
const iconEye=`<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>`;
const iconEyeOff=`<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.447 10.447 0 0 1-1.449 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg>`;

// ── Escape de html ──
const escaparHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));

// ── Avisos y confirmación ──
// Aviso flotante (3.5). Vive en la capa superior para verse también sobre un diálogo modal. Solo hay uno por tipo de
// anuncio (estado o alerta): el nuevo reemplaza al anterior. El texto entra siempre con textContent.
const mostrarAviso = (() => {
  let zona = null;
  const temporizadores = new Map();
  function crearZona() {
    zona = document.createElement('div');
    zona.className = 'aviso-zona';
    zona.popover = 'manual';
    for(const rol of ['status','alert']) {
      const region = document.createElement('div');
      region.dataset.aviso = rol;
      region.setAttribute('role',rol);
      zona.append(region);
    }
    document.body.append(zona);
  }
  return function mostrarAviso(tipo,texto) {
    const nombre = tipo in AvisoModel.tipos ? tipo : 'info';
    const regla = AvisoModel.tipos[nombre];
    if(!zona) crearZona();
    // Volver a abrir la zona la sube sobre cualquier diálogo abierto después.
    if(zona.matches(':popover-open')) zona.hidePopover();
    zona.showPopover();
    const region = zona.querySelector(`[data-aviso="${regla.rol}"]`);
    const aviso = document.createElement('div');
    aviso.className = `aviso aviso--${nombre}`;
    aviso.tabIndex = -1;
    const cuerpo = document.createElement('span');
    cuerpo.textContent = texto;
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'aviso-cerrar';
    cerrar.setAttribute('aria-label','Cerrar aviso');
    cerrar.innerHTML = icon('close');
    const retirar = () => { clearTimeout(temporizadores.get(region)); aviso.remove(); };
    cerrar.addEventListener('click',retirar);
    aviso.insertAdjacentHTML('afterbegin',icon(regla.icono));
    aviso.append(cuerpo,cerrar);
    clearTimeout(temporizadores.get(region));
    region.replaceChildren(aviso);
    if(regla.ms) temporizadores.set(region,setTimeout(retirar,regla.ms));
    return aviso;
  };
})();

// Confirmación estándar (3.6): título en pregunta, consecuencia y dos botones. Resuelve true solo si se confirma;
// cancelar, Esc o cerrar resuelven false. El foco vuelve a donde estaba.
const confirmar = (() => {
  let dialogo = null;
  function crear() {
    dialogo = document.createElement('dialog');
    dialogo.className = 'bento-panel app-dialog confirmar-dialogo';
    dialogo.setAttribute('aria-labelledby','confirmar-titulo');
    dialogo.setAttribute('aria-describedby','confirmar-texto');
    dialogo.innerHTML = '<h2 id="confirmar-titulo"></h2><p id="confirmar-texto"></p><div class="app-dialog-actions"><button class="button btn-liquid-light" type="button" data-confirmar="cancelar">Cancelar</button><button class="button" type="button" data-confirmar="aceptar"></button></div>';
    dialogo.addEventListener('click',evento => {
      const eleccion = evento.target.closest('[data-confirmar]')?.dataset.confirmar;
      if(eleccion) dialogo.close(eleccion);
    });
    document.body.append(dialogo);
  }
  return function confirmar({titulo,texto,accion,peligro = false}) {
    if(!dialogo) crear();
    const previo = document.activeElement;
    const aceptar = dialogo.querySelector('[data-confirmar="aceptar"]');
    dialogo.querySelector('#confirmar-titulo').textContent = titulo;
    dialogo.querySelector('#confirmar-texto').textContent = texto;
    aceptar.textContent = accion;
    aceptar.className = peligro ? 'button' : 'button btn-liquid-brand';
    if(peligro) aceptar.dataset.danger = 'true';
    else delete aceptar.dataset.danger;
    return new Promise(resolver => {
      dialogo.addEventListener('close',() => {
        resolver(dialogo.returnValue === 'aceptar');
        previo?.focus({preventScroll:true});
      },{once:true});
      dialogo.returnValue = '';
      dialogo.showModal();
      dialogo.querySelector('[data-confirmar="cancelar"]').focus();
    });
  };
})();

// Contraseña para confirmar una acción crítica (M-2). Resuelve la contraseña escrita, o null si se cancela.
const pedirContrasena = (() => {
  let dialogo = null;
  function crear() {
    dialogo = document.createElement('dialog');
    dialogo.className = 'bento-panel app-dialog confirmar-dialogo';
    dialogo.setAttribute('aria-labelledby','reautenticar-titulo');
    dialogo.innerHTML = '<form method="dialog" class="dialog-form" novalidate><h2 id="reautenticar-titulo">Confirma tu contraseña</h2><p id="reautenticar-texto">Esta acción es sensible. Escribe tu contraseña para continuar; no te la volveremos a pedir durante 5 minutos.</p>'
      + '<label for="reautenticar-clave">Contraseña</label><input id="reautenticar-clave" name="password" type="password" autocomplete="current-password" maxlength="256" required>'
      + '<div class="app-dialog-actions"><button class="button btn-liquid-light" type="button" data-reautenticar="cancelar">Cancelar</button><button class="button btn-liquid-brand" type="submit" value="aceptar">Confirmar</button></div></form>';
    dialogo.addEventListener('click',evento => { if(evento.target.closest('[data-reautenticar="cancelar"]')) dialogo.close('cancelar'); });
    document.body.append(dialogo);
  }
  return function pedirContrasena() {
    if(!dialogo) crear();
    const previo = document.activeElement, campo = dialogo.querySelector('#reautenticar-clave');
    campo.value = '';
    return new Promise(resolver => {
      dialogo.addEventListener('close',() => {
        const clave = dialogo.returnValue === 'aceptar' && campo.value ? campo.value : null;
        campo.value = '';
        resolver(clave);
        previo?.focus({preventScroll:true});
      },{once:true});
      dialogo.returnValue = '';
      dialogo.showModal();
      campo.focus();
    });
  };
})();

// ── Panel ──
const AppViews = (() => {
  const date = value => `<time${value && Number.isFinite(new Date(value).getTime()) ? ` datetime="${escaparHTML(new Date(value).toISOString())}"` : ''}>${escaparHTML(AppModel.date(value))}</time>`;
  const heading = (title,intro='') => `<div class="page-heading"><div><h1>${escaparHTML(title)}</h1>${intro?`<p>${escaparHTML(intro)}</p>`:''}</div></div>`;
  const state = (title,text,loading=false,retry=false) => `<div class="app-state bento-panel" role="${retry?'alert':'status'}"${loading?' aria-busy="true"':''}><span class="icon-medallion">${icon(loading?'clock':'info')}</span><h2>${escaparHTML(title)}</h2><p>${escaparHTML(text)}</p>${retry?'<button class="button btn-liquid-brand" type="button" data-app-action="reload">Reintentar</button>':''}</div>`;
  // Estado vacío dentro de una tarjeta: ícono, frase y, si aplica, la acción (HTML ya armado por la vista).
  const empty = (title,text='',action='') => `<div class="app-empty" role="status"><span class="icon-medallion">${icon('info')}</span><div><p class="app-empty-title">${escaparHTML(title)}</p>${text?`<p>${escaparHTML(text)}</p>`:''}${action}</div></div>`;
  // Escapa el texto y evita que un folio de caso (CS-XXXXXXXX) se parta al final de la línea.
  const conFolio = text => escaparHTML(text).replace(/\bCS-[0-9A-Z]{8}\b/g,'<span class="folio">$&</span>');
  // Tarjeta de resumen compacta; las cifras puras llevan `is-figure` (tamaño dominante fijo) y el texto se ajusta solo.
  const kpi = (label,value,extra='') => `<article class="bento-panel user-metric${/^[\d\s.,]+$/.test(String(value))?' is-figure':''}"><h2>${label}</h2><strong${extra}>${value}</strong></article>`;
  const accountTabs = active => `<nav class="account-tabs" aria-label="Apartados de mi cuenta">${[['perfil','','Perfil'],['huertos','/huertos','Mis huertos'],['seguridad','/seguridad','Seguridad'],['privacidad','/privacidad','Privacidad']].map(([key,path,label])=>`<a class="button ${key===active?'btn-liquid-brand active':'btn-liquid-light'}" href="#cuenta${path}"${key===active?' aria-current="page"':''}>${label}</a>`).join('')}</nav>`;
  const accountGreeting = greeting => greeting?(greeting==='Bienvenido'?greeting:'Hola, '+greeting):'Tu información de acceso.';
  // `nav` lo prepara AppController según la sesión y sus capacidades; la vista solo pinta los enlaces.
  function shell(route,{isAdmin,links,groups=[],account}) {
    const selected=route.screen==='admin'?'admin/'+route.detail:route.screen;
    const link=item=>`<a class="button btn-liquid-sidebar" href="#${item.id}"${selected===item.id?' aria-current="page"':''}>${icon(item.icon)}<span>${item.label}</span></a>`;
    const accountLink=`<a class="button compact btn-liquid-nav account-icon-link" href="#cuenta" aria-label="Mi cuenta" title="Mi cuenta">${icon('user')}</a>`;
    // Encabezado limpio en ambos roles: a la portada se vuelve con el logotipo.
    const noticesLink=`<a class="button compact btn-liquid-nav account-icon-link bell-link" href="#avisos" aria-label="Avisos" title="Avisos"${selected==='avisos'?' aria-current="page"':''}>${icon('bell')}<span class="bell-badge" data-bell-count hidden></span></a>`;
    const menuButton=`<button class="button compact btn-liquid-nav private-menu-toggle" type="button" data-app-action="toggle-menu" aria-controls="garden-navigation" aria-expanded="false" aria-label="Abrir menú de navegación"><span class="private-menu-open-icon">${icon('menu')}</span><span class="private-menu-close-icon">${icon('close')}</span><span>Menú</span></button>`;
    // Sin barra superior: logotipo y botón de ocultar viven en el panel; perfil, avisos (solo usuario) y menú flotan arriba.
    const topbar=`<div class="private-topbar"><div class="topbar-start">${brand('#inicio','YouGarden, inicio','topbar-brand')}</div><div class="topbar-actions">${accountLink}${noticesLink}${menuButton}</div></div>`;
    const sidebarTop=`<div class="sidebar-top">${brand('#inicio','YouGarden, inicio','sidebar-brand')}</div><a class="sidebar-home" href="#inicio">${icon('home')}<span>Ver página principal</span></a>${isAdmin?'<p class="private-role-label">Administración</p>':''}`;
    // Enlace externo: abre otra pestaña y el panel sigue abierto. Si no hay correo configurado, no se muestra.
    const mailLink=()=>{const url=AppModel.supportMailUrl();return url?`<a class="private-mail-link" href="${escaparHTML(url)}" target="_blank" rel="noopener noreferrer">${icon('mail')}<span>Abrir correo de soporte</span>${icon('external')}<span class="sr-only">(se abre en otra pestaña)</span></a>`:'';};
    // Administración: los grupos del menú llegan ya filtrados por capacidad; el correo de soporte va antes de Mi cuenta.
    const groupHtml=group=>`<p class="private-role-label private-group-label">${escaparHTML(group.label)}</p><div class="private-group">${group.items.map(link).join('')}</div>`;
    const navigation=isAdmin?groups.map(groupHtml).join('')+mailLink()+link(account):links.map(link).join('');
    // La página principal ya tiene acceso fijo bajo el logotipo, también en móvil.
    const menuFooter=`<div class="private-menu-footer"><button class="button private-menu-logout" type="button" data-app-action="logout">${icon('logout')}<span>Cerrar sesión</span></button></div>`;
    return `<div class="private-layout"><aside class="sidebar" id="garden-navigation">${sidebarTop}<nav class="private-nav" aria-label="Navegación de la aplicación">${navigation}</nav>${menuFooter}</aside><div class="private-content">${topbar}<main class="dashboard container" id="contenido" tabindex="-1"><div id="app-feedback" role="status" tabindex="-1" hidden></div><div id="app-page"></div></main></div></div><div class="private-menu-shade" data-app-action="close-menu" aria-hidden="true" hidden></div>`;
  }
  const FILTERS = [['todos', 'Todos'], ['no_leidos', 'No leídos'], ['equipo', 'Mi equipo'], ['ia', 'IA'], ['soporte', 'Soporte'], ['legales', 'Legales']];
  const SEVERITIES = {critico:['Crítico', 'rojo'], advertencia:['Advertencia', 'ambar'], informacion:['Información', 'gris']};
  const severity = item => { const [label, tone] = SEVERITIES[item.severity]; return `<span class="badge tone-${tone}">${label}</span>`; };
  function noticeRow(item) {
    return `<li><a class="notice-row${item.read ? '' : ' is-unread'}" href="#avisos/${item.id}" data-notice-open="${item.id}"${item.link ? ` data-notice-link="${escaparHTML(item.link)}"` : ''}>
      <span class="notice-dot" aria-hidden="true"></span><span class="sr-only">${item.read ? 'Leído' : 'No leído'}</span>${severity(item)}
      <span class="notice-main"><strong class="notice-title">${conFolio(item.title)}</strong><span class="notice-meta-line">${escaparHTML([item.garden, GardenModel.ago(item.createdAt)].filter(Boolean).join(' · '))}</span></span></a></li>`;
  }
  function noticeDetail(data) {
    if(data.status === 'loading') return heading('Avisos')+state('Cargando aviso','Consultando su información.',true);
    if(data.status === 'error') return heading('Avisos')+state('No pudimos cargar el aviso','Inténtalo de nuevo.',false,true);
    if(data.status === 'not-found' || !data.item) return heading('Aviso no disponible')+'<div class="bento-panel"><p>Este aviso no está disponible.</p><a class="button btn-liquid-light" href="#avisos">Todos los avisos</a></div>';
    const item = data.item;
    return heading('Detalle del aviso')+`<article class="bento-panel notice-detail"><div class="notice-meta">${severity(item)}${item.resolvedAt ? '<span class="badge tone-verde">Resuelto</span>' : ''}</div><h2>${conFolio(item.title)}</h2>${item.text ? `<p>${conFolio(item.text)}</p>` : ''}
      <dl class="notice-facts"><div><dt>Fecha</dt><dd>${date(item.createdAt)}</dd></div>${item.garden ? `<div><dt>Huerto</dt><dd>${escaparHTML(item.garden)}</dd></div>` : ''}${item.resolvedAt ? `<div><dt>Resolución</dt><dd>${date(item.resolvedAt)}</dd></div>` : ''}</dl>
      <div class="app-actions">${item.link ? `<a class="button btn-liquid-brand" href="${escaparHTML(item.link)}">Ir</a>` : ''}${item.resolvable ? '<button class="button btn-liquid-light" type="button" data-app-action="mark-resolved">Marcar como resuelto</button>' : ''}<a class="button btn-liquid-light" href="#avisos">Todos los avisos</a></div></article>`;
  }
  function notices(data, filter='todos', detail=null, name='') {
    if(detail) return noticeDetail(data);
    const filters = `<div class="notice-filters" role="group" aria-label="Filtrar avisos">${FILTERS.map(([id, label]) => `<button class="button ${filter===id?'btn-liquid-brand':'btn-liquid-light'}" type="button" data-filter="${id}" aria-pressed="${filter===id}">${label}</button>`).join('')}</div>`;
    let body;
    if(data.status === 'loading') body = state('Cargando avisos','Consultando tus avisos.',true);
    else if(data.status === 'error') body = state('No pudimos cargar tus avisos','Inténtalo de nuevo.',false,true);
    else if(!data.items.length) body = state(filter === 'todos' ? 'No tienes avisos' : 'No hay avisos en este filtro','Los avisos de tu equipo, de soporte y de tu cuenta aparecerán aquí.');
    else body = `<ul class="notice-list bento-panel">${data.items.map(noticeRow).join('')}</ul>${data.items.length < data.total ? '<button class="button btn-liquid-light" type="button" data-app-action="more">Cargar más</button>' : ''}`;
    return heading('Avisos',AppModel.addressed(name,'Revisa lo que necesita atención.'))+`<div class="notice-toolbar">${filters}<button class="button btn-liquid-light" type="button" data-app-action="mark-all-read">Marcar todo como leído</button></div>`+body;
  }
  // Salida al pie de Mi cuenta. Sigue disponible aunque el perfil no haya podido cargarse.
  const signOut = () => `<section class="bento-panel account-session" aria-labelledby="session-title"><div><h2 id="session-title">Tu sesión</h2><p>Saldrás de tu cuenta en este navegador.</p></div><button class="button btn-liquid-light account-logout" type="button" data-app-action="logout">${icon('logout')}<span>Cerrar sesión</span></button></section>`;
  function account(data) {
    const privacyLink = accountTabs('perfil');
    if(data.status==='loading')return heading('Mi cuenta')+privacyLink+state('Cargando cuenta','Consultando la información de tu cuenta.',true)+signOut();
    if(data.status==='error')return heading('Mi cuenta')+privacyLink+state('No se pudo consultar tu cuenta','Inténtalo de nuevo.',false,true)+signOut();
    return heading('Mi cuenta',accountGreeting(data.greeting))+privacyLink+`<section class="bento-panel account-profile" aria-labelledby="profile-title"><h2 id="profile-title">Datos de la cuenta</h2><dl class="profile-facts"><div><dt>Correo electrónico</dt><dd>${data.email?escaparHTML(data.email):'Esperando información de la cuenta'}</dd></div><div><dt>Verificación del correo</dt><dd>${data.verified===true?'Correo verificado':data.verified===false?'Correo sin verificar':'Sin información disponible'}</dd></div></dl><div class="app-actions"><a class="button btn-liquid-brand" href="#cuenta/contrasena">Cambiar contraseña</a></div></section><div data-profile-form></div>${signOut()}`;
  }
  // Marco privado ya pintado: operaciones de presentación que coordina AppController.
  function frame(root,route,nav) {
    root.innerHTML=shell(route,nav);
    const page=root.querySelector('#app-page'),feedback=root.querySelector('#app-feedback');
    const sidebar=root.querySelector('.sidebar'),toggle=root.querySelector('.private-menu-toggle'),shade=root.querySelector('.private-menu-shade');
    const messages={failed:'No se pudo completar la solicitud. Inténtalo de nuevo.'};
    return {page,sidebar,toggle,
      message(code,error=false){feedback.hidden=false;feedback.textContent=messages[code];feedback.setAttribute('role',error?'alert':'status');feedback.focus();},
      hideMessage(){feedback.hidden=true;},
      // Contador de la campana: «9+» a partir de 10; sin avisos sin leer no se muestra.
      bell(unread){const badge=root.querySelector('[data-bell-count]'),link=badge?.closest('a');if(!badge)return;
        badge.hidden=!unread;badge.textContent=unread>9?'9+':String(unread||'');
        link.setAttribute('aria-label',unread?`Avisos, ${unread} sin leer`:'Avisos');},
      pageBusy(on){page.inert=on;if(on)page.setAttribute('aria-busy','true');else page.removeAttribute('aria-busy');},
      // Devuelve el contenedor del perfil cuando la cuenta está lista; el controlador monta su formulario.
      draw(screen,data,filter,detail,alias){
        const focusedFilter=page.contains(document.activeElement)?document.activeElement.dataset.filter:null;
        let profileHost=null;
        if(screen==='avisos')page.innerHTML=notices(data,filter,detail,alias);
        if(screen==='cuenta'){page.innerHTML=account(data);if(data.status==='ready')profileHost=page.querySelector('[data-profile-form]');}
        if(focusedFilter)page.querySelector(`[data-filter="${focusedFilter}"]`)?.focus();
        return profileHost;
      },
      isEmpty:()=>!page.hasChildNodes(),
      focusFilter(value){page.querySelector(`[data-filter="${value}"]`)?.focus();},
      greeting(value){const intro=page.querySelector('.page-heading p');if(intro)intro.textContent=accountGreeting(value);},
      securityUnavailable(){page.innerHTML=heading('Página no disponible')+'<p><a href="#cuenta/seguridad">Seguridad de mi cuenta</a></p>';},
      markCurrent(href){root.querySelectorAll('.private-nav a,.account-icon-link[href]').forEach(link=>{
        if(link.getAttribute('href')===href)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});},
      focusMain(options){root.querySelector('main')?.focus(options);},
      logoutFailed(){mostrarAviso('error','No se pudo cerrar la sesión. Inténtalo de nuevo.');},
      // Menú lateral: siempre visible en escritorio; en móvil, desplegable.
      sidebarHidden(hidden){sidebar.inert=hidden;if(hidden)sidebar.setAttribute('aria-hidden','true');else sidebar.removeAttribute('aria-hidden');},
      menu(open){
        sidebar.dataset.open=String(open);
        toggle?.setAttribute('aria-expanded',String(open));
        toggle?.setAttribute('aria-label',open?'Cerrar menú de navegación':'Abrir menú de navegación');
        if(shade)shade.hidden=!open;
        document.body.classList.toggle('private-menu-open',open);
      },
      focusToggle(){toggle.focus({preventScroll:true});},
      focusCurrentLink(){sidebar.querySelector('[aria-current="page"]')?.focus();},
      keepVisible(focused){
        if(!page.contains(focused)||focused.closest('.account-tabs')||!focused.matches('input,select,textarea,button,a'))return;
        const available=window.visualViewport?window.visualViewport.height+window.visualViewport.offsetTop:innerHeight;
        if(focused.getBoundingClientRect().bottom>available-16)focused.scrollIntoView({block:'center'});
      }};
  }
  const confirmaciones = {cerrarSesion:{titulo:'¿Cerrar sesión?',texto:'Tendrás que iniciar sesión de nuevo para entrar a tu cuenta.',accion:'Cerrar sesión'},};
  return {shell,frame,heading,state,empty,conFolio,kpi,date,notices,account,accountGreeting,accountTabs,confirmaciones
  };
})();

// ── Calendario ──
// Calendario de filtros de fecha: componente de presentación (posición, foco, teclado y validación visual).
// Lo usan Mantenimientos y Equipos y ventas. Las fechas se interpretan con MaintenanceDates (modelo).
const DateFilterViews = (() => {
  // Calendario compartido: sirve a todos los campos con [data-date-open] dentro de «filter»
  // (un formulario o un contenedor con varios). Desde/Hasta de un mismo formulario se validan como rango.
  function mount(filter, signal) {
    const dates = MaintenanceDates;
    const buttons = [...filter.querySelectorAll('[data-date-open]')];
    const fieldOf = button => button.closest('form').elements.namedItem(button.dataset.dateOpen);
    const fields = buttons.map(fieldOf);
    const picker = MaintenanceViews.datePicker();
    document.body.append(picker);
    let active = null, opener = null, focused = dates.today();
    function validate(form = null) {
      for(const field of fields) {
        field.setCustomValidity(field.value && !dates.parse(field.value) ? 'Escribe una fecha válida con el formato AAAA-MM-DD.' : '');
      }
      for(const owner of new Set(fields.map(field => field.form))) {
        const since = owner.elements.namedItem('since'), until = owner.elements.namedItem('until');
        if(since && until && dates.parse(since.value) && dates.parse(until.value) && since.value > until.value) {
          until.setCustomValidity('Hasta debe ser igual o posterior a Desde.');
        }
      }
      for(const field of fields) {
        if(field.validity.valid) field.removeAttribute('aria-invalid');
        else field.setAttribute('aria-invalid','true');
      }
      return fields.find(field => (!form || field.form === form) && !field.validity.valid)?.validationMessage || '';
    }
    function position() {
      if(!active) return;
      const viewport = window.visualViewport;
      const left = viewport?.offsetLeft || 0, top = viewport?.offsetTop || 0;
      const width = viewport?.width || window.innerWidth, height = viewport?.height || window.innerHeight;
      const anchor = active.parentElement.getBoundingClientRect();
      picker.style.maxHeight = `${Math.max(0,height-16)}px`;
      picker.style.maxWidth = `${Math.max(0,width-16)}px`;
      const box = picker.getBoundingClientRect();
      const below = top+height-anchor.bottom-8, above = anchor.top-top-8;
      let y = below >= box.height || below >= above ? anchor.bottom+8 : anchor.top-box.height-8;
      y = Math.max(top+8,Math.min(y,top+height-box.height-8));
      picker.style.left = `${Math.max(left+8,Math.min(anchor.left,left+width-box.width-8))}px`;
      picker.style.top = `${y}px`;
    }
    function render(focusDay = false) {
      const year = focused.getUTCFullYear(), month = focused.getUTCMonth();
      picker.querySelector('[data-date-year]').setCustomValidity('');
      MaintenanceViews.renderCalendar(picker,{year,month,days:dates.weeks(year,month),
        selected:active.value,today:dates.format(dates.today()),focused:dates.format(focused)});
      position();
      if(focusDay) picker.querySelector('[data-date-value][tabindex="0"]')?.focus({preventScroll:true});
    }
    function close(restore = true) {
      if(!active) return;
      const target = opener;
      opener.setAttribute('aria-expanded','false');
      if(picker.hidePopover && picker.matches(':popover-open')) picker.hidePopover();
      picker.hidden = true;
      active = null; opener = null;
      if(restore && target.isConnected) target.focus({preventScroll:true});
    }
    function open(field, button) {
      if(active === field) { close(); return; }
      close(false);
      active = field; opener = button;
      focused = dates.parse(field.value) || dates.today();
      picker.querySelector('[data-date-year]').setCustomValidity('');
      picker.querySelector('#maint-calendar-title').textContent = `Calendario: ${button.dataset.dateLabel || (field.name === 'since' ? 'Desde' : 'Hasta')}`;
      opener.setAttribute('aria-expanded','true');
      picker.hidden = false;
      if(picker.showPopover) picker.showPopover();
      render(true);
    }
    function select(value) {
      const field = active;
      field.value = value;
      validate(); close();
      field.dispatchEvent(new Event('change',{bubbles:true}));
    }
    buttons.forEach(button => {
      const field = fieldOf(button);
      button.addEventListener('click',() => open(field,button),{signal});
      field.addEventListener('input',() => validate(),{signal});
      field.addEventListener('keydown',event => {
        if(event.key === 'Escape' && active) { event.preventDefault(); close(); return; }
        if(event.key === 'ArrowDown' || event.key === 'Enter') {
          event.preventDefault(); open(field,button);
        }
      },{signal});
    });
    picker.addEventListener('click',event => {
      const day = event.target.closest('[data-date-value]');
      if(day) { select(day.dataset.dateValue); return; }
      const action = event.target.closest('[data-date-action]')?.dataset.dateAction;
      if(action === 'close') close();
      if(action === 'clear') select('');
      if(action === 'today') select(dates.format(dates.today()));
      if(action === 'prev' || action === 'next') { focused = dates.shift(focused,0,action === 'prev' ? -1 : 1); render(); }
    },{signal});
    picker.addEventListener('change',event => {
      if(!event.target.matches('[data-date-month],[data-date-year]')) return;
      const year = Number(picker.querySelector('[data-date-year]').value);
      const month = Number(picker.querySelector('[data-date-month]').value);
      const yearField = picker.querySelector('[data-date-year]');
      if(!Number.isInteger(year) || year < 1 || year > 9999) {
        yearField.setCustomValidity('Escribe un año entre 1 y 9999.'); yearField.reportValidity(); return;
      }
      yearField.setCustomValidity('');
      focused = dates.make(year,month,Math.min(focused.getUTCDate(),dates.make(year,month+1,0).getUTCDate()));
      render();
    },{signal});
    picker.addEventListener('keydown',event => {
      if(event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); return; }
      if(event.key === 'Tab') {
        const stops = [...picker.querySelectorAll('button:not(:disabled),input,select')].filter(item => item.tabIndex >= 0);
        if((event.shiftKey && event.target === stops[0]) || (!event.shiftKey && event.target === stops.at(-1))) {
          event.preventDefault();
          let target = opener;
          if(!event.shiftKey) {
            const controls = [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')]
              .filter(item => !picker.contains(item) && item.tabIndex >= 0 && !item.disabled && item.getClientRects().length);
            target = controls[controls.indexOf(opener)+1] || opener;
          }
          close(false); target.focus();
        }
        return;
      }
      const day = event.target.closest('[data-date-value]');
      if(!day) return;
      const date = dates.parse(day.dataset.dateValue);
      const weekday = (date.getUTCDay()+6)%7;
      const steps = {ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7,Home:-weekday,End:6-weekday};
      if(Object.hasOwn(steps,event.key)) focused = dates.shift(date,steps[event.key]);
      else if(event.key === 'PageUp' || event.key === 'PageDown') focused = dates.shift(date,0,(event.key === 'PageUp' ? -1 : 1)*(event.shiftKey ? 12 : 1));
      else return; // Enter y espacio conservan la activación nativa del botón.
      event.preventDefault(); render(true);
    },{signal});
    document.addEventListener('pointerdown',event => {
      if(active && !picker.contains(event.target) && !active.parentElement.contains(event.target) && !event.target.closest('[data-date-open]')) close();
    },{signal});
    document.addEventListener('focusin',event => {
      if(active && !picker.contains(event.target) && !active.parentElement.contains(event.target)) close(false);
    },{signal});
    window.addEventListener('resize',position,{signal});
    window.addEventListener('scroll',position,{signal,capture:true});
    window.visualViewport?.addEventListener('resize',position,{signal});
    window.visualViewport?.addEventListener('scroll',position,{signal});
    const resize = new ResizeObserver(position);
    resize.observe(picker);
    resize.observe(filter.closest('#app-page') || filter);
    document.fonts?.ready.then(() => { if(!signal.aborted) position(); });
    signal.addEventListener('abort',() => { resize.disconnect(); close(false); picker.remove(); },{once:true});
    return {validate,close};
  }
  return Object.freeze({mount});
})();

// ── Tablas de administración ──
// Piezas que comparten las pantallas de administración: tabla, paginación visible, pestañas, calendario y diálogo.
const AdminTableViews = (() => {
  const PAGE_SIZE = 25;
  // Guarda un archivo descargado con fetch (exportaciones): enlace temporal a un objeto Blob, que se libera al terminar.
  function saveFile(blob, name) {
    const url = URL.createObjectURL(blob), link = Object.assign(document.createElement('a'), {href:url, download:name});
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  const button = (action, label, kind = 'light', attrs = '') => `<button type="button" class="button btn-liquid-${kind}" data-admin-action="${action}" ${attrs}>${label}</button>`;
  // Cada celda lleva el nombre de su columna (la vista en tarjetas del móvil lo muestra) y la primera, su texto completo como título.
  function cells(row, heads) {
    let column = -1;
    return row.replace(/<td(?=[\s>])([^>]*)>(.*?)<\/td>/gs, (_, attributes, content) => {
      column += 1;
      const title = column === 0 ? ` title="${content.replace(/<[^>]*>/g, '').trim().replaceAll('"', '&quot;')}"` : '';
      return `<td data-label="${heads[column] ?? ''}"${title}${attributes}>${content}</td>`;
    });
  }
  const table = (label, heads, rows) => `<div class="user-table-scroll" tabindex="0" role="region" aria-label="${label}"><table class="user-table admin-table"><thead><tr>${heads.map(head => `<th scope="col">${head}</th>`).join('')}</tr></thead><tbody>${rows.map(row => cells(row, heads)).join('')}</tbody></table></div>`;
  // Sin resultados no hay nada que paginar: la pantalla muestra su estado vacío.
  function pager({page, total}, action = 'page') {
    if (!total) return '';
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    return `<nav class="user-pager" aria-label="Páginas">${button(action, 'Anterior', 'light', `data-page="${page - 1}"${page <= 1 ? ' disabled' : ''}`)}<span>Página ${page} de ${pages} · ${total} en total</span>${button(action, 'Siguiente', 'light', `data-page="${page + 1}"${page >= pages ? ' disabled' : ''}`)}</nav>`;
  }
  // Pestañas del ancho de su contenido; la acción principal de la pantalla, si hay, queda a la derecha en la misma fila.
  const tabs = (items, active, action = '') => `<div class="tabs-bar"><div class="user-range-control" role="group" aria-label="Apartados">${items.map(([id, label]) => button('tab', label, id === active ? 'brand' : 'light', `data-tab="${id}" aria-pressed="${id === active}"`)).join('')}</div>${action}</div>`;
  const status = state => state === 'loading' ? AppViews.state('Cargando', 'Consultando la información.', true) : AppViews.state('No pudimos cargar esta pantalla', 'Inténtalo de nuevo.', false, true);
  const dialog = '<dialog class="bento-panel app-dialog admin-dialog" aria-labelledby="admin-dialog-title"><div data-admin-dialog-content></div></dialog>';
  const dateField = (name, label, value = '') => `<div class="maint-date-control"><label for="admin-${name}">${label}</label>
    <div class="maint-date-field"><input type="text" name="${name}" id="admin-${name}" placeholder="aaaa-mm-dd" maxlength="10" autocomplete="off" spellcheck="false" value="${escaparHTML(value)}">
    <button type="button" data-date-open="${name}" data-date-label="${label}" aria-label="Abrir calendario: ${label}" aria-controls="maint-calendar" aria-expanded="false" aria-haspopup="dialog">${icon('calendar')}</button></div></div>`;
  const day = value => value ? new Date(`${value}T12:00:00`).toLocaleDateString('es-MX', {dateStyle:'medium'}) : '—';
  const merida = value => new Date(value).toLocaleString('es-MX', {timeZone:'America/Merida', dateStyle:'medium', timeStyle:'short'});
  // Fecha y hora completas de Mérida, sin abreviar: «20/11/2026 00:15:32».
  const EXACT = new Intl.DateTimeFormat('es-MX', {timeZone:'America/Merida', day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23'});
  function exact(value) {
    const date = new Date(value);
    if(!value || Number.isNaN(date.getTime())) return '—';
    const part = Object.fromEntries(EXACT.formatToParts(date).map(({type, value: text}) => [type, text]));
    return `${part.day}/${part.month}/${part.year} ${part.hour}:${part.minute}:${part.second}`;
  }
  const money = value => new Intl.NumberFormat('es-MX', {style:'currency', currency:'MXN'}).format(Number(value));
  function open(root, html) {
    const box = root.querySelector('.admin-dialog');
    box.querySelector('[data-admin-dialog-content]').innerHTML = html;
    if(!box.open) box.showModal();
    box.querySelector('input:not([readonly]),select,textarea,button')?.focus();
  }
  function dismiss(root) { const box = root.querySelector('.admin-dialog'); if(box?.open) box.close(); }
  const paint = (root, html) => { root.innerHTML = html; };
  return Object.freeze({button, table, pager, tabs, status, dialog, dateField, day, merida, exact, money, open, dismiss, paint, saveFile});
})();

// ── Campos ──
// Filtro de teclado y pegado, y mensajes en línea, para todo campo con data-campo (reglas en Campos, modelos/comun.js).
// Números, importes, nombres de persona y MAC no admiten caracteres no válidos; los demás muestran el mensaje al salir
// del campo o al enviar. En cualquier texto se quitan los caracteres de control. El servidor vuelve a validar todo.
const CamposVista = (() => {
  const LIBRES = 'input:not([type]),input[type=text],input[type=search],input[type=email],input[type=url],textarea';
  const ENVOLTURAS = '.care-stepper,.maint-date-field,.password-input-group,.key-form-row';
  const numero = valor => valor === null || valor === undefined || valor === '' ? undefined : Number(valor);
  const reglaDe = el => el?.dataset?.campo || (el?.matches?.(LIBRES) ? 'libre' : null);
  const limites = el => ({min:numero(el.dataset?.min), max:numero(el.dataset?.max), minimo:numero(el.getAttribute('minlength')),
    maximo:numero(el.getAttribute('maxlength')), requerido:Boolean(el.required)});
  const multilinea = el => el.tagName === 'TEXTAREA';
  const activo = el => el && !el.readOnly && !el.disabled;
  let ultimoFormulario = null;

  // Mensaje en línea debajo del campo (o de su envoltura), unido con aria-describedby y aria-invalid.
  function aviso(el, mensaje, tipo = 'regla') {
    const id = `${el.id || el.name || 'campo'}-aviso`;
    const caja = el.closest?.(ENVOLTURAS) || el;
    const siguiente = caja.nextElementSibling;
    let nota = siguiente?.classList?.contains('campo-aviso') ? siguiente : null;
    const descritos = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(item => item && item !== id);
    if(!mensaje) {
      nota?.remove();
      el.removeAttribute('aria-invalid');
      if(descritos.length) el.setAttribute('aria-describedby', descritos.join(' ')); else el.removeAttribute('aria-describedby');
      return;
    }
    if(!nota) {
      nota = document.createElement('p');
      nota.className = 'campo-aviso';
      nota.id = id;
      nota.setAttribute('aria-live', 'polite');
      caja.insertAdjacentElement('afterend', nota);
    }
    nota.dataset.tipo = tipo;
    nota.textContent = mensaje;
    el.setAttribute('aria-invalid', 'true');
    el.setAttribute('aria-describedby', [...descritos, id].join(' '));
  }
  const tipoDeAviso = el => { const caja = el.closest?.(ENVOLTURAS) || el; return caja.nextElementSibling?.classList?.contains('campo-aviso') ? caja.nextElementSibling.dataset.tipo : null; };

  // Inserta texto donde está el cursor (respeta maxlength) y avisa con «input», como si se hubiera escrito.
  function insertar(el, texto) {
    const maximo = numero(el.getAttribute('maxlength'));
    const inicio = el.selectionStart ?? el.value.length, fin = el.selectionEnd ?? inicio;
    const cabe = maximo === undefined ? texto : Array.from(texto).slice(0, Math.max(0, maximo - (el.value.length - (fin - inicio)))).join('');
    if(!cabe) return;
    try { el.setRangeText(cabe, inicio, fin, 'end'); } catch { el.value = el.value.slice(0, inicio) + cabe + el.value.slice(fin); }
    el.dispatchEvent(new Event('input', {bubbles:true}));
  }

  // Al escribir: un carácter que dejaría el campo con algo no permitido no entra y se dice por qué.
  function alEscribir(event) {
    const el = event.target, regla = el?.dataset?.campo;
    if(!activo(el) || !Campos.filtra(regla) || typeof event.data !== 'string' || !/^insert(Text|ReplacementText)$/.test(event.inputType)) return;
    const inicio = el.selectionStart ?? el.value.length, fin = el.selectionEnd ?? inicio;
    const nuevo = el.value.slice(0, inicio) + event.data + el.value.slice(fin);
    if(!Campos.filtrar(regla, nuevo).cambiado) return;
    event.preventDefault();
    aviso(el, Campos.bloqueo(regla, limites(el)), 'bloqueo');
  }
  // Al pegar o soltar texto: entra solo la parte válida; si se quitó algo, se dice.
  function alPegar(event) {
    const el = event.target, regla = reglaDe(el);
    if(!activo(el) || !regla) return;
    const datos = (event.clipboardData || event.dataTransfer)?.getData('text') ?? '';
    const resultado = Campos.filtrar(regla, datos, {multilinea:multilinea(el)});
    if(!resultado.cambiado) return;
    event.preventDefault();
    if(el.type === 'number') { if(resultado.limpio === datos) insertar(el, datos); }
    else insertar(el, resultado.limpio);
    if(resultado.quitado) aviso(el, Campos.bloqueo(regla, limites(el)), 'bloqueo');
  }
  // Respaldo (autocompletar, teclados en pantalla, IME): limpia lo que haya entrado y quita el aviso cuando ya no aplica.
  function alCambiar(event) {
    const el = event.target, regla = reglaDe(el);
    if(!activo(el) || !regla || el.type === 'number') return;
    const resultado = Campos.filtrar(regla, el.value, {multilinea:multilinea(el)});
    if(resultado.cambiado) {
      const cursor = Math.max(0, (el.selectionStart ?? el.value.length) - (el.value.length - resultado.limpio.length));
      el.value = resultado.limpio;
      try { el.setSelectionRange(cursor, cursor); } catch { /* sin cursor (email, number) */ }
      if(resultado.quitado) { aviso(el, Campos.bloqueo(regla, limites(el)), 'bloqueo'); return; }
    }
    const tipo = tipoDeAviso(el);
    if(tipo === 'bloqueo' || (tipo && !Campos.validar(regla, el.value, limites(el)))) aviso(el, null);
  }
  // Al salir del campo: el valor completo con su regla (rango, largo, formato).
  function alSalir(event) {
    const el = event.target, regla = el?.dataset?.campo;
    if(!activo(el) || !regla) return;
    // Vacío no se marca al salir (el obligatorio se revisa al enviar).
    aviso(el, el.value.trim() ? Campos.validar(regla, el.value, limites(el)) : null);
  }
  // Antes de que el controlador envíe: si un campo visible no cumple, no se envía y el foco va al primero.
  function revisar(form) {
    let primero = null;
    form.querySelectorAll('[data-campo]').forEach(el => {
      if(!activo(el) || el.closest('[hidden]')) return;
      const mensaje = Campos.validar(el.dataset.campo, el.value, limites(el));
      aviso(el, mensaje);
      if(mensaje && !primero) primero = el;
    });
    primero?.focus();
    return !primero;
  }
  function alEnviar(event) {
    const form = event.target;
    if(!form?.matches?.('form')) return;
    ultimoFormulario = form;
    if(revisar(form)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  // El servidor rechazó un campo (400 con field y message): el mensaje va junto a ese campo del último formulario enviado.
  function rechazo(event) {
    const {field, message} = event.detail || {};
    const form = document.activeElement?.form || ultimoFormulario;
    const el = form?.elements?.namedItem?.(field);
    if(!el || typeof message !== 'string' || !el.matches?.('input,textarea,select')) return;
    aviso(el, message);
    el.focus();
  }
  function instalar(raiz = document) {
    raiz.addEventListener('beforeinput', alEscribir, true);
    raiz.addEventListener('paste', alPegar, true);
    raiz.addEventListener('drop', alPegar, true);
    raiz.addEventListener('input', alCambiar, true);
    raiz.addEventListener('focusout', alSalir, true);
    raiz.addEventListener('submit', alEnviar, true);
    window.addEventListener('chilito:campo', rechazo);
  }
  return Object.freeze({instalar, revisar, aviso, alEscribir, alPegar, alCambiar, alSalir, alEnviar, rechazo});
})();

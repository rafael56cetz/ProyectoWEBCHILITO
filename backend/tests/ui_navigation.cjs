
const assert=require('node:assert/strict');
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};
const frame=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));

async function navigation(page) {
 let checks=0;
 const equal=(actual,expected)=>{assert.equal(actual,expected);checks++;};
 await page.evaluate(()=>{
  window.privateNavigationCheck={header:document.querySelector('.site-header'),nav:document.querySelector('.sidebar'),checkingScreens:0,removedShell:0};
  window.privateNavigationObserver=new MutationObserver(records=>{
   const state=window.privateNavigationCheck;
   if(!state.header.isConnected||!state.nav.isConnected)state.removedShell++;
   for(const record of records) for(const node of record.addedNodes) {
    if(node.nodeType===1 && /Comprobando sesión|Comprobando tu acceso/.test(node.textContent))state.checkingScreens++;
   }
  });
  window.privateNavigationObserver.observe(document.querySelector('#app'),{childList:true,subtree:true});
 });
 for(const width of [320,390,768,1024,1440]) {
  await page.setViewportSize({width,height:900});
  for(const route of ['avisos','cuenta','asistente','huerto']) {
   await page.locator('.private-nav a[href="#'+route+'"]').click();
   await page.locator('.private-nav a[href="#'+route+'"][aria-current="page"]').waitFor();
   if(route==='avisos')await page.locator('.notice-card').first().waitFor();
   if(route==='cuenta')await page.getByText('stage2-browser@example.invalid',{exact:true}).waitFor();
   if(route==='asistente')await page.locator('.assistant-panel').waitFor();
   if(route==='huerto')await page.locator('.plant-card').first().waitFor();
   equal(await page.evaluate(()=>document.querySelector('.site-header')===window.privateNavigationCheck.header&&document.querySelector('.sidebar')===window.privateNavigationCheck.nav),true);
  }
  equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 }
 const sessionPattern='**/_allauth/browser/v1/auth/session';
 let first=true;
 const guardStarted=deferred(),releaseGuard=deferred(),guardFinished=deferred();
 await page.route(sessionPattern,async route=>{
  if(!first||route.request().method()!=='GET')return route.continue();
  first=false;guardStarted.resolve();
  await releaseGuard.promise;
  await route.continue().catch(()=>{});
  guardFinished.resolve();
 });
 await page.locator('.private-nav a[href="#avisos"]').click();
 await guardStarted.promise;
 equal(await page.locator('#app').getAttribute('aria-busy'),'true');
 equal(await page.getByRole('heading',{name:'Comprobando sesión',exact:true}).count(),0);
 equal(await page.locator('.plant-card').count(),3);
 await page.locator('.private-nav a[href="#cuenta"]').click();
 await page.getByText('stage2-browser@example.invalid',{exact:true}).waitFor();
 releaseGuard.resolve();await guardFinished.promise;await frame(page);
 equal(new URL(page.url()).hash,'#cuenta');
 equal(await page.locator('.account-profile').count(),1);
 await page.unroute(sessionPattern);

 const noticesPattern='**/api/huertos/actual/avisos';
 const dataStarted=deferred(),releaseData=deferred(),dataFinished=deferred();
 await page.route(noticesPattern,async route=>{
  dataStarted.resolve();await releaseData.promise;
  await route.continue().catch(()=>{});dataFinished.resolve();
 });
 await page.locator('.private-nav a[href="#avisos"]').click();
 await dataStarted.promise;
 await page.getByRole('heading',{name:'Cargando avisos',exact:true,includeHidden:true}).waitFor({state:'attached'});
 equal(await page.locator('#app-page').getAttribute('aria-busy'),'true');
 equal(await page.locator('.site-header').evaluate(el=>el===window.privateNavigationCheck.header),true);
 await page.locator('.private-nav a[href="#asistente"]').click();
 await page.locator('.assistant-panel').waitFor();
 releaseData.resolve();await dataFinished.promise;await frame(page);
 equal(await page.locator('.assistant-panel').count(),1);
 equal(await page.locator('.notice-card').count(),0);
 equal(await page.locator('#app-page').evaluate(el=>el.inert),false);
 await page.unroute(noticesPattern);
 equal(await page.evaluate(()=>window.privateNavigationCheck.checkingScreens),0);
 equal(await page.evaluate(()=>window.privateNavigationCheck.removedShell),0);
 await page.evaluate(()=>window.privateNavigationObserver.disconnect());

 await page.route(sessionPattern,route=>route.fulfill({status:503,json:{status:503,code:'service-unavailable'}}));
 await page.locator('.private-nav a[href="#cuenta"]').click();
 await page.locator('#auth-feedback').filter({hasText:'No podemos comprobar tu sesión'}).waitFor();
 equal(await page.locator('.private-layout').count(),0);
 await page.unroute(sessionPattern);
 await page.goto(page.url().split('#')[0]+'#huerto');
 await page.locator('.plant-card').first().waitFor();
 await page.route(sessionPattern,route=>route.fulfill({status:401,json:{status:401,meta:{is_authenticated:false},data:{flows:[]}}}));
 await page.locator('.private-nav a[href="#cuenta"]').click();
 await page.locator('#email').waitFor();
 equal(new URL(page.url()).hash,'#acceso');
 equal(await page.locator('.private-layout').count(),0);
 await page.unroute(sessionPattern);
 await page.goto(page.url().split('#')[0]+'#huerto');
 await page.locator('.plant-card').first().waitFor();
 return checks;
}

async function logout(page) {
 let checks=0,deletes=0;
 const equal=(actual,expected)=>{assert.equal(actual,expected);checks++;};
 const listener=request=>{if(request.url().endsWith('/auth/session')&&request.method()==='DELETE')deletes++;};
 page.on('request',listener);
 const trigger=page.locator('[data-app-action="logout"]');
 const dialog=page.getByRole('dialog',{name:'¿Cerrar sesión?',exact:true});
 const cancel=page.locator('[data-app-action="cancel-logout"]');
 const confirm=page.locator('[data-app-action="confirm-logout"]');
 for(const width of [320,390,768,1024,1440]) {
  await page.setViewportSize({width,height:900});
  await trigger.click();await dialog.waitFor();
  equal(await cancel.evaluate(el=>el===document.activeElement),true);
  equal(await dialog.evaluate(el=>el.matches(':modal')),true);
  equal(deletes,0);
  await page.keyboard.press('Tab');
  equal(await confirm.evaluate(el=>el===document.activeElement),true);
  await page.keyboard.press('Tab');
  // Chromium may briefly focus the dialog/document between traversal cycles.
  await page.keyboard.press('Shift+Tab');
  equal(await confirm.evaluate(el=>el===document.activeElement),true);
  const rect=await dialog.boundingBox();
  equal(rect.x>=0&&rect.x+rect.width<=width&&rect.y>=0&&rect.y+rect.height<=900,true);
  equal(await confirm.evaluate(el=>el.getBoundingClientRect().height>=44),true);
  if(width===320)await cancel.click();else await page.keyboard.press('Escape');
  await dialog.waitFor({state:'hidden'});
  equal(await trigger.evaluate(el=>el===document.activeElement),true);
  equal(await page.evaluate(()=>AuthService.session.status),'authenticated');
 }
 equal(deletes,0);
 await page.emulateMedia({reducedMotion:'reduce'});
 const pattern='**/_allauth/browser/v1/auth/session';
 await page.route(pattern,route=>route.request().method()==='DELETE'
  ?route.fulfill({status:503,json:{status:503,code:'service-unavailable'}}):route.continue());
 await trigger.click();await confirm.click();
 await dialog.getByText('No se pudo cerrar la sesión. Inténtalo de nuevo.',{exact:true}).waitFor();
 equal(deletes,1);equal(await dialog.isVisible(),true);
 equal(await page.evaluate(()=>AuthService.session.status),'authenticated');
 await cancel.click();await dialog.waitFor({state:'hidden'});
 await page.unroute(pattern);

 const started=deferred(),release=deferred();
 await page.route(pattern,async route=>{
  if(route.request().method()!=='DELETE')return route.continue();
  started.resolve();await release.promise;await route.continue();
 });
 await trigger.click();await confirm.click();await started.promise;
 equal(await confirm.isDisabled(),true);equal(await cancel.isDisabled(),true);
 await page.keyboard.press('Escape');
 equal(await dialog.isVisible(),true);
 equal(deletes,2);
 release.resolve();
 await page.waitForURL(url=>url.hash==='#acceso');
 await page.locator('#email').waitFor();
 equal(await page.evaluate(()=>AuthService.session.status),'unauthenticated');
 equal(await page.locator('.private-layout').count(),0);
 equal(deletes,2);
 await page.unroute(pattern);page.off('request',listener);
 return checks;
}
module.exports={navigation,logout};

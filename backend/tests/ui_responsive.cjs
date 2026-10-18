const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.ELCHILITO_UI_URL;
if(base!=='http://127.0.0.1:8768')throw Error('Isolated fixture required');
const sizes=[[320,568],[390,844],[568,320],[844,390],[768,1024],[820,1180],[900,650],[1024,768],[1180,820],[1440,900],[640,450]];
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({reducedMotion:'reduce'});
 const page=await context.newPage();page.setDefaultTimeout(12000);
 const issues=[],errors=[],checks=[];
 let phase='start';
 page.on('pageerror',error=>errors.push(error.name));
 async function audit(route,size){
  await page.evaluate(()=>document.fonts.ready);
  const result=await page.evaluate(()=>{
   const visible=el=>el.getClientRects().length&&!el.closest('[hidden]')&&getComputedStyle(el).visibility!=='hidden';
   const label=el=>(el.getAttribute('aria-label')||el.textContent||el.id||el.tagName).trim().slice(0,70);
   const clipped=[...document.querySelectorAll('h1,h2,h3,p,dd,label,input,select,textarea,button,a.button,.bento-panel,.plant-card')].filter(visible).filter(el=>{
    if(el.closest('.sr-only,.skip-link')||el.classList.contains('sr-only'))return false;
    const r=el.getBoundingClientRect();
    return r.width>0&&(r.left< -1||r.right>innerWidth+1||el.scrollWidth>el.clientWidth+2&&getComputedStyle(el).overflowX==='hidden'&&!el.matches('input,select,textarea'));
   }).map(label);
   const small=[...document.querySelectorAll('button,a.button,input:not([type=checkbox]),select')].filter(visible).filter(el=>{
    const r=el.getBoundingClientRect();return !el.disabled&&r.width>0&&(r.height<43||r.width<43);
   }).map(el=>({text:label(el),height:Math.round(el.getBoundingClientRect().height),width:Math.round(el.getBoundingClientRect().width)}));
   const header=document.querySelector('.site-header');
   const title=document.querySelector('main h1,.hero-text h1');
   const hr=header?.getBoundingClientRect(),tr=title?.getBoundingClientRect();
   return {overflow:document.documentElement.scrollWidth>innerWidth+1,clipped,small,
    headingUnderHeader:!!(hr&&tr&&tr.top>=0&&tr.top<hr.bottom-1),
    inputSmallFonts:[...document.querySelectorAll('input:not([type=checkbox]),select,textarea')].filter(visible).filter(el=>parseFloat(getComputedStyle(el).fontSize)<16).map(label)};
  });
  result.blockedFocus=[];
  const controls=page.locator('main a[href],main button:not([disabled]),main input:not([disabled]),main select:not([disabled]),main textarea:not([disabled]),.site-footer a[href]');
  const candidates=[];
  for(let index=0;index<await controls.count();index++)if(await controls.nth(index).isVisible())candidates.push(index);
  for(const index of [...new Set([candidates[0],candidates.at(-1)])].filter(value=>value!==undefined)){
   const control=controls.nth(index);
   await control.evaluate(element=>{element.scrollIntoView({block:'center',behavior:'instant'});element.focus({preventScroll:true});});
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   const blocked=await control.evaluate(element=>{const r=element.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;const hit=document.elementFromPoint(x,y);return !hit||!(element===hit||element.contains(hit));});
   if(blocked)result.blockedFocus.push((await control.innerText().catch(()=>''))||(await control.getAttribute('name'))||'field');
  }
  await page.evaluate(()=>scrollTo(0,0));
  checks.push({route,size});
  if(result.overflow||result.clipped.length||result.small.length||result.headingUnderHeader||result.inputSmallFonts.length||result.blockedFocus.length)issues.push({route,size,...result});
 }
 try{
  for(const size of sizes){
   await page.setViewportSize({width:size[0],height:size[1]});
   for(const route of ['inicio','acceso','registro','recuperar','restablecer','terminos','privacidad','derechos-arco']){
    phase=route+' '+size;
    await page.goto(base+'/index.html#'+route+(route==='restablecer'?'?token='+encodeURIComponent(process.env.ELCHILITO_TEST_RESET_KEY):''));
    await page.locator('#contenido').waitFor();
    if(route==='restablecer')await page.locator('#password').waitFor();
    if(route==='derechos-arco')await page.getByRole('heading',{name:'Solicitudes ARCO aún no disponibles',exact:true}).waitFor();
    await page.evaluate(()=>scrollTo(0,0));
    await audit(route,size);
    if(route==='registro'||route==='recuperar'){
     await page.locator('[type="submit"]').click();
     await page.locator('#email[aria-invalid="true"]').waitFor();
     await audit(route+'/error',size);
    }
   }
  }
  await page.goto(base+'/index.html#acceso');
  await page.locator('#email').fill('stage2-browser@example.invalid');
  await page.locator('#password').fill('Frase exclusiva para prueba de navegador aislada 37!');
  await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
  await page.locator('.plant-card').first().waitFor();
  for(const size of sizes){
   await page.setViewportSize({width:size[0],height:size[1]});
   for(const route of ['huerto','avisos','avisos/'+process.env.ELCHILITO_TEST_NOTICE,'asistente','cuenta','cuenta/contrasena','cuenta/seguridad','cuenta/privacidad']){
    phase=route+' '+size;
    await page.evaluate(route=>{location.hash='#'+route},route);
    await page.waitForFunction(screen=>document.body.dataset.screen===screen,route.split('/')[0]);
    if(route==='huerto')await page.locator('.plant-card').first().waitFor();
    if(route==='avisos')await page.locator('.notice-card').first().waitFor();
    if(route.startsWith('avisos/'))await page.locator('.notice-detail').waitFor();
    if(route==='asistente')await page.locator('.assistant-panel').waitFor();
    if(route==='cuenta')await page.locator('.account-profile').waitFor();
    if(route==='cuenta/contrasena')await page.locator('#currentPassword').waitFor();
    if(route==='cuenta/seguridad')await page.getByRole('heading',{name:'Llaves de acceso aún no disponibles',exact:true}).waitFor();
    if(route==='cuenta/privacidad')await page.getByRole('heading',{name:'Solicitudes ARCO aún no disponibles',exact:true}).waitFor();
    await page.evaluate(()=>scrollTo(0,0));
    await audit(route,size);
   }
   await page.locator('[data-app-action=logout]').click();
   const dialog=page.getByRole('dialog',{name:'¿Cerrar sesión?',exact:true});
   await dialog.waitFor();
   const info=await dialog.evaluate(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight}});
   if(info.left<0||info.right>size[0]+1||info.top<0||info.bottom>size[1]+1)issues.push({route:'logout',size,dialog:info});
   await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();
   checks.push({route:'logout',size});
  }
  fs.writeFileSync(path.join(process.cwd(),'revision/resultado-responsivo.json'),JSON.stringify({screens:checks.length,sizes,issues,errors,screenshots:false},null,2));
  console.log(JSON.stringify({screens:checks.length,issues:issues.length,errors,sizes,screenshots:false}));
  if(issues.length){console.log(JSON.stringify(issues));process.exitCode=1;}
  if(errors.length)process.exitCode=1;
 }catch(error){console.error('Responsive audit failed in '+phase+': '+error.name+' '+error.message.split('\n')[0]);process.exitCode=1;}
 finally{await context.close();await browser.close();}
})().catch(()=>{console.error('Responsive browser could not run.');process.exitCode=1;});

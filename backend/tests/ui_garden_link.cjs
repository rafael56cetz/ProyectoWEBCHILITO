const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ELCHILITO_UI_URL;
if(base!=='http://127.0.0.1:8768')throw Error('Isolated fixture required');
const password='Frase exclusiva para prueba de navegador aislada 37!';
const sizes=[[320,568],[390,844],[568,320],[844,390],[768,1024],[820,1180],[1024,768],[1440,900]];
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({reducedMotion:'reduce'});
 const page=await context.newPage();page.setDefaultTimeout(10000);
 let checks=0,phase='login',capture=false;
 const traffic=[],errors=[];
 const equal=(actual,expected)=>{assert.deepEqual(actual,expected,'Unexpected '+phase);checks++;};
 page.on('pageerror',error=>errors.push(error.name));
 page.on('request',request=>{if(capture)traffic.push({method:request.method(),path:new URL(request.url()).pathname});});
 async function login(email){
  await page.goto(base+'/index.html#acceso');
  await page.locator('#email').fill(email);await page.locator('#password').fill(password);
  await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
  await page.locator('.plant-card').first().waitFor();
 }
 async function blanks(){
  equal(await page.locator('.plant-card').count(),3);
  equal(await page.locator('.plant-name h3').allTextContents(),['Planta 1','Planta 2','Planta 3']);
  equal(await page.locator('.plant-reading strong').allTextContents(),['—','—','—']);
  equal(await page.locator('.metric strong').allTextContents(),['—','—']);
  equal(await page.locator('.tank-reading').innerText(),'—');
  equal(await page.locator('.sensor-track span').count(),0);
  equal(await page.locator('.reading-note').count(),0);
  equal(await page.locator('#app-page time[datetime]').count(),0);
  equal(await page.locator('.private-nav a').count(),4);
  equal(await page.getByText('Esperando datos',{exact:false}).count(),0);
  equal(await page.locator('#app-page .notice-card').count(),0);
 }
 try{
  await login('unassigned-browser@example.invalid');
  phase='unassigned';
  await page.locator('[data-app-action="open-link"]').waitFor();
  await blanks();
  equal(await page.evaluate(async()=>{const response=await fetch('/api/huertos/actual');return {status:response.status,body:await response.json()}}),{status:403,body:{status:403,code:'garden-unassigned'}});
  // Directly check the foreign notice using only the fixture ID passed by the isolated runner.
  equal(await page.evaluate(async id=>{const response=await fetch('/api/huertos/actual/avisos/'+id);return {status:response.status,body:await response.json()}},process.env.ELCHILITO_TEST_FOREIGN_NOTICE),{status:403,body:{status:403,code:'garden-unassigned'}});
  const trigger=page.locator('[data-app-action="open-link"]');
  const dialog=page.getByRole('dialog',{name:'Vincular mi huerto',exact:true});
  const input=page.getByLabel('Código de vinculación',{exact:true});
  capture=true;
  for(const [width,height] of sizes){
   phase='dialog '+width+'x'+height;
   await page.setViewportSize({width,height});await trigger.click();await dialog.waitFor();
   equal(await input.evaluate(element=>element===document.activeElement),true);
   equal(await dialog.evaluate(element=>element.matches(':modal')),true);
   equal(await input.getAttribute('pattern'),null);
   equal(await input.getAttribute('maxlength'),null);
   equal(await input.getAttribute('inputmode'),null);
   equal(await dialog.getByRole('button',{name:'Vincular',exact:true}).isDisabled(),true);
   equal(await dialog.getByRole('button',{name:'Vincular',exact:true}).evaluate(element=>parseFloat(getComputedStyle(element).opacity)<1),true);
   await input.fill('Formato sin definir / letras + espacios');
   await input.press('Enter');
   equal(await dialog.isVisible(),true);
   await page.keyboard.press('Tab');
   equal(await dialog.getByRole('button',{name:'Cancelar',exact:true}).evaluate(element=>element===document.activeElement),true);
   await page.keyboard.press('Shift+Tab');
   equal(await input.evaluate(element=>element===document.activeElement),true);
   const rect=await dialog.boundingBox();
   equal(rect.x>=0&&rect.y>=0&&rect.x+rect.width<=width+1&&rect.y+rect.height<=height+1,true);
   equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   equal(await input.evaluate(element=>parseFloat(getComputedStyle(element).fontSize)>=16),true);
   if(width===320)await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();else await page.keyboard.press('Escape');
   await dialog.waitFor({state:'hidden'});
   equal(await input.inputValue(),'');
   equal(await trigger.evaluate(element=>element===document.activeElement),true);
   equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  }
  equal(traffic,[]);capture=false;
  phase='error';
  const endpoint='**/api/huertos/actual';
  await page.route(endpoint,route=>route.fulfill({status:503,json:{status:503,code:'service-unavailable'}}));
  await page.reload();
  await page.getByRole('heading',{name:'No se pudo consultar el huerto',exact:true}).waitFor();
  equal(await page.locator('.plant-card').count(),0);equal(await trigger.count(),0);
  await page.unroute(endpoint);
  await page.getByRole('button',{name:'Reintentar',exact:true}).click();
  await trigger.waitFor();await blanks();
  phase='partial-response';
  await page.route(endpoint,route=>route.fulfill({status:200,json:{status:'waiting'}}));
  await page.reload();await page.getByRole('heading',{name:'No se pudo consultar el huerto',exact:true}).waitFor();
  equal(await trigger.count(),0);await page.unroute(endpoint);
  phase='expired';
  await page.route(endpoint,route=>route.fulfill({status:401,json:{status:401,code:'unauthenticated'}}));
  await page.reload();await page.locator('#email').waitFor();
  equal(new URL(page.url()).hash,'#acceso');equal(await page.locator('.private-layout').count(),0);
  await page.unroute(endpoint);
  // End this isolated session before signing in as the member fixture.
  await page.evaluate(async()=>{await AuthService.logout()});
  phase='assigned';
  await login('stage2-browser@example.invalid');
  await page.locator('.connection-strip').filter({hasText:'Sin mediciones'}).waitFor();
  equal(await trigger.count(),0);equal(await page.locator('.plant-card').count(),3);
  equal(await page.locator('.plant-reading strong').allTextContents(),['—','—','—']);
  equal(await page.locator('.tank-reading').innerText(),'—');
  equal(await page.locator('.sensor-track span').count(),0);
  equal(await page.evaluate(async()=>{const response=await fetch('/api/huertos/actual');return response.status}),200);
  const real=await page.evaluate(async()=>{const response=await fetch('/api/huertos/actual');return response.json()});
  const supplied=structuredClone(real);
  const at='2026-10-17T12:00:00Z';
  supplied.status='ready';supplied.name='Huerto autorizado con información';
  supplied.updatedAt=at;
  supplied.plants[0].reading={value:37.5,quality:'valid',at};
  supplied.temperature={value:26.4,quality:'valid',at};
  supplied.humidity={value:61.2,quality:'valid',at};
  supplied.tank={state:'not-low',at};
  phase='available-contract';
  // Test-only response fixture: no ingestion route or production measurement is created.
  await page.route(endpoint,route=>route.fulfill({status:200,json:supplied}));
  await page.reload();await page.getByRole('heading',{name:supplied.name,exact:true}).waitFor();
  equal(await page.locator('.plant-reading strong').first().innerText(),'37.5%');
  equal(await page.locator('.metric strong').allTextContents(),['26.4°C','61.2%']);
  equal(await page.locator('.sensor-track span').first().getAttribute('style'),'width:37.5%');
  equal(await page.locator('#app-page time[datetime="'+at.replace('Z','.000Z')+'"]').count()>0,true);
  equal(await trigger.count(),0);
  equal(await page.getByText('Nivel bajo no detectado',{exact:true}).count(),1);
  equal(await page.locator('#app-page').innerText().then(text=>text.includes('Equipo conectado')),false);
  await page.unroute(endpoint);
  equal(errors,[]);
  console.log(JSON.stringify({checks,failed:0,viewports:sizes,gardenApiStillForbiddenWithoutMembership:true,noRequestsWhileUsingLinkDialog:true,readingsFixtureOnlyInBrowser:true,screenshots:false}));
 }catch(error){console.error('Garden linking UI check failed in '+phase+': '+error.name+' '+error.message.split('\n')[0]);process.exitCode=1;}
 finally{await context.close();await browser.close();}
})().catch(()=>{console.error('Isolated garden linking browser could not start.');process.exitCode=1;});

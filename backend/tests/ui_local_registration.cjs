const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const readline=require('node:readline');
const base=process.env.ELCHILITO_UI_URL,email=process.env.ELCHILITO_FIXTURE_EMAIL;
if(base!=='http://127.0.0.1:8768'||!email?.endsWith('@example.invalid'))throw Error('Isolated fixture required');
const pipe=readline.createInterface({input:process.stdin});
async function fixtureCode(){
 const line=new Promise(resolve=>pipe.once('line',resolve));
 process.stdout.write(JSON.stringify({event:'fixture-code'})+'\n');
 return JSON.parse(await line).code;
}
(async()=>{
 let checks=0,phase='start',signupRequests=0;
 const equal=(actual,expected)=>{assert.equal(actual,expected,'Unexpected '+phase);checks++;};
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext();
 const page=await context.newPage();page.setDefaultTimeout(10000);
 const errors=[];
 page.on('pageerror',error=>errors.push(error.name));
 page.on('request',request=>{if(request.url().endsWith('/auth/signup')&&request.method()==='POST')signupRequests++;});
 try{
  phase='configuration';
  await page.goto(base+'/index.html#registro');
  await page.locator('#termsAccepted').waitFor();
  equal(await page.evaluate(()=>ChilitoHTTP.configuration.registrationAllowed),true);
  equal(await page.evaluate(()=>ChilitoHTTP.configuration.legal.approved),false);
  equal(await page.locator('#termsAccepted').isChecked(),false);
  equal(await page.locator('#password-minimum').innerText(),'Al menos 15 caracteres');
  equal(await page.locator('#password-minimum svg').count(),0);
  equal(await page.getByText('Máximo 256 caracteres.',{exact:true}).count(),0);
  equal(await page.getByText('El servidor comprobará estas condiciones al guardar.',{exact:true}).count(),0);
  equal(await page.locator('#password-minimum').innerText().then(text=>/Pendiente|Cumplido|Faltan/.test(text)),false);
  phase='minimum-check';
  await page.locator('#password').fill('🚀'.repeat(14));
  equal(await page.locator('#password-minimum svg').count(),0);
  await page.locator('#password').fill('🚀'.repeat(15));
  equal(await page.locator('#password-minimum svg').count(),1);
  await page.locator('#password').fill('🚀'.repeat(16));
  equal(await page.locator('#password-minimum svg').count(),1);
  const password=' '+'🚀'.repeat(13)+' ';
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.locator('#confirmation').fill(password);
  phase='checkbox';
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await page.locator('#termsAccepted[aria-invalid="true"]').waitFor();checks++;
  equal(signupRequests,0);
  for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});
   equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  await page.locator('#termsAccepted').focus();
  await page.keyboard.press('Space');
  equal(await page.locator('#termsAccepted').isChecked(),true);
  phase='unauthorized-recipient';
  await page.route('**/_allauth/browser/v1/auth/signup',route=>route.fulfill({
   status:403,contentType:'application/json',body:JSON.stringify({status:403,code:'email-not-authorized'})
  }));
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await page.locator('#email-error').filter({hasText:'no está autorizado'}).waitFor();checks++;
  equal(await page.locator('#email').getAttribute('aria-invalid'),'true');
  equal(await page.locator('#email').evaluate(element=>element===document.activeElement),true);
  equal(await page.getByText('No fue posible completar el envío a este correo.',{exact:false}).count(),0);
  equal(await page.locator('#termsAccepted').isChecked(),true);
  equal(signupRequests,1);
  await page.unroute('**/_allauth/browser/v1/auth/signup');
  equal(await page.locator('#password').inputValue(),'');
  equal(await page.locator('#confirmation').inputValue(),'');
  await page.locator('#password').fill(password);
  await page.locator('#confirmation').fill(password);
  phase='signup';
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await page.waitForURL(url=>url.hash==='#verificar');
  await page.locator('#code').waitFor();checks++;
  for(const [width,height] of [[320,568],[390,844],[568,320],[844,390],[768,1024],[820,1180],[900,650],[1024,768],[1180,820],[1440,900],[640,450]]){
   await page.setViewportSize({width,height});
   equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   equal(await page.locator('#code').evaluate(element=>parseFloat(getComputedStyle(element).fontSize)>=16),true);
   await page.locator('#code').focus();
   await page.locator('#code').evaluate(element=>element.scrollIntoView({block:'center',behavior:'instant'}));
   equal(await page.locator('#code').evaluate(element=>{const r=element.getBoundingClientRect();return document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===element}),true);
  }
  equal(signupRequests,2);
  equal(await page.getByRole('button',{name:'Reenviar código',exact:true}).isDisabled(),true);
  const code=await fixtureCode();
  const wrong=String((Number(code)+1)%1000000).padStart(6,'0');
  phase='wrong-code';
  await page.locator('#code').fill(wrong);
  await page.getByRole('button',{name:'Verificar correo',exact:true}).click();
  await page.locator('#code-error').filter({hasText:'no es correcto'}).waitFor();checks++;
  phase='resume';
  await page.reload();
  await page.locator('#code').waitFor();checks++;
  equal(await page.locator('#email').inputValue(),email);
  phase='verify';
  await page.locator('#code').fill(code);
  await page.getByRole('button',{name:'Verificar correo',exact:true}).click();
  await page.getByRole('heading',{name:'Correo verificado',exact:true}).first().waitFor();checks++;
  equal(await page.evaluate(()=>AuthService.session.status),'authenticated');
  await page.getByRole('link',{name:'Mi huerto',exact:true}).click();
  await page.locator('.sidebar').waitFor();checks++;
  phase='permissions';
  equal(await page.evaluate(async()=> (await ChilitoHTTP.request('/api/huertos/actual')).http),403);
  await page.goto(base+'/index.html#cuenta');
  await page.getByText(email,{exact:true}).waitFor();checks++;
  const own=await page.evaluate(async()=> (await ChilitoHTTP.request('/api/cuenta')).body);
  equal(own.verified,true);equal(own.gardenAssigned,false);
  for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});
   equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  equal(errors.length,0);
  await page.locator('[data-app-action="logout"]').click();
  await page.getByRole('dialog',{name:'¿Cerrar sesión?',exact:true}).getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await page.waitForURL(url=>url.hash==='#acceso');checks++;
  process.stdout.write(JSON.stringify({event:'result',checks,failed:0,widths:[320,390,768,1024,1440],
   signupVerificationSession:true,explicitNoMembership:true,checkboxKeyboard:true,screenshots:false})+'\n');
 }catch(error){process.stdout.write(JSON.stringify({event:'error',phase,type:error.name})+'\n');process.exitCode=1;}
 finally{pipe.close();await context.close();await browser.close();}
})().catch(()=>{pipe.close();process.stdout.write('{"event":"error","phase":"browser-start"}\n');process.exitCode=1;});

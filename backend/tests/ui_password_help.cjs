const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ELCHILITO_UI_URL;
const resetKey=process.env.ELCHILITO_TEST_RESET_KEY;
if(base!=='http://127.0.0.1:8768'||!resetKey)throw Error('Isolated fixture required');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({permissions:['clipboard-read','clipboard-write']});
 const page=await context.newPage();
 let checks=0,phase='initial',mutations=0;
 const pass=()=>checks++;
 const equal=(a,b)=>{assert.equal(a,b,'Unexpected state in '+phase);pass();};
 const errors=[];
 page.on('pageerror',error=>errors.push(error.name));
 page.on('request',request=>{if(request.method()!=='GET'&&request.method()!=='HEAD')mutations++;});
 const waitCounter=async text=>{
  const length=parseInt(text,10);
  await page.waitForFunction(expected=>document.querySelector('#password-counter')?.textContent===expected,length?length+' caracteres':'');pass();
 };
 const noOverflow=async()=>equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 try{
  phase='registration';
  await page.goto(base+'/index.html#registro');
  await waitCounter('0 caracteres');
  equal(await page.locator('#password').getAttribute('autocomplete'),'new-password');
  equal(await page.locator('#password').getAttribute('maxlength'),null);
  equal(await page.locator('#confirmation').getAttribute('autocomplete'),'new-password');
  equal(await page.locator('#confirmation-match').isHidden(),true);
  equal(await page.getByText('Máximo 256 caracteres.',{exact:true}).count(),0);
  for(const [length,fragment]of [[12,'Faltan 3'],[14,'Falta 1'],[15,'Mínimo alcanzado'],[16,'Mínimo alcanzado'],[256,'Mínimo alcanzado'],[257,'Supera el máximo de 256']]){
   await page.locator('#password').fill('🚀'.repeat(length));
   await waitCounter(length+' caracteres · '+fragment);
   equal(await page.locator('#password').evaluate(el=>Array.from(el.value).length),length);
   equal(await page.locator('#password-minimum').evaluate(el=>el.classList.contains('is-met')),length>=15);
  }
  await page.locator('#email').fill('not-created@example.invalid');
  await page.locator('#confirmation').fill('🚀'.repeat(257));
  await page.locator('#termsAccepted').check();
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await page.locator('#password-error').filter({hasText:'como máximo 256'}).waitFor();pass();
  equal(mutations,0);
  phase='paste';
  await page.locator('#password').fill('');
  await page.locator('#password').focus();
  await page.evaluate(()=>navigator.clipboard.writeText('a\u0301'.repeat(7)+'🚀'));
  await page.keyboard.press('Control+V');
  await waitCounter('15 caracteres · Mínimo alcanzado');
  equal(await page.locator('#password').evaluate(el=>el.value==='a\u0301'.repeat(7)+'🚀'),true);
  await page.locator('#confirmation').fill('different-test-input');
  equal(await page.locator('#confirmation-match').innerText(),'Las contraseñas todavía no coinciden');
  await page.locator('#confirmation').fill('a\u0301'.repeat(7)+'🚀');
  equal(await page.locator('#confirmation-match').innerText(),'Las contraseñas coinciden');
  await page.locator('#password').fill('b\u0301'.repeat(7)+'🚀');
  equal(await page.locator('#confirmation-match').innerText(),'Las contraseñas todavía no coinciden');
  await page.locator('[data-password-toggle="password"]').click();
  equal(await page.locator('#password').getAttribute('type'),'text');
  await page.locator('[data-password-toggle="password"]').click();
  equal(await page.locator('#password').getAttribute('type'),'password');
  equal(await page.locator('#password').getAttribute('aria-describedby'),'password-error password-counter password-minimum password-requirements');
  equal(await page.locator('#password-minimum svg').count(),1);
  equal(await page.locator('#password-counter').getAttribute('aria-live'),'off');
  phase='announcements';
  await page.locator('#confirmation').fill('');
  await page.locator('#password').fill('🚀'.repeat(14));
  await page.locator('#password').focus();
  await page.locator('#password').fill('🚀'.repeat(15));
  await page.locator('#password-help-status').filter({hasText:'Mínimo alcanzado.'}).waitFor();pass();
  await page.evaluate(()=>{
   window.statusChanges=0;
   new MutationObserver(()=>window.statusChanges++).observe(document.querySelector('#password-help-status'),{childList:true,characterData:true,subtree:true});
  });
  await page.locator('#password').pressSequentially('abc');
  await page.waitForTimeout(450);
  equal(await page.evaluate(()=>window.statusChanges),0);
  equal(mutations,0);
  const customPolicy=await page.evaluate(()=>{
   const config={password:{minLength:19,maxLength:300}};
   return [AuthModel.passwordProgress('🚀'.repeat(18),'',config).range,
     AuthModel.passwordProgress('🚀'.repeat(300),'',config).range,
     AuthModel.passwordProgress('🚀'.repeat(301),'',config).range];
  });
  equal(JSON.stringify(customPolicy),JSON.stringify(['below-minimum','within-range','over-maximum']));
  for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});
   await noOverflow();
  }
  phase='closed-registration';
  await page.locator('#password').fill('🚀'.repeat(15));
  await page.locator('#confirmation').fill('🚀'.repeat(15));
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await page.locator('#auth-feedback').filter({hasText:'El registro no está disponible'}).waitFor();pass();
  equal(mutations,0);
  await waitCounter('0 caracteres');
  phase='recovery';
  await page.goto(base+'/index.html#restablecer?token='+encodeURIComponent(resetKey));
  await page.locator('#password-counter').waitFor();
  await waitCounter('0 caracteres');
  equal(new URL(page.url()).hash,'#restablecer');
  await page.locator('#password').fill('🚀'.repeat(256));
  await page.locator('#confirmation').fill('🚀'.repeat(256));
  await waitCounter('256 caracteres · Mínimo alcanzado');
  for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});await noOverflow();
  }
  await page.getByRole('button',{name:'Guardar contraseña',exact:true}).click();
  await page.getByText('Ya puedes iniciar sesión con tu nueva contraseña.',{exact:true}).waitFor();pass();
  phase='login';
  await page.goto(base+'/index.html#acceso');
  await page.locator('#email').waitFor();
  equal(await page.locator('#password-counter').count(),0);
  equal(await page.locator('#password').getAttribute('autocomplete'),'current-password');
  await page.locator('#email').fill('stage2-browser@example.invalid');
  await page.locator('#password').fill('🚀'.repeat(256));
  await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
  await page.locator('.sidebar').waitFor();
  phase='change';
  await page.goto(base+'/index.html#cuenta/contrasena');
  await page.locator('#currentPassword').waitFor();
  equal(await page.locator('#currentPassword').getAttribute('aria-describedby'),'currentPassword-error');
  equal(await page.locator('#currentPassword').getAttribute('autocomplete'),'current-password');
  await page.locator('#currentPassword').fill('🚀'.repeat(256));
  await page.locator('#password').fill('123456789012345');
  await page.locator('#confirmation').fill('123456789012345');
  await page.getByRole('button',{name:'Guardar contraseña',exact:true}).click();
  await page.locator('#password-error').filter({hasText:'no cumple los requisitos'}).waitFor();pass();
  await waitCounter('0 caracteres');
  equal(await page.locator('#confirmation-match').isHidden(),true);
  for(const width of [320,390,768,1024,1440]){
   await page.setViewportSize({width,height:900});await noOverflow();
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('#password').focus();await page.keyboard.press('Tab');
  equal(await page.locator('[data-password-toggle="password"]').evaluate(el=>el===document.activeElement),true);
  await page.keyboard.press('Enter');
  equal(await page.locator('#password').getAttribute('type'),'text');
  await page.locator('#currentPassword').fill('🚀'.repeat(256));
  await page.locator('#password').fill(' '+'🚀'.repeat(13)+' ');
  await page.locator('#confirmation').fill(' '+'🚀'.repeat(13)+' ');
  await waitCounter('15 caracteres · Mínimo alcanzado');
  await page.getByRole('button',{name:'Guardar contraseña',exact:true}).click();
  await page.getByText('El cambio se completó correctamente.',{exact:true}).waitFor();pass();
  equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  equal(errors.length,0);
  console.log(JSON.stringify({stage:'A',checks,failed:0,widths:[320,390,768,1024,1440],paste:'clipboard and Control+V',
   realIsolatedRecoveryAndChange:true,codePointBoundaries:[14,15,16,256,257],screenshots:false}));
 }catch(error){console.error('Password guidance check failed: '+phase+' ('+error.name+')');process.exitCode=1;}
 finally{await context.close();await browser.close();}
})().catch(()=>{console.error('Isolated password browser test could not run.');process.exitCode=1;});

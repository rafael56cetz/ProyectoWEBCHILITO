const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.ELCHILITO_UI_URL;
if(base !== 'http://127.0.0.1:8768') throw new Error('Isolated UI server required');
const password='Frase exclusiva para prueba de navegador aislada 37!';
const nextPassword='Otra frase exclusiva para navegador aislado 93!';
(async()=>{
  const browser=await chromium.launch({headless:true});
  let checks=0;
  const passed=()=>{checks++;};
  const context=await browser.newContext();
  const page=await context.newPage();
  const errors=[],loaded=[];
  page.on('pageerror',e=>errors.push(e.name));
  page.on('request',r=>loaded.push(new URL(r.url()).pathname));
  try {
    for(const width of [320,390,768,1024,1440]) {
      await page.setViewportSize({width,height:900});
      for(const route of ['inicio','acceso','registro','recuperar','terminos','privacidad','derechos-arco']) {
        await page.goto(base+'/index.html#'+route);
        await page.locator('#contenido').waitFor();
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,route+' overflow '+width);
        passed();
      }
    }
    assert.equal(loaded.some(path=>path.startsWith('/desarrollo/')),false); passed();
    await page.goto(base+'/index.html#huerto');
    await page.locator('#email').waitFor();
    assert.equal(new URL(page.url()).hash,'#acceso'); passed();
    await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
    await page.locator('#email[aria-invalid="true"]').waitFor(); passed();
    await page.locator('#email').fill('stage2-browser@example.invalid');
    await page.locator('#password').fill('incorrecta');
    await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
    await page.locator('#auth-feedback').filter({hasText:'no son correctos'}).waitFor(); passed();
    await page.locator('#password').fill(password);
    await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
    await page.waitForURL(url=>url.hash==='#huerto');
    await page.locator('.sidebar').waitFor();
    assert.equal(await page.locator('.sidebar a').count(),4); passed();
    assert.equal(await page.evaluate(()=>localStorage.length),0); passed();
    await page.reload();
    await page.locator('.sidebar').waitFor();
    assert.equal(new URL(page.url()).hash,'#huerto'); passed();
    await page.goto(base+'/index.html#cuenta');
    await page.getByText('stage2-browser@example.invalid',{exact:true}).waitFor(); passed();
    for(const width of [320,390,768,1024,1440]) {
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'account overflow '+width); passed();
      if(width<=768) {
        assert.equal(await page.locator('.sidebar').evaluate(el=>getComputedStyle(el).position),'fixed'); passed();
      }
    }
    await page.goto(base+'/index.html#cuenta/contrasena');
    await page.locator('#currentPassword').fill(password);
    await page.locator('#password').fill(nextPassword);
    await page.locator('#confirmation').fill(nextPassword);
    await page.getByRole('button',{name:'Guardar contraseña',exact:true}).click();
    await page.getByText('El cambio se completó correctamente.',{exact:true}).waitFor(); passed();
    await page.goto(base+'/index.html#cuenta/seguridad');
    await page.getByRole('heading',{name:'Seguridad',exact:true}).waitFor();
    assert.equal(await page.locator('[data-passkey-item]').count(),0); passed();
    await page.goto(base+'/index.html#cuenta/privacidad');
    await page.getByRole('heading',{name:'Solicitudes ARCO aún no disponibles',exact:true}).waitFor(); passed();
    await page.goto(base+'/index.html#cuenta');
    await page.getByText('stage2-browser@example.invalid',{exact:true}).waitFor();
    await page.locator('[data-app-action="logout"]').click();
    await page.getByRole('dialog',{name:'¿Cerrar sesión?',exact:true}).getByRole('button',{name:'Cerrar sesión',exact:true}).click();
    await page.waitForURL(url=>url.hash==='#acceso'); passed();
    await page.goto(base+'/index.html#cuenta');
    await page.locator('#email').waitFor();
    assert.equal(new URL(page.url()).hash,'#acceso'); passed();
    await page.goto(base+'/index.html#registro');
    await page.locator('#email').fill('never-created@example.invalid');
    await page.locator('#password').fill(password);
    await page.locator('#confirmation').fill(password);
    await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
    await page.locator('#termsAccepted[aria-invalid="true"]').waitFor(); passed();
    await page.locator('#termsAccepted').check();
    await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
    await page.locator('#auth-feedback').filter({hasText:'El registro no está disponible'}).waitFor(); passed();
    await page.goto(base+'/index.html#recuperar');
    await page.locator('#email').fill('stage2-browser@example.invalid');
    await page.getByRole('button',{name:'Enviar enlace de recuperación',exact:true}).click();
    await page.getByRole('heading',{name:'Revisa tu correo',exact:true}).first().waitFor();
    assert.equal(await page.locator('[data-auth-action="preview-reset"]').count(),0); passed();
    await page.goto(base+'/index.html#restablecer?token=invalid-test-token');
    await page.getByRole('heading',{name:'Este enlace ya no está disponible',exact:true}).first().waitFor();
    assert.equal(new URL(page.url()).hash,'#restablecer'); passed();
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.goto(base+'/index.html#acceso');
    await page.locator('#email').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#password').evaluate(el=>el===document.activeElement),true); passed();
    const verifyEndpoint='**/_allauth/browser/v1/auth/email/verify';
    await page.route(verifyEndpoint, route=>route.fulfill({status:200,json:{status:200}}));
    const incomplete=await page.evaluate(()=>AuthService.request('verify',{code:'invalid-test-value'}));
    assert.equal(incomplete.status,'unavailable'); passed();
    await page.unroute(verifyEndpoint);
    const loginEndpoint='**/_allauth/browser/v1/auth/login';
    await page.route(loginEndpoint, route=>route.fulfill({status:200,json:{status:200}}));
    await page.locator('#email').fill('stage2-browser@example.invalid');
    await page.locator('#password').fill(nextPassword);
    await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
    await page.locator('#auth-feedback').filter({hasText:'no está disponible'}).waitFor();
    assert.equal(new URL(page.url()).hash,'#acceso'); passed();
    await page.unroute(loginEndpoint);
    assert.deepEqual(errors,[]); passed();
    console.log(JSON.stringify({checks,failed:0,widths:[320,390,768,1024,1440],screenshots:false}));
  } finally {
    await context.close();
    await browser.close();
  }
})().catch(error=>{console.error('Falló una comprobación de navegador: '+error.name+' '+error.message.split('\n')[0]);process.exitCode=1;});

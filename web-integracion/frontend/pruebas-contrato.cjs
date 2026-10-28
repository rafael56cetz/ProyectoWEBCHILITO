// Integration adapter checks; not HTTP-server, PostgreSQL or browser evidence.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const context=vm.createContext({console,crypto:webcrypto,structuredClone,DOMException,AbortController,AbortSignal,Date,Map,Set,Object,Array,JSON,Number,String,RegExp,Error,encodeURIComponent,decodeURIComponent,
  URLSearchParams,document:{cookie:'csrftoken=test-csrf'},window:{dispatchEvent(){}},Event,fetch:null});
const calls=[];let respond;
context.fetch=async(path,options)=>{calls.push({path,options});return respond(path,options);};
for(const name of ['modelo/acceso.js','modelo/servicio-acceso.js','modelo/aplicacion.js','modelo/servicio-aplicacion.js','modelo/huerto-usuario.js','modelo/administracion.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+name,'utf8'),context);
const evaluate=code=>vm.runInContext(code,context);
const reply=(http,body)=>({status:http,json:async()=>body});
(async()=>{
  respond=()=>reply(403,{code:'forbidden'});
  assert.equal((await evaluate("UserGardenService.recordTask('inspection')")).status,'forbidden');
  const p=calls.at(-1);assert.equal(p.path,'/api/huertos/actual/mantenimiento');assert.equal(p.options.method,'POST');assert.equal(JSON.parse(p.options.body).type,'inspection');assert.match(p.options.headers['Idempotency-Key'],/^[0-9a-f-]{36}$/);assert.equal(p.options.headers['X-CSRFToken'],'test-csrf');
  let n=0;respond=()=>{if(n++===0)throw new Error('network');return reply(200,{status:'accepted'});};
  await evaluate("UserGardenService.recordTask('harvest')");await evaluate("UserGardenService.recordTask('harvest')");
  assert.equal(calls.at(-2).options.headers['Idempotency-Key'],calls.at(-1).options.headers['Idempotency-Key']);
  const token='aB'.repeat(21)+'_';const ticket='4c0eb447-d16e-4ef6-89e5-127ab340c1b1';
  respond=()=>reply(200,{status:'accepted',permission:{token,ticket,createdAt:Date.now(),expiresAt:Date.now()+60000}});
  assert.equal((await evaluate("UserGardenService.issuePermission('connection',true)")).status,'accepted');
  assert.equal(evaluate('UserGardenService.permission().token'),token);
  const before=calls.length;
  assert.equal((await evaluate("AdminService.validateToken('case',' '+ 'a'.repeat(43))")).status,'invalid-token');assert.equal(calls.length,before);
  respond=(path,options)=>{assert.equal(JSON.parse(options.body).token,token);return reply(200,{status:'accepted',session:{id:'session-id',expiresAt:Date.now()+60000}});};
  context.exactToken=token;await evaluate("AdminService.validateToken('case',exactToken)");
  assert.equal(calls.at(-1).path,'/api/admin/soporte/case/abrir');assert.ok(!calls.at(-1).path.includes(token));
  const caps=evaluate("AppModel.allowedAdmin({capabilities:['atender_soporte']}).map(x=>x.id)");assert.deepEqual(Array.from(caps),['admin/soporte']);
  const unicodePassword='🌶'.repeat(256);context.unicodePassword=unicodePassword;context.passwordConfig={password:{minLength:15,maxLength:256},code:{}};
  assert.equal(evaluate('AuthModel.passwordLength(unicodePassword)'),256);assert.equal(evaluate("AuthModel.validate('restablecer',{password:unicodePassword,confirmation:unicodePassword},passwordConfig).password"),undefined);
  assert.ok(evaluate("AuthModel.validate('restablecer',{password:unicodePassword+'🌶',confirmation:unicodePassword+'🌶'},passwordConfig).password"));
  assert.equal(evaluate("AuthModel.passwordLength(' '+unicodePassword+' ')"),258);
  for(const parameter of ['key','token']) {
    let replacement;context.linkLocation={hash:'#restablecer?'+parameter+'=protected-reset-secret',pathname:'/index.html',search:''};context.linkHistory={replaceState(_a,_b,url){replacement=url;}};
    assert.equal(evaluate('AuthModel.consumeResetLink(linkLocation,linkHistory)'),'protected-reset-secret');assert.equal(replacement,'/index.html#restablecer');
  }
  respond=(path,options)=>{assert.equal(path,'/_allauth/browser/v1/auth/password/reset');assert.equal(options.headers['X-Password-Reset-Key'],'protected-reset-secret');return reply(400,{status:400});};
  await evaluate("AuthService.request('inspect-reset',{token:'protected-reset-secret'})");assert.ok(!calls.at(-1).path.includes('protected-reset-secret'));
  respond=()=>reply(401,{status:401,meta:{is_authenticated:false},data:{flows:[{id:'login'}]}});
  assert.equal((await evaluate("AuthService.request('reset',{token:'reset-only-in-body',password:'Una clave extensa y válida 2048'})")).status,'reset-complete');
  respond=()=>reply(401,{status:401,meta:{is_authenticated:false},errors:[{code:'rejected'}]});
  assert.notEqual((await evaluate("AuthService.request('reset',{token:'invalid-reset',password:'Una clave extensa y válida 2048'})")).status,'reset-complete');
  respond=()=>reply(400,{status:400,errors:[{param:'key',code:'invalid'}]});
  assert.equal((await evaluate("AuthService.request('reset',{token:'expired-reset',password:'Una clave extensa y válida 2048'})")).status,'invalid-link');
  const missing={value:null,quality:'missing',at:null};
  context.inputGarden={status:'waiting',name:'Huerto',updatedAt:null,plants:[1,2,3].map(id=>({id,zoneId:String(BigInt(id)+9007199254740992n),name:'Planta '+id,crop:'Habanero propio',reading:missing})),temperature:missing,humidity:missing,tank:{state:'unknown',at:null}};
  // Use explicit long decimal text: no Number coercion for zone identities.
  context.inputGarden.plants.forEach((p,i)=>p.zoneId=String(9007199254740993n+BigInt(i)));
  assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].crop'),'Habanero propio');assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].zoneId'),'9007199254740993');assert.equal(evaluate('AppModel.garden(inputGarden).plants[0].reading.value'),null);
  for(const name of ['vista/icons.js','vista/paginas.js','vista/acceso.js','vista/aplicacion.js','vista/huerto-usuario.js','vista/administracion.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+name,'utf8'),context);
  context.bad='<img src=x onerror=alert(1)>';context.inputGarden.name=context.bad;context.inputGarden.plants[0].name=context.bad;context.inputGarden.plants[0].crop=context.bad;
  const markup=evaluate("UserGardenViews.render('huerto',{garden:AppModel.garden(inputGarden),soil:{moisture:{value:null,quality:'missing',at:null}},connection:{wifi:null,mqtt:null}})");assert.ok(!markup.includes('<img src=x'));assert.ok(markup.includes('&lt;img'));
  console.log('PASS frontend adapters: server refusal, CSRF, uncertain-write idempotency, exact support token, capabilities, crop/IDs/null, Unicode password bounds and secret-free reset URLs.');
})().catch(error=>{console.error(error);process.exitCode=1;});

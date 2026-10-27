const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path'),{webcrypto}=require('node:crypto');
const base=path.resolve(__dirname,'../..');
let startup;
const context=vm.createContext({crypto:webcrypto,structuredClone,DOMException,Date,Number,Object,Array,Set,JSON,PrivacyService:{},SiteController:{start(options){startup=options;}}});
const source=['modelo/aplicacion.js','modelo/huerto-usuario.js','modelo/administracion.js','vista-trabajo.js'].map(file=>fs.readFileSync(path.join(base,file),'utf8')).join('\n');
vm.runInContext(source+'\nglobalThis.services={UserGardenService,AdminService};',context);
(async()=>{
 const {authService:auth,appService:app}=startup,{UserGardenService:U,AdminService:A}=context.services;
 assert.equal((await auth.restore()).status,'unauthenticated');
 await auth.request('login',{email:'demo@example.com',password:'ChilitoDemo2026!'});
 assert.equal(U.supportAvailable,false);assert.equal((await U.issuePermission('pump',true)).status,'unavailable');assert.equal(U.permission(),null);assert.equal(U.supportReports().length,0);
 const garden=await app.request('garden');assert.equal(garden.status,'waiting');assert.equal(garden.updatedAt,null);assert.equal(garden.plants.length,3);
 for(const reading of [...garden.plants.map(p=>p.reading),garden.temperature,garden.humidity]){assert.equal(reading.value,null);assert.equal(reading.at,null);assert.equal(reading.quality,'missing');}
 assert.equal(garden.tank.state,'unknown');
 for(const range of ['1h','24h','7d']){
  const data=await U.load(range);assert.equal(data.garden.status,'waiting');assert.equal(data.soil.adc,null);assert.equal(data.soil.moisture.value,null);assert.equal(data.diagnosis,null);assert.equal(data.connection.wifi,null);assert.equal(data.connection.mqtt,null);
  for(const series of Object.values(data.history))assert.equal(series.length,0);
  assert.equal((await U.command('water',data)).status,'offline');
 }
 assert.equal((await app.request('notices')).items.length,0);
 assert.equal(A.snapshot().status,'forbidden');
 await app.request('logout');await auth.request('login',{email:'admin@example.com',password:'ChilitoDemo2026!'});
 const admin=A.snapshot();assert.equal(admin.nodes.length,0);assert.equal(admin.tickets.length,0);assert.equal(admin.activeVersion,null);assert.equal(admin.knowledge,'');
 assert.ok(Object.values(admin.metrics).every(value=>value===null));
 console.log('Verificados: arranque sin lecturas, fechas, series, avisos, diagnósticos, conexiones ni flota ficticios; roles de acceso, emisión de soporte bloqueada sin servicio y rechazo de órdenes sin conexión.');
})().catch(error=>{console.error(error);process.exitCode=1;});

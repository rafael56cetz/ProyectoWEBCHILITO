// Explicit test double. Never imported by the application or its index.html.
module.exports=function supportFixture(){
 let sequence=0;
 return {
  async issuePermission(){const now=Date.now(),n=++sequence;return {status:'accepted',permission:{token:'SOLO-PRUEBA-'+n,ticket:'CASO-PRUEBA-'+n,createdAt:now,expiresAt:now+86400000}};},
  async revokePermission(){return {status:'accepted'};}
 };
};

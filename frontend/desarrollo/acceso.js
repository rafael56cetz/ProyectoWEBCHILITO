// Design walkthrough only: no account, email, password or session persists.
FrontendDevelopment.createAuth=(security,scenario=()=>FrontendDevelopment.scenarios.auth)=>{
  let registered=false,attempts=0;
  return Object.freeze({
    async request(action,payload={}, {signal}={}){
      if(action.startsWith('passkey-'))return security.request(action,payload,{signal});
      const state=scenario();
      await FrontendDevelopment.pause(signal,state==='slow'?2200:400);
      if(['unavailable','unauthenticated'].includes(state))return {status:state};
      if(action==='login')return {status:'unavailable'}; // Login is navigation before service.
      if(action==='register'){
        if(payload.termsAccepted!==true)return {status:'terms-required'};
        if(Object.keys(AuthModel.validate('registro',{...payload,confirmation:payload.password})).length)return {status:'password-rejected'};
        attempts++;
        if(state==='registration-disabled')return {status:state};
        if(state==='retry'&&attempts===1)return {status:'unavailable'};
        if(state==='legal-version-changed'&&attempts===1)return {status:state};
        registered=true;return {status:'accepted',challengeId:'development-registration-only',previewCode:'246810'};
      }
      if(action==='verify'&&registered&&payload.challengeId==='development-registration-only')return {status:payload.code==='246810'?'verified':'incorrect-code',sessionConfirmed:state!=='accepted'};
      if(action==='resend'&&registered&&payload.challengeId==='development-registration-only')return {status:'accepted',challengeId:'development-registration-only',previewCode:'246810'};
      if(action==='request-reset')return {status:'accepted',previewResetToken:'development-reset-only'};
      if(action==='inspect-reset')return {status:payload.token==='development-reset-only'?'reset-valid':'invalid-link'};
      if(action==='reset')return {status:payload.token==='development-reset-only'?'reset-complete':'invalid-link'};
      if(action==='change-password')return {status:'password-changed'};
      return {status:'unavailable'};
    }
  });
};

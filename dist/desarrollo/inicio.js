// Single explicit development composition. No URL flag selects identity or transport.
// Replace only after authorization to integrate a backend.
(()=>{
  const security=FrontendDevelopment.createSecurity();
  const privacy=FrontendDevelopment.createPrivacy();
  const auth=FrontendDevelopment.createAuth(security);
  const router=SiteController.start({
    authService:auth,appService:FrontendDevelopment.appService,privacyService:privacy,
    passkeyInteraction:security.interact,review:true,previewNavigation:true
  });
  // Development tests refresh the same application after selecting in-memory responses.
  // This is not authentication or a future production protocol.
  FrontendDevelopment.router=router;
})();

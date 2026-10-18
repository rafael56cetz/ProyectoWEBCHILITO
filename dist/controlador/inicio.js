// The only active composition: real browser session, no injected development adapters.
(async () => {
  let config = AuthConfig;
  try {
    const policy = await ChilitoHTTP.configure(AbortSignal.timeout(10000));
    config = Object.freeze({registrationAllowed:policy.registrationAllowed,password:policy.password,code:policy.code,requestTimeoutMs:20000});
  } catch { /* Every action still fails closed if the backend is unavailable. */ }
  SiteController.start({config,canEnter:options => AuthService.restore(options)});
})();

// Isolated frontend preview. This file is loaded only by this copied index.html.
// Review access is local; telemetry starts empty. No fetch, cookies, mail or database writes.
(() => {
  let signedIn = false, role='user';
  let verificationEmail = '';
  let accountEmail = '';
  const expiry = () => new Date(Date.now() + 600000).toISOString();
  const missingReading = () => ({value:null,quality:'missing',at:null});
  const config = {
    registrationAllowed: true,
    password: { minLength: 12, maxLength: 128, requirements: ['12 caracteres', 'Elige una contraseña que no uses en otros servicios.'] },
    code: { length: 6, pattern: '^[0-9]{6}$', inputMode: 'numeric', expiresAfterSeconds: 600, resendAfterSeconds: 5 },
    requestTimeoutMs: 20000
  };
  const session = () => signedIn ? { status: 'authenticated', sessionConfirmed: true, role }
    : verificationEmail ? { status: 'verification-required', email: verificationEmail, expiresAt: expiry() }
    : { status: 'unauthenticated' };
  const auth = {
    passkeysAvailable: false,
    async restore() { return session(); },
    async verificationContext() { return session(); },
    async request(action, payload = {}) {
      if (action === 'login') {
        if (!['demo@example.com','admin@example.com'].includes(payload.email) || payload.password !== 'ChilitoDemo2026!') return { status: 'invalid-credentials' };
        signedIn = true;
        role=payload.email==='admin@example.com'?'admin':'user';
        accountEmail = payload.email;
        verificationEmail = '';
        return session();
      }
      if (action === 'register') {
        if (!payload.termsAccepted) return { status: 'terms-required' };
        verificationEmail = payload.email;
        return { status: 'accepted', expiresAt: expiry(), resendAfterSeconds: 5 };
      }
      if (action === 'verify') {
        if (!verificationEmail) return { status: 'verification-expired' };
        if (payload.code !== '246810') return { status: 'incorrect-code' };
        role='user';
        accountEmail = verificationEmail;
        verificationEmail = '';
        signedIn = true;
        return { status: 'verified', sessionConfirmed: true };
      }
      if (action === 'resend') return verificationEmail
        ? { status: 'accepted', expiresAt: expiry(), resendAfterSeconds: 5 } : { status: 'verification-expired' };
      if (action === 'request-reset') return { status: 'accepted' };
      if (action === 'inspect-reset') return { status: payload.token === 'vista-de-prueba' ? 'reset-valid' : 'invalid-link' };
      if (action === 'reset') return { status: payload.token === 'vista-de-prueba' ? 'reset-complete' : 'invalid-link' };
      if (action === 'change-password') return { status: signedIn ? 'password-changed' : 'unauthenticated' };
      return { status: 'unavailable' };
    }
  };
  const notices = [];
  const app = {
    async request(action, payload = {}) {
      if (action === 'logout') {
        signedIn = false;
        verificationEmail = '';
        AdminService.closeRemote();
        role='user';
        return { status: 'accepted' };
      }
      if (!signedIn) return { status: 'unauthenticated' };
      if (action === 'profile') return { status: 'ready', email: accountEmail, verified: true };
      if (action === 'garden') return {
        status: 'waiting', name: 'Mi huerto', updatedAt: null,
        plants: [1, 2, 3].map(id => ({id,name:`Planta ${id}`,reading:missingReading()})),
        temperature:missingReading(),humidity:missingReading(),tank:{state:'unknown',at:null}
      };
      if (action === 'notices') return { status: 'empty', items: structuredClone(notices) };
      const item = notices.find(item => item.id === payload.id);
      if (action === 'notice') return item ? { status: 'ready', items: [structuredClone(item)] } : { status: 'not-found' };
      if (action === 'mark-read' && item) {
        item.read = true;
        return { status: 'accepted', id: item.id, item: structuredClone(item) };
      }
      return { status: 'unavailable' };
    }
  };
  // Empty presentation contract. Replace with readings from the future backend adapter.
  UserGardenService.configure(async () => ({
    garden:await app.request('garden'),
    soil:{adc:null,moisture:missingReading()},
    connection:{wifi:null,mqtt:null},diagnosis:null,
    history:{soil:[],temperature:[],humidity:[]}
  }));
  AdminService.configure({isAdmin:()=>signedIn&&role==='admin'});
  // Keep the existing inactive privacy / passkey screens as they are in the original.
  SiteController.start({ config, authService: auth, appService: app,
    privacyService: PrivacyService, canEnter: () => auth.restore() });
})();

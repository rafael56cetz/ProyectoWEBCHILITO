// No transport or real sessions. Replace this boundary only after agreeing the backend contract.
const AppService = Object.freeze({
  async request(action, payload = {}, {signal} = {}) {
    if (signal?.aborted) throw new DOMException('Cancelled','AbortError');
    if (action === 'garden') return {status:'waiting'};
    if (action === 'profile') return {status:'ready',email:null,verified:null};
    if (action === 'notices') return {status:'error',items:[]};
    return {status:'unavailable'};
  }
});

// Deliberately disconnected. No requests, receipts, storage or real case files.
const PrivacyService = Object.freeze({
  available:false,
  async request(action, payload = {}, {signal} = {}) {
    if(signal?.aborted) throw new DOMException('Cancelled','AbortError');
    return {status:'unavailable'};
  }
});

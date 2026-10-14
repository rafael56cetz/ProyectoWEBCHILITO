// Integration boundary only. No endpoint, account, email or session exists here.
// Kevin can replace request() with the agreed HTTP adapter and server-side session handling.
const AuthService = Object.freeze({
  async request(action, payload, { signal } = {}) {
    if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
    return { status: 'unavailable' };
  }
});

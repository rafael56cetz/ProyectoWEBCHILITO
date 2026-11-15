// MODELO · Público: envío del formulario de preguntas sobre el producto.
// Define: ProductContact.

// ── Contacto ──
// Pregunta sobre el producto. La decide y entrega el servidor; aquí no se guarda nada.
const ProductContact = Object.freeze({
  validEmail: value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
  async send({name,email,message,website}) {
    try {
      const response = await ChilitoHTTP.request('/api/contacto',{method:'POST',body:{name,email,message,website}});
      if(response.http === 200 && response.body?.status === 'accepted') return 'accepted';
      return response.http === 429 ? 'limited' : response.http === 400 ? 'invalid' : 'unavailable';
    } catch { return 'unavailable'; }
  }
});

const LegalViews = Object.freeze({
  render(document, route) {
    const other = route === 'terminos' ? 'privacidad' : 'terminos';
    const isTerminos = route === 'terminos';
    const title = isTerminos ? 'Términos y condiciones de uso' : 'Aviso de privacidad integral';
    const content = isTerminos ? `
      <h3>1. Objeto y Alcance</h3>
      <p>El presente documento establece las condiciones de uso de la plataforma digital y los servicios asociados a la estación inteligente de cultivo de chile habanero "El Chilito".</p>
      <h3>2. Uso de la Plataforma</h3>
      <p>El usuario se compromete a hacer uso de la plataforma con fines lícitos, protegiendo sus credenciales de acceso y manteniendo actualizados los datos vinculados a su cuenta.</p>
      <h3>3. Monitoreo y Automatización</h3>
      <p>Las lecturas de sensores, ciclos de iluminación LED y riego automático son proporcionados como asistencia para el cultivo interior. Las recomendaciones emitidas por el asistente digital tienen fines informativos y de apoyo al usuario.</p>
      <h3>4. Propiedad Intelectual</h3>
      <p>Todos los diseños, software, marcas y contenidos pertenecen a El Chilito o a sus respectivos licenciantes, estando protegidos por la legislación aplicable.</p>
    ` : `
      <h3>1. Responsable del Tratamiento</h3>
      <p>El Chilito es responsable del tratamiento y protección de sus datos personales conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares.</p>
      <h3>2. Datos Personales Recabados</h3>
      <p>Para la prestación de los servicios recabamos su correo electrónico, credenciales de acceso cifradas y datos técnicos asociados a la telemetría del huerto.</p>
      <h3>3. Finalidades del Tratamiento</h3>
      <p>Los datos son utilizados para la autenticación en la plataforma, personalización de las recomendaciones de cultivo, notificaciones sobre el estado del huerto y atención de solicitudes de soporte.</p>
      <h3>4. Ejercicio de Derechos ARCO</h3>
      <p>Usted tiene derecho a conocer qué datos personales tenemos, para qué los utilizamos y las condiciones de su uso (Acceso), solicitar su corrección (Rectificación), su eliminación (Cancelación) u oponerse al tratamiento de los mismos (Oposición). Puede presentar una solicitud en nuestro apartado de Derechos ARCO.</p>
    `;
    return `${siteHeader({extra:'legal-header',action:'<a class="button compact btn-liquid-light" href="#acceso">Iniciar sesión</a>'})}
      <main class="legal-content container" id="contenido" tabindex="-1">
        <h1>${authEscape(title)}</h1>
        <section class="bento-panel legal-document" aria-labelledby="legal-doc-title">
          <h2 id="legal-doc-title" class="sr-only">${authEscape(title)}</h2>
          ${content}
        </section>
        <nav class="legal-actions" aria-label="Enlaces del documento">
          <a class="button btn-liquid-brand" href="#inicio">Volver</a>
          <a class="button btn-liquid-light" href="#${other}">${authEscape(PrivacyModel.documents[other].title)}</a>
          ${route === 'privacidad' ? '<a class="button btn-liquid-light" href="#derechos-arco">Derechos ARCO</a>' : ''}
        </nav>
      </main>${publicFooter()}`;
  }
});

# Revisión de adaptación a teléfono, tablet y escritorio

Fecha: 17 de octubre de 2026. Proyecto activo: El-Chilito-Aplicacion-Web. Revisión del frontend HTML/CSS/JavaScript existente, con su organización MVC, componentes, Geist y Liquid Glass.

## Hallazgos y correcciones

1. Algunos botones privados se dibujaban con 38 o 40 px de alto por reglas anteriores de las variantes y pestañas. Se añadió una regla compartida dentro del ámbito privado para conservar al menos 44 px de altura táctil. Incluye salida, filtros, pestañas de cuenta y detalle de avisos; conserva las variantes y estilos existentes.
2. En portada a 844 × 390 el título comenzaba por encima del límite inferior del encabezado. La altura fija de 100vh impedía que la portada creciera con su texto. Ahora usa altura automática, mínimo de 100svh y reserva el alto medido del encabezado. Se retiró la segunda reserva redundante del contenido móvil.

La primera revisión registró 89 combinaciones con hallazgos, principalmente por repetición de esos botones entre pantallas. Corresponden a las dos causas anteriores. No aparecieron errores JavaScript ni desbordamientos horizontales en esa primera pasada.

## Alcance verificado

Once tamaños de viewport en Chromium: 320 × 568, 390 × 844, 568 × 320, 844 × 390, 768 × 1024, 820 × 1180, 900 × 650, 1024 × 768, 1180 × 820, 1440 × 900 y 640 × 450 px. Incluye pantallas estrechas, orientación horizontal, tablets y escritorio. 640 × 450 comprueba redistribución en un espacio equivalente a la mitad de 1280 × 900; no se presenta como una prueba del zoom nativo del navegador.

Pantallas: portada, acceso, registro, recuperación, restablecimiento con enlace de fixture válido, términos, aviso de privacidad, derechos ARCO público, huerto, lista y detalle de avisos, asistente, perfil, cambio de contraseña, seguridad, privacidad de cuenta y diálogo de cierre de sesión. Registro y recuperación también se comprobaron con errores de campos vacíos. Los apartados aplazados mantienen sus estados actuales; esta revisión no los activa.

Se revisaron:
- Desbordamiento horizontal, texto recortado y límites de tarjetas/campos.
- Botones habilitados con objetivo mínimo de 44 px y campos con tipografía mínima de 16 px.
- Separación del título respecto del encabezado.
- Primer y último control disponible de cada pantalla, también enlaces del pie: foco desplazado al área visible y comprobación de que el centro del control no esté cubierto.
- Diálogo de salida dentro del viewport incluso con 320 px de altura.
- Nombres largos de plantas y contenido largo de avisos presentes en las fixtures.
- Navegación, cancelación de salida, teclado y movimiento reducido mediante la batería existente.

Resultados finales: **209 combinaciones de pantalla/estado y tamaño revisadas, cero incidencias geométricas y cero errores JavaScript**. La batería de registro añadió comprobaciones de la pantalla de código en los once tamaños y completó **81 comprobaciones**, sin correo SMTP real. La regresión del huerto, navegación y confirmación de salida completó otras **161 comprobaciones**, además de 3 aserciones de lectura concurrente. El informe local detallado se guarda en revision/resultado-responsivo.json, dentro de la carpeta de evidencias ya excluida de Git.

## Archivos y responsabilidades

| Archivo | Responsabilidad |
| --- | --- |
| dist/vista/css/geist-glass.css | Vista: altura y espacio adaptable de la portada; reutiliza la variable del encabezado. |
| dist/vista/css/aplicacion.css | Vista: altura táctil común de botones privados. |
| backend/tests/ui_responsive.cjs | Nueva revisión de las vistas existentes en once tamaños; falla al detectar problemas y no crea capturas. |
| backend/tests/ui_local_registration.cjs | Amplía la comprobación del código de correo a horizontal, tablet y pantalla estrecha. |
| backend/tools/comprobar_frontend.py | Opción --etapa 3 --responsive con la misma aplicación, base y limpieza de fixtures existentes. Proporciona un enlace de restablecimiento exclusivamente para la cuenta aislada. |
| infra/verificar_entrega.ps1 | Incluye la revisión adaptable en el verificador existente. |
| docs/REVISION-RESPONSIVA.md | Este informe. |
| docs/MEJORAS-DE-ACCESO.md | Referencia acumulativa a esta revisión. |

No se modificaron modelos, controladores de producto, rutas de navegación, dependencias ni contratos de datos durante esta revisión. Se preservaron los cambios previos del equipo.

## Repetición y límites

Desde backend, con el entorno de pruebas ya preparado:

    python tools/comprobar_frontend.py --etapa 3 --responsive

El ejecutor usa PostgreSQL de pruebas y fixtures con limpieza; no debe ejecutarse simultáneamente con otras pruebas sobre esa base. No crea cuentas de muestra en la principal, no envía mensajes reales y no publica el sitio.

Se comprobó sintaxis JavaScript, sintaxis PowerShell del verificador y git diff --check, sin errores. Las advertencias de finales de línea pertenecen a cambios anteriores. Se verificó por HTTP que el servidor habitual entrega ambas hojas de estilo actualizadas.

Las pruebas se realizaron en tamaños simulados en Chromium. Queda la comprobación en dispositivos físicos y navegadores móviles reales, especialmente teclado virtual, gestos y áreas seguras del sistema; no se afirma que la emulación pruebe esos comportamientos. No se abrieron puertos ni se creó un acceso desde teléfonos a la instancia local.

Revisión personal: http://127.0.0.1:8766/index.html, recargando con Ctrl+F5.

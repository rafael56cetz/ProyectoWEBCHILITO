# Referencias verificadas para la capa de datos

Consulta del 27 de octubre de 2026. Selección limitada a la persistencia web, los contratos Django y los controles relacionados. No es una evaluación integral ni acredita un nivel ASVS. La presencia de un requisito de nivel 2 o 3 en esta selección no asigna ese nivel al producto.

El documento del proyecto `IOT_Chilito_Marcos_de_Seguridad.docx` propone NIST SSDF 1.1 y OWASP ASVS 5.0.0, distingue entrega web de hardware posterior y exige relacionar control, implementación y evidencia. El encargo actual limita ese alcance: no se incorporan WSTG, STRIDE, marcos IoT, políticas legales, ARCO, WebAuthn ni ejecución física.

## Fuentes fijadas

- OWASP ASVS **5.0.0**, etiqueta publicada **v5.0.0_release**, catálogo CSV oficial: https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv
- Publicación oficial ASVS 5.0.0: https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release
- NIST SSDF **1.1**, SP 800-218 final de febrero de 2022: https://csrc.nist.gov/pubs/sp/800/218/final
- Tabla de prácticas y tareas de SP 800-218: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf

No se utilizó la rama de trabajo de ASVS ni un borrador posterior de SSDF como sustituto de esas versiones. Los ejemplos de implementación de NIST no se presentan como mandatos adicionales.

## ASVS seleccionado

Descriptores resumidos; los identificadores se comprobaron contra el catálogo oficial. La columna de comprobación describe el criterio que deberá satisfacerse, no un resultado ya obtenido.

| Referencia exacta | Foco | Aplicación concreta y comprobación prevista |
| --- | --- | --- |
| v5.0.0-1.2.4 | Consultas parametrizadas | ORM o parámetros enlazados; probar texto con apóstrofes y apariencia SQL como dato, sin listas negras de palabras. |
| v5.0.0-6.2.1 | Longitud de contraseña | Mantener la decisión del proyecto de 15–256 caracteres. Este requisito admite un mínimo menor y recomienda 15; no atribuirle una obligación inexistente. |
| v5.0.0-6.2.8 | Contraseña sin transformación | Reutilizar validación/hash del framework; comprobar espacios y Unicode sin recorte ni cambio de mayúsculas. |
| v5.0.0-6.2.9 | Contraseñas largas | Comprobar aceptación de longitudes hasta 256. La longitud de la columna del hash es distinta. |
| v5.0.0-8.1.1 | Reglas de acceso documentadas | Enumerar actor, capacidad, membresía y recurso de cada futura operación API. |
| v5.0.0-8.2.1 | Permiso de función | Probar administrador con capacidad explícita y cuenta sin ella; `is_staff` y `is_superuser` no serán atajos automáticos. |
| v5.0.0-8.2.2 | Permiso de recurso | Probar acceso propio, ajeno, membresía inactiva y permiso de otro caso/dispositivo. |
| v5.0.0-8.3.1 | Control en servidor | Las funciones de persistencia verifican identidad confiable; la navegación y `session.role` solo presentan el resultado. |
| v5.0.0-8.3.2 | Revocación efectiva | Reautorizar cada operación de soporte. La fila bloqueada coordina revocación y uso; no basta revisar al abrir consola. |
| v5.0.0-13.2.2 | Mínimos privilegios | Probar rol de ejecución sin superusuario, DDL, concesión de privilegios ni alteración del historial. Separar rol migrador. |
| v5.0.0-15.3.3 | Campos permitidos | Cada servicio admite únicamente parámetros definidos. Actor, propietario y privilegios proceden del servidor. |
| v5.0.0-15.4.2 | Comprobación y uso atómicos | Probar concurrencia real entre revocación y operación con transacciones PostgreSQL independientes. |
| v5.0.0-15.4.3 | Bloqueos consistentes | Documentar el orden de bloqueos; probar ambas intercalaciones y límites de espera. |
| v5.0.0-16.2.1 | Metadatos de auditoría | Actor, fecha con zona, acción, recurso, permiso y resultado; verificar persistencia en la misma transacción pertinente. |
| v5.0.0-16.2.5 | Exclusión de secretos | Token completo, contraseñas, cookies y credenciales no entran en auditoría ni resultados de pruebas. |
| v5.0.0-16.4.2 | Protección del registro | Probar rechazo de UPDATE, DELETE y TRUNCATE del historial con rol de ejecución. El propietario no se considera adversario cubierto. |

La clasificación del catálogo para cada identificador puede consultarse en la columna `L` del CSV. La selección no evalúa automáticamente todos los requisitos de esos capítulos.

## Controles que dependen del despliegue

Las referencias siguientes se documentan como responsabilidades de configuración, no como controles ya satisfechos por SQL:

- **v5.0.0-12.3.1:** transporte entre servicios. Una prueba local en socket/loopback aislado no demuestra TLS de producción. Una conexión remota deberá verificar certificado y nombre del servidor sin degradación silenciosa.
- **v5.0.0-13.3.1 y v5.0.0-13.3.2:** custodia externa y acceso limitado a secretos. Variables de prueba sintéticas no acreditan una solución de gestión de secretos desplegada.
- **v5.0.0-14.1.2:** documentar protección, conservación, acceso y respaldo. La política legal de retención queda fuera del encargo; el paquete debe evitar borrado accidental y dejar explícita esa decisión pendiente.
- **v5.0.0-16.4.3:** copia de registros a sistema separado. El historial local protegido no demuestra resistencia a una toma del propietario de PostgreSQL ni reemplaza ese sistema.

## SSDF 1.1 aplicado al trabajo

Los localizadores de página se expresan como número impreso en SP 800-218; el contador del visor PDF es ocho páginas mayor.

| Tarea | Localizador | Actividad del paquete | Evidencia esperada y límite |
| --- | --- | --- | --- |
| PW.1.2 | p.11 | Conservar decisiones de relaciones, tokens, permisos y concurrencia. | Contrato y registro de decisiones; no sustituye el diseño general de etapa 3. |
| PW.1.3 | p.11 | Reutilizar Django/allauth para cuentas y sesiones. | Dependencias fijadas y mecanismos identificados; sin segundo sistema de autenticación. |
| PW.5.1 | p.13 | Aplicar validación, parámetros y transacciones. | Código y pruebas negativas; no certificado de software seguro. |
| PW.7.2 | p.14 | Revisar código y corregir hallazgos concretos. | Registro de revisión y correcciones; la autoinspección no equivale a revisión humana independiente. |
| PW.8.2 | p.15 | Ejecutar pruebas de requisitos y regresión. | Comandos, versiones, resultados y pendientes; distinguir tests estáticos de PostgreSQL real. |
| PW.9.1 | p.16 | Definir configuración segura de datos. | Roles, privilegios, red, transporte y secretos; límites del entorno identificados. |
| PW.9.2 | p.16 | Implementar y explicar la configuración. | SQL administrativo e instrucciones reproducibles; verificar antes de desplegar. |
| PS.3.1 | p.10 | Conservar paquete y procedencia verificable. | Huellas de fuentes y entregables; no confundir copia local con publicación. |

## Uso en la documentación final

Para cada control, quien cierre `seguridad-base-de-datos.md` debe enlazar el archivo y la prueba realmente existentes y copiar el resultado de `resultado-pruebas.md`. Si PostgreSQL no pudo iniciarse, marcar relaciones, privilegios, instalación/actualización y concurrencia como **implementados pero pendientes de ejecución**, aunque la sintaxis o las pruebas sin base hayan pasado.

Este archivo solo verifica referencias y criterios. No ejecutó pruebas ni afirma integración de la interfaz, API, correo, sensores o servicios externos.

# Resultado de comprobaciones de la capa de datos

**27 de octubre de 2026. Estado: validación PostgreSQL sintética aprobada.** No es una entrega de frontend conectado ni una API en funcionamiento.

## Entorno y alcance ejecutado

- Python 3.13.17, Django 5.2.18, django-allauth 65.20.0 y psycopg 3.3.6; dependencias fijadas conservadas.
- **PostgreSQL 17.11**, imagen oficial `postgres:17`, contenedor propio con nombre único, etiqueta de pruebas, almacenamiento efímero y puerto aleatorio publicado solo en `127.0.0.1`. No se utilizó SQLite.
- Docker ya respondió desde esta sesión. No se cambiaron permisos del sistema durante la validación. Un reintento sufrió timeout de la revisión automática antes de ejecutarse; el reintento autorizado posterior sí terminó.
- Roles, cuentas, claves y bases de pruebas fueron sintéticos. El contenedor se detuvo al finalizar. No se accedió a bases reales ni se importaron secretos originales.

## Resultados efectivos

| Comprobación | Resultado observado | Evidencia |
| --- | --- | --- |
| Instalación vacía por Django | Migraciones aplicadas en la segunda base sintética | `evidencias/ejecucion-postgres.json` |
| Actualización SQL desde baseline | Conservó cuenta y hash, nombre de planta existente, membresías, avisos y lecturas; completó las tres plantas | Mismo archivo; `backend/tools/verificar_postgres.py` |
| Equivalencia de rutas | Catálogos de restricciones de instalación Django y actualización SQL coincidentes; instalación validada con historial sin pendientes | Mismo archivo; `backend/tools/validar_instalacion.py` |
| Integridad PostgreSQL | **22 pruebas aprobadas**: FK, CHECK, UNIQUE, tres plantas, coherencia, historia, avisos y auditoría | `evidencias/pruebas-postgres-stdout.txt` |
| Servicios PostgreSQL | **20 pruebas aprobadas**, incluidas las dos intercalaciones concurrentes de revocación/uso | Mismo archivo |
| Pruebas sin base | **9 aprobadas**: contraseña/hash (2), contrato criptográfico (4) y contrato de migraciones (3) | Mismo archivo; también existe la ejecución previa en `evidencias/pruebas-sin-base.txt` |
| Runtime limitado | Operaciones de mantenimiento, soporte, revocación y solicitud de cambio persistidas; denegados DDL, TRUNCATE, alteración de auditoría, membresía y escritura en asignación de privilegios probada | `evidencias/ejecucion-postgres.json`; `backend/tools/runtime_service_probe.py` |
| Respaldo/restauración | `pg_dump -Fc` y `pg_restore --exit-on-error` ejecutados; coinciden restricciones, estado de validación y cantidades de cuatro tablas | `evidencias/ejecucion-postgres.json`; límites abajo |
| Django check y compilación Python | Sin problemas; código del paquete compilado | `evidencias/check-django.txt`; `evidencias/verificacion-local.json` |
| SQL generado | Cinco migraciones nuevas y 31 baseline; regeneración sin conexión idéntica después de la corrección | `evidencias/generacion-sql.txt`; `evidencias/plan-migraciones.json` |
| Conservación de fuentes | 96 archivos originales comparados sin cambios; siete migraciones históricas copiadas idénticas | `evidencias/conservacion-fuentes.json` |

**Total de la suite final: 51 pruebas, 51 aprobadas; 42 requieren PostgreSQL y 9 no requieren base.** Los ensayos de instalación, actualización, runtime y respaldo son comprobaciones adicionales del harness. No quedan fallos vigentes de esta ejecución.

## Fallos encontrados y correcciones

1. El primer ensayo se detuvo con `InsufficientPrivilege` antes de completar la actualización. El SQL generado fijaba `search_path=pg_catalog,public`: sus operaciones de creación no cualificadas podían intentar crear objetos en el catálogo. Se corrigió **solo el generador del paquete** a `public,pg_catalog` para esta ruta de migración como propietario y se regeneró `el_chilito.sql`. Las rutas de actualización e instalación aprobaron después. Los roles runtime y las funciones conservan su configuración propia.
2. La restauración terminó sin errores, pero la comparación textual de restricciones falló. PostgreSQL reescribe la conversión de `varchar[]` a `text[]` como conversiones por elemento. Al normalizarlas, el comparador también eliminaba un paréntesis de `ANY(...)`. Se corrigió esa comparación, conservando valores, orden, operadores y `convalidated`; no se modificó el esquema para acomodar el ensayo. Se comprobó además sin conexión que valores u operadores distintos no resultan equivalentes.
3. Se repitió el harness completo después de las correcciones. La ejecución final terminó con código 0 y `status: passed`. `evidencias/diferencia-restauracion.json` se conserva identificado como diagnóstico histórico del comparador, no como fallo vigente. `evidencias/historial-validacion-postgres.json` registra las etapas y sus límites.

Las correcciones previas sobre restricciones, bloqueos, sesiones e historial también quedaron ejercitadas por la suite PostgreSQL final. No se rehicieron modelos ni se añadieron funciones de producto en esta continuación.

## Reproducción

Desde la raíz del paquete:

```sh
PY='<entorno-python>/bin/python'
"$PY" backend/tools/verificar_postgres.py
```

Requiere Docker accesible. El harness crea su propia instancia efímera y solo detiene ese contenedor. No emplea el backend ni PostgreSQL originales. Guarda el resultado en `evidencias/ejecucion-postgres.json` y el resumen de la suite en `evidencias/pruebas-postgres-stdout.txt`; los dos archivos se renuevan al repetirlo.

También se ejecutaron `manage.py check`, compilación Python y regeneración determinista del SQL. La comparación de estado modelos/migraciones sin diferencias del ensayo previo permanece documentada; la ejecución PostgreSQL posterior aporta la comprobación de instalación e historial.

## Límites y pendientes

El respaldo compara el catálogo de restricciones y su estado de validación, más las cantidades de `cuentas_usuario`, `huerto_zona`, `datos_mantenimiento` y `datos_auditoria`. **No compara todos los objetos ni el contenido fila por fila**, ni demuestra recuperación de producción, cifrado, alta disponibilidad o recuperación a un punto en el tiempo. El dump no se conserva como entregable; solo su SHA-256.

Siguen fuera de esta validación: API HTTP autenticada, conexión del frontend, navegador, registro/recuperación reales, SMTP, fuerza bruta, TLS, despliegue/VM, WebAuthn y servicios físicos/IA. Las solicitudes siguen siendo `pending`; no acreditan actuación ni despliegue. No se enviaron correos, no se crearon cuentas reales, no se modificó Notion ni GitHub.

**El paquete está validado para los ensayos sintéticos descritos. La integración de la aplicación permanece pendiente y requiere su autorización y pruebas propias.**

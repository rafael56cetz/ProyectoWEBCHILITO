# Herramientas de integración

- `local.py start|stop`: servidor local con PostgreSQL sintético propio y volumen conservado. Configuración secreta externa, bajo `/tmp` y permisos restringidos.
- `operador.py EMAIL --huerto --capacidades ...`: asigna recursos o capacidades a una cuenta existente. Solo operador local; sin endpoints de autoasignación.
- `verificar_integracion.py`: instancia efímera separada, regresiones de datos, HTTP y prueba del runtime limitado; correo en memoria.
- `entorno.py`: preparación común de esas instancias; imagen PostgreSQL fijada por digest.
- `seed_runtime.py` y `probar_runtime.py`: fixtures y comprobaciones exclusivamente sintéticas del ensayo.

La ruta de instalación de la aplicación usa `migrate`. No ejecutar el SQL histórico encima de esa instalación. Las herramientas originales de preparación/generación SQL permanecen en el paquete validado anterior; no se copian como herramientas operativas de la aplicación nueva.

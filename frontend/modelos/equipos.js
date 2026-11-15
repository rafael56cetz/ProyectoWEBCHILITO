// MODELO · Equipos: inventario de equipos para quien gestiona dispositivos (alta, detalle, desvincular, rotar credencial y retirar).
// Define: EquipmentModel, EquipmentService.

// ── Inventario ──
// Validación previa al envío; el servidor y la base vuelven a validar todo.
const EquipmentModel = Object.freeze({
  validate(values) {
    if(!/^[A-Za-z0-9][A-Za-z0-9-]{3,31}$/.test(values.identifier)) return {field:'identifier', message:'Usa de 4 a 32 letras, números o guiones, empezando por letra o número.'};
    if(!/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(values.mac)) return {field:'mac', message:'Escribe la MAC con el formato AA:BB:CC:DD:EE:FF.'};
    if(values.firmware && !/^[A-Za-z0-9._-]{1,32}$/.test(values.firmware)) return {field:'firmware', message:'El firmware solo lleva letras, números, punto, guion y guion bajo.'};
    return null;
  }
});

const EquipmentService = (() => {
  const base = '/api/admin/equipos';
  const device = (id, rest = '') => AdminHTTP.validId(id) ? `${base}/${id}${rest}` : null;
  return Object.freeze({
    list: (filters, page) => AdminHTTP.call(base + AdminHTTP.query({...filters, page})),
    create: values => AdminHTTP.call(base, {method:'POST', body:values}),
    detail: (id, page) => AdminHTTP.call(device(id) && device(id) + AdminHTTP.query({page})),
    unlink: id => AdminHTTP.call(device(id, '/desvincular'), {method:'POST', body:{}}),
    rotate: id => AdminHTTP.call(device(id, '/rotar'), {method:'POST', body:{}}),
    retire: id => AdminHTTP.call(device(id, '/retirar'), {method:'POST', body:{}})
  });
})();

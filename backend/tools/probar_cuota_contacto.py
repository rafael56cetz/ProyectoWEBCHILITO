"""Comprueba en un entorno de pruebas desplegado el límite de 5 envíos por hora y por IP de «Consíguelo».

Envía datos inválidos a propósito: consumen cuota, pero no crean consultas ni correos.
Usa cabeceras X-Forwarded-For falsas distintas en cada envío: si la cuota se salta, el proxy está mal configurado.

  Equipo A:  python probar_cuota_contacto.py https://pruebas.ejemplo
             Espera: 5 respuestas 400 y la sexta 429.
  Equipo B, desde otra red, justo después:
             python probar_cuota_contacto.py https://pruebas.ejemplo --segundo-cliente
             Espera: 400. Un 429 indica que todos los visitantes comparten la cuota.

Agota la cuota de esa IP durante una hora. No usar contra la base oficial ni en producción con visitantes.
"""
import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

CUERPO = json.dumps({'name': '', 'email': 'no-valido', 'message': '', 'website': ''}).encode()


def enviar(abridor, base, csrf, falsa):
    peticion = urllib.request.Request(base + '/api/contacto', data=CUERPO, method='POST', headers={
        'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'Origin': base, 'Referer': base + '/', 'X-Forwarded-For': falsa})
    try:
        return abridor.open(peticion, timeout=20).status
    except urllib.error.HTTPError as respuesta:
        return respuesta.code


def main():
    opciones = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opciones.add_argument('url')
    opciones.add_argument('--segundo-cliente', action='store_true')
    argumentos = opciones.parse_args()
    base = argumentos.url.rstrip('/')
    galletas = http.cookiejar.CookieJar()
    abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(galletas))
    abridor.open(base + '/api/acceso/configuracion', timeout=20)
    csrf = next((g.value for g in galletas if g.name == 'csrftoken'), None)
    if not csrf:
        sys.exit('El servidor no entregó la cookie CSRF')
    envios, esperado = 1, [400]
    if not argumentos.segundo_cliente:
        envios, esperado = 6, [400] * 5 + [429]
    obtenido = [enviar(abridor, base, csrf, f'203.0.113.{i + 1}') for i in range(envios)]
    print('Obtenido:', obtenido, '| Esperado:', esperado)
    if obtenido != esperado:
        sys.exit('FALLO: revisa CHILITO_BEHIND_PROXY y CHILITO_TRUSTED_PROXY_COUNT, o espera una hora si esa IP ya gastó su cuota')
    print('Correcto')


if __name__ == '__main__':
    main()

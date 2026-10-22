
import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

PACIENTES_URL = os.getenv(
    'PACIENTES_URL',
    'https://integrantes-hospital-pacientes-1.onrender.com'
).rstrip('/')

LABORATORIO_URL = os.getenv(
    'LABORATORIO_URL',
    'https://integrantes-hospital-laboratorio.onrender.com'
).rstrip('/')

TIMEOUT = float(os.getenv('HTTP_TIMEOUT', '20'))


def consultar(base_url, ruta):
    if not base_url.startswith(('https://', 'http://')):
        return None, 'URL del microservicio no configurada', 503, None

    url = f'{base_url}{ruta}'

    try:
        respuesta = requests.get(
            url,
            timeout=TIMEOUT,
            headers={'Accept': 'application/json'}
        )
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado', 504, url
    except requests.exceptions.RequestException as e:
        return None, f'No se pudo conectar al microservicio: {str(e)}', 502, url

    if respuesta.status_code == 404:
        return None, 'Registro no encontrado', 404, url

    if not respuesta.ok:
        return None, f'El microservicio devolvió HTTP {respuesta.status_code}', 502, url

    try:
        return respuesta.json(), None, 200, url
    except ValueError:
        return None, 'El microservicio no devolvió JSON válido', 502, url


@app.get('/')
def inicio():
    return jsonify({
        'servicio': 'Orquestador Hospitalario Directo',
        'estado': 'activo',
        'ruta': '/atencion/<id>',
        'laboratorio_url': LABORATORIO_URL
    }), 200


@app.get('/health')
def health():
    return jsonify({'estado': 'activo'}), 200


@app.get('/atencion/<int:identificador>')
def atencion(identificador):
    if identificador < 1:
        return jsonify({
            'estado': 'ERROR',
            'mensaje': 'El ID debe ser positivo'
        }), 400

    # Consultar paciente
    paciente, error, codigo, url_paciente = consultar(
        PACIENTES_URL,
        f'/pacientes/{identificador}'
    )

    if error:
        return jsonify({
            'estado': 'ERROR',
            'servicio': 'pacientes',
            'mensaje': error,
            'url_consultada': url_paciente,
            'codigo_http': codigo
        }), codigo

    # Consultar orden de laboratorio
    laboratorio, error, codigo, url_laboratorio = consultar(
        LABORATORIO_URL,
        f'/ordenes/{identificador}'
    )

    if error:
        return jsonify({
            'estado': 'ERROR',
            'servicio': 'laboratorio',
            'mensaje': error,
            'url_consultada': url_laboratorio,
            'codigo_http': codigo
        }), codigo

    # Respuesta consolidada
    return jsonify({
        'estado': 'CONSULTA_COMPLETADA',
        'identificador_consultado': identificador,
        'pacientes': paciente,
        'laboratorio': laboratorio,
        'advertencia': (
            'Se consulta el mismo ID en ambos servicios; '
            'no se presume relación entre los registros.'
        )
    }), 200


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000'))
    )

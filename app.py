import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)
PACIENTES_URL = os.getenv('PACIENTES_URL', 'https://integrantes-hospital-pacientes-1.onrender.com').rstrip('/')
LABORATORIO_URL = os.getenv('LABORATORIO_URL', 'https://integrantes-hospital-laboratorio.onrender.com').rstrip('/')
TIMEOUT = float(os.getenv('HTTP_TIMEOUT', '20'))


def consultar(base_url, ruta):
    if not base_url.startswith(('https://', 'http://')):
        return None, 'URL del microservicio no configurada', 503
    try:
        r = requests.get(f'{base_url}{ruta}', timeout=TIMEOUT, headers={'Accept': 'application/json'})
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado', 504
    except requests.exceptions.RequestException:
        return None, 'No se pudo conectar al microservicio', 502
    if r.status_code == 404:
        return None, 'Registro no encontrado', 404
    if not r.ok:
        return None, f'El microservicio devolvió HTTP {r.status_code}', 502
    try:
        return r.json(), None, 200
    except ValueError:
        return None, 'El microservicio no devolvió JSON válido', 502


@app.get('/')
def inicio():
    return jsonify({'servicio': 'Orquestador Hospitalario Directo', 'ruta': '/atencion/<id>'})


@app.get('/atencion/<int:identificador>')
def atencion(identificador):
    if identificador < 1:
        return jsonify({'estado': 'ERROR', 'mensaje': 'El ID debe ser positivo'}), 400
    paciente, error, codigo = consultar(PACIENTES_URL, f'/pacientes/{identificador}')
    if error:
        return jsonify({'estado': 'ERROR', 'servicio': 'pacientes', 'mensaje': error}), codigo
    laboratorio, error, codigo = consultar(LABORATORIO_URL, f'/laboratorio/{identificador}')
    if error:
        return jsonify({'estado': 'ERROR', 'servicio': 'laboratorio', 'mensaje': error}), codigo
    return jsonify({
        'estado': 'CONSULTA_COMPLETADA',
        'identificador_consultado': identificador,
        'pacientes': paciente,
        'laboratorio': laboratorio,
        'advertencia': 'Se consulta el mismo ID en ambos servicios; no se presume relación entre los registros.'
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')))

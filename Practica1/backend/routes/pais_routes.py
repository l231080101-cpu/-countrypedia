from flask import Blueprint, jsonify
from services.pais_service import (
    get_country_from_cache_or_api,
    register_consulta,
    get_countries_by_region,
    get_populares
)

pais_bp = Blueprint('pais', __name__)


@pais_bp.route('/api/buscar/<name>')
def buscar_pais(name):
    try:
        pais = get_country_from_cache_or_api(name)
        if not pais:
            return jsonify({"error": "País no encontrado"}), 404

        register_consulta(pais['name']['common'])

        return jsonify([pais])

    except Exception:
        return jsonify({"error": "Error al buscar el país"}), 500


@pais_bp.route('/api/region/<region>')
def buscar_por_region(region):
    try:
        paises = get_countries_by_region(region)
        return jsonify(paises)
    except Exception:
        return jsonify({"error": "Error al obtener países de la región"}), 500


@pais_bp.route('/api/populares')
def populares_route():
    try:
        populares = get_populares()
        return jsonify(populares)
    except Exception:
        return jsonify({"error": "Error al obtener países populares"}), 500

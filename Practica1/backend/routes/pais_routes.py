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
        
    except Exception as e:
        print("ERROR REAL EN SERVIDOR:", str(e))
        return jsonify({"error": str(e)}), 500


@pais_bp.route('/api/region/<region>')
def buscar_por_region(region):
    """
    Buscar países por región
    ---
    tags:
      - Países
    parameters:
      - name: region
        in: path
        type: string
        required: true
        description: Región (ej. Americas, Europe, Asia, Africa, Oceania)
    responses:
      200:
        description: Lista de países de la región
    """
    try:
        paises = get_countries_by_region(region)
        return jsonify(paises)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pais_bp.route('/api/populares')
def populares_route():
    """
    Países más consultados
    ---
    tags:
      - Países
    responses:
      200:
        description: Lista de países populares
    """
    try:
        populares = get_populares()
        return jsonify(populares)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

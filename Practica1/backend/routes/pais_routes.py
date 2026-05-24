from flask import Blueprint, jsonify
from services.pais_service import (
    get_country_from_cache_or_api,
    register_consulta,
    get_countries_by_region,
    get_populares,
    get_all_countries_lightweight
)

pais_bp = Blueprint('pais', __name__)


@pais_bp.route('/api/buscar/<name>')
def buscar_pais(name):
    """Search for a country by name.
    ---
    tags:
      - Countries
    parameters:
      - in: path
        name: name
        type: string
        required: true
        description: Country name (common or official)
    responses:
      200:
        description: Country data
        schema:
          type: array
          items:
            type: object
      404:
        description: Country not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal error
        schema:
          type: object
          properties:
            error:
              type: string
    """
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
    """Get all countries in a region.
    ---
    tags:
      - Countries
    parameters:
      - in: path
        name: region
        type: string
        required: true
        description: Region name (e.g. Europe, Asia, Americas)
    responses:
      200:
        description: List of countries in the region
        schema:
          type: array
          items:
            type: object
      500:
        description: Internal error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        paises = get_countries_by_region(region)
        return jsonify(paises)
    except Exception:
        return jsonify({"error": "Error al obtener países de la región"}), 500


@pais_bp.route('/api/populares')
def populares_route():
    """Get most searched countries.
    ---
    tags:
      - Countries
    responses:
      200:
        description: List of popular countries with search count
        schema:
          type: array
          items:
            type: object
            properties:
              pais:
                type: string
              conteo:
                type: integer
              data:
                type: object
      500:
        description: Internal error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        populares = get_populares()
        return jsonify(populares)
    except Exception:
        return jsonify({"error": "Error al obtener países populares"}), 500


@pais_bp.route('/api/paises')
def listar_paises():
    """Get lightweight list of all countries.
    ---
    tags:
      - Countries
    responses:
      200:
        description: List of all countries with name, flags, currencies, region
        schema:
          type: array
          items:
            type: object
      500:
        description: Internal error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        paises = get_all_countries_lightweight()
        return jsonify(paises)
    except Exception:
        return jsonify({"error": "Error al obtener lista de países"}), 500

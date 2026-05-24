from flask import Blueprint, jsonify
from services.viaje_service import (
    get_exchange_rates,
    get_cambio,
    get_dummy_costos,
    get_travel_advisory,
    get_weather,
    get_news
)

viaje_bp = Blueprint('viaje', __name__)


@viaje_bp.route('/api/cambio/<moneda_codigo>')
def obtener_cambio(moneda_codigo):
    """
    Obtener tipo de cambio desde USD a la moneda especificada
    ---
    tags:
      - Monedas
    parameters:
      - name: moneda_codigo
        in: path
        type: string
        required: true
        description: Código de moneda (ej. MXN, EUR, JPY)
    responses:
      200:
        description: Tasa de cambio
    """
    cambio = get_cambio(moneda_codigo)
    if cambio:
        return jsonify(cambio)
    rates = get_exchange_rates()
    if not rates:
        return jsonify({"error": "Error en API de cambio"}), 500
    return jsonify({"error": "Moneda no soportada"}), 404


@viaje_bp.route('/api/costos/<pais>')
def obtener_costos(pais):
    """
    Obtener costo de vida simulado
    ---
    tags:
      - Utilidades
    parameters:
      - name: pais
        in: path
        type: string
        required: true
        description: Nombre del país
    responses:
      200:
        description: Datos de costos simulados
    """
    return jsonify(get_dummy_costos(pais))


@viaje_bp.route('/api/travel-advisory/<country_name>')
def travel_advisory(country_name):
    """
    Consejos de viaje para un país
    ---
    tags:
      - Viajes
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: Nombre del país
    responses:
      200:
        description: Datos de seguridad, visa, enchufes, etc.
    """
    return jsonify(get_travel_advisory(country_name))


@viaje_bp.route('/api/weather/<country_name>')
def get_weather_route(country_name):
    """
    Clima actual en la capital del país
    ---
    tags:
      - Clima
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: Nombre del país
    responses:
      200:
        description: Datos climáticos
    """
    weather = get_weather(country_name)
    if weather:
        return jsonify(weather)
    return jsonify({"error": "Clima no disponible: API key no configurada"}), 503


@viaje_bp.route('/api/noticias/<country_name>')
def noticias_route(country_name):
    """
    Noticias recientes sobre un país
    ---
    tags:
      - Noticias
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: Nombre del país
    responses:
      200:
        description: Lista de artículos de noticias
    """
    noticias = get_news(country_name)
    if noticias:
        return jsonify(noticias)
    return jsonify({"error": "Noticias no disponibles"}), 503

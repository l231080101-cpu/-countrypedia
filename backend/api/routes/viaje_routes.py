from flask import Blueprint, jsonify, request
from services.viaje_service import (
    get_exchange_rates,
    get_cambio,
    get_cost_of_living,
    get_travel_advisory,
    get_weather,
    get_news
)

viaje_bp = Blueprint('viaje', __name__)


@viaje_bp.route('/api/cambio/<moneda_codigo>')
def obtener_cambio(moneda_codigo):
    """Get exchange rate for a currency code."""
    cambio = get_cambio(moneda_codigo.upper())
    if cambio:
        return jsonify(cambio)
    rates = get_exchange_rates()
    if not rates:
        return jsonify({"error": "Error en API de cambio"}), 500
    return jsonify({"error": "Moneda no soportada"}), 404


@viaje_bp.route('/api/costo-vida/<country_name>')
def obtener_costo_vida(country_name):
    """Get real cost-of-living estimate for a country."""
    costos = get_cost_of_living(country_name)
    if costos:
        return jsonify(costos)
    return jsonify({"error": "Costo de vida no disponible"}), 503


@viaje_bp.route('/api/travel-advisory/<country_name>')
def travel_advisory(country_name):
    """Get travel advisory / safety information."""
    return jsonify(get_travel_advisory(country_name))


@viaje_bp.route('/api/weather/<country_name>')
def get_weather_route(country_name):
    """Get current weather for a country."""
    weather = get_weather(country_name)
    if weather:
        return jsonify(weather)
    return jsonify({"error": "Clima no disponible"}), 503


@viaje_bp.route('/api/noticias/<country_name>')
def noticias_route(country_name):
    """Get latest news about a country."""
    language = request.args.get('language', 'es')
    noticias = get_news(country_name, language)
    if noticias:
        return jsonify(noticias)
    return jsonify({"error": "Noticias no disponibles"}), 503

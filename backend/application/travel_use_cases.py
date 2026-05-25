import json
import time
from pathlib import Path
from infrastructure.external_apis.exchange_rate import get_rates as api_get_rates, get_rate_for_currency
from infrastructure.external_apis.rest_countries import get_country_by_name as api_get_country_by_name
from infrastructure.external_apis.openweather import get_weather as api_get_weather
from infrastructure.external_apis.news_api import get_news as api_get_news
from infrastructure.external_apis.world_bank import get_gdp_per_capita
from application.country_use_cases import (
    get_country_from_cache_or_api as _get_country,
    get_country_coordinates as _get_coords,
)


# Load travel data from JSON
DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'travel_data.json'
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    _travel_data = json.load(f)
REGION_DEFAULTS = _travel_data['REGION_DEFAULTS']
travel_advisory_data = _travel_data['travel_advisory_data']


cost_living_cache = {}


def get_exchange_rates():
    return api_get_rates()


def get_cambio(moneda_codigo):
    return get_rate_for_currency(moneda_codigo)


def get_cost_of_living(country_name):
    now = time.time()
    cache_key = country_name.lower()
    if cache_key in cost_living_cache and (now - cost_living_cache[cache_key]["timestamp"]) < 86400:
        return cost_living_cache[cache_key]["data"]

    region_cost_factors = {
        "Europe": 1.3, "North America": 1.6, "South America": 0.7,
        "Asia": 0.8, "Africa": 0.6, "Oceania": 1.4, "Antarctic": 1.0
    }

    try:
        pais_data = _get_country(country_name)
        if not pais_data:
            return None

        region = pais_data.get("region", "Americas")
        cca2 = pais_data.get("cca2", "").lower()
        factor = region_cost_factors.get(region, 1.0)

        if cca2:
            gdp = get_gdp_per_capita(cca2)
            if gdp:
                factor = max(0.3, min(3.0, gdp / 12000))

        reference = {"comida": 350, "transporte": 120, "alojamiento": 800, "entretenimiento": 200, "servicios": 150}
        costs_usd = {k: round(v * factor) for k, v in reference.items()}

        result = {"factor": round(factor, 2), "costs_usd": costs_usd, "region": region}
        cost_living_cache[cache_key] = {"data": result, "timestamp": now}
        return result

    except Exception as e:
        print(f"Error obteniendo costo de vida: {e}")
        return None


def get_travel_advisory(country_name):
    name_lower = country_name.lower()
    if name_lower in travel_advisory_data:
        data = travel_advisory_data[name_lower].copy()
        safety_emoji = {"green": "\U0001f7e2", "yellow": "\U0001f7e1", "red": "\U0001f534"}
        data["signal"] = safety_emoji.get(data["safety_level"], "\u26aa")
        return data

    region = None
    try:
        pais_data = _get_country(country_name)
        if pais_data and "region" in pais_data:
            region = pais_data["region"]
    except Exception as e:
        print(f"Error obteniendo región: {e}")

    if not region:
        region = "Americas"

    default = REGION_DEFAULTS.get(region, {
        "visa_required": "Consultar",
        "plug_type": "Consultar",
        "water_safe": "Consultar",
        "safety_level": "yellow",
        "best_time": "Consultar",
        "attractions": ["Investiga antes de viajar"],
        "details": "Revisa fuentes oficiales antes de tu viaje."
    }).copy()

    safety_emoji = {"green": "\U0001f7e2", "yellow": "\U0001f7e1", "red": "\U0001f534"}
    default["signal"] = safety_emoji.get(default["safety_level"], "\u26aa")
    return default


def get_weather(country_name):
    lat, lon = _get_coords(country_name)
    if lat is None or lon is None:
        return None
    return api_get_weather(country_name, lat, lon)


def get_news(country_name, language='es'):
    return api_get_news(country_name, language)

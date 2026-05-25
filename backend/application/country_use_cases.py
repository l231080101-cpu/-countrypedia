import json
import requests
from core.config import settings
from infrastructure.database.repositories.country_repository import (
    get_cache_by_name,
    upsert_cache,
    increment_consulta,
    get_cache_by_cca3,
    get_cache_count,
    insert_many_countries,
    get_all_names,
    get_populares as repo_get_populares,
)
from infrastructure.external_apis.rest_countries import (
    get_country_by_name as api_get_country_by_name,
    get_countries_by_region as api_get_countries_by_region,
    get_country_coordinates as api_get_country_coordinates,
    get_all_lightweight as api_get_all_lightweight,
)


def _apply_spanish_name(pais_data):
    nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
    if nombre_espanol:
        pais_data['name']['common'] = nombre_espanol


def get_country_from_cache_or_api(name):
    cache_data = get_cache_by_name(name)

    if cache_data:
        pais_data = json.loads(cache_data) if isinstance(cache_data, str) else cache_data
        _apply_spanish_name(pais_data)
        return pais_data

    try:
        pais_data = api_get_country_by_name(name)
        if pais_data is None:
            return None

        _apply_spanish_name(pais_data)

        nombre_registro = pais_data['name']['common'].lower() if pais_data.get('translations', {}).get('spa', {}).get('common') else name.lower()
        cca3 = pais_data.get('cca3')

        upsert_cache(nombre_registro, cca3, json.dumps(pais_data))
        return pais_data

    except Exception as e:
        raise e


def get_country_by_cca3(cca3):
    cache_data = get_cache_by_cca3(cca3)

    if cache_data:
        pais_data = json.loads(cache_data) if isinstance(cache_data, str) else cache_data
        _apply_spanish_name(pais_data)
        return pais_data

    return None


def get_all_countries_names():
    count = get_cache_count()
    if count < 200:
        try:
            response = requests.get(f"{settings.REST_COUNTRIES_API}/all?fields=name,flags,cca3", timeout=15)
            response.raise_for_status()
            all_countries = response.json()
            insert_many_countries(all_countries)
        except Exception as e:
            print(f"Error al cargar lista de países: {e}")
    return get_all_names()


def get_country_coordinates(country_name):
    try:
        pais_data = get_country_from_cache_or_api(country_name)
        if pais_data and "latlng" in pais_data and len(pais_data["latlng"]) >= 2:
            return pais_data["latlng"][0], pais_data["latlng"][1]
        return api_get_country_coordinates(country_name)
    except Exception as e:
        print(f"Error obteniendo coordenadas para {country_name}: {e}")
        return None, None


def get_countries_by_region(region):
    return api_get_countries_by_region(region)


def register_consulta(pais_nombre):
    increment_consulta(pais_nombre)


def get_populares(limit=10):
    return repo_get_populares(limit)


def get_all_countries_lightweight():
    return api_get_all_lightweight()

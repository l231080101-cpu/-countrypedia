import time
import requests
import json
from config.settings import REST_COUNTRIES_API
from repositories.pais_repository import (
    get_cache_by_name,
    upsert_cache,
    increment_consulta,
    get_cache_by_cca3,
    get_cache_count,
    insert_many_countries,
    get_all_names,
    get_populares as repo_get_populares
)


def get_country_from_cache_or_api(name):
    cache_data = get_cache_by_name(name)
    
    if cache_data:
        pais_data = json.loads(cache_data) if isinstance(cache_data, str) else cache_data
        nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
        if nombre_espanol:
            pais_data['name']['common'] = nombre_espanol
        return pais_data

    try:
        response = requests.get(f"{REST_COUNTRIES_API}/name/{name}", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        
        if data:
            pais_data = data[0]
            
            nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
            if nombre_espanol:
                pais_data['name']['common'] = nombre_espanol
            
            nombre_registro = nombre_espanol.lower() if nombre_espanol else name.lower()
            cca3 = pais_data.get('cca3')
            
            upsert_cache(nombre_registro, cca3, json.dumps(pais_data))
            return pais_data
        
        return None
        
    except Exception as e:
        raise e


def get_country_by_cca3(cca3):
    cache_data = get_cache_by_cca3(cca3)
    
    if cache_data:
        pais_data = json.loads(cache_data) if isinstance(cache_data, str) else cache_data
        nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
        if nombre_espanol:
            pais_data['name']['common'] = nombre_espanol
        return pais_data
    
    return None


def get_all_countries_names():
    count = get_cache_count()
    if count < 200:
        try:
            response = requests.get(f"{REST_COUNTRIES_API}/all?fields=name,flags,cca3", timeout=15)
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
        else:
            response = requests.get(f"{REST_COUNTRIES_API}/name/{country_name}?fields=latlng", timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and "latlng" in data[0] and len(data[0]["latlng"]) >= 2:
                return data[0]["latlng"][0], data[0]["latlng"][1]
            return None, None
    except Exception as e:
        print(f"Error obteniendo coordenadas para {country_name}: {e}")
        return None, None


def get_countries_by_region(region):
    response = requests.get(f"{REST_COUNTRIES_API}/region/{region}", timeout=10)
    response.raise_for_status()
    paises = response.json()
    return paises[:12]


def register_consulta(pais_nombre):
    increment_consulta(pais_nombre)


def get_populares(limit=10):
    return repo_get_populares(limit)


_all_countries_list_cache = {"data": None, "timestamp": 0}


def get_all_countries_lightweight():
    global _all_countries_list_cache
    now = time.time()
    if _all_countries_list_cache["data"] and (now - _all_countries_list_cache["timestamp"]) < 3600:
        return _all_countries_list_cache["data"]

    try:
        response = requests.get(
            f"{REST_COUNTRIES_API}/all?fields=name,flags,currencies,region,cca3",
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        data.sort(key=lambda c: c.get("name", {}).get("common", ""))
        _all_countries_list_cache = {"data": data, "timestamp": now}
        return data
    except Exception as e:
        if _all_countries_list_cache["data"]:
            return _all_countries_list_cache["data"]
        raise e

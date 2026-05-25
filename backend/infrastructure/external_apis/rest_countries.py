import time
import requests
from core.config import settings


_all_countries_list_cache = {"data": None, "timestamp": 0}


def get_country_by_name(name):
    url = f"{settings.REST_COUNTRIES_API}/name/{name}"
    response = requests.get(url, timeout=10)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


def get_countries_by_region(region):
    response = requests.get(f"{settings.REST_COUNTRIES_API}/region/{region}", timeout=10)
    response.raise_for_status()
    return response.json()[:12]


def get_all_lightweight():
    global _all_countries_list_cache
    now = time.time()
    if _all_countries_list_cache["data"] and (now - _all_countries_list_cache["timestamp"]) < 3600:
        return _all_countries_list_cache["data"]

    response = requests.get(
        f"{settings.REST_COUNTRIES_API}/all?fields=name,flags,currencies,region,cca3",
        timeout=15
    )
    response.raise_for_status()
    data = response.json()
    data.sort(key=lambda c: c.get("name", {}).get("common", ""))
    _all_countries_list_cache = {"data": data, "timestamp": now}
    return data


def get_country_coordinates(country_name):
    try:
        response = requests.get(
            f"{settings.REST_COUNTRIES_API}/name/{country_name}?fields=latlng",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data and "latlng" in data[0] and len(data[0]["latlng"]) >= 2:
            return data[0]["latlng"][0], data[0]["latlng"][1]
        return None, None
    except Exception as e:
        print(f"Error obteniendo coordenadas para {country_name}: {e}")
        return None, None

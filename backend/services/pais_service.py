from application.country_use_cases import (
    get_country_from_cache_or_api as _get_country_from_cache_or_api,
    get_country_by_cca3 as _get_country_by_cca3,
    get_all_countries_names as _get_all_countries_names,
    get_country_coordinates as _get_country_coordinates,
    get_countries_by_region as _get_countries_by_region,
    register_consulta as _register_consulta,
    get_populares as _get_populares,
    get_all_countries_lightweight as _get_all_countries_lightweight,
)


def get_country_from_cache_or_api(name):
    return _get_country_from_cache_or_api(name)


def get_country_by_cca3(cca3):
    return _get_country_by_cca3(cca3)


def get_all_countries_names():
    return _get_all_countries_names()


def get_country_coordinates(country_name):
    return _get_country_coordinates(country_name)


def get_countries_by_region(region):
    return _get_countries_by_region(region)


def register_consulta(pais_nombre):
    _register_consulta(pais_nombre)


def get_populares(limit=10):
    return _get_populares(limit)


def get_all_countries_lightweight():
    return _get_all_countries_lightweight()
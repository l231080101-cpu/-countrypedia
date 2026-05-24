import time
import requests
from config.settings import EXCHANGE_API, OPENWEATHER_API_KEY, WEATHER_CACHE_TTL, CACHE_EXCHANGE_TTL, NEWS_API_KEY, NEWS_CACHE_TTL
from data.travel_data import REGION_DEFAULTS, travel_advisory_data
from services.pais_service import get_country_from_cache_or_api, get_country_coordinates


exchange_cache = {"data": None, "timestamp": 0}
weather_cache = {}
news_cache = {}
cost_living_cache = {}


def get_exchange_rates():
    global exchange_cache
    now = time.time()
    if exchange_cache["data"] is None or (now - exchange_cache["timestamp"]) > CACHE_EXCHANGE_TTL:
        try:
            response = requests.get("https://api.frankfurter.app/latest?from=USD", timeout=15)
            if response.status_code == 200:
                data = response.json()
                exchange_cache["data"] = data["rates"]
                exchange_cache["timestamp"] = now
                print("Tasas de cambio actualizadas (Frankfurter)")
            else:
                res2 = requests.get(EXCHANGE_API, timeout=10)
                if res2.status_code == 200:
                    data2 = res2.json()
                    if data2.get("result") == "success":
                        exchange_cache["data"] = data2["rates"]
                        exchange_cache["timestamp"] = now
                        print("Tasas de cambio actualizadas (ExchangeRate-API)")
        except Exception as e:
            print(f"Error obteniendo tasas: {e}")
    return exchange_cache["data"]


def get_cambio(moneda_codigo):
    rates = get_exchange_rates()
    if rates:
        tasa = rates.get(moneda_codigo.upper())
        if tasa:
            return {"tasa": tasa, "base": "USD"}
        return None
    return None


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
        pais_data = get_country_from_cache_or_api(country_name)
        if not pais_data:
            return None

        region = pais_data.get("region", "Americas")
        cca2 = pais_data.get("cca2", "").lower()
        factor = region_cost_factors.get(region, 1.0)

        if cca2:
            try:
                wb_url = f"https://api.worldbank.org/v2/country/{cca2}/indicator/NY.GDP.PCAP.CD?format=json&per_page=1"
                wb_resp = requests.get(wb_url, timeout=10)
                if wb_resp.status_code == 200:
                    wb_data = wb_resp.json()
                    if len(wb_data) > 1 and wb_data[1] and wb_data[1][0].get("value"):
                        gdp = wb_data[1][0]["value"]
                        factor = max(0.3, min(3.0, gdp / 12000))
            except Exception:
                pass

        reference = {"comida": 350, "transporte": 120, "alojamiento": 800, "entretenimiento": 200, "servicios": 150}
        costs_usd = {k: round(v * factor) for k, v in reference.items()}

        result = {"factor": round(factor, 2), "costs_usd": costs_usd, "region": region}
        cost_living_cache[cache_key] = {"data": result, "timestamp": now}
        return result

    except Exception as e:
        print(f"Error obteniendo costo de vida: {e}")
        return None
cost_living_cache = {}


def get_exchange_rates():
    global exchange_cache
    now = time.time()
    if exchange_cache["data"] is None or (now - exchange_cache["timestamp"]) > CACHE_EXCHANGE_TTL:
        try:
            response = requests.get("https://api.frankfurter.app/latest?from=USD", timeout=15)
            if response.status_code == 200:
                data = response.json()
                exchange_cache["data"] = data["rates"]
                exchange_cache["timestamp"] = now
                print("Tasas de cambio actualizadas (Frankfurter)")
            else:
                res2 = requests.get(EXCHANGE_API, timeout=10)
                if res2.status_code == 200:
                    data2 = res2.json()
                    if data2.get("result") == "success":
                        exchange_cache["data"] = data2["rates"]
                        exchange_cache["timestamp"] = now
                        print("Tasas de cambio actualizadas (ExchangeRate-API)")
        except Exception as e:
            print(f"Error obteniendo tasas: {e}")
    return exchange_cache["data"]


def get_cambio(moneda_codigo):
    rates = get_exchange_rates()
    if rates:
        tasa = rates.get(moneda_codigo.upper())
        if tasa:
            return {"tasa": tasa, "base": "USD"}
        return None
    return None


def get_travel_advisory(country_name):
    name_lower = country_name.lower()
    if name_lower in travel_advisory_data:
        data = travel_advisory_data[name_lower].copy()
        safety_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
        data["signal"] = safety_emoji.get(data["safety_level"], "⚪")
        return data
    
    region = None
    try:
        pais_data = get_country_from_cache_or_api(country_name)
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
    
    safety_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    default["signal"] = safety_emoji.get(default["safety_level"], "⚪")
    return default


def get_weather(country_name):
    if not OPENWEATHER_API_KEY:
        return None
    
    now = time.time()
    cache_key = country_name.lower()
    if cache_key in weather_cache and (now - weather_cache[cache_key]["timestamp"]) < WEATHER_CACHE_TTL:
        return weather_cache[cache_key]["data"]
    
    lat, lon = get_country_coordinates(country_name)
    if lat is None or lon is None:
        return None
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        weather_info = {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "wind_speed": data["wind"]["speed"],
            "city": data.get("name", country_name)
        }
        
        weather_cache[cache_key] = {"data": weather_info, "timestamp": now}
        return weather_info
    except Exception as e:
        print(f"Error obteniendo clima: {e}")
        return None


def get_news(country_name, language='es'):
    if not NEWS_API_KEY:
        return None

    now = time.time()
    cache_key = f"{country_name.lower()}:{language}"
    if cache_key in news_cache and (now - news_cache[cache_key]["timestamp"]) < NEWS_CACHE_TTL:
        return news_cache[cache_key]["data"]

    try:
        url = f"https://newsapi.org/v2/everything?q={country_name}&language={language}&pageSize=5&sortBy=relevancy&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            return None

        articles = []
        for art in data.get("articles", []):
            articles.append({
                "title": art.get("title"),
                "description": art.get("description"),
                "url": art.get("url"),
                "source": art.get("source", {}).get("name"),
                "publishedAt": art.get("publishedAt"),
                "urlToImage": art.get("urlToImage")
            })

        result = {"articles": articles, "totalResults": data.get("totalResults", 0)}
        news_cache[cache_key] = {"data": result, "timestamp": now}
        return result
    except Exception as e:
        print(f"Error obteniendo noticias: {e}")
        return None

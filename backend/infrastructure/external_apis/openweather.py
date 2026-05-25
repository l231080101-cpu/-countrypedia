import time
import requests
from core.config import settings


_cache = {}


def get_weather(country_name, lat, lon):
    if not settings.OPENWEATHER_API_KEY:
        return None

    now = time.time()
    cache_key = country_name.lower()
    if cache_key in _cache and (now - _cache[cache_key]["timestamp"]) < settings.WEATHER_CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={settings.OPENWEATHER_API_KEY}&units=metric&lang=es"
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

        _cache[cache_key] = {"data": weather_info, "timestamp": now}
        return weather_info
    except Exception as e:
        print(f"Error obteniendo clima: {e}")
        return None

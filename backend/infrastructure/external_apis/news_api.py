import time
import requests
from core.config import settings


_cache = {}


def get_news(country_name, language='es'):
    if not settings.NEWS_API_KEY:
        return None

    now = time.time()
    cache_key = f"{country_name.lower()}:{language}"
    if cache_key in _cache and (now - _cache[cache_key]["timestamp"]) < settings.NEWS_CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        url = f"https://newsapi.org/v2/everything?q={country_name}&language={language}&pageSize=5&sortBy=relevancy&apiKey={settings.NEWS_API_KEY}"
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
        _cache[cache_key] = {"data": result, "timestamp": now}
        return result
    except Exception as e:
        print(f"Error obteniendo noticias: {e}")
        return None

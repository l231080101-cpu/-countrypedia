import time
import requests
from core.config import settings


_cache = {"data": None, "timestamp": 0}


def get_rates():
    global _cache
    now = time.time()
    if _cache["data"] is None or (now - _cache["timestamp"]) > settings.CACHE_EXCHANGE_TTL:
        try:
            response = requests.get("https://api.frankfurter.app/latest?from=USD", timeout=15)
            if response.status_code == 200:
                data = response.json()
                _cache["data"] = data["rates"]
                _cache["timestamp"] = now
                print("Tasas de cambio actualizadas (Frankfurter)")
            else:
                res2 = requests.get(settings.EXCHANGE_API, timeout=10)
                if res2.status_code == 200:
                    data2 = res2.json()
                    if data2.get("result") == "success":
                        _cache["data"] = data2["rates"]
                        _cache["timestamp"] = now
                        print("Tasas de cambio actualizadas (ExchangeRate-API)")
        except Exception as e:
            print(f"Error obteniendo tasas: {e}")
    return _cache["data"]


def get_rate_for_currency(currency_code):
    rates = get_rates()
    if rates:
        tasa = rates.get(currency_code.upper())
        if tasa:
            return {"tasa": tasa, "base": "USD"}
    return None

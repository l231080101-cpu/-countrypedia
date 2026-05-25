import requests


def get_gdp_per_capita(cca2: str):
    if not cca2:
        return None
    try:
        url = f"https://api.worldbank.org/v2/country/{cca2}/indicator/NY.GDP.PCAP.CD?format=json&per_page=1"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1 and data[1] and data[1][0].get("value"):
                return data[1][0]["value"]
    except Exception:
        pass
    return None

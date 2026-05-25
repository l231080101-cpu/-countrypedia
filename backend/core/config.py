import os
import re
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    PORT: int = int(os.getenv('PORT', 5000))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    API_KEY_PROTECTION: str = os.getenv('API_KEY')
    ORIGEN_PERMITIDO: str = os.getenv('ORIGEN_PERMITIDO', 'http://localhost:5000,http://localhost:8080,http://localhost')
    DATABASE_URL: str = os.getenv('DATABASE_URL') or 'geocultural.db'
    REST_COUNTRIES_API: str = os.getenv('REST_COUNTRIES_API', 'https://restcountries.com/v3.1')
    EXCHANGE_API: str = os.getenv('EXCHANGE_API', 'https://api.exchangerate-api.com/v4/latest/USD')
    OPENWEATHER_API_KEY: str = os.getenv('OPENWEATHER_API_KEY') or ''
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))
    CACHE_EXCHANGE_TTL: int = int(os.getenv('CACHE_EXCHANGE_TTL', 86400))
    WEATHER_CACHE_TTL: int = 1800
    NEWS_API_KEY: str = os.getenv('NEWS_API_KEY') or ''
    NEWS_CACHE_TTL: int = 3600
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self):
        if len(self.SECRET_KEY) < 32:
            print(f"ADVERTENCIA: SECRET_KEY tiene solo {len(self.SECRET_KEY)} bytes. Se recomienda >=32 bytes para HMAC-SHA256.")


settings = Settings()
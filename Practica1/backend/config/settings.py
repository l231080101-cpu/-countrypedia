import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_123')
API_KEY_PROTECTION = os.getenv('API_KEY', 'mi_super_clave_secreta')
ORIGEN_PERMITIDO = os.getenv('ORIGEN_PERMITIDO', 'http://localhost:5000,http://localhost:8080,http://localhost')
DATABASE_URL = os.getenv('DATABASE_URL') or 'geocultural.db'
REST_COUNTRIES_API = os.getenv('REST_COUNTRIES_API', 'https://restcountries.com/v3.1')
EXCHANGE_API = os.getenv('EXCHANGE_API', 'https://api.exchangerate-api.com/v4/latest/USD')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))
CACHE_EXCHANGE_TTL = int(os.getenv('CACHE_EXCHANGE_TTL', 86400))
WEATHER_CACHE_TTL = 1800
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWS_CACHE_TTL = 3600

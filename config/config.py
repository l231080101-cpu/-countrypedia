# Permite usar una base de datos remota (Postgres) o local (SQLite)
DATABASE_URL = os.getenv('DATABASE_URL', '')
import os

PORT = int(os.getenv('PORT', 55000))
HOST = os.getenv('HOST', '0.0.0.0')
SECRET_KEY = os.getenv('SECRET_KEY', 'clave_por_defecto_solo_para_desarrollo')
ORIGEN_PERMITIDO = os.getenv('ORIGEN_PERMITIDO', 'http://localhost:5000,http://localhost:8080,http://localhost')

REST_COUNTRIES_API = os.getenv('REST_COUNTRIES_API', 'https://restcountries.com/v3.1')
EXCHANGE_API = os.getenv('EXCHANGE_API', 'https://api.exchangerate-api.com/v4/latest/USD')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')

DB_NAME = os.getenv('DB_NAME', 'geocultural.db')
CACHE_EXCHANGE_TTL = int(os.getenv('CACHE_EXCHANGE_TTL', 86400))

JWT_EXPIRATION_DELTA_DAYS = int(os.getenv('JWT_EXPIRATION_DELTA_DAYS', 7))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))

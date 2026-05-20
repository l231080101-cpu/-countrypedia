import os
import json
import time
import uuid
import random
import jwt
import sqlite3
import psycopg2
import requests
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, jsonify, request, g
from psycopg2.extras import RealDictCursor
import psycopg2

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import settings
weather_cache = {}
exchange_cache = {"data": None, "timestamp": 0}

def get_current_user_id():
    return g.user_id

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != settings.API_KEY:
            return jsonify({"error": "API Key inválida o faltante"}), 401
        return f(*args, **kwargs)
    return decorated

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            is_postgres = not hasattr(conn, 'interrupt')
            query = "SELECT id FROM usuarios WHERE id = %s" if is_postgres else "SELECT id FROM usuarios WHERE id = ?"
            
            cursor.execute(query, (current_user_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not user:
                return jsonify({'message': 'User not found'}), 401
            
            g.user_id = current_user_id
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY
# ==========================================
# 5. RUTAS DE LA API
# ==========================================

@app.route('/')
def index():
    return jsonify({"message": "CountryPedia API - Documentación en /docs"})

@app.route('/api/buscar/<name>')
def buscar_pais(name):
    conn = None
    try:
        pais = get_country_from_cache_or_api(name)
        if not pais:
            return jsonify({"error": "País no encontrado"}), 404

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Usamos EXCLUDED para evitar cualquier ambigüedad en Postgres
        cursor.execute('''
            INSERT INTO consultas_frecuentes (pais_nombre, conteo, ultima_consulta)
            VALUES (%s, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (pais_nombre) 
            DO UPDATE SET
                conteo = consultas_frecuentes.conteo + 1,
                ultima_consulta = EXCLUDED.ultima_consulta
        ''', (pais['name']['common'],))
        
        conn.commit()
        cursor.close()
        
        return jsonify([pais])
        
    except Exception as e:
        if conn:
            conn.rollback() # Si truena el SQL, limpiamos la transacción limpia
        logger.error("ERROR REAL EN SERVIDOR:", str(e))
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            conn.close() # Nos aseguramos de soltar la conexión sí o sí


@app.route('/api/region/<region>')
def buscar_por_region(region):
    """
    Buscar países por región
    ---
    tags:
      - Países
    parameters:
      - name: region
        in: path
        type: string
        required: true
        description: Región (ej. Americas, Europe, Asia, Africa, Oceania)
    responses:
      200:
        description: Lista de países de la región
        schema:
          type: array
          items:
            $ref: '#/definitions/country_schema'
      500:
        description: Error interno
    """
    try:
        response = requests.get(f"{settings.REST_COUNTRIES_API}/region/{region}", timeout=10)
        response.raise_for_status()
        paises = response.json()
        return jsonify(paises[:12])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cambio/<moneda_codigo>')
def obtener_cambio(moneda_codigo):
    """
    Obtener tipo de cambio desde USD a la moneda especificada
    ---
    tags:
      - Monedas
    parameters:
      - name: moneda_codigo
        in: path
        type: string
        required: true
        description: Código de moneda (ej. MXN, EUR, JPY)
    responses:
      200:
        description: Tasa de cambio
        schema:
          type: object
          properties:
            tasa:
              type: number
            base:
              type: string
      404:
        description: Moneda no soportada
      500:
        description: Error en API de cambio
    """
    rates = get_exchange_rates()
    if rates:
        tasa = rates.get(moneda_codigo.upper())
        if tasa:
            return jsonify({"tasa": tasa, "base": "USD"})
        return jsonify({"error": "Moneda no soportada"}), 404
    return jsonify({"error": "Error en API de cambio"}), 500

@app.route('/api/costos/<pais>')
def obtener_costos(pais):
    """
    Obtener costo de vida simulado (dummy)
    ---
    tags:
      - Utilidades
    parameters:
      - name: pais
        in: path
        type: string
        required: true
        description: Nombre del país (solo para semilla aleatoria)
    responses:
      200:
        description: Datos de costos simulados
        schema:
          type: object
          properties:
            comida:
              type: integer
            hospedaje:
              type: integer
            transporte:
              type: integer
            ocio:
              type: integer
            seguridad:
              type: integer
    """
    random.seed(pais)
    datos = {
        "comida": random.randint(3, 10),
        "hospedaje": random.randint(2, 10),
        "transporte": random.randint(4, 10),
        "ocio": random.randint(3, 10),
        "seguridad": random.randint(5, 10)
    }
    return jsonify(datos)

@app.route('/api/travel-advisory/<country_name>')
def travel_advisory(country_name):
    """
    Consejos de viaje para un país (visa, enchufes, seguridad, etc.)
    ---
    tags:
      - Viajes
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: Nombre del país (ej. mexico)
    responses:
      200:
        description: Datos de seguridad, visa, enchufes, etc.
        schema:
          type: object
          properties:
            visa_required:
              type: boolean
            plug_type:
              type: string
            water_safe:
              type: boolean
            safety_level:
              type: string
            best_time:
              type: string
            attractions:
              type: array
              items:
                type: string
            details:
              type: string
            signal:
              type: string
    """
    name_lower = country_name.lower()
    if name_lower in travel_advisory_data:
        data = travel_advisory_data[name_lower].copy()
        safety_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
        data["signal"] = safety_emoji.get(data["safety_level"], "⚪")
        return jsonify(data)
    region = None
    try:
        pais_data = get_country_from_cache_or_api(country_name)
        if pais_data and "region" in pais_data:
            region = pais_data["region"]
    except Exception as e:
        logger.warning(f"Error obteniendo región: {e}")
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
    return jsonify(default)

@app.route('/api/weather/<country_name>')
def get_weather(country_name):
    """
    Clima actual en la capital del país
    ---
    tags:
      - Clima
    parameters:
      - name: country_name
        in: path
        type: string
        required: true
        description: Nombre del país
    responses:
      200:
        description: Datos climáticos (temperatura, humedad, etc.)
        schema:
          type: object
          properties:
            temp:
              type: number
            feels_like:
              type: number
            humidity:
              type: integer
            description:
              type: string
            wind_speed:
              type: number
            city:
              type: string
      503:
        description: API key no configurada
      404:
        description: Coordenadas no encontradas
    """
    if not settings.OPENWEATHER_API_KEY:
        return jsonify({"error": "Clima no disponible: API key no configurada"}), 503
    now = time.time()
    cache_key = country_name.lower()
    if cache_key in weather_cache and (now - weather_cache[cache_key]["timestamp"]) < settings.WEATHER_CACHE_TTL:
        return jsonify(weather_cache[cache_key]["data"])
    lat, lon = get_country_coordinates(country_name)
    if lat is None or lon is None:
        return jsonify({"error": "No se pudieron obtener coordenadas para el país"}), 404
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
        weather_cache[cache_key] = {"data": weather_info, "timestamp": now}
        return jsonify(weather_info)
    except Exception as e:
        logger.error(f"Error obteniendo clima: {e}")
        return jsonify({"error": "Error al obtener el clima"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({"error": "Faltan campos"}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Cambiamos ? por %s y agregamos RETURNING id para Postgres
        cursor.execute(
            "INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, password_hash)
        )
        
        # 2. Obtenemos el ID generado (esto reemplaza a lastrowid)
        user_id = cursor.fetchone()[0]
        
        # Confirmamos la transacción
        conn.commit()

        # El resto de tu código sigue igual, pero usando el user_id que ya tenemos
        access_token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        refresh_token = str(uuid.uuid4())
        expires_refresh = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        cursor.execute(
            "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, refresh_token, expires_refresh)
        )
        conn.commit()
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": user_id, "username": username, "email": email}
        }), 201
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return jsonify({"error": "El nombre de usuario ya existe"}), 400
        elif "email" in str(e):
            return jsonify({"error": "El email ya está registrado"}), 400
        else:
            return jsonify({"error": "Error al registrar usuario"}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Faltan campos"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash FROM usuarios WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 401
    user_id, username_db, email, password_hash = user
    if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
        conn.close()
        return jsonify({"error": "Contraseña incorrecta"}), 401
    access_token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    refresh_token = str(uuid.uuid4())
    expires_refresh = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    cursor.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user_id, refresh_token, expires_refresh)
    )
    conn.commit()
    conn.close()
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user_id, "username": username_db, "email": email}
    })

@app.route('/api/refresh', methods=['POST'])
def refresh():
    data = request.json
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "Refresh token required"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, expires_at, revoked FROM refresh_tokens WHERE token = %s",
        (refresh_token,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Invalid refresh token"}), 401
    user_id, expires_at, revoked = row
    if revoked:
        conn.close()
        return jsonify({"error": "Token revoked"}), 401
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if datetime.now(timezone.utc) > expires_at:
        conn.close()
        return jsonify({"error": "Refresh token expired"}), 401
    new_access_token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    conn.close()
    return jsonify({"access_token": new_access_token})

@app.route('/api/logout', methods=['POST'])
@token_required
def logout():
    user_id = get_current_user_id()
    data = request.json
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "refresh_token required"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token = %s AND user_id = %s",
        (refresh_token, user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Logged out successfully"})

@app.route('/api/me', methods=['GET'])
@token_required
def me():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({"id": user[0], "username": user[1], "email": user[2]})
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/favoritos', methods=['GET', 'POST'])
@require_api_key
@token_required
def gestionar_favoritos():
    user_id = get_current_user_id()
    conn = None
    
    if request.method == 'POST':
        try:
            data = request.json
            cca3 = data.get('cca3')
            if not cca3:
                return jsonify({"error": "Se requiere cca3 del país"}), 400
            
            cca3 = cca3.upper()
            pais = get_country_by_cca3(cca3)
            if not pais:
                return jsonify({"error": f"No se encontró el país con código {cca3}"}), 404
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # CORRECCIÓN EN POSTGRESQL: Reemplazamos "INSERT OR REPLACE" por "ON CONFLICT"
            # Nota: Esto asume que tienes una llave primaria compuesta o restricción única en (usuario_id, pais_cca3)
            cursor.execute('''
                INSERT INTO favoritos_usuarios (usuario_id, pais_cca3) 
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, pais_cca3) DO NOTHING
            ''', (user_id, cca3))
            
            conn.commit()
            cursor.close()
            return jsonify({"status": "success", "message": f"País {pais['name']['common']} guardado en favoritos"}), 201
            
        except Exception as e:
            if conn:
                conn.rollback()  # 🌟 ¡Esto evita que se trabe la base de datos!
            logger.error("ERROR EN POST FAVORITOS:", str(e))
            return jsonify({"error": str(e)}), 500
        finally:
            if conn:
                conn.close()

    # MENTODO GET
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # En Supabase es buena idea verificar si tu columna se llama 'fecha_agregado' o si se creó automáticamente
        cursor.execute(
            "SELECT pais_cca3 FROM favoritos_usuarios WHERE usuario_id = %s ORDER BY fecha_agregado DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        
        favoritos = []
        for row in rows:
            cca3 = row[0]
            pais = get_country_by_cca3(cca3)
            if pais:
                favoritos.append(pais)
                
        return jsonify(favoritos)
        
    except Exception as e:
        logger.error("ERROR EN GET FAVORITOS:", str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
@app.route('/api/favoritos/<cca3>', methods=['DELETE'])
@token_required
def eliminar_favorito(cca3):
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favoritos_usuarios WHERE usuario_id = %s AND pais_cca3 = %s",
        (user_id, cca3.upper())
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404
def get_db_connection():
    db_url = settings.DATABASE_URL
    logger.info("Conectando con la base de datos...")
    
    if db_url and db_url.startswith('postgresql'):
        return psycopg2.connect(db_url, prepare_threshold=0)
    else:
        conn = sqlite3.connect('geocultural.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    is_postgres = not hasattr(conn, 'interrupt')
    
    pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    bool_default = "FALSE" if is_postgres else "0"
    
    sql_commands = [
        f"""
        CREATE TABLE IF NOT EXISTS consultas_frecuentes (
            id {pk_type},
            pais_nombre TEXT UNIQUE,
            conteo INTEGER DEFAULT 1,
            ultima_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS usuarios (
            id {pk_type},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS favoritos_usuarios (
            id {pk_type},
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            pais_cca3 TEXT NOT NULL,
            fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, pais_cca3)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS paises_cache (
            id {pk_type},
            nombre_comun TEXT UNIQUE NOT NULL,
            cca3 TEXT,
            data TEXT NOT NULL,
            ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_paises_cache_cca3 ON paises_cache(cca3)
        """,
        f"""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id {pk_type},
            user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT {bool_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id {pk_type},
            jti TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    for sql in sql_commands:
        try:
            cursor.execute(sql)
        except Exception as e:
            logger.warning(f"Nota al procesar estructura: {e}")
            
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Base de datos verificada e inicializada correctamente")

def get_exchange_rates():
    global exchange_cache
    now = time.time()
    if exchange_cache["data"] is None or (now - exchange_cache["timestamp"]) > 86400:
        try:
            response = requests.get("https://api.frankfurter.app/latest?from=USD", timeout=15)
            if response.status_code == 200:
                data = response.json()
                exchange_cache["data"] = data["rates"]
                exchange_cache["timestamp"] = now
                logger.info("Tasas de cambio actualizadas (Frankfurter)")
            else:
                res2 = requests.get(settings.EXCHANGE_API, timeout=10)
                if res2.status_code == 200:
                    data2 = res2.json()
                    if data2.get("result") == "success":
                        exchange_cache["data"] = data2["rates"]
                        exchange_cache["timestamp"] = now
                        logger.info("Tasas de cambio actualizadas (ExchangeRate-API)")
        except Exception as e:
            logger.warning(f"Error al obtener tasas de cambio: {e}")
    return exchange_cache["data"]

def get_country_from_cache_or_api(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Buscamos en el caché
    cursor.execute("SELECT data FROM paises_cache WHERE nombre_comun = %s", (name.lower(),))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("UPDATE paises_cache SET ultima_actualizacion = CURRENT_TIMESTAMP WHERE nombre_comun = %s", (name.lower(),))
        conn.commit()
        cursor.close()
        conn.close()
        
        pais_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        
        # 🌟 COMPROBACIÓN EXTRA AL LEER DEL CACHÉ: 
        # Aseguramos que siempre viaje traducido, incluso si se guardó en inglés viejo
        nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
        if nombre_espanol:
            pais_data['name']['common'] = nombre_espanol
            
        return pais_data

    try:
        # 2. Si no está en caché, lo pedimos a la API externa
        response = requests.get(f"{settings.REST_COUNTRIES_API}/name/{name}", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            pais_data = data[0]
            
            # 🌟 INTERCEPTAMOS E INYECTAMOS EL NOMBRE EN ESPAÑOL ANTES DE GUARDAR
            nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
            if nombre_espanol:
                pais_data['name']['common'] = nombre_espanol  # Forzamos español para el Frontend
            
            nombre_registro = nombre_espanol.lower() if nombre_espanol else name.lower()

            cursor.execute('''
                INSERT INTO paises_cache (nombre_comun, data, ultima_actualizacion) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (nombre_comun) 
                DO UPDATE SET 
                    data = EXCLUDED.data,
                    ultima_actualizacion = CURRENT_TIMESTAMP
            ''', (nombre_registro, json.dumps(pais_data)))
            
            conn.commit()
            cursor.close()
            conn.close()
            return pais_data
            
        cursor.close()
        conn.close()
        return None
        
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        raise e
    
def get_country_by_cca3(cca3):
    """Obtiene datos completos de un país a partir de su código cca3."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cca3 = cca3.upper()
    
    try:
        cursor.execute("SELECT data FROM paises_cache WHERE data->>'cca3' = %s", (cca3,))
        row = cursor.fetchone()
        
        if row:
            cursor.close()
            conn.close()
            pais_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            
            # 🌟 ASEGURAMOS TRADUCCIÓN AL LEER DESDE FAVORITOS
            nombre_espanol = pais_data.get('translations', {}).get('spa', {}).get('common')
            if nombre_espanol:
                pais_data['name']['common'] = nombre_espanol
                
            return pais_data
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error obteniendo país por cca3 {cca3}: {e}")
    finally:
        if conn:
            try:
                cursor.close()
                conn.close()
            except:
                pass
                
    return None
def get_all_countries_names():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM paises_cache")
    count = cursor.fetchone()[0]
    if count < 200:
        try:
            response = requests.get(f"{settings.REST_COUNTRIES_API}/all?fields=name,flags,cca3", timeout=15)
            response.raise_for_status()
            all_countries = response.json()
            for country in all_countries:
                nombre = country['name']['common']
                cursor.execute("INSERT OR REPLACE INTO paises_cache (nombre_comun, data) VALUES (%s, %s)",
                               (nombre, json.dumps(country)))
            conn.commit()
        except Exception as e:
            logger.error(f"Error al cargar lista de países: {e}")
    cursor.execute("SELECT nombre_comun FROM paises_cache ORDER BY nombre_comun")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_country_coordinates(country_name):
    try:
        pais_data = get_country_from_cache_or_api(country_name)
        if pais_data and "latlng" in pais_data and len(pais_data["latlng"]) >= 2:
            return pais_data["latlng"][0], pais_data["latlng"][1]
        else:
            response = requests.get(f"{settings.REST_COUNTRIES_API}/name/{country_name}?fields=latlng", timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and "latlng" in data[0] and len(data[0]["latlng"]) >= 2:
                return data[0]["latlng"][0], data[0]["latlng"][1]
            return None, None
    except Exception as e:
        logger.error(f"Error obteniendo coordenadas para {country_name}: {e}")
        return None, None

REGION_DEFAULTS = {
    "Europe": {
        "visa_required": False,
        "plug_type": "C/F",
        "water_safe": True,
        "safety_level": "green",
        "best_time": "Primavera (abril-junio) u otoño (septiembre-octubre).",
        "attractions": ["Patrimonio histórico", "Gastronomía local", "Arquitectura emblemática"],
        "details": "Destino popular con buena infraestructura turística."
    },
    "Asia": {
        "visa_required": True,
        "plug_type": "A/C/I",
        "water_safe": False,
        "safety_level": "yellow",
        "best_time": "Noviembre a febrero (temporada seca).",
        "attractions": ["Templos milenarios", "Mercados flotantes", "Naturaleza exótica"],
        "details": "Verifica requisitos de visa. El agua embotellada es esencial."
    },
    "Americas": {
        "visa_required": False,
        "plug_type": "A/B",
        "water_safe": False,
        "safety_level": "yellow",
        "best_time": "Diciembre a abril (temporada seca).",
        "attractions": ["Ruinas arqueológicas", "Playas paradisíacas", "Naturaleza exuberante"],
        "details": "Investiga la seguridad de tu destino específico."
    },
    "Africa": {
        "visa_required": True,
        "plug_type": "C/D/G",
        "water_safe": False,
        "safety_level": "yellow",
        "best_time": "Mayo a octubre (temporada seca).",
        "attractions": ["Safaris", "Playas vírgenes", "Cultura ancestral"],
        "details": "Consulta las vacunas requeridas."
    },
    "Oceania": {
        "visa_required": True,
        "plug_type": "I",
        "water_safe": True,
        "safety_level": "green",
        "best_time": "Septiembre a noviembre o marzo a mayo.",
        "attractions": ["Parques nacionales", "Arrecifes de coral", "Playas impresionantes"],
        "details": "País generalmente seguro, respeta la naturaleza local."
    }
}

travel_advisory_data = {
    # --- América ---
    "mexico": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Chichén Itzá", "Teotihuacán", "Cenotes", "Palacio de Bellas Artes"], "details": "💧 Agua no potable. Precaución en zonas turísticas."},
    "united states": {"visa_required": True, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Primavera y otoño", "attractions": ["Gran Cañón", "Times Square", "Disney World", "Golden Gate"], "details": "Visa requerida. País seguro."},
    "canada": {"visa_required": True, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Verano o invierno", "attractions": ["Niagara", "Banff", "CN Tower", "Quebec"], "details": "Visa eTA. Seguro."},
    "brazil": {"visa_required": True, "plug_type": "N", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a marzo", "attractions": ["Cristo Redentor", "Pan de Azúcar", "Iguazú", "Amazonas"], "details": "Visa requerida. Agua no potable."},
    "argentina": {"visa_required": False, "plug_type": "C/I", "water_safe": False, "safety_level": "yellow", "best_time": "Octubre a abril", "attractions": ["Iguazú", "Perito Moreno", "Cerro de los Siete Colores"], "details": "Sin visa. Agua no potable."},
    "colombia": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a marzo", "attractions": ["Ciudad Perdida", "Catedral de Sal", "Tayrona"], "details": "Sin visa. Precaución en ciudades."},
    "peru": {"visa_required": False, "plug_type": "A/B/C", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a septiembre", "attractions": ["Machu Picchu", "Nazca", "Titicaca", "Colca"], "details": "Sin visa. Agua no potable."},
    "chile": {"visa_required": False, "plug_type": "C/L", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a marzo", "attractions": ["Torres del Paine", "Isla de Pascua", "Valle de la Luna"], "details": "Sin visa. Seguro."},
    "costa rica": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["Volcán Arenal", "Monteverde", "Manuel Antonio"], "details": "Sin visa. Agua potable."},
    "cuba": {"visa_required": True, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["La Habana Vieja", "Varadero", "Valle de Viñales"], "details": "Visa requerida (tarjeta de turista)."},
    "dominican republic": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a abril", "attractions": ["Punta Cana", "Santo Domingo", "Puerto Plata"], "details": "Sin visa. Agua no potable."},
    "jamaica": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a mediados de diciembre", "attractions": ["Montego Bay", "Negril", "Kingston"], "details": "Sin visa. Precaución."},
    "bahamas": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["Atlantis", "Exumas", "Nassau"], "details": "Sin visa."},
    "puerto rico": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["El Yunque", "Viejo San Juan", "Culebra"], "details": "Territorio EE.UU., sin visa para mexicanos."},
    "guatemala": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Tikal", "Antigua", "Lago Atitlán"], "details": "Sin visa. Precaución."},
    "panama": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a abril", "attractions": ["Canal de Panamá", "Bocas del Toro", "San Blas"], "details": "Sin visa."},
    "uruguay": {"visa_required": False, "plug_type": "C/I", "water_safe": True, "safety_level": "green", "best_time": "Octubre a marzo", "attractions": ["Montevideo", "Punta del Este", "Colonia"], "details": "Sin visa. Seguro."},
    "ecuador": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Junio a septiembre", "attractions": ["Galápagos", "Quito", "Baños", "Cuenca"], "details": "Sin visa."},
    "bolivia": {"visa_required": True, "plug_type": "A/C", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a octubre", "attractions": ["Salar de Uyuni", "La Paz", "Lago Titicaca"], "details": "Visa requerida."},
    "paraguay": {"visa_required": False, "plug_type": "C", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a septiembre", "attractions": ["Asunción", "Jesuítas", "Itaipú"], "details": "Sin visa."},
    "venezuela": {"visa_required": True, "plug_type": "A/B", "water_safe": False, "safety_level": "red", "best_time": "Diciembre a abril", "attractions": ["Salto Ángel", "Los Roques", "Mérida"], "details": "🔴 Visa requerida. Situación compleja. No viajar."},
    "honduras": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a abril", "attractions": ["Copán", "Roatán", "Tegucigalpa"], "details": "Sin visa. Precaución."},
    "el salvador": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Santa Ana", "El Tunco", "San Salvador"], "details": "Sin visa."},
    "nicaragua": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Granada", "Ometepe", "León"], "details": "Sin visa."},
    "belize": {"visa_required": False, "plug_type": "A/B/G", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Gran Agujero Azul", "Cuevas Actun Tunichil Muknal", "San Ignacio"], "details": "Sin visa. Agua no potable."},
    "guyana": {"visa_required": True, "plug_type": "A/B/D/G", "water_safe": False, "safety_level": "yellow", "best_time": "Febrero a abril", "attractions": ["Cataratas Kaieteur", "Georgetown", "Selva amazónica"], "details": "Visa requerida."},
    "suriname": {"visa_required": True, "plug_type": "A/B/C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Agosto a noviembre", "attractions": ["Central Suriname Nature Reserve", "Paramaribo"], "details": "Visa requerida."},
    "french guiana": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Julio a diciembre", "attractions": ["Centro Espacial Guayanés", "Isla del Diablo", "Kourou"], "details": "Territorio francés, visa Schengen."},
    "trinidad and tobago": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "green", "best_time": "Enero a mayo", "attractions": ["Carnaval", "Maracas Bay", "Pitch Lake"], "details": "Sin visa."},
    "barbados": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a junio", "attractions": ["Playa Crane", "Barbados Wildlife Reserve", "Bridgetown"], "details": "Sin visa."},
    "bahamas": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["Atlantis", "Exumas", "Nassau"], "details": "Sin visa."},
    "antigua and barbuda": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["English Harbour", "Playa Dickenson", "St. John's"], "details": "Sin visa."},
    "st. lucia": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Diciembre a mayo", "attractions": ["Pitones", "Volcán Qualibou", "Castries"], "details": "Sin visa."},
    "grenada": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Enero a abril", "attractions": ["Cascadas Grand Etang", "Fort George", "St. George's"], "details": "Sin visa."},
    "st. vincent and the grenadines": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Diciembre a mayo", "attractions": ["Bahía de Tobago", "Kingstown", "Parque Nacional La Soufrière"], "details": "Sin visa."},
    # --- Europa ---
    "france": {"visa_required": False, "plug_type": "C/E", "water_safe": True, "safety_level": "green", "best_time": "Abril-junio, septiembre-octubre", "attractions": ["Torre Eiffel", "Louvre", "Versalles", "Mont Saint-Michel"], "details": "Schengen. Cuidado con carteristas."},
    "spain": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, septiembre-noviembre", "attractions": ["Sagrada Familia", "Alhambra", "Parque del Retiro", "Mezquita de Córdoba"], "details": "Schengen. Muy seguro."},
    "italy": {"visa_required": False, "plug_type": "C/F/L", "water_safe": True, "safety_level": "green", "best_time": "Abril-junio, septiembre-octubre", "attractions": ["Coliseo", "Venecia", "Florencia", "Costa Amalfi"], "details": "Schengen. Precaución con carteras."},
    "united kingdom": {"visa_required": True, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Mayo a septiembre", "attractions": ["Big Ben", "Torre de Londres", "Stonehenge", "Lago Ness"], "details": "Visa requerida."},
    "germany": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo a septiembre", "attractions": ["Puerta de Brandeburgo", "Neuschwanstein", "Catedral de Colonia"], "details": "Schengen. Muy seguro."},
    "turkey": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Abril-mayo, septiembre-octubre", "attractions": ["Santa Sofía", "Capadocia", "Éfeso", "Palacio Topkapi"], "details": "Visa electrónica. Agua no potable."},
    "greece": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-junio, septiembre", "attractions": ["Acrópolis", "Santorini", "Miconos", "Creta"], "details": "Schengen."},
    "austria": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Abril-mayo, septiembre-octubre", "attractions": ["Schönbrunn", "Salzburgo", "Hallstatt"], "details": "Schengen."},
    "portugal": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, septiembre-octubre", "attractions": ["Torre de Belém", "Lisboa", "Oporto", "Algarve"], "details": "Schengen."},
    "netherlands": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Abril-mayo (tulipanes), septiembre", "attractions": ["Casa de Ana Frank", "Museo Van Gogh", "Ámsterdam"], "details": "Schengen."},
    "switzerland": {"visa_required": False, "plug_type": "C/J", "water_safe": True, "safety_level": "green", "best_time": "Junio-septiembre, diciembre-marzo", "attractions": ["Alpes", "Interlaken", "Ginebra", "Zúrich"], "details": "Schengen."},
    "belgium": {"visa_required": False, "plug_type": "C/E", "water_safe": True, "safety_level": "green", "best_time": "Abril-octubre", "attractions": ["Atomium", "Gran Plaza", "Brujas"], "details": "Schengen."},
    "sweden": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-agosto", "attractions": ["Estocolmo", "ABBA Museum", "Icehotel"], "details": "Schengen."},
    "denmark": {"visa_required": False, "plug_type": "C/E/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Copenhague", "Tivoli", "Little Mermaid"], "details": "Schengen."},
    "norway": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Fiordos", "Tromsø", "Bergen"], "details": "Schengen."},
    "ireland": {"visa_required": False, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Acantilados de Moher", "Dublín", "Anillo de Kerry"], "details": "Sin visa para mexicanos."},
    "croatia": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-septiembre", "attractions": ["Dubrovnik", "Plitvice", "Split"], "details": "Schengen."},
    "poland": {"visa_required": False, "plug_type": "C/E", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Cracovia", "Auschwitz", "Varsovia"], "details": "Schengen."},
    "hungary": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Abril-octubre", "attractions": ["Parlamento de Budapest", "Bastión de los Pescadores", "Balaton"], "details": "Schengen."},
    "czech republic": {"visa_required": False, "plug_type": "C/E", "water_safe": True, "safety_level": "green", "best_time": "Abril-octubre", "attractions": ["Praga", "Castillo de Praga", "Puente Carlos"], "details": "Schengen."},
    "russia": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "No recomendado", "attractions": [], "details": "🔴 Guerra activa contra Ucrania. Riesgo extremo para viajeros. No viajar."},
    "finland": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Helsinki", "Laponia", "Aurora Boreal"], "details": "Schengen."},
    "iceland": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Círculo Dorado", "Laguna Azul", "Reykjavik"], "details": "Schengen."},
    "slovakia": {"visa_required": False, "plug_type": "C/E", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Castillo de Bratislava", "Altos Tatras", "Košice"], "details": "Schengen."},
    "slovenia": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Lago Bled", "Ljubljana", "Cuevas de Postojna"], "details": "Schengen."},
    "estonia": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Tallin", "Isla Saaremaa", "Parque Nacional Lahemaa"], "details": "Schengen."},
    "latvia": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Riga", "Costa del Báltico", "Jūrmala"], "details": "Schengen."},
    "lithuania": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Junio-agosto", "attractions": ["Vilna", "Castillo de Trakai", "Curonian Spit"], "details": "Schengen."},
    "belarus": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "No recomendado", "attractions": [], "details": "🔴 Régimen autoritario, riesgo para viajeros. No viajar."},
    "moldova": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-septiembre", "attractions": ["Chisináu", "Bodegas Cricova", "Monasterio Saharna"], "details": "Sin visa (90 días). Precaución."},
    "romania": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Castillo de Bran", "Bucarest", "Delta del Danubio"], "details": "Sin visa (90 días)."},
    "bulgaria": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Playa de Sunny Beach", "Sofía", "Monasterio de Rila"], "details": "Sin visa."},
    "serbia": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Abril-octubre", "attractions": ["Belgrado", "Novi Sad", "Parque Nacional Tara"], "details": "Sin visa. Precaución."},
    "bosnia and herzegovina": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-octubre", "attractions": ["Mostar", "Sarajevo", "Puente Mehmed Paša Sokolović"], "details": "Sin visa."},
    "montenegro": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-octubre", "attractions": ["Kotor", "Budva", "Parque Nacional Durmitor"], "details": "Sin visa."},
    "albania": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-septiembre", "attractions": ["Tirana", "Berat", "Riviera Albanesa"], "details": "Sin visa."},
    "north macedonia": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-septiembre", "attractions": ["Skopie", "Lago Ohrid", "Matka Canyon"], "details": "Sin visa."},
    "kosovo": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo-septiembre", "attractions": ["Pristina", "Prizren", "Monumento a la Madre Teresa"], "details": "Sin visa."},
    "cyprus": {"visa_required": False, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, septiembre-octubre", "attractions": ["Nicosia", "Ayia Napa", "Pafos"], "details": "Sin visa."},
    "malta": {"visa_required": False, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Abril-octubre", "attractions": ["La Valeta", "La Ventana Azul (antigua)", "Mdina"], "details": "Schengen."},
    "luxembourg": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Mayo-septiembre", "attractions": ["Luxemburgo ciudad", "Castillo de Vianden", "Valle del Mosela"], "details": "Schengen."},
    "monaco": {"visa_required": False, "plug_type": "C/E/F", "water_safe": True, "safety_level": "green", "best_time": "Todo el año", "attractions": ["Casino de Montecarlo", "Palacio Principesco", "Puerto Hércules"], "details": "Sin visa."},
    "andorra": {"visa_required": False, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Invierno para esquí, verano para montaña", "attractions": ["Andorra la Vieja", "Estación de esquí Grandvalira", "Valle de Ordino"], "details": "Sin visa."},
    "san marino": {"visa_required": False, "plug_type": "C/F/L", "water_safe": True, "safety_level": "green", "best_time": "Todo el año", "attractions": ["Centro histórico", "Castillo de Guaita", "Palacio Público"], "details": "Sin visa."},
    "vatican city": {"visa_required": False, "plug_type": "C/F/L", "water_safe": True, "safety_level": "green", "best_time": "Todo el año", "attractions": ["Basílica de San Pedro", "Museos Vaticanos", "Capilla Sixtina"], "details": "Sin visa."},
    # --- Asia ---
    "japan": {"visa_required": False, "plug_type": "A/B", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, octubre-noviembre", "attractions": ["Monte Fuji", "Kinkaku-ji", "Shibuya", "Himeji"], "details": "Sin visa 90 días. Muy seguro."},
    "china": {"visa_required": True, "plug_type": "A/C/I", "water_safe": False, "safety_level": "yellow", "best_time": "Abril-mayo, septiembre-octubre", "attractions": ["Gran Muralla", "Ciudad Prohibida", "Guerreros Terracota"], "details": "Visa requerida. Agua no potable."},
    "thailand": {"visa_required": False, "plug_type": "A/B/C", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a febrero", "attractions": ["Bangkok", "Phuket", "Chiang Mai", "Ayutthaya"], "details": "Sin visa 30-60 días. Agua no potable."},
    "india": {"visa_required": True, "plug_type": "C/D/M", "water_safe": False, "safety_level": "red", "best_time": "Octubre a marzo", "attractions": ["Taj Mahal", "Jaipur", "Varanasi", "Goa"], "details": "🔴 Visa electrónica. Agua no potable. Precaución extrema."},
    "vietnam": {"visa_required": True, "plug_type": "A/B/C", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a abril", "attractions": ["Bahía de Halong", "Hanoi", "Ho Chi Minh", "Hoi An"], "details": "Visa electrónica."},
    "malaysia": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Diciembre a febrero", "attractions": ["Petronas", "Penang", "Langkawi", "Cameron Highlands"], "details": "Sin visa. Agua no potable."},
    "south korea": {"visa_required": True, "plug_type": "C/F", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, septiembre-noviembre", "attractions": ["Seúl", "Busán", "Jeju", "Gyeongbokgung"], "details": "Visa requerida (K-ETA). Muy seguro."},
    "indonesia": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a octubre", "attractions": ["Bali", "Borobudur", "Yakarta", "Komodo"], "details": "Visa a la llegada."},
    "singapore": {"visa_required": False, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Todo el año", "attractions": ["Marina Bay", "Sentosa", "Gardens by the Bay"], "details": "Sin visa. País muy seguro."},
    "philippines": {"visa_required": False, "plug_type": "A/B/C", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a mayo", "attractions": ["Palawan", "Boracay", "Manila", "Tubbataha"], "details": "Sin visa 30 días."},
    "nepal": {"visa_required": True, "plug_type": "C/D/M", "water_safe": False, "safety_level": "yellow", "best_time": "Octubre a diciembre, marzo a mayo", "attractions": ["Monte Everest", "Katmandú", "Pokhara", "Lumbini"], "details": "Visa a la llegada."},
    "israel": {"visa_required": False, "plug_type": "C/H", "water_safe": True, "safety_level": "red", "best_time": "No recomendado", "attractions": [], "details": "🔴 Conflicto activo en Gaza y Cisjordania. Situación de guerra. No viajar."},
    "qatar": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Noviembre a marzo", "attractions": ["Doha", "Museo Islámico", "Souq Waqif"], "details": "Sin visa. País seguro."},
    "uae": {"visa_required": False, "plug_type": "G", "water_safe": False, "safety_level": "green", "best_time": "Noviembre a marzo", "attractions": ["Burj Khalifa", "Dubai Mall", "Sheikh Zayed Mosque"], "details": "Sin visa. País seguro."},
    "sri lanka": {"visa_required": True, "plug_type": "D/G", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a marzo", "attractions": ["Sigiriya", "Kandy", "Galle", "Elefantes"], "details": "Visa electrónica."},
    "cambodia": {"visa_required": True, "plug_type": "A/C/G", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a marzo", "attractions": ["Angkor Wat", "Phnom Penh", "Sihanoukville"], "details": "Visa a la llegada."},
    "mongolia": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Junio a agosto", "attractions": ["Ubate", "Desierto de Gobi", "Lago Khövsgöl"], "details": "Visa requerida."},
    "myanmar": {"visa_required": True, "plug_type": "C/D/F", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Inestabilidad política, violencia, pobreza extrema. No viajar."},
    "afghanistan": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Situación de guerra. Extremadamente peligroso."},
    "syria": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Conflicto armado. No viajar."},
    "yemen": {"visa_required": True, "plug_type": "A/C/G", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Guerra civil. No viajar."},
    "ukraine": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "No recomendado", "attractions": [], "details": "🔴 Guerra activa. Peligro extremo. Sigue indicaciones de tu embajada."},
    "pakistan": {"visa_required": True, "plug_type": "C/D/M", "water_safe": False, "safety_level": "red", "best_time": "Octubre a marzo", "attractions": ["Karachi", "Lahore", "Islamabad", "Valles del Norte"], "details": "🔴 Visa requerida. Riesgo de terrorismo."},
    "bangladesh": {"visa_required": True, "plug_type": "A/C/D/G", "water_safe": False, "safety_level": "red", "best_time": "Noviembre a febrero", "attractions": ["Dhaka", "Sundarbans", "Cox's Bazar"], "details": "🔴 Visa requerida. Pobreza extrema."},
    "kazakhstan": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a septiembre", "attractions": ["Almaty", "Nur-Sultán", "Lago Balkhash"], "details": "Sin visa 30 días."},
    "uzbekistan": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a junio, septiembre a octubre", "attractions": ["Samarcanda", "Bujará", "Taskent"], "details": "Sin visa."},
    "tajikistan": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a septiembre", "attractions": ["Dushanbé", "Pamir Highway", "Lago Iskanderkul"], "details": "Visa electrónica."},
    "kyrgyzstan": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Junio a septiembre", "attractions": ["Biskek", "Lago Issyk-Kul", "Montañas Tian Shan"], "details": "Sin visa."},
    "turkmenistan": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "Primavera y otoño", "attractions": ["Asjabad", "Cráter de Darvaza", "Ruinas de Merv"], "details": "🔴 Visa requerida. Régimen autoritario."},
    "azerbaijan": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a junio, septiembre a octubre", "attractions": ["Bakú", "Gobustán", "Montañas del Cáucaso"], "details": "Visa electrónica."},
    "georgia": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a octubre", "attractions": ["Tiflis", "Kazbegi", "Valles del vino", "Batúmi"], "details": "Sin visa."},
    "armenia": {"visa_required": False, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a octubre", "attractions": ["Ereván", "Monasterio de Geghard", "Lago Seván"], "details": "Sin visa."},
    # --- África ---
    "egypt": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "yellow", "best_time": "Octubre a abril", "attractions": ["Pirámides de Guiza", "Luxor", "Valle de los Reyes", "Mar Rojo"], "details": "Visa requerida. Agua no potable. Precaución en zonas turísticas."},
    "morocco": {"visa_required": False, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Marzo a mayo, septiembre a octubre", "attractions": ["Marrakech", "Sáhara", "Fez", "Casablanca"], "details": "Sin visa. Agua no potable."},
    "south africa": {"visa_required": False, "plug_type": "M/N", "water_safe": True, "safety_level": "yellow", "best_time": "Mayo a septiembre", "attractions": ["Ciudad del Cabo", "Parque Kruger", "Jardín Botánico Kirstenbosch", "Robben Island"], "details": "Sin visa (90 días). Precaución en ciudades."},
    "tunisia": {"visa_required": False, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Marzo a mayo, septiembre a octubre", "attractions": ["Túnez", "Cartago", "Sidi Bou Said", "Desierto del Sahara"], "details": "Sin visa."},
    "senegal": {"visa_required": False, "plug_type": "C/D/E/K", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a junio", "attractions": ["Dakar", "Isla de Gorée", "Lago Rosa"], "details": "Sin visa."},
    "kenya": {"visa_required": True, "plug_type": "G", "water_safe": False, "safety_level": "yellow", "best_time": "Julio a octubre", "attractions": ["Masái Mara", "Nairobi", "Monte Kenia", "Mombasa"], "details": "Visa electrónica."},
    "tanzania": {"visa_required": True, "plug_type": "D/G", "water_safe": False, "safety_level": "yellow", "best_time": "Junio a octubre", "attractions": ["Kilimanjaro", "Serengueti", "Zanzíbar", "Ngorongoro"], "details": "Visa requerida."},
    "ghana": {"visa_required": True, "plug_type": "D/G", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a marzo", "attractions": ["Acra", "Castillo de Cape Coast", "Parque Nacional Kakum"], "details": "Visa requerida."},
    "ivory coast": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Noviembre a marzo", "attractions": ["Yamusukro", "Abiyán", "Parque Nacional Taï"], "details": "Visa requerida."},
    "nigeria": {"visa_required": True, "plug_type": "D/G", "water_safe": False, "safety_level": "red", "best_time": "Diciembre a febrero", "attractions": ["Lagos", "Abuya", "Parque Nacional Yankari"], "details": "🔴 Visa requerida. Riesgo de secuestros."},
    "ethiopia": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "Evitar regiones de conflicto", "attractions": [], "details": "🔴 Conflicto en Tigray y otras zonas. Pobreza extrema."},
    "sudan": {"visa_required": True, "plug_type": "C/D", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Conflicto armado. No viajar."},
    "south sudan": {"visa_required": True, "plug_type": "C/D", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Hambruna, conflicto, condiciones sanitarias críticas."},
    "somalia": {"visa_required": True, "plug_type": "C", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Riesgo extremo de seguridad, pobreza, ataques terroristas."},
    "central african republic": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Conflicto civil, desplazados, falta de atención médica."},
    "burundi": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "Evitar", "attractions": [], "details": "🔴 Pobreza extrema, inestabilidad, brotes de enfermedades."},
    "niger": {"visa_required": True, "plug_type": "C/D/E", "water_safe": False, "safety_level": "red", "best_time": "No recomendable", "attractions": [], "details": "🔴 Inseguridad alimentaria, terrorismo, condiciones climáticas extremas."},
    "chad": {"visa_required": True, "plug_type": "C/D/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Pobreza masiva, conflictos intercomunitarios, malaria endémica."},
    "liberia": {"visa_required": True, "plug_type": "A/B", "water_safe": False, "safety_level": "red", "best_time": "Precaución extrema", "attractions": [], "details": "🔴 Postguerra, desempleo, sistema de salud deficiente."},
    "zimbabwe": {"visa_required": True, "plug_type": "D/G", "water_safe": False, "safety_level": "red", "best_time": "No recomendado", "attractions": [], "details": "🔴 Crisis económica, pobreza extrema, escasez de medicinas."},
    "congo": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Conflicto armado, desplazamiento masivo, enfermedades (ébola, malaria)."},
    "democratic republic of the congo": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Guerra civil, inestabilidad, brotes de enfermedades."},
    "burkina faso": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Violencia yihadista, secuestros, desplazados."},
    "mali": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Conflicto armado, extremismo, riesgo de atentados."},
    "mozambique": {"visa_required": True, "plug_type": "C/F/M", "water_safe": False, "safety_level": "red", "best_time": "Evitar norte del país", "attractions": [], "details": "🔴 Insurgencia en Cabo Delgado, violencia, pobreza."},
    "madagascar": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a octubre", "attractions": ["Avenue of Baobabs", "Parque Nacional Isalo", "Antananarivo"], "details": "Visa a la llegada."},
    "mauritius": {"visa_required": False, "plug_type": "C/G", "water_safe": True, "safety_level": "green", "best_time": "Mayo a diciembre", "attractions": ["Playa Flic en Flac", "Port Louis", "Parque Nacional Black River Gorges"], "details": "Sin visa."},
    "seychelles": {"visa_required": False, "plug_type": "G", "water_safe": True, "safety_level": "green", "best_time": "Abril a mayo, octubre a noviembre", "attractions": ["Mahé", "Praslin", "La Digue"], "details": "Sin visa."},
    "namibia": {"visa_required": False, "plug_type": "D/M", "water_safe": False, "safety_level": "green", "best_time": "Mayo a octubre", "attractions": ["Desierto de Namib", "Sossusvlei", "Parque Nacional Etosha"], "details": "Sin visa."},
    "botswana": {"visa_required": False, "plug_type": "D/G/M", "water_safe": False, "safety_level": "green", "best_time": "Mayo a octubre", "attractions": ["Delta del Okavango", "Chobe", "Gaborone"], "details": "Sin visa."},
    "zambia": {"visa_required": True, "plug_type": "C/D/G", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a octubre", "attractions": ["Cataratas Victoria", "Parque Nacional South Luangwa", "Lusaka"], "details": "Visa electrónica."},
    "malawi": {"visa_required": True, "plug_type": "G", "water_safe": False, "safety_level": "yellow", "best_time": "Mayo a octubre", "attractions": ["Lago Malawi", "Monte Mulanje", "Lilongwe"], "details": "Visa requerida."},
    "rwanda": {"visa_required": True, "plug_type": "C/J", "water_safe": False, "safety_level": "green", "best_time": "Junio a septiembre", "attractions": ["Gorilas de montaña", "Kigali", "Lago Kivu"], "details": "Visa electrónica."},
    "uganda": {"visa_required": True, "plug_type": "G", "water_safe": False, "safety_level": "yellow", "best_time": "Diciembre a febrero", "attractions": ["Parque Nacional de las Montañas Rwenzori", "Lago Victoria", "Kampala"], "details": "Visa electrónica."},
    "angola": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "Mayo a septiembre", "attractions": ["Luanda", "Parque Nacional Kissama", "Cascadas de Kalandula"], "details": "🔴 Visa requerida. Pobreza."},
    "cameroon": {"visa_required": True, "plug_type": "C/E", "water_safe": False, "safety_level": "red", "best_time": "Noviembre a febrero", "attractions": ["Yaundé", "Monte Camerún", "Parque Nacional Waza"], "details": "🔴 Riesgo de secuestros."},
    "algeria": {"visa_required": True, "plug_type": "C/F", "water_safe": False, "safety_level": "red", "best_time": "Marzo a mayo, septiembre a octubre", "attractions": ["Argel", "Tassili n'Ajjer", "Roma en África"], "details": "🔴 Visa requerida. Riesgo terrorista."},
    "libya": {"visa_required": True, "plug_type": "C/E/L", "water_safe": False, "safety_level": "red", "best_time": "No viajar", "attractions": [], "details": "🔴 Guerra civil. No viajar."},
    # --- Oceanía ---
    "australia": {"visa_required": True, "plug_type": "I", "water_safe": True, "safety_level": "green", "best_time": "Marzo-mayo, septiembre-noviembre", "attractions": ["Ópera Sídney", "Gran Barrera", "Uluru", "Great Ocean Road"], "details": "Visa electrónica."},
    "new zealand": {"visa_required": True, "plug_type": "I", "water_safe": True, "safety_level": "green", "best_time": "Septiembre-noviembre, marzo-mayo", "attractions": ["Fiordland", "Rotorua", "Queenstown", "Hobbiton"], "details": "Visa electrónica."},
    "fiji": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Mayo a octubre", "attractions": ["Nadi", "Denarau", "Mamanuca", "Suva"], "details": "Sin visa."},
    "papua new guinea": {"visa_required": True, "plug_type": "I", "water_safe": False, "safety_level": "red", "best_time": "Mayo a octubre", "attractions": ["Monte Hagen", "Cultura tribal", "Buceo"], "details": "🔴 Visa requerida. Seguridad baja, violencia tribal."},
    "samoa": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Mayo a octubre", "attractions": ["Playas", "Cascadas", "Apia"], "details": "Sin visa."},
    "tonga": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Mayo a octubre", "attractions": ["Nuku'alofa", "Cuevas de Anahulu", "Ballenas jorobadas"], "details": "Sin visa."},
    "vanuatu": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Abril a octubre", "attractions": ["Port Vila", "Volcán Monte Yasur", "Buceo"], "details": "Sin visa."},
    "solomon islands": {"visa_required": True, "plug_type": "I", "water_safe": False, "safety_level": "yellow", "best_time": "Abril a septiembre", "attractions": ["Honiara", "Islas de la Luna de Miel", "Buceo en la Segunda Guerra Mundial"], "details": "Visa requerida."},
    "micronesia": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "green", "best_time": "Noviembre a abril", "attractions": ["Islas Chuuk", "Palikir", "Buceo"], "details": "Sin visa."},
    "palau": {"visa_required": False, "plug_type": "A/B", "water_safe": False, "safety_level": "green", "best_time": "Noviembre a abril", "attractions": ["Lago de las Medusas", "Koror", "Rock Islands"], "details": "Sin visa."},
    "marshall islands": {"visa_required": True, "plug_type": "A/B", "water_safe": False, "safety_level": "green", "best_time": "Diciembre a abril", "attractions": ["Majuro", "Arrecifes", "Atolón Bikini"], "details": "Visa requerida."},
    "kiribati": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Abril a octubre", "attractions": ["Tarawa", "Isla Navidad", "Pesca"], "details": "Sin visa."},
    "tuvalu": {"visa_required": False, "plug_type": "I", "water_safe": False, "safety_level": "green", "best_time": "Marzo a octubre", "attractions": ["Funafuti", "Playas", "Cultura polinesia"], "details": "Sin visa."},
    "nauru": {"visa_required": True, "plug_type": "I", "water_safe": False, "safety_level": "yellow", "best_time": "Todo el año", "attractions": ["Nauru", "Fosfatos", "Arrecifes"], "details": "Visa requerida."},
}
# ==========================================
# 4. INICIALIZACIÓN
# ==========================================

logger.info("Iniciando aplicación...")
logger.info(f"DATABASE_URL configurada: {'Sí' if os.getenv('DATABASE_URL') else 'No'}")
logger.info(f"SECRET_KEY length: {len(os.getenv('SECRET_KEY', ''))}")

try:
    init_db()
    logger.info("Base de datos inicializada correctamente")
except Exception as e:
    logger.error(f"Error al inicializar DB: {e}", exc_info=True)
    raise

if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.PORT)
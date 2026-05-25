import os
import sqlite3
import datetime
from core.config import settings


_db_initialized = False
_use_postgres = False
_pool = None
_sqlite_fallback_path = None


sqlite3.register_adapter(datetime.datetime, lambda val: val.isoformat())


def _initialize_db():
    global _db_initialized, _use_postgres, _pool
    if _db_initialized:
        return

    _db_initialized = True

    if settings.DATABASE_URL and settings.DATABASE_URL.startswith('postgresql'):
        try:
            import psycopg2
            from psycopg2 import pool

            conn_url = settings.DATABASE_URL
            if 'sslmode=' not in conn_url:
                if '?' in conn_url:
                    conn_url += "&sslmode=require"
                else:
                    conn_url += "?sslmode=require"

            _pool = pool.ThreadedConnectionPool(1, 2, conn_url)
            conn = _pool.getconn()
            conn.close()
            _pool.putconn(conn)
            _use_postgres = True
            print("Conexion exitosa a PostgreSQL/Supabase (pool activo)")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo conectar a PostgreSQL ({e}). Usando SQLite como fallback.")
            _use_postgres = False
            _sqlite_fallback_path = "/tmp/geocultural.db"
    else:
        _use_postgres = False


_initialize_db()


def is_postgres():
    return _use_postgres


def get_db_connection():
    if _use_postgres and _pool is not None:
        return _pool.getconn()
    db_path = _sqlite_fallback_path or settings.DATABASE_URL
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def close_db_connection(conn):
    if _use_postgres and _pool is not None:
        _pool.putconn(conn)
    else:
        conn.close()


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()

    pk_type = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    bool_default = "FALSE" if pg else "0"

    sql_commands = [
        f"""CREATE TABLE IF NOT EXISTS consultas_frecuentes (
            id {pk_type},
            pais_nombre TEXT UNIQUE,
            conteo INTEGER DEFAULT 1,
            ultima_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS usuarios (
            id {pk_type},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS favoritos_usuarios (
            id {pk_type},
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            pais_cca3 TEXT NOT NULL,
            fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, pais_cca3)
        )""",
        f"""CREATE TABLE IF NOT EXISTS paises_cache (
            id {pk_type},
            nombre_comun TEXT UNIQUE NOT NULL,
            cca3 TEXT,
            data TEXT NOT NULL,
            ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS refresh_tokens (
            id {pk_type},
            user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT {bool_default}
        )""",
        f"""CREATE TABLE IF NOT EXISTS token_blacklist (
            id {pk_type},
            jti TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE INDEX IF NOT EXISTS idx_paises_cache_cca3 ON paises_cache(cca3)""",
        f"""CREATE INDEX IF NOT EXISTS idx_favoritos_usuario ON favoritos_usuarios(usuario_id)""",
        f"""CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)""",
        f"""CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)""",
    ]

    for sql in sql_commands:
        try:
            cursor.execute(sql)
        except Exception as e:
            print(f"Error creando tabla: {e}")

    conn.commit()
    cursor.close()
    close_db_connection(conn)
    print("Base de datos inicializada correctamente")

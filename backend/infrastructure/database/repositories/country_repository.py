import json
from core.database import get_db_connection, close_db_connection, is_postgres


def get_cache_by_name(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()
    ph = "%s" if pg else "?"
    cursor.execute(f"SELECT data FROM paises_cache WHERE nombre_comun = {ph}", (name.lower(),))
    row = cursor.fetchone()
    if row:
        cursor.execute(f"UPDATE paises_cache SET ultima_actualizacion = CURRENT_TIMESTAMP WHERE nombre_comun = {ph}", (name.lower(),))
        conn.commit()
    cursor.close()
    close_db_connection(conn)
    return row[0] if row else None


def upsert_cache(name_lower, cca3, data_json):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_postgres():
            cursor.execute('''
                INSERT INTO paises_cache (nombre_comun, cca3, data, ultima_actualizacion) 
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (nombre_comun) 
                DO UPDATE SET 
                    data = EXCLUDED.data,
                    ultima_actualizacion = CURRENT_TIMESTAMP
            ''', (name_lower, cca3, data_json))
        else:
            cursor.execute("INSERT OR REPLACE INTO paises_cache (nombre_comun, cca3, data, ultima_actualizacion) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                           (name_lower, cca3, data_json))
        conn.commit()
    finally:
        cursor.close()
        close_db_connection(conn)


def increment_consulta(pais_nombre):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_postgres():
            cursor.execute('''
                INSERT INTO consultas_frecuentes (pais_nombre, conteo, ultima_consulta)
                VALUES (%s, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (pais_nombre) 
                DO UPDATE SET
                    conteo = consultas_frecuentes.conteo + 1,
                    ultima_consulta = EXCLUDED.ultima_consulta
            ''', (pais_nombre,))
        else:
            cursor.execute('''
                INSERT INTO consultas_frecuentes (pais_nombre, conteo, ultima_consulta)
                VALUES (?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (pais_nombre) 
                DO UPDATE SET
                    conteo = consultas_frecuentes.conteo + 1,
                    ultima_consulta = CURRENT_TIMESTAMP
            ''', (pais_nombre,))
        conn.commit()
    finally:
        cursor.close()
        close_db_connection(conn)


def get_cache_by_cca3(cca3):
    conn = get_db_connection()
    cursor = conn.cursor()
    cca3 = cca3.upper()
    try:
        if is_postgres():
            cursor.execute("SELECT data FROM paises_cache WHERE data->>'cca3' = %s", (cca3,))
        else:
            cursor.execute("SELECT data FROM paises_cache WHERE json_extract(data, '$.cca3') = ?", (cca3,))
        row = cursor.fetchone()
        cursor.close()
        close_db_connection(conn)
        return row[0] if row else None
    except Exception as e:
        cursor.close()
        close_db_connection(conn)
        print(f"Error obteniendo pais por cca3 {cca3}: {e}")
        return None


def get_cache_count():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM paises_cache")
    count = cursor.fetchone()[0]
    cursor.close()
    close_db_connection(conn)
    return count


def insert_many_countries(countries):
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()
    for country in countries:
        nombre = country['name']['common']
        data = json.dumps(country)
        if pg:
            cursor.execute('''
                INSERT INTO paises_cache (nombre_comun, data, ultima_actualizacion) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (nombre_comun) DO UPDATE SET data = EXCLUDED.data
            ''', (nombre, data))
        else:
            cursor.execute("INSERT OR REPLACE INTO paises_cache (nombre_comun, data, ultima_actualizacion) VALUES (?, ?, CURRENT_TIMESTAMP)",
                           (nombre, data))
    conn.commit()
    cursor.close()
    close_db_connection(conn)


def get_all_names():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_comun FROM paises_cache ORDER BY nombre_comun")
    rows = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return [row[0] for row in rows]


def get_populares(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(
        f"SELECT pais_nombre, conteo FROM consultas_frecuentes ORDER BY conteo DESC, ultima_consulta DESC LIMIT {ph}",
        (limit,)
    )
    rows = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return [{"pais": row[0], "conteo": row[1]} for row in rows]

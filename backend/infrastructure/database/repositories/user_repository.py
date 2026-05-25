from datetime import datetime, timezone
from core.database import get_db_connection, close_db_connection, is_postgres
from domain.user import User


def get_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(f"SELECT id, username, email FROM usuarios WHERE id = {ph}", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    return row


def get_by_username_with_hash(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(f"SELECT id, username, email, password_hash FROM usuarios WHERE username = {ph}", (username,))
    row = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    return row


def create(username, email, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_postgres():
            cursor.execute(
                "INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (username, email, password_hash)
            )
            user_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                "INSERT INTO usuarios (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        close_db_connection(conn)
        return user_id
    except Exception as e:
        cursor.close()
        close_db_connection(conn)
        raise e


def create_refresh_token(user_id, token, expires_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()
    ph = "%s" if pg else "?"
    cursor.execute(
        f"INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES ({ph}, {ph}, {ph})",
        (user_id, token, expires_at)
    )
    conn.commit()
    cursor.close()
    close_db_connection(conn)


def get_refresh_token(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(
        f"SELECT user_id, expires_at, revoked FROM refresh_tokens WHERE token = {ph}",
        (token,)
    )
    row = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    return row


def revoke_refresh_token(token, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()
    ph = "%s" if pg else "?"
    revoked_val = '1' if not pg else True
    cursor.execute(
        f"UPDATE refresh_tokens SET revoked = {ph} WHERE token = {ph} AND user_id = {ph}",
        (revoked_val, token, user_id)
    )
    conn.commit()
    cursor.close()
    close_db_connection(conn)


def get_user_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(
        f"SELECT pais_cca3 FROM favoritos_usuarios WHERE usuario_id = {ph} ORDER BY fecha_agregado DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return [row[0] for row in rows]


def add_favorite(user_id, cca3):
    conn = get_db_connection()
    cursor = conn.cursor()
    cca3 = cca3.upper()
    try:
        if is_postgres():
            cursor.execute('''
                INSERT INTO favoritos_usuarios (usuario_id, pais_cca3) 
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, pais_cca3) DO NOTHING
            ''', (user_id, cca3))
        else:
            cursor.execute('''
                INSERT OR IGNORE INTO favoritos_usuarios (usuario_id, pais_cca3, fecha_agregado) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, cca3))
        conn.commit()
        cursor.close()
        close_db_connection(conn)
        return True
    except Exception as e:
        cursor.close()
        close_db_connection(conn)
        raise e


def remove_favorite(user_id, cca3):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(
        f"DELETE FROM favoritos_usuarios WHERE usuario_id = {ph} AND pais_cca3 = {ph}",
        (user_id, cca3.upper())
    )
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return True


def add_to_blacklist(jti, expires_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_postgres():
            cursor.execute(
                "INSERT INTO token_blacklist (jti, expires_at) VALUES (%s, %s) ON CONFLICT (jti) DO NOTHING",
                (jti, expires_at)
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO token_blacklist (jti, expires_at) VALUES (?, ?)",
                (jti, expires_at)
            )
        conn.commit()
    finally:
        cursor.close()
        close_db_connection(conn)


def is_jti_blacklisted(jti):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cursor.execute(f"SELECT 1 FROM token_blacklist WHERE jti = {ph}", (jti,))
    row = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    return row is not None


def cleanup_expired_tokens():
    conn = get_db_connection()
    cursor = conn.cursor()
    pg = is_postgres()
    ph = "%s" if pg else "?"
    try:
        cursor.execute(f"DELETE FROM token_blacklist WHERE expires_at < {ph}", (datetime.now(timezone.utc),))
        deleted_blacklist = cursor.rowcount
        cursor.execute(f"DELETE FROM refresh_tokens WHERE expires_at < {ph}", (datetime.now(timezone.utc),))
        deleted_refresh = cursor.rowcount
        conn.commit()
        if deleted_blacklist > 0 or deleted_refresh > 0:
            print(f"Limpieza: {deleted_blacklist} blacklist + {deleted_refresh} refresh tokens expirados")
    finally:
        cursor.close()
        close_db_connection(conn)

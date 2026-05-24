import bcrypt
import jwt
import uuid
import re
from datetime import datetime, timedelta, timezone
from config.settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, EMAIL_REGEX
from repositories.usuario_repository import (
    get_by_id,
    get_by_username_with_hash,
    create as create_user,
    create_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
    get_user_favorites,
    add_favorite as repo_add_favorite,
    remove_favorite as repo_remove_favorite,
    add_to_blacklist
)


def validate_password(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    if not re.search(r'[A-Z]', password):
        return "La contraseña debe contener al menos una mayúscula"
    if not re.search(r'[0-9]', password):
        return "La contraseña debe contener al menos un número"
    return None


def validate_username(username):
    if len(username) < 3:
        return "El nombre de usuario debe tener al menos 3 caracteres"
    if len(username) > 30:
        return "El nombre de usuario no puede exceder 30 caracteres"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return "El nombre de usuario solo puede contener letras, números y guión bajo"
    return None


def generate_access_token(user_id):
    return jwt.encode({
        'jti': str(uuid.uuid4()),
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }, SECRET_KEY, algorithm='HS256')


def generate_refresh_token():
    return str(uuid.uuid4())


def register(username, email, password):
    if not username or not email or not password:
        return None, "Faltan campos"

    if not EMAIL_REGEX.match(email):
        return None, "Formato de email inválido"

    err = validate_username(username)
    if err:
        return None, err

    err = validate_password(password)
    if err:
        return None, err

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        user_id = create_user(username, email, password_hash)

        access_token = generate_access_token(user_id)
        refresh_token = generate_refresh_token()
        expires_refresh = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        create_refresh_token(user_id, refresh_token, expires_refresh)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": user_id, "username": username, "email": email}
        }, None

    except Exception as e:
        error_msg = str(e)
        if "username" in error_msg.lower():
            return None, "El nombre de usuario ya existe"
        elif "email" in error_msg.lower():
            return None, "El email ya está registrado"
        return None, "Error al registrar usuario"


def login(username, password):
    if not username or not password:
        return None, "Faltan campos"
    
    user = get_by_username_with_hash(username)
    if not user:
        return None, "Usuario no encontrado"
    
    user_id, username_db, email, password_hash = user
    
    if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
        return None, "Contraseña incorrecta"
    
    access_token = generate_access_token(user_id)
    refresh_token = generate_refresh_token()
    expires_refresh = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    create_refresh_token(user_id, refresh_token, expires_refresh)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user_id, "username": username_db, "email": email}
    }, None


def refresh_access_token(refresh_token):
    if not refresh_token:
        return None, "Refresh token required"
    
    token_data = get_refresh_token(refresh_token)
    if not token_data:
        return None, "Invalid refresh token"
    
    user_id, expires_at, revoked = token_data
    
    if revoked:
        return None, "Token revoked"
    
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    if datetime.now(timezone.utc) > expires_at:
        return None, "Refresh token expired"
    
    new_access_token = generate_access_token(user_id)
    return {"access_token": new_access_token}, None


def logout(user_id, refresh_token, access_token=None):
    if not refresh_token:
        return False, "refresh_token required"

    if access_token:
        try:
            data = jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])
            jti = data.get('jti')
            exp = datetime.fromtimestamp(data['exp'], tz=timezone.utc)
            if jti:
                add_to_blacklist(jti, exp)
        except Exception:
            pass

    revoke_refresh_token(refresh_token, user_id)
    return True, None


def get_user_info(user_id):
    user = get_by_id(user_id)
    if user:
        return {"id": user[0], "username": user[1], "email": user[2]}
    return None


def get_favorites(user_id):
    return get_user_favorites(user_id)


def add_favorite(user_id, cca3):
    if not cca3:
        return False, "Se requiere cca3 del país"
    
    repo_add_favorite(user_id, cca3)
    return True, None


def remove_favorite(user_id, cca3):
    repo_remove_favorite(user_id, cca3)
    return True, None

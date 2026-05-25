from functools import wraps
from flask import request, jsonify, g
import jwt
from core.config import settings

SECRET_KEY = settings.SECRET_KEY
API_KEY_PROTECTION = settings.API_KEY_PROTECTION
from services.auth_service import is_token_blacklisted


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or api_key != API_KEY_PROTECTION:
            return jsonify({"error": "No autorizado. x-api-key inválida"}), 401
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
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']

            jti = data.get('jti')
            if jti and is_token_blacklisted(jti):
                return jsonify({'message': 'Token has been revoked'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        g.user_id = current_user_id
        return f(*args, **kwargs)
    return decorated


def get_current_user_id():
    return g.get('user_id')

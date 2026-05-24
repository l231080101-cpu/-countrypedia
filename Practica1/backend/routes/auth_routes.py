from flask import Blueprint, jsonify, request, g
from services.auth_service import (
    register,
    login,
    refresh_access_token,
    logout,
    get_user_info,
    get_favorites,
    add_favorite,
    remove_favorite
)
from services.pais_service import get_country_by_cca3
from middleware.auth import token_required
from middleware.rate_limiter import rate_limit

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/register', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=300)
def register_route():
    """Register a new user.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              example: "usuario1"
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "SecurePass1"
    responses:
      201:
        description: User registered successfully
        schema:
          type: object
          properties:
            message:
              type: string
            user:
              type: object
      400:
        description: Validation error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    result, error = register(username, email, password)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result), 201


@auth_bp.route('/api/login', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def login_route():
    """Login and get access + refresh tokens.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: "usuario1"
            password:
              type: string
              example: "SecurePass1"
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
      401:
        description: Invalid credentials
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    result, error = login(username, password)
    if error:
        return jsonify({"error": error}), 401
    return jsonify(result)


@auth_bp.route('/api/refresh', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def refresh_route():
    """Refresh an expired access token using a refresh token.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - refresh_token
          properties:
            refresh_token:
              type: string
              example: "your-refresh-token"
    responses:
      200:
        description: Token refreshed successfully
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
      400:
        description: Invalid or expired refresh token
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.json or {}
    refresh_token = data.get('refresh_token')

    result, error = refresh_access_token(refresh_token)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@auth_bp.route('/api/logout', methods=['POST'])
@token_required
def logout_route():
    """Logout and revoke tokens.
    ---
    tags:
      - Auth
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            refresh_token:
              type: string
              example: "your-refresh-token"
            access_token:
              type: string
              example: "your-access-token"
    responses:
      200:
        description: Logged out successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Logged out successfully"
      400:
        description: Error during logout
        schema:
          type: object
          properties:
            error:
              type: string
    """
    user_id = g.user_id
    data = request.json
    refresh_token = data.get('refresh_token')
    access_token = data.get('access_token')

    result, error = logout(user_id, refresh_token, access_token)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route('/api/me', methods=['GET'])
@token_required
def me_route():
    """Get current authenticated user info.
    ---
    tags:
      - Auth
    security:
      - BearerAuth: []
    responses:
      200:
        description: User info
        schema:
          type: object
          properties:
            id:
              type: integer
            username:
              type: string
            email:
              type: string
      404:
        description: User not found
        schema:
          type: object
          properties:
            error:
              type: string
    """
    user_id = g.user_id
    user = get_user_info(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "Usuario no encontrado"}), 404


@auth_bp.route('/api/favoritos', methods=['GET', 'POST'])
@token_required
def gestionar_favoritos():
    """List or add favorites for the authenticated user.
    ---
    tags:
      - Favorites
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            cca3:
              type: string
              example: "MEX"
    responses:
      200:
        description: List of favorite countries (GET)
        schema:
          type: array
          items:
            type: object
      201:
        description: Country added to favorites (POST)
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            message:
              type: string
      400:
        description: Validation error
        schema:
          type: object
          properties:
            error:
              type: string
      404:
        description: Country not found
        schema:
          type: object
          properties:
            error:
              type: string
    """
    user_id = g.user_id
    
    if request.method == 'POST':
        try:
            data = request.json
            cca3 = data.get('cca3')
            
            pais = get_country_by_cca3(cca3)
            if not pais:
                return jsonify({"error": f"No se encontró el país con código {cca3}"}), 404
            
            result, error = add_favorite(user_id, cca3)
            if error:
                return jsonify({"error": error}), 400
            
            return jsonify({"status": "success", "message": f"País {pais['name']['common']} guardado en favoritos"}), 201
            
        except Exception as e:
            print("ERROR EN POST FAVORITOS:", str(e))
            return jsonify({"error": str(e)}), 500
    
    try:
        cca3_list = get_favorites(user_id)
        favoritos = []
        for cca3 in cca3_list:
            pais = get_country_by_cca3(cca3)
            if pais:
                favoritos.append(pais)
        
        return jsonify(favoritos)
        
    except Exception as e:
        print("ERROR EN GET FAVORITOS:", str(e))
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/api/favoritos/<cca3>', methods=['DELETE'])
@token_required
def eliminar_favorito(cca3):
    """Remove a country from favorites.
    ---
    tags:
      - Favorites
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: cca3
        type: string
        required: true
        description: ISO 3166-1 alpha-3 country code
    responses:
      200:
        description: Favorite removed
        schema:
          type: object
          properties:
            status:
              type: string
              example: "deleted"
    """
    user_id = g.user_id
    result, error = remove_favorite(user_id, cca3)
    return jsonify({"status": "deleted"}), 200

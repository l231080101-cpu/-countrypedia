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
from middleware.auth import require_api_key, token_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/register', methods=['POST'])
def register_route():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    result, error = register(username, email, password)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result), 201


@auth_bp.route('/api/login', methods=['POST'])
def login_route():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    result, error = login(username, password)
    if error:
        return jsonify({"error": error}), 401
    return jsonify(result)


@auth_bp.route('/api/refresh', methods=['POST'])
def refresh_route():
    data = request.json
    refresh_token = data.get('refresh_token')
    
    result, error = refresh_access_token(refresh_token)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result)


@auth_bp.route('/api/logout', methods=['POST'])
@token_required
def logout_route():
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
    user_id = g.user_id
    user = get_user_info(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "Usuario no encontrado"}), 404


@auth_bp.route('/api/favoritos', methods=['GET', 'POST'])
@require_api_key
@token_required
def gestionar_favoritos():
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
@require_api_key
@token_required
def eliminar_favorito(cca3):
    user_id = g.user_id
    result, error = remove_favorite(user_id, cca3)
    return jsonify({"status": "deleted"}), 200

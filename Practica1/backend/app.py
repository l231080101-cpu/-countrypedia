import os
import threading
from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

import config.settings as settings
from models.database import init_db
from routes.pais_routes import pais_bp
from routes.auth_routes import auth_bp
from routes.viaje_routes import viaje_bp
from repositories.usuario_repository import cleanup_expired_tokens

swagger_config = {
    "headers": [],
    "specs": [{
        "endpoint": 'apispec', "route": '/apispec.json',
        "rule_filter": lambda rule: True, "model_filter": lambda tag: True
    }],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
    "info": {
        "title": "CountryPedia API",
        "description": "API para explorar países, gestionar favoritos y obtener datos de viaje.",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-KEY",
            "description": "API Key requerida para endpoints de favoritos"
        },
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Access JWT token: 'Bearer <token>'"
        }
    },
    "security": [
        {"ApiKeyAuth": []},
        {"BearerAuth": []}
    ]
}

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY

origins = [o.strip() for o in settings.ORIGEN_PERMITIDO.split(',')]
CORS(app, resources={r"/api/*": {"origins": origins}})
Swagger(app, config=swagger_config)

app.register_blueprint(pais_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(viaje_bp)


@app.route('/')
def index():
    """Health check endpoint.
    ---
    tags:
      - Health
    responses:
      200:
        description: API is running
        schema:
          type: object
          properties:
            message:
              type: string
              example: "CountryPedia API - Documentación en /docs"
    """
    return jsonify({"message": "CountryPedia API - Documentación en /docs"})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404


with app.app_context():
    init_db()

if not os.getenv('DONT_CLEANUP_TOKENS'):
    def _cleanup_loop():
        while True:
            threading.Event().wait(3600)
            try:
                with app.app_context():
                    cleanup_expired_tokens()
            except Exception:
                pass

    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()

if __name__ == '__main__':
    print(f"Servidor iniciado en {settings.HOST}:{settings.PORT}")
    app.run(host=settings.HOST, port=settings.PORT)

import os
import time
from functools import wraps
from flask import request, jsonify, current_app

_attempts = {}


def rate_limit(max_requests=10, window_seconds=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_app.config.get('TESTING') or os.environ.get('TESTING'):
                return f(*args, **kwargs)

            client_ip = request.remote_addr or 'unknown'
            key = f"{client_ip}:{request.path}"

            now = time.time()
            window_start = now - window_seconds

            if key not in _attempts:
                _attempts[key] = []

            _attempts[key] = [t for t in _attempts[key] if t > window_start]

            if len(_attempts[key]) >= max_requests:
                return jsonify({"error": "Demasiadas solicitudes. Intente de nuevo más tarde."}), 429

            _attempts[key].append(now)
            return f(*args, **kwargs)

        return decorated
    return decorator

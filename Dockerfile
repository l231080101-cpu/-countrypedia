# STAGE 1: Frontend Builder — prepara assets estáticos
# ============================================================
FROM node:20-alpine AS frontend-builder

ARG API_BASE_URL=

WORKDIR /frontend

COPY frontend/ .

RUN if [ -z "$API_BASE_URL" ]; then \
      printf 'window.API_BASE = "";\n' > env-config.js; \
    else \
      sed -i "s|__API_BASE__|${API_BASE_URL}|g" env-config.js; \
    fi

# ============================================================
# STAGE 2: Python Builder — instala dependencias
# ============================================================
FROM python:3.11-slim AS python-builder

WORKDIR /build

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# STAGE 3: Runtime — Flask + Nginx
# ============================================================
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends nginx ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default

COPY --from=python-builder /install /usr/local

COPY backend/ /app/backend/
WORKDIR /app/backend

COPY --from=frontend-builder /frontend /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD rm -f /etc/nginx/sites-enabled/default && nginx && gunicorn -w 4 --worker-class sync --timeout 30 --keep-alive 5 -b 0.0.0.0:5000 app:app

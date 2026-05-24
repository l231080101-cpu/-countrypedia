# ============================================================
# STAGE 1: Builder — prepara y optimiza assets
# ============================================================
FROM node:20-alpine AS builder

ARG API_BASE_URL=http://127.0.0.1:5000

WORKDIR /build

# Copia el código fuente estático
COPY . .

# Reemplaza el placeholder con la URL real del backend
RUN sed -i "s|__API_BASE__|${API_BASE_URL}|g" env-config.js

# ============================================================
# STAGE 2: Runtime — solo nginx con los archivos estáticos
# ============================================================
FROM nginx:alpine

# Copia configuración personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia los archivos estáticos desde el builder (sin node, npm ni build tools)
COPY --from=builder /build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

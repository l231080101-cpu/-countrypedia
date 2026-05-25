# ============================================================
# STAGE 1: Builder — instala dependencias (incluye build tools)
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Solo copia el archivo de dependencias para aprovechar caché
COPY requirements.txt .

# Instala en un prefijo separado para copiar solo lo necesario
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# STAGE 2: Runtime — solo librerías necesarias para ejecutar
# ============================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Solo ca-certificates para requests HTTPS (nada de build-essential, gcc, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia únicamente los paquetes instalados, no el pip ni setuptools del builder
COPY --from=builder /install /usr/local

# Copia el código fuente
COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "--worker-class", "sync", "--timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "-b", "0.0.0.0:5000", "app:app"]

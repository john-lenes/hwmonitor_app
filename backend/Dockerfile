# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instala dependências de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python no diretório de instalação prefixado
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="HardwareMonitor"
LABEL description="Backend FastAPI – monitoramento de hardware e controle de ventoinhas"

WORKDIR /app

# Ferramentas de monitoramento de hardware no Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    lm-sensors \
    dmidecode \
    pciutils \
    && rm -rf /var/lib/apt/lists/*

# Copia pacotes instalados do stage builder
COPY --from=builder /install /usr/local

# Copia o código da aplicação
COPY app/ ./app/

# Copia dados padrão (perfis)
COPY data/ ./data/

# Variáveis de ambiente padrão (podem ser sobrescritas)
ENV HOST=0.0.0.0 \
    PORT=8765 \
    LOG_LEVEL=INFO \
    POLL_INTERVAL_SECONDS=2.0 \
    FAN_CONTROL_ENABLED=true \
    DATA_DIR=/app/data

EXPOSE 8765

# Health-check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/api/health')" || exit 1

CMD ["python", "-m", "app.main"]

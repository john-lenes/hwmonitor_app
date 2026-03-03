# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copia manifests de dependências primeiro (aproveita cache)
COPY package.json package-lock.json* ./

RUN npm ci --frozen-lockfile

# Copia o restante e compila
COPY . .

# A URL da API em runtime é injetada via variável de ambiente no build
ARG VITE_API_URL=http://localhost:8765
ARG VITE_WS_URL=ws://localhost:8765/ws
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build


# ── Stage 2: servidor estático Nginx ─────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="HardwareMonitor"
LABEL description="Frontend React – HardwareMonitor"

# Copia o build gerado pelo Vite
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuração personalizada do Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]

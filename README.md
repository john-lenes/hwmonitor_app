# HardwareMonitor

Aplicação web para monitoramento em tempo real de temperatura, uso de CPU/GPU/memória/disco e controle de velocidade de ventoinhas com perfis customizáveis.

## Sumário

- [Como funciona](#como-funciona)
- [Stack](#stack)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Início rápido com Docker](#início-rápido-com-docker)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [API REST](#api-rest)
- [WebSocket](#websocket)
- [Build de produção](#build-de-produção)
- [Pré-requisitos de hardware](#pré-requisitos-de-hardware)

---

## Como funciona

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│   React + Zustand + Recharts (Vite / Nginx :80)         │
│       │  REST /api/*          │  ws://…/ws              │
└───────┼───────────────────────┼─────────────────────────┘
        │                       │
┌───────▼───────────────────────▼─────────────────────────┐
│                    Backend FastAPI :8765                 │
│                                                         │
│  HardwareMonitor  FanController   ProfileManager        │
│  (psutil/sensors) (sysfs hwmon)  (profiles.json)        │
│        │                                                │
│        │ polling a cada 2 s                             │
│        ▼                                                │
│  WebSocketManager ──► broadcast para todos os clientes  │
└─────────────────────────────────────────────────────────┘
        │
        ▼  lê diretamente
  /sys/class/hwmon  /proc  lm-sensors
```

### Fluxo de dados

1. **HardwareMonitor** coleta métricas a cada `POLL_INTERVAL_SECONDS` (padrão 2 s) usando `psutil` e, no Linux, `lm-sensors` via `psutil.sensors_temperatures()`.
2. O snapshot é armazenado em memória e transmitido via **WebSocket** para todos os clientes conectados.
3. O **frontend** mantém até 60 entradas de histórico (~2 minutos) exibidos nos gráficos Recharts.
4. O **FanController** lê/escreve em `/sys/class/hwmon/*/pwm*` (Linux) ou via WMI/LibreHardwareMonitor (Windows).
5. **Perfis de ventoinha** são persistidos em `data/profiles.json` e mapeiam curvas temperatura → PWM.

---

## Stack

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.12, FastAPI, Uvicorn, WebSockets, psutil, py-cpuinfo, GPUtil, Pydantic v2 |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Zustand + Immer, Radix UI |
| **Infra** | Docker, Docker Compose, Nginx, Makefile |
| **Qualidade** | Ruff, Mypy, Pytest, ESLint |

---

## Estrutura do projeto

```
monitor_app/
├── docker-compose.yml          # Orquestração de produção
├── docker-compose.override.yml # Overrides de desenvolvimento (hot-reload)
├── Makefile                    # Atalhos de desenvolvimento
├── .env.example                # Template de variáveis de ambiente
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt        # Dependências de produção
│   ├── requirements-dev.txt    # Dependências de dev (ruff, pytest…)
│   ├── pyproject.toml          # Configuração ruff, mypy, pytest
│   ├── data/
│   │   └── profiles.json       # Perfis de ventoinha persistidos
│   ├── tests/
│   │   └── test_api.py         # Smoke tests da API
│   └── app/
│       ├── main.py             # Entry point FastAPI + lifespan
│       ├── api/routes/
│       │   ├── health.py       # GET /api/health  ← usado pelo healthcheck Docker
│       │   ├── hardware.py     # GET /api/hardware/*
│       │   ├── fans.py         # GET|POST /api/fans/*
│       │   └── profiles.py     # CRUD /api/profiles/*
│       ├── core/
│       │   ├── config.py       # Settings via variáveis de ambiente
│       │   └── logger.py       # Logger com detecção de container
│       ├── models/             # Pydantic schemas
│       ├── services/
│       │   ├── hardware_monitor.py  # Coleta CPU/GPU/memória/disco/temp
│       │   ├── fan_controller.py    # Leitura e escrita de RPM/PWM
│       │   └── profile_manager.py  # CRUD de perfis em JSON
│       └── websocket/
│           └── manager.py      # Broadcast para clientes WebSocket
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf              # Proxy reverso API + WebSocket + SPA
    ├── src/
    │   ├── components/dashboard/
    │   ├── pages/
    │   ├── services/api.ts     # Chamadas REST via Axios
    │   ├── store/hardwareStore.ts  # Estado global Zustand
    │   └── types/hardware.ts
    └── package.json
```

---

## Início rápido com Docker

### Pré-requisitos

- Docker >= 24 e Docker Compose Plugin v2
- Linux com `lm-sensors` instalado no host (para leitura de temperaturas)

```bash
# 1. Clone e configure
git clone <repo-url> monitor_app
cd monitor_app
cp .env.example .env        # ajuste variáveis se necessário

# 2. Suba os serviços
make up-build
# ou: docker compose up -d --build

# 3. Acesse
# Frontend: http://localhost
# API docs: http://localhost:8765/api/docs
# Health:   http://localhost:8765/api/health
```

### Comandos úteis

```bash
make logs       # acompanha logs em tempo real
make ps         # estado dos containers
make restart    # reinicia os serviços
make down       # para os serviços
make clean      # remove containers, volumes e imagens
```

---

## Variáveis de ambiente

Copie `.env.example` para `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `HOST` | `127.0.0.1` | Interface de bind (use `0.0.0.0` em container) |
| `PORT` | `8765` | Porta do backend |
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `POLL_INTERVAL_SECONDS` | `2.0` | Intervalo de coleta de métricas (segundos) |
| `FAN_CONTROL_ENABLED` | `true` | Habilita escrita de PWM para controle de ventoinhas |

---

## API REST

Documentação interativa disponível em `/api/docs` (Swagger UI).

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/health` | Health-check (uptime, versão) |
| `GET` | `/api/hardware/snapshot` | Snapshot completo de hardware |
| `GET` | `/api/hardware/cpu` | CPU (uso %, frequência, temperatura) |
| `GET` | `/api/hardware/memory` | Memória (usada, disponível, %) |
| `GET` | `/api/hardware/disks` | Discos por partição |
| `GET` | `/api/hardware/gpus` | GPUs NVIDIA (via GPUtil) |
| `GET` | `/api/hardware/temperatures` | Todos os sensores de temperatura |
| `GET` | `/api/fans/` | Lista ventoinhas detectadas |
| `POST` | `/api/fans/{id}/speed` | Define velocidade em % |
| `POST` | `/api/fans/{id}/auto` | Restaura controle automático |
| `POST` | `/api/fans/auto` | Restaura todas para automático |
| `GET` | `/api/profiles/` | Lista perfis de ventoinha |
| `POST` | `/api/profiles/` | Cria novo perfil |
| `PUT` | `/api/profiles/{id}` | Atualiza perfil |
| `DELETE` | `/api/profiles/{id}` | Remove perfil |
| `POST` | `/api/profiles/{id}/activate` | Ativa perfil |

---

## WebSocket

Conecte-se em `ws://localhost:8765/ws` para receber snapshots em tempo real.

Cada mensagem é um JSON com o schema de `HardwareSnapshot`:

```jsonc
{
  "timestamp": 1709500000.0,
  "cpu": { "usage_percent": 23.5, "frequency_mhz": 3600, "temperature": 58.0 },
  "memory": { "total_gb": 16.0, "used_gb": 8.2, "percent": 51.3 },
  "temperatures": [{ "component": "coretemp", "sensors": [...] }],
  "gpus": [...],
  "disks": [...]
}
```

---

## Pré-requisitos de hardware

### Linux

```bash
sudo apt install lm-sensors
sudo sensors-detect
```

Para controle de ventoinhas (PWM), o container roda com `privileged: true` para acesso a `/sys/class/hwmon`.

### Windows

Instale o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) como serviço Windows para expor sensores via WMI.

---

## Build de produção

```bash
make build && make up
```

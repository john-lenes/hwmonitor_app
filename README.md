# HardwareMonitor

Aplicação web para monitoramento em tempo real de temperatura, uso de CPU/GPU/memória/disco e controle de velocidade de ventoinhas com perfis customizáveis.

Desenvolvida e testada em **Windows 11 + Python 3.14** com hardware real (Intel i5-9300H, NVIDIA GTX 1650, 16 GB DDR4).

## Sumário

- [Como funciona](#como-funciona)
- [Stack](#stack)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Início rápido – Windows (nativo)](#início-rápido--windows-nativo)
- [Início rápido – Docker](#início-rápido--docker)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [API REST](#api-rest)
- [WebSocket](#websocket)
- [Tela de Painel](#tela-de-painel)
- [Tela de Ventoinhas](#tela-de-ventoinhas)
- [Perfis de Ventoinha](#perfis-de-ventoinha)
- [Build de produção](#build-de-produção)
- [Pré-requisitos de hardware](#pré-requisitos-de-hardware)
- [Testes](#testes)

---

## Como funciona

```
Browser (React 18 + Vite :5173 dev / Nginx :80 Docker)
  |   REST /api/*          |  ws://localhost:8765/ws (snapshot a cada 2 s)
  v                        v
Backend FastAPI :8765
  +-- HardwareMonitor  (psutil + LHM PowerShell reader no Windows)
  +-- FanController    (sysfs PWM no Linux / modos em memoria no Windows)
  +-- ProfileManager   (data/profiles.json, 4 perfis padrao)
  +-- WebSocketManager --> broadcast JSON para todos os clientes
        |
        v
  LibreHardwareMonitor DLL -> PowerShell reader -> %TEMP%\hwmonitor_lhm_sensors.json
```

### Fluxo de dados

1. **HardwareMonitor** coleta métricas a cada `POLL_INTERVAL_SECONDS` (padrão 2 s) usando `psutil` e, no Windows, um processo PowerShell em background lê a `LibreHardwareMonitorLib.dll` e exporta sensores para um arquivo JSON temporário (`%TEMP%\hwmonitor_lhm_sensors.json`, UTF-8 com BOM).
2. O snapshot é armazenado em memória e transmitido via **WebSocket** para todos os clientes conectados.
3. O **frontend** mantém até 60 entradas de histórico (~2 minutos) exibidos nos gráficos Recharts.
4. O **FanController** lê/escreve em `/sys/class/hwmon/*/pwm*` (Linux) ou rastreia modos em memória (Windows — controle físico requer drivers do fabricante).
5. **Perfis de ventoinha** são persistidos em `data/profiles.json` e mapeiam curvas temperatura &rarr; percentual de velocidade.

---

## Stack

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.12+, FastAPI 0.110, Uvicorn 0.29, WebSockets, psutil 5.9, Pydantic v2, pydantic-settings |
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS 3, Recharts 2, Zustand + Immer, Lucide React, Axios |
| **Infra** | Docker, Docker Compose, Nginx, Makefile, PyInstaller |
| **Qualidade** | Ruff, Mypy, Pytest 8, ESLint |
| **Sensores Windows** | LibreHardwareMonitorLib.dll (LHM 0.9.x) via PowerShell reader |

---

## Estrutura do projeto

```
hwmonitor_app/
├── docker-compose.yml
├── Makefile
├── monitor.spec                 # Spec do PyInstaller (bundle standalone)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml           # Configuração ruff, mypy, pytest
│   ├── data/
│   │   └── profiles.json        # Perfis persistidos
│   ├── tests/
│   │   └── test_api.py          # Smoke tests + teste de endpoint de modo
│   └── app/
│       ├── main.py              # Entry point FastAPI + lifespan
│       ├── api/routes/
│       │   ├── health.py        # GET /api/health
│       │   ├── hardware.py      # GET /api/hardware/*
│       │   ├── fans.py          # GET|POST /api/fans/*
│       │   └── profiles.py      # CRUD /api/profiles/*
│       ├── core/
│       │   ├── config.py        # Settings via variáveis de ambiente
│       │   └── logger.py        # Logger estruturado
│       ├── models/
│       │   ├── hardware.py      # CpuStats, MemoryStats, DiskStats, GpuStats...
│       │   ├── fan.py           # FanReading, FanSpeedRequest, FanModeRequest, SPEED_MODES
│       │   └── profile.py       # FanProfile, CurvePoint
│       ├── services/
│       │   ├── hardware_monitor.py   # Coleta CPU/GPU/memória/disco/temp + LHM bridge
│       │   ├── fan_controller.py     # RPM tracking, PWM (Linux) e modos (Windows)
│       │   └── profile_manager.py   # CRUD de perfis com 4 perfis padrão
│       └── websocket/
│           └── manager.py       # Broadcast para clientes WebSocket
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf               # Proxy reverso API + WebSocket + SPA
    └── src/
        ├── components/dashboard/
        │   ├── FanSpeedControl.tsx   # Cartão estilo Nitro Sense (3 modos + RPM + sparkline)
        │   ├── HardwareCard.tsx
        │   ├── HistoryChart.tsx
        │   ├── TemperatureGauge.tsx
        │   └── UsageBar.tsx
        ├── pages/
        │   ├── Dashboard.tsx         # Painel principal de hardware
        │   ├── FanProfiles.tsx       # Perfis de ventoinha + painel tempo real
        │   └── Settings.tsx
        ├── services/api.ts           # Chamadas REST via Axios
        ├── store/hardwareStore.ts    # Estado global Zustand + polling RPM 3 s
        └── types/hardware.ts         # Interfaces TypeScript (espelham Pydantic)
```

---

## Início rápido – Windows (nativo)

### Pré-requisitos

- Python 3.12+ (`py` launcher)
- Node.js 18+
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) instalado (para temperaturas, GPU e ventoinhas)

```powershell
# 1. Backend
cd hwmonitor_app\backend
py -m pip install -r requirements-dev.txt
py -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

# 2. Frontend (outro terminal)
cd hwmonitor_app\frontend
npm install
npm run dev
# Acesse: http://localhost:5173
```

> **Sensores Windows:** Execute o LibreHardwareMonitor antes de iniciar o backend. O script PowerShell `lhm_reader.ps1` é iniciado automaticamente quando a DLL é encontrada.

---

## Início rápido – Docker

### Pré-requisitos

- Docker >= 24 e Docker Compose Plugin v2
- Linux com `lm-sensors` instalado no host

```bash
git clone <repo-url> hwmonitor_app
cd hwmonitor_app

make up-build
# ou: docker compose up -d --build

# Acesse:
# Frontend:  http://localhost
# API docs:  http://localhost:8765/api/docs
# Health:    http://localhost:8765/api/health
```

### Comandos Makefile

```bash
make build      # constrói as imagens sem subir
make up         # sobe os serviços em background
make up-build   # reconstrói imagens e sobe
make down       # para e remove os containers
make restart    # reinicia todos os serviços
make logs       # acompanha os logs em tempo real
make ps         # lista o estado dos containers
make clean      # remove containers, volumes e imagens
```

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `HOST` | `127.0.0.1` | Interface de bind (`0.0.0.0` em container) |
| `PORT` | `8765` | Porta do backend |
| `LOG_LEVEL` | `INFO` | Nível de log |
| `POLL_INTERVAL_SECONDS` | `2.0` | Intervalo de coleta de métricas (segundos) |
| `HISTORY_MAX_POINTS` | `120` | Tamanho do buffer circular de histórico (~4 min com 2 s de intervalo) |
| `RATE_LIMIT_REQUESTS` | `60` | Máximo de requisições de escrita por IP na janela |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Janela de tempo do rate limiter (segundos) |
| `VITE_API_URL` | `http://127.0.0.1:8765` | URL base da API (frontend) |
| `VITE_WS_URL` | `ws://<hostname>:8765/ws` | URL do WebSocket (frontend) |

---

## API REST

Documentação interativa disponível em `http://localhost:8765/api/docs`.

Todos os endpoints utilizam o prefixo `/api/v1/`. O endpoint `/api/health` é mantido como alias de compatibilidade retroativa para o Docker HEALTHCHECK.

### Respostas de erro padronizadas

Erros retornam sempre o mesmo envelope JSON:

```json
{
  "success": false,
  "error": "NotFoundError",
  "detail": "Perfil 'meu_perfil' não encontrado.",
  "path": "/api/v1/profiles/meu_perfil",
  "timestamp": "2024-03-04T12:00:00+00:00"
}
```

### Rate Limiting

Requisições de escrita (POST/PUT/PATCH/DELETE) são limitadas por IP a **60 req/60 s** por padrão (configurável via `RATE_LIMIT_REQUESTS` e `RATE_LIMIT_WINDOW_SECONDS`). Ao exceder o limite, a API retorna `HTTP 429` com header `Retry-After`.

### Hardware

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/health` | Health-check (status, uptime, versão, OS) |
| `GET` | `/api/v1/hardware/snapshot` | Snapshot completo (CPU, RAM, disco, GPU, temperaturas) |
| `GET` | `/api/v1/hardware/history?limit=60` | Últimos N snapshots do buffer circular em memória |
| `GET` | `/api/v1/hardware/cpu` | CPU — uso %, frequência MHz, temperatura, por-core |
| `GET` | `/api/v1/hardware/memory` | Memória — usada, disponível, %, slots físicos DDR |
| `GET` | `/api/v1/hardware/disks` | Discos — partição lógica + modelo físico, tipo (NVMe/SSD/HDD) |
| `GET` | `/api/v1/hardware/gpus` | GPUs — carga, VRAM, temperatura, driver |
| `GET` | `/api/v1/hardware/temperatures` | Todos os sensores de temperatura agrupados por componente |

#### Parâmetros do endpoint `/history`

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `limit` | int (1–500) | `60` | Número de snapshots a retornar |

### Ventoinhas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/fans/` | Lista ventoinhas com RPM atual, RPM máximo histórico e modo ativo |
| `POST` | `/api/v1/fans/{id}/speed` | Define velocidade em % (0–100) |
| `POST` | `/api/v1/fans/{id}/mode` | Define modo de velocidade (ver tabela abaixo) |
| `POST` | `/api/v1/fans/{id}/auto` | Restaura controle automático (BIOS) |
| `POST` | `/api/v1/fans/auto` | Restaura todas para automático |

#### Modos de ventoinha (`POST /api/fans/{id}/mode`)

```json
{ "mode": "quiet" }
```

| Modo | Velocidade | Descrição |
|------|-----------|-----------|
| `quiet` | ~30% | Silencioso — baixo ruído, uso leve |
| `balanced` | ~60% | Balanceado — uso geral e multitarefa |
| `turbo` | ~100% | Turbo — máxima performance |
| `auto` | BIOS | Restaura controle automático |

> No Linux o modo é traduzido para PWM via sysfs. No Windows é salvo em memória (controle físico requer drivers do fabricante como Nitro Sense).

### Perfis de Ventoinha

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/profiles/` | Lista todos os perfis (padrões + personalizados) |
| `GET` | `/api/v1/profiles/active` | Retorna o perfil atualmente ativo |
| `POST` | `/api/v1/profiles/` | Cria novo perfil customizado |
| `PUT` | `/api/v1/profiles/{id}` | Atualiza perfil existente |
| `DELETE` | `/api/v1/profiles/{id}` | Remove perfil (apenas não-padrão) |
| `POST` | `/api/v1/profiles/{id}/activate` | Ativa um perfil |
| `POST` | `/api/v1/profiles/{id}/reset` | Restaura perfil padrão às configs originais |

---

## WebSocket

Conecte-se em `ws://localhost:8765/ws`. Cada mensagem é um JSON `HardwareSnapshot` enviado a cada ~2 s:

```jsonc
{
  "timestamp": 1709500000.0,
  "cpu": {
    "usage_percent": 23.5,
    "per_core": [18.0, 3.0, 18.0, 6.0, 12.0, 6.0, 17.0, 9.0],
    "frequency_mhz": 3600.0,
    "temperature": 58.0
  },
  "memory": {
    "total_gb": 16.0,
    "used_gb": 8.2,
    "percent": 51.3,
    "slots": [
      { "device_locator": "DIMM 0", "size_gb": 8, "speed_mhz": 2667, "memory_type": "DDR4" }
    ]
  },
  "disks": [
    {
      "device": "C:\\",
      "mountpoint": "C:\\",
      "total_gb": 119.24,
      "used_gb": 60.1,
      "percent": 50.4,
      "model": "NVMe IM2P33F8BR1-128G",
      "media_type": "NVMe",
      "physical_size_gb": 119.24
    }
  ],
  "gpus": [
    {
      "name": "NVIDIA GeForce GTX 1650",
      "load_percent": 12.0,
      "memory_used_mb": 512.0,
      "memory_total_mb": 4096.0,
      "temperature": 68.0,
      "vram_gb": 4.0
    }
  ],
  "temperatures": [
    { "component": "CPU Package", "sensors": [{ "label": "CPU Package", "current": 58.0 }] }
  ]
}
```

### FanReading (via `GET /api/fans/`)

```jsonc
{
  "id": "fan_0",
  "label": "CPU Fan",
  "rpm": 1200,
  "min_rpm": 0,
  "max_rpm": 4800,   // RPM máximo observado (rastreado em memória)
  "percent": 30,
  "controllable": true,
  "speed_mode": "quiet"   // "auto" | "quiet" | "balanced" | "turbo"
}
```

---

## Tela de Painel

A página principal exibe em tempo real:

- **CPU** — uso total e por núcleo, frequência MHz, temperatura com código de cor
- **Memória** — uso em GB/%, slots físicos DDR (via `Win32_PhysicalMemory` no Windows)
- **Disco** — uso por partição, modelo do disco físico, badge de tipo (NVMe/SSD/HDD)
- **GPU** — carga %, VRAM usada/total, temperatura (via LHM no Windows, não GPUtil)
- **Gráfico histórico** — CPU, GPU e RAM nos últimos ~2 minutos
- **Ventoinhas** — cartões `FanSpeedControl` com RPM e seletor de modo rápido

---

## Tela de Ventoinhas

Acessível em `/fans`:

### Painel de monitoramento em tempo real

Atualizado via WebSocket e polling de 3 s:

- Temperatura CPU e GPU com código de cor (verde < 55°C / amarelo < 70°C / âmbar < 85°C / vermelho >= 85°C)
- Uso de CPU % e RAM %
- **Velocidade alvo calculada** por interpolação linear da curva do perfil ativo
- Mini-gráfico `CurveMarker` mostrando onde na curva o sistema opera agora

### Cartões de ventoinha (estilo Nitro Sense)

Cada `FanSpeedControl` exibe:

- RPM atual em destaque + RPM máximo histórico observado
- Barra de progresso RPM / máximo colorida pelo modo ativo
- Sparkline do histórico de RPM (até 60 leituras / ~3 min)
- **Seletor de 3 modos**: Silencioso / Balanceado / Turbo
- Botão "Restaurar automático (BIOS)"
- Borda colorida por modo (verde / âmbar / vermelho)

---

## Perfis de Ventoinha

Acessível em `/fans` (segunda seção):

- Visualizar e ativar perfis padrão e personalizados
- Criar perfis com curva temperatura (°C) -> velocidade (%) com até 8 pontos
- Sensor de controle configurável: CPU Package, GPU, SSD NVMe
- Visualização da curva com equivalência em °F
- Templates para preenchimento rápido

### Perfis padrão incluídos

| Nome | Sensor | Curva (resumida) |
|------|--------|-----------------|
| **Silencioso** | CPU | 0°C=0% · 50°C=20% · 65°C=40% · 80°C=70% · 90°C=100% |
| **Balanceado** | CPU | 0°C=20% · 50°C=40% · 65°C=60% · 75°C=80% · 85°C=100% |
| **Performance** | CPU | 0°C=50% · 40°C=60% · 60°C=80% · 75°C=100% |
| **Gamer (GPU)** | GPU | 0°C=30% · 50°C=50% · 70°C=80% · 80°C=100% |

---

## Build de produção

### Docker

```bash
make build && make up
```

### Standalone (PyInstaller)

```powershell
cd hwmonitor_app\backend
py -m PyInstaller monitor.spec
# Executável gerado em dist/
```

---

## Pré-requisitos de hardware

### Windows

1. Instale o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
2. Execute-o ao menos uma vez para calibrar os sensores
3. O backend localiza a DLL automaticamente em:
   - `%LOCALAPPDATA%\Microsoft\WinGet\Packages\**\LibreHardwareMonitorLib.dll`
   - `C:\Program Files\LibreHardwareMonitor\`
   - `C:\Program Files (x86)\LibreHardwareMonitor\`
   - `C:\Tools\LibreHardwareMonitor\`

> **Nota sobre controle de ventoinhas:** Em alguns notebooks (ex.: Acer Nitro 5) o EC não expõe RPM via LHM — o hardware usa ACPI proprietário. O app salva o modo em memória e mostra o estado na UI, mas o controle físico requer o software do fabricante (Nitro Sense, OMEN Command Center etc.).

> **Nota sobre GPU:** Dados de GPU são lidos do JSON do LHM, não via GPUtil (incompatível com Python 3.14+).

### Linux

```bash
sudo apt install lm-sensors
sudo sensors-detect
```

Para controle PWM de ventoinhas, o processo precisa de permissão de escrita em `/sys/class/hwmon/*/pwm*` (normalmente `root` ou container com `privileged: true`).

---

## Testes

```bash
cd hwmonitor_app/backend
py -m pytest tests/ -v
```

> **Nota:** A primeira execução pode levar ~12 s devido à inicialização do processo PowerShell LHM. Em execuções sequenciais, o processo já está em cache.

| Teste | Descrição |
|-------|-----------|
| `test_health_ok` | GET /api/v1/health retorna 200 com `success: true` e campos de metadados |
| `test_health_backward_compat` | GET /api/health (alias legado) continua funcionando |
| `test_openapi_docs` | GET /api/docs retorna 200 |
| `test_hardware_snapshot` | Snapshot contém `cpu`, `memory`, `disks`, `gpus`, `temperatures`, `timestamp` |
| `test_hardware_history_default` | GET /api/v1/hardware/history retorna lista |
| `test_hardware_history_limit` | GET /history?limit=5 retorna no máximo 5 entradas |
| `test_hardware_history_limit_validation` | GET /history?limit=0 retorna 422 com body padronizado `{success: false}` |
| `test_hardware_cpu` | Estatísticas da CPU contêm `usage_percent` e `frequency_mhz` |
| `test_fans_list` | Lista de ventoinhas retorna array com campos `id`, `rpm`, `speed_mode` |
| `test_fan_mode_valid` | POST /mode aceita quiet/balanced/turbo/auto e retorna 200 |
| `test_fan_mode_invalid` | POST /mode com modo inválido retorna 422 com `{success: false}` |
| `test_profiles_list` | Lista de perfis retorna array com >= 1 perfil |
| `test_profile_not_found` | GET /profiles/inexistente retorna 404 com body padronizado |
| `test_active_profile` | GET /profiles/active retorna 200 ou 404 |

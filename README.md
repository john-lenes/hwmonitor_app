# HardwareMonitor

Aplicação de monitoramento de temperatura de hardware e controle de fans com perfis customizáveis.

## Stack

- **Backend**: Python 3.12+, FastAPI, WebSocket, psutil, py-cpuinfo
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Recharts, Zustand + Immer
- **Packaging**: PyInstaller (backend embarcado)

## Estrutura

```
monitor_app/
├── backend/          # Python FastAPI + WebSocket
│   ├── app/
│   │   ├── api/      # Rotas REST
│   │   ├── core/     # Configurações e utilitários
│   │   ├── models/   # Pydantic models
│   │   ├── services/ # Lógica de negócio (hardware, fans)
│   │   └── websocket/ # Gerenciador WebSocket
│   └── requirements.txt
└── frontend/         # React + Vite + TypeScript
    └── src/
        ├── components/ # Componentes UI
        ├── lib/        # Utilitários
        ├── pages/      # Páginas da aplicação
        ├── services/   # Chamadas de API REST
        ├── store/      # Estado global (Zustand)
        └── types/      # TypeScript types
```

## Pré-requisitos

### Linux
```bash
sudo apt install lm-sensors fancontrol
sudo sensors-detect
```

### Windows
- Instale o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) como serviço

## Desenvolvimento

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main

# Frontend (outro terminal)
cd frontend
npm install
npm run dev

```

## Build de Produção

```bash
# Gera o bundle do frontend
cd frontend && npm run build

# Empacota o backend com PyInstaller (a partir da raiz)
pyinstaller monitor.spec
```

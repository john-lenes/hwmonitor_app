# ── HardwareMonitor – Makefile ────────────────────────────────────────────────
# Atalhos Docker. Uso: make <target>

.PHONY: help build up up-build down restart logs ps clean

## ── Ajuda ─────────────────────────────────────────────────────────────────────
help:          ## Exibe esta mensagem de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ── Docker Compose ───────────────────────────────────────────────────────────
build:         ## Constrói as imagens sem subir
	docker compose build

up:            ## Sobe os serviços em background
	docker compose up -d

up-build:      ## Reconstrói imagens e sobe
	docker compose up -d --build

down:          ## Para e remove os containers
	docker compose down

restart:       ## Reinicia todos os serviços
	docker compose restart

logs:          ## Acompanha os logs em tempo real
	docker compose logs -f

ps:            ## Lista o estado dos containers
	docker compose ps

## ── Limpeza ───────────────────────────────────────────────────────────────────
clean:         ## Remove containers, volumes e imagens do projeto
	docker compose down --volumes --remove-orphans --rmi local 2>/dev/null || true

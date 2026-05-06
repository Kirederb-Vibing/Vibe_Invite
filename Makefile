# Vibe Invite — convenience commands
# Run "make help" to see all targets

.PHONY: help start start-caddy start-pangolin stop logs build update \
        shell migrate createsuperuser backup-db

COMPOSE = docker compose

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Startup (choose one) ──────────────────────────────────────────────────────

start:  ## Start with external proxy (NPM, Traefik, Pangolin) — exposes port 8000
	$(COMPOSE) up -d

start-caddy:  ## Start with built-in Caddy (auto-SSL) — requires DOMAIN and ACME_EMAIL in .env
	$(COMPOSE) --profile caddy up -d

start-pangolin:  ## Start with Pangolin newt agent bundled — requires PANGOLIN_* vars in .env
	$(COMPOSE) --profile pangolin up -d

# ── Management ────────────────────────────────────────────────────────────────

stop:  ## Stop all services
	$(COMPOSE) down

logs:  ## Follow live logs
	$(COMPOSE) logs -f

build:  ## Rebuild the application image
	$(COMPOSE) build

update:  ## Pull latest image and restart
	$(COMPOSE) pull
	$(COMPOSE) up -d

shell:  ## Open a Django shell
	$(COMPOSE) exec vibe_invite_web python manage.py shell

migrate:  ## Run database migrations manually
	$(COMPOSE) exec vibe_invite_web python manage.py migrate

createsuperuser:  ## Create a Django admin user
	$(COMPOSE) exec vibe_invite_web python manage.py createsuperuser

backup-db:  ## Dump the database to a local .sql file
	$(COMPOSE) exec vibe_invite_db pg_dump -U $${DB_USER:-vibe_invite} $${DB_NAME:-vibe_invite} > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved."

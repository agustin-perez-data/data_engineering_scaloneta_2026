# =============================================================================
# Makefile — Argentina 2026 World Cup analytics
# =============================================================================
.DEFAULT_GOAL := help

# Color codes for help output
CYAN  := \033[36m
RESET := \033[0m

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

.PHONY: up
up:  ## Start all services in detached mode
	docker-compose up -d

.PHONY: down
down:  ## Stop and remove all containers
	docker-compose down

.PHONY: logs
logs:  ## Follow logs from all services
	docker-compose logs -f

# ---------------------------------------------------------------------------
# ETL pipeline
# ---------------------------------------------------------------------------

.PHONY: etl-extract
etl-extract:  ## Run the data extraction step (FBRef + StatsBomb)
	docker-compose exec etl_runner python -m etl.extract.run_extract

.PHONY: etl-transform
etl-transform:  ## Run the data transformation / cleaning step
	docker-compose exec etl_runner python -m etl.transform.run_transform

.PHONY: etl-load
etl-load:  ## Load transformed data into PostgreSQL
	docker-compose exec etl_runner python -m etl.load.run_all

.PHONY: etl-all
etl-all: etl-extract etl-transform etl-load  ## Run full ETL pipeline (extract → transform → load)

# ---------------------------------------------------------------------------
# Database utilities
# ---------------------------------------------------------------------------

.PHONY: psql
psql:  ## Open an interactive psql session inside the postgres container
	docker-compose exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

.PHONY: reset-db
reset-db:  ## Drop and recreate the main database (WARNING: destroys all data)
	docker-compose exec postgres psql -U $${POSTGRES_USER} -c "DROP DATABASE IF EXISTS $${POSTGRES_DB};"
	docker-compose exec postgres psql -U $${POSTGRES_USER} -c "CREATE DATABASE $${POSTGRES_DB};"
	docker-compose exec etl_runner psql -h $${POSTGRES_HOST} -U $${POSTGRES_USER} -d $${POSTGRES_DB} -f /app/sql/schema.sql

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help:  ## List all available targets with descriptions
	@echo ""
	@echo "Argentina 2026 World Cup Analytics — available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

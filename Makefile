
setup-project:
	@echo "Setting up project..."
	uv sync
	pre-commit install

run-pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Infra
up: down
	@echo "Starting development environment..."

	docker compose -f docker-compose-dev.yml up -d
	make intra-script
	make app-script

intra-script:
	@echo "Running script.py..."
	uv run script.py

app-script:
	make m-apply

down:
	@echo "Stopping and removing development containers..."
	docker compose -f docker-compose-dev.yml down


# Alembic migration commands
m-create:
	@echo "Creating new migration..."
	alembic revision --autogenerate -m "./alembic"

m-apply:
	@echo "Applying migrations..."
	alembic upgrade head

m-rollback:
	@echo "Rolling back one migration..."
	alembic downgrade -1

m-current:
	@echo "Current database version:"
	alembic current

m-history:
	@echo "Migration history:"
	alembic history --verbose

m-sql:
	@echo "Showing SQL for pending migrations:"
	alembic upgrade head --sql
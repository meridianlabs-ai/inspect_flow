.PHONY: check
check:
	uv run ruff check --fix
	uv run ruff format
	uv run pyright

.PHONY: test
test:
	uv run pytest

.PHONY: cov
cov:
	uv run pytest --cov=inspect_flow --cov-report=html --cov-branch

.PHONY: hooks
hooks:
	pre-commit install

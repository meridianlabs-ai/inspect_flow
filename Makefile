.PHONY: check
check:
	ruff check --fix
	ruff format
	pyright

.PHONY: test
test:
	pytest

.PHONY: cov
cov:
	pytest --cov=inspect_flow --cov-report=html --cov-branch

.PHONY: hooks
hooks:
	pre-commit install

.PHONY: docs
docs:
	uv sync --extra doc
	uv run quarto render docs

.PHONY: docs-publish
docs-publish:
	uv sync --extra doc
	git worktree prune
	cd docs && PRE_COMMIT_ALLOW_NO_CONFIG=1 uv run quarto publish gh-pages --no-prompt
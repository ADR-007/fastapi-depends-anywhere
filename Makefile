.PHONY: lint lint-fix test test-cov test-all install-githooks

install-githooks:
	@cd .git/hooks; \
	ln -sf ../../.githooks/pre-push .; \
	ln -sf ../../.githooks/pre-commit .;

lint:
	uv run ruff check fastapi_depends_anywhere tests/
	uv run ruff format --check fastapi_depends_anywhere tests/
	uv run mypy fastapi_depends_anywhere tests/

lint-fix:
	uv run ruff format fastapi_depends_anywhere tests/
	uv run ruff check --fix fastapi_depends_anywhere tests/

test:
	uv run pytest tests/ -v

test-cov:
	uv run coverage run -m pytest tests/ -v
	uv run coverage report --skip-empty --show-missing

test-all:
	uv run tox

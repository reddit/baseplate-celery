.DEFAULT_GOAL := help

# pytest exits 5 when no tests are collected.
TEST_CMD = uv run --exact --group dev pytest -n auto -ra

.PHONY: help
help:
	@echo "Available commands:"
	@echo '  make build - Build the sdist and wheel into dist/'
	@echo '  make fmt - Apply formatting and lint fixes'
	@echo '  make lint - Run all lint checks'
	@echo '  make scaffold - Set up the local venv and git hooks'
	@echo '  make test - Run tests'
	@echo '  make test-cov - Run tests with coverage'

.PHONY: scaffold
scaffold:
	uv sync --exact --group dev
	lefthook install

.PHONY: lint
lint:
	uv run --exact --group dev ruff check
	uv run --exact --group dev ruff format --check
	uv run --exact --group dev ty check

.PHONY: fmt
fmt:
	uv run --exact --group dev ruff format
	uv run --exact --group dev ruff check --fix

.PHONY: test
test:
	$(TEST_CMD) --no-cov || [ $$? -eq 5 ]

.PHONY: test-cov
test-cov:
	$(TEST_CMD) --cov --cov-report=term --cov-report=lcov --no-cov-on-fail || [ $$? -eq 5 ]

.PHONY: build
build:
	uv build

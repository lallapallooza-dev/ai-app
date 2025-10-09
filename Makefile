.PHONY: check-tools
check-tools:
	which autoflake || pip install autoflake
	which isort || pip install isort
	which black || pip install black
	which flake8 || pip install flake8

.PHONY: lint
lint: check-tools
	@echo "\n=== Checking files with flake8 ===\n"
	flake8 . --count --statistics --show-source --format="%(path)s:%(row)d:%(col)d: %(code)s %(text)s" --filename="*.py"

.PHONY: check-files
check-files: check-tools
	@echo "\n=== Files that need formatting ===\n"
	@black --check . --quiet || true
	@echo "\n=== Files with import issues ===\n"
	@isort --check-only --diff . || true
	@echo "\n=== Files with unused imports ===\n"
	@autoflake --recursive --check . || true

.PHONY: format
format: check-tools
	isort . --profile black --multi-line=3 --trailing-comma --force-grid-wrap=0 --use-parentheses --line-length=88
	black . --line-length=88 --target-version=py38 --preview

.PHONY: install-dev
install-dev:
	pip install black flake8 isort autoflake

.PHONY: clean
clean: check-tools
	autoflake --recursive --in-place --remove-all-unused-imports --remove-unused-variables .

.PHONY: check-all
check-all: check-files clean format lint


.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make check-files - Show files that need formatting"
	@echo "  make lint        - Run linter (flake8) with detailed output"
	@echo "  make format      - Run formatters (black, isort)"
	@echo "  make clean       - Remove unused imports and variables (autoflake)"
	@echo "  make check-all   - Run all checks and formatting"
	@echo "  make install-dev - Install development dependencies" 
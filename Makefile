.PHONY: all setup install lock test cov demo clean lint format format-check typecheck audit dist help

# Default target
all: install

# Create .venv from the lockfile with the dev tools (needs uv). --frozen: a
# user-level uv config must never rewrite the shared lockfile; see `lock`.
setup:
	uv sync --frozen --extra dev

# Regenerate uv.lock after editing pyproject.toml. --no-config keeps settings
# from ~/.config/uv/uv.toml (such as exclude-newer) out of the lockfile, so
# the lock is the same on every machine and in CI.
lock:
	uv lock --no-config

# Install the package editable into the active environment (unlocked, pip only)
install:
	pip install -e '.[dev]'

# Run tests
test:
	pytest tests/

# Run tests with a coverage report (fails below the threshold in pyproject.toml)
cov:
	pytest --cov=ldapie --cov-report=term-missing tests/

# Run the demo
demo:
	ldapie --demo

# Lint (ruff replaces flake8, isort and pylint)
lint:
	ruff check src tests scripts

# Sort imports and format code
format:
	ruff check --select I --fix src tests scripts
	ruff format src tests scripts

# Check formatting without changing files (CI runs this; `lint` covers import order)
format-check:
	ruff format --check src tests scripts

# Run mypy
typecheck:
	cd src && PYTHONPATH=. mypy --config-file=../mypy.ini ldapie

# Check the locked dependencies against known vulnerabilities (pip-audit is in the dev extra)
audit:
	uv export --quiet --frozen --all-extras --no-emit-project --format requirements-txt > .requirements-audit.txt
	pip-audit --no-deps --disable-pip -r .requirements-audit.txt
	rm -f .requirements-audit.txt

# Clean up temporary files and builds
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -f .requirements-audit.txt
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './.venv/*' -delete

# Build distribution packages (sdist and wheel)
dist:
	uv build

# Help
help:
	@echo "Available targets:"
	@echo "  setup             - Create .venv from uv.lock with the dev tools (needs uv)"
	@echo "  install           - pip install the package editable with the dev tools (unlocked)"
	@echo "  lock              - Regenerate uv.lock after editing pyproject.toml"
	@echo "  test              - Run tests with pytest"
	@echo "  cov               - Run tests with a coverage report"
	@echo "  demo              - Run the demo with mock LDAP server"
	@echo "  lint              - Run ruff check"
	@echo "  format            - Sort imports and format with ruff"
	@echo "  format-check      - Check formatting"
	@echo "  typecheck         - Run mypy type checking"
	@echo "  audit             - Check locked dependencies for known vulnerabilities"
	@echo "  dist              - Build sdist and wheel (uv build)"
	@echo "  clean             - Clean up temporary files and builds"

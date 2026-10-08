.PHONY: all setup install test demo clean lint flake typecheck format dist help

# Default target
all: install

# Setup development environment
setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -e '.[dev]'

# Install the package
install:
	pip install -e .

# Run tests
test:
	pytest tests/

# Run the demo
demo:
	ldapie --demo

# Run pylint
lint:
	pylint --rcfile=.pylintrc src/ldapie

# Run flake8
flake:
	flake8 src tests scripts

# Run mypy
typecheck:
	cd src && PYTHONPATH=. mypy --config-file=../mypy.ini ldapie

# Clean up temporary files and builds
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -not -path './.venv/*' -not -path './venv/*' -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './.venv/*' -not -path './venv/*' -delete

# Build distribution packages (sdist and wheel)
dist:
	python -m build

# Sort imports, then format code with Black
format:
	isort --profile black src tests scripts
	black src tests scripts

# Help
help:
	@echo "Available targets:"
	@echo "  setup             - Create .venv and install the package with dev extras"
	@echo "  install           - Install the package in development mode"
	@echo "  test              - Run tests with pytest"
	@echo "  demo              - Run the demo with mock LDAP server"
	@echo "  clean             - Clean up temporary files and builds"
	@echo "  dist              - Build sdist and wheel (python -m build)"
	@echo "  lint              - Run pylint on src/ldapie"
	@echo "  flake             - Run flake8 on src, tests and scripts"
	@echo "  typecheck         - Run mypy type checking"
	@echo "  format            - Sort imports with isort and format with Black"

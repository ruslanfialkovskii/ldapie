.PHONY: setup install test demo clean

# Default target
all: install

# Setup development environment
setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -e .

# Install the package
install:
	pip install -e .

# Run tests
test:
	pytest

# Run the demo
demo:
	python tests/demo.py

# Run the enhanced demo
demo-enhanced:
	python tests/enhanced_demo.py

# Install shell completion for zsh
install-completion:
	mkdir -p ~/.zsh/completion
	cp completion.zsh ~/.zsh/completion/_ldapie
	@echo "Add the following to your ~/.zshrc if you haven't already:"
	@echo "fpath=(~/.zsh/completion \$$fpath)"
	@echo "autoload -Uz compinit && compinit"

# Clean up temporary files and builds
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf tests/__pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# Build distribution packages
dist:
	python setup.py sdist bdist_wheel

# Check for lint issues
lint:
	flake8 src tests

# Format code with Black
format:
	black src tests

# Generate documentation
docs:
	cd docs && make html

# Help
help:
	@echo "Available targets:"
	@echo "  setup             - Set up development environment"
	@echo "  install           - Install the package in development mode"
	@echo "  test              - Run tests"
	@echo "  demo              - Run the demo with mock LDAP server"
	@echo "  demo-enhanced     - Run the enhanced demo with interactive mock LDAP server"
	@echo "  install-completion - Install shell completion for zsh"
	@echo "  clean             - Clean up temporary files and builds"
	@echo "  dist              - Build distribution packages"
	@echo "  lint              - Check for lint issues"
	@echo "  format            - Format code with Black"
	@echo "  docs              - Generate documentation"

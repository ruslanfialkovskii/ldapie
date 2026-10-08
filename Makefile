.PHONY: all setup install test demo clean lint flake typecheck format dist help \
	install-completion install-completion-zsh install-completion-bash install-completion-fish

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

# Install shell completion for zsh
install-completion-zsh:
	mkdir -p ~/.zsh/completion
	cp completion.zsh ~/.zsh/completion/_ldapie
	@echo "Add the following to your ~/.zshrc if you haven't already:"
	@echo "fpath=(~/.zsh/completion \$$fpath)"
	@echo "autoload -Uz compinit && compinit"

# Install shell completion for bash
install-completion-bash:
	mkdir -p ~/.bash_completion.d
	cp completion.bash ~/.bash_completion.d/ldapie
	@echo "Add the following to your ~/.bashrc if you haven't already:"
	@echo "source ~/.bash_completion.d/ldapie"

# Install shell completion for fish
install-completion-fish:
	mkdir -p ~/.config/fish/completions
	cp completion.fish ~/.config/fish/completions/ldapie.fish
	@echo "Fish completion installed to ~/.config/fish/completions/ldapie.fish"

# Install shell completion for all supported shells
install-completion: install-completion-zsh install-completion-bash install-completion-fish
	@echo "Completion files installed for zsh, bash, and fish shells."

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
	@echo "  install-completion - Install shell completion for all supported shells"
	@echo "  install-completion-zsh - Install shell completion for zsh"
	@echo "  install-completion-bash - Install shell completion for bash"
	@echo "  install-completion-fish - Install shell completion for fish"
	@echo "  clean             - Clean up temporary files and builds"
	@echo "  dist              - Build sdist and wheel (python -m build)"
	@echo "  lint              - Run pylint on src/ldapie"
	@echo "  flake             - Run flake8 on src, tests and scripts"
	@echo "  typecheck         - Run mypy type checking"
	@echo "  format            - Sort imports with isort and format with Black"

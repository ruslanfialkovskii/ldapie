.PHONY: setup install test demo clean lint

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
	python ./tests/test_completion.py
	python ./tests/test_context_help.py
	python -m unittest discover -s tests -p "*.py" -v

# Run the demo
demo:
	python tests/demo.py

# Run lint checks
lint:
	pylint --rcfile=.pylintrc ./src/ldapie
	pylint --rcfile=.pylintrc ./ldapie
flake:
	flake8 src tests

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
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf tests/__pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# Build distribution packages
dist:
	python setup.py sdist bdist_wheel

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
	@echo "  install-completion - Install shell completion for all supported shells"
	@echo "  install-completion-zsh - Install shell completion for zsh"
	@echo "  install-completion-bash - Install shell completion for bash"
	@echo "  install-completion-fish - Install shell completion for fish"
	@echo "  clean             - Clean up temporary files and builds"
	@echo "  dist              - Build distribution packages"
	@echo "  lint              - Check for lint issues"
	@echo "  format            - Format code with Black"
	@echo "  docs              - Generate documentation"

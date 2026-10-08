## Development and Contributing

### Development Setup

To set up LDAPie for development:

```bash
# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in develop mode with the dev tools (pytest, black, isort, flake8, pylint, mypy)
pip install -e '.[dev]'
```

With [mise](https://mise.jdx.dev), `mise run install` does the same in `.venv`.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=ldapie tests/
```

Tests use an in-memory ldap3 `MOCK_SYNC` server with the OpenLDAP schema
(fixtures in `tests/conftest.py`), and run with `HOME` and the working
directory pointed at a temporary directory, so they never touch your real
history or config files.

### Code Style

LDAPie follows PEP 8 style guidelines with some adjustments defined in the pyproject.toml file:

```bash
# Check code formatting and import order (CI fails on these)
black --check src tests scripts
isort --check-only --profile black src tests scripts

# Fix code formatting
isort --profile black src tests scripts
black src tests scripts

# Run linting (flake8 is blocking in CI, pylint is advisory)
flake8 src tests scripts
pylint --rcfile=.pylintrc src/ldapie
```

### Type Checking

LDAPie uses mypy for static type checking:

```bash
# Run type checking
make typecheck
```

`mypy.ini` holds the type-checking configuration; CI fails on mypy errors.

### Release Process

LDAPie uses an automated release workflow built with GitHub Actions.

#### Creating a New Release

##### Option 1: Using GitHub Actions (Recommended)

1. Navigate to the [Actions tab](https://github.com/ruslanfialkovskii/ldapie/actions) in the GitHub repository
2. Select the "LDAPie Release Workflow (Improved)" workflow
3. Click "Run workflow" and fill in the details:
   - Release type (patch, minor, major)
   - Optional version number (or leave empty for auto-increment)
   - Draft or pre-release options
   - Custom changelog entry (optional)

The workflow will:
- Validate the new version
- Update version in source files
- Update the CHANGELOG.md
- Run tests across multiple Python versions
- Create GitHub release with release notes
- Publish to PyPI
- Build and push Docker images
- Update documentation references

##### Option 2: Using the Local Script

For local development or when you need more control:

```bash
# Basic usage - bump patch version
python scripts/bump_version.py patch

# Bump minor version with dry run
python scripts/bump_version.py minor --dry-run

# Set an exact version
python scripts/bump_version.py patch --set-version 1.0.0

# Bump major version with auto-commit, tag, and push
python scripts/bump_version.py major --auto-commit --tag --push

# Add custom changelog message
python scripts/bump_version.py patch --changelog-message "Added new feature X and fixed bug Y" --tag
```

For complete details on the release process, see [RELEASE.md](RELEASE.md).

### Project Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [RELEASE.md](RELEASE.md) - Release process details
- [ROADMAP.md](ROADMAP.md) - Project roadmap and future plans

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

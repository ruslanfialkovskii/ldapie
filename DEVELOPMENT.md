## Development and Contributing

### Development Setup

To set up LDAPie for development:

```bash
# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies and develop mode
pip install -e .
pip install pytest pytest-cov black flake8 pylint
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/
```

### Code Style

LDAPie follows PEP 8 style guidelines with some adjustments defined in the pyproject.toml file:

```bash
# Check code formatting
black --check src tests

# Fix code formatting
black src tests

# Run linting
flake8 src tests
pylint src tests
```

### Type Checking

LDAPie uses mypy for static type checking:

```bash
# Run type checking
make typecheck
```

See [TYPING.md](TYPING.md) for guidance on fixing type errors and adding type annotations.
```

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

# Bump major version with auto-commit, tag, and push
python scripts/bump_version.py major --auto-commit --tag --push

# Add custom changelog message
python scripts/bump_version.py patch --changelog-message "Added new feature X and fixed bug Y" --tag
```

For complete details on the release process, see [RELEASE.md](RELEASE.md).

### Project Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [CONTAINER.md](CONTAINER.md) - Docker container usage
- [RELEASE.md](RELEASE.md) - Release process details
- [ROADMAP.md](ROADMAP.md) - Project roadmap and future plans

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Development and Contributing

### Development Setup

Dependencies are locked in `uv.lock`; [uv](https://docs.astral.sh/uv/) installs
exactly those versions into `.venv`:

```bash
# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Create .venv with the package (editable) and the dev tools (pytest, ruff, mypy)
make setup               # uv sync --frozen --extra dev
source .venv/bin/activate
```

With [mise](https://mise.jdx.dev), `mise install` provides Python and uv and
`mise run install` runs the sync; `mise run test`, `lint`, `typecheck`,
`format` and `audit` call the matching `make` targets.

Without uv, `pip install -e '.[dev]'` (or `make install`) installs the same
tools at whatever versions pip resolves; CI and the Docker image use the
lockfile.

### Running Tests

```bash
# Run all tests
make test                # pytest tests/

# Run tests with coverage (fails below 75%, the threshold in pyproject.toml)
make cov                 # pytest --cov=ldapie --cov-report=term-missing tests/
```

Tests use an in-memory ldap3 `MOCK_SYNC` server with the OpenLDAP schema
(fixtures in `tests/conftest.py`), and run with `HOME` and the working
directory pointed at a temporary directory, so they never touch your real
history or config files. The paged-search loop is tested with a fake
connection in `tests/test_search.py`, because `MOCK_SYNC` has no paging.

### Code Style

[Ruff](https://docs.astral.sh/ruff/) formats the code, sorts imports and lints
(it replaced black, isort, flake8 and pylint); its configuration is in
`pyproject.toml` under `[tool.ruff]`.

```bash
# Sort imports and format
make format

# Check import order and formatting without changing files (CI fails on these)
make format-check

# Lint (CI fails on findings)
make lint
```

`pre-commit install` sets up git hooks that run ruff and mypy before each
commit (configuration in `.pre-commit-config.yaml`).

### Type Checking

LDAPie uses mypy for static type checking:

```bash
# Run type checking
make typecheck
```

`mypy.ini` holds the type-checking configuration; CI fails on mypy errors.

### Dependencies

- Runtime dependencies are declared in `pyproject.toml`; `uv.lock` pins the
  whole tree. After changing `pyproject.toml`, run `make lock` and commit the
  lockfile. `make lock` runs `uv lock --no-config`, so settings from a
  user-level `~/.config/uv/uv.toml` (such as `exclude-newer`) never leak into
  the shared lockfile; `make setup` uses `--frozen` for the same reason. CI
  installs with `--locked` and fails if the lock and `pyproject.toml` disagree.
- `make audit` checks the locked versions against known vulnerabilities with
  pip-audit (part of the `dev` extra); CI runs the same target.
- CI runs the Makefile targets (`make lint format-check typecheck audit` and
  `make cov`) through `uv run`, so what passes locally passes in CI.
- Dependabot (`.github/dependabot.yml`) opens pull requests for the lockfile,
  the SHA-pinned GitHub Actions and the digest-pinned Docker base images.

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
- Publish to PyPI (Trusted Publishing, see RELEASE.md)
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

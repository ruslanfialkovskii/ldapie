# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is LDAPie

A modern LDAP client CLI tool inspired by HTTPie. Built on `ldap3` + `click` + `rich`. Entry point: `ldapie.ldapie:cli`.

## Build & Development Commands

```bash
# Setup (.venv from uv.lock with the dev tools; pip install -e '.[dev]' is the unlocked fallback)
make setup && source .venv/bin/activate   # uv sync --frozen --extra dev

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_ldapcli_utils.py -v

# Run tests with coverage (fails below 75%)
pytest --cov=ldapie tests/

# Demo with mock LDAP server
make demo

# Linting & formatting (ruff replaced black, isort, flake8 and pylint)
make format          # ruff check --select I --fix; ruff format
make format-check    # CI-blocking, like lint and mypy
make lint            # ruff check src tests scripts

# Type checking (must run from src/ with PYTHONPATH)
cd src && PYTHONPATH=. mypy --config-file=../mypy.ini ldapie

# Dependencies: relock after editing pyproject.toml (uv lock --no-config, so a
# user-level ~/.config/uv/uv.toml never leaks into the lockfile); audit the locked tree
make lock
make audit
```

CI runs the same Makefile targets through `uv run --locked` (`make lint format-check typecheck audit`, `make cov`).

## Architecture

The source lives in `src/ldapie/` with a flat module layout. Version is defined in `__init__.py`.

**Core flow:** `ldapie.py` defines the Click CLI group and all commands. The `connection_options` decorator adds the shared connection flags, merges config-file defaults (`config.py`), and passes each command a ready `LdapConfig` (connection factory); commands then delegate to operation modules:

- `ldapie.py` — CLI commands, `LdapConfig` class, `connection_options` and `handle_connection_error` decorators, shell-completion setup, theme definitions. This is the largest module and acts as the hub. `LdapConfig.get_connection(get_info=...)` takes `NONE` for the write commands and LDIF export, which do not need the schema download; `ALL` where values are formatted or the schema is shown.
- `config.py` — loads `~/.config/ldapie/config.yaml` and `./.ldapie.yaml`. The project file is tightening-only: `theme`, and `use_ssl`/`starttls` set to `true`; everything else is ignored with a warning, and a notice names the keys it contributed.
- `search.py` — `iter_paged_search()` (generator, one page in memory, last page shrunk to the remaining `--limit`), `paged_search()` (its list form), `compare_entries()`.
- `entry_operations.py` — `delete_entry()` (recursive delete uses a paged subtree listing).
- `ldif_parser.py` — `parse_ldif()` for `import` and `add --ldif-file` (RFC 2849 content records).
- `schema.py` — schema browsing, object class exploration, `output_server_info_rich()`.
- `output.py` — formatters: `output_rich()`, `output_json()` and `output_ldif()` (both accept any iterable and stream; LDIF from raw values via `ldif_lines()`), `output_csv()`, tree view. `safe_text()` = `sanitize_text()` (control characters become `\xNN`) + Rich `escape`; everything from the server, including error messages and `conn.result`, goes through it before `console.print`. CSV cells and header names that look like formulas get a leading `'`. `--output` files are written through `_atomic_write()` (temp file, 0600, `os.replace`).
- `interactive.py` — `LDAPShell(cmd.Cmd)` for interactive mode with readline history; it owns a `QueryHistory` and `TabCompletion`.
- `demo/` — `ldapie --demo`: the scripted tour (`tour.py`) and its mock LDAP server (`mock_server.py`).

**Help & UX layer** (runs alongside core):
- `help_context.py` — `HelpContext` (one per shell) tracking command history, errors and session state, and `CommandValidator` behind the shell's `validate`. `COMMAND_PATTERNS` describes the shell's commands (syntax, examples, tips), not the CLI's. `parse_connect_args()` returns a validated `ConnectArgs` and is shared by the shell's `connect`, its validator and (for the option list) tab completion.
- `help_overlay.py` — `?`-triggered help overlay using HelpContext.
- `tab_completion.py` — `TabCompletion` and `QueryHistory` for dynamic shell completion.
- `rich_formatter.py` — custom Rich formatting for styled CLI help.

**Import pattern:** Modules use plain relative imports. `ldapie.ldapie` imports most modules, so modules it imports (`interactive.do_connect`, `rich_formatter.get_console`) import it back lazily inside functions. Status messages go to `err_console` (stderr); results go to `console` (stdout).

**Tests:** `tests/conftest.py` provides a `MOCK_SYNC` server with the OpenLDAP offline schema (`ldap_server`), a `mock_ldap` fixture that routes `LdapConfig.get_connection` to it, and an autouse fixture that points `HOME` and the working directory at a temp dir. `MOCK_SYNC` has no paging control, so `tests/test_search.py` drives the paging loop with a fake connection.

**Supply chain:** `uv.lock` pins the dependency tree (`pyasn1>=0.6.4` is a deliberate floor: it decodes every server response). GitHub Actions are SHA-pinned and the Dockerfile's base images digest-pinned; Dependabot updates all three. PyPI publishing uses Trusted Publishing (see RELEASE.md).

## Code Style

- Ruff: line-length 88, target Python 3.10, rules E/F/W/I/B/PLE/PLW with E501 ignored; `ruff format` for layout
- Type hints expected; mypy configured with `strict_optional`, `check_untyped_defs`
- snake_case for functions/variables, CamelCase for classes, kebab-case for CLI options

## Commit Style

Short imperative messages, often with PR numbers: `Add type checking support with mypy (#17)`. Version bumps are explicit commits.

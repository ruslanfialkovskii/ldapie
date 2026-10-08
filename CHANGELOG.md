# Changelog

All notable changes to the LDAPie project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Unreleased

### Security
- STARTTLS now upgrades the connection before the bind; credentials were sent in clear text before.
- Interactive `connect --ssl` verifies certificates (it used ldap3's no-verify default); `connect` gained `--starttls` and `--no-verify`.
- `--debug` no longer prints the password.
- `./.ldapie.yaml` cannot set `no_verify`; only the user config file and the command line can.
- The release workflow passes its inputs through environment variables instead of interpolating them into shell scripts.

### Fixed
- `modify --add/--replace/--delete` built changes in a format ldap3 rejects (`invalid change list`).
- `search --output FILE` crashed with "I/O operation on closed file" in the default format.
- `schema HOST CLASS` and `schema --attr NAME` crashed on ldap3 schema objects.
- `--json` crashed on timestamp attributes (`datetime is not JSON serializable`).
- `import` stopped at the first failed entry; it now attempts every entry and exits 1 if any failed.
- The interactive shell crashed on `base`, reported errors after successful `connect`/`search`, looped forever at end of input, and exited on any command error.
- `?` context help in the shell was never triggered.
- `ldapie --show-completion`, `--install-completion` and `--demo` failed with "Missing command".
- `rename` could not keep the old RDN; use `--keep-old-rdn`.
- LDIF export uses raw values (binary and timestamps survive a round trip), base64-encodes non-ASCII DNs and folds long lines.
- The LDIF parser handles folded lines, `version: 1`, comments and binary values, and rejects unsupported records instead of guessing.
- LDAP values containing `[brackets]` no longer break or disappear in Rich output and help text.
- `add --ldif-file` was ignored.
- Literal `\n` sequences in shell output; tab completion treated the letters `t` and `n` as word separators.

### Changed
- `search`, `export` and recursive `delete` use paged results (500 per page; `search --page-size 0` turns paging off), so server size limits no longer truncate results silently.
- `delete --recursive` asks for confirmation; `--yes` skips it.
- Status messages go to stderr, so `--json`, `--ldif` and `--csv` output can be piped.
- Connection flags are now pairs (`--ssl/--no-ssl`, `--starttls/--no-starttls`, `--verify/--no-verify`) so config-file defaults can be overridden; `--no-verify` works as before.
- Config file settings (`~/.config/ldapie/config.yaml`, `./.ldapie.yaml`) are now applied as defaults.
- The demo moved into the package (`ldapie.demo`), so `ldapie --demo` works from pip and Docker installs.
- Dependencies reduced to ldap3, rich, click (>= 8.0) and pyyaml; packaging is defined in `pyproject.toml` only (setup.py removed).
- CI fails on black, isort, flake8 and mypy errors and tests Python 3.10-3.13; the Docker image runs as a non-root user.

# 0.1.4 (2025-05-22)

### Added
- 

### Changed
- 

### Fixed
- 

# 0.1.3 (2025-05-22)

### Added
- 

### Changed
- 

### Fixed
- 

## 0.1.1 (2025-05-22)

### Added

- Container usage documentation
- Installation instructions for pip
- Automated release workflow
- CHANGELOG to track version changes

### Fixed

- Package import issues when installed via pip
- Fixed dependency installation in setup.py

### Changed

- Improved error handling in CLI
- Enhanced release documentation

## 0.1.0 (2025-05-01)

### Added

- Initial release of LDAPie
- Core LDAP operations: search, add, modify, delete, rename
- Multiple output formats: Rich text, JSON, LDIF, CSV, tree view
- Interactive mode with terminal UI
- Docker container support
- Demo mode with mock LDAP server
- Shell completion for Bash, Zsh, and Fish
- Context-sensitive help system

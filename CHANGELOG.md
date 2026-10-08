# Changelog

All notable changes to the LDAPie project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Security
- `./.ldapie.yaml` (the project-level config file, read from the current directory) could point `ldapie interactive` at a server of its choosing with `default_host` and `default_username`, so a cloned repository could collect the user's `LDAP_PASSWORD`; it could also turn `use_ssl` and `starttls` off over the user config. The project file may now set only `theme`, `use_ssl: true` and `starttls: true`; everything else is ignored with a warning, and a notice on stderr names the keys it contributed.
- Control characters in attribute values (terminal escape sequences, C1 controls) reached the terminal through the table, tree and CSV output; they are now printed as `\xNN`. JSON and LDIF output were already safe.
- CSV cells that a spreadsheet would run as a formula (starting with `=`, `+`, `-` or `@`) get a leading `'`.
- `pyasn1>=0.6.4` is now a direct requirement: ldap3 only asks for `>=0.4.6`, and older versions can be made to hang by a hostile server while decoding its responses (CVE-2026-30922, CVE-2026-59884, CVE-2026-59885, CVE-2026-59886).
- The server name is sent in the TLS handshake (SNI), so servers that host several names present the right certificate instead of forcing `--no-verify`.
- Error messages that quote the server (LDAP diagnostic messages, `conn.result`) and config-file warnings that quote a key are sanitized like attribute values before they reach the terminal.
- CSV header cells (attribute names) are sanitized and formula-guarded like the data cells; LDIF output skips an attribute whose name is not a valid attribute description, with a comment naming it.
- `--output` files are written to a temporary file and renamed into place when complete, so a failed streamed export leaves no truncated file and keeps the previous one. They are created readable by their owner only.
- `--ca-cert` given on the command line without `--ssl` or `--starttls` is an error instead of being silently ignored; with `--no-verify` it prints a warning.
- GitHub Actions are pinned to commit SHAs (current Node 24 releases; Node 20 was removed from the runners in September 2026), the Docker base images to digests, and PyPI publishing uses Trusted Publishing instead of a stored API token. Dependabot keeps all three current with a seven-day cooldown, and CI audits the locked dependencies with pip-audit from the lockfile.

### Added
- `--ca-cert FILE` (and `ca_cert` in the user config file) verifies the server certificate against your own CA bundle; the interactive `connect` takes it too.
- `--timeout SECONDS` (and `timeout` in the user config file) bounds the connection and every server response; a stalled server no longer hangs a command forever.
- `uv.lock` pins the dependency tree for development, CI and the Docker image; `make audit` checks it for known vulnerabilities.

### Changed
- `export` writes entries as they arrive, page by page, instead of holding the whole result in memory.
- `search --limit N` asks the server for at most N entries even with paging on; it used to download a full page and discard the rest.
- The write commands (`add`, `modify`, `delete`, `rename`, `import`) and `export --format ldif` no longer download the server schema when they connect.
- Ruff replaced black, isort, flake8 and pylint; `make format`, `make format-check` and `make lint` run it. The `dev` extra was split into `test` (pytest) and `dev` (plus ruff, mypy, pip-audit, twine). CI runs the Makefile targets, so local and CI checks are the same commands.
- `make lock` (`uv lock --no-config`) regenerates the lockfile without settings from a user-level uv config; `make setup` installs with `--frozen` and CI with `--locked`.
- The Docker image is built in two stages from `uv.lock` with compiled bytecode; the final image carries only the virtual environment. CI builds and smoke-tests the image on pull requests too.
- The shell's `connect` validates the port range and the bind DN before connecting, as `validate connect` already did.
- README rewritten around the 0.2.0 command set.
- `.gitignore` no longer ignores every `*.json`, `*.ldif` and `*.csv` file.

### Fixed
- The interactive shell's `?` context help, `help <command>` and `validate` described the command-line commands (`search <host> <base_dn>`) instead of the shell's own (`search [filter] [attributes...]`).
- `validate connect --ssl` (options without a host) crashed instead of reporting the missing host.
- The demo's interactive-shell example showed `cd`, `ls` and `show` commands that do not exist.
- `LICENSE` contains the full GPL-3.0 text instead of a stub.

### Removed
- `requirements.txt` (it duplicated `pyproject.toml`), `.flake8` and `.pylintrc`.
- The hand-written `completion.bash`, `completion.zsh` and `completion.fish` scripts and the `make install-completion*` targets: they were out of date and overrode Click's own completion. Use `ldapie --install-completion`.

## 0.2.0 (2026-10-08)

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

## 0.1.4 (2025-05-22)

### Fixed
- Release workflow fixes.

## 0.1.3 (2025-05-22)

### Fixed
- Release workflow fixes.

## 0.1.2 (2025-05-22)

### Added
- Automated release workflow and `scripts/bump_version.py`.
- DEVELOPMENT.md and RELEASE.md.

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

# LDAPie Roadmap

Status as of 0.2.0 (October 2026). What the tool does today is described in
[README.md](README.md); changes per version are in [CHANGELOG.md](CHANGELOG.md).

## Done

- Commands: `search`, `info`, `compare`, `schema`, `add`, `modify`, `delete`,
  `rename`, `export`, `import`
- Output formats: Rich tables, JSON, LDIF, CSV, tree
- Paged results, LDAPS and STARTTLS with certificate verification, config files
- Interactive shell with tab completion, query history and context help
- Shell completion for bash, zsh and fish (`ldapie --install-completion`)
- Demo mode against a mock LDAP server (`ldapie --demo`)
- PyPI package, multi-architecture Docker image, automated release workflow
- CI: ruff (lint, imports, formatting), mypy and a dependency audit are
  blocking; tests run on Python 3.10 to 3.13 against `uv.lock`

## Ideas, not scheduled

- Password change command using the Password Modify extended operation
- Template-based entry creation
- Richer interactive shell (entry browsing, forms)
- Linux distribution packages (deb, rpm)

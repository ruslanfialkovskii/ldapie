# LDAPie

A command-line LDAP client in the spirit of [HTTPie](https://httpie.io): short commands,
readable output, and formats you can pipe. Built on
[ldap3](https://github.com/cannatag/ldap3), [Click](https://click.palletsprojects.com)
and [Rich](https://github.com/Textualize/rich).

[![PyPI](https://img.shields.io/pypi/v/ldapie.svg)](https://pypi.org/project/ldapie/)
[![Python](https://img.shields.io/pypi/pyversions/ldapie.svg)](https://pypi.org/project/ldapie/)
[![CI](https://github.com/ruslanfialkovskii/ldapie/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ruslanfialkovskii/ldapie/actions/workflows/ci-cd.yml)
[![Docker](https://img.shields.io/docker/v/ruslanfialkovsky/ldapie?sort=semver&label=docker)](https://hub.docker.com/r/ruslanfialkovsky/ldapie)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

```bash
pip install ldapie

ldapie search ldap.example.com "dc=example,dc=com" "(objectClass=person)" -a cn -a mail
```

```text
╭─ uid=mwhite,ou=people,dc=example,dc=com ───╮
│ ╭───────────┬────────────────────────╮     │
│ │ Attribute │ Value                  │     │
│ ├───────────┼────────────────────────┤     │
│ │ cn        │ Mike White             │     │
│ │ mail      │ mike.white@example.com │     │
│ ╰───────────┴────────────────────────╯     │
╰────────────────────────────────────────────╯
```

Add `--json`, `--ldif`, `--csv` or `--tree` to change the format. Status messages go
to stderr, so the result can be piped as-is:

```bash
ldapie search ldap.example.com "dc=example,dc=com" "(objectClass=person)" --json | jq '.[].mail'
```

No directory at hand? `ldapie --demo` runs a scripted tour against an in-memory mock
LDAP server.

## Features

- `search`, `info`, `compare`, `schema`, `add`, `modify`, `delete`, `rename`,
  `export` and `import`, plus an interactive shell
- Output as Rich tables (default), JSON, LDIF, CSV or a tree
- Paged results by default, so server size limits do not truncate silently
- LDAPS and STARTTLS, with certificate verification on by default
- Passwords from a prompt or `LDAP_PASSWORD`; never required on the command line
- Defaults from a user-level and a per-project config file
- Interactive shell with tab completion, query history and context help
- Shell completion for bash, zsh and fish
- Dark and light themes

## Installation

LDAPie needs Python 3.10 or newer. Its dependencies (`ldap3`, `rich`, `click`,
`pyyaml`) install from PyPI without any system packages.

```bash
# PyPI (a virtual environment or pipx is recommended)
pip install ldapie

# Docker
docker run --rm ruslanfialkovsky/ldapie:latest --help

# From source
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie
pip install .
```

In a source checkout, `./ldapie` runs the code in `src/` without installing
the package (the dependencies must be installed).

```bash
ldapie --version
ldapie --demo
```

## Usage

```text
ldapie search      <host> <base_dn> [<filter>] [options]
ldapie info        <host> [options]
ldapie compare     <host> <dn1> <dn2> [options]
ldapie schema      <host> [<object_class>] [options]
ldapie add         <host> <dn> [options]
ldapie modify      <host> <dn> [options]
ldapie delete      <host> <dn> [options]
ldapie rename      <host> <dn> <new_rdn> [options]
ldapie export      <host> <base_dn> [<filter>] --output <file> [options]
ldapie import      <host> <ldif_file> [options]
ldapie interactive [options]
```

`ldapie COMMAND --help` lists the options of a command. `ldapie --debug` prints
stack traces on errors (passwords are redacted).

### Connection options

Every command that connects takes the same options:

| Option | Meaning |
|---|---|
| `-u, --username` | Bind DN (omit for an anonymous bind) |
| `-p, --password` | Password; prefer `LDAP_PASSWORD` or the prompt (see below) |
| `--ssl / --no-ssl` | Use LDAPS (default port 636) |
| `--starttls / --no-starttls` | Upgrade the connection with STARTTLS before binding |
| `--verify / --no-verify` | Verify the server certificate (default: verify) |
| `--port` | Port (default: 389, or 636 with `--ssl`) |

With STARTTLS the connection is upgraded before the bind, so credentials never
travel in clear text. `--no-verify` prints a warning every time it is used.

### Passwords

When `-u` is given without `-p`, LDAPie reads `LDAP_PASSWORD` from the
environment and otherwise prompts for the password. Passing `-p` on the command
line works but prints a warning, because the password shows up in the process
list and in shell history.

```bash
# Prompted for the password
ldapie search ldap.example.com "dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# From the environment, e.g. in scripts
read -rs LDAP_PASSWORD && export LDAP_PASSWORD
ldapie search ldap.example.com "dc=example,dc=com" -u "cn=admin,dc=example,dc=com"
```

### search

```bash
# Whole subtree, all attributes (the default filter is "(objectClass=*)")
ldapie search ldap.example.com "dc=example,dc=com"

# Filter, selected attributes, scope and limit
ldapie search ldap.example.com "dc=example,dc=com" "(uid=j*)" -a uid -a mail --scope one --limit 10

# Other formats; --output writes to a file instead of stdout
ldapie search ldap.example.com "dc=example,dc=com" --ldif --output people.ldif
ldapie search ldap.example.com "dc=example,dc=com" --tree

# Paging: 500 entries per page by default; 0 turns it off
ldapie search ldap.example.com "dc=example,dc=com" --page-size 100
```

`--scope` is `base`, `one` or `sub` (default). If the server still cuts the
results short, LDAPie prints a warning on stderr.

### info and schema

```bash
# Vendor, LDAP versions, supported controls and extensions, naming contexts
ldapie info ldap.example.com
ldapie info ldap.example.com --json

# All object classes, one object class, or one attribute type
ldapie schema ldap.example.com
ldapie schema ldap.example.com inetOrgPerson
ldapie schema ldap.example.com --attr mail
```

### compare

```bash
# Attribute-by-attribute diff of two entries; -a restricts the attributes
ldapie compare ldap.example.com "uid=alice,ou=people,dc=example,dc=com" "uid=bob,ou=people,dc=example,dc=com" -a mail -a title
```

### add

Attributes can come from `-c/--class` and `-a/--attr` options, a one-entry
LDIF file, a JSON object, or any mix of those.

```bash
ldapie add ldap.example.com "uid=carol,ou=people,dc=example,dc=com" \
  -c inetOrgPerson -a uid=carol -a cn="Carol Jones" -a sn=Jones -u "cn=admin,dc=example,dc=com"

ldapie add ldap.example.com "uid=carol,ou=people,dc=example,dc=com" --ldif-file carol.ldif -u "cn=admin,dc=example,dc=com"

# group.json: {"objectClass": ["groupOfNames"], "cn": "ops", "member": ["uid=carol,ou=people,dc=example,dc=com"]}
ldapie add ldap.example.com "cn=ops,ou=groups,dc=example,dc=com" --json-file group.json -u "cn=admin,dc=example,dc=com"
```

### modify

```bash
# Add a value, replace all values, delete one value, delete a whole attribute
ldapie modify ldap.example.com "uid=carol,ou=people,dc=example,dc=com" --add mail=carol@example.com -u "cn=admin,dc=example,dc=com"
ldapie modify ldap.example.com "uid=carol,ou=people,dc=example,dc=com" --replace title=Engineer -u "cn=admin,dc=example,dc=com"
ldapie modify ldap.example.com "uid=carol,ou=people,dc=example,dc=com" --delete mail=old@example.com -u "cn=admin,dc=example,dc=com"
ldapie modify ldap.example.com "uid=carol,ou=people,dc=example,dc=com" --delete mobile -u "cn=admin,dc=example,dc=com"

# Several changes in one operation; repeated --add values are all added
ldapie modify ldap.example.com "uid=carol,ou=people,dc=example,dc=com" \
  --add mail=a@example.com --add mail=b@example.com --replace title=Manager -u "cn=admin,dc=example,dc=com"
```

A bare `--replace name` clears the attribute. `--file changes.json` applies
changes in ldap3's format instead, for example
`{"title": [["MODIFY_REPLACE", ["Manager"]]]}`.

### delete and rename

```bash
ldapie delete ldap.example.com "uid=carol,ou=people,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Delete a subtree; asks for confirmation unless --yes is given
ldapie delete ldap.example.com "ou=old,dc=example,dc=com" --recursive --yes -u "cn=admin,dc=example,dc=com"

# Change the RDN
ldapie rename ldap.example.com "uid=carol,ou=people,dc=example,dc=com" "uid=cjones" -u "cn=admin,dc=example,dc=com"

# Move to another parent; --keep-old-rdn keeps the old RDN value as an attribute
ldapie rename ldap.example.com "uid=carol,ou=people,dc=example,dc=com" "uid=carol" --parent "ou=admins,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"
```

### export and import

```bash
# Subtree to LDIF (default) or JSON; binary values are base64-encoded
ldapie export ldap.example.com "ou=people,dc=example,dc=com" --output people.ldif
ldapie export ldap.example.com "ou=people,dc=example,dc=com" "(objectClass=person)" --format json --output people.json

# Every entry is attempted; exits with status 1 if any entry failed
ldapie import ldap.example.com people.ldif -u "cn=admin,dc=example,dc=com"
```

`import` reads LDIF content records and `changetype: add` records, including
folded lines, comments and `::` base64 values. Other change types and `:<` URL
values are rejected with the offending line number.

### Interactive shell

```bash
ldapie interactive
ldapie interactive --host ldap.example.com -u "cn=admin,dc=example,dc=com" --base "dc=example,dc=com"
```

Inside the shell:

```text
connect host [port] [bind_dn] [--ssl] [--starttls] [--no-verify]
base <dn>                          set the base DN (shown in the prompt)
search [filter] [attribute...]     search below the base DN
info                               server information
schema [objectClass|--attr name]   browse the schema
validate <command>                 check a command without running it
suggest                            context-aware suggestions
history [search|base|host]         recent filters, base DNs and hosts
help [command]                     help; end a partial command with ? for context help
exit, quit, Ctrl-D                 leave the shell
```

The shell has tab completion and keeps readline history in `~/.ldapie_history`
and query history in `~/.ldapie_query_history.json`. Errors never end the
session.

## Output formats

| Flag | Format |
|---|---|
| (none) | One Rich panel per entry with an attribute table |
| `--json` | Array of objects with `dn`; single-valued attributes are scalars, multi-valued ones arrays. Binary values are `base64:...` strings, timestamps ISO 8601 |
| `--ldif` | RFC 2849 from the raw values: `version: 1`, `::` base64 for binary or non-ASCII values, lines folded at 76 characters. Round-trips through `import` |
| `--csv` | One column per attribute seen in any entry, plus `dn`; multiple values joined with `;` |
| `--tree` | Entry hierarchy below the base DN with attributes |

Results go to stdout and status messages to stderr. Non-TTY output has no
color codes, so the default format is readable in a file or a pager too.

## Configuration file

Defaults for the connection options live in `~/.config/ldapie/config.yaml`
(user level) and `./.ldapie.yaml` (project level, read from the current
directory). The project file overrides the user file, and options on the
command line override both.

```yaml
default_host: ldap.example.com   # used by `ldapie interactive` without --host
default_username: cn=admin,dc=example,dc=com
use_ssl: false
starttls: true
port: 389
theme: dark                      # or light
no_verify: false                 # user-level file only
```

`no_verify` is ignored in `./.ldapie.yaml`, with a warning: a project file can
come from a cloned repository and must not be able to turn off certificate
checks. Unknown keys and values of the wrong type are skipped with a warning.

## Themes

The color theme comes from `search --theme`, then the `LDAPIE_THEME`
environment variable, then `theme:` in the config file.

```bash
LDAPIE_THEME=light ldapie search ldap.example.com "dc=example,dc=com"
```

## Shell completion

```bash
# Detects $SHELL (bash, zsh or fish), writes the completion script and, for
# bash and zsh, adds a setup line to ~/.bashrc or ~/.zshrc
ldapie --install-completion

# Print the line to add to your shell config instead
ldapie --show-completion
```

Restart the shell afterwards.

## Docker

The image `ruslanfialkovsky/ldapie` is published for `linux/amd64` and
`linux/arm64` with the tags `latest` and `x.y.z` (one per release). It runs as
an unprivileged user with `ldapie` as the entrypoint, so arguments are passed
exactly as to the installed command.

```bash
docker run --rm ruslanfialkovsky/ldapie:latest search ldap.example.com "dc=example,dc=com" --json

# Pass the password through the environment
docker run --rm -e LDAP_PASSWORD ruslanfialkovsky/ldapie:latest \
  search ldap.example.com "dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Interactive shell needs a TTY
docker run --rm -it ruslanfialkovsky/ldapie:latest interactive --host ldap.example.com

# Read or write local files through a mount; use your own UID to write to it
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/data ruslanfialkovsky/ldapie:latest \
  export ldap.example.com "dc=example,dc=com" --output /data/backup.ldif
```

`LDAPIE_THEME` and `LDAP_PASSWORD` work in the container as they do locally.
To build the image yourself, run `docker build -t ldapie .` in a checkout.

## Development

Set-up, tests, linting and the release process are described in
[DEVELOPMENT.md](https://github.com/ruslanfialkovskii/ldapie/blob/main/DEVELOPMENT.md).
Changes per version are listed in
[CHANGELOG.md](https://github.com/ruslanfialkovskii/ldapie/blob/main/CHANGELOG.md).

```bash
pip install -e '.[dev]'
pytest tests/
```

## License

GPL-3.0. See [LICENSE](https://github.com/ruslanfialkovskii/ldapie/blob/main/LICENSE).

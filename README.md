# LDAPie

A modern LDAP client CLI tool inspired by [HTTPie](https://httpie.io), using [ldap3](https://github.com/cannatag/ldap3) for LDAP operations and [Rich](https://github.com/Textualize/rich) for beautiful terminal output.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

LDAPie makes LDAP operations more accessible and intuitive with a modern command-line interface, beautiful output, and comprehensive features for both beginners and LDAP experts.

## Features

- Beautiful, colorized output with syntax highlighting
- Intuitive command-line interface
- LDAP operations: search, add, modify, delete, and rename entries
- Interactive mode with terminal UI interface
- Multiple output formats: Rich text, JSON, LDIF, CSV, and tree view
- Anonymous and authenticated connections
- Support for SSL/TLS connections
- Certificate-based authentication
- Multiple search scope options (base, one, sub)
- Theme support with light and dark modes
- Secure password handling options
- Shell completion for Bash, Zsh, and Fish
- Directory navigation in interactive mode
- Context-sensitive help system with smart suggestions

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Create a virtual environment and install LDAPie with its dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Try the automated demo with a mock LDAP server
ldapie --demo

# Install shell completion (optional)
./ldapie --install-completion
```

The automated demo will showcase all major features of LDAPie using a mock LDAP server, so you don't need a real LDAP server to get started.

## Installation

### Option 1: Install from PyPI

The easiest way to install LDAPie is via pip from PyPI:

```bash
# Install globally (may require sudo)
pip install ldapie

# Install in user space
pip install --user ldapie

# Install in a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install ldapie
```

After installation, you can use the `ldapie` command directly:

```bash
# Check if installation was successful
ldapie --version

# Run the demo to explore features
ldapie --demo
```

### Option 2: Install from Source

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Install from source
pip install .

# Alternatively, install in development mode with the dev tools
pip install -e '.[dev]'
```

### Option 3: Run From a Checkout Without Installing

The `ldapie` script in the repository root runs the sources in `src/`
(the dependencies must be installed, e.g. `pip install -r requirements.txt`):

```bash
./ldapie search localhost "dc=example,dc=com"
```

### Option 4: Using Docker

```bash
# Build the Docker image
docker build -t ldapie .

# Run using Docker
docker run -it ldapie search ldap.example.com "dc=example,dc=com"
```

### Dependencies

LDAPie requires the following Python packages, which will be automatically installed by pip:

- ldap3 >= 2.9, < 3.0: For LDAP functionality
- rich >= 12.0.0: For beautiful terminal output
- click >= 8.0: For command-line interface
- pyyaml >= 6.0: For configuration files

### System Requirements

- Python 3.10 or newer
- For LDAPS (SSL/TLS) support, OpenSSL libraries may be required

## Shell Completion

LDAPie provides shell completion for Bash, Zsh, and Fish:

```bash
# Install shell completion for your $SHELL (writes the completion script
# and, for bash/zsh, adds a setup line to ~/.bashrc or ~/.zshrc)
ldapie --install-completion

# Show the line to add to your shell config instead
ldapie --show-completion
```

## Usage

LDAPie provides a command-line interface for LDAP operations:

```bash
ldapie search <host> <base_dn> [<filter>] [options]
ldapie info <host> [options]
ldapie compare <host> <dn1> <dn2> [options]
ldapie schema <host> [<object_class>] [options]
ldapie add <host> <dn> [options]
ldapie modify <host> <dn> [options]
ldapie delete <host> <dn> [options]
ldapie rename <host> <dn> <new_rdn> [options]
ldapie export <host> <base_dn> [<filter>] --output <file> [options]
ldapie import <host> <ldif_file> [options]
ldapie interactive [options]
```

Every command that connects accepts the same connection options:

| Option | Meaning |
|---|---|
| `-u, --username` | Bind DN (omit for an anonymous bind) |
| `-p, --password` | Password; prefer `LDAP_PASSWORD` or the prompt |
| `--ssl / --no-ssl` | Use LDAPS (default port 636) |
| `--starttls / --no-starttls` | Upgrade to TLS with STARTTLS before binding |
| `--verify / --no-verify` | Verify the server certificate (default: verify) |
| `--port` | Port (default: 389, or 636 with `--ssl`) |

Status messages go to stderr, so `--json`, `--ldif` and `--csv` output on
stdout can be piped (for example into `jq`).

## Configuration File

Defaults for the connection options can live in `~/.config/ldapie/config.yaml`
(user level) and `./.ldapie.yaml` (project level, read from the current
directory, takes precedence). Options given on the command line always win.

```yaml
default_host: ldap.example.com   # used by `ldapie interactive` without --host
default_username: cn=admin,dc=example,dc=com
use_ssl: false
starttls: true
port: 389
theme: dark                      # or light; LDAPIE_THEME overrides it
no_verify: false                 # user-level file only
```

`no_verify` is ignored in `./.ldapie.yaml`: a project file can come from a
cloned repository, and it must not be able to turn off certificate checks.
Unknown keys and values of the wrong type are skipped with a warning.

## Context-Sensitive Help System

LDAPie includes a comprehensive context-sensitive help system that provides smart suggestions based on your current context and command history:

- **Progressive Help**: In interactive mode, end a partial command with '?' to get context-specific help
- **Command Validation**: In interactive mode, `validate <command>` checks and previews a command without running it
- **Smart Suggestions**: Get intelligent recommendations based on your current operation context
- **"Did you mean...?"**: Get automatic corrections for mistyped commands
- **History-Aware Help**: Suggestions are informed by your previous commands and operations

Examples:

```bash
# Get help for a partial command (interactive mode)
ldapie> search ?

# Validate a command without executing it (interactive mode)
ldapie> validate search ldap.example.com "dc=example,dc=com"
```

## Usage Examples

### LDAP Search Operations

```bash
# Basic search
./ldapie search ldap.example.com "dc=example,dc=com"

# Search with filter
./ldapie search ldap.example.com "dc=example,dc=com" "(objectClass=person)"

# Authenticate with username and password
./ldapie search ldap.example.com "dc=example,dc=com" "(uid=admin)" -u "cn=admin,dc=example,dc=com" -p secret

# Specify attributes to retrieve
./ldapie search ldap.example.com "dc=example,dc=com" "(cn=*)" -a cn -a mail -a uid

# Use SSL/TLS
./ldapie search ldaps.example.com "dc=example,dc=com" --ssl

# Output in JSON format
./ldapie search ldap.example.com "dc=example,dc=com" --json

# Output in LDIF format
./ldapie search ldap.example.com "dc=example,dc=com" --ldif

# Output in CSV format
./ldapie search ldap.example.com "dc=example,dc=com" --csv

# Display results as a tree
./ldapie search ldap.example.com "dc=example,dc=com" --tree

# Secure password handling (will prompt for password)
./ldapie search ldap.example.com "dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Limit search results
./ldapie search ldap.example.com "dc=example,dc=com" --limit 10

# Results are paged (500 entries per page) so server size limits do not
# truncate them; change the page size or turn paging off
./ldapie search ldap.example.com "dc=example,dc=com" --page-size 100
./ldapie search ldap.example.com "dc=example,dc=com" --page-size 0

# Pipe JSON output (status messages go to stderr)
./ldapie search ldap.example.com "dc=example,dc=com" --json | jq '.[].dn'

# Save results to a file
./ldapie search ldap.example.com "dc=example,dc=com" --json --output results.json
```

### Get LDAP Server Information

```bash
# Get server information
./ldapie info ldap.example.com

# Authenticate to get server information
./ldapie info ldap.example.com -u "cn=admin,dc=example,dc=com" -p secret
```

### Compare Two LDAP Entries

```bash
# Compare two LDAP entries
./ldapie compare ldap.example.com "uid=user1,ou=people,dc=example,dc=com" "uid=user2,ou=people,dc=example,dc=com"

# Compare specific attributes
./ldapie compare ldap.example.com "uid=user1,ou=people,dc=example,dc=com" "uid=user2,ou=people,dc=example,dc=com" -a uid -a cn -a mail
```

### Get Schema Information

```bash
# Get a list of all object classes
./ldapie schema ldap.example.com

# Get information about a specific object class
./ldapie schema ldap.example.com person

# Get information about a specific attribute
./ldapie schema ldap.example.com --attr mail
```

### Add New LDAP Entry

```bash
# Add a simple entry
./ldapie add ldap.example.com "cn=newuser,ou=people,dc=example,dc=com" --class inetOrgPerson --attr cn=newuser --attr sn=User --attr uid=newuser -u "cn=admin,dc=example,dc=com"

# Add an entry whose attributes come from an LDIF file with one entry
./ldapie add ldap.example.com "cn=newuser,ou=people,dc=example,dc=com" --ldif-file newuser.ldif -u "cn=admin,dc=example,dc=com"

# Add an entry whose attributes come from a JSON object
./ldapie add ldap.example.com "cn=newgroup,ou=groups,dc=example,dc=com" --json-file group.json -u "cn=admin,dc=example,dc=com"
```

### Modify LDAP Entry

```bash
# Add a value to an attribute
./ldapie modify ldap.example.com "cn=user1,ou=people,dc=example,dc=com" --add mail=user1@example2.com -u "cn=admin,dc=example,dc=com"

# Replace an attribute value
./ldapie modify ldap.example.com "cn=user1,ou=people,dc=example,dc=com" --replace mobile=555-1234 -u "cn=admin,dc=example,dc=com"

# Delete an attribute value
./ldapie modify ldap.example.com "cn=user1,ou=people,dc=example,dc=com" --delete mail=user1@example.com -u "cn=admin,dc=example,dc=com"

# Delete an entire attribute
./ldapie modify ldap.example.com "cn=user1,ou=people,dc=example,dc=com" --delete mobile -u "cn=admin,dc=example,dc=com"

# Several changes at once; repeated --add values are all added
./ldapie modify ldap.example.com "cn=user1,ou=people,dc=example,dc=com" --add mail=a@example.com --add mail=b@example.com --replace title=Manager -u "cn=admin,dc=example,dc=com"
```

### Delete LDAP Entry

```bash
# Delete an entry
./ldapie delete ldap.example.com "cn=user1,ou=people,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Delete an entry and all its children (asks for confirmation)
./ldapie delete ldap.example.com "ou=people,dc=example,dc=com" --recursive -u "cn=admin,dc=example,dc=com"

# Skip the confirmation, e.g. in scripts
./ldapie delete ldap.example.com "ou=people,dc=example,dc=com" --recursive --yes -u "cn=admin,dc=example,dc=com"
```

### Rename or Move LDAP Entry

```bash
# Rename an entry (change RDN)
./ldapie rename ldap.example.com "cn=user1,ou=people,dc=example,dc=com" "cn=user1renamed" -u "cn=admin,dc=example,dc=com"

# Move an entry to a different location
./ldapie rename ldap.example.com "cn=user1,ou=people,dc=example,dc=com" "cn=user1" --parent "ou=admins,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Rename but keep the old RDN value as an attribute value
./ldapie rename ldap.example.com "cn=user1,ou=people,dc=example,dc=com" "cn=user1renamed" --keep-old-rdn -u "cn=admin,dc=example,dc=com"
```

### Export and Import

```bash
# Export a subtree to LDIF (binary values are base64-encoded)
./ldapie export ldap.example.com "ou=people,dc=example,dc=com" --output people.ldif -u "cn=admin,dc=example,dc=com"

# Export as JSON
./ldapie export ldap.example.com "ou=people,dc=example,dc=com" --format json --output people.json

# Import entries from LDIF; every entry is attempted and the command exits
# with status 1 if any entry could not be added
./ldapie import ldap.example.com people.ldif -u "cn=admin,dc=example,dc=com"
```

`import` reads LDIF content records and `changetype: add` records; other
change types and `:<` URL values are rejected with the offending line number.

### Interactive Mode

```bash
# Start interactive mode
./ldapie interactive

# Start interactive mode and connect to a server
./ldapie interactive --host ldap.example.com -u "cn=admin,dc=example,dc=com" --base "dc=example,dc=com"

# Start interactive mode with SSL
./ldapie interactive --host ldap.example.com --ssl --base "dc=example,dc=com"
```

In interactive mode, you can use commands like:

- `connect ldap.example.com 389 cn=admin,dc=example,dc=com --starttls` - Connect to a server
  (flags: `--ssl`, `--starttls`, `--no-verify`; you are prompted for the password)
- `base ou=people,dc=example,dc=com` - Set the base DN
- `search "(objectClass=person)" cn mail` - Search for entries
- `info`, `schema [objectClass]`, `schema --attr name` - Server and schema information
- `history [search|base|host]` - Show recent filters, base DNs and hosts
- `search ?` - Context help for a partial command
- `help` - Show all available commands; `exit`, `quit` or Ctrl-D leaves the shell

## Password Handling

LDAPie supports several methods for securely handling passwords:

### Interactive Password Prompt

The most secure method is to not specify the password on the command line and let the tool prompt for it:

```bash
./ldapie search ldap.example.com "dc=example,dc=com" -u "cn=admin,dc=example,dc=com"
# You'll be prompted to enter password securely
```

### Passwords With Special Characters

If you need to provide passwords containing special shell characters on the command line:

1. Use single quotes to prevent shell interpretation:

   ```bash
   ./ldapie search ldap.example.com "dc=example,dc=com" -u "user" -p 'password!with#special@chars'
   ```

2. Use the `LDAP_PASSWORD` environment variable; LDAPie reads it when `-p` is not given,
   so the password does not appear in the process list:

   ```bash
   read -rs LDAP_PASSWORD && export LDAP_PASSWORD
   ./ldapie search ldap.example.com "dc=example,dc=com" -u "user"
   ```

3. Escape special characters:

   ```bash
   ./ldapie search ldap.example.com "dc=example,dc=com" -u "user" -p "password\!with\#special\@chars"
   ```

## Help

```bash
./ldapie --help
./ldapie search --help
./ldapie info --help
./ldapie compare --help
./ldapie schema --help
./ldapie add --help
./ldapie modify --help
./ldapie delete --help
./ldapie rename --help
./ldapie export --help
./ldapie import --help
./ldapie interactive --help
```

## Themes

LDAPie supports light and dark themes. Set one with the `--theme` option of `search`,
the `LDAPIE_THEME` environment variable, or `theme:` in the config file
(in that order of precedence):

```bash
# Set theme using command-line option
./ldapie search ldap.example.com "dc=example,dc=com" --theme light

# Set theme using environment variable
LDAPIE_THEME=light ./ldapie search ldap.example.com "dc=example,dc=com"
```

## Container Usage

LDAPie is available as a Docker container, making it easy to use without installing Python or dependencies on your local machine.

### Prerequisites

- Docker installed on your system
- Basic knowledge of Docker commands

### Using the Pre-built Container

```bash
# Pull the latest image from Docker Hub
docker pull ruslanfialkovsky/ldapie:latest

# Run the help command to verify it works
docker run --rm ruslanfialkovsky/ldapie:latest --help

# Run the demo to explore LDAPie's features
docker run --rm ruslanfialkovsky/ldapie:latest --demo
```

### Running LDAP Commands with the Container

The container can be used just like the regular command-line tool:

```bash
# Basic LDAP search
docker run --rm ruslanfialkovsky/ldapie:latest search ldap.example.com "dc=example,dc=com" "(objectClass=*)"

# Search with authentication
docker run --rm ruslanfialkovsky/ldapie:latest search ldap.example.com "dc=example,dc=com" \
  "(objectClass=person)" --username "cn=admin,dc=example,dc=com" --password secret

# Output results in JSON format
docker run --rm ruslanfialkovsky/ldapie:latest search ldap.example.com "dc=example,dc=com" \
  "(objectClass=person)" --json

# Get server info
docker run --rm ruslanfialkovsky/ldapie:latest info ldap.example.com
```

### Using Interactive Mode with the Container

Interactive mode requires some additional Docker parameters:

```bash
docker run --rm -it ruslanfialkovsky/ldapie:latest interactive
```

The `-it` flags ensure that Docker allocates a pseudo-TTY and keeps STDIN open, which is necessary for interactive mode to work properly.

### Working with Local Files

To save output to files or read input files, you'll need to mount a volume:

```bash
# Mount the current directory to /data in the container. The image runs as a
# non-root user, so run it with your own user ID to write to the mount.
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/data ruslanfialkovsky/ldapie:latest \
  search ldap.example.com "dc=example,dc=com" "(objectClass=*)" --output /data/results.json --json
```

### Building the Container Locally

If you prefer to build the container yourself:

```bash
# Clone the repository
git clone https://github.com/ruslanfialkovskii/ldapie.git
cd ldapie

# Build the image
docker build -t ldapie .

# Run your local image
docker run --rm ldapie --help
```

### Environment Variables

The container supports the following environment variables:

- `LDAPIE_THEME`: Set to "light" or "dark" to control the color theme
- `LDAP_PASSWORD`: Bind password used when `-p` is not given

Example:

```bash
docker run --rm -e LDAPIE_THEME=light ruslanfialkovsky/ldapie:latest --help
```

### Container Tags

- `latest`: Most recent stable release
- `dev`: Development version
- `x.y.z` (e.g., `0.1.1`): Specific version releases

### Resource Considerations

The LDAPie container is lightweight and requires minimal resources. For most operations, the default Docker resource limits are sufficient.

For operations on very large LDAP directories, you may need to increase the memory limit:

```bash
docker run --rm --memory=512m ruslanfialkovsky/ldapie:latest search ldap.example.com \
  "dc=example,dc=com" "(objectClass=*)" --page-size 1000
```

## Development and Contributing

For information on setting up a development environment, contributing to the project, and the release process, see [DEVELOPMENT.md](DEVELOPMENT.md).

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

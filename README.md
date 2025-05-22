# LDAPie

A modern LDAP client CLI tool inspired by [HTTPie](https://httpie.io), using [ldap3](https://github.com/cannatag/ldap3) for LDAP operations and [Rich](https://github.com/Textualize/rich) for beautiful terminal output.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)

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

# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Make the wrapper scripts executable
chmod +x ldapie ldapie.sh

# Try the automated demo with a mock LDAP server
./ldapie.sh --demo

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

# Alternatively, install in development mode
pip install -e .
```

### Option 3: Quick Setup Script

```bash
# Make the wrapper script executable
chmod +x ldapie

# Use the wrapper script directly
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
- click >= 7.0: For command-line interface
- pydantic >= 1.9.0: For data validation
- typer >= 0.6.0: For command-line typing
- pyyaml >= 6.0: For configuration files
- cryptography >= 38.0.0: For secure connections
- python-dotenv >= 0.20.0: For environment variables
- python-Levenshtein >= 0.20.0: For command suggestions

### System Requirements

- Python 3.8 or newer
- For LDAPS (SSL/TLS) support, OpenSSL libraries may be required

## Shell Completion

LDAPie provides shell completion for Bash, Zsh, and Fish:

```bash
# Install shell completion
./ldapie --install-completion

# Show completion script without installing
./ldapie --show-completion
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
ldapie interactive [options]
```

## Context-Sensitive Help System

LDAPie includes a comprehensive context-sensitive help system that provides smart suggestions based on your current context and command history:

- **Progressive Help**: Type '?' after any partial command to get context-specific help
- **Command Validation**: Use the `--validate` flag to check and preview commands without execution
- **Smart Suggestions**: Get intelligent recommendations based on your current operation context
- **"Did you mean...?"**: Get automatic corrections for mistyped commands
- **History-Aware Help**: Suggestions are informed by your previous commands and operations

Examples:

```bash
# Get help for a partial command
./ldapie search?

# Validate a command without executing it
./ldapie search ldap.example.com "dc=example,dc=com" --validate

# Get help during interactive mode
ldapie> search?
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

# Add an entry from LDIF file
./ldapie add ldap.example.com --ldif entries.ldif -u "cn=admin,dc=example,dc=com"

# Add an entry from JSON file
./ldapie add ldap.example.com "cn=newgroup,ou=groups,dc=example,dc=com" --json group.json -u "cn=admin,dc=example,dc=com"
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
```

### Delete LDAP Entry

```bash
# Delete an entry
./ldapie delete ldap.example.com "cn=user1,ou=people,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"

# Delete an entry and all its children (recursive)
./ldapie delete ldap.example.com "ou=people,dc=example,dc=com" --recursive -u "cn=admin,dc=example,dc=com"
```

### Rename or Move LDAP Entry

```bash
# Rename an entry (change RDN)
./ldapie rename ldap.example.com "cn=user1,ou=people,dc=example,dc=com" "cn=user1renamed" -u "cn=admin,dc=example,dc=com"

# Move an entry to a different location
./ldapie rename ldap.example.com "cn=user1,ou=people,dc=example,dc=com" "cn=user1" --parent "ou=admins,dc=example,dc=com" -u "cn=admin,dc=example,dc=com"
```

### Interactive Mode

```bash
# Start interactive mode
./ldapie interactive

# Start interactive mode and connect to a server
./ldapie interactive --host ldap.example.com --user "cn=admin,dc=example,dc=com" --base "dc=example,dc=com"

# Start interactive mode with SSL
./ldapie interactive --host ldap.example.com --ssl --base "dc=example,dc=com"
```

In interactive mode, you can use commands like:

- `connect ldap.example.com 389 admin --ssl` - Connect to server
- `ls` - List entries in current base DN
- `cd ou=people,dc=example,dc=com` - Change base DN
- `search "(objectClass=person)" cn mail` - Search for entries
- `show 0` - Show first entry from last search
- `add cn=user,ou=people,dc=example,dc=com person cn=User sn=User` - Add entry
- `delete cn=user,ou=people,dc=example,dc=com` - Delete entry
- `help` - Show all available commands

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

2. Use environment variables:

   ```bash
   export LDAP_PASSWORD="password!with#special@chars"
   ./ldapie search ldap.example.com "dc=example,dc=com" -u "user" -p "$LDAP_PASSWORD"
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
./ldapie interactive --help
```

## Themes

LDAPie supports light and dark themes that can be set through the `--theme` option or environment variable:

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
docker pull ruslanfialkovskii/ldapie:latest

# Run the help command to verify it works
docker run --rm ruslanfialkovskii/ldapie:latest --help

# Run the demo to explore LDAPie's features
docker run --rm ruslanfialkovskii/ldapie:latest --demo
```

### Running LDAP Commands with the Container

The container can be used just like the regular command-line tool:

```bash
# Basic LDAP search
docker run --rm ruslanfialkovskii/ldapie:latest search ldap.example.com "dc=example,dc=com" "(objectClass=*)"

# Search with authentication
docker run --rm ruslanfialkovskii/ldapie:latest search ldap.example.com "dc=example,dc=com" \
  "(objectClass=person)" --username "cn=admin,dc=example,dc=com" --password secret

# Output results in JSON format
docker run --rm ruslanfialkovskii/ldapie:latest search ldap.example.com "dc=example,dc=com" \
  "(objectClass=person)" --json

# Get server info
docker run --rm ruslanfialkovskii/ldapie:latest info ldap.example.com
```

### Using Interactive Mode with the Container

Interactive mode requires some additional Docker parameters:

```bash
docker run --rm -it ruslanfialkovskii/ldapie:latest interactive
```

The `-it` flags ensure that Docker allocates a pseudo-TTY and keeps STDIN open, which is necessary for interactive mode to work properly.

### Working with Local Files

To save output to files or read input files, you'll need to mount a volume:

```bash
# Mount the current directory to /data in the container
docker run --rm -v $(pwd):/data ruslanfialkovskii/ldapie:latest search ldap.example.com \
  "dc=example,dc=com" "(objectClass=*)" --output /data/results.json --json
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
- `LDAPIE_DEFAULT_SERVER`: Default LDAP server hostname

Example:

```bash
docker run --rm -e LDAPIE_THEME=light ruslanfialkovskii/ldapie:latest --help
```

### Container Tags

- `latest`: Most recent stable release
- `dev`: Development version
- `x.y.z` (e.g., `0.1.1`): Specific version releases

### Resource Considerations

The LDAPie container is lightweight and requires minimal resources. For most operations, the default Docker resource limits are sufficient.

For operations on very large LDAP directories, you may need to increase the memory limit:

```bash
docker run --rm --memory=512m ruslanfialkovskii/ldapie:latest search ldap.example.com \
  "dc=example,dc=com" "(objectClass=*)" --page-size 1000
```

For more detailed information about using LDAPie in containers, see [CONTAINER.md](CONTAINER.md).

## Development and Contributing

For information on setting up a development environment, contributing to the project, and the release process, see [DEVELOPMENT.md](DEVELOPMENT.md).

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

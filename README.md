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
- Command history and help system

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

### Option 1: Install from Source

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Option 2: Quick Setup Script

```bash
# Make the wrapper script executable
chmod +x ldapie

# Use the wrapper script directly
./ldapie search localhost "dc=example,dc=com"
```

### Option 3: Using Docker

```bash
# Build the Docker image
docker build -t ldapie .

# Run using Docker
docker run -it ldapie search ldap.example.com "dc=example,dc=com"
```

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

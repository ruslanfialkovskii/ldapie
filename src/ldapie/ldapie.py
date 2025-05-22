#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAPie - A modern LDAP client CLI tool

This module provides a command-line interface for LDAP operations,
inspired by HTTPie's design philosophy. It uses the ldap3 library for
LDAP functionality and Rich for beautiful terminal output.

Key features:
- Search and browse LDAP directories
- View and modify LDAP entries
- Compare entries and attributes
- Explore schema information
- Interactive shell mode

Usage:
    ldapie search <host> <base_dn> [<filter>] [options]
    ldapie info <host> [options]
    ldapie compare <host> <dn1> <dn2> [options]
    ldapie schema <host> [<object_class>] [options]
    ldapie add <host> <dn> [options]
    ldapie delete <host> <dn> [options]
    ldapie modify <host> <dn> [options]
    ldapie rename <host> <dn> <new_rdn> [options]
    ldapie interactive [options]
"""

__version__ = "0.1.0"

import os
import sys
import click
import getpass
from typing import List, Optional, Dict, Any, Tuple
from rich.console import Console
from rich.theme import Theme
from rich.style import Style
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich import box
import json
import ldap3
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES, SUBTREE, BASE, LEVEL
from ldap3.core.exceptions import LDAPException, LDAPBindError

# Define color themes before importing other modules to avoid circular imports
DARK_THEME = {
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "highlight": "magenta",
    "ldap.dn": "bright_blue",
    "ldap.attr": "bright_magenta",
    "ldap.value": "bright_white",
    "command": "cyan",
    "option": "yellow",
    "usage": "green",
}

LIGHT_THEME = {
    "info": "blue",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "highlight": "magenta",
    "ldap.dn": "blue",
    "ldap.attr": "purple",
    "ldap.value": "black",
    "command": "blue",
    "option": "yellow",
    "usage": "green",
}

# Get theme from environment or default to dark
theme_name = os.environ.get("LDAPIE_THEME", "dark").lower()
theme_colors = LIGHT_THEME if theme_name == "light" else DARK_THEME
console = Console(theme=Theme(theme_colors))

# Now import modules that might need the console
try:
    # Try importing as an installed package
    import ldapie.ldapie_utils as utils
    from ldapie.rich_formatter import add_rich_help_option
except ImportError:
    # Fall back to development path
    import src.ldapie.ldapie_utils as utils
    from src.ldapie.rich_formatter import add_rich_help_option

class LdapConfig:
    """
    LDAP Connection Configuration
    
    Stores configuration details for an LDAP connection and provides
    methods to establish connections.
    
    Attributes:
        host (str): LDAP server hostname
        username (Optional[str]): Bind DN for authentication
        password (Optional[str]): Password for authentication
        use_ssl (bool): Whether to use SSL/TLS
        port (int): LDAP port number
        timeout (int): Connection timeout in seconds
    """
    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
        port: Optional[int] = None,
        timeout: int = 30,
    ):
        """
        Initialize LDAP connection configuration.
        
        Args:
            host: LDAP server hostname
            username: Optional bind DN for authentication
            password: Optional password for authentication
            use_ssl: Whether to use SSL/TLS
            port: LDAP port number (default: 389, or 636 with SSL)
            timeout: Connection timeout in seconds
            
        Example:
            >>> config = LdapConfig("ldap.example.com", 
            ...                    username="cn=admin,dc=example,dc=com",
            ...                    password="secret", use_ssl=True)
        """
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.port = port or (636 if use_ssl else 389)
        self.timeout = timeout

    def get_connection(self) -> Tuple[Server, Connection]:
        """
        Create an LDAP server connection based on configuration.
        
        Establishes a connection to the LDAP server using the configured
        parameters. If username is provided but password is not, prompts
        for password interactively.
        
        Returns:
            Tuple containing:
                - Server object
                - Connection object (bound to the server)
                
        Raises:
            LDAPBindError: If authentication fails
            LDAPException: For other LDAP-related errors
            
        Example:
            >>> server, conn = config.get_connection()
        """
        server_uri = f"{'ldaps' if self.use_ssl else 'ldap'}://{self.host}:{self.port}"
        server = Server(server_uri, get_info=ALL, connect_timeout=self.timeout)
        
        # Handle anonymous vs. authenticated binding
        if self.username:
            if self.password is None:
                # Prompt for password if not provided
                self.password = getpass.getpass(f"Enter password for {self.username}: ")
            
            conn = Connection(
                server,
                user=self.username,
                password=self.password,
                auto_bind=True,
                raise_exceptions=True
            )
        else:
            # Anonymous binding
            conn = Connection(
                server,
                auto_bind=True,
                raise_exceptions=True
            )
            
        return server, conn


def handle_connection_error(func):
    """
    Decorator to handle LDAP connection errors.
    
    Catches LDAP exceptions that might occur during connection operations
    and displays user-friendly error messages.
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function that handles LDAP connection errors
        
    Example:
        >>> @handle_connection_error
        ... def my_ldap_function():
        ...     # LDAP operations
        ...     pass
    """
    def wrapper(*args, **kwargs):
        try:
            # Check if help context is available
            try:
                try:
                    from ldapie.help_context import HelpContext
                except ImportError:
                    from src.ldapie.help_context import HelpContext
                help_context = HelpContext()
                help_context_available = True
            except ImportError:
                help_context_available = False
            
            # Get the command string for error tracking
            import inspect
            func_name = func.__name__
            command_str = func_name.replace("_command", "")
            
            # Execute the function
            result = func(*args, **kwargs)
            return result
        except LDAPBindError as e:
            error_msg = f"Authentication failed: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Record error in help context if available
            if help_context_available:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except LDAPException as e:
            error_msg = f"LDAP error: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Record error in help context if available
            if help_context_available:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Record error in help context if available
            if help_context_available:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
    return wrapper

@click.group(name="ldapie")
@click.version_option(version=__version__)
@click.option('--install-completion', is_flag=True, help='Install completion for the current shell.')
@click.option('--show-completion', is_flag=True, help='Show completion for the current shell, to copy it or customize the installation.')
@click.option('--demo', is_flag=True, help='Run the automated demo with mock LDAP server.')
@add_rich_help_option
def cli(install_completion=False, show_completion=False, demo=False):
    """LDAPie - A modern LDAP client"""
    # Import help context for CLI commands
    try:
        try:
            from ldapie.help_context import HelpContext
        except ImportError:
            from src.ldapie.help_context import HelpContext
        # Initialize the help context as a singleton
        help_context = HelpContext()
    except ImportError:
        pass
    
    # Check for demo flag first
    if demo:
        console.print("[info]Starting the automated LDAPie demo...[/info]")
        # We'll handle this in the main block
        return
        
    # Install shell completion if requested
    if install_completion or show_completion:
        import subprocess
        
        # Determine the shell
        shell = os.environ.get('SHELL', '').split('/')[-1]
        if not shell:
            console.print("[error]Unable to determine your shell type.[/error]")
            sys.exit(1)
            
        if shell not in ['bash', 'zsh', 'fish']:
            console.print(f"[error]Unsupported shell: {shell}[/error]")
            sys.exit(1)
            
        # Generate completion script
        completion_script = f"""
# LDAPie shell completion
eval "$(_LDAPIE_COMPLETE={shell}_source ldapie)"
"""
        
        if show_completion:
            console.print(f"# LDAPie completion for {shell}")
            console.print(completion_script)
            sys.exit(0)
            
        if install_completion:
            # Determine the shell config file
            if shell == 'bash':
                rcfile = os.path.expanduser('~/.bashrc')
            elif shell == 'zsh':
                rcfile = os.path.expanduser('~/.zshrc')
            elif shell == 'fish':
                rcfile = os.path.expanduser('~/.config/fish/config.fish')
                
            # Check if completion is already installed
            try:
                with open(rcfile, 'r') as f:
                    if completion_script.strip() in f.read():
                        console.print(f"[warning]Completion for {shell} is already installed.[/warning]")
                        sys.exit(0)
            except FileNotFoundError:
                pass
                
            # Append the completion script to the shell config file
            try:
                with open(rcfile, 'a') as f:
                    f.write(f"\n{completion_script}\n")
                console.print(f"[success]Completion for {shell} has been installed to {rcfile}[/success]")
                console.print("[info]Please restart your shell or source the config file.[/info]")
                sys.exit(0)
            except Exception as e:
                console.print(f"[error]Failed to install completion: {e}[/error]")
                sys.exit(1)

@cli.command("search")
@click.argument("host")
@click.argument("base_dn")
@click.argument("filter_query", default="(objectClass=*)")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("-a", "--attrs", multiple=True, help="Attributes to fetch (can be used multiple times)")
@click.option("--scope", type=click.Choice(["base", "one", "sub"]), default="sub", help="Search scope")
@click.option("--limit", type=int, help="Maximum number of entries to return")
@click.option("--page-size", type=int, help="Page size for paged results")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.option("--ldif", is_flag=True, help="Output in LDIF format")
@click.option("--csv", is_flag=True, help="Output in CSV format")
@click.option("--tree", is_flag=True, help="Display results as a tree")
@click.option("--output", help="Save results to a file")
@click.option("--theme", type=click.Choice(["dark", "light"]), help="Color theme")
@add_rich_help_option
@handle_connection_error
def search_command(
    host, base_dn, filter_query, username, password, ssl, port, attrs,
    scope, limit, page_size, json, ldif, csv, tree, output, theme
):
    """
    Search the LDAP directory.
    
    Performs an LDAP search operation and displays the results in various formats.
    
    Args:
        host: LDAP server hostname
        base_dn: Base DN for search
        filter_query: LDAP search filter (default: (objectClass=*))
        username: Optional bind DN for authentication
        password: Optional password for authentication
        ssl: Whether to use SSL/TLS
        port: LDAP port number
        attrs: Attributes to fetch
        scope: Search scope (base, one, sub)
        limit: Maximum number of entries to return
        page_size: Page size for paged results
        json: Output in JSON format
        ldif: Output in LDIF format
        csv: Output in CSV format
        tree: Display results as a tree
        output: Save results to a file
        theme: Color theme
        
    Example:
        ldapie search ldap.example.com dc=example,dc=com "(objectClass=person)" \\
                --attrs cn --attrs mail --limit 100
    """
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Determine search scope
    search_scope = {
        "base": BASE,
        "one": LEVEL,
        "sub": SUBTREE
    }[scope]
    
    # Attributes to retrieve
    attributes = list(attrs) if attrs else ALL_ATTRIBUTES
    
    # Execute search
    console.print(f"[info]Searching {host} with filter: {filter_query}[/info]")
    
    if page_size:
        # Use paged search
        entries = utils.paged_search(
            conn, base_dn, filter_query, 
            search_scope, attributes, 
            page_size, limit
        )
    else:
        # Regular search
        conn.search(
            base_dn, 
            filter_query, 
            search_scope=search_scope, 
            attributes=attributes,
            size_limit=limit or 0
        )
        entries = conn.entries
    
    # Process and display results
    if len(entries) == 0:
        console.print("[warning]No entries found.[/warning]")
        return
    
    # Update help context with search results if available
    try:
        try:
            from ldapie.help_context import HelpContext
        except ImportError:
            from src.ldapie.help_context import HelpContext
        help_context = HelpContext()
        help_context.current_context["base_dn"] = base_dn
        help_context.current_context["filter"] = filter_query
        help_context.current_context["attributes"] = attributes
    except ImportError:
        pass
    
    console.print(f"[success]Found {len(entries)} entries.[/success]")
    
    # Handle different output formats
    if json:
        utils.output_json(entries, output)
    elif ldif:
        utils.output_ldif(entries, output)
    elif csv:
        utils.output_csv(entries, output)
    elif tree:
        utils.output_tree(entries, base_dn, console, output)
    else:
        # Default rich text output
        utils.output_rich(entries, console, output)

@cli.command("info")
@click.argument("host")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--json", is_flag=True, help="Output in JSON format")
@add_rich_help_option
@handle_connection_error
def info_command(host, username, password, ssl, port, json):
    """Show information about LDAP server"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Get server info
    if json:
        utils.output_server_info_json(server, conn, console)
    else:
        utils.output_server_info_rich(server, conn, console)

@cli.command("compare")
@click.argument("host")
@click.argument("dn1")
@click.argument("dn2")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("-a", "--attrs", multiple=True, help="Attributes to compare (can be used multiple times)")
@add_rich_help_option
@handle_connection_error
def compare_command(host, dn1, dn2, username, password, ssl, port, attrs):
    """Compare two LDAP entries"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Perform comparison
    utils.compare_entries(conn, dn1, dn2, attrs, console)

@cli.command("schema")
@click.argument("host")
@click.argument("object_class", required=False)
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--attr", help="Display information about specific attribute")
@add_rich_help_option
@handle_connection_error
def schema_command(host, object_class, username, password, ssl, port, attr):
    """Get schema information from LDAP server"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Get and display schema information
    utils.show_schema(server, object_class, attr, console)

@cli.command("add")
@click.argument("host")
@click.argument("dn")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("-c", "--class", "object_class", multiple=True, help="Object class for new entry")
@click.option("-a", "--attr", multiple=True, help="Attribute to add in the format name=value")
@click.option("--ldif", help="LDIF file containing entry attributes")
@click.option("--json", help="JSON file containing entry attributes")
@add_rich_help_option
@handle_connection_error
def add_command(host, dn, username, password, ssl, port, object_class, attr, ldif, json):
    """Add a new entry to the LDAP directory"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Parse attributes from different sources
    attributes = {}
    
    # Add object classes if specified
    if object_class:
        attributes['objectClass'] = list(object_class)
    
    # Load attributes from JSON file
    if json:
        with open(json, 'r') as f:
            json_data = json.load(f)
            for key, value in json_data.items():
                attributes[key] = value
    
    # Parse attributes from command line
    for a in attr:
        try:
            name, value = a.split('=', 1)
            if name in attributes:
                if isinstance(attributes[name], list):
                    attributes[name].append(value)
                else:
                    attributes[name] = [attributes[name], value]
            else:
                attributes[name] = value
        except ValueError:
            console.print(f"[error]Invalid attribute format: {a}. Use name=value[/error]")
            sys.exit(1)
    
    # Add entry
    if conn.add(dn, attributes=attributes):
        console.print(f"[success]Successfully added entry: {dn}[/success]")
    else:
        console.print(f"[error]Failed to add entry: {conn.result}[/error]")
        sys.exit(1)

@cli.command("delete")
@click.argument("host")
@click.argument("dn")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--recursive", is_flag=True, help="Delete recursively")
@add_rich_help_option
@handle_connection_error
def delete_command(host, dn, username, password, ssl, port, recursive):
    """Delete an entry from the LDAP directory"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    if recursive:
        utils.delete_recursive(conn, dn, console)
    else:
        if conn.delete(dn):
            console.print(f"[success]Successfully deleted entry: {dn}[/success]")
        else:
            console.print(f"[error]Failed to delete entry: {conn.result}[/error]")
            sys.exit(1)

@cli.command("modify")
@click.argument("host")
@click.argument("dn")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--add", multiple=True, help="Add attribute in format name=value")
@click.option("--replace", multiple=True, help="Replace attribute in format name=value")
@click.option("--delete", multiple=True, help="Delete attribute in format name=value")
@click.option("--file", help="JSON file with changes")
@add_rich_help_option
@handle_connection_error
def modify_command(host, dn, username, password, ssl, port, add, replace, delete, file):
    """Modify an existing LDAP entry"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    changes = {}
    
    if file:
        with open(file, 'r') as f:
            changes = json.load(f)
    else:
        # Parse attributes
        changes = utils.parse_modification_attributes(add, replace, delete)
        
    if not changes:
        console.print("[error]No changes specified.[/error]")
        sys.exit(1)
        
    # Apply modifications
    if conn.modify(dn, changes):
        console.print(f"[success]Successfully modified entry: {dn}[/success]")
    else:
        console.print(f"[error]Failed to modify entry: {conn.result}[/error]")
        sys.exit(1)

@cli.command("rename")
@click.argument("host")
@click.argument("dn")
@click.argument("new_rdn")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--delete-old-rdn", is_flag=True, help="Delete old RDN", default=True)
@click.option("--parent", help="New parent DN")
@add_rich_help_option
@handle_connection_error
def rename_command(host, dn, new_rdn, username, password, ssl, port, delete_old_rdn, parent):
    """Rename or move an LDAP entry"""
    
    # Configure LDAP connection
    config = LdapConfig(
        host=host,
        username=username,
        password=password,
        use_ssl=ssl,
        port=port
    )
    
    # Connect to LDAP server
    server, conn = config.get_connection()
    
    # Rename entry
    if conn.modify_dn(dn, new_rdn, delete_old_rdn=delete_old_rdn, new_superior=parent):
        console.print(f"[success]Successfully renamed entry[/success]")
    else:
        console.print(f"[error]Failed to rename entry: {conn.result}[/error]")
        sys.exit(1)

@cli.command("interactive")
@click.option("--host", help="LDAP server hostname")
@click.option("-u", "--username", help="Bind DN for authentication")
@click.option("-p", "--password", help="Password for authentication")
@click.option("--ssl", is_flag=True, help="Use SSL/TLS connection")
@click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)")
@click.option("--base", help="Base DN for operations")
@add_rich_help_option
@handle_connection_error
def interactive_command(host, username, password, ssl, port, base):
    """Start interactive LDAP console"""
    console.print("[info]Starting interactive mode[/info]")
    
    if host:
        # Configure LDAP connection
        config = LdapConfig(
            host=host,
            username=username,
            password=password,
            use_ssl=ssl,
            port=port
        )
        
        # Connect to LDAP server
        server, conn = config.get_connection()
        
        # Start interactive session with connection
        utils.start_interactive_session(server, conn, console, base)
    else:
        # Start interactive session without connection
        utils.start_interactive_session(None, None, console, None)

def print_help():
    """
    Print detailed help information.
    
    Displays usage information, available commands, and options
    in a user-friendly format using Rich formatting.
    """
    console.print("[usage]Usage:[/usage] ldapie [OPTIONS] COMMAND [ARGS]...")
    console.print("\nLDAPie - A modern LDAP client")
    
    # Options section
    console.print("\n[bold]Options[/bold]")
    console.rule()
    
    options_table = Table(show_header=False, box=None)
    options_table.add_column("Option", style="option")
    options_table.add_column("Description")
    
    options_table.add_row("--install-completion", "Install completion for the current shell.")
    options_table.add_row("--show-completion", "Show completion for the current shell, to copy it or customize the installation.")
    options_table.add_row("--demo", "Run the automated demo with mock LDAP server.")
    options_table.add_row("--help", "Show this message and exit.")
    options_table.add_row("--version", "Show the version and exit.")
    
    console.print(options_table)
    
    # Commands section
    console.print("\n[bold]Commands[/bold]")
    console.rule()
    
    commands_table = Table(show_header=False, box=None)
    commands_table.add_column("Command", style="command")
    commands_table.add_column("Description")
    
    commands_table.add_row("search", "Search the LDAP directory")
    commands_table.add_row("info", "Show information about LDAP server")
    commands_table.add_row("compare", "Compare two LDAP entries")
    commands_table.add_row("schema", "Get schema information from LDAP server")
    commands_table.add_row("add", "Add a new entry to the LDAP directory")
    commands_table.add_row("delete", "Delete an entry from the LDAP directory")
    commands_table.add_row("modify", "Modify an existing LDAP entry")
    commands_table.add_row("rename", "Rename or move an LDAP entry")
    commands_table.add_row("interactive", "Start interactive LDAP console")
    
    console.print(commands_table)
    
    # Additional help message
    console.print("\n[info]Run 'ldapie COMMAND --help' for more information on a command.[/info]")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--help":
        print_help()  # Use our custom help formatter for top-level help
    elif len(sys.argv) == 2 and sys.argv[1] == "--demo":
        # Run the demo script
        try:
            # Add the parent directory to path for imports if needed
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Import and run the demo
            from tests.demo import run_demo
            run_demo()
        except Exception as e:
            console.print(f"[error]Error running demo: {e}[/error]")
            sys.exit(1)
    elif len(sys.argv) == 1:
        print_help()  # Use our custom help formatter when no args are provided
    else:
        cli()  # For all other cases, use Click's CLI

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
    ldapie export <host> <base_dn> [<filter>] --output <file> [options]
    ldapie import <host> <ldif_file> [options]
    ldapie interactive [options]
"""

import functools
import getpass
import json as json_lib  # Renamed to avoid conflicts with parameter names
import os
import ssl
import sys
import traceback  # For debug stack traces
from typing import Any, Dict, NamedTuple, Optional, Tuple

import click
from click.core import ParameterSource
from click.shell_completion import get_completion_class
from ldap3 import (
    ALL,
    ALL_ATTRIBUTES,
    AUTO_BIND_NO_TLS,
    AUTO_BIND_TLS_BEFORE_BIND,
    BASE,
    LEVEL,
    SUBTREE,
    Connection,
    Server,
    Tls,
)
from ldap3.core.exceptions import LDAPBindError, LDAPException
from ldap3.core.results import RESULT_SIZE_LIMIT_EXCEEDED
from rich.console import Console
from rich.markup import escape
from rich.theme import Theme

from . import __version__
from . import entry_operations as entry_utils
from . import interactive as interactive_utils
from . import output as output_utils
from . import schema as schema_utils
from . import search as search_utils
from . import utils as general_utils
from .config import load_config
from .help_context import HelpContext
from .ldif_parser import parse_ldif
from .rich_formatter import add_rich_help_option

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

# Page size used when paging is on by default (search, export, recursive delete)
DEFAULT_PAGE_SIZE = 500


def _theme(name: Optional[str]) -> Theme:
    return Theme(LIGHT_THEME if name == "light" else DARK_THEME)


# Results go to stdout; status messages go to stderr, so --json, --ldif and
# --csv output can be piped.
console = Console(theme=_theme(os.environ.get("LDAPIE_THEME", "dark").lower()))
err_console = Console(
    stderr=True, theme=_theme(os.environ.get("LDAPIE_THEME", "dark").lower())
)


def _apply_theme(name: str) -> None:
    """Switch both consoles to the named color theme."""
    for target in (console, err_console):
        target.push_theme(_theme(name))


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
        starttls: bool = False,
        no_verify: bool = False,
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
            starttls: Whether to use STARTTLS (upgrade plain to TLS)
            no_verify: Skip TLS certificate verification (insecure)
        """
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.port = port or (636 if use_ssl else 389)
        self.timeout = timeout
        self.starttls = starttls
        self.no_verify = no_verify

    def __repr__(self) -> str:
        # Never include the password: debug output prints this object
        return (
            f"LdapConfig(host={self.host!r}, port={self.port}, "
            f"username={self.username!r}, use_ssl={self.use_ssl}, "
            f"starttls={self.starttls}, no_verify={self.no_verify})"
        )

    def get_connection(self) -> Tuple[Server, Connection]:
        """
        Create an LDAP server connection based on configuration.

        Establishes a connection to the LDAP server using the configured
        parameters. If username is provided but password is not, uses
        LDAP_PASSWORD or prompts for the password interactively.

        With STARTTLS the connection is upgraded to TLS before the bind, so
        credentials never travel in clear text.

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
        # Configure TLS if SSL or STARTTLS is enabled
        tls_config = None
        if self.use_ssl or self.starttls:
            validate = ssl.CERT_NONE if self.no_verify else ssl.CERT_REQUIRED
            if self.no_verify:
                err_console.print(
                    "[warning]Warning: TLS certificate verification is disabled.[/warning]"
                )
            tls_config = Tls(validate=validate)

        server_uri = f"{'ldaps' if self.use_ssl else 'ldap'}://{self.host}:{self.port}"
        server = Server(
            server_uri, get_info=ALL, connect_timeout=self.timeout, tls=tls_config
        )

        auto_bind = (
            AUTO_BIND_TLS_BEFORE_BIND
            if self.starttls and not self.use_ssl
            else AUTO_BIND_NO_TLS
        )

        # Handle anonymous vs. authenticated binding
        if self.username:
            if self.password is None:
                # Try LDAP_PASSWORD env var before prompting
                env_password = os.environ.get("LDAP_PASSWORD")
                if env_password:
                    self.password = env_password
                else:
                    self.password = getpass.getpass(
                        f"Enter password for {self.username}: "
                    )

            conn = Connection(
                server,
                user=self.username,
                password=self.password,
                auto_bind=auto_bind,
                raise_exceptions=True,
            )
        else:
            # Anonymous binding
            conn = Connection(server, auto_bind=auto_bind, raise_exceptions=True)

        return server, conn


def _warn_if_password_on_cli(password):
    """Print a security warning if password was passed via CLI flag."""
    if password is not None:
        err_console.print(
            "[warning]Warning: Passing passwords via --password is insecure. "
            "Use LDAP_PASSWORD env var or omit to be prompted.[/warning]"
        )


_ERROR_MESSAGES = {
    LDAPBindError: "Authentication failed",
    LDAPException: "LDAP error",
    ValueError: "Operation error (ValueError)",
    TypeError: "Operation error (TypeError)",
    KeyError: "Operation error (KeyError)",
    OSError: "File operation error",
}


def _format_error(exc, mapping):
    """Return a user-friendly error message for an exception using the mapping."""
    for exc_type, prefix in mapping.items():
        if isinstance(exc, exc_type):
            return f"{prefix}: {exc}"
    return f"Unexpected error: {exc}"


def _redacted(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Copy kwargs for debug output with password values masked."""
    return {
        key: ("***" if "password" in key and value is not None else value)
        for key, value in kwargs.items()
    }


def handle_connection_error(func):
    """Decorator to handle LDAP connection errors with user-friendly messages."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context(silent=True)
        is_debug = False
        if ctx and isinstance(ctx.obj, dict):
            is_debug = ctx.obj.get("DEBUG", False)

        command_str = func.__name__.replace("_command", "")
        help_context = HelpContext()

        try:
            if is_debug:
                err_console.print(
                    f"[bold blue]DEBUG[/bold blue]: Executing {func.__name__}"
                )
                err_console.print(f"[bold blue]DEBUG[/bold blue]: Arguments: {args}")
                err_console.print(
                    f"[bold blue]DEBUG[/bold blue]: Keyword arguments: {_redacted(kwargs)}"
                )

            result = func(*args, **kwargs)

            if is_debug:
                err_console.print(
                    f"[bold blue]DEBUG[/bold blue]: {func.__name__} completed successfully"
                )
            return result

        except (click.ClickException, click.exceptions.Abort, click.exceptions.Exit):
            raise  # Click reports these itself (usage errors, declined prompts)
        except (
            LDAPException,
            ValueError,
            TypeError,
            KeyError,
            OSError,
        ) as e:
            error_msg = _format_error(e, _ERROR_MESSAGES)
        except Exception as e:  # pylint: disable=broad-except
            error_msg = f"Unexpected error: {e}"

        err_console.print(f"[error]{error_msg}[/error]")
        if is_debug:
            err_console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
            err_console.print(traceback.format_exc())
        help_context.add_error(command_str, error_msg)
        sys.exit(1)

    return wrapper


_CONNECTION_OPTIONS = [
    click.option("-u", "--username", help="Bind DN for authentication"),
    click.option(
        "-p",
        "--password",
        help="Password for authentication (prefer LDAP_PASSWORD or the prompt)",
    ),
    click.option(
        "--ssl/--no-ssl", "use_ssl", default=False, help="Use an LDAPS connection"
    ),
    click.option(
        "--starttls/--no-starttls",
        default=False,
        help="Upgrade the connection with STARTTLS before binding",
    ),
    click.option(
        "--verify/--no-verify",
        default=True,
        help="Verify TLS certificates (--no-verify is insecure)",
    ),
    click.option("--port", type=int, help="LDAP port (default: 389, or 636 with SSL)"),
]


def connection_options(func):
    """Add the shared connection options and pass an ``ldap_config`` instead.

    Options not given on the command line fall back to the config file
    (see config.py). The command receives ``ldap_config`` (None when there
    is no host, which only the interactive command allows).
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        settings = {
            name: kwargs.pop(name)
            for name in (
                "username",
                "password",
                "use_ssl",
                "starttls",
                "verify",
                "port",
            )
        }
        file_config = (ctx.find_root().obj or {}).get("config", {})

        def use_config(param: str, key: str, convert=lambda value: value) -> None:
            if key in file_config and ctx.get_parameter_source(param) in (
                None,
                ParameterSource.DEFAULT,
            ):
                settings[param] = convert(file_config[key])

        use_config("username", "default_username")
        use_config("use_ssl", "use_ssl")
        use_config("starttls", "starttls")
        use_config("verify", "no_verify", lambda no_verify: not no_verify)
        use_config("port", "port")

        host = kwargs.get("host") or file_config.get("default_host")
        if "host" in kwargs:
            kwargs["host"] = host

        _warn_if_password_on_cli(settings["password"])
        kwargs["ldap_config"] = (
            LdapConfig(
                host=host,
                username=settings["username"],
                password=settings["password"],
                use_ssl=settings["use_ssl"],
                port=settings["port"],
                starttls=settings["starttls"],
                no_verify=not settings["verify"],
            )
            if host
            else None
        )
        return func(*args, **kwargs)

    for option in reversed(_CONNECTION_OPTIONS):
        wrapper = option(wrapper)
    return wrapper


def _validate_dn_or_exit(dn: str) -> None:
    try:
        general_utils.validate_dn(dn)
    except ValueError as e:
        err_console.print(f"[error]Invalid DN: {e}[/error]")
        sys.exit(1)


def _validate_filter_or_exit(filter_query: str) -> None:
    try:
        general_utils.validate_search_filter(filter_query)
    except ValueError as e:
        err_console.print(f"[error]Invalid LDAP filter: {e}[/error]")
        sys.exit(1)


def _warn_if_truncated(conn: Connection, count: int, limit: Optional[int]) -> None:
    """Warn when the server cut the results short with its own size limit."""
    result = conn.result or {}
    if result.get("result") == RESULT_SIZE_LIMIT_EXCEEDED and not (
        limit and count >= limit
    ):
        err_console.print(
            "[warning]Warning: the server's size limit was reached; "
            "the results are incomplete.[/warning]"
        )


# Shell completion: how to enable it, and where --install-completion writes it
class _CompletionSetup(NamedTuple):
    activate: str  # line that enables completion in the shell config
    file: str  # where --install-completion writes the script
    rcfile: Optional[str]  # shell config to update, if the shell needs it
    rc_lines: Optional[str]


_COMPLETION = {
    "bash": _CompletionSetup(
        activate='eval "$(_LDAPIE_COMPLETE=bash_source ldapie)"',
        file="~/.bash_completion.d/ldapie",
        rcfile="~/.bashrc",
        rc_lines="source ~/.bash_completion.d/ldapie",
    ),
    "zsh": _CompletionSetup(
        activate='eval "$(_LDAPIE_COMPLETE=zsh_source ldapie)"',
        file="~/.zsh/completion/_ldapie",
        rcfile="~/.zshrc",
        rc_lines="fpath=(~/.zsh/completion $fpath)\nautoload -Uz compinit && compinit",
    ),
    "fish": _CompletionSetup(
        # fish loads ~/.config/fish/completions automatically
        activate="_LDAPIE_COMPLETE=fish_source ldapie | source",
        file="~/.config/fish/completions/ldapie.fish",
        rcfile=None,
        rc_lines=None,
    ),
}
_RC_MARKER = "# LDAPie completion"


def _detect_shell() -> str:
    shell = os.path.basename(os.environ.get("SHELL", ""))
    if shell not in _COMPLETION:
        err_console.print(
            f"[error]Unsupported or unknown shell: '{shell}'. "
            "Supported shells are: bash, zsh, fish[/error]"
        )
        sys.exit(1)
    return shell


def _install_completion(ctx: click.Context, shell: str) -> None:
    settings = _COMPLETION[shell]
    completion_cls = get_completion_class(shell)
    if completion_cls is None:  # pragma: no cover - all three shells are built in
        raise click.ClickException(f"Click has no completion support for {shell}")
    script = completion_cls(ctx.command, {}, "ldapie", "_LDAPIE_COMPLETE").source()

    target = os.path.expanduser(settings.file)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(script)
    console.print(f"[success]Completion for {shell} installed to {target}[/success]")

    if settings.rcfile:
        rcfile = os.path.expanduser(settings.rcfile)
        content = ""
        if os.path.exists(rcfile):
            with open(rcfile, "r", encoding="utf-8") as f:
                content = f.read()
        if _RC_MARKER not in content:
            with open(rcfile, "a", encoding="utf-8") as f:
                f.write(f"\n{_RC_MARKER}\n{settings.rc_lines}\n")
            console.print(f"[info]Added completion setup to {rcfile}[/info]")

    console.print(
        "[info]Restart your shell or source its config file to enable completions.[/info]"
    )


@click.group(name="ldapie", invoke_without_command=True, no_args_is_help=True)
@click.version_option(version=__version__)
@click.option(
    "--install-completion",
    is_flag=True,
    help="Install completion for the current shell.",
)
@click.option(
    "--show-completion",
    is_flag=True,
    help="Show how to enable completion for the current shell.",
)
@click.option(
    "--demo", is_flag=True, help="Run the automated demo with mock LDAP server."
)
@click.option(
    "--debug", is_flag=True, help="Enable debug mode for detailed error output."
)
@add_rich_help_option
@click.pass_context
def cli(ctx, install_completion=False, show_completion=False, demo=False, debug=False):
    """LDAPie - A modern LDAP client"""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["config"] = load_config(
        warn=lambda message: err_console.print(
            f"[warning]Config: {escape(message)}[/warning]"
        )
    )

    theme = ctx.obj["config"].get("theme")
    if theme and "LDAPIE_THEME" not in os.environ:
        _apply_theme(theme)

    if debug:
        err_console.print("[bold red]Debug mode enabled.[/bold red]")

    if demo:
        from . import demo as demo_module

        console.print("[info]Starting the automated LDAPie demo...[/info]")
        demo_module.run_demo()
        ctx.exit(0)

    if show_completion:
        shell = _detect_shell()
        console.print(f"# Add this line to your {shell} config to enable completion:")
        console.print(_COMPLETION[shell].activate, markup=False, highlight=False)
        ctx.exit(0)

    if install_completion:
        _install_completion(ctx, _detect_shell())
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("search")
@click.argument("host")
@click.argument("base_dn")
@click.argument("filter_query", default="(objectClass=*)")
@connection_options
@click.option(
    "-a",
    "--attrs",
    multiple=True,
    help="Attributes to fetch (can be used multiple times)",
)
@click.option(
    "--scope",
    type=click.Choice(["base", "one", "sub"]),
    default="sub",
    help="Search scope",
)
@click.option("--limit", type=int, help="Maximum number of entries to return")
@click.option(
    "--page-size",
    type=click.IntRange(min=0),
    default=DEFAULT_PAGE_SIZE,
    show_default=True,
    help="Page size for paged results (0 disables paging)",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--ldif", is_flag=True, help="Output in LDIF format")
@click.option("--csv", is_flag=True, help="Output in CSV format")
@click.option("--tree", is_flag=True, help="Display results as a tree")
@click.option("--output", "output_file", help="Save results to a file")
@click.option("--theme", type=click.Choice(["dark", "light"]), help="Color theme")
@add_rich_help_option
@handle_connection_error
def search_command(
    host,
    base_dn,
    filter_query,
    ldap_config,
    attrs,
    scope,
    limit,
    page_size,
    json_output,
    ldif,
    csv,
    tree,
    output_file,
    theme,
):
    """
    Search the LDAP directory.

    Results are fetched in pages (--page-size) so server size limits do not
    cut them short. Status messages go to stderr, so --json, --ldif and
    --csv output can be piped.

    Example:
        ldapie search ldap.example.com dc=example,dc=com "(objectClass=person)" \\
                --attrs cn --attrs mail --limit 100
    """
    if theme:
        _apply_theme(theme)

    _validate_filter_or_exit(filter_query)

    server, conn = ldap_config.get_connection()

    search_scope = {"base": BASE, "one": LEVEL, "sub": SUBTREE}[scope]
    attributes = list(attrs) if attrs else ALL_ATTRIBUTES

    err_console.print(f"[info]Searching {host} with filter: {filter_query}[/info]")

    if page_size:
        entries = search_utils.paged_search(
            conn, base_dn, filter_query, search_scope, attributes, page_size, limit
        )
    else:
        conn.search(
            base_dn,
            filter_query,
            search_scope=search_scope,
            attributes=attributes,
            size_limit=limit or 0,
        )
        entries = conn.entries
    _warn_if_truncated(conn, len(entries), limit)

    if len(entries) == 0:
        err_console.print("[warning]No entries found.[/warning]")
        return

    help_context = HelpContext()
    help_context.current_context["base_dn"] = base_dn
    help_context.current_context["filter"] = filter_query
    help_context.current_context["attributes"] = attributes

    err_console.print(f"[success]Found {len(entries)} entries.[/success]")

    if json_output:
        output_utils.output_json(entries, output_file)
    elif ldif:
        output_utils.output_ldif(entries, output_file)
    elif csv:
        output_utils.output_csv(entries, output_file)
    elif tree:
        output_utils.output_tree(entries, base_dn, console, output_file)
    else:
        output_utils.output_rich(entries, console, output_file)


@cli.command("info")
@click.argument("host")
@connection_options
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@add_rich_help_option
@handle_connection_error
def info_command(host, ldap_config, json_output):
    """Show information about LDAP server"""
    server, conn = ldap_config.get_connection()

    if json_output:
        schema_utils.output_server_info_json(server, err_console)
    else:
        schema_utils.output_server_info_rich(server, console)


@cli.command("compare")
@click.argument("host")
@click.argument("dn1")
@click.argument("dn2")
@connection_options
@click.option(
    "-a",
    "--attrs",
    multiple=True,
    help="Attributes to compare (can be used multiple times)",
)
@add_rich_help_option
@handle_connection_error
def compare_command(host, dn1, dn2, ldap_config, attrs):
    """Compare two LDAP entries"""
    for dn_val in (dn1, dn2):
        _validate_dn_or_exit(dn_val)

    server, conn = ldap_config.get_connection()
    search_utils.compare_entries(conn, dn1, dn2, attrs, console)


@cli.command("schema")
@click.argument("host")
@click.argument("object_class", required=False)
@connection_options
@click.option("--attr", help="Display information about specific attribute")
@add_rich_help_option
@handle_connection_error
def schema_command(host, object_class, ldap_config, attr):
    """Get schema information from LDAP server"""
    server, conn = ldap_config.get_connection()
    schema_utils.show_schema(server, object_class, attr, console)


@cli.command("add")
@click.argument("host")
@click.argument("dn")
@connection_options
@click.option(
    "-c", "--class", "object_class", multiple=True, help="Object class for new entry"
)
@click.option(
    "-a", "--attr", multiple=True, help="Attribute to add in the format name=value"
)
@click.option(
    "--ldif-file",
    "ldif_file",
    type=click.Path(exists=True, dir_okay=False),
    help="LDIF file with one entry whose attributes to add",
)
@click.option(
    "--json-file",
    "json_file",
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file containing entry attributes",
)
@add_rich_help_option
@handle_connection_error
def add_command(host, dn, ldap_config, object_class, attr, ldif_file, json_file):
    """Add a new entry to the LDAP directory"""
    _validate_dn_or_exit(dn)

    attributes: Dict[str, Any] = {}

    def add_values(name: str, values) -> None:
        values = values if isinstance(values, list) else [values]
        attributes.setdefault(name, []).extend(values)

    if object_class:
        add_values("objectClass", list(object_class))

    if ldif_file:
        with open(ldif_file, "r", encoding="utf-8") as f:
            records = parse_ldif(f.read())
        if len(records) != 1:
            err_console.print(
                f"[error]{ldif_file} has {len(records)} entries; --ldif-file takes "
                "exactly one. Use 'ldapie import' for several entries.[/error]"
            )
            sys.exit(1)
        for name, values in records[0][1].items():
            add_values(name, values)

    if json_file:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json_lib.load(f)
        if not isinstance(json_data, dict):
            err_console.print(
                f"[error]{json_file} must contain a JSON object of attributes[/error]"
            )
            sys.exit(1)
        for name, values in json_data.items():
            add_values(name, values)

    for item in attr:
        name, sep, value = item.partition("=")
        if not sep or not name:
            err_console.print(
                f"[error]Invalid attribute format: {item}. Use name=value[/error]"
            )
            sys.exit(1)
        add_values(name, value)

    server, conn = ldap_config.get_connection()

    if conn.add(dn, attributes=attributes):
        console.print(f"[success]Successfully added entry: {dn}[/success]")
    else:
        err_console.print(f"[error]Failed to add entry: {conn.result}[/error]")
        sys.exit(1)


@cli.command("delete")
@click.argument("host")
@click.argument("dn")
@connection_options
@click.option(
    "--recursive", is_flag=True, help="Delete the entry and everything below it"
)
@click.option(
    "-y", "--yes", is_flag=True, help="Do not ask for confirmation (with --recursive)"
)
@add_rich_help_option
@handle_connection_error
def delete_command(host, dn, ldap_config, recursive, yes):
    """Delete an entry from the LDAP directory"""
    _validate_dn_or_exit(dn)

    if recursive and not yes:
        click.confirm(
            f"Delete {dn} and ALL entries below it on {host}?",
            abort=True,
            err=True,
        )

    server, conn = ldap_config.get_connection()

    try:
        count = entry_utils.delete_entry(conn, dn, recursive=recursive)
    except RuntimeError as e:
        err_console.print(f"[error]Failed to delete entry: {e}[/error]")
        sys.exit(1)
    suffix = f" ({count} entries)" if recursive else ""
    console.print(f"[success]Successfully deleted entry: {dn}{suffix}[/success]")


@cli.command("modify")
@click.argument("host")
@click.argument("dn")
@connection_options
@click.option("--add", multiple=True, help="Add a value: name=value (can be repeated)")
@click.option(
    "--replace",
    multiple=True,
    help="Replace all values: name=value (bare name clears the attribute)",
)
@click.option(
    "--delete",
    multiple=True,
    help="Delete a value (name=value) or the whole attribute (name)",
)
@click.option(
    "--file",
    type=click.Path(exists=True, dir_okay=False),
    help='JSON file with ldap3 changes: {"attr": [["MODIFY_REPLACE", ["value"]]]}',
)
@add_rich_help_option
@handle_connection_error
def modify_command(host, dn, ldap_config, add, replace, delete, file):
    """Modify an existing LDAP entry"""
    _validate_dn_or_exit(dn)

    if file:
        with open(file, "r", encoding="utf-8") as f:
            changes = json_lib.load(f)
    else:
        changes = general_utils.parse_modification_attributes(add, replace, delete)

    if not changes:
        err_console.print("[error]No changes specified.[/error]")
        sys.exit(1)

    server, conn = ldap_config.get_connection()

    if conn.modify(dn, changes):
        console.print(f"[success]Successfully modified entry: {dn}[/success]")
    else:
        err_console.print(f"[error]Failed to modify entry: {conn.result}[/error]")
        sys.exit(1)


@cli.command("rename")
@click.argument("host")
@click.argument("dn")
@click.argument("new_rdn")
@connection_options
@click.option(
    "--delete-old-rdn/--keep-old-rdn",
    default=True,
    show_default=True,
    help="Remove the old RDN value from the entry, or keep it as an attribute value",
)
@click.option("--parent", help="New parent DN")
@add_rich_help_option
@handle_connection_error
def rename_command(host, dn, new_rdn, ldap_config, delete_old_rdn, parent):
    """Rename or move an LDAP entry"""
    _validate_dn_or_exit(dn)

    server, conn = ldap_config.get_connection()

    if conn.modify_dn(dn, new_rdn, delete_old_dn=delete_old_rdn, new_superior=parent):
        console.print("[success]Successfully renamed entry[/success]")
    else:
        err_console.print(f"[error]Failed to rename entry: {conn.result}[/error]")
        sys.exit(1)


@cli.command("interactive")
@click.option("--host", help="LDAP server hostname")
@connection_options
@click.option("--base", help="Base DN for operations")
@add_rich_help_option
@handle_connection_error
def interactive_command(host, ldap_config, base):
    """Start interactive LDAP console"""
    console.print("[info]Starting interactive mode[/info]")

    if ldap_config:
        server, conn = ldap_config.get_connection()
        interactive_utils.start_interactive_session(server, conn, console, base)
    else:
        interactive_utils.start_interactive_session(None, None, console, base)


@cli.command("export")
@click.argument("host")
@click.argument("base_dn")
@click.argument("filter_query", default="(objectClass=*)")
@connection_options
@click.option("--output", "output_file", required=True, help="Output file path")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["ldif", "json"]),
    default="ldif",
    help="Export format",
)
@add_rich_help_option
@handle_connection_error
def export_command(host, base_dn, filter_query, ldap_config, output_file, fmt):
    """Export LDAP entries to a file"""
    _validate_filter_or_exit(filter_query)

    server, conn = ldap_config.get_connection()
    entries = search_utils.paged_search(
        conn, base_dn, filter_query, SUBTREE, ALL_ATTRIBUTES, DEFAULT_PAGE_SIZE
    )
    _warn_if_truncated(conn, len(entries), None)

    if not entries:
        err_console.print("[warning]No entries found to export.[/warning]")
        return

    if fmt == "json":
        output_utils.output_json(entries, output_file)
    else:
        output_utils.output_ldif(entries, output_file)

    console.print(
        f"[success]Exported {len(entries)} entries to {output_file}[/success]"
    )


@cli.command("import")
@click.argument("host")
@click.argument("ldif_file", type=click.Path(exists=True, dir_okay=False))
@connection_options
@add_rich_help_option
@handle_connection_error
def import_command(host, ldif_file, ldap_config):
    """Import LDAP entries from an LDIF file

    Every entry is attempted; failures are reported and the command exits
    with status 1 if any entry could not be added.
    """
    with open(ldif_file, "r", encoding="utf-8") as f:
        records = parse_ldif(f.read())
    if not records:
        err_console.print("[warning]No entries found in LDIF file.[/warning]")
        return

    server, conn = ldap_config.get_connection()

    success_count = 0
    error_count = 0
    for dn, attributes in records:
        try:
            added = conn.add(dn, attributes=attributes)
        except LDAPException as e:
            added = False
            err_console.print(f"[error]Failed to add {dn}: {e}[/error]")
        else:
            if not added:
                err_console.print(f"[error]Failed to add {dn}: {conn.result}[/error]")
        if added:
            success_count += 1
        else:
            error_count += 1

    style = "error" if error_count else "success"
    console.print(
        f"[{style}]Import complete: {success_count} added, {error_count} errors[/{style}]"
    )
    if error_count:
        sys.exit(1)


if __name__ == "__main__":
    cli()

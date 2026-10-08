#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive shell functionality for LDAPie.
"""

import cmd
import os
import shlex
from textwrap import dedent
from typing import Any, Optional

from ldap3 import ALL_ATTRIBUTES, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPException
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .help_context import (
    CONNECT_SYNTAX,
    CommandValidator,
    HelpContext,
    parse_connect_args,
)
from .help_overlay import show_help_overlay
from .output import output_rich, safe_text
from .schema import output_server_info_rich, show_schema
from .search import paged_search
from .tab_completion import QueryHistory, TabCompletion, readline
from .utils import validate_dn, validate_search_filter

SEARCH_PAGE_SIZE = 500

SHELL_HELP = dedent(f"""\
    Available commands:
    - {CONNECT_SYNTAX}
                                             Connect to LDAP server
    - base <dn>                              Set base DN for operations
    - search [filter] [attributes...]        Search the directory
    - info                                   Show server information
    - schema [objectclass|--attr name]       Browse schema information
    - validate <command>                     Validate a command without executing it
    - suggest                                Show context-aware suggestions
    - history [search|base|host]             View query history
    - help [command]                         Show help for commands
    - exit, quit, Ctrl-D                     Exit interactive mode

    TIP: End a partial command with '?' (e.g. 'search ?') for context-sensitive help
    TIP: Press TAB to use command auto-completion""")


class LDAPShell(cmd.Cmd):
    intro: Optional[str] = (
        "\nWelcome to LDAPie interactive console. Type help or ? to list commands.\n"
    )
    prompt = "ldapie> "

    def __init__(
        self,
        server: Optional[Server],
        conn: Optional[Connection],
        console: Console,
        base_dn: Optional[str] = None,
    ):
        super().__init__()
        self.server = server
        self.conn = conn
        self.console = console
        self.base_dn = base_dn or ""
        self.connected = conn is not None and conn.bound
        self.help_context = HelpContext()
        self.query_history = QueryHistory()
        self.tab_completer = TabCompletion(self.query_history)

        self.history_file: Optional[str] = os.path.expanduser("~/.ldapie_history")
        if readline is not None:
            readline.set_completer_delims(" \t\n")
            try:
                if os.path.exists(self.history_file):
                    readline.read_history_file(self.history_file)
                    os.chmod(self.history_file, 0o600)
            except OSError as e:
                console.print(f"[warning]Could not read history file: {e}[/warning]")
                console.print("[info]History will not be saved.[/info]")
                self.history_file = None

        self._update_prompt()
        self.help_context.current_context["base_dn"] = self.base_dn or None
        self.help_context.update_session_state(
            connected=self.connected,
            authenticated=bool(conn is not None and conn.user),
            ssl_enabled=bool(
                conn is not None and (conn.server.ssl or conn.tls_started)
            ),
        )

    def _update_prompt(self) -> None:
        base_str = f" [{self.base_dn}]" if self.base_dn else ""
        self.prompt = f"ldapie{base_str}> "

    def complete(self, text, state):
        return self.tab_completer.complete(text, state)

    def cmdloop(self, intro: Optional[str] = None) -> None:
        """Run the loop; Ctrl-C cancels the current line, history is saved on exit."""
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.console.print(self.intro)
            self.intro = None

        try:
            while True:
                try:
                    super().cmdloop(intro="")
                    break
                except KeyboardInterrupt:
                    self.console.print("^C")
        finally:
            self._save_history()

    def _save_history(self) -> None:
        if readline is None or not self.history_file:
            return
        try:
            readline.set_history_length(1000)
            readline.write_history_file(self.history_file)
            os.chmod(self.history_file, 0o600)
        except OSError as e:
            self.console.print(f"[warning]Could not save history: {e}[/warning]")

    def precmd(self, line: str) -> str:
        """Show the help overlay for input ending in '?' instead of running it."""
        stripped = line.strip()
        if stripped.endswith("?") and stripped != "?":
            show_help_overlay(stripped[:-1].strip(), self.help_context, self.console)
            return ""
        return line

    def onecmd(self, line: str) -> bool:
        """Run one command; errors are reported and never end the session."""
        if not line:
            return False

        self.help_context.add_command(line)
        try:
            return bool(super().onecmd(line))
        except Exception as e:
            # Exception text can carry server data; see output.safe_text
            self.console.print(f"[error]Error: {safe_text(str(e))}[/error]")
            return False

    def default(self, line: str) -> None:
        self.console.print(
            f"[error]Unknown command: {line.split()[0]}. Type 'help' for a list.[/error]"
        )

    def do_validate(self, arg: str) -> None:
        """
        Validate a command without executing it
        Usage: validate <command>
        """
        if not arg:
            self.console.print("[error]Please provide a command to validate[/error]")
            return

        result = CommandValidator(self.help_context).validate_command(arg)

        # Help text contains [brackets]; escape it so Rich prints it as-is
        if "error" in result:
            self.console.print(f"[error]Error: {escape(result['error'])}[/error]")
            if "suggestion" in result:
                self.console.print(
                    f"[info]Suggestion: {escape(result['suggestion'])}[/info]"
                )
            if "examples" in result:
                self.console.print("\n[bold]Examples:[/bold]")
                for example in result["examples"]:
                    self.console.print(f"  [command]{escape(example)}[/command]")
        else:
            self.console.print(f"[success]✓ {escape(result['validation'])}[/success]")
            self.console.print(f"\n[bold]Preview:[/bold] {escape(result['preview'])}")
            if "warning" in result:
                self.console.print(
                    f"\n[warning]Warning: {escape(result['warning'])}[/warning]"
                )
            if "suggestion" in result:
                self.console.print(
                    f"\n[info]Suggestion: {escape(result['suggestion'])}[/info]"
                )

    def do_connect(self, arg: str) -> None:
        """
        Connect to an LDAP server
        Usage: connect host [port] [bind_dn] [--ssl] [--starttls] [--no-verify]
               [--ca-cert FILE]
        """
        # Imported here: ldapie.ldapie imports this module
        from .ldapie import LdapConfig

        try:
            args = parse_connect_args(shlex.split(arg))
        except ValueError as e:
            self.console.print(f"[error]Invalid arguments: {escape(str(e))}[/error]")
            self.console.print(Text(f"Usage: {CONNECT_SYNTAX}"))
            return

        config = LdapConfig(
            host=args.host,
            username=args.bind_dn,
            use_ssl="--ssl" in args.flags,
            port=args.port,
            starttls="--starttls" in args.flags,
            no_verify="--no-verify" in args.flags,
            ca_cert=os.path.expanduser(args.ca_cert) if args.ca_cert else None,
        )
        try:
            server, conn = config.get_connection()
        except (LDAPException, OSError) as e:
            # The server's diagnostic message is part of the exception text
            self.console.print(f"[error]Connection failed: {safe_text(str(e))}[/error]")
            return

        if self.conn is not None and self.conn is not conn:
            try:
                self.conn.unbind()
            except LDAPException:
                pass
        self.server, self.conn = server, conn
        self.connected = True
        self.console.print(f"[success]Connected to {escape(args.host)}[/success]")
        self.query_history.add_host(args.host)
        self._update_prompt()
        self.help_context.update_session_state(
            connected=True,
            authenticated=args.bind_dn is not None,
            ssl_enabled=args.encrypted,
        )

    def do_base(self, arg: str) -> None:
        """Set the base DN for operations"""
        if not arg:
            self.console.print(f"[info]Current base DN: {self.base_dn}[/info]")
            return
        try:
            validate_dn(arg)
        except ValueError as e:
            self.console.print(f"[error]{e}[/error]")
            return

        self.base_dn = arg
        self._update_prompt()
        self.console.print(f"[info]Base DN set to: {self.base_dn}[/info]")
        self.query_history.add_base(arg)
        self.help_context.current_context["base_dn"] = arg

    def do_search(self, arg: str) -> None:
        """
        Search the LDAP directory
        Usage: search [filter] [attribute1 attribute2 ...]
        """
        if not self.connected or not self.conn:
            self.console.print("[error]Not connected to any LDAP server[/error]")
            return

        if not self.base_dn:
            self.console.print(
                "[error]Base DN not set. Use 'base' command to set it.[/error]"
            )
            return

        try:
            args = shlex.split(arg)
        except ValueError:
            args = arg.split()

        filter_query = args[0] if args else "(objectClass=*)"
        attributes: Any = args[1:] if len(args) > 1 else ALL_ATTRIBUTES

        try:
            validate_search_filter(filter_query)
        except ValueError as e:
            self.console.print(f"[error]Invalid LDAP filter: {e}[/error]")
            return

        self.console.print(f"[info]Searching with filter: {filter_query}[/info]")
        try:
            entries = paged_search(
                self.conn,
                self.base_dn,
                filter_query,
                SUBTREE,
                attributes,
                SEARCH_PAGE_SIZE,
            )
        except LDAPException as e:
            self.console.print(f"[error]Search failed: {safe_text(str(e))}[/error]")
            return

        self.query_history.add_search(filter_query)
        self.help_context.update_search_results(entries)
        if not entries:
            self.console.print("[warning]No entries found.[/warning]")
            return

        self.console.print(f"[success]Found {len(entries)} entries.[/success]")
        output_rich(entries, self.console)

    def do_info(self, arg: str) -> None:
        """Show information about the connected LDAP server"""
        if not self.connected or not self.server or not self.conn:
            self.console.print("[error]Not connected to any LDAP server[/error]")
            return
        output_server_info_rich(self.server, self.console)

    def do_schema(self, arg: str) -> None:
        """
        View schema information
        Usage: schema [objectClass|--attr attribute_name]
        """
        if not self.connected or not self.server:
            self.console.print("[error]Not connected to any LDAP server[/error]")
            return

        args = arg.split()
        if not args:
            show_schema(self.server, None, None, self.console)
        elif args[0] == "--attr" and len(args) > 1:
            show_schema(self.server, None, args[1], self.console)
        else:
            show_schema(self.server, args[0], None, self.console)

    def do_exit(self, arg: str) -> bool:
        """Exit the interactive console"""
        self.console.print("[info]Exiting interactive mode.[/info]")
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the interactive console"""
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:  # the method name cmd.Cmd looks for
        """Exit on Ctrl-D or end of input"""
        self.console.print()
        return self.do_exit(arg)

    def do_suggest(self, arg: str) -> None:
        """Show context-aware suggestions based on current state"""
        suggestions = self.help_context.get_suggestions()

        self.console.print("\n[bold]Context-Aware Suggestions[/bold]")
        self.console.rule()

        if suggestions["next_commands"]:
            self.console.print("\n[bold]Next Steps[/bold]")
            for suggestion in suggestions["next_commands"]:
                self.console.print(f"  [success]• {escape(suggestion)}[/success]")

        if suggestions["examples"]:
            self.console.print("\n[bold]Examples[/bold]")
            for example in suggestions["examples"]:
                self.console.print(f"  [command]{escape(example)}[/command]")

        if suggestions["tips"]:
            self.console.print("\n[bold]Tips[/bold]")
            for tip in suggestions["tips"]:
                self.console.print(f"  [info]• {escape(tip)}[/info]")

        if not any(suggestions.values()):
            self.console.print(
                "  No specific suggestions available for current context."
            )

    def do_history(self, arg: str) -> None:
        """
        View query history
        Usage: history [search|base|host]
        """
        sources = {
            "search": ("Search History", "Filter", self.query_history.get_searches),
            "base": ("Base DN History", "DN", self.query_history.get_bases),
            "host": ("Host History", "Host", self.query_history.get_hosts),
        }

        if not arg:
            table = Table(title="Query History", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="green")
            for history_type, (_, _, getter) in sources.items():
                for value in getter():
                    table.add_row(history_type, value)
            self.console.print(table)
        elif arg in sources:
            title, column, getter = sources[arg]
            table = Table(title=title, show_header=True)
            table.add_column("#", style="dim")
            table.add_column(column, style="green")
            for i, value in enumerate(getter(), 1):
                table.add_row(str(i), value)
            self.console.print(table)
        else:
            self.console.print(f"[error]Unknown history type: {arg}[/error]")
            self.console.print("[info]Available types: search, base, host[/info]")

    def do_help(self, arg: str) -> None:
        """Show help for commands"""
        if arg:
            super().do_help(arg)
            cmd_help = self.help_context.get_command_help(arg)
            if cmd_help.get("examples"):
                self.console.print("\n[bold]Examples:[/bold]")
                for example in cmd_help["examples"]:
                    self.console.print(f"  [command]{escape(example)}[/command]")
            if cmd_help.get("common_errors"):
                self.console.print("\n[bold]Common Issues:[/bold]")
                for tip in cmd_help["common_errors"]:
                    self.console.print(f"  [info]• {escape(tip)}[/info]")
            return

        # Text, not markup: the usage lines contain [brackets]
        self.console.print(
            Panel(Text(SHELL_HELP), title="LDAPie Interactive Mode Help", expand=False)
        )
        suggestions = self.help_context.get_suggestions()
        if suggestions["next_commands"]:
            self.console.print("\n[bold]Suggested Next Steps[/bold]")
            for suggestion in suggestions["next_commands"]:
                self.console.print(f"  [success]• {escape(suggestion)}[/success]")
        if suggestions["tips"]:
            self.console.print("\n[bold]Tips[/bold]")
            for tip in suggestions["tips"]:
                self.console.print(f"  [info]• {escape(tip)}[/info]")


def start_interactive_session(
    server: Optional[Server],
    conn: Optional[Connection],
    console: Console,
    base_dn: Optional[str] = None,
) -> None:
    """
    Start an interactive LDAP console session.
    """
    shell = LDAPShell(server, conn, console, base_dn)
    if readline is not None:
        console.print("[info]Tab completion and query history enabled.[/info]")
    shell.cmdloop()

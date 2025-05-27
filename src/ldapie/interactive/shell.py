\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive shell functionality for LDAPie.
"""

import os
import cmd
import readline
from typing import Optional, Any, List, Dict
import ldap3
from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES
from rich.console import Console
from rich.panel import Panel
from getpass import getpass

# Assuming these are in the same directory or accessible via PYTHONPATH
from ..ui.output import output_rich 
from ..operations.schema import output_server_info_rich, show_schema

# Import context-sensitive help components if available
try:
    from .help_context import HelpContext, CommandValidator
    from .help_overlay import show_help_overlay
    help_available = True
except ImportError:
    help_available = False
    HelpContext = None 
    CommandValidator = None
    show_help_overlay = None


class LDAPShell(cmd.Cmd):
    intro = "\\nWelcome to LDAPie interactive console. Type help or ? to list commands.\\n"
    prompt = "ldapie> "
    
    def __init__(self, server: Optional[Server], conn: Optional[Connection], console: Console, base_dn: Optional[str] = None):
        super().__init__()
        self.server = server
        self.conn = conn
        self.console = console
        self.base_dn = base_dn or ""
        self.connected = conn is not None and conn.bound
        self.help_context = HelpContext() if help_available and HelpContext else None
        self.search_history: List[str] = []
        self.query_history: Dict[str, List[str]] = {
            'search': [],    # Store search filters
            'base': [],      # Store base DNs
            'host': []       # Store host names
        }
        
        # Set up readline for tab completion and history
        readline.set_completer_delims(' \\t\\n')
        # The completer will be set by enhance_shell if available
        # readline.set_completer(self.complete) 
        readline.parse_and_bind('tab: complete')
        
        self.history_file = os.path.expanduser('~/.ldapie_history')
        try:
            history_dir = os.path.dirname(self.history_file)
            if not os.path.exists(history_dir) and history_dir:
                try:
                    os.makedirs(history_dir, exist_ok=True)
                except (OSError, PermissionError) as e:
                    console.print(f"[warning]Could not create history directory: {e}[/warning]")
    
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
    
        except (OSError, IOError, PermissionError) as e:
            console.print(f"[warning]Could not read history file: {e}[/warning]")
            console.print("[info]History will not be saved.[/info]")
            self.history_file = None # type: ignore
        
        self._update_prompt()
        
        if help_available and self.help_context:
            self.help_context.update_session_state(
                connected=self.connected,
                server=self.server,
                connection=self.conn,
                authenticated=self.connected and self.conn.bound if self.conn else False
            )
    
    def _update_prompt(self):
        base_str = f" [{self.base_dn}]" if self.base_dn else ""
        self.prompt = f"ldapie{base_str}> "
    
    def cmdloop(self, intro: Optional[str] = None) -> None:
        """Override cmdloop to add custom command processing and history saving."""
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.console.print(self.intro)
            self.intro = None
            
        try:
            super().cmdloop(intro=None)
        finally:
            if hasattr(self, 'history_file') and self.history_file:
                try:
                    readline.set_history_length(1000)
                    readline.write_history_file(self.history_file)
                except (OSError, IOError, PermissionError) as e:
                    self.console.print(f"[warning]Could not save history: {e}[/warning]")

    def get_input(self, prompt: str) -> str:
        """Custom input handler that supports '?' for context help"""
        line = input(prompt)
        
        if help_available and show_help_overlay and self.help_context and ('?' in line):
            if ' ?' in line:
                line_without_question = line.replace(' ?', '').strip()
            else:
                line_without_question = line.replace('?', '').strip()
            
            show_help_overlay(line_without_question, self.help_context, self.console)
            return "" 
        
        return line
    
    def onecmd(self, line: str) -> bool:
        """Override onecmd to add command history and validation"""
        if not line:
            return False # type: ignore
            
        if help_available and self.help_context:
            self.help_context.add_command(line)
            
        return super().onecmd(line) # type: ignore

    def do_validate(self, arg: str) -> None:
        """
        Validate a command without executing it
        Usage: validate <command>
        """
        if not arg:
            self.console.print("[error]Please provide a command to validate[/error]")
            return
            
        if not help_available or not CommandValidator:
            self.console.print("[error]Command validation is not available[/error]")
            return
        
        validator = CommandValidator(self.help_context) # type: ignore
        result = validator.validate_command(arg)
        
        if "error" in result:
            self.console.print(f"[error]Error: {result['error']}[/error]")
            if "suggestion" in result:
                self.console.print(f"[info]Suggestion: {result['suggestion']}[/info]")
            if "examples" in result:
                self.console.print("\\n[bold]Examples:[/bold]")
                for example in result['examples']:
                    self.console.print(f"  [command]{example}[/command]")
        else:
            if "validation" in result:
                self.console.print(f"[success]✓ {result['validation']}[/success]")
            if "preview" in result:
                self.console.print(f"\\n[bold]Preview:[/bold] {result['preview']}")
            if "warning" in result:
                self.console.print(f"\\n[warning]Warning: {result['warning']}[/warning]")
            if "suggestion" in result:
                self.console.print(f"\\n[info]Suggestion: {result['suggestion']}[/info]")
        
    def do_connect(self, arg: str) -> None:
        """
        Connect to an LDAP server
        Usage: connect host [port] [username] [--ssl]
        """
        args = arg.split()
        if not args:
            self.console.print("[error]Must specify a hostname[/error]")
            return
            
        host = args[0]
        port_str = args[1] if len(args) > 1 and args[1].isdigit() else None
        port = int(port_str) if port_str else None
        username = args[2] if len(args) > 2 and not args[2].startswith('-') else None
        use_ssl = '--ssl' in args
        
        try:
            server_uri = f"{'ldaps' if use_ssl else 'ldap'}://{host}"
            if port:
                server_uri += f":{port}"
                
            self.server = ldap3.Server(server_uri, get_info=ldap3.ALL)
            
            if username:
                password = getpass(f"Password for {username}: ")
                self.conn = ldap3.Connection(self.server, user=username, password=password, auto_bind=True)
            else:
                self.conn = ldap3.Connection(self.server, auto_bind=True)
                
            self.connected = True
            self.console.print(f"[success]Connected to {host}[/success]")
            
            if host not in self.query_history.get('host', []):
                self.query_history.setdefault('host', []).append(host)
                self.query_history['host'] = self.query_history['host'][-20:]
            
            self._update_prompt()
            
            if help_available and self.help_context:
                self.help_context.update_session_state(
                    connected=True,
                    authenticated=username is not None,
                    server=self.server,
                    connection=self.conn,
                    ssl_enabled=use_ssl
                )
            
        except Exception as e:
            self.console.print(f"[error]Connection failed: {e}[/error]")
            if help_available and self.help_context:
                self.help_context.add_error("connect " + arg, str(e))
    
    def do_base(self, arg: str) -> None:
        """Set the base DN for operations"""
        if arg:
            self.base_dn = arg
            self._update_prompt()
            self.console.print(f"[info]Base DN set to: {self.base_dn}[/info]")
            
            if arg not in self.query_history.get('base', []):
                self.query_history.setdefault('base', []).append(arg)
                self.query_history['base'] = self.query_history['base'][-20:]
            
            if help_available and self.help_context:
                self.help_context.current_context["base_dn"] = arg
        else:
            self.console.print(f"[info]Current base DN: {self.base_dn}[/info]")
    
    def do_search(self, arg: str) -> None:
        """
        Search the LDAP directory
        Usage: search [filter] [attribute1 attribute2 ...]
        """
        if not self.connected or not self.conn:
            self.console.print("[error]Not connected to any LDAP server[/error]")
            return
            
        if not self.base_dn:
            self.console.print("[error]Base DN not set. Use 'base' command to set it.[/error]")
            return
            
        import shlex
        try:
            args = shlex.split(arg)
        except ValueError:
            args = arg.split()
            
        filter_query = args[0] if args else "(objectClass=*)"
        attributes = args[1:] if len(args) > 1 else ALL_ATTRIBUTES
        
        if filter_query.startswith(("'", '"')) and filter_query.endswith(("'", '"')):
            filter_query = filter_query[1:-1]
        
        try:
            self.console.print(f"[info]Searching with filter: {filter_query}[/info]")
            self.conn.search(
                self.base_dn, 
                filter_query, 
                search_scope=SUBTREE, 
                attributes=attributes
            )
            
            if not self.conn.entries:
                self.console.print("[warning]No entries found.[/warning]")
                return
                
            self.console.print(f"[success]Found {len(self.conn.entries)} entries.[/success]")
            output_rich(self.conn.entries, self.console) # type: ignore
            
            if filter_query not in self.search_history:
                self.search_history.append(filter_query)
                if len(self.search_history) > 20:
                    self.search_history = self.search_history[-20:]
            
            if filter_query not in self.query_history.get('search', []):
                self.query_history.setdefault('search', []).append(filter_query)
                self.query_history['search'] = self.query_history['search'][-20:]
            
            if help_available and self.help_context:
                self.help_context.update_search_results(self.conn.entries)
            
        except Exception as e:
            self.console.print(f"[error]Search failed: {e}[/error]")
            if help_available and self.help_context:
                self.help_context.add_error("search " + arg, str(e))
    
    def do_info(self, arg: str) -> None:
        """Show information about the connected LDAP server"""
        if not self.connected or not self.server or not self.conn:
            self.console.print("[error]Not connected to any LDAP server[/error]")
            return
        output_server_info_rich(self.server, self.conn, self.console)
    
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
        elif args[0] == '--attr' and len(args) > 1:
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
        
    def do_suggest(self, arg: str) -> None:
        """Show context-aware suggestions based on current state"""
        if not help_available or not self.help_context:
            self.console.print("[error]Context-sensitive help is not available[/error]")
            return
            
        suggestions = self.help_context.get_suggestions()
        
        self.console.print("\\n[bold]Context-Aware Suggestions[/bold]")
        self.console.rule()
        
        if suggestions["next_commands"]:
            self.console.print("\\n[bold]Next Steps[/bold]")
            for suggestion in suggestions["next_commands"]:
                self.console.print(f"  [success]• {suggestion}[/success]")
                
        if suggestions["examples"]:
            self.console.print("\\n[bold]Examples[/bold]")
            for example in suggestions["examples"]:
                self.console.print(f"  [command]{example}[/command]")
                
        if suggestions["tips"]:
            self.console.print("\\n[bold]Tips[/bold]")
            for tip in suggestions["tips"]:
                self.console.print(f"  [info]• {tip}[/info]")
                
        if not any([suggestions["next_commands"], suggestions["examples"], suggestions["tips"]]):
            self.console.print("  No specific suggestions available for current context.")
            
    def do_history(self, arg: str) -> None:
        """
        View command history or specific query types
        Usage: history [search|base|host]
        """
        from rich.table import Table # Local import for this method
        
        if not arg:
            table = Table(title="Command History", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="green")
            
            for filter_query in self.search_history:
                table.add_row("search", filter_query)
            for base_dn_val in self.query_history.get('base', []): # Renamed to avoid conflict
                table.add_row("base", base_dn_val)
            for host_val in self.query_history.get('host', []): # Renamed to avoid conflict
                table.add_row("host", host_val)
            self.console.print(table)
        elif arg == "search":
            table = Table(title="Search History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("Filter", style="green")
            for i, filter_query in enumerate(self.search_history, 1):
                table.add_row(str(i), filter_query)
            self.console.print(table)
        elif arg == "base":
            table = Table(title="Base DN History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("DN", style="green")
            for i, base_dn_val in enumerate(self.query_history.get('base', []), 1): # Renamed
                table.add_row(str(i), base_dn_val)
            self.console.print(table)
        elif arg == "host":
            table = Table(title="Host History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("Host", style="green")
            for i, host_val in enumerate(self.query_history.get('host', []), 1): # Renamed
                table.add_row(str(i), host_val)
            self.console.print(table)
        else:
            self.console.print("[info]Available types: search, base, host[/info]")
            
    def do_help(self, arg: str) -> None:
        """Show help for commands"""
        if arg:
            super().do_help(arg)
            if help_available and self.help_context:
                cmd_help = self.help_context.get_command_help(arg)
                if 'examples' in cmd_help and cmd_help['examples']:
                    self.console.print("\\n[bold]Examples:[/bold]")
                    for example in cmd_help['examples']:
                        self.console.print(f"  [command]{example}[/command]")
                if 'common_errors' in cmd_help and cmd_help['common_errors']:
                    self.console.print("\\n[bold]Common Issues:[/bold]")
                    for tip in cmd_help['common_errors']:
                        self.console.print(f"  [info]• {tip}[/info]")
        else:
            self.console.print(
                Panel(
                    """
                    Available commands:
                    - connect host [port] [username] [--ssl]  Connect to LDAP server
                    - base <dn>                              Set base DN for operations
                    - search [filter] [attributes...]         Search the directory
                    - info                                   Show server information
                    - schema [objectclass|--attr name]        Browse schema information
                    - validate <command>                      Validate a command without executing it
                    - suggest                                 Show context-aware suggestions
                    - history                                View command history
                    - help [command]                         Show help for commands
                    - exit, quit                             Exit interactive mode
                    
                    TIP: Type '?' after any partial command (e.g., 'search?' or 'search ?') to get context-sensitive help
                    TIP: Press TAB to use command auto-completion
                    """,
                    title="LDAPie Interactive Mode Help",
                    expand=False
                )
            )
            if help_available and self.help_context:
                suggestions = self.help_context.get_suggestions()
                if suggestions["next_commands"]:
                    self.console.print("\\n[bold]Suggested Next Steps[/bold]")
                    for suggestion in suggestions["next_commands"]:
                        self.console.print(f"  [success]• {suggestion}[/success]")
                if suggestions["tips"]:
                    self.console.print("\\n[bold]Tips[/bold]")
                    for tip in suggestions["tips"]:
                        self.console.print(f"  [info]• {tip}[/info]")

def start_interactive_session(server: Optional[Server], conn: Optional[Connection], console: Console, base_dn: Optional[str] = None) -> None:
    """
    Start an interactive LDAP console session.
    """
    shell = LDAPShell(server, conn, console, base_dn)
    try:
        from .shell_enhancements import enhance_shell # Relative import
        shell = enhance_shell(shell) # type: ignore
        console.print("[info]Tab completion and query history enabled.[/info]")
    except ImportError:
        console.print("[warning]Tab completion and query history features not available.[/warning]")
    except Exception as e:
        console.print(f"[warning]Could not enhance shell: {e}[/warning]")

    shell.cmdloop()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context-sensitive help for the LDAPie interactive shell.

The shell owns one HelpContext, feeds it every command line and error, and
asks it for command help (``help <command>``, ``?``), suggestions
(``suggest``) and dry-run validation (``validate <command>``).

Key components:
- COMMAND_PATTERNS: syntax, examples and tips for every shell command
- HelpContext: tracks command history, session state and the current operation
- CommandValidator: checks a shell command without running it
"""

import shlex
from collections import defaultdict, deque
from difflib import get_close_matches
from typing import Any, Callable, Deque, Dict, List, Optional

from .utils import validate_dn, validate_search_filter

CONNECT_FLAGS = ("--ssl", "--starttls", "--no-verify")

# The shell's commands: syntax, examples, next steps and common errors
COMMAND_PATTERNS: Dict[str, Dict[str, Any]] = {
    "connect": {
        "syntax": "connect host [port] [bind_dn] [--ssl] [--starttls] [--no-verify]",
        "examples": [
            "connect ldap.example.com",
            "connect ldap.example.com 636 cn=admin,dc=example,dc=com --ssl",
            "connect ldap.example.com 389 cn=admin,dc=example,dc=com --starttls",
        ],
        "next_steps": [
            "Set the base DN: base dc=example,dc=com",
            "Check the server: info",
        ],
        "common_errors": [
            "Without a bind DN the connection is anonymous",
            "You are prompted for the password (or set LDAP_PASSWORD)",
            "--no-verify disables certificate checks; use it only for testing",
        ],
    },
    "base": {
        "syntax": "base <dn>",
        "examples": ["base dc=example,dc=com", "base ou=people,dc=example,dc=com"],
        "next_steps": ["Search below the base DN: search (objectClass=*)"],
        "common_errors": ["The DN must be well-formed: ou=people,dc=example,dc=com"],
    },
    "search": {
        "syntax": "search [filter] [attribute...]",
        "examples": [
            "search",
            "search (objectClass=person)",
            "search (uid=j*) cn mail",
            "search '(&(objectClass=person)(mail=*@example.com))' cn",
        ],
        "next_steps": [
            "Narrow the results with a filter: search (uid=admin)",
            "Fetch only some attributes: search (objectClass=person) cn mail",
            "Look up an object class: schema person",
        ],
        "common_errors": [
            "Filters must be enclosed in parentheses",
            "Quote a filter that contains spaces",
            "Set the base DN first: base <dn>",
        ],
    },
    "info": {
        "syntax": "info",
        "examples": ["info"],
        "next_steps": ["Browse the schema: schema"],
        "common_errors": ["Requires a connection (connect first)"],
    },
    "schema": {
        "syntax": "schema [objectClass|--attr name]",
        "examples": ["schema", "schema inetOrgPerson", "schema --attr mail"],
        "next_steps": ["Search for entries of a class: search (objectClass=person)"],
        "common_errors": ["The object class or attribute may not exist in the schema"],
    },
    "validate": {
        "syntax": "validate <command>",
        "examples": [
            "validate search (uid=admin) cn",
            "validate connect ldap.example.com 636 --ssl",
        ],
    },
    "suggest": {"syntax": "suggest", "examples": ["suggest"]},
    "history": {
        "syntax": "history [search|base|host]",
        "examples": ["history", "history search"],
        "common_errors": ["The history type must be search, base or host"],
    },
    "help": {"syntax": "help [command]", "examples": ["help", "help search"]},
    "exit": {"syntax": "exit", "examples": ["exit"]},
    "quit": {"syntax": "quit", "examples": ["quit"]},
}


# Commands about the shell itself; they do not become the "current operation"
META_COMMANDS = {"help", "suggest", "validate", "history", "exit", "quit"}


def split_command(command_str: str) -> List[str]:
    """Split a command line like a shell does; fall back to whitespace."""
    try:
        return shlex.split(command_str)
    except ValueError:  # e.g. an unclosed quote while still typing
        return command_str.split()


class HelpContext:
    """
    Tracks the shell session for context-aware help.

    Attributes:
        command_history: Deque of recent command lines
        current_context: The current command, base DN and last search results
        session_state: Connection, authentication and TLS state
        command_frequency: How often each command was used
    """

    def __init__(self) -> None:
        self.command_history: Deque[str] = deque(maxlen=20)
        self.current_context: Dict[str, Any] = {
            "command": None,
            "base_dn": None,
            "search_results": None,
        }
        self.session_state = {
            "connected": False,
            "authenticated": False,
            "ssl_enabled": False,
        }
        self.command_frequency: Dict[str, int] = defaultdict(int)

    def add_command(self, command_str: str) -> None:
        """Record a command line; a directory operation becomes the current one."""
        self.command_history.append(command_str)
        parts = split_command(command_str)
        if not parts:
            return
        self.command_frequency[parts[0]] += 1
        if parts[0] in COMMAND_PATTERNS and parts[0] not in META_COMMANDS:
            self.current_context["command"] = parts[0]

    def update_session_state(
        self, connected: bool, authenticated: bool, ssl_enabled: bool
    ) -> None:
        """Record the connection state."""
        self.session_state = {
            "connected": connected,
            "authenticated": authenticated,
            "ssl_enabled": ssl_enabled,
        }

    def update_search_results(self, results: List[Any]) -> None:
        """Store the results of the last search."""
        self.current_context["search_results"] = results

    def get_suggestions(self) -> Dict[str, List[str]]:
        """Next steps, examples and tips for the current command and session state."""
        cmd_info = COMMAND_PATTERNS.get(self.current_context.get("command") or "", {})
        suggestions: Dict[str, List[str]] = {
            "next_commands": list(cmd_info.get("next_steps", [])),
            "examples": list(cmd_info.get("examples", [])),
            "tips": list(cmd_info.get("common_errors", [])),
        }

        connected = self.session_state["connected"]
        if not connected:
            suggestions["next_commands"].append(
                "Connect first: connect ldap.example.com"
            )
        elif not self.current_context.get("base_dn"):
            suggestions["next_commands"].append(
                "Set the base DN: base dc=example,dc=com"
            )

        if self.current_context.get("search_results"):
            suggestions["next_commands"].extend(
                [
                    "Look up an entry's object class: schema <objectClass>",
                    "Reuse an earlier filter: history search",
                ]
            )

        if connected and not self.session_state["authenticated"]:
            suggestions["tips"].append(
                "The bind is anonymous; reconnect with a bind DN for more privileges"
            )
        if connected and not self.session_state["ssl_enabled"]:
            suggestions["tips"].append(
                "The connection is not encrypted; reconnect with --ssl or --starttls"
            )

        return suggestions

    def get_command_help(self, command: str) -> Dict[str, Any]:
        """Help for a command, or an error with a "did you mean" suggestion."""
        cmd_info = COMMAND_PATTERNS.get(command)
        if cmd_info is not None:
            return cmd_info

        matches = get_close_matches(command, list(COMMAND_PATTERNS), n=1, cutoff=0.6)
        if matches:
            return {
                "error": f"Command '{command}' not found. Did you mean '{matches[0]}'?",
                "suggested_command": matches[0],
            }
        return {"error": f"Command '{command}' not found."}

    def analyze_command(self, command_str: str) -> Dict[str, Any]:
        """Check that a command exists and has its required arguments."""
        parts = split_command(command_str)
        if not parts:
            return {"error": "Empty command"}

        cmd = parts[0]
        cmd_info = self.get_command_help(cmd)
        if "error" in cmd_info:
            return cmd_info

        # Required arguments are the syntax words not wrapped in [ ]
        syntax = cmd_info["syntax"]
        required_count = sum(
            1 for word in syntax.split()[1:] if not word.startswith("[")
        )
        if len(parts) - 1 < required_count:
            return {
                "error": f"Not enough arguments for '{cmd}'. Syntax: {syntax}",
                "syntax": syntax,
                "examples": cmd_info.get("examples", []),
            }

        return {
            "command": cmd,
            "arguments": parts[1:],
            "syntax": syntax,
            "examples": cmd_info.get("examples", []),
        }


class CommandValidator:
    """Validates a shell command without running it and previews its effect."""

    def __init__(self, help_context: Optional[HelpContext] = None):
        self.help_context = help_context or HelpContext()

    def validate_command(self, command_str: str) -> Dict[str, Any]:
        """Return either an "error" or a "validation" with a "preview".

        "warning" and "suggestion" may accompany either.
        """
        analysis = self.help_context.analyze_command(command_str)
        if "error" in analysis:
            return analysis

        validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = getattr(
            self, f"_validate_{analysis['command']}", None
        )
        if validator is not None:
            return validator(analysis)
        return {
            **analysis,
            "validation": "Command structure looks valid",
            "preview": f"Would run: {command_str}",
        }

    @staticmethod
    def _error(
        analysis: Dict[str, Any], message: str, suggestion: Optional[str] = None
    ) -> Dict[str, Any]:
        result = {
            "error": message,
            "syntax": analysis["syntax"],
            "examples": analysis["examples"],
        }
        if suggestion:
            result["suggestion"] = suggestion
        return result

    def _validate_connect(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        args = analysis["arguments"]
        unknown = [a for a in args if a.startswith("--") and a not in CONNECT_FLAGS]
        if unknown:
            return self._error(
                analysis,
                f"Unknown option '{unknown[0]}'. Options: {', '.join(CONNECT_FLAGS)}",
            )

        positional = [a for a in args if not a.startswith("--")]
        host, rest = positional[0], positional[1:]
        port = 636 if "--ssl" in args else 389
        if rest and rest[0].isdigit():
            port = int(rest.pop(0))
            if not 0 < port < 65536:
                return self._error(analysis, f"Port {port} is out of range")
        bind_dn = rest[0] if rest else None
        if bind_dn:
            try:
                validate_dn(bind_dn)
            except ValueError as e:
                return self._error(analysis, str(e))

        encrypted = "--ssl" in args or "--starttls" in args
        result = {
            **analysis,
            "validation": "Connect command looks valid",
            "preview": f"Would connect to {host}:{port} as {bind_dn or 'anonymous'}"
            + (" over TLS" if encrypted else ""),
        }
        if "--no-verify" in args:
            result["warning"] = "Certificate verification would be disabled"
        elif not encrypted:
            result["warning"] = "The connection would not be encrypted"
            result["suggestion"] = "Add --ssl or --starttls"
        return result

    def _validate_base(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        dn = analysis["arguments"][0]
        try:
            validate_dn(dn)
        except ValueError as e:
            return self._error(analysis, str(e))
        return {
            **analysis,
            "validation": "Base command looks valid",
            "preview": f"Would set the base DN to {dn}",
        }

    def _validate_search(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        args = analysis["arguments"]
        filter_query = args[0] if args else "(objectClass=*)"
        try:
            validate_search_filter(filter_query)
        except ValueError as e:
            suggestion = None
            if not filter_query.startswith("("):
                suggestion = f"Try: search ({filter_query})"
            return self._error(analysis, f"Invalid LDAP filter: {e}", suggestion)

        base_dn = self.help_context.current_context.get("base_dn")
        preview = (
            f"Would search below {base_dn or '<base DN>'} with filter {filter_query}"
        )
        if len(args) > 1:
            preview += f", attributes: {', '.join(args[1:])}"
        result = {
            **analysis,
            "validation": "Search command looks valid",
            "preview": preview,
        }
        if not self.help_context.session_state["connected"]:
            result["warning"] = "Not connected; use connect first"
        elif not base_dn:
            result["warning"] = "The base DN is not set; use base <dn> first"
        return result

    def _validate_schema(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        args = analysis["arguments"]
        if args == ["--attr"]:
            return self._error(analysis, "--attr needs an attribute name")
        if args[:1] == ["--attr"]:
            preview = f"Would show the attribute type {args[1]}"
        elif args:
            preview = f"Would show the object class {args[0]}"
        else:
            preview = "Would list all object classes"
        return {
            **analysis,
            "validation": "Schema command looks valid",
            "preview": preview,
        }

    def _validate_history(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        args = analysis["arguments"]
        if args and args[0] not in ("search", "base", "host"):
            return self._error(
                analysis, f"Unknown history type '{args[0]}'; use search, base or host"
            )
        return {
            **analysis,
            "validation": "History command looks valid",
            "preview": f"Would show the {args[0] if args else 'whole'} history",
        }

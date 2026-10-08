#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help overlay for the LDAPie interactive shell.

Ending an input line with '?' ('search ?' or 'search?') shows help for what
is being typed instead of running it: the list of commands, or the syntax,
options, examples and recent values of the command.
"""

from typing import Any, Dict, List

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .help_context import COMMAND_PATTERNS, HelpContext, split_command

CONNECT_OPTIONS = [
    "--ssl: use an LDAPS connection",
    "--starttls: upgrade the connection with STARTTLS before binding",
    "--no-verify: skip certificate verification (insecure)",
]


def _recent_arguments(help_context: HelpContext, command: str) -> List[str]:
    """First arguments given to a command earlier in the session, newest first."""
    seen: List[str] = []
    for line in reversed(help_context.command_history):
        parts = split_command(line)
        if len(parts) > 1 and parts[0] == command and parts[1] not in seen:
            seen.append(parts[1])
    return seen[:3]


def get_help(input_text: str, help_context: HelpContext) -> Dict[str, Any]:
    """Build the help for the partial command line ``input_text``."""
    parts = input_text.split()

    if not parts:
        frequent = sorted(
            help_context.command_frequency.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return {
            "title": "Available Commands",
            "help_text": "Type a command, or 'help' for the full list.",
            "suggestions": list(COMMAND_PATTERNS),
            "frequent_commands": [cmd for cmd, count in frequent[:5] if count > 0],
        }

    cmd = parts[0]
    cmd_help = help_context.get_command_help(cmd)
    if "error" in cmd_help:
        suggested = cmd_help.get("suggested_command")
        return {
            "title": "Unknown Command",
            "help_text": cmd_help["error"],
            "suggestions": [suggested] if suggested else [],
        }

    help_info: Dict[str, Any] = {
        "title": f"Help for '{cmd}'",
        "help_text": f"Syntax: {cmd_help['syntax']}",
        "examples": cmd_help.get("examples", []),
        "tips": cmd_help.get("common_errors", []),
    }

    if cmd == "connect":
        help_info["options"] = CONNECT_OPTIONS
        recent = _recent_arguments(help_context, "connect")
        if recent:
            help_info["recent_usage"] = f"Recent hosts: {', '.join(recent)}"
    elif cmd == "base":
        recent = _recent_arguments(help_context, "base")
        if recent:
            help_info["recent_usage"] = f"Recent base DNs: {', '.join(recent)}"
    elif cmd == "search":
        base_dn = help_context.current_context.get("base_dn")
        recent = _recent_arguments(help_context, "search")
        notes = [f"Base DN: {base_dn}"] if base_dn else ["Base DN not set"]
        if recent:
            notes.append(f"Recent filters: {', '.join(recent)}")
        help_info["recent_usage"] = ". ".join(notes)
        if len(parts) > 1:
            help_info["help_text"] += "\nWords after the filter are attribute names."

    return help_info


def show_help_overlay(
    input_text: str, help_context: HelpContext, console: Console
) -> None:
    """Print the help panel for the partial command line ``input_text``."""
    help_info = get_help(input_text, help_context)

    table = Table(box=None, show_header=False, expand=True)
    table.add_column("Content", style="bright_white")

    table.add_row(f"[bold cyan]{escape(help_info['title'])}[/bold cyan]")
    table.add_row("")
    table.add_row(escape(help_info["help_text"]))
    table.add_row("")

    if help_info.get("recent_usage"):
        table.add_row(
            f"[bold magenta]{escape(help_info['recent_usage'])}[/bold magenta]"
        )
        table.add_row("")

    sections = [
        ("Frequently Used Commands:", "frequent_commands", "command", ""),
        ("Options:", "options", "option", ""),
        ("Tips & Common Issues:", "tips", "info", "• "),
        ("Examples:", "examples", "command", ""),
        ("Suggestions:", "suggestions", "success", "• "),
    ]
    for heading, key, style, bullet in sections:
        items = help_info.get(key)
        if not items:
            continue
        table.add_row(f"[bold]{heading}[/bold]")
        for item in items:
            table.add_row(f"  [{style}]{bullet}{escape(item)}[/{style}]")
        table.add_row("")

    console.print(
        Panel(table, title="[bold]Context Help[/bold]", border_style="bright_blue")
    )
    console.print(f"\nCurrent input: [command]{escape(input_text)}[/command]")

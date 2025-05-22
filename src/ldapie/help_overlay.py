#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help Overlay for LDAPie

This module provides an overlay UI for context-sensitive help that can be
triggered with the '?' key during command input. It displays relevant
suggestions, examples, and documentation based on the current command context.

Key functions:
- show_help_overlay: Display a help overlay based on current input
- process_help_key: Process the '?' key and determine if help overlay should be shown

Example:
    >>> from help_overlay import show_help_overlay
    >>> show_help_overlay(current_input, help_context, console)
"""

import re
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.markdown import Markdown

from src.ldapie.help_context import HelpContext, CommandValidator, COMMAND_PATTERNS

def parse_partial_command(input_text: str) -> Dict[str, Any]:
    """
    Parse a partial command to understand what help to provide
    
    Args:
        input_text: Current input text from the command line
        
    Returns:
        Dictionary with parsed command information
    """
    parts = input_text.strip().split()
    
    result = {
        "full_text": input_text,
        "command": None,
        "subcommand": None,
        "args": [],
        "current_arg_index": 0,
        "current_arg_type": None
    }
    
    if not parts:
        return result
        
    result["command"] = parts[0]
    
    if len(parts) > 1:
        result["args"] = parts[1:]
        result["current_arg_index"] = len(parts) - 1
        
    # Determine current argument type based on common LDAP patterns
    if result["command"] in ["search", "info", "add", "modify", "delete", "rename", "compare", "schema"]:
        if result["current_arg_index"] == 1:
            result["current_arg_type"] = "host"
        elif result["current_arg_index"] == 2:
            result["current_arg_type"] = "base_dn"
        elif result["current_arg_index"] == 3 and result["command"] == "search":
            result["current_arg_type"] = "filter"
    
    return result

def get_help_for_position(parsed_input: Dict[str, Any], help_context: HelpContext) -> Dict[str, Any]:
    """
    Get context-sensitive help based on the current input position
    
    Args:
        parsed_input: Parsed command information
        help_context: HelpContext instance for context awareness
        
    Returns:
        Dictionary with context-sensitive help information
    """
    cmd = parsed_input["command"]
    
    # If no command yet, show available commands
    if cmd is None:
        return {
            "title": "Available Commands",
            "help_text": "Type a command to begin, or use 'help' for more information.",
            "suggestions": list(COMMAND_PATTERNS.keys())
        }
    
    # Get command help if available
    cmd_help = help_context.get_command_help(cmd)
    
    # If unknown command, suggest corrections
    if "error" in cmd_help:
        return {
            "title": "Unknown Command",
            "help_text": cmd_help.get("error", "Unknown command"),
            "suggestions": cmd_help.get("suggested_command", []) if isinstance(cmd_help.get("suggested_command"), list) else [cmd_help.get("suggested_command")] if cmd_help.get("suggested_command") else []
        }
    
    # Get help based on argument position
    arg_type = parsed_input["current_arg_type"]
    current_index = parsed_input["current_arg_index"]
    
    if arg_type == "host":
        return {
            "title": "LDAP Host",
            "help_text": "Enter the LDAP server hostname or IP address.\nExample: ldap.example.com",
            "examples": ["ldap.example.com", "localhost", "192.168.1.100"]
        }
    elif arg_type == "base_dn":
        return {
            "title": "Base DN",
            "help_text": "Enter the base Distinguished Name (DN) for the operation.\nExample: dc=example,dc=com",
            "examples": ["dc=example,dc=com", "ou=people,dc=example,dc=com", "cn=admin,dc=example,dc=com"]
        }
    elif arg_type == "filter":
        return {
            "title": "LDAP Filter",
            "help_text": "Enter an LDAP search filter.\nFilters should be enclosed in parentheses.",
            "examples": ["(objectClass=*)", "(cn=user*)", "(&(objectClass=person)(mail=*@example.com))"]
        }
    
    # General help for the command
    return {
        "title": f"Help for '{cmd}'",
        "help_text": f"Syntax: {cmd_help.get('syntax', '')}",
        "examples": cmd_help.get("examples", [])
    }

def show_help_overlay(input_text: str, help_context: HelpContext, console: Console, non_interactive: bool = False) -> None:
    """
    Display a help overlay based on the current input
    
    Args:
        input_text: Current input text from the command line
        help_context: HelpContext instance for context awareness
        console: Rich console for output
        non_interactive: If True, don't wait for user input
    """
    # Parse the current input
    parsed_input = parse_partial_command(input_text)
    
    # Get context-sensitive help
    help_info = get_help_for_position(parsed_input, help_context)
    
    # Create help panel
    help_table = Table(box=None, show_header=False, expand=True)
    help_table.add_column("Content", style="bright_white")
    
    # Add title
    help_table.add_row(f"[bold cyan]{help_info['title']}[/bold cyan]")
    help_table.add_row("")
    
    # Add help text
    if "help_text" in help_info:
        help_table.add_row(help_info["help_text"])
        help_table.add_row("")
    
    # Add examples if available
    if "examples" in help_info and help_info["examples"]:
        help_table.add_row("[bold]Examples:[/bold]")
        for example in help_info["examples"]:
            help_table.add_row(f"  [command]{example}[/command]")
        help_table.add_row("")
    
    # Add suggestions if available
    if "suggestions" in help_info and help_info["suggestions"]:
        help_table.add_row("[bold]Suggestions:[/bold]")
        for suggestion in help_info["suggestions"]:
            help_table.add_row(f"  [success]• {suggestion}[/success]")
    
    # Create and display the panel
    panel = Panel(
        help_table,
        title="[bold]Context Help[/bold]",
        subtitle="Press Esc to close",
        border_style="bright_blue"
    )
    
    # Don't clear screen in non-interactive mode
    if not non_interactive:
        console.clear()
    console.print(panel)
    console.print(f"\nCurrent input: [command]{input_text}[/command]")
    
    # Wait for key press to continue only in interactive mode
    if not non_interactive:
        console.input("\nPress Enter to continue...")

def process_help_key(current_input: str, console: Console) -> None:
    """
    Process the '?' key and show help overlay if appropriate
    
    Args:
        current_input: Current input text from the command line
        console: Rich console for output
    """
    # Only show help if the input doesn't end with a quoted string
    if current_input.endswith('?'):
        # Remove the ? character
        input_without_question = current_input[:-1].strip()
        
        # Get help context
        help_context = HelpContext()
        
        # Show help overlay
        show_help_overlay(input_without_question, help_context, console)
        
        return input_without_question
    
    return current_input

# For testing
if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    help_context = HelpContext()
    
    # Test with different inputs
    test_inputs = [
        "",
        "search",
        "search ldap.example.com",
        "search ldap.example.com dc=example,dc=com",
        "unknown",
        "interactive"
    ]
    
    for test_input in test_inputs:
        show_help_overlay(test_input, help_context, console)

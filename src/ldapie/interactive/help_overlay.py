#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help Overlay for LDAPie

This module provides an overlay UI for context-sensitive help that can be
triggered with the '?' key during command input. It displays relevant
suggestions, examples, and documentation based on the current command context.

The help overlay can be triggered in two ways:
- By appending '?' directly to a command: 'search?'
- By adding a space before '?': 'search ?'

In both cases, only the help is shown, and the command is not executed.

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

try:
    from .help_context import HelpContext, CommandValidator, COMMAND_PATTERNS
except ImportError:
    # Fallback for when help_context is not available
    HelpContext = None
    CommandValidator = None
    COMMAND_PATTERNS = {}

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
        # Show command frequency to suggest most used commands first
        frequent_commands = sorted(
            help_context.command_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        suggestions = list(COMMAND_PATTERNS.keys())
        return {
            "title": "Available Commands",
            "help_text": "Type a command to begin, or use 'help' for more information.",
            "suggestions": suggestions,
            "frequent_commands": [cmd for cmd, count in frequent_commands if count > 0]
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
    args = parsed_input.get("args", [])
    arg_type = parsed_input["current_arg_type"]
    current_index = parsed_input["current_arg_index"]
    
    # For search command, add more context-specific help
    if cmd == "search" and len(args) >= 1:
        host = args[0]
        
        # Detect if we're at the host argument
        if arg_type == "host":
            # Check recent hosts from history
            recent_hosts = set()
            for cmd_str in help_context.command_history:
                parts = cmd_str.split()
                if len(parts) > 1 and parts[0] in ["search", "info", "add", "modify", "delete", "rename", "compare", "schema"]:
                    recent_hosts.add(parts[1])
            
            return {
                "title": "LDAP Host",
                "help_text": "Enter the LDAP server hostname or IP address.",
                "examples": list(recent_hosts)[:3] + ["ldap.example.com", "localhost", "192.168.1.100"],
                "recent_usage": f"You've recently used these hosts: {', '.join(list(recent_hosts)[:3])}" if recent_hosts else None
            }
        # If we're at the base_dn argument and have previous searches
        elif arg_type == "base_dn" and help_context.current_context.get("base_dn"):
            recent_base_dns = set()
            for cmd_str in help_context.command_history:
                parts = cmd_str.split()
                if len(parts) > 2 and parts[0] in ["search", "add", "modify", "delete", "rename", "compare"]:
                    recent_base_dns.add(parts[2])
            
            return {
                "title": "Base DN",
                "help_text": "Enter the base Distinguished Name (DN) for the operation.",
                "examples": list(recent_base_dns)[:3] + ["dc=example,dc=com", "ou=people,dc=example,dc=com"],
                "recent_usage": f"Recent base DNs: {', '.join(list(recent_base_dns)[:3])}" if recent_base_dns else None,
                "tips": ["Enclose the DN in quotes if it contains spaces or special characters"]
            }
        # If we're at the filter argument
        elif arg_type == "filter" and len(args) >= 2:
            recent_filters = set()
            for cmd_str in help_context.command_history:
                parts = cmd_str.split()
                if len(parts) > 3 and parts[0] == "search":
                    recent_filters.add(parts[3])
            
            return {
                "title": "LDAP Filter",
                "help_text": "Enter an LDAP search filter.\nFilters should be enclosed in parentheses.",
                "examples": list(recent_filters)[:2] + ["(objectClass=*)", "(cn=user*)", "(&(objectClass=person)(mail=*@example.com))"],
                "tips": [
                    "Use * as a wildcard: (cn=user*)",
                    "Combine filters with & (AND) or | (OR): (&(objectClass=person)(cn=admin))",
                    "Use ! for NOT: (!(objectClass=computer))"
                ]
            }
    
    # Default basic position-based help
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
    
    # General help for the command with additional context-specific information
    help_info = {
        "title": f"Help for '{cmd}'",
        "help_text": f"Syntax: {cmd_help.get('syntax', '')}",
        "examples": cmd_help.get("examples", []),
        "tips": cmd_help.get("common_errors", [])
    }
    
    # Add command-specific additional help
    if cmd == "search":
        help_info["options"] = [
            "--tree: Display results in a hierarchical tree",
            "--json: Output results in JSON format",
            "--ldif: Output results in LDIF format",
            "-a <attr>: Specify attributes to fetch (can be used multiple times)"
        ]
    elif cmd == "modify":
        help_info["options"] = [
            "--add <attr>=<value>: Add a value to an attribute",
            "--replace <attr>=<value>: Replace an attribute value",
            "--delete <attr>: Delete an entire attribute",
            "--delete <attr>=<value>: Delete a specific attribute value"
        ]
    
    return help_info

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
    
    # Add recent usage if available (specific context)
    if "recent_usage" in help_info and help_info["recent_usage"]:
        help_table.add_row(f"[bold magenta]{help_info['recent_usage']}[/bold magenta]")
        help_table.add_row("")
    
    # Add frequently used commands if available
    if "frequent_commands" in help_info and help_info["frequent_commands"]:
        help_table.add_row("[bold]Frequently Used Commands:[/bold]")
        for cmd in help_info["frequent_commands"]:
            help_table.add_row(f"  [command]{cmd}[/command]")
        help_table.add_row("")
        
    # Add options if available
    if "options" in help_info and help_info["options"]:
        help_table.add_row("[bold]Useful Options:[/bold]")
        for option in help_info["options"]:
            help_table.add_row(f"  [option]{option}[/option]")
        help_table.add_row("")
    
    # Add tips if available
    if "tips" in help_info and help_info["tips"]:
        help_table.add_row("[bold]Tips & Common Issues:[/bold]")
        for tip in help_info["tips"]:
            help_table.add_row(f"  [info]• {tip}[/info]")
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
        border_style="bright_blue"
    )
    
    # Don't clear screen in non-interactive mode
    if not non_interactive:
        console.clear()
    console.print(panel)
    console.print(f"\nCurrent input: [command]{input_text}[/command]")
    
    # No longer wait for user input - auto-dismisses
    # The actual timeout implementation would be in the calling function

def process_help_key(current_input: str, console: Console) -> None:
    """
    Process the '?' key and show help overlay if appropriate
    
    Args:
        current_input: Current input text from the command line
        console: Rich console for output
    """
    # Check if the input contains a question mark (both "command?" and "command ?" formats)
    if '?' in current_input:
        # Remove the ? character and any surrounding whitespace
        input_without_question = current_input.replace('?', '').strip()
        
        # Get help context
        help_context = HelpContext()
        
        # Import necessary modules for auto-dismiss
        import threading
        import time
        
        # Show help overlay without waiting for input
        show_help_overlay(input_without_question, help_context, console)
        
        # Set up a timer to auto-dismiss the overlay (in a real application)
        # This creates a temporary overlay that will be replaced by the main UI after a delay
        def dismiss_overlay():
            time.sleep(5)  # Wait for 5 seconds
            console.clear()
            console.print(f"[info]Input: [command]{input_without_question}[/command][/info]")
            
        # Start the auto-dismiss timer in a non-blocking thread
        threading.Thread(target=dismiss_overlay, daemon=True).start()
        
        # Return empty string to prevent command execution after showing help
        return ""
    
    return current_input

# For testing
if __name__ == "__main__":
    import time
    import threading
    from rich.console import Console
    
    console = Console()
    help_context = HelpContext()
    
    # Test auto-dismiss functionality
    def test_auto_dismiss():
        # Test with a single input to demonstrate auto-dismiss
        test_input = "search ldap.example.com"
        
        print("Testing auto-dismiss overlay with input:", test_input)
        
        # Get help context
        help_context = HelpContext()
        help_context.add_command("search ldap1.example.com dc=example,dc=com")
        help_context.add_command("search ldap2.example.com ou=people,dc=example,dc=com")
        
        # Show help overlay
        show_help_overlay(test_input, help_context, console, False)
        
        # Auto-dismiss after 5 seconds
        def dismiss():
            time.sleep(5)  # Wait for 5 seconds
            console.clear()
            console.print(f"[info]Overlay auto-dismissed. Input restored: [command]{test_input}[/command][/info]")
        
        # Start the auto-dismiss timer
        dismiss_thread = threading.Thread(target=dismiss, daemon=True)
        dismiss_thread.start()
        
        # Wait for the thread to complete
        dismiss_thread.join()
        
    # Run the test
    test_auto_dismiss()

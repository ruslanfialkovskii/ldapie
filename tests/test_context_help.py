#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for LDAPie context-sensitive help system

This script verifies the functionality of the context-sensitive help system
by exercising its various components and capabilities.

Usage:
    python3 test_context_help.py
"""

import os
import sys
import traceback
from rich.console import Console

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the src directory
try:
    from ldapie.help_context import HelpContext, CommandValidator
    from ldapie.help_overlay import show_help_overlay
except ImportError:
    from src.ldapie.help_context import HelpContext, CommandValidator
    from src.ldapie.help_overlay import show_help_overlay

# Initialize console for output
console = Console()

def test_help_context():
    """Test the HelpContext class"""
    console.print("\n[bold]Testing HelpContext[/bold]")
    console.rule()
    
    # Create a help context instance
    help_context = HelpContext()
    
    # Add some commands to history
    help_context.add_command("search ldap.example.com 'dc=example,dc=com'")
    help_context.add_command("info ldap.example.com")
    
    # Update session state
    help_context.update_session_state(connected=True, authenticated=True, ssl_enabled=False)
    
    # Get suggestions
    suggestions = help_context.get_suggestions()
    console.print("\n[bold]Context-aware suggestions:[/bold]")
    if suggestions["next_commands"]:
        console.print("\n[bold]Next Steps:[/bold]")
        for suggestion in suggestions["next_commands"]:
            console.print(f"  [success]• {suggestion}[/success]")
    if suggestions["examples"]:
        console.print("\n[bold]Examples:[/bold]")
        for example in suggestions["examples"]:
            console.print(f"  [command]{example}[/command]")
    if suggestions["tips"]:
        console.print("\n[bold]Tips:[/bold]")
        for tip in suggestions["tips"]:
            console.print(f"  [info]• {tip}[/info]")
    
    # Test command help
    console.print("\n[bold]Command help for 'search':[/bold]")
    cmd_help = help_context.get_command_help("search")
    console.print(f"Syntax: {cmd_help.get('syntax', '')}")
    if "examples" in cmd_help:
        console.print("\n[bold]Examples:[/bold]")
        for example in cmd_help["examples"]:
            console.print(f"  [command]{example}[/command]")
    
    # Test suggestion for mistyped command
    console.print("\n[bold]Help for mistyped command 'serch':[/bold]")
    mistyped_help = help_context.get_command_help("serch")
    console.print(f"  {mistyped_help.get('error', '')}")
    
    return True

def test_command_validator():
    """Test the CommandValidator class"""
    console.print("\n[bold]Testing CommandValidator[/bold]")
    console.rule()
    
    # Create a help context and validator
    help_context = HelpContext()
    validator = CommandValidator(help_context)
    
    # Test a valid command
    console.print("\n[bold]Validating a valid command:[/bold]")
    result = validator.validate_command("search ldap.example.com 'dc=example,dc=com' '(objectClass=person)'")
    console.print(f"  Validation: {result.get('validation', '')}")
    console.print(f"  Preview: {result.get('preview', '')}")
    
    # Test an invalid command
    console.print("\n[bold]Validating an invalid command:[/bold]")
    result = validator.validate_command("search")
    console.print(f"  Error: {result.get('error', '')}")
    
    # Test a delete command without recursive flag
    console.print("\n[bold]Validating a delete command without recursive flag:[/bold]")
    result = validator.validate_command("delete ldap.example.com 'dc=example,dc=com'")
    console.print(f"  Validation: {result.get('validation', '')}")
    console.print(f"  Warning: {result.get('warning', '')}")
    console.print(f"  Suggestion: {result.get('suggestion', '')}")
    
    return True

def test_help_overlay():
    """Test the help overlay functionality"""
    console.print("\n[bold]Testing Help Overlay[/bold]")
    console.rule()
    
    help_context = HelpContext()
    
    # Test different command inputs
    test_inputs = [
        "",
        "search",
        "search ldap.example.com",
        "search ldap.example.com dc=example,dc=com",
        "serch",  # Mistyped command
    ]
    
    for test_input in test_inputs:
        console.print(f"\n[bold]Testing overlay for input: [cyan]{test_input}[/cyan][/bold]")
        try:
            # Use non-interactive mode to avoid waiting for user input
            show_help_overlay(test_input, help_context, console, non_interactive=True)
        except Exception as e:
            console.print(f"[error]Error showing help overlay: {e}[/error]")
            traceback.print_exc()
    
    return True

def main():
    """Main test function"""
    console.print("[bold]LDAPie Context-Sensitive Help System Test[/bold]")
    
    try:
        # Test HelpContext
        test_help_context()
        
        # Test CommandValidator
        test_command_validator()
        
        # Test help overlay
        test_help_overlay()
        
        console.print("\n[success]All tests completed successfully![/success]")
    except Exception as e:
        console.print(f"[error]Test failed: {e}[/error]")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

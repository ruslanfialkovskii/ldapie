#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich formatter for Click commands

This module provides a custom help formatter for Click using Rich for beautiful output.
"""

import os
import sys
import click
from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from functools import wraps
from typing import Optional, Callable, List, Dict, Any

# Create a local console if needed, but prefer importing from ldapie.py
# to avoid creating multiple consoles
_local_console = None

def get_console():
    """
    Get the console instance, either from the parent module or create a local one.
    
    This helps avoid circular imports while maintaining a single console instance.
    """
    global _local_console
    
    # Try to import the console from ldapie first
    try:
        from src.ldapie.ldapie import console
        return console
    except (ImportError, AttributeError):
        # If that fails, create a local console
        if _local_console is None:
            # Define simplified themes
            dark_theme = {
                "info": "cyan",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "highlight": "magenta",
                "command": "cyan",
                "option": "yellow",
                "usage": "green",
            }
            
            light_theme = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "highlight": "magenta",
                "command": "blue",
                "option": "yellow",
                "usage": "green",
            }
            
            # Get theme from environment or default to dark
            theme_name = os.environ.get("LDAPIE_THEME", "dark").lower()
            theme_colors = light_theme if theme_name == "light" else dark_theme
            _local_console = Console(theme=Theme(theme_colors))
        
        return _local_console

def show_rich_help(ctx: click.Context, param: click.Option, value: bool) -> bool:
    """
    Show rich help for a Click command.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: Parameter value
        
    Returns:
        Boolean value passed in
    """
    if not value or ctx.resilient_parsing:
        return value
    
    console = get_console()
    
    command = ctx.command
    command_name = command.name
    
    # Title and description
    console.print(f"\n[bold]{command_name.upper()}[/bold]", style="highlight")
    if command.help:
        console.print(f"\n{command.help}\n")
    
    # Usage
    usage_parts = ["[usage]Usage:[/usage]", command_name]
    
    # Add command arguments
    for param in command.params:
        if isinstance(param, click.Argument):
            usage_parts.append(f"<{param.name}>")
    
    # Add [options] placeholder
    usage_parts.append("[OPTIONS]")
    
    # Check if this is a group with commands to add COMMAND [ARGS]
    if isinstance(command, click.Group) and command.list_commands(ctx):
        usage_parts.append("COMMAND [ARGS]...")
    
    console.print(" ".join(usage_parts))
    
    # Options table
    if command.params:
        options_table = Table(show_header=False, box=None)
        options_table.add_column("Option", style="option")
        options_table.add_column("Description")
        
        for param in command.params:
            if isinstance(param, click.Option):
                option_names = ", ".join(param.opts)
                help_text = param.help or ""
                if param.default and not param.is_flag and param.default != "":
                    help_text += f" [default: {param.default}]"
                options_table.add_row(option_names, help_text)
        
        console.print("\n[bold]Options[/bold]")
        console.rule()
        console.print(options_table)
    
    # Commands section for groups
    if isinstance(command, click.Group):
        commands = command.list_commands(ctx)
        if commands:
            commands_table = Table(show_header=False, box=None)
            commands_table.add_column("Command", style="command")
            commands_table.add_column("Description")
            
            for cmd_name in sorted(commands):
                cmd = command.get_command(ctx, cmd_name)
                cmd_help = cmd.get_short_help_str() if cmd else ""
                commands_table.add_row(cmd_name, cmd_help)
            
            console.print("\n[bold]Commands[/bold]")
            console.rule()
            console.print(commands_table)
            
            console.print("\n[info]Run 'ldapie COMMAND --help' for more information on a command.[/info]")
    
    # Examples
    if command.help:
        # Look for examples in the docstring
        help_lines = command.help.split("\n")
        example_lines = []
        in_example = False
        
        for line in help_lines:
            if line.strip().lower().startswith("example:"):
                in_example = True
                example_lines.append(line)
            elif in_example:
                example_lines.append(line)
        
        if example_lines:
            console.print("\n[bold]Examples[/bold]")
            console.rule()
            console.print("\n".join(example_lines))
    
    ctx.exit()

def add_rich_help_option(f: Callable) -> Callable:
    """
    Add a --help-rich option to a Click command.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        return f(*args, **kwargs)
    
    decorator = click.option(
        '--help',
        is_flag=True,
        expose_value=False,
        is_eager=True,
        help="Show this message and exit.",
        callback=show_rich_help
    )(decorator)
    
    return decorator

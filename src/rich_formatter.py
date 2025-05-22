#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich formatted help for Click commands

This module provides enhanced formatting of Click command help text using
the Rich library. It replaces the standard Click help formatter with a more
visually appealing and structured output that includes color highlighting
and better organization of command options and arguments.

The module works by replacing Click's standard help option with a custom
one that renders help text using Rich's styling capabilities. This results
in more readable and visually appealing help text compared to the standard
terminal output.

Functions:
    get_command_arguments: Extract positional arguments from a Click command
    format_rich_help: Format help text for a command using Rich
    show_rich_help: Click callback to show help using Rich formatting
    add_rich_help_option: Add a custom --help option to a command

Example:
    To add rich formatting to a Click command:
    
    >>> @click.command()
    >>> @add_rich_help_option
    >>> def my_command():
    >>>     \"\"\"This is my command\"\"\"
    >>>     pass
"""

import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.rule import Rule

def get_command_arguments(command):
    """
    Get all positional arguments for a command.
    
    Extracts the positional arguments (not options) from a Click command
    for display in the help text usage section.
    
    Args:
        command: Click Command object to analyze
        
    Returns:
        List of argument names in uppercase
        
    Example:
        >>> args = get_command_arguments(search_command)
        >>> print(args)
        ['HOST', 'BASE_DN', 'FILTER_QUERY']
    """
    arguments = []
    for param in command.params:
        if isinstance(param, click.Argument):
            arguments.append(param.name.upper())
    return arguments

def format_rich_help(ctx, console=None):
    """
    Format help text for a command using Rich formatting.
    
    Creates a beautifully formatted help text for a Click command or command group.
    The output includes a usage section, command description, options table,
    and (for groups) a commands table.
    
    Args:
        ctx: Click Context object containing the command to format help for
        console: Rich Console object to use for output. If None, imports the
                console from ldapie.py
                
    Returns:
        None - output is printed directly to the console
        
    Example:
        >>> # Using your own console
        >>> from rich.console import Console
        >>> console = Console()
        >>> format_rich_help(ctx, console)
        >>>
        >>> # Using console from ldapie
        >>> format_rich_help(ctx)
        
    Note:
        This function automatically displays command arguments in uppercase in
        the usage section, and organizes options and subcommands in separate tables.
    """
    if console is None:
        # Import console directly from ldapie
        import sys
        import os
        
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add to path if needed
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Now import the console
        from ldapie import console  # Updated from ldapcli to ldapie
    
    command = ctx.command
    
    # Get arguments for the command
    arguments = get_command_arguments(command)
    arguments_str = ' '.join(arguments)
    
    # Print header with usage
    console.print(f"[usage]Usage:[/usage] {ctx.command_path} [OPTIONS] {arguments_str}")
    
    # Print command help
    if command.help:
        console.print(f"\n{command.help}")
    
    # Print options
    if command.params:
        console.print("\n[bold]Options[/bold]")
        console.print(Rule())
        
        options_table = Table(show_header=False, box=None)
        options_table.add_column("Option", style="option")
        options_table.add_column("Description")
        
        for param in command.params:
            # Skip hidden parameters and arguments
            if getattr(param, 'hidden', False) or isinstance(param, click.Argument):
                continue
                
            # Get option strings
            opts = []
            for opt in param.opts:
                opts.append(opt)
            for opt in param.secondary_opts:
                opts.append(opt)
                
            # Format parameter help
            param_help = param.help or ''
            if isinstance(param, click.Option) and param.default is not None and param.show_default:
                param_help = f"{param_help} (default: {param.default})"
                
            # Add metavar if available
            opt_str = ', '.join(opts)
            if param.metavar:
                opt_str = f"{opt_str} {param.metavar}"
                
            options_table.add_row(opt_str, param_help)
            
        console.print(options_table)
    
    # Print commands for groups
    if isinstance(command, click.Group) and command.commands:
        console.print("\n[bold]Commands[/bold]")
        console.print(Rule())
        
        commands_table = Table(show_header=False, box=None)
        commands_table.add_column("Command", style="command")
        commands_table.add_column("Description")
        
        for name, cmd in sorted(command.commands.items()):
            # Skip hidden commands
            if getattr(cmd, 'hidden', False):
                continue
                
            commands_table.add_row(name, cmd.short_help or '')
            
        console.print(commands_table)

def show_rich_help(ctx, param, value):
    """
    Click callback to show help using Rich formatting.
    
    This function is designed to be used as a callback for Click's --help option.
    When the --help flag is provided, this callback is triggered and displays
    the command's help text using Rich formatting instead of Click's default
    formatter.
    
    Args:
        ctx: Click Context object for the current command
        param: Click Parameter object that triggered this callback (the --help option)
        value: The value of the parameter (True if --help was specified)
        
    Returns:
        None - Exits the program after displaying help
        
    Example:
        >>> @click.command()
        >>> @click.option('--help', '-h', is_flag=True, callback=show_rich_help,
        >>>               expose_value=False, is_eager=True,
        >>>               help="Show this message and exit.")
        >>> def my_command():
        >>>     \"\"\"My command description\"\"\"
        >>>     pass
        
    Note:
        This function will exit the program after displaying help, as is standard
        behavior for --help options.
    """
    if value and not ctx.resilient_parsing:
        # Import console directly from ldapie
        import sys
        import os
        
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add to path if needed
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Now import the console
        from ldapie import console  # Updated from ldapcli to ldapie
        
        format_rich_help(ctx, console)
        ctx.exit()

def add_rich_help_option(command):
    """
    Add --help option that uses rich formatting to a command.
    
    This is a decorator that adds a custom --help option to a Click command,
    replacing the standard help with our Rich-formatted version. This function
    is the main entry point for users of this module.
    
    Args:
        command: Click Command object to enhance with rich help
        
    Returns:
        The decorated command with rich help enabled
        
    Example:
        >>> @click.command()
        >>> @add_rich_help_option
        >>> def my_command():
        >>>     \"\"\"My command help text\"\"\"
        >>>     pass
        
    Usage:
        Apply this decorator after @click.command() or @click.group() but before
        any other decorators that modify the command's help behavior.
        
    Note:
        This replaces the standard --help/-h option completely. If you need to
        keep the standard help behavior alongside this, you should use a different
        approach.
    """
    help_option = click.option(
        '--help', '-h', is_flag=True, expose_value=False,
        help='Show this message and exit.',
        callback=show_rich_help
    )
    return help_option(command)

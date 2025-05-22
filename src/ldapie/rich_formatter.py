#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich formatted help for Click commands with context-sensitive suggestions

This module provides enhanced formatting of Click command help text using
the Rich library with context-sensitive suggestions based on the current
command state and user history. It replaces the standard Click help formatter 
with a more visually appealing and structured output that includes color 
highlighting, better organization of command options and arguments, and
intelligent suggestions based on context.

The module works by replacing Click's standard help option with a custom
one that renders help text using Rich's styling capabilities and adds
contextual help and suggestions from the HelpContext system.

Functions:
    get_command_arguments: Extract positional arguments from a Click command
    format_rich_help: Format help text for a command using Rich
    format_context_help: Add context-sensitive suggestions to help output
    show_rich_help: Click callback to show help using Rich formatting
    add_rich_help_option: Add a custom --help option to a command
    show_command_validation: Show validation preview for a command

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
from rich.panel import Panel

# We'll import the help context system when we need it
# to avoid circular imports

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
    
    # Add context-sensitive help if available
    try:
        # Only import when needed to avoid circular imports
        from src.help_context import HelpContext
        
        # Add context-sensitive suggestions
        format_context_help(ctx, console)
    except ImportError:
        # Context-sensitive help not available
        pass


def format_context_help(ctx, console):
    """
    Add context-sensitive suggestions to help output based on HelpContext
    
    Args:
        ctx: Click Context object containing the command to format help for
        console: Rich Console object to use for output
    """
    try:
        from src.help_context import HelpContext
        
        help_context = HelpContext()
        command_name = ctx.command.name if hasattr(ctx.command, 'name') else ''
        
        # Get suggestions for the current command
        if command_name:
            cmd_help = help_context.get_command_help(command_name)
            suggestions = help_context.get_suggestions()
            
            # Print examples if available
            if 'examples' in cmd_help and cmd_help['examples']:
                console.print("\n[bold]Examples[/bold]")
                console.print(Rule())
                for example in cmd_help['examples']:
                    console.print(f"  [command]{example}[/command]")
            
            # Print tips if available
            if 'tips' in suggestions and suggestions['tips']:
                console.print("\n[bold]Tips[/bold]")
                console.print(Rule())
                for tip in suggestions['tips']:
                    console.print(f"  [info]• {tip}[/info]")
                    
            # Print next steps if available
            if 'next_commands' in suggestions and suggestions['next_commands']:
                console.print("\n[bold]Next Steps[/bold]")
                console.print(Rule())
                for next_cmd in suggestions['next_commands']:
                    console.print(f"  [success]• {next_cmd}[/success]")
    except Exception:
        # Silently fail if context help is not available
        pass

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
    """
    if value and not ctx.resilient_parsing:
        # Import console from ldapie module
        from src.ldapie import console
        
        format_rich_help(ctx, console)
        ctx.exit()


def show_command_validation(ctx, param, value):
    """
    Click callback to show command validation preview.
    
    This function is triggered by the --validate flag and shows a preview
    of what the command would do without actually executing it.
    
    Args:
        ctx: Click Context object for the current command
        param: Click Parameter object that triggered this callback
        value: The value of the parameter (True if --validate was specified)
        
    Returns:
        None - Exits the program after displaying validation
    """
    if not value or ctx.resilient_parsing:
        return
        
    # Import required components
    from ldapie import console
    
    try:
        from src.help_context import CommandValidator, HelpContext
        
        # Construct the command string from context
        cmd_path = ctx.command_path
        cmd_args = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in ctx.args])
        cmd_str = f"{cmd_path} {cmd_args}".strip()
        
        # Validate the command
        help_context = HelpContext()
        validator = CommandValidator(help_context)
        result = validator.validate_command(cmd_str)
        
        # Display validation results
        console.print("\n[bold]Command Validation[/bold]")
        console.print(Rule())
        
        if "error" in result:
            console.print(f"[error]Error: {result['error']}[/error]")
            if "suggestion" in result:
                console.print(f"[info]Suggestion: {result['suggestion']}[/info]")
            if "examples" in result:
                console.print("\n[bold]Examples:[/bold]")
                for example in result['examples']:
                    console.print(f"  [command]{example}[/command]")
        else:
            if "validation" in result:
                console.print(f"[success]✓ {result['validation']}[/success]")
            if "preview" in result:
                console.print(f"\n[bold]Preview:[/bold] {result['preview']}")
            if "warning" in result:
                console.print(f"\n[warning]Warning: {result['warning']}[/warning]")
            if "suggestion" in result:
                console.print(f"\n[info]Suggestion: {result['suggestion']}[/info]")
    except ImportError:
        console.print("[warning]Command validation is not available.[/warning]")
    except (ValueError, TypeError, AttributeError) as e:
        console.print(f"[error]Error during validation: {str(e)}[/error]")
    
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
    # Add the --help option
    help_option = click.option(
        '--help', '-h', is_flag=True, expose_value=False,
        is_eager=True, help='Show this message and exit.',
        callback=show_rich_help
    )
    
    # Add the --validate option
    validate_option = click.option(
        '--validate', is_flag=True, expose_value=False,
        is_eager=True, help='Validate command without executing it.',
        callback=show_command_validation
    )
    
    # Apply both options to the command
    command = help_option(command)
    command = validate_option(command)
    
    return command

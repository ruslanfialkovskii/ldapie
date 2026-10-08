#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich formatter for Click commands

This module provides a custom help formatter for Click using Rich for beautiful output.
"""

from functools import wraps
from typing import Callable, List

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table


def get_console() -> Console:
    """Return the CLI console.

    Imported at call time because ldapie.ldapie imports this module.
    """
    from .ldapie import console

    return console


def _split_examples(help_text: str):
    """Split a docstring into (description, example lines)."""
    description: List[str] = []
    examples: List[str] = []
    for line in help_text.splitlines():
        if examples or line.strip().lower().startswith("example:"):
            examples.append(line)
        else:
            description.append(line)
    return "\n".join(description).strip(), examples


def show_rich_help(ctx: click.Context, param: click.Parameter, value: bool) -> bool:
    """
    Show rich help for a Click command.

    Help text, option names and defaults are escaped: they contain [brackets]
    that Rich would otherwise read as markup.

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
    description, examples = _split_examples(command.help or "")

    console.print(
        f"\n[bold]{escape((command.name or '').upper())}[/bold]", style="highlight"
    )
    if description:
        console.print(f"\n{escape(description)}\n")

    usage_parts = [ctx.command_path]
    usage_parts += [
        f"<{p.name}>" if p.required else f"[<{p.name}>]"
        for p in command.params
        if isinstance(p, click.Argument)
    ]
    usage_parts.append("[OPTIONS]")
    if isinstance(command, click.Group) and command.list_commands(ctx):
        usage_parts.append("COMMAND [ARGS]...")
    console.print(f"[usage]Usage:[/usage] {escape(' '.join(usage_parts))}")

    options = [p for p in command.params if isinstance(p, click.Option)]
    if options:
        options_table = Table(show_header=False, box=None)
        options_table.add_column("Option", style="option")
        options_table.add_column("Description")

        for option in options:
            names = " / ".join(
                n
                for n in (", ".join(option.opts), ", ".join(option.secondary_opts))
                if n
            )
            help_text = option.help or ""
            # Plain values only: unset defaults are a sentinel in Click 8.3+
            default = option.get_default(ctx, call=False)
            if (
                isinstance(default, (str, int))
                and not isinstance(default, bool)
                and default != ""
            ):
                help_text += f" [default: {default}]"
            options_table.add_row(escape(names), escape(help_text))

        console.print("\n[bold]Options[/bold]")
        console.rule()
        console.print(options_table)

    if isinstance(command, click.Group):
        commands = command.list_commands(ctx)
        if commands:
            commands_table = Table(show_header=False, box=None)
            commands_table.add_column("Command", style="command")
            commands_table.add_column("Description")

            for cmd_name in sorted(commands):
                cmd = command.get_command(ctx, cmd_name)
                cmd_help = cmd.get_short_help_str() if cmd else ""
                commands_table.add_row(escape(cmd_name), escape(cmd_help))

            console.print("\n[bold]Commands[/bold]")
            console.rule()
            console.print(commands_table)

            console.print(
                "\n[info]Run 'ldapie COMMAND --help' for more information on a command.[/info]"
            )

    if examples:
        console.print("\n[bold]Examples[/bold]")
        console.rule()
        console.print(escape("\n".join(examples)))

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
        "--help",
        is_flag=True,
        expose_value=False,
        is_eager=True,
        help="Show this message and exit.",
        callback=show_rich_help,
    )(decorator)

    return decorator

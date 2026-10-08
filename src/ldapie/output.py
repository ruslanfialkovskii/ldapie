#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output formatting functions (JSON, LDIF, CSV, etc.) for LDAPie.
"""

import base64
import csv
import json
from datetime import date, datetime
from io import StringIO
from typing import Any, Iterable, Iterator, List, Optional

from ldap3.utils.dn import parse_dn
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

LDIF_LINE_WIDTH = 76


def _json_default(value: Any) -> str:
    """Serialize values json.dumps cannot handle (bytes, timestamps, UUIDs...)."""
    if isinstance(value, bytes):
        return f"base64:{base64.b64encode(value).decode('ascii')}"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _text_value(value: Any) -> str:
    """Render one attribute value as plain text for tables and CSV."""
    if isinstance(value, bytes):
        return _json_default(value)
    return str(value)


def _ldif_needs_base64(value: str) -> bool:
    if not value:
        return False
    if value[0] in (" ", ":", "<") or value[-1] == " ":
        return True
    for ch in value:
        if ch in ("\n", "\r") or ord(ch) < 0x20 or ord(ch) >= 0x7F:
            return True
    return False


def _ldif_line(name: str, raw: bytes) -> str:
    """Format one LDIF line, base64-encoding values that are not safe text."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is None or _ldif_needs_base64(text):
        return f"{name}:: {base64.b64encode(raw).decode('ascii')}"
    return f"{name}: {text}"


def _fold(line: str, width: int = LDIF_LINE_WIDTH) -> List[str]:
    """Fold a long LDIF line; continuation lines start with one space."""
    if len(line) <= width:
        return [line]
    parts = [line[:width]]
    rest = line[width:]
    while rest:
        parts.append(" " + rest[: width - 1])
        rest = rest[width - 1 :]
    return parts


def ldif_lines(entries: Iterable[Any]) -> Iterator[str]:
    """Yield RFC 2849 LDIF lines for entries, using the raw attribute values.

    Raw values keep binary data and server-side syntax (timestamps, SIDs)
    intact, so the output can be imported again.
    """
    yield "version: 1"
    for entry in entries:
        yield ""
        yield from _fold(_ldif_line("dn", entry.entry_dn.encode("utf-8")))
        for attr_name in sorted(entry.entry_attributes):
            for raw in entry[attr_name].raw_values:
                yield from _fold(_ldif_line(attr_name, raw))


def output_json(entries: List[Any], output_file: Optional[str] = None) -> None:
    """
    Output LDAP entries as JSON.

    Converts LDAP entry objects to JSON-compatible format and outputs them
    either to stdout or to a file.

    Args:
        entries: List of LDAP entry objects
        output_file: Optional path to save output to a file. If None, prints to stdout.

    Returns:
        None

    Example:
        >>> output_json(entries, "output.json")
        >>> output_json(entries)  # Prints to stdout
    """
    json_entries = []
    for entry in entries:
        entry_dict: dict = {"dn": entry.entry_dn}
        for attr_name in entry.entry_attributes:
            values = entry[attr_name].values
            entry_dict[attr_name] = values[0] if len(values) == 1 else list(values)
        json_entries.append(entry_dict)

    json_str = json.dumps(json_entries, indent=2, default=_json_default)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json_str)
    else:
        print(json_str)


def output_ldif(entries: List[Any], output_file: Optional[str] = None) -> None:
    """
    Output LDAP entries as LDIF.

    Formats LDAP entries according to the LDAP Data Interchange Format (LDIF)
    and outputs them either to stdout or to a file.

    Args:
        entries: List of LDAP entry objects
        output_file: Optional path to save output to a file. If None, prints to stdout.

    Returns:
        None

    Example:
        >>> output_ldif(entries, "output.ldif")
        >>> output_ldif(entries)  # Prints to stdout

    Note:
        Values that are binary or not plain ASCII text are base64-encoded,
        and long lines are folded, as RFC 2849 specifies.
    """
    ldif_text = "\n".join(ldif_lines(entries)) + "\n"

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(ldif_text)
    else:
        print(ldif_text, end="")


def output_csv(entries: List[Any], output_file: Optional[str] = None) -> None:
    """
    Output LDAP entries as CSV.

    Converts LDAP entries to CSV format and outputs them either to stdout or
    to a file. All attributes from all entries are included as columns.

    Args:
        entries: List of LDAP entry objects
        output_file: Optional path to save output to a file. If None, prints to stdout.

    Returns:
        None

    Example:
        >>> output_csv(entries, "output.csv")
        >>> output_csv(entries)  # Prints to stdout

    Note:
        Multi-valued attributes are joined with semicolons in the CSV output.
    """
    if not entries:
        return

    # Collect all attribute names from all entries
    attr_names = {"dn"}
    for entry in entries:
        attr_names.update(entry.entry_attributes)

    # Sort attribute names for consistent output
    fieldnames = sorted(attr_names)

    # Create CSV output
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for entry in entries:
        row = {"dn": entry.entry_dn}
        for attr in entry.entry_attributes:
            # Join multiple values with a semicolon
            row[attr] = ";".join(_text_value(v) for v in entry[attr].values)

        writer.writerow(row)

    csv_text = output.getvalue()

    if output_file:
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            f.write(csv_text)
    else:
        print(csv_text)


def _dn_parts(dn: str) -> List[str]:
    """Split a DN into normalized RDNs: lowercase names, no extra spaces."""
    return [f"{attr.lower()}={value}" for attr, value, _ in parse_dn(dn)]


def build_tree(entries: List[Any], base_dn: str) -> Tree:
    """
    Build a hierarchical tree of LDAP entries.

    Organizes LDAP entries into a hierarchical tree structure based on their DNs,
    with the specified base_dn as the root.

    Args:
        entries: List of LDAP entry objects
        base_dn: Base DN to use as the root of the tree

    Returns:
        Rich Tree object representing the hierarchy

    Example:
        >>> tree = build_tree(entries, "dc=example,dc=com")
        >>> console.print(tree)
    """
    root_tree = Tree(f"[yellow]{escape(base_dn)}[/yellow]")

    # Index nodes by normalized DN so case and spacing differences still match
    root_key = ",".join(_dn_parts(base_dn))
    tree_nodes = {root_key: root_tree}

    # Shallowest entries first, so parents exist before their children
    for entry in sorted(entries, key=lambda e: len(parse_dn(e.entry_dn))):
        parts = _dn_parts(entry.entry_dn)
        key = ",".join(parts)
        if key == root_key:
            continue

        # Attach to the base when the parent was not part of the results
        parent_node = tree_nodes.get(",".join(parts[1:]), root_tree)
        entry_node = parent_node.add(f"[yellow]{escape(parts[0])}[/yellow]")

        for attr_name in sorted(entry.entry_attributes):
            values = [escape(_text_value(v)) for v in entry[attr_name].values]
            if len(values) == 1:
                entry_node.add(f"[cyan]{attr_name}:[/cyan] [green]{values[0]}[/green]")
            else:
                attr_node = entry_node.add(f"[cyan]{attr_name}:[/cyan]")
                for value in values:
                    attr_node.add(f"[green]{value}[/green]")

        tree_nodes[key] = entry_node

    return root_tree


def output_tree(
    entries: List[Any],
    base_dn: str,
    console: Console,
    output_file: Optional[str] = None,
) -> None:
    """
    Output LDAP entries as a hierarchical tree.

    Displays LDAP entries in a hierarchical tree format showing the DN hierarchy
    and all attributes. Outputs either to console or to a file.

    Args:
        entries: List of LDAP entry objects
        base_dn: Base DN to use as the root of the tree
        console: Rich Console object for output
        output_file: Optional path to save output to a file

    Returns:
        None

    Example:
        >>> output_tree(entries, "dc=example,dc=com", console)
        >>> output_tree(entries, "dc=example,dc=com", console, "output.txt")
    """
    tree = build_tree(entries, base_dn)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            Console(file=f, highlight=False).print(tree)
    else:
        console.print(tree)


def output_rich(
    entries: List[Any], console: Console, output_file: Optional[str] = None
) -> None:
    """
    Output LDAP entries in rich text format.

    Displays LDAP entries with a formatted rich text interface using tables
    and panels for better readability.

    Args:
        entries: List of LDAP entry objects
        console: Rich Console object for output
        output_file: Optional path to save output to a file

    Returns:
        None

    Example:
        >>> output_rich(entries, console)
        >>> output_rich(entries, console, "output.txt")
    """
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f_out:
            _print_entries(entries, Console(file=f_out, highlight=False))
    else:
        _print_entries(entries, console)


def _print_entries(entries: List[Any], console: Console) -> None:
    """Print one panel with an attribute table per entry."""
    for entry in entries:
        table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
        table.add_column("Attribute", style="cyan")
        table.add_column("Value", style="green")

        for attr_name in sorted(entry.entry_attributes):
            # LDAP data is not Rich markup; escape it so brackets print as-is
            values = (escape(_text_value(v)) for v in entry[attr_name].values)
            table.add_row(attr_name, "\n".join(values))

        panel = Panel(
            table,
            title=f"[yellow]{escape(entry.entry_dn)}[/yellow]",
            title_align="left",
            border_style="blue",
        )
        console.print(panel)
        console.print()  # Empty line between entries

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output formatting functions (JSON, LDIF, CSV, etc.) for LDAPie.

Directory data is untrusted: values are escaped before Rich renders them and
control characters are made visible before anything reaches the terminal.
Files are written atomically, so a failed streamed export never leaves a
truncated file behind or destroys the previous one.
"""

import base64
import contextlib
import csv
import itertools
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from io import StringIO
from typing import IO, Any, Dict, Iterable, Iterator, List, Optional

from ldap3.utils.dn import parse_dn
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

LDIF_LINE_WIDTH = 76

# C0 controls (except newline and tab), DEL and the C1 controls; terminals
# act on ESC (0x1b) and on C1 codes such as CSI (0x9b)
_CONTROL_CHARS = {
    code: f"\\x{code:02x}"
    for code in itertools.chain(range(0x20), (0x7F,), range(0x80, 0xA0))
    if chr(code) not in "\n\t"
}

# Cells starting with these characters are formulas to spreadsheet programs
# (OWASP list; a leading CR cannot occur because sanitize_text rewrites it)
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t")

# An LDIF attribute description: a name or a numeric OID, with options (RFC 4512)
_LDIF_ATTRIBUTE_NAME = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9-]*|[0-9]+(?:\.[0-9]+)*)(?:;[A-Za-z0-9-]+)*$"
)


def sanitize_text(text: str) -> str:
    """Make text from the directory safe to print: control characters become
    ``\\xNN`` escapes, so a value cannot clear the screen, move the cursor or
    plant a terminal hyperlink. Newlines and tabs are kept."""
    return text.translate(_CONTROL_CHARS)


def safe_text(text: str) -> str:
    """Sanitize server data and escape it for Rich markup, in that order.

    Use this for everything that came from the server or a file and goes
    through ``console.print``: values, names, DNs and error messages.
    """
    return escape(sanitize_text(text))


@contextlib.contextmanager
def _atomic_write(path: str, newline: Optional[str] = None) -> Iterator[IO[str]]:
    """Write ``path`` through a temporary file in the same directory.

    The file is renamed into place only when the block completes, so a
    failure part-way (a dropped connection during a streamed export) leaves
    the previous file untouched and no partial file behind. The file is
    created readable by its owner only: exports can hold password hashes.
    """
    target = os.path.abspath(path)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline=newline,
        dir=os.path.dirname(target),
        prefix=f".{os.path.basename(target)}.",
        suffix=".part",
        delete=False,
    )
    try:
        with handle:
            yield handle
        os.replace(handle.name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(handle.name)
        raise


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
    return sanitize_text(str(value))


def _csv_value(text: str) -> str:
    """Keep spreadsheet programs from running a value as a formula."""
    if text.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


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
    intact, so the output can be imported again. An attribute whose name is
    not a valid attribute description cannot be written in LDIF (names are
    never encoded); it is skipped with a comment line that names it.
    """
    yield "version: 1"
    for entry in entries:
        yield ""
        yield from _fold(_ldif_line("dn", entry.entry_dn.encode("utf-8")))
        for attr_name in sorted(entry.entry_attributes):
            if not _LDIF_ATTRIBUTE_NAME.match(attr_name):
                shown = attr_name.encode("unicode_escape").decode("ascii")
                yield f"# skipped attribute with an invalid name: {shown}"
                continue
            for raw in entry[attr_name].raw_values:
                yield from _fold(_ldif_line(attr_name, raw))


def json_records(entries: Iterable[Any]) -> Iterator[Dict[str, Any]]:
    """Yield one JSON-ready dict per entry: the DN and the formatted values."""
    for entry in entries:
        record: Dict[str, Any] = {"dn": entry.entry_dn}
        for attr_name in entry.entry_attributes:
            values = entry[attr_name].values
            record[attr_name] = values[0] if len(values) == 1 else list(values)
        yield record


def _write_json(records: Iterable[Dict[str, Any]], out: IO[str]) -> None:
    """Write records as one JSON array without holding them all in memory.

    The layout matches ``json.dumps(list, indent=2)``.
    """
    out.write("[")
    first = True
    for record in records:
        out.write("\n" if first else ",\n")
        first = False
        text = json.dumps(record, indent=2, default=_json_default)
        out.write("  " + text.replace("\n", "\n  "))
    out.write("]\n" if first else "\n]\n")


def output_json(entries: Iterable[Any], output_file: Optional[str] = None) -> None:
    """
    Output LDAP entries as JSON.

    Converts LDAP entry objects to JSON-compatible format and outputs them
    either to stdout or to a file. Entries are written as they come, so an
    iterator can stream a large export.

    Args:
        entries: LDAP entry objects
        output_file: Optional path to save output to a file. If None, prints to stdout.

    Returns:
        None

    Example:
        >>> output_json(entries, "output.json")
        >>> output_json(entries)  # Prints to stdout
    """
    records = json_records(entries)
    if output_file:
        with _atomic_write(output_file) as f:
            _write_json(records, f)
    else:
        _write_json(records, sys.stdout)


def output_ldif(entries: Iterable[Any], output_file: Optional[str] = None) -> None:
    """
    Output LDAP entries as LDIF.

    Formats LDAP entries according to the LDAP Data Interchange Format (LDIF)
    and outputs them either to stdout or to a file. Entries are written as
    they come, so an iterator can stream a large export.

    Args:
        entries: LDAP entry objects
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
    lines = ldif_lines(entries)
    if output_file:
        with _atomic_write(output_file) as f:
            for line in lines:
                f.write(line + "\n")
    else:
        for line in lines:
            sys.stdout.write(line + "\n")


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
        Cells that a spreadsheet would run as a formula (starting with ``=``,
        ``+``, ``-``, ``@`` or a tab) get a leading apostrophe; header cells
        (attribute names) are guarded the same way.
    """
    if not entries:
        return

    # Collect all attribute names from all entries; the header is server data too
    attr_names = {"dn"}
    for entry in entries:
        attr_names.update(entry.entry_attributes)
    column = {name: _csv_value(sanitize_text(name)) for name in attr_names}

    # Sort column names for consistent output
    fieldnames = sorted(set(column.values()))

    # Create CSV output
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for entry in entries:
        row = {column["dn"]: _csv_value(sanitize_text(entry.entry_dn))}
        for attr in entry.entry_attributes:
            # Join multiple values with a semicolon
            values = ";".join(_text_value(v) for v in entry[attr].values)
            row[column[attr]] = _csv_value(values)

        writer.writerow(row)

    csv_text = output.getvalue()

    if output_file:
        with _atomic_write(output_file, newline="") as f:
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
        entry_node = parent_node.add(f"[yellow]{safe_text(parts[0])}[/yellow]")

        for attr_name in sorted(entry.entry_attributes):
            name = safe_text(attr_name)
            values = [escape(_text_value(v)) for v in entry[attr_name].values]
            if len(values) == 1:
                entry_node.add(f"[cyan]{name}:[/cyan] [green]{values[0]}[/green]")
            else:
                attr_node = entry_node.add(f"[cyan]{name}:[/cyan]")
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
        with _atomic_write(output_file) as f:
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
        with _atomic_write(output_file) as f_out:
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
            table.add_row(safe_text(attr_name), "\n".join(values))

        panel = Panel(
            table,
            title=f"[yellow]{safe_text(entry.entry_dn)}[/yellow]",
            title_align="left",
            border_style="blue",
        )
        console.print(panel)
        console.print()  # Empty line between entries

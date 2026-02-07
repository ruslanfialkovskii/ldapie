#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output formatting functions (JSON, LDIF, CSV, etc.) for LDAPie.
"""

import json
import base64
import csv
from io import StringIO
from typing import List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box
from ldap3.utils.dn import parse_dn

def _json_safe_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return f"base64:{base64.b64encode(value).decode('ascii')}"
    return value

def _ldif_needs_base64(value: str) -> bool:
    if not value:
        return False
    if value[0] in (" ", ":", "<"):
        return True
    for ch in value:
        if ch in ("\n", "\r") or ord(ch) < 0x20 or ord(ch) >= 0x7f:
            return True
    return False

def _ldif_value_line(attr_name: str, value: Any) -> str:
    if isinstance(value, bytes):
        b64_value = base64.b64encode(value).decode("ascii")
        return f"{attr_name}:: {b64_value}"
    str_value = str(value)
    if _ldif_needs_base64(str_value):
        b64_value = base64.b64encode(str_value.encode("utf-8")).decode("ascii")
        return f"{attr_name}:: {b64_value}"
    return f"{attr_name}: {str_value}"

def _split_dn(dn: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    escape = False
    for ch in dn:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            buf.append(ch)
            escape = True
            continue
        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf).strip())
    return [part for part in parts if part]

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
    # Convert entries to JSON-compatible dictionaries
    json_entries = []
    for entry in entries:
        entry_dict = {"dn": entry.entry_dn}
        for attr_name in entry.entry_attributes:
            if len(entry[attr_name].values) == 1:
                # Single value
                entry_dict[attr_name] = _json_safe_value(entry[attr_name].value)
            else:
                # Multi-value
                entry_dict[attr_name] = [
                    _json_safe_value(value) for value in entry[attr_name].values
                ]
        json_entries.append(entry_dict)
    
    # Output JSON
    json_str = json.dumps(json_entries, indent=2)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:  # Added encoding
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
        Binary values are automatically base64-encoded according to LDIF specs.
    """
    ldif_lines = []
    
    for entry in entries:
        ldif_lines.append(f"dn: {entry.entry_dn}")
        
        for attr_name in sorted(entry.entry_attributes):
            for value in entry[attr_name].values:
                ldif_lines.append(_ldif_value_line(attr_name, value))
        
        ldif_lines.append("")  # Empty line between entries
    
    ldif_text = "\n".join(ldif_lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:  # Added encoding
            f.write(ldif_text)
    else:
        print(ldif_text)

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
    all_attrs = set(["dn"])
    for entry in entries:
        all_attrs.update(entry.entry_attributes)
    
    # Sort attribute names for consistent output
    all_attrs = sorted(list(all_attrs))
    
    # Create CSV output
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=all_attrs)
    writer.writeheader()
    
    for entry in entries:
        row = {"dn": entry.entry_dn}
        for attr in entry.entry_attributes:
            if len(entry[attr].values) == 1:
                row[attr] = entry[attr].value
            else:
                # Join multiple values with a semicolon
                row[attr] = ";".join(str(v) for v in entry[attr].values)
                
        writer.writerow(row)
    
    csv_text = output.getvalue()
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:  # Added encoding
            f.write(csv_text)
    else:
        print(csv_text)

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
    # Create root tree
    root_tree = Tree(f"[yellow]{base_dn}[/yellow]")
    
    # Organize entries by DN hierarchy
    tree_nodes = {base_dn: root_tree}
    
    # Sort entries by DN length (shallowest first)
    sorted_entries = sorted(entries, key=lambda e: len(parse_dn(e.entry_dn)))
    
    for entry in sorted_entries:
        dn = entry.entry_dn
        
        # Skip if this is the base DN
        if dn == base_dn:
            continue
            
        # Find parent DN
        dn_parts = _split_dn(dn)
        parent_dn = ",".join(dn_parts[1:]) if len(dn_parts) > 1 else base_dn
        
        # If we don't have the parent, use the base or nearest ancestor
        if parent_dn not in tree_nodes:
            parent_dn = base_dn
            
        # Add this entry to its parent
        if parent_dn in tree_nodes:
            rdn = dn_parts[0] if dn_parts else dn
            entry_node = tree_nodes[parent_dn].add(f"[yellow]{rdn}[/yellow]")
            
            # Add attributes as children
            for attr_name in sorted(entry.entry_attributes):
                values = entry[attr_name].values
                if len(values) == 1:
                    entry_node.add(f"[cyan]{attr_name}:[/cyan] [green]{values[0]}[/green]")
                else:
                    attr_node = entry_node.add(f"[cyan]{attr_name}:[/cyan]")
                    for value in values:
                        attr_node.add(f"[green]{value}[/green]")
            
            # Add this node to tree_nodes for potential children
            tree_nodes[dn] = entry_node
    
    return root_tree

def output_tree(entries: List[Any], base_dn: str, console: Console, output_file: Optional[str] = None) -> None:
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
        with open(output_file, 'w', encoding='utf-8') as f:  # Added encoding
            console = Console(file=f, highlight=False)
            console.print(tree)
    else:
        console.print(tree)

def output_rich(entries: List[Any], console: Console, output_file: Optional[str] = None) -> None:
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
        # Ensure the file is opened with utf-8 encoding
        with open(output_file, 'w', encoding='utf-8') as f_out:  # Added encoding and changed variable name
            out_console = Console(file=f_out, highlight=False)
    else:
        out_console = console
        
    for entry in entries:
        # Create a panel for each entry
        table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
        table.add_column("Attribute", style="cyan")
        table.add_column("Value", style="green")
        
        for attr_name in sorted(entry.entry_attributes):
            values = entry[attr_name].values
            if len(values) == 1:
                table.add_row(attr_name, str(values[0]))
            else:
                # For multi-valued attributes, join with newlines
                table.add_row(attr_name, "\n".join(str(v) for v in values))
        
        # Create a panel with the DN as title
        panel = Panel(
            table,
            title=f"[yellow]{entry.entry_dn}[/yellow]",
            title_align="left",
            border_style="blue"
        )
        out_console.print(panel)
        out_console.print()  # Empty line between entries

def format_output_filename(filename: str, extension: str) -> str:
    """
    Format output filename based on extension.
    
    Ensures the filename has the correct extension.
    
    Args:    
        filename: Base filename
        extension: File extension without leading dot
    
    Returns:
        Filename with proper extension
        
    Example:
        >>> format_output_filename("results", "json")  # "results.json"
        >>> format_output_filename("results.txt", "json")  # "results.txt.json"
        >>> format_output_filename("results.json", "json")  # "results.json"
    """
    if filename.endswith(f".{extension}"):
        return filename
    elif "." in filename:
        return f"{filename}.{extension}"
    else:
        return f"{filename}.{extension}"


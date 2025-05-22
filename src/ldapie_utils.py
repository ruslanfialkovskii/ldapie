#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for LDAPie - A modern LDAP client CLI tool

This module provides utility functions for LDAP operations and formatting results.
It works with ldap3 library for LDAP operations and rich library for 
terminal output formatting.

Functions are categorized into several groups:
- Search and query functions
- Output formatting functions (JSON, LDIF, CSV, etc.)
- LDAP entry manipulation functions (add, modify, delete, rename)
- Server information and schema retrieval
- Helper utilities for DN, filters, and attributes
"""

import os
import sys
import json
import base64
import getpass
from typing import List, Dict, Any, Optional, Tuple
import ldap3
from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES, BASE, LEVEL
from ldap3 import MODIFY_ADD, MODIFY_REPLACE, MODIFY_DELETE
from ldap3.utils.dn import parse_dn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich import box
import csv
from io import StringIO

def paged_search(
    conn: Connection,
    base_dn: str,
    filter_query: str,
    search_scope,
    attributes,
    page_size: int,
    limit: Optional[int] = None
) -> List[Any]:
    """
    Perform a paged search and return all entries.
    
    Uses the LDAP paged results control to retrieve large result sets in
    chunks, which is more efficient than fetching all results at once.
    
    Args:
        conn: LDAP connection object
        base_dn: Search base DN
        filter_query: LDAP search filter
        search_scope: Search scope (BASE, LEVEL, SUBTREE)
        attributes: List of attributes to retrieve or ALL_ATTRIBUTES
        page_size: Number of entries per page
        limit: Maximum number of entries to return (None for no limit)
    
    Returns:
        List of LDAP entry objects
        
    Example:
        >>> entries = paged_search(conn, "dc=example,dc=com", "(objectClass=person)", 
        ...                        SUBTREE, ["cn", "mail"], 100, 500)
    """
    entries = []
    entry_count = 0
    cookie = None
    
    while True:
        conn.search(
            base_dn,
            filter_query,
            search_scope=search_scope,
            attributes=attributes,
            paged_size=page_size,
            paged_cookie=cookie
        )
        
        entries.extend(conn.entries)
        entry_count += len(conn.entries)
        
        # Check if we've reached the limit
        if limit and entry_count >= limit:
            entries = entries[:limit]
            break
            
        # Get cookie for next page
        cookie = conn.result.get('controls', {}).get('1.2.840.113556.1.4.319', {}).get('value', {}).get('cookie')
        
        # If no more pages, exit loop
        if not cookie:
            break
            
    return entries

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
                entry_dict[attr_name] = entry[attr_name].value
            else:
                # Multi-value
                entry_dict[attr_name] = list(entry[attr_name].values)
        json_entries.append(entry_dict)
    
    # Output JSON
    json_str = json.dumps(json_entries, indent=2)
    
    if output_file:
        with open(output_file, 'w') as f:
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
                if isinstance(value, bytes):
                    # Base64 encode binary values
                    b64_value = base64.b64encode(value).decode('ascii')
                    ldif_lines.append(f"{attr_name}:: {b64_value}")
                else:
                    # Handle special characters in value
                    str_value = str(value)
                    if str_value.startswith(' ') or str_value.startswith(':') or str_value.startswith('<'):
                        ldif_lines.append(f"{attr_name}: {str_value}")
                    else:
                        ldif_lines.append(f"{attr_name}: {str_value}")
        
        ldif_lines.append("")  # Empty line between entries
    
    ldif_text = "\n".join(ldif_lines)
    
    if output_file:
        with open(output_file, 'w') as f:
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
        with open(output_file, 'w') as f:
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
    # Parse base DN
    base_parts = parse_dn(base_dn)
    
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
        parent_dn = ",".join(dn.split(",")[1:])
        
        # If we don't have the parent, use the base or nearest ancestor
        if parent_dn not in tree_nodes:
            parent_dn = base_dn
            
        # Add this entry to its parent
        if parent_dn in tree_nodes:
            entry_node = tree_nodes[parent_dn].add(f"[yellow]{dn.split(',')[0]}[/yellow]")
            
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
        with open(output_file, 'w') as f:
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
        out_console = Console(file=open(output_file, 'w'), highlight=False)
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

def output_server_info_rich(server: Server, conn: Connection, console: Console) -> None:
    """
    Display server information in rich text format.
    
    Shows details about the LDAP server including vendor, version,
    supported controls, extensions, and naming contexts.
    
    Args:
        server: LDAP server object
        conn: LDAP connection object
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> output_server_info_rich(server, conn, console)
    """
    # For testing purposes, check if we have a mocked _info attribute
    server_info = getattr(server, "_info", server.info)
    
    if not server_info:
        console.print("[yellow]No server info available.[/yellow]")
        return
        
    # Create a table for server info
    table = Table(title="LDAP Server Information", box=box.ROUNDED, show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Add server properties
    if hasattr(server_info, "vendor_name"):
        table.add_row("Vendor", str(server_info.vendor_name))
    if hasattr(server_info, "vendor_version"):
        table.add_row("Version", str(server_info.vendor_version))
    
    # Add supported LDAP protocol versions
    if hasattr(server_info, "supported_ldap_versions"):
        # Convert list to string before adding to table
        versions_str = ", ".join(str(v) for v in server_info.supported_ldap_versions)
        table.add_row("LDAP Versions", versions_str)
    
    # Add supported controls
    if hasattr(server_info, "supported_controls"):
        controls = []
        for oid in server_info.supported_controls:
            try:
                control_name = ldap3.protocol.rfc4511.KNOWN_CONTROLS.get(oid, oid)
                controls.append(f"{control_name}")
            except (AttributeError, KeyError):
                controls.append(str(oid))
        # Ensure controls is a string, not a list
        controls_str = "\n".join(controls) if controls else "None"
        table.add_row("Supported Controls", controls_str)
    
    # Add supported extensions
    if hasattr(server_info, "supported_extensions"):
        exts = []
        for oid in server_info.supported_extensions:
            try:
                ext_name = ldap3.protocol.rfc4511.KNOWN_EXTENSIONS.get(oid, oid)
                exts.append(f"{ext_name}")
            except (AttributeError, KeyError):
                exts.append(str(oid))
        # Ensure extensions is a string, not a list
        exts_str = "\n".join(exts) if exts else "None"
        table.add_row("Supported Extensions", exts_str)
    
    # Add naming contexts
    if hasattr(server_info, "naming_contexts"):
        # Convert list to string before adding to table
        contexts_str = "\n".join(str(ctx) for ctx in server_info.naming_contexts) if server_info.naming_contexts else "None"
        table.add_row("Naming Contexts", contexts_str)
    
    console.print(table)

def output_server_info_json(server: Server, conn: Connection, console: Console) -> None:
    """
    Display server information in JSON format.
    
    Outputs LDAP server information as JSON, including vendor, version,
    supported controls, extensions, and naming contexts.
    
    Args:
        server: LDAP server object
        conn: LDAP connection object
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> output_server_info_json(server, conn, console)
    """
    if not server.info:
        console.print("[warning]No server info available.[/warning]")
        return
        
    info = {}
    
    # Add server properties
    if hasattr(server.info, "vendor_name"):
        info["vendor"] = server.info.vendor_name
    if hasattr(server.info, "vendor_version"):
        info["version"] = server.info.vendor_version
    
    # Add supported LDAP protocol versions
    if hasattr(server.info, "supported_ldap_versions"):
        info["ldap_versions"] = server.info.supported_ldap_versions
        
    # Add supported controls
    if hasattr(server.info, "supported_controls"):
        info["supported_controls"] = {}
        for oid in server.info.supported_controls:
            control_name = ldap3.protocol.rfc4511.KNOWN_CONTROLS.get(oid, oid)
            info["supported_controls"][oid] = control_name
        
    # Add supported extensions
    if hasattr(server.info, "supported_extensions"):
        info["supported_extensions"] = {}
        for oid in server.info.supported_extensions:
            ext_name = ldap3.protocol.rfc4511.KNOWN_EXTENSIONS.get(oid, oid)
            info["supported_extensions"][oid] = ext_name
        
    # Add naming contexts
    if hasattr(server.info, "naming_contexts"):
        info["naming_contexts"] = server.info.naming_contexts
    
    print(json.dumps(info, indent=2))

def compare_entries(
    conn: Connection, 
    dn1: str, 
    dn2: str, 
    attrs: List[str], 
    console: Console
) -> None:
    """
    Compare two LDAP entries.
    
    Compares attributes between two LDAP entries and displays differences
    in a detailed table.
    
    Args:
        conn: LDAP connection object
        dn1: DN of first entry to compare
        dn2: DN of second entry to compare
        attrs: List of attributes to compare (if empty, compares all attributes)
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> compare_entries(conn, "uid=user1,ou=users,dc=example,dc=com", 
        ...                "uid=user2,ou=users,dc=example,dc=com", 
        ...                ["cn", "mail"], console)
    """
    # Get the entries
    attributes = list(attrs) if attrs else ALL_ATTRIBUTES
    
    # Search for first entry
    conn.search(dn1, "(objectClass=*)", search_scope="BASE", attributes=attributes)
    if not conn.entries:
        console.print(f"[red]Entry not found: {dn1}[/red]")
        return
    entry1 = conn.entries[0]
    
    # Search for second entry
    conn.search(dn2, "(objectClass=*)", search_scope="BASE", attributes=attributes)
    if not conn.entries:
        console.print(f"[red]Entry not found: {dn2}[/red]")
        return
    entry2 = conn.entries[0]
    
    # Get all attributes to compare
    attr_set = set(entry1.entry_attributes).union(set(entry2.entry_attributes))
    if attrs:
        attr_set = attr_set.intersection(set(attrs))
    
    # Create comparison table
    table = Table(title="Entry Comparison", box=box.ROUNDED, show_header=True)
    table.add_column("Attribute", style="cyan")
    table.add_column(f"DN 1: {dn1}", style="green")
    table.add_column(f"DN 2: {dn2}", style="green")
    table.add_column("Status", style="yellow")
    
    # Compare each attribute
    equal_count = 0
    diff_count = 0
    missing_count = 0
    
    for attr in sorted(attr_set):
        has_attr1 = attr in entry1.entry_attributes
        has_attr2 = attr in entry2.entry_attributes
        
        if has_attr1 and has_attr2:
            # Both entries have this attribute
            values1 = sorted(str(v) for v in entry1[attr].values)
            values2 = sorted(str(v) for v in entry2[attr].values)
            
            if values1 == values2:
                # Values are equal
                table.add_row(
                    attr,
                    "\n".join(values1),
                    "\n".join(values2),
                    "✓ Equal"
                )
                equal_count += 1
            else:
                # Values differ
                table.add_row(
                    attr,
                    "\n".join(values1),
                    "\n".join(values2),
                    "≠ Different"
                )
                diff_count += 1
        elif has_attr1:
            # Only first entry has this attribute
            table.add_row(
                attr,
                "\n".join(str(v) for v in entry1[attr].values),
                "",
                "! Missing in DN 2"
            )
            missing_count += 1
        elif has_attr2:
            # Only second entry has this attribute
            table.add_row(
                attr,
                "",
                "\n".join(str(v) for v in entry2[attr].values),
                "! Missing in DN 1"
            )
            missing_count += 1
    
    # Print the comparison table
    console.print(table)
    
    # Print summary
    console.print(f"\n[yellow]Comparison Summary:[/yellow]")
    console.print(f"  Equal attributes: {equal_count}")
    console.print(f"  Different attributes: {diff_count}")
    console.print(f"  Missing attributes: {missing_count}")

def show_schema(server: Server, object_class: Optional[str], attribute: Optional[str], console: Console) -> None:
    """
    Display schema information from the server.
    
    Shows LDAP schema information for object classes or attributes.
    If no specific object class or attribute is provided, lists all object classes.
    
    Args:
        server: LDAP server object
        object_class: Optional specific object class to show
        attribute: Optional specific attribute to show
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> show_schema(server, "person", None, console)  # Show info for person class
        >>> show_schema(server, None, "cn", console)      # Show info for cn attribute
        >>> show_schema(server, None, None, console)      # List all object classes
        
    Note:
        Cannot specify both object_class and attribute at the same time.
    """
    if not server.schema:
        console.print("[warning]No schema information available.[/warning]")
        return
    
    if object_class and attribute:
        console.print("[error]Cannot specify both object class and attribute.[/error]")
        return
    
    if object_class:
        # Show info about a specific object class
        oc_info = server.schema.object_classes.get(object_class.lower())
        if not oc_info:
            console.print(f"[error]Object class '{object_class}' not found in schema.[/error]")
            return
            
        table = Table(title=f"Object Class: {object_class}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")
        
        table.add_row("Name", oc_info.name)
        table.add_row("OID", oc_info.oid)
        table.add_row("Description", oc_info.description or "")
        table.add_row("Type", oc_info.type or "")
        
        if oc_info.must_contain:
            table.add_row("Required Attributes", "\n".join(sorted(oc_info.must_contain)))
        else:
            table.add_row("Required Attributes", "None")
            
        if oc_info.may_contain:
            table.add_row("Optional Attributes", "\n".join(sorted(oc_info.may_contain)))
        else:
            table.add_row("Optional Attributes", "None")
            
        if oc_info.superior:
            table.add_row("Parent Classes", "\n".join(sorted(oc_info.superior)))
        else:
            table.add_row("Parent Classes", "None")
            
        console.print(table)
        
    elif attribute:
        # Show info about a specific attribute
        attr_info = server.schema.attribute_types.get(attribute.lower())
        if not attr_info:
            console.print(f"[error]Attribute '{attribute}' not found in schema.[/error]")
            return
            
        table = Table(title=f"Attribute: {attribute}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")
        
        table.add_row("Name", attr_info.name)
        table.add_row("OID", attr_info.oid)
        table.add_row("Description", attr_info.description or "")
        table.add_row("Syntax", attr_info.syntax or "")
        table.add_row("Single Value", "Yes" if attr_info.single_value else "No")
        
        if attr_info.equality:
            table.add_row("Equality Match", attr_info.equality)
        if attr_info.ordering:
            table.add_row("Ordering", attr_info.ordering)
        if attr_info.substring:
            table.add_row("Substring Match", attr_info.substring)
            
        console.print(table)
        
    else:
        # List all object classes
        table = Table(title="Object Classes", box=box.ROUNDED)
        table.add_column("Name", style="ldap.attr")
        table.add_column("Description", style="ldap.value")
        
        for name, oc_info in sorted(server.schema.object_classes.items()):
            table.add_row(name, oc_info.description or "")
            
        console.print(table)

def delete_recursive(conn: Connection, dn: str, console: Console) -> None:
    """
    Delete an entry and all its children recursively.
    
    Performs a bottom-up deletion of an LDAP subtree, starting with
    leaf entries and working up to the parent.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name of the root entry to delete
        console: Rich Console object for output and logging
    
    Returns:
        None
        
    Example:
        >>> delete_recursive(conn, "ou=users,dc=example,dc=com", console)
        
    Note:
        This operation can be dangerous and should be used with caution.
    """
    # First, find all children
    console.print(f"[info]Searching for children of {dn}...[/info]")
    conn.search(dn, "(objectClass=*)", search_scope=SUBTREE, attributes=["objectClass"])
    
    if not conn.entries:
        console.print("[warning]Entry not found or no children to delete.[/warning]")
        return
    
    # Sort entries by longest DN first (leaf nodes)
    entries = sorted(conn.entries, key=lambda e: len(e.entry_dn), reverse=True)
    
    total = len(entries)
    console.print(f"[info]Found {total} entries to delete.[/info]")
    
    # Delete entries from the bottom up
    success = 0
    failures = 0
    for idx, entry in enumerate(entries, 1):
        entry_dn = entry.entry_dn
        console.print(f"[info]Deleting {idx}/{total}: {entry_dn}[/info]")
        
        if conn.delete(entry_dn):
            success += 1
        else:
            console.print(f"[warning]Failed to delete {entry_dn}: {conn.result}[/warning]")
            failures += 1
    
    # Print summary
    console.print(f"[success]Successfully deleted {success} entries.[/success]")
    if failures:
        console.print(f"[error]Failed to delete {failures} entries.[/error]")

def parse_modification_attributes(add_attrs, replace_attrs, delete_attrs):
    """
    Parse modification attributes from command-line arguments.
    
    Converts command-line attribute specifications into a format suitable
    for LDAP modify operations.
    
    Args:
        add_attrs: List of attributes to add in format "name=value"
        replace_attrs: List of attributes to replace in format "name=value"
        delete_attrs: List of attributes to delete (either "name" or "name=value")
    
    Returns:
        Dictionary of LDAP modifications compatible with ldap3.Connection.modify()
        
    Example:
        >>> mods = parse_modification_attributes(
        ...     ["mail=user@example.com"], 
        ...     ["title=Manager"], 
        ...     ["description", "mobile=12345"])
    """
    from ldap3 import MODIFY_ADD, MODIFY_REPLACE, MODIFY_DELETE
    
    changes = {}
    
    # Process additions
    for attr_str in add_attrs:
        try:
            name, value = attr_str.split('=', 1)
            if name not in changes:
                changes[name] = {'operation': MODIFY_ADD, 'value': []}
            if isinstance(changes[name]['value'], list):
                changes[name]['value'].append(value)
            else:
                changes[name]['value'] = [changes[name]['value'], value]
        except ValueError:
            continue
            
    # Process replacements
    for attr_str in replace_attrs:
        try:
            name, value = attr_str.split('=', 1)
            changes[name] = {'operation': MODIFY_REPLACE, 'value': value}
        except ValueError:
            continue
            
    # Process deletions
    for attr_str in delete_attrs:
        if '=' in attr_str:
            try:
                name, value = attr_str.split('=', 1)
                if name not in changes:
                    changes[name] = {'operation': MODIFY_DELETE, 'value': []}
                if isinstance(changes[name]['value'], list):
                    changes[name]['value'].append(value)
                else:
                    changes[name]['value'] = [changes[name]['value'], value]
            except ValueError:
                continue
        else:
            # Delete entire attribute
            changes[attr_str] = {'operation': MODIFY_DELETE, 'value': []}
            
    return changes

def start_interactive_session(server, conn, console, base_dn=None):
    """
    Start an interactive LDAP console session.
    
    Launches an interactive shell-like interface for performing LDAP operations.
    
    Args:
        server: LDAP server object or None if not connected yet
        conn: LDAP connection object or None if not connected yet
        console: Rich Console object for output
        base_dn: Optional base DN to use for operations
    
    Returns:
        None
        
    Example:
        >>> start_interactive_session(server, conn, console, "dc=example,dc=com")
        
    Note:
        If server and conn are None, the interactive session starts in
        disconnected mode, allowing the user to connect later.
    """
    import cmd
    from rich.panel import Panel
    from ldap3 import SUBTREE, ALL_ATTRIBUTES
    
    # Import context-sensitive help components
    try:
        from src.help_context import HelpContext, CommandValidator
        from src.help_overlay import process_help_key, show_help_overlay
        # Initialize help context
        help_context = HelpContext()
        command_validator = CommandValidator(help_context)
        help_available = True
    except ImportError:
        help_available = False
    
    class LDAPShell(cmd.Cmd):
        intro = "\nWelcome to LDAPie interactive console. Type help or ? to list commands.\n"
        prompt = "ldapie> "
        
        def __init__(self, server, conn, console, base_dn):
            super().__init__()
            self.server = server
            self.conn = conn
            self.console = console
            self.base_dn = base_dn or ""
            self.connected = conn is not None and conn.bound
            self.help_context = HelpContext() if help_available else None
            
            # Update prompt to show current base DN
            self._update_prompt()
            
            # Update session state in help context
            if help_available and self.help_context:
                self.help_context.update_session_state(
                    connected=self.connected,
                    server=self.server,
                    connection=self.conn,
                    authenticated=self.connected and self.conn.bound
                )
        
        def _update_prompt(self):
            base_str = f" [{self.base_dn}]" if self.base_dn else ""
            self.prompt = f"ldapie{base_str}> "
        
        def cmdloop(self, intro=None):
            """Override cmdloop to add custom command processing"""
            while True:
                try:
                    # We need to override the input handling for '?' support
                    if self.cmdqueue:
                        line = self.cmdqueue.pop(0)
                    else:
                        if self.use_rawinput:
                            try:
                                # Use our custom input handler
                                line = self.get_input(self.prompt)
                            except EOFError:
                                line = 'EOF'
                        else:
                            self.stdout.write(self.prompt)
                            self.stdout.flush()
                            line = self.stdin.readline()
                            if not len(line):
                                line = 'EOF'
                            else:
                                line = line.rstrip('\r\n')
                                
                    line = self.precmd(line)
                    stop = self.onecmd(line)
                    stop = self.postcmd(stop, line)
                    if stop:
                        break
                except KeyboardInterrupt:
                    self.console.print("\n[warning]Interrupted[/warning]")
                except Exception as e:
                    self.console.print(f"\n[error]Error: {str(e)}[/error]")
        
        def get_input(self, prompt):
            """Custom input handler that supports '?' for context help"""
            line = input(prompt)
            if line.endswith('?') and help_available:
                # Process the help request and show overlay
                line_without_question = line[:-1].strip()
                show_help_overlay(line_without_question, self.help_context, self.console)
                return line_without_question
            return line
        
        def onecmd(self, line):
            """Override onecmd to add command history and validation"""
            # Skip empty lines
            if not line:
                return False
                
            # Add command to help context history
            if help_available and self.help_context:
                self.help_context.add_command(line)
                
            # Process the command normally
            return cmd.Cmd.onecmd(self, line)
        
        def precmd(self, line):
            """Process the command line before execution"""
            return line
            
        def postcmd(self, stop, line):
            """Process the command line after execution"""
            return stop
            
        def do_validate(self, arg):
            """
            Validate a command without executing it
            Usage: validate <command>
            """
            if not arg:
                self.console.print("[error]Please provide a command to validate[/error]")
                return
                
            if not help_available:
                self.console.print("[error]Command validation is not available[/error]")
                return
                
            result = command_validator.validate_command(arg)
            
            if "error" in result:
                self.console.print(f"[error]Error: {result['error']}[/error]")
                if "suggestion" in result:
                    self.console.print(f"[info]Suggestion: {result['suggestion']}[/info]")
                if "examples" in result:
                    self.console.print("\n[bold]Examples:[/bold]")
                    for example in result['examples']:
                        self.console.print(f"  [command]{example}[/command]")
            else:
                if "validation" in result:
                    self.console.print(f"[success]✓ {result['validation']}[/success]")
                if "preview" in result:
                    self.console.print(f"\n[bold]Preview:[/bold] {result['preview']}")
                if "warning" in result:
                    self.console.print(f"\n[warning]Warning: {result['warning']}[/warning]")
                if "suggestion" in result:
                    self.console.print(f"\n[info]Suggestion: {result['suggestion']}[/info]")
            
        def do_connect(self, arg):
            """
            Connect to an LDAP server
            Usage: connect host [port] [username] [--ssl]
            """
            from getpass import getpass
            import ldap3
            
            args = arg.split()
            if not args:
                self.console.print("[error]Must specify a hostname[/error]")
                return
                
            host = args[0]
            port = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            username = args[2] if len(args) > 2 and not args[2].startswith('-') else None
            use_ssl = '--ssl' in args
            
            # Create server connection
            try:
                server_uri = f"{'ldaps' if use_ssl else 'ldap'}://{host}"
                if port:
                    server_uri += f":{port}"
                    
                server = ldap3.Server(server_uri, get_info=ldap3.ALL)
                
                if username:
                    password = getpass(f"Password for {username}: ")
                    conn = ldap3.Connection(server, user=username, password=password, auto_bind=True)
                else:
                    conn = ldap3.Connection(server, auto_bind=True)
                    
                self.server = server
                self.conn = conn
                self.connected = True
                
                self.console.print(f"[success]Connected to {host}[/success]")
                
                # Update command prompt
                self._update_prompt()
                
                # Update help context with connection state
                if help_available and self.help_context:
                    self.help_context.update_session_state(
                        connected=True,
                        authenticated=username is not None,
                        server=server,
                        connection=conn,
                        ssl_enabled=use_ssl
                    )
                
            except Exception as e:
                self.console.print(f"[error]Connection failed: {e}[/error]")
                
                # Update help context with failed connection
                if help_available and self.help_context:
                    self.help_context.add_error("connect " + arg, str(e))
        
        def do_base(self, arg):
            """Set the base DN for operations"""
            if arg:
                self.base_dn = arg
                self._update_prompt()
                self.console.print(f"[info]Base DN set to: {self.base_dn}[/info]")
                
                # Update help context with base DN
                if help_available and self.help_context:
                    self.help_context.current_context["base_dn"] = arg
            else:
                self.console.print(f"[info]Current base DN: {self.base_dn}[/info]")
        
        def do_search(self, arg):
            """
            Search the LDAP directory
            Usage: search [filter] [attribute1 attribute2 ...]
            """
            if not self.connected:
                self.console.print("[error]Not connected to any LDAP server[/error]")
                return
                
            if not self.base_dn:
                self.console.print("[error]Base DN not set. Use 'base' command to set it.[/error]")
                return
                
            # Parse arguments
            args = arg.split()
            filter_query = args[0] if args else "(objectClass=*)"
            attributes = args[1:] if len(args) > 1 else ALL_ATTRIBUTES
            
            try:
                self.console.print(f"[info]Searching with filter: {filter_query}[/info]")
                self.conn.search(
                    self.base_dn, 
                    filter_query, 
                    search_scope=SUBTREE, 
                    attributes=attributes
                )
                
                if not self.conn.entries:
                    self.console.print("[warning]No entries found.[/warning]")
                    return
                    
                self.console.print(f"[success]Found {len(self.conn.entries)} entries.[/success]")
                output_rich(self.conn.entries, self.console)
                
                # Update help context with search results
                if help_available and self.help_context:
                    self.help_context.update_search_results(self.conn.entries)
                
            except Exception as e:
                self.console.print(f"[error]Search failed: {e}[/error]")
                
                # Add error to help context
                if help_available and self.help_context:
                    self.help_context.add_error("search " + arg, str(e))
        
        def do_info(self, arg):
            """Show information about the connected LDAP server"""
            if not self.connected:
                self.console.print("[error]Not connected to any LDAP server[/error]")
                return
                
            output_server_info_rich(self.server, self.conn, self.console)
        
        def do_schema(self, arg):
            """
            View schema information
            Usage: schema [objectClass|--attr attribute_name]
            """
            if not self.connected:
                self.console.print("[error]Not connected to any LDAP server[/error]")
                return
                
            args = arg.split()
            if not args:
                # Show all object classes
                show_schema(self.server, None, None, self.console)
            elif args[0] == '--attr' and len(args) > 1:
                # Show specific attribute
                show_schema(self.server, None, args[1], self.console)
            else:
                # Show specific object class
                show_schema(self.server, args[0], None, self.console)
        
        def do_exit(self, arg):
            """Exit the interactive console"""
            self.console.print("[info]Exiting interactive mode.[/info]")
            return True
            
        def do_quit(self, arg):
            """Exit the interactive console"""
            return self.do_exit(arg)
            
        def do_suggest(self, arg):
            """Show context-aware suggestions based on current state"""
            if not help_available:
                self.console.print("[error]Context-sensitive help is not available[/error]")
                return
                
            suggestions = self.help_context.get_suggestions()
            
            self.console.print("\n[bold]Context-Aware Suggestions[/bold]")
            self.console.rule()
            
            if suggestions["next_commands"]:
                self.console.print("\n[bold]Next Steps[/bold]")
                for suggestion in suggestions["next_commands"]:
                    self.console.print(f"  [success]• {suggestion}[/success]")
                    
            if suggestions["examples"]:
                self.console.print("\n[bold]Examples[/bold]")
                for example in suggestions["examples"]:
                    self.console.print(f"  [command]{example}[/command]")
                    
            if suggestions["tips"]:
                self.console.print("\n[bold]Tips[/bold]")
                for tip in suggestions["tips"]:
                    self.console.print(f"  [info]• {tip}[/info]")
                    
            if not any([suggestions["next_commands"], suggestions["examples"], suggestions["tips"]]):
                self.console.print("  No specific suggestions available for current context.")
            
        def do_help(self, arg):
            """Show help information"""
            if arg:
                # Show help for specific command
                super().do_help(arg)
                
                # If context help is available, show additional examples and tips
                if help_available and self.help_context:
                    cmd_help = self.help_context.get_command_help(arg)
                    if 'examples' in cmd_help and cmd_help['examples']:
                        self.console.print("\n[bold]Examples:[/bold]")
                        for example in cmd_help['examples']:
                            self.console.print(f"  [command]{example}[/command]")
                    
                    if 'common_errors' in cmd_help and cmd_help['common_errors']:
                        self.console.print("\n[bold]Common Issues:[/bold]")
                        for tip in cmd_help['common_errors']:
                            self.console.print(f"  [info]• {tip}[/info]")
            else:
                # Show general help
                self.console.print(
                    Panel(
                        """
                        Available commands:
                        - connect host [port] [username] [--ssl]  Connect to LDAP server
                        - base <dn>                              Set base DN for operations
                        - search [filter] [attributes...]         Search the directory
                        - info                                   Show server information
                        - schema [objectclass|--attr name]        Browse schema information
                        - validate <command>                      Validate a command without executing it
                        - suggest                                 Show context-aware suggestions
                        - help [command]                         Show help for commands
                        - exit, quit                             Exit interactive mode
                        
                        TIP: Type '?' after any partial command to get context-sensitive help
                        """,
                        title="LDAPie Interactive Mode Help",
                        expand=False
                    )
                )
                
                # If we have context help available, add context-sensitive suggestions
                if help_available and self.help_context:
                    suggestions = self.help_context.get_suggestions()
                    
                    if suggestions["next_commands"]:
                        self.console.print("\n[bold]Suggested Next Steps[/bold]")
                        for suggestion in suggestions["next_commands"]:
                            self.console.print(f"  [success]• {suggestion}[/success]")
                            
                    if suggestions["tips"]:
                        self.console.print("\n[bold]Tips[/bold]")
                        for tip in suggestions["tips"]:
                            self.console.print(f"  [info]• {tip}[/info]")
    
    # Start the shell
    shell = LDAPShell(server, conn, console, base_dn)
    shell.cmdloop()

def format_output_filename(filename, extension):
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

def compare_entry(conn, dn, attribute, value):
    """
    Compare an attribute value in an LDAP entry.
    
    Performs an LDAP compare operation to check if an entry has a specific
    attribute value.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name of the entry
        attribute: Name of the attribute to compare
        value: Value to compare against
        
    Returns:
        True if the values match, False otherwise
        
    Example:
        >>> compare_entry(conn, "uid=user,dc=example,dc=com", "mail", "user@example.com")
    """
    return conn.compare(dn, attribute, value)

def get_schema_info(conn, schema_type, name=None):
    """
    Get schema information from LDAP server.
    
    Retrieves and formats schema information for object classes or attributes.
    
    Args:
        conn: LDAP connection object
        schema_type: Type of schema information to retrieve ("objectclasses" or "attributes")
        name: Optional specific name to get information about
        
    Returns:
        Formatted schema information as a string
        
    Example:
        >>> info = get_schema_info(conn, "objectclasses", "person")
        >>> info = get_schema_info(conn, "attributes", "cn")
        >>> info = get_schema_info(conn, "objectclasses")  # All object classes
        
    Raises:
        ValueError: If schema_type is invalid
    """
    if not conn.server.schema:
        return "No schema information available"
    
    if schema_type.lower() == "objectclasses" or schema_type.lower() == "objectclass":
        if name:
            schema_obj = conn.server.schema.object_classes.get(name.lower())
            if not schema_obj:
                return f"Object class '{name}' not found in schema"
            return format_schema_output(schema_obj)
        else:
            return format_schema_output(conn.server.schema.object_classes)
    
    elif schema_type.lower() == "attributes" or schema_type.lower() == "attribute":
        if name:
            schema_attr = conn.server.schema.attribute_types.get(name.lower())
            if not schema_attr:
                return f"Attribute '{name}' not found in schema"
            return format_schema_output(schema_attr)
        else:
            return format_schema_output(conn.server.schema.attribute_types)
    
    return "Invalid schema type. Use 'objectclasses' or 'attributes'"

def format_schema_output(schema_obj):
    """
    Format schema object for display.
    
    Converts schema objects into a human-readable string representation.
    
    Args:
        schema_obj: Schema object or dictionary of schema objects
        
    Returns:
        Formatted string representation
        
    Example:
        >>> output = format_schema_output(server.schema.object_classes["person"])
    """
    if isinstance(schema_obj, dict):
        # Format a collection of schema objects
        output = []
        for name, obj in schema_obj.items():
            output.append(f"{name}: {obj.description or 'No description'}")
        return "\n".join(output)
    else:
        # Format a single schema object
        result = []
        for attr in dir(schema_obj):
            if not attr.startswith('_') and not callable(getattr(schema_obj, attr)):
                value = getattr(schema_obj, attr)
                if value is not None:
                    result.append(f"{attr}: {value}")
        return "\n".join(result)

def add_entry(conn, dn, attributes):
    """
    Add a new entry to the LDAP directory.
    
    Creates a new LDAP entry with the specified DN and attributes.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name for the new entry
        attributes: Dictionary of attributes for the new entry
        
    Returns:
        True if successful
        
    Raises:
        Exception: If the add operation fails
        
    Example:
        >>> attrs = {
        ...     "objectClass": ["person", "organizationalPerson"],
        ...     "cn": ["Test User"],
        ...     "sn": ["User"],
        ...     "mail": ["user@example.com"]
        ... }
        >>> add_entry(conn, "cn=Test User,ou=users,dc=example,dc=com", attrs)
    """
    object_classes = attributes.get("objectClass", [])
    
    # Copy attributes without objectClass
    attrs = {k: v for k, v in attributes.items() if k != "objectClass"}
    
    if conn.add(dn, object_classes, attrs):
        return True
    else:
        raise Exception(f"Failed to add entry: {conn.last_error}")

def delete_entry(conn, dn, recursive=False):
    """
    Delete an entry from the LDAP directory.
    
    Removes an LDAP entry. Can optionally delete the entire subtree.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name of the entry to delete
        recursive: Whether to delete recursively (all children)
        
    Returns:
        True if successful
        
    Example:
        >>> delete_entry(conn, "cn=Test User,ou=users,dc=example,dc=com")
        >>> delete_entry(conn, "ou=users,dc=example,dc=com", recursive=True)
        
    Note:
        Using recursive=True can be dangerous and should be used with caution.
    """
    if recursive:
        # Find all children first
        conn.search(dn, "(objectClass=*)", search_scope=SUBTREE, attributes=["objectClass"])
        
        if conn.entries:
            # Sort entries by length of DN, longest first (children before parents)
            entries = sorted(conn.entries, key=lambda e: len(e.entry_dn), reverse=True)
            
            # Delete all entries from bottom up
            for entry in entries:
                conn.delete(entry.entry_dn)
            
            # If the parent DN wasn't included in the search results, delete it explicitly
            if entries and entries[-1].entry_dn != dn:
                conn.delete(dn)
            
            return True
    else:
        # Simple delete of just the requested entry
        return conn.delete(dn)

def rename_entry(conn, dn, new_rdn, delete_old_dn=True, new_superior=None):
    """
    Rename or move an LDAP entry.
    
    Changes the RDN of an entry and optionally moves it to a new parent.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name of the entry
        new_rdn: New relative distinguished name
        delete_old_dn: Whether to delete the old RDN attribute
        new_superior: Optional new parent DN
        
    Returns:
        True if successful
        
    Example:
        >>> rename_entry(conn, "cn=Old Name,ou=users,dc=example,dc=com", "cn=New Name")
        >>> rename_entry(conn, "cn=User,ou=old,dc=example,dc=com", "cn=User", 
        ...              new_superior="ou=new,dc=example,dc=com")
    """
    # When no new_superior is provided, don't pass it as None to modify_dn
    if new_superior is None:
        return conn.modify_dn(dn, new_rdn, delete_old_dn=delete_old_dn)
    else:
        return conn.modify_dn(dn, new_rdn, delete_old_dn=delete_old_dn, new_superior=new_superior)

def parse_ldap_uri(uri):
    """
    Parse an LDAP URI into components.
    
    Breaks down an LDAP URI into protocol, host, port, base DN, and SSL flag.
    
    Args:
        uri: LDAP URI string (e.g., "ldap://example.com:389/dc=example,dc=com")
        
    Returns:
        Dictionary with URI components:
        {
            "protocol": "ldap" or "ldaps",
            "host": hostname,
            "port": port number,
            "base_dn": optional base DN,
            "use_ssl": True or False
        }
        
    Example:
        >>> parse_ldap_uri("ldap://example.com:389/dc=example,dc=com")
        >>> parse_ldap_uri("ldaps://secure.example.com")
    """
    result = {
        "protocol": None,
        "host": None,
        "port": None,
        "base_dn": None,
        "use_ssl": False
    }
    
    # Parse protocol
    if uri.startswith("ldap://"):
        result["protocol"] = "ldap"
        uri = uri[7:]  # Remove 'ldap://'
        result["port"] = 389
    elif uri.startswith("ldaps://"):
        result["protocol"] = "ldaps"
        uri = uri[8:]  # Remove 'ldaps://'
        result["port"] = 636
        result["use_ssl"] = True
    
    # Split host/port from base DN
    if '/' in uri:
        host_part, base_dn = uri.split('/', 1)
        result["base_dn"] = base_dn
    else:
        host_part = uri
    
    # Parse host and port
    if ':' in host_part:
        host, port = host_part.split(':', 1)
        result["host"] = host
        result["port"] = int(port)
    else:
        result["host"] = host_part
    
    return result

def validate_search_filter(filter_str):
    """
    Validate a LDAP search filter.
    
    Performs basic validation of an LDAP search filter syntax.
    
    Args:
        filter_str: LDAP search filter string
        
    Returns:
        True if the filter appears valid, False otherwise
        
    Example:
        >>> validate_search_filter("(cn=user)")  # True
        >>> validate_search_filter("(cn=user")   # False (unbalanced parenthesis)
        
    Note:
        This is a simple syntactic validation. It doesn't check if the filter
        is semantically correct or supported by the LDAP server.
    """
    # Simple validation: check for balanced parentheses
    count = 0
    for char in filter_str:
        if char == '(':
            count += 1
        elif char == ')':
            count -= 1
        if count < 0:
            return False
    return count == 0

def parse_attributes(attr_string):
    """
    Parse a comma-separated list of attributes.
    
    Converts a comma-separated string into a list of attribute names.
    
    Args:
        attr_string: Comma-separated attribute string
        
    Returns:
        List of attribute names
        
    Example:
        >>> parse_attributes("cn,sn,mail")  # ["cn", "sn", "mail"]
        >>> parse_attributes("cn, sn, mail")  # ["cn", "sn", "mail"]
    """
    if not attr_string:
        return []
    return [attr.strip() for attr in attr_string.split(',')]

def format_json(data):
    """
    Format data as JSON.
    
    Converts a Python object to a formatted JSON string.
    
    Args:
        data: Python data structure to convert
        
    Returns:
        Formatted JSON string
        
    Example:
        >>> format_json({"dn": "cn=user,dc=example,dc=com", "cn": ["user"]})
    """
    return json.dumps(data, indent=2)

def format_ldif(entry):
    """
    Format LDAP entry as LDIF.
    
    Converts an LDAP entry object to LDIF format.
    
    Args:
        entry: LDAP entry object
        
    Returns:
        LDIF-formatted string
        
    Example:
        >>> format_ldif(entry)
    """
    lines = [f"dn: {entry.entry_dn}"]
    
    for attr_name in sorted(entry.entry_attributes_as_dict.keys()):
        for value in entry.entry_attributes_as_dict[attr_name]:
            lines.append(f"{attr_name}: {value}")
    
    return "\n".join(lines)

def format_ldap_entry(entry, format_type):
    """
    Format an LDAP entry based on specified format.
    
    Converts an LDAP entry to the requested format (JSON, LDIF, etc.).
    
    Args:
        entry: LDAP entry object
        format_type: Format to use ("json", "ldif", etc.)
        
    Returns:
        Formatted entry string
        
    Example:
        >>> format_ldap_entry(entry, "json")
        >>> format_ldap_entry(entry, "ldif")
    """
    if format_type == "json":
        data = {"dn": entry.entry_dn}
        for attr in entry.entry_attributes_as_dict:
            data[attr] = entry.entry_attributes_as_dict[attr]
        return format_json(data)
    
    elif format_type == "ldif":
        return format_ldif(entry)
    
    else:
        # Default rich text format
        return str(entry)

def convert_to_csv(entries, fields):
    """
    Convert LDAP entries to CSV format.
    
    Transforms LDAP entries into CSV format with specified fields.
    
    Args:
        entries: List of LDAP entry dictionaries
        fields: List of field names to include in CSV
        
    Returns:
        CSV-formatted string
        
    Example:
        >>> convert_to_csv(entries, ["dn", "cn", "mail"])
    """
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    
    for entry in entries:
        row = {}
        for field in fields:
            if field == "dn":
                row[field] = entry["dn"]
            elif field in entry["attributes"]:
                values = entry["attributes"][field]
                if len(values) == 1:
                    row[field] = values[0]
                else:
                    row[field] = ";".join(str(v) for v in values)
        writer.writerow(row)
    
    return output.getvalue()

def format_entries_as_csv(entries, fields):
    """
    Format LDAP entries as CSV.
    
    Prepares LDAP entries for CSV output with specified fields.
    
    Args:
        entries: List of LDAP entries
        fields: List of field names to include in CSV
        
    Returns:
        CSV-formatted string
        
    Example:
        >>> format_entries_as_csv(entries, ["dn", "cn", "mail"])
    """
    entries_list = []
    for entry in entries:
        entry_dict = {
            "dn": entry["dn"],
            "attributes": entry["attributes"]
        }
        entries_list.append(entry_dict)
    
    return convert_to_csv(entries_list, fields)

def create_connection(server, username=None, password=None):
    """
    Create an LDAP connection.
    
    Establishes a connection to an LDAP server with optional authentication.
    
    Args:
        server: LDAP server object
        username: Optional username for binding
        password: Optional password for binding
        
    Returns:
        LDAP connection object
        
    Example:
        >>> conn = create_connection(server)  # Anonymous connection
        >>> conn = create_connection(server, "cn=admin,dc=example,dc=com", "secret")
    """
    from ldap3 import Connection
    
    if username:
        conn = Connection(server, user=username, password=password, auto_bind=True)
    else:
        conn = Connection(server, auto_bind=True)
    
    return conn

def handle_error_response(error):
    """
    Handle LDAP error response.
    
    Processes an LDAP error, displays a message, and exits the program.
    
    Args:
        error: LDAP error object
        
    Returns:
        None
        
    Note:
        This function exits the program with a non-zero status.
        
    Example:
        >>> try:
        ...     conn.bind()
        ... except ldap3.core.exceptions.LDAPBindError as e:
        ...     handle_error_response(e)
    """
    import sys
    
    # Print error message to stderr
    print(f"LDAP Error: {error.description}", file=sys.stderr)
    sys.exit(1)

def safe_get_password(provided_password=None):
    """
    Securely get a password.
    
    Returns a provided password or prompts for one if not provided.
    
    Args:
        provided_password: Password that may have been provided
        
    Returns:
        Password string
        
    Example:
        >>> password = safe_get_password()  # Prompts for password
        >>> password = safe_get_password("secret")  # Returns "secret"
    """
    # The issue might be with how getpass is imported - make sure it's always available
    import getpass
    
    # Explicitly check if provided_password is None
    if provided_password is not None:
        return provided_password
    
    # If no password provided, use getpass to prompt for it
    return getpass.getpass("Password: ")

def modify_entry(conn, dn, modifications):
    """
    Modify an existing LDAP entry.
    
    Updates an LDAP entry with the specified modifications.
    
    Args:
        conn: LDAP connection object
        dn: Distinguished name of the entry
        modifications: Dictionary with modification operations
        
    Returns:
        True if successful
        
    Raises:
        Exception: If the modify operation fails
        
    Example:
        >>> modifications = {
        ...     "mail": {"operation": ldap3.MODIFY_REPLACE, "value": ["new@example.com"]},
        ...     "title": {"operation": ldap3.MODIFY_ADD, "value": ["Manager"]}
        ... }
        >>> modify_entry(conn, "cn=user,dc=example,dc=com", modifications)
    """
    if conn.modify(dn, modifications):
        return True
    else:
        raise Exception(f"Failed to modify entry: {conn.last_error}")

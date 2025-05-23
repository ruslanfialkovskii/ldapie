#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP search and query related functions for LDAPie.
"""

from typing import List, Any, Optional
from ldap3 import Connection, ALL_ATTRIBUTES, BASE
from rich.console import Console
from rich.table import Table
from rich import box

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
    conn.search(dn1, "(objectClass=*)", search_scope=BASE, attributes=attributes)
    if not conn.entries:
        console.print(f"[red]Entry not found: {dn1}[/red]")
        return
    entry1 = conn.entries[0]
    
    # Search for second entry
    conn.search(dn2, "(objectClass=*)", search_scope=BASE, attributes=attributes)
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
                    "\\n".join(values1),
                    "\\n".join(values2),
                    "✓ Equal"
                )
                equal_count += 1
            else:
                # Values differ
                table.add_row(
                    attr,
                    "\\n".join(values1),
                    "\\n".join(values2),
                    "≠ Different"
                )
                diff_count += 1
        elif has_attr1:
            # Only first entry has this attribute
            table.add_row(
                attr,
                "\\n".join(str(v) for v in entry1[attr].values),
                "",
                "! Missing in DN 2"
            )
            missing_count += 1
        elif has_attr2:
            # Only second entry has this attribute
            table.add_row(
                attr,
                "",
                "\\n".join(str(v) for v in entry2[attr].values),
                "! Missing in DN 1"
            )
            missing_count += 1
    
    # Print the comparison table
    console.print(table)
    
    # Print summary
    console.print("\\n[yellow]Comparison Summary:[/yellow]")
    console.print(f"  Equal attributes: {equal_count}")
    console.print(f"  Different attributes: {diff_count}")
    console.print(f"  Missing attributes: {missing_count}")

def compare_entry(conn: Connection, dn: str, attribute: str, value: Any) -> bool:
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

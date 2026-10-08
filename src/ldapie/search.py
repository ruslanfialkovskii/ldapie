#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP search and query related functions for LDAPie.
"""

from typing import Any, Iterator, List, Optional

from ldap3 import ALL_ATTRIBUTES, BASE, Connection
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from .output import safe_text

PAGED_RESULTS_OID = "1.2.840.113556.1.4.319"


def iter_paged_search(
    conn: Connection,
    base_dn: str,
    filter_query: str,
    search_scope,
    attributes,
    page_size: int,
    limit: Optional[int] = None,
) -> Iterator[Any]:
    """
    Run a paged search and yield the entries page by page.

    Uses the LDAP paged results control, so server size limits do not cut
    the result short and only one page is held in memory at a time. With a
    limit, no page is larger than the number of entries still wanted, so
    ``--limit 5`` downloads 5 entries and not a whole page.

    Args:
        conn: LDAP connection object
        base_dn: Search base DN
        filter_query: LDAP search filter
        search_scope: Search scope (BASE, LEVEL, SUBTREE)
        attributes: List of attributes to retrieve or ALL_ATTRIBUTES
        page_size: Number of entries per page (at least 1)
        limit: Maximum number of entries to yield (None or 0 for no limit)

    Yields:
        LDAP entry objects
    """
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    limit = limit or None
    entry_count = 0
    cookie = None

    while True:
        size = page_size if limit is None else min(page_size, limit - entry_count)
        conn.search(
            base_dn,
            filter_query,
            search_scope=search_scope,
            attributes=attributes,
            paged_size=size,
            paged_cookie=cookie,
        )

        page = conn.entries
        entries = page if limit is None else page[: limit - entry_count]
        entry_count += len(entries)
        yield from entries

        if limit is not None and entry_count >= limit:
            return

        # The server returns a cookie while more pages are available. A
        # server that repeats the same cookie with an empty page makes no
        # progress; stop instead of looping forever.
        next_cookie = (
            (conn.result or {})
            .get("controls", {})
            .get(PAGED_RESULTS_OID, {})
            .get("value", {})
            .get("cookie")
        )
        if not next_cookie or (not page and next_cookie == cookie):
            return
        cookie = next_cookie


def paged_search(
    conn: Connection,
    base_dn: str,
    filter_query: str,
    search_scope,
    attributes,
    page_size: int,
    limit: Optional[int] = None,
) -> List[Any]:
    """
    Perform a paged search and return all entries as a list.

    See ``iter_paged_search`` for the arguments; this collects what it yields.

    Example:
        >>> entries = paged_search(conn, "dc=example,dc=com", "(objectClass=person)",
        ...                        SUBTREE, ["cn", "mail"], 100, 500)
    """
    return list(
        iter_paged_search(
            conn, base_dn, filter_query, search_scope, attributes, page_size, limit
        )
    )


def compare_entries(
    conn: Connection, dn1: str, dn2: str, attrs: List[str], console: Console
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
        console.print(f"[red]Entry not found: {escape(dn1)}[/red]")
        return
    entry1 = conn.entries[0]

    # Search for second entry
    conn.search(dn2, "(objectClass=*)", search_scope=BASE, attributes=attributes)
    if not conn.entries:
        console.print(f"[red]Entry not found: {escape(dn2)}[/red]")
        return
    entry2 = conn.entries[0]

    # Get all attributes to compare (attribute names are case-insensitive)
    attr_set = set(entry1.entry_attributes).union(entry2.entry_attributes)
    if attrs:
        wanted = {a.lower() for a in attrs}
        attr_set = {a for a in attr_set if a.lower() in wanted}

    table = Table(title="Entry Comparison", box=box.ROUNDED, show_header=True)
    table.add_column("Attribute", style="cyan")
    table.add_column(f"DN 1: {escape(dn1)}", style="green")
    table.add_column(f"DN 2: {escape(dn2)}", style="green")
    table.add_column("Status", style="yellow")

    counts = {"equal": 0, "different": 0, "missing": 0}
    for attr in sorted(attr_set):
        values1 = _sorted_values(entry1, attr)
        values2 = _sorted_values(entry2, attr)

        if values1 is not None and values2 is not None:
            kind, status = (
                ("equal", "✓ Equal")
                if values1 == values2
                else ("different", "≠ Different")
            )
        else:
            kind = "missing"
            status = "! Missing in DN 2" if values2 is None else "! Missing in DN 1"
        counts[kind] += 1
        # Directory data is neither Rich markup nor terminal control codes
        table.add_row(
            safe_text(attr),
            safe_text("\n".join(values1 or [])),
            safe_text("\n".join(values2 or [])),
            status,
        )

    console.print(table)
    console.print("\n[yellow]Comparison Summary:[/yellow]")
    console.print(f"  Equal attributes: {counts['equal']}")
    console.print(f"  Different attributes: {counts['different']}")
    console.print(f"  Missing attributes: {counts['missing']}")


def _sorted_values(entry: Any, attr: str) -> Optional[List[str]]:
    """Return the entry's values for attr as sorted text, or None if absent."""
    if attr not in entry.entry_attributes:
        return None
    return sorted(str(v) for v in entry[attr].values)

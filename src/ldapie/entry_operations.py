#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP entry manipulation functions for LDAPie.
"""

from typing import List

import ldap3
from ldap3 import Connection

from .search import paged_search

DELETE_PAGE_SIZE = 500


def list_subtree(connection: Connection, entry_dn: str) -> List[str]:
    """Return the DNs of entry_dn and all its descendants, deepest first.

    Uses paged results so large subtrees are not cut off by server size limits.
    """
    entries = paged_search(
        connection,
        entry_dn,
        "(objectClass=*)",
        ldap3.SUBTREE,
        [],  # Only need DNs
        DELETE_PAGE_SIZE,
    )
    # A child DN always has more RDNs than its parent, so sorting by the
    # comma count puts every child before its parent.
    return sorted(
        (entry.entry_dn for entry in entries),
        key=lambda dn: dn.count(","),
        reverse=True,
    )


def delete_entry(connection: Connection, entry_dn: str, recursive: bool = False) -> int:
    """Delete an LDAP entry, and with recursive=True all its descendants first.

    Returns:
        The number of deleted entries.

    Raises:
        RuntimeError: If the server refuses a delete without raising itself.
    """
    # An empty subtree listing still tries entry_dn, so the server reports why
    dns = (list_subtree(connection, entry_dn) if recursive else None) or [entry_dn]
    for dn in dns:
        if not connection.delete(dn):
            error_message = (
                connection.result.get("description", "Unknown error")
                if connection.result
                else "Unknown error"
            )
            raise RuntimeError(
                f"LDAP Delete operation failed for {dn}: {error_message}"
            )
    return len(dns)

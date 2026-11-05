#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP entry manipulation functions for LDAPie.
"""

from typing import List, Tuple

import ldap3
from ldap3 import Connection
from ldap3.core.exceptions import LDAPInvalidDnError
from ldap3.utils.dn import parse_dn

from .search import paged_search

DELETE_PAGE_SIZE = 500


def _rdns(dn: str) -> List[Tuple[str, str]]:
    """The DN's (attribute, value) pairs, case-folded for comparison."""
    return [(attr.lower(), value.lower()) for attr, value, _ in parse_dn(dn)]


def _is_within(dn: str, base: List[Tuple[str, str]]) -> bool:
    try:
        rdns = _rdns(dn)
    except LDAPInvalidDnError:
        return False
    return len(rdns) >= len(base) and rdns[len(rdns) - len(base) :] == base


def list_subtree(connection: Connection, entry_dn: str) -> List[str]:
    """Return the DNs of entry_dn and all its descendants, deepest first.

    Uses paged results so large subtrees are not cut off by server size limits.
    Aliases are not followed: an alias in the subtree is deleted as an entry,
    never the entries it points to.

    Raises:
        RuntimeError: If the server returns a DN outside entry_dn's subtree.
    """
    entries = paged_search(
        connection,
        entry_dn,
        "(objectClass=*)",
        ldap3.SUBTREE,
        [],  # Only need DNs
        DELETE_PAGE_SIZE,
        dereference_aliases=ldap3.DEREF_NEVER,
    )
    base = _rdns(entry_dn)
    dns = [entry.entry_dn for entry in entries]
    outside = [dn for dn in dns if not _is_within(dn, base)]
    if outside:
        raise RuntimeError(
            f"Not deleting: the subtree listing of {entry_dn} returned "
            f"{len(outside)} entries outside it, e.g. {outside[0]}"
        )
    # A child DN always has more RDNs than its parent, so sorting by the RDN
    # count puts every child before its parent.
    return sorted(dns, key=lambda dn: len(parse_dn(dn)), reverse=True)


def delete_entry(connection: Connection, entry_dn: str, recursive: bool = False) -> int:
    """Delete an LDAP entry, and with recursive=True all its descendants first.

    Returns:
        The number of deleted entries.

    Raises:
        RuntimeError: If the server refuses a delete without raising itself,
            or a recursive listing returns an entry outside entry_dn.
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP entry manipulation functions (add, modify, delete, rename, compare) for LDAPie.
"""

from typing import Any, Dict

import ldap3  # Keep ldap3 for Connection type hint and LEVEL constant
from ldap3 import Connection  # Explicitly import Connection for type hinting


def add_entry(
    connection: Connection, dn: str, attributes: Dict[str, Any], controls=None
) -> bool:
    """Adds a new LDAP entry."""
    object_classes = attributes.get("objectClass", [])
    attrs_for_add = {k: v for k, v in attributes.items() if k != "objectClass"}

    if connection.add(dn, object_classes, attrs_for_add, controls=controls):
        return True

    error_message = (
        connection.result.get("description", "Unknown error")
        if connection.result
        else "Unknown error"
    )
    raise RuntimeError(f"LDAP Add operation failed for {dn}: {error_message}")


def delete_entry(
    connection: Connection, entry_dn: str, recursive: bool = False, controls=None
) -> bool:
    """Deletes an LDAP entry. Can recursively delete child entries.

    When recursive=True, performs a single SUBTREE search to find all
    descendants, sorts by depth (deepest first), then deletes in order.
    This is O(1) network round trips for discovery instead of O(n).
    """
    if recursive:
        connection.search(
            search_base=entry_dn,
            search_filter="(objectClass=*)",
            search_scope=ldap3.SUBTREE,
            attributes=[],  # Only need DNs
            controls=controls,
        )

        # Sort by depth (deepest first) so children are deleted before parents
        all_dns = sorted(
            [entry.entry_dn for entry in connection.entries],
            key=lambda dn: len(dn.split(",")),
            reverse=True,
        )

        for dn in all_dns:
            if dn == entry_dn:
                continue  # Delete the root entry last
            if not connection.delete(dn, controls=controls):
                error_message = (
                    connection.result.get("description", "Unknown error")
                    if connection.result
                    else "Unknown error"
                )
                raise RuntimeError(
                    f"LDAP Delete operation failed for {dn}: {error_message}"
                )

    if connection.delete(entry_dn, controls=controls):
        return True

    error_message = (
        connection.result.get("description", "Unknown error")
        if connection.result
        else "Unknown error"
    )
    raise RuntimeError(f"LDAP Delete operation failed for {entry_dn}: {error_message}")


def modify_entry(
    connection: Connection, dn: str, modifications: Dict[str, Any], controls=None
) -> bool:
    """Modifies an existing LDAP entry."""
    # The `modifications` dict is expected to be pre-formatted with ldap3.MODIFY_ADD, etc.
    if connection.modify(dn, modifications, controls=controls):
        return True

    error_message = (
        connection.result.get("description", "Unknown error")
        if connection.result
        else "Unknown error"
    )
    raise RuntimeError(f"LDAP Modify operation failed for {dn}: {error_message}")

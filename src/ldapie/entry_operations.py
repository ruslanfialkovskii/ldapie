#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP entry manipulation functions (add, modify, delete, rename, compare) for LDAPie.
"""

from typing import Dict, Any
import ldap3  # Keep ldap3 for Connection type hint and LEVEL constant
from ldap3 import Connection  # Explicitly import Connection for type hinting


def add_entry(connection: Connection, dn: str, attributes: Dict[str, Any], controls=None) -> bool:
    """Adds a new LDAP entry."""
    object_classes = attributes.get("objectClass", [])
    attrs_for_add = {k: v for k, v in attributes.items() if k != "objectClass"}

    if connection.add(dn, object_classes, attrs_for_add, controls=controls):
        return True

    error_message = (connection.result.get('description', 'Unknown error')
                    if connection.result else 'Unknown error')
    raise RuntimeError(f"LDAP Add operation failed for {dn}: {error_message}")


def delete_entry(connection: Connection, entry_dn: str, recursive: bool = False, controls=None) -> bool:
    """Deletes an LDAP entry. Can recursively delete child entries."""
    if recursive:
        connection.search(search_base=entry_dn,
                          search_filter='(objectClass=*)',
                          search_scope=ldap3.LEVEL,  # Direct children
                          attributes=['objectClass'],  # Minimal attributes
                          controls=controls)

        children_dns = [entry.entry_dn for entry in connection.entries]
        for child_dn in children_dns:
            # Recursive call
            delete_entry(connection, child_dn, recursive=True, controls=controls)

    if connection.delete(entry_dn, controls=controls):
        return True

    error_message = (connection.result.get('description', 'Unknown error')
                    if connection.result else 'Unknown error')
    raise RuntimeError(f"LDAP Delete operation failed for {entry_dn}: {error_message}")


def modify_entry(connection: Connection, dn: str, modifications: Dict[str, Any], controls=None) -> bool:
    """Modifies an existing LDAP entry."""
    # The `modifications` dict is expected to be pre-formatted with ldap3.MODIFY_ADD, etc.
    if connection.modify(dn, modifications, controls=controls):
        return True

    error_message = (connection.result.get('description', 'Unknown error')
                    if connection.result else 'Unknown error')
    raise RuntimeError(f"LDAP Modify operation failed for {dn}: {error_message}")



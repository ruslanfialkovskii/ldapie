#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP entry manipulation functions (add, modify, delete, rename, compare) for LDAPie.
"""

from typing import Dict, Any, Optional
from unittest.mock import MagicMock  # For schema simulation
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


def rename_entry(connection: Connection, current_dn: str, new_rdn: str,
                _new_superior_dn: Optional[str] = None, _delete_old_rdn: bool = True,
                _controls=None) -> bool:
    """Renames an LDAP entry (DN modification). Placeholder."""
    _ = connection  # Mark as unused for linters in placeholder
    msg = f"rename_entry for {current_dn} to {new_rdn} is a placeholder and not fully implemented."
    raise NotImplementedError(msg)


def compare_entry(connection: Connection, dn: str, attribute: str, _value: str, _controls=None) -> bool:
    """Compares an attribute of an entry with a given value. Placeholder."""
    _ = connection  # Mark as unused for linters in placeholder
    msg = f"compare_entry for {dn} on attribute {attribute} is a placeholder and not fully implemented."
    raise NotImplementedError(msg)


def get_schema_info(_connection: Connection, schema_type: str, name: Optional[str] = None) -> Any:
    """
    Retrieves schema information (object classes or attribute types).
    Placeholder implementation using mocked data. Connection argument is for API consistency.
    """
    # This placeholder simulates schema access for testing purposes.
    # A real implementation would use `_connection.server.schema`.
    mock_schema_objectclasses = {
        "person": MagicMock(must_contain=['cn', 'sn'], may_contain=['mail', 'telephoneNumber']),
        "groupOfNames": MagicMock(must_contain=['member', 'cn'], may_contain=['description'])
    }
    mock_schema_attributetypes = {
        "cn": MagicMock(syntax='1.3.6.1.4.1.1466.115.121.1.15', equality='caseIgnoreMatch'),
        "sn": MagicMock(syntax='1.3.6.1.4.1.1466.115.121.1.15', equality='caseIgnoreMatch'),
        "mail": MagicMock(syntax='1.3.6.1.4.1.1466.115.121.1.26', equality='caseIgnoreIA5Match')
    }

    if schema_type == "objectclasses":
        if name:
            data = mock_schema_objectclasses.get(name)
            if data is None:
                raise ValueError(f"Mock schema: Object class '{name}' not found.")
            return data
        return list(mock_schema_objectclasses.keys())

    if schema_type == "objectclass" and name:  # Alias for specific object class
        data = mock_schema_objectclasses.get(name)
        if data is None:
            raise ValueError(f"Mock schema: Object class '{name}' not found.")
        return data

    if schema_type == "attributetypes":
        if name:
            data = mock_schema_attributetypes.get(name)
            if data is None:
                raise ValueError(f"Mock schema: Attribute type '{name}' not found.")
            return data
        return list(mock_schema_attributetypes.keys())

    if schema_type == "attributetype" and name:  # Alias for specific attribute type
        data = mock_schema_attributetypes.get(name)
        if data is None:
            raise ValueError(f"Mock schema: Attribute type '{name}' not found.")
        return data

    # Specific type requested but no name given
    if schema_type in ["objectclass", "attributetype"] and not name:
        raise ValueError(f"Schema type '{schema_type}' requires a name to be specified.")

    # Catches invalid schema_type values or other unsupported combinations
    msg = f"Invalid or unsupported schema_type/name combination: type='{schema_type}', name='{name}'."
    raise ValueError(msg)

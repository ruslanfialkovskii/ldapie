#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General utility functions for LDAPie.
"""

# General purpose utilities for LDAPie

import ldap3 # For parse_modification_attributes
from ldap3 import Connection # Explicitly import Connection for type hinting
from typing import Dict, Any, Optional, List

# Re-export commonly used functions from other modules to maintain compatibility
# with code that imports from ldapie_utils
try:
    # Import the functions but don't actually use them here - just re-export
    from .output import output_json, output_ldif, output_csv, build_tree, output_tree, output_rich
    from .schema import output_server_info_rich, output_server_info_json, show_schema, get_schema_info
    from .entry_operations import delete_entry, add_entry, modify_entry
    from .search import compare_entries, compare_entry
    
    __all__ = [
        'output_json', 'output_ldif', 'output_csv', 'build_tree', 'output_tree', 'output_rich',
        'output_server_info_rich', 'output_server_info_json', 'show_schema', 'get_schema_info',
        'delete_entry', 'add_entry', 'modify_entry', 'compare_entries', 'compare_entry',
        # Utilities defined in this file
        'parse_ldap_uri', 'validate_search_filter', 'parse_attributes', 'create_connection',
        'safe_get_password', 'handle_error_response', 'parse_modification_attributes', 'format_output_filename'
    ]
except ImportError:
    # This will be handled by the main script's import error handling
    pass

def parse_ldap_uri(uri: str):
    """Parses an LDAP URI."""
    # Placeholder implementation
    raise NotImplementedError("parse_ldap_uri is not yet implemented")

def validate_search_filter(filter_str: str):
    """Validates an LDAP search filter."""
    # Placeholder implementation
    # For now, assume all filters are valid
    _ = filter_str # Mark as used
    return True

def parse_attributes(attributes_str: str | None):
    """Parses a string of comma-separated attributes."""
    if not attributes_str:
        return []
    return [attr.strip() for attr in attributes_str.split(',')]

def create_connection(ldap_uri: str, bind_dn: str | None = None, password: str | None = None, sasl_mechanism: str | None = None):
    """Creates an LDAP connection."""
    # Placeholder implementation
    raise NotImplementedError("create_connection is not yet implemented")

def safe_get_password(prompt: str = "Password: "):
    """Safely gets a password from the user."""
    # Placeholder implementation
    import getpass
    return getpass.getpass(prompt)

def handle_error_response(response, msg: str = "LDAP operation failed"):
    """Handles an error response from an LDAP operation."""
    # Placeholder implementation
    # This function would typically raise an exception or log an error
    print(f"Error: {msg} - {response}")
    raise RuntimeError(f"{msg} - {response}")

def parse_modification_attributes(add_attrs: list[str] | None, replace_attrs: list[str] | None, delete_attrs: list[str] | None) -> dict:
    """Parses modification attributes from command-line arguments."""
    mods = {}
    if add_attrs:
        for attr_val in add_attrs:
            parts = attr_val.split('=', 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ''
            # ldap3 expects list of values for an attribute modification
            current_mod = mods.get(attr, {'operation': ldap3.MODIFY_ADD, 'value': []})
            current_mod['value'].append(val)
            mods[attr] = current_mod
    if replace_attrs:
        for attr_val in replace_attrs:
            parts = attr_val.split('=', 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ''
            mods[attr] = {'operation': ldap3.MODIFY_REPLACE, 'value': [val]}
    if delete_attrs:
        for attr_val in delete_attrs: # Assuming delete_attrs might contain attr=val or just attr
            attr = attr_val.split('=', 1)[0]
            # For delete, value can be specific or empty to delete all values
            # Placeholder: simple delete of attribute itself or specific values if provided
            if '=' in attr_val:
                _, val = attr_val.split('=', 1)
                mods[attr] = {'operation': ldap3.MODIFY_DELETE, 'value': [val]}
            else:
                mods[attr] = {'operation': ldap3.MODIFY_DELETE, 'value': []}
    return mods

def format_output_filename(basename: str, extension: str) -> str:
    """Formats an output filename, ensuring correct extension."""
    if basename.endswith(f".{extension}"):
        return basename
    # if basename contains a dot not at the end, and it's not the target extension, append target extension
    if '.' in basename and not basename.endswith('.'):
        return f"{basename}.{extension}"
    # if no extension or ends with a dot, just append
    return f"{basename}.{extension}"

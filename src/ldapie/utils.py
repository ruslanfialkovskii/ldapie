#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General utility functions for LDAPie.
"""

# This file can be used for any future general-purpose utilities.

import ldap3 # For parse_modification_attributes

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

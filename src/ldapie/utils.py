#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General utility functions for LDAPie.
"""

# General purpose utilities for LDAPie

from typing import List

import ldap3  # For parse_modification_attributes
from ldap3.utils.dn import parse_dn

# Re-export commonly used functions from other modules to maintain compatibility
# with code that imports from ldapie_utils
try:
    # Import the functions but don't actually use them here - just re-export
    from .entry_operations import add_entry, delete_entry, modify_entry
    from .output import (
        build_tree,
        output_csv,
        output_json,
        output_ldif,
        output_rich,
        output_tree,
    )
    from .schema import (
        get_schema_info,
        output_server_info_json,
        output_server_info_rich,
        show_schema,
    )
    from .search import compare_entries, compare_entry

    __all__ = [
        "output_json",
        "output_ldif",
        "output_csv",
        "build_tree",
        "output_tree",
        "output_rich",
        "output_server_info_rich",
        "output_server_info_json",
        "show_schema",
        "get_schema_info",
        "delete_entry",
        "add_entry",
        "modify_entry",
        "compare_entries",
        "compare_entry",
        # Utilities defined in this file
        "validate_search_filter",
        "validate_dn",
        "parse_attributes",
        "safe_get_password",
        "handle_error_response",
        "parse_modification_attributes",
        "format_output_filename",
    ]
except ImportError:
    # This will be handled by the main script's import error handling
    pass


def validate_search_filter(filter_str: str) -> bool:
    """Validates an LDAP search filter per RFC 4515 structure.

    Checks balanced parentheses, enclosing parens, valid operators,
    and compound operators (&, |, !).

    Raises:
        ValueError: If the filter is structurally invalid.

    Returns:
        True if the filter is valid.
    """
    if not filter_str:
        raise ValueError("Filter cannot be empty")

    stripped = filter_str.strip()
    if not stripped.startswith("(") or not stripped.endswith(")"):
        raise ValueError("Filter must be enclosed in parentheses")

    # Check balanced parentheses
    depth = 0
    for ch in stripped:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            raise ValueError("Unbalanced parentheses: unexpected ')'")
    if depth != 0:
        raise ValueError("Unbalanced parentheses: missing ')'")

    # Validate inner content recursively
    _validate_filter_node(stripped)

    return True


def _validate_filter_node(node: str) -> None:
    """Recursively validate a single filter node."""
    # Strip outer parens
    if node.startswith("(") and node.endswith(")"):
        inner = node[1:-1]
    else:
        raise ValueError(f"Filter component must be enclosed in parentheses: {node}")

    if not inner:
        raise ValueError("Empty filter component '()'")

    # Compound operators: &, |, !
    if inner[0] in ("&", "|"):
        # Must have at least one sub-filter
        sub_filters = _extract_sub_filters(inner[1:])
        if not sub_filters:
            raise ValueError(
                f"Compound operator '{inner[0]}' requires at least one sub-filter"
            )
        for sf in sub_filters:
            _validate_filter_node(sf)
        return

    if inner[0] == "!":
        sub_filters = _extract_sub_filters(inner[1:])
        if len(sub_filters) != 1:
            raise ValueError("NOT operator '!' requires exactly one sub-filter")
        _validate_filter_node(sub_filters[0])
        return

    # Simple filter: must contain an operator (=, >=, <=, ~=)
    if inner.startswith("("):
        # Nested parens without operator — could be a sub-filter group
        sub_filters = _extract_sub_filters(inner)
        for sf in sub_filters:
            _validate_filter_node(sf)
        return

    # Check for valid comparison operators
    if ">=" in inner or "<=" in inner or "~=" in inner or "=" in inner:
        return

    raise ValueError(f"Invalid filter item (missing operator): ({inner})")


def _extract_sub_filters(s: str) -> List[str]:
    """Extract parenthesized sub-filter strings from a compound filter body."""
    filters: List[str] = []
    s = s.strip()
    i = 0
    while i < len(s):
        if s[i] == "(":
            depth = 0
            start = i
            while i < len(s):
                if s[i] == "(":
                    depth += 1
                elif s[i] == ")":
                    depth -= 1
                    if depth == 0:
                        filters.append(s[start : i + 1])
                        i += 1
                        break
                i += 1
            else:
                raise ValueError("Unbalanced parentheses in sub-filter")
        else:
            i += 1
    return filters


def validate_dn(dn: str) -> bool:
    """Validates a Distinguished Name using ldap3's parse_dn.

    Raises:
        ValueError: If the DN is malformed.

    Returns:
        True if the DN is valid.
    """
    if not dn or not dn.strip():
        raise ValueError("DN cannot be empty")
    try:
        parse_dn(dn)
    except Exception as e:
        raise ValueError(f"Invalid DN '{dn}': {e}") from e
    return True


def parse_attributes(attributes_str: str | None):
    """Parses a string of comma-separated attributes."""
    if not attributes_str:
        return []
    return [attr.strip() for attr in attributes_str.split(",")]


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


def parse_modification_attributes(
    add_attrs: list[str] | None,
    replace_attrs: list[str] | None,
    delete_attrs: list[str] | None,
) -> dict:
    """Parses modification attributes from command-line arguments."""
    mods = {}
    if add_attrs:
        for attr_val in add_attrs:
            parts = attr_val.split("=", 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ""
            # ldap3 expects list of values for an attribute modification
            current_mod = mods.get(attr, {"operation": ldap3.MODIFY_ADD, "value": []})
            current_mod["value"].append(val)
            mods[attr] = current_mod
    if replace_attrs:
        for attr_val in replace_attrs:
            parts = attr_val.split("=", 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ""
            mods[attr] = {"operation": ldap3.MODIFY_REPLACE, "value": [val]}
    if delete_attrs:
        for (
            attr_val
        ) in delete_attrs:  # Assuming delete_attrs might contain attr=val or just attr
            attr = attr_val.split("=", 1)[0]
            # For delete, value can be specific or empty to delete all values
            # Placeholder: simple delete of attribute itself or specific values if provided
            if "=" in attr_val:
                _, val = attr_val.split("=", 1)
                mods[attr] = {"operation": ldap3.MODIFY_DELETE, "value": [val]}
            else:
                mods[attr] = {"operation": ldap3.MODIFY_DELETE, "value": []}
    return mods


def format_output_filename(basename: str, extension: str) -> str:
    """Formats an output filename, ensuring correct extension."""
    if basename.endswith(f".{extension}"):
        return basename
    # if basename contains a dot not at the end, and it's not the target extension, append target extension
    if "." in basename and not basename.endswith("."):
        return f"{basename}.{extension}"
    # if no extension or ends with a dot, just append
    return f"{basename}.{extension}"

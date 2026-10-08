#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General utility functions for LDAPie: input validation and argument parsing.
"""

from typing import Dict, Iterable, List, Optional, Tuple

import ldap3
from ldap3.utils.dn import parse_dn


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


def _split_assignment(item: str) -> Tuple[str, Optional[str]]:
    """Split 'name=value' into (name, value); a bare 'name' gives (name, None)."""
    name, sep, value = item.partition("=")
    name = name.strip()
    if not name:
        raise ValueError(f"Invalid attribute specification: '{item}'. Use name=value")
    return name, (value if sep else None)


def parse_modification_attributes(
    add_attrs: Optional[Iterable[str]],
    replace_attrs: Optional[Iterable[str]],
    delete_attrs: Optional[Iterable[str]],
) -> Dict[str, List[Tuple[str, List[str]]]]:
    """Build an ldap3 modify changes dict from --add/--replace/--delete values.

    Returns {attribute: [(operation, [values]), ...]}, the format
    ldap3.Connection.modify expects. Repeated options for the same
    attribute and operation collect their values into one change, so
    --add mail=a --add mail=b adds both values. A bare --replace name or
    --delete name removes every value of the attribute; --delete name=value
    removes one value.

    Raises:
        ValueError: If an --add item has no =value part.
    """
    changes: Dict[str, List[Tuple[str, List[str]]]] = {}

    def add_change(name: str, operation: str, value: Optional[str]) -> None:
        operations = changes.setdefault(name, [])
        for op, values in operations:
            if op == operation:
                if value is not None:
                    values.append(value)
                return
        operations.append((operation, [] if value is None else [value]))

    for item in add_attrs or ():
        name, value = _split_assignment(item)
        if value is None:
            raise ValueError(f"Invalid --add value: '{item}'. Use name=value")
        add_change(name, ldap3.MODIFY_ADD, value)
    for item in replace_attrs or ():
        name, value = _split_assignment(item)
        add_change(name, ldap3.MODIFY_REPLACE, value)
    for item in delete_attrs or ():
        name, value = _split_assignment(item)
        add_change(name, ldap3.MODIFY_DELETE, value)
    return changes

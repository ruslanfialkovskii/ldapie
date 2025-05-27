#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsing utilities for LDAPie.

This module contains functions for parsing LDAP URIs, filters, attributes,
and other LDAP-related data structures.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE
from urllib.parse import urlparse


def parse_ldap_uri(uri: str) -> Dict[str, Any]:
    """
    Parse an LDAP URI into its components.
    
    Args:
        uri: LDAP URI string
        
    Returns:
        Dictionary containing parsed components
    """
    parsed = urlparse(uri)
    return {
        'scheme': parsed.scheme,
        'hostname': parsed.hostname,
        'port': parsed.port,
        'path': parsed.path,
        'params': parsed.params,
        'query': parsed.query,
        'fragment': parsed.fragment
    }


def validate_search_filter(filter_str: str) -> bool:
    """
    Validate an LDAP search filter.
    
    Args:
        filter_str: LDAP filter string
        
    Returns:
        True if valid, False otherwise
    """
    if not filter_str:
        return False
    
    # Basic validation - check for balanced parentheses
    open_count = filter_str.count('(')
    close_count = filter_str.count(')')
    
    return open_count == close_count and open_count > 0


def parse_attributes(attr_list: List[str]) -> List[str]:
    """
    Parse and validate attribute list.
    
    Args:
        attr_list: List of attribute names
        
    Returns:
        Cleaned list of valid attribute names
    """
    if not attr_list:
        return []
    
    cleaned = []
    for attr in attr_list:
        # Remove whitespace and validate
        attr = attr.strip()
        if attr and re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', attr):
            cleaned.append(attr)
    
    return cleaned


def parse_modification_attributes(add: List[str], replace: List[str], delete: List[str]) -> Dict[str, Any]:
    """
    Parse modification attributes for LDAP modify operations.
    
    Args:
        add: List of attributes to add
        replace: List of attributes to replace
        delete: List of attributes to delete
        
    Returns:
        Dictionary of modifications for ldap3
    """
    changes = {}
    
    # Parse add operations
    for attr in add:
        if '=' in attr:
            name, value = attr.split('=', 1)
            if name in changes:
                if isinstance(changes[name], list):
                    changes[name].append((MODIFY_ADD, [value]))
                else:
                    changes[name] = [(MODIFY_ADD, [changes[name][0][1][0]]), (MODIFY_ADD, [value])]
            else:
                changes[name] = [(MODIFY_ADD, [value])]
    
    # Parse replace operations
    for attr in replace:
        if '=' in attr:
            name, value = attr.split('=', 1)
            changes[name] = [(MODIFY_REPLACE, [value])]
    
    # Parse delete operations
    for attr in delete:
        if '=' in attr:
            name, value = attr.split('=', 1)
            changes[name] = [(MODIFY_DELETE, [value])]
        else:
            # Delete entire attribute
            changes[attr] = [(MODIFY_DELETE, [])]
    
    return changes


def parse_dn_components(dn: str) -> List[Tuple[str, str]]:
    """
    Parse DN into its component parts.
    
    Args:
        dn: Distinguished Name string
        
    Returns:
        List of (attribute, value) tuples
    """
    components = []
    if not dn:
        return components
    
    # Simple DN parsing - split by comma and then by =
    parts = dn.split(',')
    for part in parts:
        part = part.strip()
        if '=' in part:
            attr, value = part.split('=', 1)
            components.append((attr.strip(), value.strip()))
    
    return components


def normalize_dn(dn: str) -> str:
    """
    Normalize a DN string by removing extra whitespace.
    
    Args:
        dn: Distinguished Name string
        
    Returns:
        Normalized DN string
    """
    if not dn:
        return dn
    
    components = parse_dn_components(dn)
    return ','.join(f"{attr}={value}" for attr, value in components)

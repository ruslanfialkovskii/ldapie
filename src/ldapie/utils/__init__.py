"""
Utility functions and helpers for LDAPie.

This package contains general utility functions, connection helpers,
and other supporting functionality.
"""

from .connection import create_connection, handle_connection_error
from .parsers import (
    parse_ldap_uri, validate_search_filter, parse_attributes,
    parse_modification_attributes, parse_dn_components, normalize_dn
)
from .helpers import (
    safe_get_password, handle_error_response, format_output_filename,
    validate_dn, sanitize_filename, get_config_dir, ensure_config_dir
)

__all__ = [
    'create_connection', 'handle_connection_error',
    'parse_ldap_uri', 'validate_search_filter', 'parse_attributes',
    'parse_modification_attributes', 'parse_dn_components', 'normalize_dn',
    'safe_get_password', 'handle_error_response', 'format_output_filename',
    'validate_dn', 'sanitize_filename', 'get_config_dir', 'ensure_config_dir'
]

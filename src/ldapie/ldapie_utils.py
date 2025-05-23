#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[DEPRECATED] Utility functions for LDAPie - A modern LDAP client CLI tool

This module is deprecated. Instead, use the specific modules:
- utils.py for general utilities
- output.py for output formatting
- search.py for search operations
- schema.py for schema operations
- entry_operations.py for LDAP entry operations
- interactive.py for interactive session

This module now serves as a compatibility layer for older code.
"""

import warnings

warnings.warn(
    "ldapie_utils is deprecated. Import directly from utils, output, search, schema, entry_operations modules instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import functions from the new modules to maintain compatibility for a short while
# Or, update all imports in ldapie.py to point to the new locations directly.
# For now, let's re-export them here.

from .search import paged_search, compare_entries, compare_entry
from .output import (
    output_json, 
    output_ldif, 
    output_csv, 
    build_tree, 
    output_tree, 
    output_rich, 
    format_output_filename
)
from .schema import (
    output_server_info_rich, 
    output_server_info_json, 
    show_schema, 
    get_schema_info, 
    format_schema_output
)
from .entry_operations import (
    parse_modification_attributes, 
    add_entry, 
    delete_entry, 
    modify_entry
)
# delete_recursive is not a separate function - delete_entry has a recursive parameter
from .interactive import start_interactive_session

# Any functions that were truly "general utilities" and didn't fit elsewhere
# would remain in this file or be moved to the new `utils.py`.
# Based on the provided code, all functions seem to have found a new home.

# The original content of ldapie_utils.py is now distributed among:
# - search.py
# - output.py
# - schema.py
# - entry_operations.py
# - interactive.py
# - utils.py (if any general utilities were left)

# This file can be deprecated or removed once all imports are updated.
# For now, it serves as a compatibility layer.

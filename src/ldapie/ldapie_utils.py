#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for LDAPie - A modern LDAP client CLI tool

This module provides utility functions for LDAP operations and formatting results.
It works with ldap3 library for LDAP operations and rich library for 
terminal output formatting.

Functions are categorized into several groups:
- Search and query functions
- Output formatting functions (JSON, LDIF, CSV, etc.)
- LDAP entry manipulation functions (add, modify, delete, rename)
- Server information and schema retrieval
- Helper utilities for DN, filters, and attributes
"""

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
    delete_recursive, 
    parse_modification_attributes, 
    add_entry, 
    delete_entry, 
    modify_entry
)
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

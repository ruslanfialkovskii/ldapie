"""
User interface and output formatting for LDAPie.

This package contains modules for output formatting, Rich console
integration, and other UI-related functionality.
"""

from .output import (
    output_json, output_ldif, output_csv, build_tree, 
    output_tree, output_rich, format_output_filename
)
from .rich_formatter import add_rich_help_option

__all__ = [
    'output_json', 'output_ldif', 'output_csv', 'build_tree',
    'output_tree', 'output_rich', 'format_output_filename',
    'add_rich_help_option'
]

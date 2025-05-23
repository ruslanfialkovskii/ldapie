"""
LDAPie - A modern LDAP client CLI tool

This package provides a user-friendly interface for interacting with LDAP servers.
It combines the simplicity of HTTPie's design with powerful LDAP functionality.

This is the main package that exports all the necessary modules and defines the version.
"""

__version__ = "0.1.4"

# Export modules
from . import help_context, help_overlay, tab_completion, shell_enhancements

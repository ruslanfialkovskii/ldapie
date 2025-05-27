"""
LDAPie - A modern LDAP client CLI tool

This package provides a user-friendly interface for interacting with LDAP servers.
It combines the simplicity of HTTPie's design with powerful LDAP functionality.

This is the main package that exports all the necessary modules and defines the version.
"""

__version__ = "0.1.4"

# Export main CLI interface
from .core import cli

# Export subpackages
from . import core, operations, interactive, ui, utils

__all__ = ['cli', 'core', 'operations', 'interactive', 'ui', 'utils', '__version__']

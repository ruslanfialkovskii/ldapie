"""
Interactive shell components for LDAPie.

This package contains modules for the interactive shell mode,
including help systems, tab completion, and shell enhancements.
"""

from .shell import LDAPShell, start_interactive_session
from .help_context import HelpContext
from .help_overlay import show_help_overlay
from .tab_completion import TabCompletion, QueryHistory
from .shell_enhancements import enhance_shell

__all__ = [
    'LDAPShell', 'start_interactive_session',
    'HelpContext', 'show_help_overlay',
    'TabCompletion', 'QueryHistory', 'enhance_shell'
]

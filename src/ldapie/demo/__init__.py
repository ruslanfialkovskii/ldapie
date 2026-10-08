"""
Automated LDAPie demo against an in-memory mock LDAP server.

Run it with ``ldapie --demo`` or ``python -m ldapie.demo``.
"""

from .tour import run_demo

__all__ = ["run_demo"]

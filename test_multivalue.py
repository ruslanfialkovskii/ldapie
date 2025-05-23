#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for multi-valued attribute display in LDAPie.
"""

import os
import sys
from rich.console import Console

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)

# Add the src directory to the Python path
src_dir = os.path.join(parent_dir, 'src')
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

# Try to import the output module
try:
    from ldapie.output import output_rich
except ImportError:
    try:
        from src.ldapie.output import output_rich 
    except ImportError:
        print("Error: Could not import output_rich function.")
        sys.exit(1)

# Create a mock LDAP entry with multi-valued attributes to test rendering
class MockLdapEntry:
    def __init__(self, dn, attributes):
        self.entry_dn = dn
        self.entry_attributes = list(attributes.keys())
        self._attributes = attributes

    def __getitem__(self, key):
        class AttrValues:
            def __init__(self, values):
                self.values = values
                self.value = values[0] if values else None
        return AttrValues(self._attributes.get(key, []))

def main():
    console = Console()
    console.print("[bold]Testing multi-valued attribute display in LDAPie[/bold]")
    
    # Create a mock entry with a multi-valued memberOf attribute
    entry = MockLdapEntry(
        "cn=testUser,ou=People,dc=example,dc=com",
        {
            "objectClass": ["top", "person", "inetOrgPerson"],
            "cn": ["testUser"],
            "sn": ["User"],
            "uid": ["testuser"],
            "mail": ["testuser@example.com"],
            "memberOf": [
                "cn=Developers,ou=Groups,dc=example,dc=com",
                "cn=Admins,ou=Groups,dc=example,dc=com",
                "cn=Users,ou=Groups,dc=example,dc=com"
            ]
        }
    )
    
    # Test the output with our updated fix
    console.print("\n[bold cyan]Output of entry with multi-valued memberOf attribute:[/bold cyan]")
    output_rich([entry], console)

if __name__ == "__main__":
    main()

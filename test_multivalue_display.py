#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for multi-valued attribute display in LDAPie.
This script directly tests the output formatting for multi-valued attributes.
"""

import os
import sys
from rich.console import Console

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Directly import the output module to test it
from ldapie.output import output_rich

# Create a mock LDAP entry with multi-valued attributes to test rendering
class MockAttribute:
    def __init__(self, values):
        self.values = values
        self.value = values[0] if values else None

class MockLdapEntry:
    def __init__(self, dn, attributes):
        self.entry_dn = dn
        self.entry_attributes = list(attributes.keys())
        self._attributes = {k: MockAttribute(v) for k, v in attributes.items()}

    def __getitem__(self, key):
        return self._attributes.get(key, MockAttribute([]))

def main():
    console = Console()
    print("Starting test...")  # Plain print to ensure output is visible
    console.print("[bold]Testing multi-valued attribute display in LDAPie[/bold]")
    
    # Create a mock entry with a multi-valued memberOf attribute
    print("Creating mock LDAP entry...")
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
    
    # Print member values to debug
    print("memberOf attribute values:")
    for val in entry["memberOf"].values:
        print(f"  - {val}")
    
    # Test the output with our updated fix
    print("\nRendering output with Rich...")
    console.print("\n[bold cyan]Output of entry with multi-valued memberOf attribute:[/bold cyan]")
    output_rich([entry], console)
    print("\nTest completed.")

if __name__ == "__main__":
    main()

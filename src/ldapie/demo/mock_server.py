#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock LDAP server for testing and demo purposes.
"""

from ldap3 import MOCK_SYNC, OFFLINE_SLAPD_2_4, Connection, Server


class MockLdapServer:
    """Mock LDAP server for testing and demo purposes"""

    def __init__(self):
        """Initialize the mock LDAP server with sample data"""
        # Offline OpenLDAP schema, so schema browsing works in the demo
        self.server = Server("ldap://mock_server", get_info=OFFLINE_SLAPD_2_4)
        self.connection = Connection(
            self.server,
            user="cn=admin,dc=example,dc=com",
            password="admin",
            client_strategy=MOCK_SYNC,
        )
        self.connection.bind()

        # Add mock server info for testing
        self._add_mock_server_info()

        # Add mock entries
        self._add_mock_entries()

    def _add_mock_server_info(self):
        """Describe the mock server (vendor, controls, naming contexts)"""

        # Create a simple object to simulate server info
        class MockServerInfo:
            def __init__(self):
                self.vendor_name = "Mock LDAP Server"
                self.vendor_version = "0.0.1"
                self.supported_ldap_versions = [3]
                self.supported_controls = [
                    "1.2.840.113556.1.4.319",  # Simple Paged Results
                    "1.2.840.113556.1.4.473",  # Sort Control
                ]
                self.supported_extensions = [
                    "1.3.6.1.4.1.4203.1.11.1",  # Password Modify
                    "1.3.6.1.4.1.1466.20037",  # Start TLS
                ]
                self.naming_contexts = ["dc=example,dc=com"]

        # Replace the offline DSA info with demo-specific details
        self.server._dsa_info = MockServerInfo()  # ldap3 has no setter for this

    def get_connection(self):
        """Return the mock LDAP connection"""
        return self.connection

    def _add_mock_entries(self):
        """Add mock entries to the LDAP server"""
        # Base organization
        self.connection.add(
            "dc=example,dc=com",
            attributes={
                "objectClass": ["dcObject", "organization"],
                "dc": "example",
                "o": "Example Organization",
            },
        )

        # Organizational units
        self.connection.add(
            "ou=people,dc=example,dc=com",
            attributes={"objectClass": ["organizationalUnit"], "ou": "people"},
        )

        self.connection.add(
            "ou=groups,dc=example,dc=com",
            attributes={"objectClass": ["organizationalUnit"], "ou": "groups"},
        )

        # People entries
        self.connection.add(
            "uid=jdoe,ou=people,dc=example,dc=com",
            attributes={
                "objectClass": ["inetOrgPerson"],
                "uid": "jdoe",
                "cn": "John Doe",
                "sn": "Doe",
                "givenName": "John",
                "mail": "john.doe@example.com",
                "userPassword": "password",
                "title": "Developer",
                "telephoneNumber": "+1 555 123 4567",
            },
        )

        self.connection.add(
            "uid=jsmith,ou=people,dc=example,dc=com",
            attributes={
                "objectClass": ["inetOrgPerson"],
                "uid": "jsmith",
                "cn": "Jane Smith",
                "sn": "Smith",
                "givenName": "Jane",
                "mail": "jane.smith@example.com",
                "userPassword": "password",
                "title": "Project Manager",
                "telephoneNumber": "+1 555 234 5678",
            },
        )

        self.connection.add(
            "uid=admin,ou=people,dc=example,dc=com",
            attributes={
                "objectClass": ["inetOrgPerson"],
                "uid": "admin",
                "cn": "LDAP Admin",
                "sn": "Admin",
                "givenName": "LDAP",
                "mail": "admin@example.com",
                "userPassword": "admin_password",
                "title": "System Administrator",
                "telephoneNumber": "+1 555 987 6543",
            },
        )

        self.connection.add(
            "uid=mwhite,ou=people,dc=example,dc=com",
            attributes={
                "objectClass": ["inetOrgPerson"],
                "uid": "mwhite",
                "cn": "Mike White",
                "sn": "White",
                "givenName": "Mike",
                "mail": "mike.white@example.com",
                "userPassword": "password",
                "title": "Designer",
                "telephoneNumber": "+1 555 345 6789",
            },
        )

        # Group entries
        self.connection.add(
            "cn=admins,ou=groups,dc=example,dc=com",
            attributes={
                "objectClass": ["groupOfNames"],
                "cn": "admins",
                "description": "Administrator group",
                "member": ["uid=admin,ou=people,dc=example,dc=com"],
            },
        )

        self.connection.add(
            "cn=developers,ou=groups,dc=example,dc=com",
            attributes={
                "objectClass": ["groupOfNames"],
                "cn": "developers",
                "description": "Developer group",
                "member": [
                    "uid=jdoe,ou=people,dc=example,dc=com",
                    "uid=jsmith,ou=people,dc=example,dc=com",
                ],
            },
        )

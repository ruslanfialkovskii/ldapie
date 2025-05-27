#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for core LDAPie functionality.
"""

import pytest
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from ldapie.core import cli, LdapConfig


class TestLdapConfig:
    """Test the LdapConfig class."""
    
    def test_config_creation(self):
        """Test creating an LdapConfig instance."""
        config = LdapConfig(
            host="ldap.example.com",
            username="cn=admin,dc=example,dc=com",
            password="secret",
            use_ssl=False,
            port=389
        )
        
        assert config.host == "ldap.example.com"
        assert config.username == "cn=admin,dc=example,dc=com"
        assert config.password == "secret"
        assert config.use_ssl is False
        assert config.port == 389
    
    def test_config_ssl_port_default(self):
        """Test that SSL defaults to port 636."""
        config = LdapConfig(
            host="ldap.example.com",
            use_ssl=True
        )
        
        assert config.port == 636
    
    def test_config_non_ssl_port_default(self):
        """Test that non-SSL defaults to port 389."""
        config = LdapConfig(
            host="ldap.example.com",
            use_ssl=False
        )
        
        assert config.port == 389


class TestCLI:
    """Test the CLI interface."""
    
    def test_cli_import(self):
        """Test that the CLI can be imported."""
        assert cli is not None
        assert callable(cli)


if __name__ == "__main__":
    pytest.main([__file__])

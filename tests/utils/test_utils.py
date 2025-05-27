#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for utility functions.
"""

import pytest
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from ldapie.utils.parsers import (
    parse_ldap_uri, validate_search_filter, parse_attributes,
    parse_modification_attributes, parse_dn_components, normalize_dn
)
from ldapie.utils.helpers import (
    safe_get_password, handle_error_response, format_output_filename,
    validate_dn, sanitize_filename
)
from ldapie.utils.connection import create_connection


class TestParsers:
    """Test parsing utility functions."""
    
    def test_validate_search_filter(self):
        """Test LDAP filter validation."""
        assert validate_search_filter("(objectClass=person)") is True
        assert validate_search_filter("(cn=test)") is True
        assert validate_search_filter("") is False
        assert validate_search_filter("invalid") is False
    
    def test_parse_attributes(self):
        """Test attribute parsing."""
        attrs = parse_attributes(["cn", "mail", "uid"])
        assert "cn" in attrs
        assert "mail" in attrs
        assert "uid" in attrs
    
    def test_parse_dn_components(self):
        """Test DN component parsing."""
        dn = "cn=test,ou=people,dc=example,dc=com"
        components = parse_dn_components(dn)
        assert len(components) == 4
        assert components[0] == ("cn", "test")
        assert components[1] == ("ou", "people")
    
    def test_normalize_dn(self):
        """Test DN normalization."""
        dn = " cn = test , ou = people , dc = example , dc = com "
        normalized = normalize_dn(dn)
        assert normalized == "cn=test,ou=people,dc=example,dc=com"


class TestHelpers:
    """Test helper utility functions."""
    
    def test_format_output_filename(self):
        """Test output filename formatting."""
        assert format_output_filename("test", "json") == "test.json"
        assert format_output_filename("test.txt", "json") == "test.json"
        assert format_output_filename("test.json", "json") == "test.json"
    
    def test_validate_dn(self):
        """Test DN validation."""
        assert validate_dn("cn=test,dc=example,dc=com") is True
        assert validate_dn("") is False
        assert validate_dn("invalid") is False
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("test<file>") == "test_file_"
        assert sanitize_filename("test:file") == "test_file"
        assert sanitize_filename("") == "output"


class TestConnection:
    """Test connection utilities."""
    
    def test_create_connection_import(self):
        """Test that create_connection can be imported."""
        assert create_connection is not None
        assert callable(create_connection)


if __name__ == "__main__":
    pytest.main([__file__])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for LDAP operations functionality.
"""

import pytest
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from ldapie.operations.search import paged_search, compare_entries
from ldapie.operations.schema import get_schema_info
from ldapie.operations.entry_operations import add_entry, delete_entry, modify_entry


class TestSearchOperations:
    """Test search operations."""
    
    def test_paged_search_import(self):
        """Test that paged_search can be imported."""
        assert paged_search is not None
        assert callable(paged_search)
    
    def test_compare_entries_import(self):
        """Test that compare_entries can be imported."""
        assert compare_entries is not None
        assert callable(compare_entries)


class TestSchemaOperations:
    """Test schema operations."""
    
    def test_get_schema_info_import(self):
        """Test that get_schema_info can be imported."""
        assert get_schema_info is not None
        assert callable(get_schema_info)


class TestEntryOperations:
    """Test entry operations."""
    
    def test_add_entry_import(self):
        """Test that add_entry can be imported."""
        assert add_entry is not None
        assert callable(add_entry)
    
    def test_delete_entry_import(self):
        """Test that delete_entry can be imported."""
        assert delete_entry is not None
        assert callable(delete_entry)
    
    def test_modify_entry_import(self):
        """Test that modify_entry can be imported."""
        assert modify_entry is not None
        assert callable(modify_entry)


if __name__ == "__main__":
    pytest.main([__file__])

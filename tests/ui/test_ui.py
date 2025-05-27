#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for UI and output functionality.
"""

import pytest
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from ldapie.ui.output import output_json, output_ldif, output_csv, output_rich
from ldapie.ui.rich_formatter import add_rich_help_option


class TestOutputFormats:
    """Test output formatting functions."""
    
    def test_output_json_import(self):
        """Test that output_json can be imported."""
        assert output_json is not None
        assert callable(output_json)
    
    def test_output_ldif_import(self):
        """Test that output_ldif can be imported."""
        assert output_ldif is not None
        assert callable(output_ldif)
    
    def test_output_csv_import(self):
        """Test that output_csv can be imported."""
        assert output_csv is not None
        assert callable(output_csv)
    
    def test_output_rich_import(self):
        """Test that output_rich can be imported."""
        assert output_rich is not None
        assert callable(output_rich)


class TestRichFormatter:
    """Test Rich formatting functionality."""
    
    def test_add_rich_help_option_import(self):
        """Test that add_rich_help_option can be imported."""
        assert add_rich_help_option is not None
        assert callable(add_rich_help_option)


if __name__ == "__main__":
    pytest.main([__file__])

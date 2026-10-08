#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared pytest fixtures for LDAPie tests.
"""

import os
import sys

import pytest
from click.testing import CliRunner

# Ensure the src directory is on the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)


@pytest.fixture
def cli_runner():
    """Provide a Click CliRunner for CLI integration tests."""
    return CliRunner()

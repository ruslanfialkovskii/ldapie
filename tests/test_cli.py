#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI integration tests for LDAPie using Click's CliRunner.
"""

import os
import sys
import pytest
from click.testing import CliRunner

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ldapie.ldapie import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_version(runner):
    """Test --version flag"""
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'ldapie' in result.output.lower() or 'version' in result.output.lower()


def test_help(runner):
    """Test --help flag"""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'LDAPie' in result.output


def test_search_invalid_filter(runner):
    """Test that search rejects invalid LDAP filter"""
    result = runner.invoke(cli, [
        'search', 'ldap.example.com', 'dc=example,dc=com', 'invalid_no_parens'
    ])
    assert result.exit_code != 0
    assert 'Invalid LDAP filter' in result.output


def test_search_unbalanced_filter(runner):
    """Test that search rejects unbalanced filter"""
    result = runner.invoke(cli, [
        'search', 'ldap.example.com', 'dc=example,dc=com', '(cn=user'
    ])
    assert result.exit_code != 0
    assert 'Invalid LDAP filter' in result.output


def test_add_invalid_dn(runner):
    """Test that add rejects invalid DN"""
    result = runner.invoke(cli, [
        'add', 'ldap.example.com', '', '--class', 'person'
    ])
    assert result.exit_code != 0


def test_delete_invalid_dn(runner):
    """Test that delete rejects empty DN"""
    result = runner.invoke(cli, [
        'delete', 'ldap.example.com', ''
    ])
    assert result.exit_code != 0


def test_search_help(runner):
    """Test search command help"""
    result = runner.invoke(cli, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Search the LDAP directory' in result.output


def test_search_valid_filter_no_connection(runner):
    """Test that valid filter passes validation but fails on connection"""
    result = runner.invoke(cli, [
        'search', 'nonexistent.example.com', 'dc=example,dc=com',
        '(objectClass=*)', '--port', '1'
    ])
    # Should fail on connection, not on filter validation
    assert result.exit_code != 0
    assert 'Invalid LDAP filter' not in result.output

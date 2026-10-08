#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared pytest fixtures for LDAPie tests.
"""

import os
import sys

import pytest
from click.testing import CliRunner
from ldap3 import MOCK_SYNC, OFFLINE_SLAPD_2_4, Connection, Server

# Ensure the src directory is on the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

BASE_DN = "dc=example,dc=com"
ADMIN_DN = f"cn=admin,{BASE_DN}"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep tests away from the real home directory, env and working directory.

    The interactive shell and the config loader read and write files under
    ``~`` and the current directory.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LDAP_PASSWORD", raising=False)
    monkeypatch.delenv("LDAPIE_THEME", raising=False)
    monkeypatch.chdir(tmp_path)
    return home


@pytest.fixture
def cli_runner():
    """Provide a Click CliRunner for CLI integration tests."""
    return CliRunner()


@pytest.fixture
def ldap_server():
    """A bound MOCK_SYNC connection with OpenLDAP schema and sample entries.

    Returns the ``(server, connection)`` pair, like ``LdapConfig.get_connection``.
    """
    server = Server("mock", get_info=OFFLINE_SLAPD_2_4)
    conn = Connection(
        server,
        user=ADMIN_DN,
        password="secret",
        client_strategy=MOCK_SYNC,
        raise_exceptions=True,
    )
    conn.strategy.add_entry(ADMIN_DN, {"userPassword": "secret", "sn": "admin"})
    conn.bind()
    conn.strategy.add_entry(
        BASE_DN, {"objectClass": ["top", "domain"], "dc": "example"}
    )
    conn.strategy.add_entry(
        f"ou=people,{BASE_DN}",
        {"objectClass": ["top", "organizationalUnit"], "ou": "people"},
    )
    for uid in ("jdoe", "jsmith"):
        conn.strategy.add_entry(
            f"cn={uid},ou=people,{BASE_DN}",
            {
                "objectClass": ["top", "person"],
                "cn": uid,
                "sn": uid.upper(),
                "description": f"{uid} description",
                "createTimestamp": "20240101120000Z",
            },
        )
    return server, conn


@pytest.fixture
def mock_ldap(monkeypatch, ldap_server):
    """Route every LdapConfig connection (CLI and shell) to the mock server."""
    from ldapie.ldapie import LdapConfig

    monkeypatch.setattr(LdapConfig, "get_connection", lambda self: ldap_server)
    return ldap_server

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security behavior: clear-text binds, recursive delete scope, history permissions.
"""

import io
import os
import stat

import ldap3
import pytest
from rich.console import Console

from ldapie import entry_operations, interactive
from ldapie import ldapie as ldapie_module
from ldapie.help_context import CommandValidator
from ldapie.interactive import LDAPShell
from ldapie.ldapie import LdapConfig, PlaintextBindRefused, cli
from ldapie.utils import is_loopback_host

BASE_DN = "dc=example,dc=com"
HOST = "ldap.example.com"


class _FakeConnection:
    instances: list = []

    def __init__(self, server, **kwargs):
        self.kwargs = kwargs
        _FakeConnection.instances.append(self)


@pytest.fixture
def fake_connection(monkeypatch):
    _FakeConnection.instances = []
    monkeypatch.setattr(ldapie_module, "Connection", _FakeConnection)
    return _FakeConnection


def _no_prompt(prompt=""):
    raise AssertionError("prompted for a password")


class TestPlaintextBind:
    def test_password_bind_without_tls_is_refused_before_reading_it(
        self, fake_connection, monkeypatch
    ):
        monkeypatch.setenv("LDAP_PASSWORD", "from-env")
        monkeypatch.setattr(ldapie_module.getpass, "getpass", _no_prompt)
        config = LdapConfig(host=HOST, username="cn=admin")

        with pytest.raises(PlaintextBindRefused, match="clear text"):
            config.get_connection()

        assert config.password is None
        assert fake_connection.instances == []

    @pytest.mark.parametrize("flag", ["use_ssl", "starttls"])
    def test_tls_bind_is_allowed(self, fake_connection, flag):
        LdapConfig(
            host=HOST, username="cn=admin", password="pw", **{flag: True}
        ).get_connection()
        assert len(fake_connection.instances) == 1

    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
    def test_loopback_bind_is_allowed(self, fake_connection, host):
        LdapConfig(host=host, username="cn=admin", password="pw").get_connection()
        assert len(fake_connection.instances) == 1

    def test_allow_plaintext_binds_with_a_warning(self, fake_connection, capsys):
        LdapConfig(
            host=HOST, username="cn=admin", password="pw", allow_plaintext=True
        ).get_connection()
        assert len(fake_connection.instances) == 1
        assert "clear text" in capsys.readouterr().err

    def test_anonymous_plain_connection_is_allowed(self, fake_connection):
        LdapConfig(host=HOST).get_connection()
        assert len(fake_connection.instances) == 1

    def test_cli_reports_the_refusal(self, cli_runner, fake_connection, monkeypatch):
        monkeypatch.setenv("LDAP_PASSWORD", "from-env")
        result = cli_runner.invoke(cli, ["search", HOST, BASE_DN, "-u", "cn=admin"])
        assert result.exit_code == 1
        assert "refusing to send the password in clear text" in result.output
        assert fake_connection.instances == []

    def test_cli_flag_allows_it(self, cli_runner, monkeypatch):
        seen = {}

        def fake_get_connection(config, **kwargs):
            seen.update(vars(config))
            raise ldap3.core.exceptions.LDAPException("stop here")

        monkeypatch.setattr(LdapConfig, "get_connection", fake_get_connection)
        cli_runner.invoke(
            cli, ["search", HOST, BASE_DN, "-u", "cn=admin", "--allow-plaintext"]
        )
        assert seen["allow_plaintext"] is True

    def test_shell_connect_reports_the_refusal(self, fake_connection, monkeypatch):
        monkeypatch.setenv("LDAP_PASSWORD", "from-env")
        out = io.StringIO()
        shell = LDAPShell(None, None, Console(file=out, width=200), None)
        shell.onecmd(f"connect {HOST} cn=admin,{BASE_DN}")
        assert "refusing to send the password" in out.getvalue()
        assert not shell.connected

    def test_validate_warns_about_the_refusal(self):
        result = CommandValidator().validate_command(
            f"connect {HOST} cn=admin,{BASE_DN}"
        )
        assert "refused" in result["warning"]

    def test_validate_accepts_allow_plaintext(self):
        result = CommandValidator().validate_command(
            f"connect {HOST} cn=admin,{BASE_DN} --allow-plaintext"
        )
        assert "refused" not in result.get("warning", "")


def test_loopback_host():
    assert is_loopback_host("LOCALHOST")
    assert is_loopback_host("127.0.0.2")
    assert not is_loopback_host("ldap.example.com")
    assert not is_loopback_host("10.0.0.1")


class _ListingConnection:
    def __init__(self, dns):
        self.dns = dns
        self.search_kwargs = {}
        self.result = {}

    def search(self, base_dn, search_filter, **kwargs):
        self.search_kwargs = kwargs
        self.entries = [type("Entry", (), {"entry_dn": dn})() for dn in self.dns]
        return True


class TestRecursiveDelete:
    def test_listing_does_not_follow_aliases(self):
        conn = _ListingConnection([f"ou=old,{BASE_DN}", f"cn=a,ou=old,{BASE_DN}"])
        dns = entry_operations.list_subtree(conn, f"ou=old,{BASE_DN}")
        assert conn.search_kwargs["dereference_aliases"] == ldap3.DEREF_NEVER
        assert dns == [f"cn=a,ou=old,{BASE_DN}", f"ou=old,{BASE_DN}"]

    def test_entry_outside_the_subtree_stops_the_delete(self):
        conn = _ListingConnection([f"ou=old,{BASE_DN}", f"cn=jdoe,ou=people,{BASE_DN}"])
        with pytest.raises(RuntimeError, match="outside"):
            entry_operations.list_subtree(conn, f"ou=old,{BASE_DN}")

    def test_scope_check_ignores_case(self):
        conn = _ListingConnection(["CN=a,OU=Old,DC=example,DC=com"])
        assert entry_operations.list_subtree(conn, f"ou=old,{BASE_DN}") == [
            "CN=a,OU=Old,DC=example,DC=com"
        ]

    def test_similar_suffix_is_outside(self):
        conn = _ListingConnection([f"cn=a,ou=older,{BASE_DN}"])
        with pytest.raises(RuntimeError, match="outside"):
            entry_operations.list_subtree(conn, f"ou=old,{BASE_DN}")


def test_history_file_is_owner_only_before_readline_writes(tmp_path, monkeypatch):
    if interactive.readline is None:
        pytest.skip("readline is not available")
    modes = []

    def fake_write(path):
        modes.append(stat.S_IMODE(os.stat(path).st_mode))

    monkeypatch.setattr(interactive.readline, "write_history_file", fake_write)
    shell = LDAPShell(None, None, Console(file=io.StringIO()), None)
    shell.history_file = str(tmp_path / "history")
    shell._save_history()
    assert modes == [0o600]

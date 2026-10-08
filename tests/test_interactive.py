#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive shell tests against a MOCK_SYNC LDAP server.
"""

import io
import threading

import pytest
from rich.console import Console
from rich.theme import Theme

from ldapie import interactive
from ldapie.interactive import LDAPShell
from ldapie.ldapie import DARK_THEME, LdapConfig

BASE_DN = "dc=example,dc=com"
JDOE = f"cn=jdoe,ou=people,{BASE_DN}"


@pytest.fixture
def make_shell():
    def factory(server=None, conn=None, base_dn=None):
        out = io.StringIO()
        console = Console(file=out, width=200, theme=Theme(DARK_THEME))
        shell = LDAPShell(server, conn, console, base_dn)
        shell.output = out
        return shell

    return factory


@pytest.fixture
def shell(make_shell, ldap_server):
    server, conn = ldap_server
    return make_shell(server, conn)


def test_base_sets_dn_and_records_history(shell):
    assert shell.onecmd(f"base {BASE_DN}") is False
    assert shell.base_dn == BASE_DN
    assert shell.query_history.get_bases() == [BASE_DN]
    assert BASE_DN in shell.prompt


def test_base_rejects_invalid_dn(shell):
    shell.onecmd("base not a dn")
    assert shell.base_dn == ""
    assert "Invalid DN" in shell.output.getvalue()


def test_search_prints_results_and_records_history(shell):
    shell.onecmd(f"base {BASE_DN}")
    shell.onecmd("search (cn=jdoe)")
    output = shell.output.getvalue()
    assert JDOE in output
    assert "Search failed" not in output
    assert "Error" not in output
    assert shell.query_history.get_searches() == ["(cn=jdoe)"]


def test_connect_uses_ldap_config(make_shell, ldap_server, monkeypatch):
    seen = {}

    def fake_get_connection(config, **kwargs):
        seen.update(vars(config))
        return ldap_server

    monkeypatch.setattr(LdapConfig, "get_connection", fake_get_connection)
    shell = make_shell()
    shell.onecmd(f"connect ldap.example.com 389 cn=admin,{BASE_DN} --starttls")

    output = shell.output.getvalue()
    assert "Connected to ldap.example.com" in output
    assert "Connection failed" not in output
    assert shell.connected
    assert seen["starttls"] is True
    assert seen["no_verify"] is False
    assert seen["username"] == f"cn=admin,{BASE_DN}"
    assert seen["port"] == 389
    assert shell.query_history.get_hosts() == ["ldap.example.com"]


def test_connect_rejects_unknown_flags(make_shell):
    shell = make_shell()
    shell.onecmd("connect ldap.example.com --bogus")
    assert "Usage: connect" in shell.output.getvalue()
    assert not shell.connected


def test_connect_passes_the_ca_bundle(make_shell, ldap_server, monkeypatch, tmp_path):
    seen = {}

    def fake_get_connection(config, **kwargs):
        seen.update(vars(config))
        return ldap_server

    monkeypatch.setattr(LdapConfig, "get_connection", fake_get_connection)
    shell = make_shell()
    shell.onecmd(f"connect ldap.example.com --ssl --ca-cert {tmp_path}/ca.pem")
    assert shell.connected, shell.output.getvalue()
    assert seen["ca_cert"] == f"{tmp_path}/ca.pem"
    assert seen["use_ssl"] is True
    # The file name is the option's value, not the bind DN
    assert seen["username"] is None


def test_connect_reports_a_missing_ca_bundle(make_shell):
    shell = make_shell()
    shell.onecmd("connect ldap.example.com --ssl --ca-cert /nonexistent/ca.pem")
    assert "Connection failed" in shell.output.getvalue()
    assert not shell.connected


def test_connect_ca_cert_needs_a_value(make_shell):
    shell = make_shell()
    shell.onecmd("connect ldap.example.com --ca-cert")
    output = shell.output.getvalue()
    assert "--ca-cert needs a value" in output
    assert "Usage: connect" in output


def test_connect_validates_its_arguments_before_connecting(make_shell):
    """The shell applies the same checks as `validate connect`."""
    shell = make_shell()
    shell.onecmd("connect ldap.example.com 99999")
    shell.onecmd("connect ldap.example.com not-a-dn")
    shell.onecmd("connect ldap.example.com --ca-cert /tmp/ca.pem")
    shell.onecmd("connect ldap.example.com 389 cn=admin,dc=x extra")
    output = shell.output.getvalue()
    assert "Port 99999 is out of range" in output
    assert "Invalid DN" in output
    assert "--ca-cert needs --ssl or --starttls" in output
    assert "Unexpected argument 'extra'" in output
    assert not shell.connected


def test_connect_failure_message_is_sanitized(make_shell, monkeypatch):
    from ldap3.core.exceptions import LDAPException

    def boom(config, **kwargs):
        raise LDAPException("diag: \x1b[2J [link=http://evil.example]x[/link]")

    monkeypatch.setattr(LdapConfig, "get_connection", boom)
    shell = make_shell()
    shell.onecmd("connect ldap.example.com")
    output = shell.output.getvalue()
    assert "Connection failed" in output
    assert "\x1b" not in output
    assert "\\x1b[2J" in output
    assert "[link=http://evil.example]x[/link]" in output


def test_search_requires_connection_base_and_a_valid_filter(make_shell, ldap_server):
    shell = make_shell()
    shell.onecmd("search (cn=*)")
    assert "Not connected" in shell.output.getvalue()

    server, conn = ldap_server
    shell = make_shell(server, conn)
    shell.onecmd("search (cn=*)")
    assert "Base DN not set" in shell.output.getvalue()

    shell.onecmd(f"base {BASE_DN}")
    shell.onecmd("search cn=*")
    assert "Invalid LDAP filter" in shell.output.getvalue()
    shell.onecmd("search (cn=nobody)")
    assert "No entries found" in shell.output.getvalue()


def test_info_and_schema_need_a_connection(make_shell):
    shell = make_shell()
    shell.onecmd("info")
    shell.onecmd("schema")
    assert shell.output.getvalue().count("Not connected") == 2


def test_info_and_schema_in_the_shell(shell):
    shell.onecmd("info")
    shell.onecmd("schema person")
    shell.onecmd("schema --attr cn")
    output = shell.output.getvalue()
    assert "LDAP Server Information" in output
    assert "STRUCTURAL" in output
    assert "commonName" in output


def test_history_suggest_validate_and_unknown_commands(shell):
    shell.onecmd(f"base {BASE_DN}")
    shell.onecmd("history")
    shell.onecmd("history base")
    shell.onecmd("history bogus")
    shell.onecmd("suggest")
    shell.onecmd("validate search (cn=*)")
    shell.onecmd("validate")
    shell.onecmd("bogus")
    output = shell.output.getvalue()
    assert "Query History" in output
    assert "Base DN History" in output
    assert "Unknown history type: bogus" in output
    assert "Context-Aware Suggestions" in output
    assert "Search command looks valid" in output
    assert "Please provide a command to validate" in output
    assert "Unknown command: bogus" in output


def test_command_errors_do_not_end_the_session(shell, monkeypatch):
    def boom(arg):
        raise RuntimeError("kaput")

    monkeypatch.setattr(shell, "do_info", boom)
    assert shell.onecmd("info") is False
    assert "kaput" in shell.output.getvalue()


def test_eof_exits(shell):
    assert shell.onecmd("EOF") is True


def test_cmdloop_stops_at_end_of_input(shell):
    shell.use_rawinput = False
    shell.stdin = io.StringIO("help\n")
    worker = threading.Thread(target=shell.cmdloop, daemon=True)
    worker.start()
    worker.join(timeout=10)
    assert not worker.is_alive(), "shell kept looping after end of input"


def test_question_mark_shows_help_overlay(shell, monkeypatch):
    calls = []
    monkeypatch.setattr(
        interactive, "show_help_overlay", lambda text, *args: calls.append(text)
    )
    assert shell.precmd("search ?") == ""
    assert shell.precmd("search?") == ""
    assert calls == ["search", "search"]
    # A lone '?' stays the standard help command
    assert shell.precmd("?") == "?"


def test_help_panel_shows_bracketed_usage(shell):
    shell.onecmd("help")
    assert "connect host [port] [bind_dn]" in shell.output.getvalue()


def test_intro_has_real_newlines(shell):
    assert "\\n" not in shell.intro


def test_completer_delimiters_are_whitespace(shell):
    if interactive.readline is None:
        pytest.skip("readline not available")
    assert interactive.readline.get_completer_delims() == " \t\n"

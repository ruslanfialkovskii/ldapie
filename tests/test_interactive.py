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

    def fake_get_connection(config):
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

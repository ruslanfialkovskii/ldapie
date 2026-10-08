#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the context-sensitive help system (HelpContext, CommandValidator,
help overlay).
"""

import io

import pytest
from rich.console import Console
from rich.theme import Theme

from ldapie.help_context import CommandValidator, HelpContext
from ldapie.help_overlay import show_help_overlay
from ldapie.ldapie import DARK_THEME


def test_suggestions_after_commands():
    help_context = HelpContext()
    help_context.add_command("search ldap.example.com 'dc=example,dc=com'")
    help_context.update_session_state(
        connected=True, authenticated=True, ssl_enabled=False
    )

    suggestions = help_context.get_suggestions()
    assert set(suggestions) >= {"next_commands", "examples", "tips"}
    assert suggestions["next_commands"]


def test_discovered_syntax_lists_arguments_not_options():
    syntax = HelpContext().get_command_help("search")["syntax"]
    assert syntax == "search <host> <base_dn> [<filter_query>] [options]"


def test_mistyped_command_gets_a_suggestion():
    help_info = HelpContext().get_command_help("serch")
    assert "Did you mean 'search'" in help_info["error"]


def test_validator_accepts_quoted_filter():
    result = CommandValidator(HelpContext()).validate_command(
        "search ldap.example.com 'dc=example,dc=com' '(objectClass=person)'"
    )
    assert "error" not in result
    assert "warning" not in result
    assert result["arguments"] == [
        "ldap.example.com",
        "dc=example,dc=com",
        "(objectClass=person)",
    ]


def test_validator_reports_missing_arguments():
    result = CommandValidator(HelpContext()).validate_command("search")
    assert "Not enough arguments" in result["error"]


def test_validator_warns_about_non_recursive_delete():
    result = CommandValidator(HelpContext()).validate_command(
        "delete ldap.example.com 'ou=x,dc=example,dc=com'"
    )
    assert "--recursive" in result["suggestion"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "search",
        "search ldap.example.com",
        "search ldap.example.com dc=example,dc=com",
        "serch",
    ],
)
def test_help_overlay_renders(text):
    out = io.StringIO()
    console = Console(file=out, width=120, theme=Theme(DARK_THEME))
    show_help_overlay(text, HelpContext(), console, non_interactive=True)
    assert "Context Help" in out.getvalue()

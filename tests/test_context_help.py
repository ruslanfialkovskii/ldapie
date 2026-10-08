#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the interactive shell's context help (HelpContext, CommandValidator,
help overlay).
"""

import io

import pytest
from rich.console import Console
from rich.theme import Theme

from ldapie.help_context import COMMAND_PATTERNS, CommandValidator, HelpContext
from ldapie.help_overlay import show_help_overlay
from ldapie.interactive import LDAPShell
from ldapie.ldapie import DARK_THEME


def render_overlay(text, help_context=None):
    out = io.StringIO()
    console = Console(file=out, width=120, theme=Theme(DARK_THEME))
    show_help_overlay(text, help_context or HelpContext(), console)
    return out.getvalue()


def test_patterns_cover_every_shell_command():
    shell_commands = {
        name[len("do_") :] for name in dir(LDAPShell) if name.startswith("do_")
    }
    assert shell_commands - {"EOF"} == set(COMMAND_PATTERNS)


def test_command_help_describes_shell_syntax():
    assert (
        HelpContext().get_command_help("search")["syntax"]
        == "search [filter] [attribute...]"
    )


def test_mistyped_command_gets_a_suggestion():
    help_info = HelpContext().get_command_help("serch")
    assert "Did you mean 'search'" in help_info["error"]


def test_suggestions_follow_the_session_state():
    help_context = HelpContext()
    help_context.add_command("search (objectClass=person)")
    help_context.update_session_state(
        connected=True, authenticated=False, ssl_enabled=False
    )

    help_context.add_command("suggest")  # asking for help keeps 'search' current

    suggestions = help_context.get_suggestions()
    assert suggestions["examples"] == COMMAND_PATTERNS["search"]["examples"]
    assert any("base" in step for step in suggestions["next_commands"])
    assert any("--starttls" in tip for tip in suggestions["tips"])
    assert any("anonymous" in tip for tip in suggestions["tips"])


def test_validator_reports_missing_arguments():
    result = CommandValidator().validate_command("base")
    assert "Not enough arguments" in result["error"]


def test_validator_previews_search_with_attributes():
    help_context = HelpContext()
    help_context.current_context["base_dn"] = "dc=example,dc=com"
    help_context.update_session_state(
        connected=True, authenticated=True, ssl_enabled=True
    )
    result = CommandValidator(help_context).validate_command(
        "search '(objectClass=person)' cn mail"
    )
    assert "error" not in result
    assert "warning" not in result
    assert result["arguments"] == ["(objectClass=person)", "cn", "mail"]
    assert "dc=example,dc=com" in result["preview"]
    assert "cn, mail" in result["preview"]


def test_validator_rejects_filter_without_parentheses():
    result = CommandValidator().validate_command("search objectClass=person")
    assert "Invalid LDAP filter" in result["error"]
    assert result["suggestion"] == "Try: search (objectClass=person)"


def test_validator_warns_when_not_connected():
    result = CommandValidator().validate_command("search (cn=*)")
    assert "Not connected" in result["warning"]


def test_validator_handles_connect_ca_cert_option():
    validator = CommandValidator()
    result = validator.validate_command(
        "connect ldap.example.com --ssl --ca-cert /etc/ssl/corp.pem"
    )
    assert "error" not in result, result
    assert result["preview"] == (
        "Would connect to ldap.example.com:636 as anonymous over TLS, "
        "verified with /etc/ssl/corp.pem"
    )

    result = validator.validate_command("connect ldap.example.com --ca-cert")
    assert result["error"] == "--ca-cert needs a value"

    result = validator.validate_command("connect ldap.example.com --ca-cert ca.pem")
    assert result["error"] == "--ca-cert needs --ssl or --starttls"

    # Options alone are not a host
    result = validator.validate_command("connect --ssl")
    assert result["error"] == "connect needs a host"


def test_validator_rejects_bad_connect_port_and_dn():
    validator = CommandValidator()
    assert "out of range" in validator.validate_command("connect host 70000")["error"]
    assert "Invalid DN" in validator.validate_command("connect host 389 nope")["error"]


def test_help_overlay_lists_every_connect_option():
    from ldapie.help_context import CONNECT_FLAGS, CONNECT_VALUE_OPTIONS
    from ldapie.help_overlay import CONNECT_OPTIONS

    for option in CONNECT_FLAGS + CONNECT_VALUE_OPTIONS:
        assert any(line.startswith(option) for line in CONNECT_OPTIONS), option


def test_validator_rejects_unknown_connect_flag():
    result = CommandValidator().validate_command("connect ldap.example.com --bogus")
    assert "--bogus" in result["error"]


def test_validator_previews_connect():
    result = CommandValidator().validate_command(
        "connect ldap.example.com 636 cn=admin,dc=example,dc=com --ssl"
    )
    assert result["preview"] == (
        "Would connect to ldap.example.com:636 as cn=admin,dc=example,dc=com over TLS"
    )
    assert "warning" not in result


def test_validator_warns_about_plain_connect():
    result = CommandValidator().validate_command("connect ldap.example.com")
    assert "not be encrypted" in result["warning"]


def test_validator_rejects_invalid_base_dn():
    result = CommandValidator().validate_command("base not a dn")
    assert "Invalid DN" in result["error"]


@pytest.mark.parametrize(
    "text", ["", "search", "search (uid=*)", "connect", "base", "info", "serch"]
)
def test_help_overlay_renders(text):
    assert "Context Help" in render_overlay(text)


def test_help_overlay_shows_shell_syntax():
    text = render_overlay("search")
    assert "search [filter] [attribute...]" in text
    assert "<host>" not in text


def test_help_overlay_shows_connect_options_and_recent_hosts():
    help_context = HelpContext()
    help_context.add_command("connect ldap.example.com 389")
    text = render_overlay("connect", help_context)
    assert "connect host [port] [bind_dn]" in text
    assert "--starttls" in text
    assert "Recent hosts: ldap.example.com" in text

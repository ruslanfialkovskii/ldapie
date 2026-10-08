#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for config file loading and how commands use config defaults.
"""

import pytest

from ldapie import ldapie as ldapie_module
from ldapie.config import load_config
from ldapie.ldapie import LdapConfig, cli

BASE_DN = "dc=example,dc=com"


@pytest.fixture
def user_config(isolated_home):
    path = isolated_home / ".config" / "ldapie" / "config.yaml"
    path.parent.mkdir(parents=True)

    def write(text):
        path.write_text(text)

    return write


@pytest.fixture
def project_config(tmp_path):
    # The autouse isolated_home fixture makes tmp_path the working directory
    def write(text):
        (tmp_path / ".ldapie.yaml").write_text(text)

    return write


@pytest.fixture
def captured_config(monkeypatch, ldap_server):
    """Record the LdapConfig each command connects with."""
    seen = []

    def fake_get_connection(config):
        seen.append(config)
        return ldap_server

    monkeypatch.setattr(LdapConfig, "get_connection", fake_get_connection)
    return seen


def test_project_config_overrides_user_config(user_config, project_config):
    user_config("default_username: cn=user\nport: 1389\n")
    project_config("port: 2389\n")
    assert load_config() == {"default_username": "cn=user", "port": 2389}


def test_project_config_cannot_disable_tls_verification(user_config, project_config):
    project_config("no_verify: true\nuse_ssl: true\n")
    warnings = []
    assert load_config(warnings.append) == {"use_ssl": True}
    assert any("no_verify" in w for w in warnings)

    user_config("no_verify: true\n")
    assert load_config()["no_verify"] is True


@pytest.mark.parametrize(
    "text, message",
    [
        ("port: abc\n", "expected int"),
        ("port: true\n", "expected int"),
        ("use_ssl: 'yes'\n", "expected bool"),
        ("theme: neon\n", "theme"),
        ("colour: red\n", "unknown setting"),
        ("- just\n- a list\n", "mapping"),
        ("port: [unclosed\n", "could not read"),
    ],
)
def test_invalid_settings_are_skipped_with_a_warning(user_config, text, message):
    user_config(text)
    warnings = []
    assert load_config(warnings.append) == {}
    assert any(message in w for w in warnings), warnings


def test_commands_use_config_defaults(cli_runner, user_config, captured_config):
    user_config(
        "default_username: cn=admin,dc=example,dc=com\n"
        "use_ssl: true\n"
        "port: 1636\n"
        "no_verify: true\n"
    )
    result = cli_runner.invoke(cli, ["search", "ldap.example.com", BASE_DN])
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.username == "cn=admin,dc=example,dc=com"
    assert config.use_ssl is True
    assert config.port == 1636
    assert config.no_verify is True


def test_command_line_overrides_config(cli_runner, user_config, captured_config):
    user_config(
        "default_username: cn=admin,dc=example,dc=com\n"
        "use_ssl: true\n"
        "starttls: true\n"
        "no_verify: true\n"
    )
    result = cli_runner.invoke(
        cli,
        [
            "search",
            "ldap.example.com",
            BASE_DN,
            "-u",
            "cn=other",
            "--no-ssl",
            "--no-starttls",
            "--verify",
        ],
    )
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.username == "cn=other"
    assert config.use_ssl is False
    assert config.starttls is False
    assert config.no_verify is False


def test_interactive_uses_default_host(cli_runner, user_config, captured_config):
    user_config("default_host: ldap.example.com\n")
    result = cli_runner.invoke(cli, ["interactive"], input="exit\n")
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.host == "ldap.example.com"


def test_config_theme_is_applied(cli_runner, user_config, monkeypatch):
    applied = []
    monkeypatch.setattr(ldapie_module, "_apply_theme", applied.append)
    user_config("theme: light\n")
    cli_runner.invoke(cli, ["--show-completion"], env={"SHELL": "/bin/bash"})
    assert applied == ["light"]


def test_theme_env_var_wins_over_config(cli_runner, user_config, monkeypatch):
    applied = []
    monkeypatch.setattr(ldapie_module, "_apply_theme", applied.append)
    monkeypatch.setenv("LDAPIE_THEME", "dark")
    user_config("theme: light\n")
    cli_runner.invoke(cli, ["--show-completion"], env={"SHELL": "/bin/bash"})
    assert applied == []


def test_defaults_without_config(cli_runner, captured_config):
    result = cli_runner.invoke(cli, ["search", "ldap.example.com", BASE_DN])
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.port == 389
    assert config.username is None
    assert config.password is None
    assert config.use_ssl is False
    assert config.starttls is False
    assert config.no_verify is False

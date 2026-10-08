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

    def fake_get_connection(config, **kwargs):
        seen.append(config)
        return ldap_server

    monkeypatch.setattr(LdapConfig, "get_connection", fake_get_connection)
    return seen


def test_project_config_can_only_set_theme_and_turn_tls_on(user_config, project_config):
    user_config("default_username: cn=user\nport: 1389\nuse_ssl: false\n")
    project_config(
        "theme: light\n"
        "starttls: true\n"
        "port: 2389\n"
        "default_host: evil.example.net\n"
        "default_username: cn=admin\n"
        "ca_cert: /tmp/evil-ca.pem\n"
        "timeout: 1\n"
    )
    warnings, notices = [], []
    assert load_config(warnings.append, notices.append) == {
        "default_username": "cn=user",
        "port": 1389,
        "use_ssl": False,
        "theme": "light",
        "starttls": True,
    }
    for key in ("port", "default_host", "default_username", "ca_cert", "timeout"):
        assert any(f"'{key}'" in w for w in warnings), (key, warnings)
    assert notices == [".ldapie.yaml: using starttls, theme"]


def test_project_config_cannot_turn_tls_off(user_config, project_config):
    user_config("use_ssl: true\nstarttls: true\n")
    project_config("use_ssl: false\nstarttls: false\n")
    warnings, notices = [], []
    config = load_config(warnings.append, notices.append)
    assert config["use_ssl"] is True
    assert config["starttls"] is True
    assert len([w for w in warnings if "can only turn TLS on" in w]) == 2
    assert notices == []


def test_config_warnings_are_sanitized(cli_runner, project_config):
    """A key from a cloned repository's file is quoted in the warning."""
    project_config('"\\e[2J evil": 1\n')
    result = cli_runner.invoke(cli, ["--show-completion"], env={"SHELL": "/bin/bash"})
    assert result.exit_code == 0, result.output
    assert "\x1b" not in result.output
    assert "\\x1b[2J evil" in result.output


def test_project_config_cannot_disable_tls_verification(user_config, project_config):
    project_config("no_verify: true\nuse_ssl: true\n")
    warnings = []
    assert load_config(warnings.append) == {"use_ssl": True}
    assert any("no_verify" in w for w in warnings)

    user_config("no_verify: true\n")
    assert load_config()["no_verify"] is True


def test_project_config_cannot_choose_the_server(
    cli_runner, project_config, captured_config, monkeypatch
):
    """A cloned repository must not be able to point the shell, and the
    user's LDAP_PASSWORD, at a server of its choosing."""
    project_config("default_host: evil.example.net\ndefault_username: cn=admin,dc=x\n")
    monkeypatch.setenv("LDAP_PASSWORD", "s3cret")
    result = cli_runner.invoke(cli, ["interactive"], input="exit\n")
    assert result.exit_code == 0, result.output
    assert captured_config == []
    assert "ignoring 'default_host'" in result.output
    assert "ignoring 'default_username'" in result.output


@pytest.mark.parametrize(
    "text, message",
    [
        ("port: abc\n", "expected int"),
        ("port: true\n", "expected int"),
        ("port: 0\n", "positive"),
        ("timeout: -5\n", "positive"),
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
    assert config.ca_cert is None
    assert config.timeout == 30


def test_ca_cert_and_timeout_from_config(
    cli_runner, user_config, captured_config, isolated_home
):
    (isolated_home / "ca.pem").write_text("cert")
    user_config("ca_cert: ~/ca.pem\ntimeout: 5\n")
    result = cli_runner.invoke(cli, ["search", "ldap.example.com", BASE_DN])
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.ca_cert == str(isolated_home / "ca.pem")
    assert config.timeout == 5


def test_ca_cert_and_timeout_from_command_line(cli_runner, captured_config, tmp_path):
    ca = tmp_path / "corp.pem"
    ca.write_text("cert")
    result = cli_runner.invoke(
        cli,
        [
            "search",
            "ldap.example.com",
            BASE_DN,
            "--ssl",
            "--ca-cert",
            str(ca),
            "--timeout",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output
    (config,) = captured_config
    assert config.ca_cert == str(ca)
    assert config.timeout == 3

    result = cli_runner.invoke(
        cli,
        [
            "search",
            "ldap.example.com",
            BASE_DN,
            "--ssl",
            "--ca-cert",
            str(tmp_path / "x"),
        ],
    )
    assert result.exit_code == 2
    assert "does not exist" in result.output

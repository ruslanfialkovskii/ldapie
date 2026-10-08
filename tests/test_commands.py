#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI command tests against a MOCK_SYNC LDAP server.

Each test drives the real command body through CliRunner; only
LdapConfig.get_connection is replaced (see the ``mock_ldap`` fixture).
"""

import json

import pytest
from ldap3 import AUTO_BIND_TLS_BEFORE_BIND, BASE
from ldap3.core.exceptions import LDAPNoSuchObjectResult

from ldapie import ldapie as ldapie_module
from ldapie.ldapie import LdapConfig, cli
from ldapie.ldif_parser import parse_ldif

BASE_DN = "dc=example,dc=com"
JDOE = f"cn=jdoe,ou=people,{BASE_DN}"
HOST = "ldap.example.com"


def read_entry(conn, dn, attrs=("*",)):
    try:
        conn.search(dn, "(objectClass=*)", BASE, attributes=list(attrs))
    except LDAPNoSuchObjectResult:
        return None
    return conn.entries[0] if conn.entries else None


# --- modify ---------------------------------------------------------------


def test_modify_replace(cli_runner, mock_ldap):
    _, conn = mock_ldap
    result = cli_runner.invoke(
        cli, ["modify", HOST, JDOE, "--replace", "description=new value"]
    )
    assert result.exit_code == 0, result.output
    assert read_entry(conn, JDOE).description.values == ["new value"]


def test_modify_add_multiple_values_and_delete(cli_runner, mock_ldap):
    _, conn = mock_ldap
    result = cli_runner.invoke(
        cli,
        [
            "modify",
            HOST,
            JDOE,
            "--add",
            "mail=a@example.com",
            "--add",
            "mail=b@example.com",
            "--delete",
            "description",
        ],
    )
    assert result.exit_code == 0, result.output
    entry = read_entry(conn, JDOE)
    assert sorted(entry.mail.values) == ["a@example.com", "b@example.com"]
    assert "description" not in entry.entry_attributes


# --- search output ----------------------------------------------------------


def test_search_rich_output_to_file(cli_runner, mock_ldap, tmp_path):
    out = tmp_path / "out.txt"
    result = cli_runner.invoke(
        cli, ["search", HOST, BASE_DN, "(cn=jdoe)", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert JDOE in out.read_text()


def test_search_json_serializes_timestamps(cli_runner, mock_ldap):
    result = cli_runner.invoke(
        cli,
        [
            "search",
            HOST,
            BASE_DN,
            "(cn=jdoe)",
            "-a",
            "cn",
            "-a",
            "createTimestamp",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    # Status lines go to stderr, so stdout is pipeable JSON
    payload = json.loads(result.stdout)
    assert payload[0]["dn"] == JDOE
    assert payload[0]["createTimestamp"].startswith("2024-01-01T12:00:00")


def test_search_pages_by_default(cli_runner, mock_ldap, monkeypatch):
    calls = []
    original = ldapie_module.search_utils.paged_search

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(ldapie_module.search_utils, "paged_search", spy)
    result = cli_runner.invoke(cli, ["search", HOST, BASE_DN, "(cn=*)"])
    assert result.exit_code == 0, result.output
    assert calls, "search should use paged results by default"
    assert "Found 3 entries" in result.output


def test_search_theme_option_is_applied(cli_runner, mock_ldap):
    result = cli_runner.invoke(
        cli, ["search", HOST, BASE_DN, "(cn=jdoe)", "--theme", "light"]
    )
    assert result.exit_code == 0, result.output


# --- schema -----------------------------------------------------------------


def test_schema_object_class(cli_runner, mock_ldap):
    result = cli_runner.invoke(cli, ["schema", HOST, "person"])
    assert result.exit_code == 0, result.output
    assert "STRUCTURAL" in result.output
    assert "sn" in result.output


def test_schema_attribute(cli_runner, mock_ldap):
    result = cli_runner.invoke(cli, ["schema", HOST, "--attr", "cn"])
    assert result.exit_code == 0, result.output
    assert "commonName" in result.output


def test_schema_lists_object_classes(cli_runner, mock_ldap):
    result = cli_runner.invoke(cli, ["schema", HOST])
    assert result.exit_code == 0, result.output
    assert "inetOrgPerson" in result.output


# --- import / export ----------------------------------------------------------


def test_import_continues_after_failed_entry(cli_runner, mock_ldap, tmp_path):
    _, conn = mock_ldap
    ldif = tmp_path / "in.ldif"
    ldif.write_text(
        "version: 1\n"
        "# jdoe already exists\n"
        f"dn: {JDOE}\n"
        "objectClass: person\n"
        "cn: jdoe\n"
        "sn: X\n"
        "\n"
        f"dn: cn=newbie,ou=people,{BASE_DN}\n"
        "objectClass: person\n"
        "cn: newbie\n"
        "sn: N\n"
        "description: a long description that was folded\n"
        "  across two lines\n"
    )
    result = cli_runner.invoke(cli, ["import", HOST, str(ldif)])
    assert result.exit_code == 1, result.output
    assert "1 added, 1 errors" in result.output
    entry = read_entry(conn, f"cn=newbie,ou=people,{BASE_DN}")
    assert entry is not None
    assert entry.description.value == (
        "a long description that was folded across two lines"
    )


def test_export_ldif_round_trips_binary_values(cli_runner, mock_ldap, tmp_path):
    _, conn = mock_ldap
    photo = bytes(range(256))
    conn.strategy.add_entry(
        f"cn=pic,ou=people,{BASE_DN}",
        {"objectClass": ["person"], "cn": "pic", "sn": "P", "jpegPhoto": photo},
    )
    out = tmp_path / "export.ldif"
    result = cli_runner.invoke(
        cli, ["export", HOST, BASE_DN, "(cn=pic)", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    records = parse_ldif(out.read_text())
    assert len(records) == 1
    dn, attrs = records[0]
    assert dn == f"cn=pic,ou=people,{BASE_DN}"
    assert attrs["jpegPhoto"] == [photo]
    assert attrs["cn"] == ["pic"]


# --- rename / delete ------------------------------------------------------------


@pytest.mark.parametrize(
    "flags, expected",
    [([], True), (["--delete-old-rdn"], True), (["--keep-old-rdn"], False)],
)
def test_rename_old_rdn_flag(cli_runner, mock_ldap, monkeypatch, flags, expected):
    # MOCK_SYNC does not model deleteoldrdn, so check what is sent to ldap3
    _, conn = mock_ldap
    calls = []
    original = conn.modify_dn

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(conn, "modify_dn", spy)
    result = cli_runner.invoke(cli, ["rename", HOST, JDOE, "cn=johnd", *flags])
    assert result.exit_code == 0, result.output
    assert calls[0]["delete_old_dn"] is expected
    assert read_entry(conn, f"cn=johnd,ou=people,{BASE_DN}") is not None


def test_recursive_delete_asks_for_confirmation(cli_runner, mock_ldap):
    _, conn = mock_ldap
    people = f"ou=people,{BASE_DN}"
    result = cli_runner.invoke(
        cli, ["delete", HOST, people, "--recursive"], input="n\n"
    )
    assert result.exit_code != 0
    assert read_entry(conn, people) is not None

    result = cli_runner.invoke(cli, ["delete", HOST, people, "--recursive", "--yes"])
    assert result.exit_code == 0, result.output
    assert read_entry(conn, people) is None
    assert read_entry(conn, JDOE) is None


# --- group-level flags --------------------------------------------------------


@pytest.mark.parametrize(
    "shell, expected",
    [
        ("/bin/bash", 'eval "$(_LDAPIE_COMPLETE=bash_source ldapie)"'),
        ("/bin/zsh", 'eval "$(_LDAPIE_COMPLETE=zsh_source ldapie)"'),
        ("/usr/bin/fish", "_LDAPIE_COMPLETE=fish_source ldapie | source"),
    ],
)
def test_show_completion(cli_runner, monkeypatch, shell, expected):
    monkeypatch.setenv("SHELL", shell)
    result = cli_runner.invoke(cli, ["--show-completion"])
    assert result.exit_code == 0, result.output
    assert expected in result.output


def test_install_completion_fish(cli_runner, monkeypatch, isolated_home):
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    result = cli_runner.invoke(cli, ["--install-completion"])
    assert result.exit_code == 0, result.output
    target = isolated_home / ".config" / "fish" / "completions" / "ldapie.fish"
    assert "complete" in target.read_text()


def test_install_completion_zsh(cli_runner, monkeypatch, isolated_home):
    monkeypatch.setenv("SHELL", "/bin/zsh")
    result = cli_runner.invoke(cli, ["--install-completion"])
    assert result.exit_code == 0, result.output
    script = (isolated_home / ".zsh" / "completion" / "_ldapie").read_text()
    assert script.startswith("#compdef ldapie")
    assert "fpath=(~/.zsh/completion $fpath)" in (isolated_home / ".zshrc").read_text()

    # A second run must not append the rc snippet again
    cli_runner.invoke(cli, ["--install-completion"])
    assert (isolated_home / ".zshrc").read_text().count("# LDAPie completion") == 1


def test_demo_flag_runs_demo(cli_runner, monkeypatch):
    import ldapie.demo

    called = []
    monkeypatch.setattr(ldapie.demo, "run_demo", lambda: called.append(True))
    result = cli_runner.invoke(cli, ["--demo"])
    assert result.exit_code == 0, result.output
    assert called == [True]


def test_no_arguments_shows_help(cli_runner):
    result = cli_runner.invoke(cli, [])
    assert "Usage" in result.output


# --- security -------------------------------------------------------------------


def test_debug_output_redacts_password(cli_runner, mock_ldap):
    result = cli_runner.invoke(
        cli,
        ["--debug", "search", HOST, BASE_DN, "(cn=jdoe)", "-u", "cn=x", "-p", "S3cret"],
    )
    assert result.exit_code == 0, result.output
    assert "S3cret" not in result.output


class _FakeConnection:
    instances: list = []

    def __init__(self, server, **kwargs):
        self.kwargs = kwargs
        self.start_tls_called = False
        _FakeConnection.instances.append(self)

    def start_tls(self, *args, **kwargs):
        self.start_tls_called = True


def test_starttls_runs_before_bind(monkeypatch):
    _FakeConnection.instances = []
    monkeypatch.setattr(ldapie_module, "Connection", _FakeConnection)
    LdapConfig(
        host=HOST, username="cn=admin", password="pw", starttls=True
    ).get_connection()
    (conn,) = _FakeConnection.instances
    assert conn.kwargs["auto_bind"] == AUTO_BIND_TLS_BEFORE_BIND
    assert not conn.start_tls_called


def test_anonymous_starttls_runs_before_bind(monkeypatch):
    _FakeConnection.instances = []
    monkeypatch.setattr(ldapie_module, "Connection", _FakeConnection)
    LdapConfig(host=HOST, starttls=True).get_connection()
    (conn,) = _FakeConnection.instances
    assert conn.kwargs["auto_bind"] == AUTO_BIND_TLS_BEFORE_BIND


# --- other read commands ---------------------------------------------------


def test_compare_entries(cli_runner, mock_ldap):
    result = cli_runner.invoke(
        cli,
        [
            "compare",
            HOST,
            JDOE,
            f"cn=jsmith,ou=people,{BASE_DN}",
            "-a",
            "SN",
            "-a",
            "objectClass",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Different attributes: 1" in result.output
    assert "Equal attributes: 1" in result.output


def test_info_rich_and_json(cli_runner, mock_ldap):
    result = cli_runner.invoke(cli, ["info", HOST])
    assert result.exit_code == 0, result.output
    assert "LDAP Simple Paged Results" in result.output

    result = cli_runner.invoke(cli, ["info", HOST, "--json"])
    assert result.exit_code == 0, result.output
    info = json.loads(result.stdout)
    assert "o=test" in info["naming_contexts"]


def test_search_tree_and_csv(cli_runner, mock_ldap):
    result = cli_runner.invoke(cli, ["search", HOST, BASE_DN, "--tree", "-a", "cn"])
    assert result.exit_code == 0, result.output
    assert "ou=people" in result.stdout
    assert "cn=jdoe" in result.stdout

    result = cli_runner.invoke(
        cli, ["search", HOST, BASE_DN, "(cn=*)", "--csv", "-a", "cn", "-a", "sn"]
    )
    assert result.exit_code == 0, result.output
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "cn,dn,sn"
    assert len(lines) == 4


def test_rich_output_escapes_markup_in_values(cli_runner, mock_ldap):
    _, conn = mock_ldap
    conn.strategy.add_entry(
        f"cn=br,ou=people,{BASE_DN}",
        {"objectClass": ["person"], "cn": "br", "sn": "[/bold] [red]x"},
    )
    result = cli_runner.invoke(cli, ["search", HOST, BASE_DN, "(cn=br)"])
    assert result.exit_code == 0, result.output
    assert "[/bold] [red]x" in result.stdout


def test_demo_runs_end_to_end(monkeypatch, capsys):
    from ldapie.demo import tour

    monkeypatch.setattr(tour.time, "sleep", lambda seconds: None)
    tour.run_demo()
    output = capsys.readouterr().out
    assert "Mock LDAP Server" in output
    assert "Error" not in output

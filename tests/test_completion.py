#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for tab completion and query history in the LDAPie interactive shell.
"""

import os
import stat

from ldapie.tab_completion import QueryHistory, TabCompletion


def test_tab_completion_uses_history():
    query_history = QueryHistory()
    query_history.add_search("(objectClass=person)")
    query_history.add_search("(uid=admin)")
    query_history.add_base("dc=example,dc=com")
    query_history.add_host("ldap.example.com")
    completer = TabCompletion(query_history)

    assert completer.get_commands("s") == ["search", "schema", "suggest"]
    assert completer.get_search_filters_completion("(obj") == ["(objectClass=person)"]
    assert completer.get_base_dns_completion("dc=") == ["dc=example,dc=com"]
    assert completer.get_hosts_completion("ldap") == ["ldap.example.com"]


def test_connect_completion_offers_tls_flags():
    completer = TabCompletion(QueryHistory())
    options = completer.complete_connect("--", "connect host --", 13, 15)
    assert options == ["--ssl", "--starttls", "--no-verify"]


def test_query_history_round_trip_and_permissions(isolated_home):
    query_history = QueryHistory()
    for search in ("(objectClass=person)", "(uid=admin)", "(objectClass=person)"):
        query_history.add_search(search)
    query_history.add_host("localhost")

    # Re-adding moves an item to the end instead of duplicating it
    assert query_history.get_searches() == ["(uid=admin)", "(objectClass=person)"]

    reloaded = QueryHistory()
    assert reloaded.get_searches() == ["(uid=admin)", "(objectClass=person)"]
    assert reloaded.get_hosts() == ["localhost"]

    path = os.path.join(str(isolated_home), ".ldapie_query_history.json")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_query_history_ignores_corrupt_file(isolated_home):
    path = os.path.join(str(isolated_home), ".ldapie_query_history.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write('["not", "a", "mapping"]')
    assert QueryHistory().get_searches() == []


def test_query_history_keeps_last_twenty():
    query_history = QueryHistory()
    for i in range(25):
        query_history.add_base(f"ou={i},dc=example,dc=com")
    bases = query_history.get_bases()
    assert len(bases) == 20
    assert bases[-1] == "ou=24,dc=example,dc=com"

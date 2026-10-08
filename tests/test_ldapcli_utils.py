#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for LDAPie utility functions
"""

import ldap3
import pytest
from ldap3 import BASE

from ldapie.entry_operations import delete_entry, list_subtree
from ldapie.utils import (
    parse_modification_attributes,
    validate_dn,
    validate_search_filter,
)

BASE_DN = "dc=example,dc=com"


def test_parse_modification_attributes_builds_ldap3_changes():
    changes = parse_modification_attributes(
        ["mail=a@example.com", "mail=b@example.com"],
        ["title=New Title"],
        ["description", "mail=old@example.com"],
    )
    assert changes == {
        "mail": [
            (ldap3.MODIFY_ADD, ["a@example.com", "b@example.com"]),
            (ldap3.MODIFY_DELETE, ["old@example.com"]),
        ],
        "title": [(ldap3.MODIFY_REPLACE, ["New Title"])],
        "description": [(ldap3.MODIFY_DELETE, [])],
    }


def test_parse_modification_attributes_keeps_equals_in_values():
    changes = parse_modification_attributes(None, ["seeAlso=cn=x,dc=y"], None)
    assert changes == {"seeAlso": [(ldap3.MODIFY_REPLACE, ["cn=x,dc=y"])]}


def test_parse_modification_attributes_bare_replace_clears_attribute():
    changes = parse_modification_attributes(None, ["description"], None)
    assert changes == {"description": [(ldap3.MODIFY_REPLACE, [])]}


@pytest.mark.parametrize("bad", [["mail"], ["=value"]])
def test_parse_modification_attributes_rejects_add_without_value(bad):
    with pytest.raises(ValueError):
        parse_modification_attributes(bad, None, None)


def test_parse_modification_attributes_empty():
    assert parse_modification_attributes(None, None, None) == {}


@pytest.mark.parametrize(
    "ldap_filter",
    [
        "(cn=user)",
        "(objectClass=*)",
        "(&(cn=user)(sn=Smith))",
        "(|(cn=user)(cn=admin))",
        "(!(cn=user))",
        "(cn>=A)",
        "(cn<=Z)",
        "(cn~=user)",
        "(&(objectClass=person)(|(cn=user)(mail=user@*)))",
    ],
)
def test_validate_search_filter_valid(ldap_filter):
    assert validate_search_filter(ldap_filter)


@pytest.mark.parametrize("ldap_filter", ["", "cn=user", "(cn=user", "()", "(&)"])
def test_validate_search_filter_invalid(ldap_filter):
    with pytest.raises(ValueError):
        validate_search_filter(ldap_filter)


@pytest.mark.parametrize(
    "dn",
    ["cn=user,dc=example,dc=com", "ou=people,dc=example,dc=com", "uid=admin,ou=system"],
)
def test_validate_dn_valid(dn):
    assert validate_dn(dn)


@pytest.mark.parametrize("dn", ["", "   "])
def test_validate_dn_invalid(dn):
    with pytest.raises(ValueError):
        validate_dn(dn)


def _exists(conn, dn):
    try:
        conn.search(dn, "(objectClass=*)", BASE, attributes=[])
    except ldap3.core.exceptions.LDAPNoSuchObjectResult:
        return False
    return bool(conn.entries)


def test_delete_entry_single(ldap_server):
    _, conn = ldap_server
    jdoe = f"cn=jdoe,ou=people,{BASE_DN}"
    assert delete_entry(conn, jdoe) == 1
    assert not _exists(conn, jdoe)


def test_list_subtree_puts_children_first_even_with_escaped_commas(ldap_server):
    _, conn = ldap_server
    parent = f"ou=Doe\\, John,ou=people,{BASE_DN}"
    child = f"cn=x,{parent}"
    conn.strategy.add_entry(
        parent, {"objectClass": ["organizationalUnit"], "ou": "Doe, John"}
    )
    conn.strategy.add_entry(child, {"objectClass": ["person"], "cn": "x", "sn": "x"})

    dns = list_subtree(conn, f"ou=people,{BASE_DN}")
    assert dns.index(child) < dns.index(parent)
    assert dns[-1] == f"ou=people,{BASE_DN}"


def test_delete_entry_recursive(ldap_server):
    _, conn = ldap_server
    people = f"ou=people,{BASE_DN}"
    assert delete_entry(conn, people, recursive=True) == 3
    assert not _exists(conn, people)
    assert _exists(conn, BASE_DN)

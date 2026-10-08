#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the paged search loop.

MOCK_SYNC does not implement the paged results control, so a fake connection
hands out numbered entries page by page and records what was asked of it.
"""

import pytest
from ldap3 import SUBTREE

from ldapie.search import PAGED_RESULTS_OID, iter_paged_search, paged_search


class FakeConnection:
    def __init__(self, total):
        self.total = total
        self.calls = []
        self.entries = []
        self.result = {}

    def search(self, base_dn, filter_query, **kwargs):
        size = kwargs["paged_size"]
        start = int(kwargs["paged_cookie"] or 0)
        self.calls.append((size, kwargs["paged_cookie"]))
        end = min(start + size, self.total)
        self.entries = [f"entry{i}" for i in range(start, end)]
        cookie = str(end) if end < self.total else b""
        self.result = {"controls": {PAGED_RESULTS_OID: {"value": {"cookie": cookie}}}}


def search(conn, page_size, limit=None):
    return list(
        iter_paged_search(conn, "dc=x", "(a=*)", SUBTREE, ["cn"], page_size, limit)
    )


def test_pages_follow_the_cookie_until_the_server_runs_out():
    conn = FakeConnection(total=5)
    assert paged_search(conn, "dc=x", "(a=*)", SUBTREE, ["cn"], 2) == [
        f"entry{i}" for i in range(5)
    ]
    assert conn.calls == [(2, None), (2, "2"), (2, "4")]


def test_limit_shrinks_the_last_page_and_stops():
    conn = FakeConnection(total=10)
    assert search(conn, page_size=4, limit=6) == [f"entry{i}" for i in range(6)]
    assert [size for size, _ in conn.calls] == [4, 2]


def test_limit_smaller_than_a_page_requests_only_that_many():
    conn = FakeConnection(total=1000)
    assert search(conn, page_size=500, limit=5) == [f"entry{i}" for i in range(5)]
    assert conn.calls == [(5, None)]


def test_zero_limit_means_no_limit():
    conn = FakeConnection(total=3)
    assert len(search(conn, page_size=2, limit=0)) == 3


def test_entries_are_yielded_before_the_next_page_is_fetched():
    conn = FakeConnection(total=4)
    results = iter_paged_search(conn, "dc=x", "(a=*)", SUBTREE, ["cn"], 2)
    assert next(results) == "entry0"
    assert len(conn.calls) == 1
    assert next(results) == "entry1"
    assert next(results) == "entry2"
    assert len(conn.calls) == 2


def test_page_size_must_be_positive():
    with pytest.raises(ValueError, match="page_size"):
        search(FakeConnection(total=1), page_size=0)


def test_negative_limit_is_rejected():
    with pytest.raises(ValueError, match="limit"):
        search(FakeConnection(total=1), page_size=2, limit=-1)


class StuckConnection(FakeConnection):
    """A hostile server: no entries, but always the same non-empty cookie."""

    def search(self, base_dn, filter_query, **kwargs):
        self.calls.append((kwargs["paged_size"], kwargs["paged_cookie"]))
        self.entries = []
        self.result = {"controls": {PAGED_RESULTS_OID: {"value": {"cookie": "stuck"}}}}


def test_empty_page_with_an_unchanged_cookie_ends_the_loop():
    conn = StuckConnection(total=0)
    assert search(conn, page_size=2) == []
    # One retry with the new cookie, then stop: no progress is being made
    assert len(conn.calls) == 2

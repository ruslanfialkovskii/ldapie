#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the output guards: hostile attribute names and atomic file writes.
"""

import os

import pytest

from ldapie.output import _atomic_write, ldif_lines, output_csv


class _Attr:
    def __init__(self, values):
        self.values = values
        self.raw_values = [v.encode("utf-8") for v in values]


class _Entry:
    def __init__(self, dn, attrs):
        self.entry_dn = dn
        self._attrs = attrs
        self.entry_attributes = list(attrs)

    def __getitem__(self, name):
        return _Attr(self._attrs[name])


HOSTILE = _Entry(
    "cn=x,dc=example,dc=com",
    {"=cmd()": ["v"], "bad\x1b[2Jname": ["w"], "cn": ["x"]},
)


def test_csv_header_names_are_sanitized_and_formula_guarded(capsys):
    output_csv([HOSTILE])
    header, row = capsys.readouterr().out.strip().splitlines()
    assert header == "'=cmd(),bad\\x1b[2Jname,cn,dn"
    assert "\x1b" not in row
    assert row.split(",")[0] == "v"


def test_ldif_skips_attributes_with_invalid_names():
    lines = list(ldif_lines([HOSTILE]))
    assert "cn: x" in lines
    comments = [line for line in lines if line.startswith("# skipped")]
    assert len(comments) == 2
    assert "=cmd()" in comments[0]
    assert "bad\\x1b[2Jname" in comments[1]
    assert not any(line.startswith(("=cmd", "bad")) for line in lines)
    assert "\x1b" not in "\n".join(lines)


def test_atomic_write_replaces_the_file_only_on_success(tmp_path):
    out_dir = tmp_path / "exports"
    out_dir.mkdir()
    target = out_dir / "out.txt"
    target.write_text("old")

    with pytest.raises(RuntimeError):
        with _atomic_write(str(target)) as f:
            f.write("partial")
            raise RuntimeError("boom")
    assert target.read_text() == "old"
    assert [p.name for p in out_dir.iterdir()] == ["out.txt"]

    with _atomic_write(str(target)) as f:
        f.write("new")
    assert target.read_text() == "new"
    assert [p.name for p in out_dir.iterdir()] == ["out.txt"]
    assert os.stat(target).st_mode & 0o777 == 0o600

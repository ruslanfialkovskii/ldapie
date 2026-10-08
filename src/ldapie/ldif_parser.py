#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDIF parser for LDAPie imports.

Parses LDIF content records (RFC 2849): the optional ``version: 1`` line,
comments, folded lines, ``::`` base64 values and ``changetype: add``
records. Other change types and ``:<`` URL values are rejected with an
error that names the line, so an import never applies a partial guess.
"""

import base64
import binascii
from typing import Dict, Iterator, List, Tuple, Union

Value = Union[str, bytes]
Record = Tuple[str, Dict[str, List[Value]]]


def _logical_lines(text: str) -> Iterator[Tuple[int, str]]:
    """Yield (line number, line) with folded lines joined and comments removed.

    A blank line is yielded as ``""`` to mark the end of a record.
    """
    current = None
    start = 0
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(" ") and current is not None:
            current += line[1:]
            continue
        if current is not None and not current.startswith("#"):
            yield start, current
        current, start = line, number
        if not line:
            yield number, ""
            current = None
    if current is not None and not current.startswith("#"):
        yield start, current


def _parse_line(number: int, line: str) -> Tuple[str, Value]:
    """Split an 'attr: value' / 'attr:: base64' line into name and value."""
    name, sep, rest = line.partition(":")
    if not sep or not name or " " in name:
        raise ValueError(f"line {number}: expected 'attribute: value', got {line!r}")

    if rest.startswith("<"):
        raise ValueError(
            f"line {number}: URL values (':<') are not supported for '{name}'"
        )
    if not rest.startswith(":"):
        return name, rest.lstrip(" ")

    try:
        raw = base64.b64decode(rest[1:].strip(), validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"line {number}: invalid base64 value for '{name}'") from e
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return name, raw
    # Valid UTF-8 can still be binary data (e.g. b"\x00\x01")
    if any(ord(ch) < 0x20 and ch not in "\t\r\n" for ch in text):
        return name, raw
    return name, text


def parse_ldif(text: str) -> List[Record]:
    """Parse LDIF text into a list of ``(dn, {attribute: [values]})`` records.

    Text values are returned as ``str``; base64 values that are not valid
    UTF-8 (photos, certificates) are returned as ``bytes``.

    Raises:
        ValueError: For malformed input or unsupported LDIF features.
    """
    records: List[Record] = []
    dn = None
    attrs: Dict[str, List[Value]] = {}
    seen_content = False

    for number, line in _logical_lines(text):
        if not line:
            if dn is not None:
                records.append((dn, attrs))
            dn, attrs = None, {}
            continue

        name, value = _parse_line(number, line)
        lower = name.lower()

        if dn is None:
            if lower == "version" and not seen_content:
                if value != "1":
                    raise ValueError(
                        f"line {number}: unsupported LDIF version {value!r}"
                    )
                seen_content = True
                continue
            if lower != "dn":
                raise ValueError(f"line {number}: record must start with 'dn:'")
            if isinstance(value, bytes):
                raise ValueError(f"line {number}: DN is not valid UTF-8")
            dn, seen_content = value, True
            continue

        if lower == "dn":
            raise ValueError(f"line {number}: second 'dn:' in one record")
        if lower == "control":
            raise ValueError(f"line {number}: LDIF controls are not supported")
        if lower == "changetype":
            if value != "add":
                raise ValueError(
                    f"line {number}: changetype {value!r} is not supported; "
                    "only entries to add can be imported"
                )
            continue
        attrs.setdefault(name, []).append(value)

    if dn is not None:
        records.append((dn, attrs))
    return records

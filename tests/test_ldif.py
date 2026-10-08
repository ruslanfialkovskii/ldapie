#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the LDIF parser and the LDIF writer.
"""

import base64

import pytest

from ldapie.ldif_parser import parse_ldif
from ldapie.output import ldif_lines


def test_parses_records_with_version_comments_and_folding():
    text = (
        "version: 1\n"
        "# a comment that is\n"
        "  folded\n"
        "dn: cn=a,dc=example,dc=com\n"
        "objectClass: top\n"
        "objectClass: person\n"
        "cn: a\n"
        "description: first part\n"
        "  second part\n"
        "\n"
        "\n"
        "dn: cn=b,dc=example,dc=com\n"
        "cn: b\n"
    )
    records = parse_ldif(text)
    assert records == [
        (
            "cn=a,dc=example,dc=com",
            {
                "objectClass": ["top", "person"],
                "cn": ["a"],
                "description": ["first part second part"],
            },
        ),
        ("cn=b,dc=example,dc=com", {"cn": ["b"]}),
    ]


def test_base64_values_keep_binary_and_decode_text():
    binary = b"\x00\xff\x10"
    text_value = "Jörg"
    ldif = (
        f"dn:: {base64.b64encode('cn=Jörg,dc=example,dc=com'.encode()).decode()}\n"
        f"cn:: {base64.b64encode(text_value.encode()).decode()}\n"
        f"jpegPhoto:: {base64.b64encode(binary).decode()}\n"
    )
    [(dn, attrs)] = parse_ldif(ldif)
    assert dn == "cn=Jörg,dc=example,dc=com"
    assert attrs["cn"] == ["Jörg"]
    assert attrs["jpegPhoto"] == [binary]


def test_attribute_options_and_crlf_line_endings():
    ldif = "dn: cn=a,dc=x\r\nuserCertificate;binary:: AAE=\r\ncn: a\r\n"
    [(_, attrs)] = parse_ldif(ldif)
    assert attrs["userCertificate;binary"] == [b"\x00\x01"]


def test_changetype_add_is_accepted():
    [(dn, attrs)] = parse_ldif("dn: cn=a,dc=x\nchangetype: add\ncn: a\n")
    assert dn == "cn=a,dc=x"
    assert attrs == {"cn": ["a"]}


@pytest.mark.parametrize(
    "ldif, message",
    [
        ("dn: cn=a,dc=x\nchangetype: modify\nreplace: cn\ncn: b\n-\n", "changetype"),
        ("dn: cn=a,dc=x\njpegPhoto:< file:///etc/passwd\n", "URL"),
        ("cn: a\n", "dn"),
        ("dn: cn=a,dc=x\nno separator here\n", "line 2"),
        ("dn: cn=a,dc=x\ncn:: !!!notbase64\n", "base64"),
    ],
)
def test_rejects_unsupported_or_invalid_input(ldif, message):
    with pytest.raises(ValueError, match=message):
        parse_ldif(ldif)


class _Attr:
    def __init__(self, raw_values):
        self.raw_values = raw_values


class _Entry:
    def __init__(self, dn, attrs):
        self.entry_dn = dn
        self._attrs = attrs
        self.entry_attributes = list(attrs)

    def __getitem__(self, name):
        return _Attr(self._attrs[name])


def test_writer_round_trips_through_parser():
    entry = _Entry(
        "cn=Jörg,dc=example,dc=com",
        {
            "cn": [b"J\xc3\xb6rg"],
            "description": [b" leading space", b"plain"],
            "jpegPhoto": [bytes(range(256))],
        },
    )
    text = "\n".join(ldif_lines([entry]))
    assert "dn:: " in text
    [(dn, attrs)] = parse_ldif(text)
    assert dn == "cn=Jörg,dc=example,dc=com"
    assert attrs["cn"] == ["Jörg"]
    assert attrs["description"] == [" leading space", "plain"]
    assert attrs["jpegPhoto"] == [bytes(range(256))]

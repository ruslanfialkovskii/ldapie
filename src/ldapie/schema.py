#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema and server information functions for LDAPie.
"""

import json
from typing import Any, Dict, List, Optional

from ldap3 import Server
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table


def _as_list(value: Any) -> List[Any]:
    """ldap3 returns schema and DSA fields as a list, a scalar, or None."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _text(value: Any, empty: str = "") -> str:
    """Join a schema field into escaped display text."""
    items = [str(v) for v in _as_list(value)]
    return escape(", ".join(items)) if items else empty


def _oid_label(oid: Any) -> str:
    """Name a control/extension; ldap3 decodes them to (oid, kind, name, doc)."""
    if isinstance(oid, tuple) and len(oid) >= 3 and oid[2]:
        return f"{oid[2]} ({oid[0]})"
    if isinstance(oid, tuple):
        return str(oid[0])
    return str(oid)


def _server_info_dict(server: Server) -> Dict[str, Any]:
    info = server.info
    return {
        "vendor": _as_list(info.vendor_name),
        "version": _as_list(info.vendor_version),
        "ldap_versions": [str(v) for v in _as_list(info.supported_ldap_versions)],
        "supported_controls": [
            _oid_label(oid) for oid in _as_list(info.supported_controls)
        ],
        "supported_extensions": [
            _oid_label(oid) for oid in _as_list(info.supported_extensions)
        ],
        "naming_contexts": [str(nc) for nc in _as_list(info.naming_contexts)],
    }


def output_server_info_rich(server: Server, console: Console) -> None:
    """
    Display server information in rich text format.

    Shows details about the LDAP server including vendor, version,
    supported controls, extensions, and naming contexts.

    Args:
        server: LDAP server object
        console: Rich Console object for output
    """
    if not server.info:
        console.print("[warning]No server info available.[/warning]")
        return

    info = _server_info_dict(server)
    table = Table(title="LDAP Server Information", box=box.ROUNDED, show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    rows = [
        ("Vendor", ", ".join(map(str, info["vendor"]))),
        ("Version", ", ".join(map(str, info["version"]))),
        ("LDAP Versions", ", ".join(info["ldap_versions"])),
        ("Supported Controls", "\n".join(info["supported_controls"])),
        ("Supported Extensions", "\n".join(info["supported_extensions"])),
        ("Naming Contexts", "\n".join(info["naming_contexts"])),
    ]
    for label, value in rows:
        table.add_row(label, escape(value) if value else "None")

    console.print(table)


def output_server_info_json(server: Server, console: Console) -> None:
    """
    Display server information in JSON format.

    Outputs LDAP server information as JSON, including vendor, version,
    supported controls, extensions, and naming contexts.

    Args:
        server: LDAP server object
        console: Rich Console object for warnings
    """
    if not server.info:
        console.print("[warning]No server info available.[/warning]")
        return

    print(json.dumps(_server_info_dict(server), indent=2, default=str))


def show_schema(
    server: Server,
    object_class: Optional[str],
    attribute: Optional[str],
    console: Console,
) -> None:
    """
    Display schema information from the server.

    Shows LDAP schema information for object classes or attributes.
    If no specific object class or attribute is provided, lists all object classes.

    Args:
        server: LDAP server object
        object_class: Optional specific object class to show
        attribute: Optional specific attribute to show
        console: Rich Console object for output

    Example:
        >>> show_schema(server, "person", None, console)  # Show info for person class
        >>> show_schema(server, None, "cn", console)      # Show info for cn attribute
        >>> show_schema(server, None, None, console)      # List all object classes

    Note:
        Cannot specify both object_class and attribute at the same time.
    """
    if not server.schema:
        console.print("[warning]No schema information available.[/warning]")
        return

    if object_class and attribute:
        console.print("[error]Cannot specify both object class and attribute.[/error]")
        return

    if object_class:
        oc_info = server.schema.object_classes.get(object_class)
        if not oc_info:
            console.print(
                f"[error]Object class '{escape(object_class)}' not found in schema.[/error]"
            )
            return

        table = Table(title=f"Object Class: {escape(object_class)}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")

        table.add_row("Name", _text(oc_info.name))
        table.add_row("OID", _text(oc_info.oid))
        table.add_row("Description", _text(oc_info.description))
        table.add_row("Type", _text(oc_info.kind))
        for label, values in (
            ("Required Attributes", oc_info.must_contain),
            ("Optional Attributes", oc_info.may_contain),
            ("Parent Classes", oc_info.superior),
        ):
            items = sorted(str(v) for v in _as_list(values))
            table.add_row(label, escape("\n".join(items)) if items else "None")

        console.print(table)

    elif attribute:
        attr_info = server.schema.attribute_types.get(attribute)
        if not attr_info:
            console.print(
                f"[error]Attribute '{escape(attribute)}' not found in schema.[/error]"
            )
            return

        table = Table(title=f"Attribute: {escape(attribute)}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")

        table.add_row("Name", _text(attr_info.name))
        table.add_row("OID", _text(attr_info.oid))
        table.add_row("Description", _text(attr_info.description))
        table.add_row("Syntax", _text(attr_info.syntax))
        table.add_row("Single Value", "Yes" if attr_info.single_value else "No")
        for label, value in (
            ("Parent Attribute", attr_info.superior),
            ("Equality Match", attr_info.equality),
            ("Ordering", attr_info.ordering),
            ("Substring Match", attr_info.substring),
        ):
            if value:
                table.add_row(label, _text(value))

        console.print(table)

    else:
        table = Table(title="Object Classes", box=box.ROUNDED)
        table.add_column("Name", style="ldap.attr")
        table.add_column("Description", style="ldap.value")

        for name, oc_info in sorted(server.schema.object_classes.items()):
            table.add_row(escape(name), _text(oc_info.description))

        console.print(table)

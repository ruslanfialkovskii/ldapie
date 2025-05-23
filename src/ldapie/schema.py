#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema and server information functions for LDAPie.
"""

import json
from typing import Optional, Any
import ldap3 # Keep ldap3 import for KNOWN_CONTROLS and KNOWN_EXTENSIONS if they exist
from ldap3 import Server, Connection # Removed unused Connection import from here, will be used by functions
from rich.console import Console
from rich.table import Table
from rich import box

# Attempt to import KNOWN_CONTROLS and KNOWN_EXTENSIONS safely
try:
    from ldap3.protocol.rfc4511 import KNOWN_CONTROLS, KNOWN_EXTENSIONS
except ImportError:
    KNOWN_CONTROLS = {}
    KNOWN_EXTENSIONS = {}


def output_server_info_rich(server: Server, console: Console) -> None: # Removed unused conn argument
    """
    Display server information in rich text format.
    
    Shows details about the LDAP server including vendor, version,
    supported controls, extensions, and naming contexts.
    
    Args:
        server: LDAP server object
        # conn: LDAP connection object # Removed
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> output_server_info_rich(server, console)
    """
    # For testing purposes, check if we have a mocked _info attribute
    server_info = getattr(server, "_info", server.info)
    
    if not server_info:
        console.print("[yellow]No server info available.[/yellow]")
        return
        
    # Create a table for server info
    table = Table(title="LDAP Server Information", box=box.ROUNDED, show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Add server properties
    if hasattr(server_info, "vendor_name"):
        table.add_row("Vendor", str(server_info.vendor_name))
    if hasattr(server_info, "vendor_version"):
        table.add_row("Version", str(server_info.vendor_version))
    
    # Add supported LDAP protocol versions
    if hasattr(server_info, "supported_ldap_versions"):
        # Convert list to string before adding to table
        versions_str = ", ".join(str(v) for v in server_info.supported_ldap_versions)
        table.add_row("LDAP Versions", versions_str)
    
    # Add supported controls
    if hasattr(server_info, "supported_controls"):
        controls = []
        for oid in server_info.supported_controls:
            control_name = KNOWN_CONTROLS.get(oid, oid) # Use safely imported KNOWN_CONTROLS
            controls.append(f"{control_name}")
        # Ensure controls is a string, not a list
        controls_str = "\n".join(controls) if controls else "None"
        table.add_row("Supported Controls", controls_str)
    
    # Add supported extensions
    if hasattr(server_info, "supported_extensions"):
        exts = []
        for oid in server_info.supported_extensions:
            ext_name = KNOWN_EXTENSIONS.get(oid, oid) # Use safely imported KNOWN_EXTENSIONS
            exts.append(f"{ext_name}")
        # Ensure extensions is a string, not a list
        exts_str = "\n".join(exts) if exts else "None"
        table.add_row("Supported Extensions", exts_str)
    
    # Add naming contexts
    if hasattr(server_info, "naming_contexts"):
        # Convert list to string before adding to table
        contexts_str = "\n".join(str(ctx) for ctx in server_info.naming_contexts) if server_info.naming_contexts else "None"
        table.add_row("Naming Contexts", contexts_str)
    
    console.print(table)

def output_server_info_json(server: Server, console: Console) -> None: # Removed unused conn argument
    """
    Display server information in JSON format.
    
    Outputs LDAP server information as JSON, including vendor, version,
    supported controls, extensions, and naming contexts.
    
    Args:
        server: LDAP server object
        # conn: LDAP connection object # Removed
        console: Rich Console object for output
    
    Returns:
        None
        
    Example:
        >>> output_server_info_json(server, console)
    """
    if not server.info:
        console.print("[warning]No server info available.[/warning]")
        return
        
    info = {}
    
    # Add server properties
    if hasattr(server.info, "vendor_name"):
        info["vendor"] = server.info.vendor_name
    if hasattr(server.info, "vendor_version"):
        info["version"] = server.info.vendor_version
    
    # Add supported LDAP protocol versions
    if hasattr(server.info, "supported_ldap_versions"):
        info["ldap_versions"] = server.info.supported_ldap_versions
        
    # Add supported controls
    if hasattr(server.info, "supported_controls"):
        info["supported_controls"] = {}
        for oid in server.info.supported_controls:
            control_name = KNOWN_CONTROLS.get(oid, oid) # Use safely imported KNOWN_CONTROLS
            info["supported_controls"][oid] = control_name
        
    # Add supported extensions
    if hasattr(server.info, "supported_extensions"):
        info["supported_extensions"] = {}
        for oid in server.info.supported_extensions:
            ext_name = KNOWN_EXTENSIONS.get(oid, oid) # Use safely imported KNOWN_EXTENSIONS
            info["supported_extensions"][oid] = ext_name
        
    # Add naming contexts
    if hasattr(server.info, "naming_contexts"):
        info["naming_contexts"] = server.info.naming_contexts
    
    print(json.dumps(info, indent=2))

def show_schema(server: Server, object_class: Optional[str], attribute: Optional[str], console: Console) -> None:
    """
    Display schema information from the server.
    
    Shows LDAP schema information for object classes or attributes.
    If no specific object class or attribute is provided, lists all object classes.
    
    Args:
        server: LDAP server object
        object_class: Optional specific object class to show
        attribute: Optional specific attribute to show
        console: Rich Console object for output
    
    Returns:
        None
        
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
        # Show info about a specific object class
        oc_info = server.schema.object_classes.get(object_class.lower())
        if not oc_info:
            console.print(f"[error]Object class '{object_class}' not found in schema.[/error]")
            return
            
        table = Table(title=f"Object Class: {object_class}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")
        
        table.add_row("Name", oc_info.name)
        table.add_row("OID", oc_info.oid)
        table.add_row("Description", oc_info.description or "")
        table.add_row("Type", oc_info.type or "")
        
        if oc_info.must_contain:
            table.add_row("Required Attributes", "\n".join(sorted(oc_info.must_contain)))
        else:
            table.add_row("Required Attributes", "None")
            
        if oc_info.may_contain:
            table.add_row("Optional Attributes", "\n".join(sorted(oc_info.may_contain)))
        else:
            table.add_row("Optional Attributes", "None")
            
        if oc_info.superior:
            table.add_row("Parent Classes", "\n".join(sorted(oc_info.superior)))
        else:
            table.add_row("Parent Classes", "None")
            
        console.print(table)
        
    elif attribute:
        # Show info about a specific attribute
        attr_info = server.schema.attribute_types.get(attribute.lower())
        if not attr_info:
            console.print(f"[error]Attribute '{attribute}' not found in schema.[/error]")
            return
            
        table = Table(title=f"Attribute: {attribute}", box=box.ROUNDED)
        table.add_column("Property", style="ldap.attr")
        table.add_column("Value", style="ldap.value")
        
        table.add_row("Name", attr_info.name)
        table.add_row("OID", attr_info.oid)
        table.add_row("Description", attr_info.description or "")
        table.add_row("Syntax", attr_info.syntax or "")
        table.add_row("Single Value", "Yes" if attr_info.single_value else "No")
        
        if attr_info.equality:
            table.add_row("Equality Match", attr_info.equality)
        if attr_info.ordering:
            table.add_row("Ordering", attr_info.ordering)
        if attr_info.substring:
            table.add_row("Substring Match", attr_info.substring)
            
        console.print(table)
        
    else:
        # List all object classes
        table = Table(title="Object Classes", box=box.ROUNDED)
        table.add_column("Name", style="ldap.attr")
        table.add_column("Description", style="ldap.value")
        
        for name, oc_info in sorted(server.schema.object_classes.items()):
            table.add_row(name, oc_info.description or "")
            
        console.print(table)

def get_schema_info(conn: Connection, schema_type: str, name: Optional[str] = None) -> str: # conn is used here
    """
    Get schema information from LDAP server.
    
    Retrieves and formats schema information for object classes or attributes.
    
    Args:
        conn: LDAP connection object
        schema_type: Type of schema information to retrieve ("objectclasses" or "attributes")
        name: Optional specific name to get information about
        
    Returns:
        Formatted schema information as a string
        
    Example:
        >>> info = get_schema_info(conn, "objectclasses", "person")    
        >>> info = get_schema_info(conn, "attributes", "cn")
        >>> info = get_schema_info(conn, "objectclasses")  # All object classes
        
    Raises:
        ValueError: If schema_type is invalid
    """
    if not conn.server.schema:
        return "No schema information available"
            
    if schema_type.lower() == "objectclasses" or schema_type.lower() == "objectclass":
        if name:
            schema_obj = conn.server.schema.object_classes.get(name.lower())
            if not schema_obj:
                return f"Object class '{name}' not found in schema"
            return format_schema_output(schema_obj)
        else:
            return format_schema_output(conn.server.schema.object_classes)
    
    elif schema_type.lower() == "attributes" or schema_type.lower() == "attribute":
        if name:
            schema_attr = conn.server.schema.attribute_types.get(name.lower())
            if not schema_attr:
                return f"Attribute '{name}' not found in schema"
            return format_schema_output(schema_attr)
        else:
            return format_schema_output(conn.server.schema.attribute_types)
    
    raise ValueError("Invalid schema type. Use 'objectclasses' or 'attributes'")

def format_schema_output(schema_obj: Any) -> str:
    """
    Format schema object for display.
    
    Converts schema objects into a human-readable string representation.
    
    Args:
        schema_obj: Schema object or dictionary of schema objects
        
    Returns:
        Formatted string representation
        
    Example:
        >>> output = format_schema_output(server.schema.object_classes["person"])
    """
    if isinstance(schema_obj, dict):
        # Format a collection of schema objects
        output = []
        for name, obj in schema_obj.items():
            output.append(f"{name}: {obj.description or 'No description'}")
        return "\n".join(output)
    else:
        # Format a single schema object
        result = []
        for attr in dir(schema_obj):
            if not attr.startswith('_') and not callable(getattr(schema_obj, attr)):
                value = getattr(schema_obj, attr)
                if value is not None:
                    result.append(f"{attr}: {value}")
        return "\n".join(result)

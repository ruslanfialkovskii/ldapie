#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper utility functions for LDAPie.

This module contains general helper functions for password handling,
error handling, file operations, and other utility functionality.
"""

import os
import getpass
from typing import Optional, Any
from rich.console import Console


def safe_get_password(prompt: str = "Password: ") -> str:
    """
    Safely get a password from user input.
    
    Args:
        prompt: Prompt string to display
        
    Returns:
        Password string
    """
    try:
        return getpass.getpass(prompt)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        exit(1)
    except Exception as e:
        print(f"Error reading password: {e}")
        exit(1)


def handle_error_response(error: Exception, console: Console, debug: bool = False) -> None:
    """
    Handle and display error responses.
    
    Args:
        error: Exception that occurred
        console: Rich console for output
        debug: Whether to show debug information
    """
    if debug:
        import traceback
        console.print(f"[error]Error: {str(error)}[/error]")
        console.print("[dim]Full traceback:[/dim]")
        console.print(traceback.format_exc())
    else:
        console.print(f"[error]Error: {str(error)}[/error]")


def format_output_filename(filename: str, extension: str) -> str:
    """
    Format output filename with proper extension.
    
    Args:
        filename: Base filename
        extension: File extension (with or without dot)
        
    Returns:
        Formatted filename with extension
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    if filename.endswith(extension):
        return filename
    
    # Remove any existing extension and add the new one
    base_name = os.path.splitext(filename)[0]
    return base_name + extension


def validate_dn(dn: str) -> bool:
    """
    Validate a Distinguished Name.
    
    Args:
        dn: Distinguished Name string
        
    Returns:
        True if valid, False otherwise
    """
    if not dn or not isinstance(dn, str):
        return False
    
    # Basic validation - check for at least one = sign
    return '=' in dn and len(dn.strip()) > 0


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'output'
    
    return filename


def get_config_dir() -> str:
    """
    Get the configuration directory for LDAPie.
    
    Returns:
        Path to configuration directory
    """
    # Use XDG config directory if available, otherwise fall back to home
    config_dir = os.environ.get('XDG_CONFIG_HOME')
    if config_dir:
        return os.path.join(config_dir, 'ldapie')
    else:
        return os.path.join(os.path.expanduser('~'), '.config', 'ldapie')


def ensure_config_dir() -> str:
    """
    Ensure configuration directory exists and return its path.
    
    Returns:
        Path to configuration directory
    """
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def create_connection(ldap_uri: str, bind_dn: str | None = None, password: str | None = None, sasl_mechanism: str | None = None):
    """Creates an LDAP connection."""
    # Placeholder implementation
    raise NotImplementedError("create_connection is not yet implemented")

def safe_get_password(prompt: str = "Password: "):
    """Safely gets a password from the user."""
    # Placeholder implementation
    import getpass
    return getpass.getpass(prompt)

def handle_error_response(response, msg: str = "LDAP operation failed"):
    """Handles an error response from an LDAP operation."""
    # Placeholder implementation
    # This function would typically raise an exception or log an error
    print(f"Error: {msg} - {response}")
    raise RuntimeError(f"{msg} - {response}")

def parse_modification_attributes(add_attrs: list[str] | None, replace_attrs: list[str] | None, delete_attrs: list[str] | None) -> dict:
    """Parses modification attributes from command-line arguments."""
    mods = {}
    if add_attrs:
        for attr_val in add_attrs:
            parts = attr_val.split('=', 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ''
            # ldap3 expects list of values for an attribute modification
            current_mod = mods.get(attr, {'operation': ldap3.MODIFY_ADD, 'value': []})
            current_mod['value'].append(val)
            mods[attr] = current_mod
    if replace_attrs:
        for attr_val in replace_attrs:
            parts = attr_val.split('=', 1)
            attr = parts[0]
            val = parts[1] if len(parts) > 1 else ''
            mods[attr] = {'operation': ldap3.MODIFY_REPLACE, 'value': [val]}
    if delete_attrs:
        for attr_val in delete_attrs: # Assuming delete_attrs might contain attr=val or just attr
            attr = attr_val.split('=', 1)[0]
            # For delete, value can be specific or empty to delete all values
            # Placeholder: simple delete of attribute itself or specific values if provided
            if '=' in attr_val:
                _, val = attr_val.split('=', 1)
                mods[attr] = {'operation': ldap3.MODIFY_DELETE, 'value': [val]}
            else:
                mods[attr] = {'operation': ldap3.MODIFY_DELETE, 'value': []}
    return mods

def format_output_filename(basename: str, extension: str) -> str:
    """Formats an output filename, ensuring correct extension."""
    if basename.endswith(f".{extension}"):
        return basename
    # if basename contains a dot not at the end, and it's not the target extension, append target extension
    if '.' in basename and not basename.endswith('.'):
        return f"{basename}.{extension}"
    # if no extension or ends with a dot, just append
    return f"{basename}.{extension}"

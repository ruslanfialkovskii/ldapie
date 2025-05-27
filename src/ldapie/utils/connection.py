#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection utilities and error handling for LDAPie.

This module contains utilities for creating LDAP connections
and handling connection-related errors.
"""

import sys
import traceback
import functools
from typing import Optional, Callable
import click
from ldap3.core.exceptions import LDAPException, LDAPBindError
from rich.console import Console

# Import console from parent to avoid creating multiple instances
try:
    from .. import console
except ImportError:
    console = Console()


def handle_connection_error(func: Callable) -> Callable:
    """
    Decorator to handle LDAP connection errors.
    
    Catches LDAP exceptions that might occur during connection operations
    and displays user-friendly error messages.
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function that handles LDAP connection errors
        
    Example:
        >>> @handle_connection_error
        ... def my_ldap_function():
        ...     # LDAP operations
        ...     pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if we're in debug mode via click context
        ctx = click.get_current_context(silent=True)
        is_debug = False
        if ctx and hasattr(ctx, 'obj') and isinstance(ctx.obj, dict):
            is_debug = ctx.obj.get('DEBUG', False)
        
        # Get the command string for error tracking before entering try block
        func_name = func.__name__
        command_str = func_name.replace("_command", "")
        
        # Set up variables outside try block
        help_context_available = False
        help_context = None
        
        try:
            # Check if help context is available
            try:
                from ...interactive.help_context import HelpContext
                help_context = HelpContext()
                help_context_available = True
            except ImportError:
                help_context_available = False
                if is_debug:
                    console.print("[bold yellow]DEBUG[/bold yellow]: Could not import HelpContext.")
            
            # Debug mode: show function call details
            if is_debug:
                console.print(f"[bold blue]DEBUG[/bold blue]: Executing {func.__name__}")
                console.print(f"[bold blue]DEBUG[/bold blue]: Arguments: {args}")
                console.print(f"[bold blue]DEBUG[/bold blue]: Keyword arguments: {kwargs}")
            
            # Execute the function
            result = func(*args, **kwargs)
            
            if is_debug:
                console.print(f"[bold blue]DEBUG[/bold blue]: {func.__name__} completed successfully")
                
            return result
        except LDAPBindError as e:
            error_msg = f"Authentication failed: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Show stack trace in debug mode
            if is_debug:
                console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
                console.print(traceback.format_exc())
            
            # Record error in help context if available
            if help_context_available and help_context:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except LDAPException as e:
            error_msg = f"LDAP error: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Show stack trace in debug mode
            if is_debug:
                console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
                console.print(traceback.format_exc())
            
            # Record error in help context if available
            if help_context_available and help_context:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except (ValueError, TypeError, KeyError) as e:
            # Handle most common operation errors
            error_msg = f"Operation error ({type(e).__name__}): {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Show stack trace in debug mode
            if is_debug:
                console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
                console.print(traceback.format_exc())
            
            # Record error in help context if available
            if help_context_available and help_context:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except (OSError, IOError) as e:
            # Handle file operation errors
            error_msg = f"File operation error: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Show stack trace in debug mode
            if is_debug:
                console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
                console.print(traceback.format_exc())
            
            # Record error in help context if available
            if help_context_available and help_context:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
        except Exception as e:
            # This is our last resort fallback for unexpected errors
            error_msg = f"Unexpected error: {e}"
            console.print(f"[error]{error_msg}[/error]")
            
            # Show stack trace in debug mode
            if is_debug:
                console.print("[bold yellow]DEBUG: Stack trace[/bold yellow]")
                console.print(traceback.format_exc())
            
            # Record error in help context if available
            if help_context_available and help_context:
                help_context.add_error(command_str, error_msg)
                
            sys.exit(1)
    return wrapper


def create_connection(host: str, port: Optional[int] = None, use_ssl: bool = False, 
                     username: Optional[str] = None, password: Optional[str] = None):
    """
    Create an LDAP connection with the given parameters.
    
    Args:
        host: LDAP server hostname
        port: Port number (optional)
        use_ssl: Whether to use SSL/TLS
        username: Bind username (optional)
        password: Bind password (optional)
        
    Returns:
        Tuple of (server, connection) objects
        
    Raises:
        LDAPException: If connection fails
    """
    from ldap3 import Server, Connection, ALL
    
    # Determine port if not specified
    if port is None:
        port = 636 if use_ssl else 389
    
    # Create server object
    server = Server(host, port=port, use_ssl=use_ssl, get_info=ALL)
    
    # Create connection
    if username and password:
        conn = Connection(server, user=username, password=password, auto_bind=True)
    else:
        conn = Connection(server, auto_bind=True)
    
    return server, conn

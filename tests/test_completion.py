#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for tab completion and query history in LDAPie interactive shell
"""

import os
import sys
from rich.console import Console

# Add the src directory to the path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from ldapie.tab_completion import TabCompletion, QueryHistory
    from ldapie.shell_enhancements import enhance_shell
except ImportError:
    from src.ldapie.tab_completion import TabCompletion, QueryHistory
    from src.ldapie.shell_enhancements import enhance_shell

# Create a console for output
console = Console()

def test_tab_completion():
    """Test the tab completion functionality"""
    console.print("[bold]Testing Tab Completion[/bold]")
    console.rule()
    
    # Create a query history
    query_history = QueryHistory()
    query_history.add_search("(objectClass=person)")
    query_history.add_search("(uid=admin)")
    query_history.add_base("dc=example,dc=com")
    query_history.add_host("ldap.example.com")
    
    # Create a tab completer
    tab_completer = TabCompletion(query_history)
    
    # Test command completion
    commands = tab_completer.get_commands("s")
    console.print(f"Command completions for 's': {commands}")
    
    # Test search filter completion
    filters = tab_completer.get_search_filters_completion("(obj")
    console.print(f"Filter completions for '(obj': {filters}")
    
    # Test base DN completion
    dns = tab_completer.get_base_dns_completion("dc=")
    console.print(f"Base DN completions for 'dc=': {dns}")
    
    # Test host completion
    hosts = tab_completer.get_hosts_completion("ldap")
    console.print(f"Host completions for 'ldap': {hosts}")
    
    console.print("[green]✓ Tab completion tests completed[/green]")
    console.print()

def test_query_history():
    """Test the query history functionality"""
    console.print("[bold]Testing Query History[/bold]")
    console.rule()
    
    # Create a query history
    query_history = QueryHistory()
    
    # Add some items
    query_history.add_search("(objectClass=person)")
    query_history.add_search("(uid=admin)")
    query_history.add_search("(cn=*)")
    query_history.add_base("dc=example,dc=com")
    query_history.add_base("ou=people,dc=example,dc=com")
    query_history.add_host("ldap.example.com")
    query_history.add_host("localhost")
    
    # Test retrieval
    console.print(f"Search filters: {query_history.get_searches()}")
    console.print(f"Base DNs: {query_history.get_bases()}")
    console.print(f"Hosts: {query_history.get_hosts()}")
    
    # Test save and load
    query_history.save_history()
    
    # Create a new history object that should load the saved history
    new_history = QueryHistory()
    console.print(f"Loaded history: {new_history.get_history()}")
    
    console.print("[green]✓ Query history tests completed[/green]")

if __name__ == "__main__":
    console.print("[bold cyan]LDAPie Tab Completion and Query History Tests[/bold cyan]")
    console.print()
    
    test_tab_completion()
    test_query_history()
    
    console.print("\n[bold green]All tests completed successfully![/bold green]")

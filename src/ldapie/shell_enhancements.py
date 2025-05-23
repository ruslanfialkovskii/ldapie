#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Shell Integration for LDAPie

This module integrates the tab completion and query history features
into the LDAPShell class.
"""

from .tab_completion import TabCompletion, QueryHistory

def integrate_tab_completion(shell_instance):
    """
    Integrate tab completion into the shell instance
    
    Args:
        shell_instance: LDAPShell instance
    """
    # Create query history manager
    query_history = QueryHistory()
    
    # Create tab completion handler
    tab_completer = TabCompletion(query_history)
    
    # Add references to shell
    shell_instance.query_history = query_history
    shell_instance.tab_completer = tab_completer
    
    # Update the shell's complete method to use our tab completer
    shell_instance.complete = tab_completer.complete
    
    # Return the integrated shell
    return shell_instance

def add_history_command(shell_instance):
    """
    Add the history command to the shell instance
    
    Args:
        shell_instance: LDAPShell instance
    """
    # Define the history command
    def do_history(self, arg):
        """
        View command history or specific query types
        Usage: history [search|base|host]
        """
        from rich.table import Table
        
        # Parse arguments
        if not arg:
            # Show all history
            table = Table(title="Command History", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="green")
            
            # Show search filters
            for filter_query in self.query_history.get_searches():
                table.add_row("search", filter_query)
            
            # Show base DNs
            for base_dn in self.query_history.get_bases():
                table.add_row("base", base_dn)
                
            # Show hosts
            for host in self.query_history.get_hosts():
                table.add_row("host", host)
                
            self.console.print(table)
        elif arg == "search":
            # Show search filters
            table = Table(title="Search History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("Filter", style="green")
            
            for i, filter_query in enumerate(self.query_history.get_searches(), 1):
                table.add_row(str(i), filter_query)
                
            self.console.print(table)
        elif arg == "base":
            # Show base DNs
            table = Table(title="Base DN History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("DN", style="green")
            
            for i, base_dn in enumerate(self.query_history.get_bases(), 1):
                table.add_row(str(i), base_dn)
                
            self.console.print(table)
        elif arg == "host":
            # Show hosts
            table = Table(title="Host History", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("Host", style="green")
            
            for i, host in enumerate(self.query_history.get_hosts(), 1):
                table.add_row(str(i), host)
                
            self.console.print(table)
        else:
            self.console.print(f"[error]Unknown history type: {arg}[/error]")
            self.console.print("[info]Available types: search, base, host[/info]")
    
    # Add the method to the shell instance
    shell_instance.do_history = do_history.__get__(shell_instance)
    
    return shell_instance

def enhance_do_search(shell_instance):
    """Enhance search command to track history"""
    original_do_search = shell_instance.do_search
    
    def enhanced_do_search(self, arg):
        """Enhanced search with history tracking"""
        import shlex
        
        # Extract the filter from the arg
        try:
            args = shlex.split(arg)
            if args:
                filter_query = args[0]
                
                # Remove surrounding quotes if present
                if filter_query.startswith(("'", '"')) and filter_query.endswith(("'", '"')):
                    filter_query = filter_query[1:-1]
                    
                # Add to history
                self.query_history.add_search(filter_query)
        except:
            pass  # Ignore parsing errors
        
        # Call original method
        return original_do_search(arg)
    
    # Replace the method
    shell_instance.do_search = enhanced_do_search.__get__(shell_instance)
    
    return shell_instance

def enhance_do_base(shell_instance):
    """Enhance base command to track history"""
    original_do_base = shell_instance.do_base
    
    def enhanced_do_base(self, arg):
        """Enhanced base command with history tracking"""
        if arg:
            # Add to history
            self.query_history.add_base(arg)
        
        # Call original method
        return original_do_base(arg)
    
    # Replace the method
    shell_instance.do_base = enhanced_do_base.__get__(shell_instance)
    
    return shell_instance

def enhance_do_connect(shell_instance):
    """Enhance connect command to track history"""
    original_do_connect = shell_instance.do_connect
    
    def enhanced_do_connect(self, arg):
        """Enhanced connect command with history tracking"""
        args = arg.split()
        if args:
            host = args[0]
            # Add to history
            self.query_history.add_host(host)
        
        # Call original method
        return original_do_connect(arg)
    
    # Replace the method
    shell_instance.do_connect = enhanced_do_connect.__get__(shell_instance)
    
    return shell_instance

def enhance_shell(shell_instance):
    """
    Enhance the shell with tab completion and query history
    
    Args:
        shell_instance: LDAPShell instance
        
    Returns:
        Enhanced shell instance
    """
    # Integrate tab completion
    shell_instance = integrate_tab_completion(shell_instance)
    
    # Add history command
    shell_instance = add_history_command(shell_instance)
    
    # Enhance commands to track history
    shell_instance = enhance_do_search(shell_instance)
    shell_instance = enhance_do_base(shell_instance)
    shell_instance = enhance_do_connect(shell_instance)
    
    return shell_instance

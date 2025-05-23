#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tab Completion and Query History for LDAPie

This module provides tab completion functionality and query history tracking
for the LDAPie interactive shell.
"""

import os
import readline
import json

class QueryHistory:
    """
    Manages command and query history for the interactive shell
    
    This class stores and retrieves query history for different command types
    and provides methods to save/load history to/from disk.
    """
    
    def __init__(self):
        """Initialize query history"""
        self.history = {
            'search': [],  # search filters
            'base': [],    # base DNs
            'host': []     # hostnames
        }
        self.history_file = os.path.expanduser('~/.ldapie_query_history.json')
        self.load_history()
        
    def add_search(self, filter_query):
        """Add a search filter to history"""
        self._add_to_history('search', filter_query)
        
    def add_base(self, base_dn):
        """Add a base DN to history"""
        self._add_to_history('base', base_dn)
        
    def add_host(self, host):
        """Add a host to history"""
        self._add_to_history('host', host)
        
    def _add_to_history(self, history_type, value):
        """Add an item to a specific history type"""
        if not value:
            return
            
        # Remove if already exists (to move to end)
        if value in self.history[history_type]:
            self.history[history_type].remove(value)
            
        # Add to end of list
        self.history[history_type].append(value)
        
        # Keep history to a reasonable size
        if len(self.history[history_type]) > 20:
            self.history[history_type] = self.history[history_type][-20:]
            
        # Save to disk
        self.save_history()
        
    def get_searches(self):
        """Get search filter history"""
        return self.history['search']
        
    def get_bases(self):
        """Get base DN history"""
        return self.history['base']
        
    def get_hosts(self):
        """Get host history"""
        return self.history['host']
        
    def get_history(self, history_type=None):
        """Get full history or specific type"""
        if history_type:
            return self.history.get(history_type, [])
        return self.history
        
    def save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not save query history: {e}")
            
    def load_history(self):
        """Load history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.history.update(json.load(f))
        except (IOError, json.JSONDecodeError, PermissionError) as e:
            print(f"Warning: Could not load query history: {e}")


class TabCompletion:
    """Tab completion functionality for LDAPShell"""
    
    def __init__(self, query_history=None):
        """Initialize with optional query history"""
        self.query_history = query_history or QueryHistory()
    
    def complete_search(self, text, line, begidx, endidx):
        """Tab completion for search command"""
        args = line.split()
        if len(args) == 1 and not text:
            # Just entered "search"
            return ["(objectClass=*)", "(cn=*)", "(uid=*)", "--help"]
        elif len(args) == 2 or (len(args) == 1 and text):
            # Second argument - filter
            return self.get_search_filters_completion(text)
        else:
            # Attributes or options
            if text.startswith('-'):
                # Options
                options = ['-a', '--tree', '--json', '--ldif', '--csv']
                return [opt for opt in options if opt.startswith(text)]
            return []

    def complete_connect(self, text, line, begidx, endidx):
        """Tab completion for connect command"""
        args = line.split()
        if len(args) == 1 and not text:
            # Just entered "connect"
            return ["ldap://", "ldaps://"] + self.get_hosts_completion("")
        elif len(args) <= 2 or (len(args) == 1 and text):
            # Second argument - host
            return self.get_hosts_completion(text)
        elif len(args) == 3 or (len(args) == 2 and text):
            # Third argument - port
            if text.startswith('-'):
                return ['--ssl'] if '--ssl'.startswith(text) else []
            return ['389', '636'] if not text else []
        elif len(args) >= 4:
            # Options and username
            if text.startswith('-'):
                options = ['--ssl']
                return [opt for opt in options if opt.startswith(text)]
        return []

    def complete_base(self, text, line, begidx, endidx):
        """Tab completion for base command"""
        args = line.split()
        if len(args) <= 2 or (len(args) == 1 and text):
            # Base DN
            return self.get_base_dns_completion(text)
        return []
            
    def complete_history(self, text, line, begidx, endidx):
        """Tab completion for history command"""
        history_types = ['search', 'base', 'host']
        if len(line.split()) == 1:
            return [h for h in history_types if h.startswith(text)]
        return []
        
    def complete_schema(self, text, line, begidx, endidx):
        """Tab completion for schema command"""
        args = line.split()
        if len(args) == 2 and text.startswith('--'):
            return ['--attr'] if '--attr'.startswith(text) else []
        return []
        
    def complete(self, text, state):
        """Main completion method for readline"""
        if state == 0:
            # This is the first time for this text, so build a match list
            line = readline.get_line_buffer()
            if not line:
                self.matches = self.get_commands('')
            else:
                parts = line.split()
                command = parts[0] if parts else None
                
                # If we're completing a command name
                if len(parts) == 1 and not line.endswith(' '):
                    self.matches = self.get_commands(text)
                # If we're completing command arguments
                else:
                    # Forward to command-specific completion method
                    method_name = f"complete_{command}" if command else None
                    if method_name and hasattr(self, method_name):
                        self.matches = getattr(self, method_name)(
                            text, line, readline.get_begidx(), readline.get_endidx()
                        )
                    else:
                        self.matches = []
        
        # Return the state'th match
        try:
            return self.matches[state]
        except (IndexError, AttributeError):
            return None
            
    def get_commands(self, prefix):
        """Get all command names starting with prefix"""
        commands = [
            'connect', 'base', 'search', 'info', 'schema', 
            'exit', 'quit', 'help', 'history', 'validate', 'suggest'
        ]
        return [cmd for cmd in commands if cmd.startswith(prefix)]
            
    def get_hosts_completion(self, text):
        """Get host completions"""
        hosts = set(self.query_history.get_hosts())
        
        # Add common defaults
        if not hosts:
            hosts.update(['localhost', 'ldap.example.com', '127.0.0.1'])
        
        return [host for host in hosts if host.startswith(text)]
        
    def get_base_dns_completion(self, text):
        """Get base DN completions"""
        dns = set(self.query_history.get_bases())
        
        # Add common defaults
        if not dns:
            dns.update(['dc=example,dc=com', 'ou=people,dc=example,dc=com', 'ou=groups,dc=example,dc=com'])
        
        return [dn for dn in dns if dn.startswith(text)]
        
    def get_search_filters_completion(self, text):
        """Get search filter completions"""
        filters = set(self.query_history.get_searches())
        
        # Add common defaults
        if not filters:
            filters.update([
                '(objectClass=*)', 
                '(cn=*)', 
                '(uid=*)',
                '(&(objectClass=person)(cn=*))',
                '(|(uid=*)(mail=*))'
            ])
            
        return [f for f in filters if f.startswith(text)]

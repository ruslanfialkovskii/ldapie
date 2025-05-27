#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context-Sensitive Help System for LDAPie

This module implements a context-aware help system that provides smart suggestions
and guidance based on the current operation context and command history.

Key components:
- HelpContext: A singleton class that tracks command history and operation context
- CommandAnalyzer: Parses and analyzes user input for intent detection
- SuggestionEngine: Provides contextual suggestions and examples
- ValidationEngine: Performs dry-run of commands to validate before execution

Example:
    >>> from help_context import HelpContext
    >>> ctx = HelpContext()
    >>> ctx.add_command("search ldap.example.com 'dc=example,dc=com'")
    >>> suggestions = ctx.get_suggestions()
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import deque, defaultdict
from difflib import get_close_matches
import Levenshtein

# Common LDAP command patterns for analysis and suggestions
COMMAND_PATTERNS = {
    "search": {
        "syntax": "search <host> <base_dn> [<filter>] [options]",
        "examples": [
            "search ldap.example.com 'dc=example,dc=com'",
            "search ldap.example.com 'dc=example,dc=com' '(objectClass=person)' -a cn -a mail",
            "search ldap.example.com 'dc=example,dc=com' --tree"
        ],
        "next_steps": [
            "Use --json, --ldif, or --csv to change output format",
            "Add -a attribute to specify attributes to retrieve",
            "Use --tree to view results in a tree structure"
        ],
        "common_errors": [
            "Missing quotes around base_dn or filter",
            "Invalid filter syntax",
            "Using special characters without escaping"
        ]
    },
    "info": {
        "syntax": "info <host> [options]",
        "examples": [
            "info ldap.example.com",
            "info ldap.example.com -u 'cn=admin,dc=example,dc=com'"
        ],
        "next_steps": [
            "Use schema command to view object class details",
            "Check server capabilities with --json option"
        ],
        "common_errors": [
            "Authentication required for detailed information"
        ]
    },
    "compare": {
        "syntax": "compare <host> <dn1> <dn2> [options]",
        "examples": [
            "compare ldap.example.com 'uid=user1,ou=people,dc=example,dc=com' 'uid=user2,ou=people,dc=example,dc=com'",
            "compare ldap.example.com 'uid=user1,ou=people,dc=example,dc=com' 'uid=user2,ou=people,dc=example,dc=com' -a mail -a cn"
        ],
        "next_steps": [
            "Specify attributes to compare with -a option",
            "Use --json for machine-readable output"
        ],
        "common_errors": [
            "DNs must be properly quoted",
            "Both entries must exist"
        ]
    },
    "schema": {
        "syntax": "schema <host> [<object_class>] [options]",
        "examples": [
            "schema ldap.example.com",
            "schema ldap.example.com person",
            "schema ldap.example.com --attr mail"
        ],
        "next_steps": [
            "Look up specific object class details",
            "Check attribute syntax with --attr option"
        ],
        "common_errors": [
            "Object class or attribute may not exist"
        ]
    },
    "add": {
        "syntax": "add <host> <dn> [options]",
        "examples": [
            "add ldap.example.com 'cn=newuser,ou=people,dc=example,dc=com' --class inetOrgPerson --attr cn=newuser --attr sn=User",
            "add ldap.example.com 'cn=newgroup,ou=groups,dc=example,dc=com' --json group.json"
        ],
        "next_steps": [
            "Use search to verify entry was added",
            "Add additional attributes with --attr option"
        ],
        "common_errors": [
            "Missing required attributes for object class",
            "DN already exists",
            "Parent DN doesn't exist"
        ]
    },
    "modify": {
        "syntax": "modify <host> <dn> [options]",
        "examples": [
            "modify ldap.example.com 'cn=user1,ou=people,dc=example,dc=com' --add mail=user1@example2.com",
            "modify ldap.example.com 'cn=user1,ou=people,dc=example,dc=com' --replace mobile=555-1234",
            "modify ldap.example.com 'cn=user1,ou=people,dc=example,dc=com' --delete mail=user1@example.com"
        ],
        "next_steps": [
            "Use search to verify changes",
            "Combine multiple modifications in one command"
        ],
        "common_errors": [
            "Attempting to modify non-existent entry",
            "Missing required attributes",
            "Deleting a value that doesn't exist"
        ]
    },
    "delete": {
        "syntax": "delete <host> <dn> [options]",
        "examples": [
            "delete ldap.example.com 'cn=user1,ou=people,dc=example,dc=com'",
            "delete ldap.example.com 'ou=people,dc=example,dc=com' --recursive"
        ],
        "next_steps": [
            "Use --recursive for subtree deletion",
            "Use search to verify deletion"
        ],
        "common_errors": [
            "Entry has children (use --recursive)",
            "Entry doesn't exist",
            "Insufficient permissions"
        ]
    },
    "rename": {
        "syntax": "rename <host> <dn> <new_rdn> [options]",
        "examples": [
            "rename ldap.example.com 'cn=user1,ou=people,dc=example,dc=com' 'cn=user1renamed'",
            "rename ldap.example.com 'cn=user1,ou=people,dc=example,dc=com' 'cn=user1' --parent 'ou=admins,dc=example,dc=com'"
        ],
        "next_steps": [
            "Use search to verify the rename",
            "Use --parent to move entry to different location"
        ],
        "common_errors": [
            "New RDN already exists",
            "Parent DN doesn't exist",
            "Missing required attributes in new RDN"
        ]
    },
    "interactive": {
        "syntax": "interactive [options]",
        "examples": [
            "interactive",
            "interactive --host ldap.example.com --base 'dc=example,dc=com'"
        ],
        "next_steps": [
            "Use 'help' command to see available commands",
            "Use 'connect' to establish connection",
            "Use 'ls' to list entries"
        ],
        "common_errors": [
            "Not connected to server (use connect command)",
            "Not setting base DN (use cd command)"
        ]
    }
}

class HelpContext:
    """
    Singleton class that tracks command history and operational context
    
    Maintains a record of commands executed, their results, and the current
    operation state to provide context-aware help and suggestions.
    
    Attributes:
        _instance: Singleton instance reference
        command_history: Deque of recent commands
        current_context: Dictionary containing current operation state
        session_state: Connection and authentication state
        user_preferences: User-defined settings and preferences
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HelpContext, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize context tracking structures"""
        self.command_history = deque(maxlen=20)
        self.current_context = {
            "command": None,
            "subcommand": None,
            "host": None,
            "base_dn": None,
            "filter": None,
            "attributes": [],
            "search_results": None,
            "last_entry": None,
            "operation_result": None
        }
        self.session_state = {
            "connected": False,
            "authenticated": False,
            "server": None,
            "connection": None,
            "ssl_enabled": False
        }
        self.user_preferences = {
            "theme": "dark",
            "output_format": "rich",
            "page_size": 100
        }
        self.command_frequency = defaultdict(int)
        self.error_history = []
        
    def add_command(self, command_str: str) -> None:
        """
        Add a command to the history
        
        Args:
            command_str: The command string executed by the user
            
        Example:
            >>> ctx = HelpContext()
            >>> ctx.add_command("search ldap.example.com 'dc=example,dc=com'")
        """
        self.command_history.append(command_str)
        
        # Parse command to update context
        parts = command_str.split()
        if not parts:
            return
            
        # Update command frequency for statistics
        cmd = parts[0]
        self.command_frequency[cmd] += 1
        
        # Basic context update based on command
        if cmd in COMMAND_PATTERNS:
            self.current_context["command"] = cmd
            
            # Extract host and base_dn where applicable
            if len(parts) > 1 and cmd in ["search", "info", "add", "modify", "delete", "rename", "compare", "schema"]:
                self.current_context["host"] = parts[1]
                
            if len(parts) > 2 and cmd in ["search", "add", "modify", "delete", "rename", "compare"]:
                self.current_context["base_dn"] = parts[2]
                
            if len(parts) > 3 and cmd == "search":
                self.current_context["filter"] = parts[3]
    
    def add_error(self, command_str: str, error_msg: str) -> None:
        """
        Record a command error for analysis
        
        Args:
            command_str: Command that caused the error
            error_msg: Error message produced
        """
        self.error_history.append({
            "command": command_str,
            "error": error_msg,
            "timestamp": self._get_timestamp()
        })
    
    def update_session_state(self, connected: bool = None, authenticated: bool = None, 
                             server: Any = None, connection: Any = None, ssl_enabled: bool = None) -> None:
        """
        Update the current session state
        
        Args:
            connected: Whether connected to a server
            authenticated: Whether authenticated
            server: Server object
            connection: Connection object
            ssl_enabled: Whether SSL is enabled
        """
        if connected is not None:
            self.session_state["connected"] = connected
        if authenticated is not None:
            self.session_state["authenticated"] = authenticated
        if server is not None:
            self.session_state["server"] = server
        if connection is not None:
            self.session_state["connection"] = connection
        if ssl_enabled is not None:
            self.session_state["ssl_enabled"] = ssl_enabled
    
    def update_operation_result(self, result: Any) -> None:
        """Store the result of the last operation"""
        self.current_context["operation_result"] = result
    
    def update_search_results(self, results: List[Any]) -> None:
        """Store search results in the context"""
        self.current_context["search_results"] = results
    
    def get_suggestions(self) -> Dict[str, Any]:
        """
        Get context-aware suggestions based on current state
        
        Returns a dictionary of suggestions including next commands,
        examples, tips, and corrections.
        
        Returns:
            Dictionary with suggestions
        """
        suggestions = {
            "next_commands": [],
            "examples": [],
            "tips": [],
            "corrections": []
        }
        
        # Get current command for context
        current_cmd = self.current_context.get("command")
        
        # Add general suggestions based on usage patterns
        if current_cmd:
            # Add next steps from command patterns
            cmd_info = COMMAND_PATTERNS.get(current_cmd, {})
            suggestions["next_commands"] = cmd_info.get("next_steps", [])
            
            # Add examples related to current command
            suggestions["examples"] = cmd_info.get("examples", [])
            
            # Add common error tips
            suggestions["tips"] = cmd_info.get("common_errors", [])
        
        # If we have search results, suggest operations on those results
        if self.current_context.get("search_results"):
            suggestions["next_commands"].extend([
                "Use --json to output results in JSON format",
                "Use --tree to view results in a hierarchical tree",
                "Use --csv to export results to CSV",
                "Use compare to compare two entries from the results"
            ])
        
        # Add authentication suggestions if not authenticated
        if not self.session_state.get("authenticated") and self.session_state.get("connected"):
            suggestions["tips"].append("Use -u and -p options to authenticate for more privileges")
        
        # Add SSL suggestions if not using SSL
        if not self.session_state.get("ssl_enabled") and self.session_state.get("connected"):
            suggestions["tips"].append("Consider using --ssl for secure connection")
        
        return suggestions
    
    def get_command_help(self, command: str) -> Dict[str, Any]:
        """
        Get detailed help for a specific command
        
        Args:
            command: Command to get help for
            
        Returns:
            Dictionary with command help information
        """
        cmd_info = COMMAND_PATTERNS.get(command, {})
        if not cmd_info:
            # Try to find closest command
            all_commands = list(COMMAND_PATTERNS.keys())
            matches = get_close_matches(command, all_commands, n=1, cutoff=0.6)
            
            if matches:
                return {
                    "error": f"Command '{command}' not found. Did you mean '{matches[0]}'?",
                    "suggested_command": matches[0],
                    "help": COMMAND_PATTERNS.get(matches[0], {})
                }
            else:
                return {"error": f"Command '{command}' not found."}
                
        return cmd_info
    
    def analyze_command(self, command_str: str) -> Dict[str, Any]:
        """
        Analyze a command string for validation and suggestions
        
        Args:
            command_str: Command string to analyze
            
        Returns:
            Dictionary with analysis results
        """
        parts = command_str.split()
        if not parts:
            return {"error": "Empty command"}
            
        cmd = parts[0]
        
        # Check if command exists
        if cmd not in COMMAND_PATTERNS:
            # Try to find closest command
            all_commands = list(COMMAND_PATTERNS.keys())
            matches = get_close_matches(cmd, all_commands, n=3, cutoff=0.6)
            
            if matches:
                return {
                    "error": f"Command '{cmd}' not found. Did you mean '{matches[0]}'?",
                    "suggested_commands": matches
                }
            else:
                return {"error": f"Command '{cmd}' not found."}
        
        # Check argument count
        cmd_info = COMMAND_PATTERNS.get(cmd, {})
        syntax = cmd_info.get("syntax", "")
        syntax_parts = syntax.split()
        
        # Count required arguments (those without [ ])
        required_args = [p for p in syntax_parts if not (p.startswith('[') and p.endswith(']'))]
        required_count = len(required_args) - 1  # Subtract 1 for the command itself
        
        if len(parts) < required_count + 1:
            return {
                "error": f"Not enough arguments for '{cmd}'. Syntax: {syntax}",
                "syntax": syntax,
                "examples": cmd_info.get("examples", [])
            }
        
        # Basic validation passed, return command info
        return {
            "command": cmd,
            "arguments": parts[1:],
            "syntax": syntax,
            "examples": cmd_info.get("examples", []),
            "next_steps": cmd_info.get("next_steps", []),
            "common_errors": cmd_info.get("common_errors", [])
        }
    
    def get_help_for_validation_error(self, command_str: str, error_msg: str) -> Dict[str, Any]:
        """
        Get help for a validation error
        
        Args:
            command_str: Command that caused the error
            error_msg: Error message
            
        Returns:
            Dictionary with help information
        """
        parts = command_str.split()
        if not parts:
            return {"error": "Empty command"}
            
        cmd = parts[0]
        cmd_info = COMMAND_PATTERNS.get(cmd, {})
        
        # Look for common error patterns
        common_errors = {
            "no such object": "The specified DN does not exist",
            "already exists": "Entry already exists",
            "invalid filter": "The LDAP filter syntax is incorrect",
            "insufficient access rights": "You don't have permission for this operation",
            "invalid DN syntax": "The DN syntax is incorrect - check for proper escaping and formatting"
        }
        
        help_info = {
            "error": error_msg,
            "syntax": cmd_info.get("syntax", ""),
            "examples": cmd_info.get("examples", [])
        }
        
        # Add specific help based on error message pattern
        for pattern, message in common_errors.items():
            if pattern in error_msg.lower():
                help_info["suggestion"] = message
                break
        
        return help_info
    
    def _get_timestamp(self):
        """Get current timestamp for history entries"""
        import datetime
        return datetime.datetime.now().isoformat()


class CommandValidator:
    """
    Validates commands before execution
    
    Provides a preview of command execution and validates parameters
    without actually performing the operation.
    """
    def __init__(self, help_context: HelpContext = None):
        self.help_context = help_context or HelpContext()
    
    def validate_command(self, command_str: str) -> Dict[str, Any]:
        """
        Validate a command without executing it
        
        Args:
            command_str: Command string to validate
            
        Returns:
            Dictionary with validation results
        """
        # First use the analyzer to check basic command structure
        analysis = self.help_context.analyze_command(command_str)
        if "error" in analysis:
            return analysis
            
        cmd = analysis["command"]
        
        # Perform command-specific validation
        if cmd == "search":
            return self._validate_search(command_str, analysis)
        elif cmd == "add":
            return self._validate_add(command_str, analysis)
        elif cmd == "modify":
            return self._validate_modify(command_str, analysis)
        elif cmd == "delete":
            return self._validate_delete(command_str, analysis)
        elif cmd == "rename":
            return self._validate_rename(command_str, analysis)
        
        # For commands without specific validation, return the basic analysis
        return {
            **analysis,
            "validation": "Command structure looks valid",
            "preview": f"Command would execute: {command_str}"
        }
    
    def _validate_search(self, command_str: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search command"""
        args = analysis["arguments"]
        
        # Need at least host and base_dn
        if len(args) < 2:
            return {
                "error": "Not enough arguments for search command",
                "syntax": analysis["syntax"],
                "examples": analysis["examples"]
            }
        
        # Check for filter syntax if provided
        if len(args) > 2:
            filter_arg = args[2]
            if not (filter_arg.startswith('(') and filter_arg.endswith(')')):
                return {
                    "warning": "LDAP filter should be enclosed in parentheses",
                    "suggestion": f"Try: search {args[0]} {args[1]} '({filter_arg})'",
                    **analysis
                }
        
        return {
            **analysis,
            "validation": "Search command looks valid",
            "preview": f"Would search {args[0]} with base DN {args[1]}"
        }
    
    def _validate_add(self, command_str: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate add command"""
        # Implementation for add command validation
        return {
            **analysis,
            "validation": "Add command structure looks valid",
            "preview": "Would add new entry to the directory"
        }
    
    def _validate_modify(self, command_str: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate modify command"""
        # Implementation for modify command validation
        return {
            **analysis,
            "validation": "Modify command structure looks valid",
            "preview": "Would modify the specified entry"
        }
    
    def _validate_delete(self, command_str: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate delete command"""
        # Check for recursive flag on delete
        if "--recursive" not in command_str and "-r" not in command_str:
            return {
                **analysis,
                "validation": "Delete command structure looks valid",
                "warning": "Note: This will only delete the entry if it has no children",
                "suggestion": "Add --recursive flag to delete the entry and all its children",
                "preview": "Would delete the specified entry"
            }
        
        return {
            **analysis,
            "validation": "Delete command structure looks valid",
            "warning": "This will delete the entry and all its children recursively",
            "preview": "Would recursively delete the specified entry and all children"
        }
    
    def _validate_rename(self, command_str: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rename command"""
        # Implementation for rename command validation
        return {
            **analysis,
            "validation": "Rename command structure looks valid",
            "preview": "Would rename the specified entry"
        }


# For testing
if __name__ == "__main__":
    # Example usage
    ctx = HelpContext()
    ctx.add_command("search ldap.example.com 'dc=example,dc=com'")
    print(ctx.get_suggestions())
    
    validator = CommandValidator(ctx)
    result = validator.validate_command("search ldap.example.com 'dc=example,dc=com' objectClass=person")
    print(json.dumps(result, indent=2))

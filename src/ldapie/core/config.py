#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration management for LDAPie.

This module contains configuration classes and connection handling
for LDAP operations.
"""

import getpass
from typing import Optional, Tuple
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPException, LDAPBindError


class LdapConfig:
    """
    LDAP Connection Configuration
    
    Stores configuration details for an LDAP connection and provides
    methods to establish connections.
    
    Attributes:
        host (str): LDAP server hostname
        username (Optional[str]): Bind DN for authentication
        password (Optional[str]): Password for authentication
        use_ssl (bool): Whether to use SSL/TLS
        port (int): LDAP port number
        timeout (int): Connection timeout in seconds
    """
    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
        port: Optional[int] = None,
        timeout: int = 30,
    ):
        """
        Initialize LDAP connection configuration.
        
        Args:
            host: LDAP server hostname
            username: Optional bind DN for authentication
            password: Optional password for authentication
            use_ssl: Whether to use SSL/TLS
            port: LDAP port number (default: 389, or 636 with SSL)
            timeout: Connection timeout in seconds
            
        Example:
            >>> config = LdapConfig("ldap.example.com", 
            ...                    username="cn=admin,dc=example,dc=com",
            ...                    password="secret", use_ssl=True)
        """
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.port = port or (636 if use_ssl else 389)
        self.timeout = timeout

    def get_connection(self) -> Tuple[Server, Connection]:
        """
        Create an LDAP server connection based on configuration.
        
        Establishes a connection to the LDAP server using the configured
        parameters. If username is provided but password is not, prompts
        for password interactively.
        
        Returns:
            Tuple containing:
                - Server object
                - Connection object (bound to the server)
                
        Raises:
            LDAPBindError: If authentication fails
            LDAPException: For other LDAP-related errors
            
        Example:
            >>> server, conn = config.get_connection()
        """
        server_uri = f"{'ldaps' if self.use_ssl else 'ldap'}://{self.host}:{self.port}"
        server = Server(server_uri, get_info=ALL, connect_timeout=self.timeout)
        
        # Handle anonymous vs. authenticated binding
        if self.username:
            if self.password is None:
                # Prompt for password if not provided
                self.password = getpass.getpass(f"Enter password for {self.username}: ")
            
            conn = Connection(
                server,
                user=self.username,
                password=self.password,
                auto_bind=True,
                raise_exceptions=True
            )
        else:
            # Anonymous binding
            conn = Connection(
                server,
                auto_bind=True,
                raise_exceptions=True
            )
            
        return server, conn

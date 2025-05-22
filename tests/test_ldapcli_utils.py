#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for LDAPie utility functions
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import ldap3
from io import StringIO

# Add the parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the utility functions to test
from src import ldapie_utils as utils

class TestLdapUtils(unittest.TestCase):
    """Test case for LDAP utility functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a StringIO object to capture stdout
        self.stdout = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout
    
    def tearDown(self):
        """Tear down test fixtures"""
        # Restore stdout
        sys.stdout = self.original_stdout
    
    def test_parse_modification_attributes(self):
        """Test parsing modification attributes"""
        # Test adding an attribute
        add_attrs = ["mail=newmail@example.com"]
        replace_attrs = []
        delete_attrs = []
        mods = utils.parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        
        self.assertTrue("mail" in mods)
        self.assertEqual(mods["mail"]["operation"], ldap3.MODIFY_ADD)
        
        # Test replacing an attribute
        add_attrs = []
        replace_attrs = ["title=New Title"]
        delete_attrs = []
        mods = utils.parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        
        self.assertTrue("title" in mods)
        self.assertEqual(mods["title"]["operation"], ldap3.MODIFY_REPLACE)
        
        # Test deleting an attribute
        add_attrs = []
        replace_attrs = []
        delete_attrs = ["description"]
        mods = utils.parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        
        self.assertTrue("description" in mods)
        self.assertEqual(mods["description"]["operation"], ldap3.MODIFY_DELETE)
    
    def test_format_output_filename(self):
        """Test formatting output filename based on extension"""
        self.assertEqual(utils.format_output_filename("test", "json"), "test.json")
        self.assertEqual(utils.format_output_filename("test.json", "json"), "test.json")
        self.assertEqual(utils.format_output_filename("test.txt", "json"), "test.txt.json")
    
    def test_parse_ldap_uri(self):
        """Test parsing of LDAP URI into components"""
        # Test standard LDAP URI
        uri = "ldap://example.com:389"
        result = utils.parse_ldap_uri(uri)
        self.assertEqual(result["protocol"], "ldap")
        self.assertEqual(result["host"], "example.com")
        self.assertEqual(result["port"], 389)
        self.assertFalse(result["use_ssl"])
        
        # Test LDAPS URI
        uri = "ldaps://secure.example.com"
        result = utils.parse_ldap_uri(uri)
        self.assertEqual(result["protocol"], "ldaps")
        self.assertEqual(result["host"], "secure.example.com")
        self.assertEqual(result["port"], 636)  # Default LDAPS port
        self.assertTrue(result["use_ssl"])
        
        # Test URI with base DN
        uri = "ldap://example.com/dc=example,dc=com"
        result = utils.parse_ldap_uri(uri)
        self.assertEqual(result["base_dn"], "dc=example,dc=com")
    
    def test_format_ldap_entry(self):
        """Test formatting of LDAP entries for display"""
        # Create a mock LDAP entry
        entry = MagicMock()
        entry.entry_dn = "cn=user,dc=example,dc=com"
        entry.entry_attributes_as_dict = {
            "cn": ["user"],
            "objectClass": ["top", "person"],
            "sn": ["User"],
            "mail": ["user@example.com"]
        }
        
        # Test JSON formatting
        with patch.object(utils, 'format_json', return_value='{"dn": "cn=user,dc=example,dc=com"}'):
            result = utils.format_ldap_entry(entry, "json")
            utils.format_json.assert_called_once()
            self.assertIn("dn", result)
        
        # Test LDIF formatting
        with patch.object(utils, 'format_ldif', return_value='dn: cn=user,dc=example,dc=com'):
            result = utils.format_ldap_entry(entry, "ldif")
            utils.format_ldif.assert_called_once()
            self.assertIn("dn:", result)
    
    def test_parse_search_filter(self):
        """Test parsing and validation of LDAP search filters"""
        # Test simple filter
        filter_str = "(cn=user)"
        self.assertTrue(utils.validate_search_filter(filter_str))
        
        # Test complex filter
        filter_str = "(&(objectClass=person)(|(cn=user)(mail=user@example.com)))"
        self.assertTrue(utils.validate_search_filter(filter_str))
        
        # Test invalid filter
        filter_str = "(cn=user"  # Missing closing parenthesis
        self.assertFalse(utils.validate_search_filter(filter_str))
    
    def test_parse_attributes(self):
        """Test parsing of attribute list"""
        # Test single attribute
        attrs = utils.parse_attributes("cn")
        self.assertEqual(attrs, ["cn"])
        
        # Test multiple attributes
        attrs = utils.parse_attributes("cn,sn,mail")
        self.assertEqual(attrs, ["cn", "sn", "mail"])
        
        # Test with spaces
        attrs = utils.parse_attributes("cn, sn, mail")
        self.assertEqual(attrs, ["cn", "sn", "mail"])
    
    def test_create_connection(self):
        """Test creation of LDAP connection"""
        # Mock the ldap3.Connection
        with patch('ldap3.Connection') as mock_conn:
            mock_conn.return_value.bind.return_value = True
            
            # Test anonymous connection
            server = MagicMock()
            conn = utils.create_connection(server)
            mock_conn.assert_called_once()
            self.assertIsNotNone(conn)
            
            # Reset mock
            mock_conn.reset_mock()
            
            # Test authenticated connection
            conn = utils.create_connection(server, "cn=admin,dc=example,dc=com", "password")
            mock_conn.assert_called_once()
            self.assertIsNotNone(conn)
    
    def test_format_csv(self):
        """Test CSV formatting of LDAP data"""
        # Create mock entries
        entries = [
            {"dn": "cn=user1,dc=example,dc=com", "attributes": {"cn": ["user1"], "mail": ["user1@example.com"]}},
            {"dn": "cn=user2,dc=example,dc=com", "attributes": {"cn": ["user2"], "mail": ["user2@example.com"]}}
        ]
        
        # Test CSV formatting
        with patch.object(utils, 'convert_to_csv', return_value='dn,cn,mail\n...'):
            result = utils.format_entries_as_csv(entries, ["dn", "cn", "mail"])
            utils.convert_to_csv.assert_called_once()
            self.assertIn("dn,cn,mail", result)
    
    def test_handle_error_response(self):
        """Test error response handling"""
        # Mock error response
        error = ldap3.core.exceptions.LDAPOperationResult()
        error.description = "Invalid credentials"
        
        # Test error handling
        with self.assertRaises(SystemExit):
            with patch('sys.stderr', new=StringIO()):
                utils.handle_error_response(error)
                self.assertIn("Invalid credentials", sys.stderr.getvalue())
    
    def test_safe_get_password(self):
        """Test secure password retrieval"""
        # Test with explicit password
        with patch('getpass.getpass') as mock_getpass:
            password = utils.safe_get_password(provided_password="secret")
            mock_getpass.assert_not_called()
            self.assertEqual(password, "secret")
        
        # Test with prompt - patch the module where it's used, not imported
        with patch('src.ldapcli_utils.getpass.getpass', return_value="prompted_secret") as mock_getpass:
            password = utils.safe_get_password()
            mock_getpass.assert_called_once()
            self.assertEqual(password, "prompted_secret")
    
    def test_compare_entries(self):
        """Test comparing two LDAP entries"""
        # Mock connection and response
        conn = MagicMock()
        conn.compare.return_value = True
        
        # Test successful comparison
        result = utils.compare_entry(conn, "cn=user,dc=example,dc=com", "mail", "user@example.com")
        self.assertTrue(result)
        conn.compare.assert_called_with("cn=user,dc=example,dc=com", "mail", "user@example.com")
        
        # Test failed comparison
        conn.compare.return_value = False
        result = utils.compare_entry(conn, "cn=user,dc=example,dc=com", "mail", "wrong@example.com")
        self.assertFalse(result)
    
    def test_get_schema_info(self):
        """Test retrieving schema information"""
        # Mock connection and schema
        conn = MagicMock()
        schema_mock = MagicMock()
        schema_mock.object_classes = {
            "person": MagicMock(must_contain=["cn", "sn"], may_contain=["description"]),
            "organizationalPerson": MagicMock(must_contain=["cn"], may_contain=["title"])
        }
        schema_mock.attribute_types = {
            "cn": MagicMock(syntax="1.3.6.1.4.1.1466.115.121.1.15"),
            "sn": MagicMock(syntax="1.3.6.1.4.1.1466.115.121.1.15")
        }
        conn.server.schema = schema_mock
        
        # Test getting all object classes
        with patch.object(utils, 'format_schema_output', return_value="SCHEMA DATA"):
            result = utils.get_schema_info(conn, "objectclasses")
            self.assertEqual(result, "SCHEMA DATA")
            utils.format_schema_output.assert_called_once()
        
        # Test getting specific object class
        with patch.object(utils, 'format_schema_output', return_value="PERSON SCHEMA"):
            result = utils.get_schema_info(conn, "objectclass", "person")
            self.assertEqual(result, "PERSON SCHEMA")
    
    def test_add_entry(self):
        """Test adding a new LDAP entry"""
        # Mock connection
        conn = MagicMock()
        conn.add.return_value = True
        
        # Test adding entry with attributes
        attributes = {"objectClass": ["person"], "cn": ["testuser"], "sn": ["User"]}
        result = utils.add_entry(conn, "cn=testuser,dc=example,dc=com", attributes)
        self.assertTrue(result)
        conn.add.assert_called_with("cn=testuser,dc=example,dc=com", 
                                  ["person"], 
                                  {"cn": ["testuser"], "sn": ["User"]})
        
        # Test failed add
        conn.add.return_value = False
        conn.last_error = "Entry already exists"
        with self.assertRaises(Exception):
            utils.add_entry(conn, "cn=testuser,dc=example,dc=com", attributes)
    
    def test_delete_entry(self):
        """Test deleting an LDAP entry"""
        # Mock connection
        conn = MagicMock()
        
        # Test successful delete
        conn.delete.return_value = True
        result = utils.delete_entry(conn, "cn=testuser,dc=example,dc=com")
        self.assertTrue(result)
        conn.delete.assert_called_with("cn=testuser,dc=example,dc=com")
        
        # Test recursive delete
        conn.delete.reset_mock()
        
        # Mock search results for children
        conn.search.return_value = True
        child_entries = [
            {"dn": "cn=child1,cn=testuser,dc=example,dc=com"},
            {"dn": "cn=child2,cn=testuser,dc=example,dc=com"}
        ]
        conn.entries = [MagicMock(entry_dn=entry["dn"]) for entry in child_entries]
        
        result = utils.delete_entry(conn, "cn=testuser,dc=example,dc=com", recursive=True)
        self.assertTrue(result)
        # Should delete children first, then parent
        self.assertEqual(conn.delete.call_count, 3)
    
    def test_modify_entry(self):
        """Test modifying an LDAP entry"""
        # Mock connection
        conn = MagicMock()
        conn.modify.return_value = True
        
        # Create modifications dictionary
        modifications = {
            "mail": {"operation": ldap3.MODIFY_REPLACE, "value": ["new@example.com"]},
            "title": {"operation": ldap3.MODIFY_ADD, "value": ["Manager"]}
        }
        
        # Test successful modify
        result = utils.modify_entry(conn, "cn=testuser,dc=example,dc=com", modifications)
        self.assertTrue(result)
        conn.modify.assert_called_with("cn=testuser,dc=example,dc=com", modifications)
        
        # Test failed modify
        conn.modify.return_value = False
        conn.last_error = "No such attribute"
        with self.assertRaises(Exception):
            utils.modify_entry(conn, "cn=testuser,dc=example,dc=com", modifications)
    
    def test_rename_entry(self):
        """Test renaming or moving an LDAP entry"""
        # Mock connection
        conn = MagicMock()
        conn.modify_dn.return_value = True
        
        # Test simple rename (change RDN)
        result = utils.rename_entry(conn, "cn=oldname,dc=example,dc=com", "cn=newname")
        self.assertTrue(result)
        conn.modify_dn.assert_called_with("cn=oldname,dc=example,dc=com", "cn=newname", delete_old_dn=True)
        
        # Test move to different container
        conn.modify_dn.reset_mock()
        result = utils.rename_entry(conn, "cn=user,ou=oldou,dc=example,dc=com", 
                                   "cn=user", new_superior="ou=newou,dc=example,dc=com")
        self.assertTrue(result)
        conn.modify_dn.assert_called_with("cn=user,ou=oldou,dc=example,dc=com", 
                                       "cn=user", 
                                       delete_old_dn=True, 
                                       new_superior="ou=newou,dc=example,dc=com")
        
        # Test rename and move
        conn.modify_dn.reset_mock()
        result = utils.rename_entry(conn, "cn=oldname,ou=oldou,dc=example,dc=com", 
                                   "cn=newname", new_superior="ou=newou,dc=example,dc=com")
        self.assertTrue(result)
        conn.modify_dn.assert_called_with("cn=oldname,ou=oldou,dc=example,dc=com", 
                                       "cn=newname", 
                                       delete_old_dn=True, 
                                       new_superior="ou=newou,dc=example,dc=com")

if __name__ == "__main__":
    unittest.main()

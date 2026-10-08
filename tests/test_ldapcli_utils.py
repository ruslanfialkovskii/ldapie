#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for LDAPie utility functions
"""

import os
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import ldap3

# Add the parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ldapie.entry_operations import (
    add_entry,
    delete_entry,
    modify_entry,
)

# Import the utility functions to test
from ldapie.utils import (
    format_output_filename,
    handle_error_response,
    parse_attributes,
    parse_modification_attributes,
    safe_get_password,
    validate_dn,
    validate_search_filter,
)


class TestLdapUtils(unittest.TestCase):
    """Test case for LDAP utility functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.stdout = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout
        # Common mock connection for tests that need it
        self.mock_conn = MagicMock(spec=ldap3.Connection)
        self.mock_conn.result = {"description": "mocked error", "result": 1}

    def tearDown(self):
        """Tear down test fixtures"""
        sys.stdout = self.original_stdout

    def test_parse_modification_attributes(self):
        """Test parsing modification attributes"""
        add_attrs = ["mail=newmail@example.com"]
        replace_attrs = []
        delete_attrs = []
        mods = parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        self.assertTrue("mail" in mods)
        self.assertEqual(mods["mail"]["operation"], ldap3.MODIFY_ADD)
        self.assertEqual(mods["mail"]["value"], ["newmail@example.com"])

        add_attrs = []
        replace_attrs = ["title=New Title"]
        delete_attrs = []
        mods = parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        self.assertTrue("title" in mods)
        self.assertEqual(mods["title"]["operation"], ldap3.MODIFY_REPLACE)
        self.assertEqual(mods["title"]["value"], ["New Title"])

        add_attrs = []
        replace_attrs = []
        delete_attrs = ["description"]
        mods = parse_modification_attributes(add_attrs, replace_attrs, delete_attrs)
        self.assertTrue("description" in mods)
        self.assertEqual(mods["description"]["operation"], ldap3.MODIFY_DELETE)
        self.assertEqual(mods["description"]["value"], [])

        delete_attrs_val = ["description=old value"]
        mods_val = parse_modification_attributes(None, None, delete_attrs_val)
        self.assertTrue("description" in mods_val)
        self.assertEqual(mods_val["description"]["operation"], ldap3.MODIFY_DELETE)
        self.assertEqual(mods_val["description"]["value"], ["old value"])

    def test_format_output_filename(self):
        """Test formatting output filename based on extension"""
        self.assertEqual(format_output_filename("test", "json"), "test.json")
        self.assertEqual(format_output_filename("test.json", "json"), "test.json")
        self.assertEqual(format_output_filename("test.txt", "json"), "test.txt.json")
        self.assertEqual(format_output_filename("archive.tar", "gz"), "archive.tar.gz")
        self.assertEqual(format_output_filename("test.", "json"), "test..json")

    def test_validate_search_filter_valid(self):
        """Test validation of valid LDAP search filters"""
        self.assertTrue(validate_search_filter("(cn=user)"))
        self.assertTrue(validate_search_filter("(objectClass=*)"))
        self.assertTrue(validate_search_filter("(&(cn=user)(sn=Smith))"))
        self.assertTrue(validate_search_filter("(|(cn=user)(cn=admin))"))
        self.assertTrue(validate_search_filter("(!(cn=user))"))
        self.assertTrue(validate_search_filter("(cn>=A)"))
        self.assertTrue(validate_search_filter("(cn<=Z)"))
        self.assertTrue(validate_search_filter("(cn~=user)"))
        self.assertTrue(
            validate_search_filter("(&(objectClass=person)(|(cn=user)(mail=user@*)))")
        )

    def test_validate_search_filter_invalid(self):
        """Test validation of invalid LDAP search filters"""
        with self.assertRaises(ValueError):
            validate_search_filter("")
        with self.assertRaises(ValueError):
            validate_search_filter("cn=user")  # Missing parens
        with self.assertRaises(ValueError):
            validate_search_filter("(cn=user")  # Unbalanced
        with self.assertRaises(ValueError):
            validate_search_filter("()")  # Empty
        with self.assertRaises(ValueError):
            validate_search_filter("(&)")  # Compound with no sub-filters

    def test_validate_dn_valid(self):
        """Test validation of valid DNs"""
        self.assertTrue(validate_dn("cn=user,dc=example,dc=com"))
        self.assertTrue(validate_dn("ou=people,dc=example,dc=com"))
        self.assertTrue(validate_dn("uid=admin,ou=system"))

    def test_validate_dn_invalid(self):
        """Test validation of invalid DNs"""
        with self.assertRaises(ValueError):
            validate_dn("")
        with self.assertRaises(ValueError):
            validate_dn("   ")

    def test_parse_attributes(self):
        """Test parsing of attribute list"""
        self.assertEqual(parse_attributes("cn"), ["cn"])
        self.assertEqual(parse_attributes("cn,sn,mail"), ["cn", "sn", "mail"])
        self.assertEqual(parse_attributes("cn, sn, mail"), ["cn", "sn", "mail"])
        self.assertEqual(parse_attributes(None), [])
        self.assertEqual(parse_attributes(""), [])

    def test_handle_error_response(self):
        """Test error response handling"""
        with self.assertRaisesRegex(RuntimeError, "LDAP operation failed - Test Error"):
            handle_error_response("Test Error", "LDAP operation failed")

    def test_safe_get_password(self):
        """Test secure password retrieval"""
        with patch(
            "getpass.getpass", return_value="prompted_secret"
        ) as mock_getpass_direct:
            password = safe_get_password("Enter test password: ")
            mock_getpass_direct.assert_called_once_with("Enter test password: ")
            self.assertEqual(password, "prompted_secret")

    def test_add_entry(self):
        """Test adding a new LDAP entry"""
        self.mock_conn.add.return_value = True
        attributes_with_oc = {
            "objectClass": ["person"],
            "cn": ["testuser"],
            "sn": ["User"],
        }

        result = add_entry(
            self.mock_conn, "cn=testuser,dc=example,dc=com", attributes_with_oc
        )
        self.assertTrue(result)
        self.mock_conn.add.assert_called_with(
            "cn=testuser,dc=example,dc=com",
            ["person"],
            {"cn": ["testuser"], "sn": ["User"]},
            controls=None,
        )

        self.mock_conn.add.return_value = False
        with self.assertRaisesRegex(
            RuntimeError,
            "LDAP Add operation failed for cn=testuser,dc=example,dc=com: mocked error",
        ):
            add_entry(
                self.mock_conn,
                "cn=testuser,dc=example,dc=com",
                {"objectClass": ["person"], "cn": ["entryAlreadyExists"]},
            )

    def test_delete_entry(self):
        """Test deleting an LDAP entry"""
        self.mock_conn.delete.return_value = True
        # Test non-recursive delete first
        result_non_recursive = delete_entry(
            self.mock_conn, "cn=testuser,dc=example,dc=com"
        )
        self.assertTrue(result_non_recursive)
        self.mock_conn.delete.assert_called_once_with(
            "cn=testuser,dc=example,dc=com", controls=None
        )

        # Test recursive delete (optimized: single SUBTREE search)
        self.mock_conn.reset_mock()
        self.mock_conn.delete.return_value = True

        parent_dn = "cn=testuser,dc=example,dc=com"
        child_entry1_dn = f"cn=child1,{parent_dn}"
        child_entry2_dn = f"cn=child2,{parent_dn}"

        # Mock entries returned by a single SUBTREE search (includes root + children)
        parent_entry = MagicMock(spec=ldap3.Entry)
        parent_entry.entry_dn = parent_dn
        child_entry1 = MagicMock(spec=ldap3.Entry)
        child_entry1.entry_dn = child_entry1_dn
        child_entry2 = MagicMock(spec=ldap3.Entry)
        child_entry2.entry_dn = child_entry2_dn

        self.mock_conn.search.return_value = True
        self.mock_conn.entries = [parent_entry, child_entry1, child_entry2]

        result_recursive = delete_entry(self.mock_conn, parent_dn, recursive=True)
        self.assertTrue(result_recursive)

        # Should be a single SUBTREE search
        self.mock_conn.search.assert_called_once_with(
            search_base=parent_dn,
            search_filter="(objectClass=*)",
            search_scope=ldap3.SUBTREE,
            attributes=[],
            controls=None,
        )

        # Children should be deleted before parent (deepest first)
        # Then the parent is deleted by the final connection.delete() call
        # Total deletes: 2 children + 1 parent = 3
        self.assertEqual(self.mock_conn.delete.call_count, 3)

    def test_modify_entry(self):
        """Test modifying an LDAP entry"""
        self.mock_conn.modify.return_value = True
        ldap3_formatted_mods = {
            "mail": [(ldap3.MODIFY_REPLACE, ["new@example.com"])],
            "title": [(ldap3.MODIFY_ADD, ["Manager"])],
        }

        result = modify_entry(
            self.mock_conn, "cn=testuser,dc=example,dc=com", ldap3_formatted_mods
        )
        self.assertTrue(result)
        self.mock_conn.modify.assert_called_with(
            "cn=testuser,dc=example,dc=com", ldap3_formatted_mods, controls=None
        )

        self.mock_conn.modify.return_value = False
        with self.assertRaisesRegex(
            RuntimeError,
            "LDAP Modify operation failed for cn=testuser,dc=example,dc=com: mocked error",
        ):
            modify_entry(
                self.mock_conn,
                "cn=testuser,dc=example,dc=com",
                {"mail": [(ldap3.MODIFY_REPLACE, ["noSuchAttribute"])]},
            )


if __name__ == "__main__":
    unittest.main()

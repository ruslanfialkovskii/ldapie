#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script for LDAPie with mock LDAP server
"""

import json
import sys
import time

import ldap3
from rich.panel import Panel
from rich.syntax import Syntax

from .. import output, schema, search
from ..ldapie import console
from .mock_server import MockLdapServer


def display_demo_header():
    console.print("[bold]LDAPie automated demo with mock LDAP server[/bold]\n")


def display_command(cmd):
    console.print("\n[bold cyan]Running command:[/bold cyan]")
    console.print(Panel(cmd, expand=False))
    time.sleep(1)  # Pause for effect


def section_header(title):
    console.print(f"\n[bold magenta]{'=' * 20} {title} {'=' * 20}[/bold magenta]\n")


def pause_demo(auto_mode=True):
    """Pause the demo and wait for user input"""
    if auto_mode:
        # Just add a small visual separator in auto mode
        console.print("\n")
        return

    console.print(
        "\n[bold yellow]Press Enter to continue or 'q' to quit...[/bold yellow]"
    )
    user_input = input()
    if user_input.lower() == "q":
        console.print(
            "\n[bold green]Demo ended by user. Thanks for trying LDAPie![/bold green]"
        )
        sys.exit(0)


def interactive_choice(options, prompt_text="Select an option:"):
    """Present an interactive choice to the user"""
    console.print(f"\n[bold cyan]{prompt_text}[/bold cyan]")
    for i, option in enumerate(options, 1):
        console.print(f"  [cyan]{i}.[/cyan] {option}")

    console.print("\n[yellow]Enter your choice (or 'q' to quit):[/yellow]")
    choice = input()

    if choice.lower() == "q":
        console.print(
            "\n[bold green]Demo ended by user. Thanks for trying LDAPie![/bold green]"
        )
        sys.exit(0)

    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(options):
            return choice_idx
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            return interactive_choice(options, prompt_text)
    except ValueError:
        console.print("[bold red]Invalid choice. Please try again.[/bold red]")
        return interactive_choice(options, prompt_text)


def run_demo():
    """Run the LDAPie demo with mock LDAP server"""
    display_demo_header()

    # Create mock server
    section_header("Setting up mock LDAP server")
    console.print("Initializing mock LDAP server with sample data...")
    mock_server = MockLdapServer()
    conn = mock_server.get_connection()
    server = mock_server.server

    console.print("[green]✓[/green] Mock LDAP server ready with sample data")

    # Run all demos in sequence
    section_header("Running all demos sequentially")

    # 1. Basic Search
    basic_search_demo(conn)

    # 2. Search with Filtering
    filtered_search_demo(
        conn, auto_choice=0
    )  # Automatically use the first filter option

    # 3. Output Formats
    output_formats_demo(conn, auto_choice=0)  # Use rich text format

    # 4. Server Information
    server_info_demo(server, conn)

    # 5. Entry Comparison
    entry_comparison_demo(conn)

    # 6. Tree View
    tree_view_demo(conn)

    # 7. Advanced LDAP Operations
    advanced_operations_demo(conn, auto_choice=0)  # Add a new user

    # 8. Batch Operations
    batch_operations_demo(conn)

    # 9. Interactive Shell (just show example, don't run interactive)
    interactive_shell_demo(server, conn)

    # End the demo
    section_header("Demo Complete")
    console.print(
        "\n[bold green]Automated demo complete! You've seen all the functionality of LDAPie.[/bold green]"
    )


def basic_search_demo(conn):
    """Demo basic search functionality"""
    section_header("Basic Search")
    display_command(
        "ldapie search ldap.example.com 'dc=example,dc=com' '(objectClass=*)'"
    )

    conn.search("dc=example,dc=com", "(objectClass=*)", attributes=["*"])
    output.output_rich(conn.entries, console)

    pause_demo()


def filtered_search_demo(conn, auto_choice=None):
    """Demo filtered search functionality"""
    section_header("Search with Filtering")

    filter_options = [
        "(uid=*) - All users with UID",
        "(objectClass=inetOrgPerson) - All person entries",
        "(title=*Manager*) - People with Manager in title",
        "(&(objectClass=inetOrgPerson)(uid=j*)) - Users with UID starting with j",
    ]

    if auto_choice is not None:
        choice = auto_choice
        console.print(
            f"[cyan]Automatically selecting filter: {filter_options[choice]}[/cyan]"
        )
    else:
        choice = interactive_choice(filter_options, "Select a search filter:")

    ldap_filter = filter_options[choice].split(" - ")[0]
    display_command(
        f"ldapie search ldap.example.com 'ou=people,dc=example,dc=com' '{ldap_filter}'"
    )

    conn.search("ou=people,dc=example,dc=com", ldap_filter, attributes=["*"])
    output.output_rich(conn.entries, console)

    pause_demo()


def output_formats_demo(conn, auto_choice=None):
    """Demo different output formats"""
    section_header("Output Formats")

    format_options = ["Rich text (default)", "JSON", "LDIF", "CSV"]

    conn.search("ou=people,dc=example,dc=com", "(objectClass=*)", attributes=["*"])
    entries = conn.entries

    if auto_choice is not None:
        choice = auto_choice
        console.print(
            f"[cyan]Automatically selecting output format: {format_options[choice]}[/cyan]"
        )
    else:
        choice = interactive_choice(format_options, "Select an output format:")

    if choice == 0:  # Rich text
        display_command("ldapie search ldap.example.com 'ou=people,dc=example,dc=com'")
        output.output_rich(entries, console)
    elif choice == 1:  # JSON
        display_command(
            "ldapie search ldap.example.com 'ou=people,dc=example,dc=com' --json"
        )
        output.output_json(entries)
    elif choice == 2:  # LDIF
        display_command(
            "ldapie search ldap.example.com 'ou=people,dc=example,dc=com' --ldif"
        )
        output.output_ldif(entries)
    elif choice == 3:  # CSV
        display_command(
            "ldapie search ldap.example.com 'ou=people,dc=example,dc=com' --csv"
        )
        output.output_csv(entries)

    pause_demo()


def server_info_demo(server, conn):
    """Demo server information display"""
    section_header("Server Information")
    display_command("ldapie info ldap.example.com")

    schema.output_server_info_rich(server, console)

    pause_demo()


def entry_comparison_demo(conn):
    """Demo entry comparison"""
    section_header("Entry Comparison")
    display_command(
        "ldapie compare ldap.example.com 'uid=jdoe,ou=people,dc=example,dc=com' 'uid=jsmith,ou=people,dc=example,dc=com'"
    )

    search.compare_entries(
        conn,
        "uid=jdoe,ou=people,dc=example,dc=com",
        "uid=jsmith,ou=people,dc=example,dc=com",
        [],
        console,
    )

    pause_demo()


def tree_view_demo(conn):
    """Demo tree view of LDAP data"""
    section_header("Tree View")
    display_command("ldapie search ldap.example.com 'dc=example,dc=com' --tree")

    conn.search("dc=example,dc=com", "(objectClass=*)", attributes=["*"])
    output.output_tree(conn.entries, "dc=example,dc=com", console)

    pause_demo()


def advanced_operations_demo(conn, auto_choice=None):
    """Demo advanced LDAP operations like add, modify, delete"""
    section_header("Advanced LDAP Operations")

    operation_options = [
        "Add a new user",
        "Modify an existing user",
        "Delete a user",
        "Rename/Move an entry",
    ]

    if auto_choice is not None:
        choice = auto_choice
        console.print(
            f"[cyan]Automatically selecting operation: {operation_options[choice]}[/cyan]"
        )
    else:
        choice = interactive_choice(operation_options, "Select an operation:")

    if choice == 0:  # Add a new user
        display_command(
            "ldapie add ldap.example.com 'uid=testuser,ou=people,dc=example,dc=com' --class inetOrgPerson --attr cn=Test --attr sn=User --attr uid=testuser"
        )

        # Show the add operation
        console.print("\n[bold]Adding a new user:[/bold]")
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        attrs = {
            "objectClass": ["inetOrgPerson"],
            "cn": "Test User",
            "sn": "User",
            "uid": "testuser",
            "mail": "testuser@example.com",
        }

        conn.add(user_dn, attributes=attrs)
        console.print(f"[green]✓[/green] Added user: {user_dn}")

        # Show the new entry
        conn.search(user_dn, "(objectClass=*)", attributes=["*"])
        output.output_rich(conn.entries, console)

    elif choice == 1:  # Modify an existing user
        display_command(
            "ldapie modify ldap.example.com 'uid=jdoe,ou=people,dc=example,dc=com' --add title='Senior Developer' --replace mail=john.doe.updated@example.com"
        )

        # Show the modify operation
        console.print("\n[bold]Modifying an existing user:[/bold]")
        user_dn = "uid=jdoe,ou=people,dc=example,dc=com"

        # Show before
        console.print("[cyan]Before modification:[/cyan]")
        conn.search(user_dn, "(objectClass=*)", attributes=["*"])
        output.output_rich(conn.entries, console)

        # Perform modification
        changes = {
            "title": [(ldap3.MODIFY_REPLACE, ["Senior Developer"])],
            "mail": [(ldap3.MODIFY_REPLACE, ["john.doe.updated@example.com"])],
        }
        conn.modify(user_dn, changes)
        console.print(f"[green]✓[/green] Modified user: {user_dn}")

        # Show after
        console.print("[cyan]After modification:[/cyan]")
        conn.search(user_dn, "(objectClass=*)", attributes=["*"])
        output.output_rich(conn.entries, console)

    elif choice == 2:  # Delete a user
        display_command(
            "ldapie delete ldap.example.com 'uid=mwhite,ou=people,dc=example,dc=com'"
        )

        # Show the delete operation
        console.print("\n[bold]Deleting a user:[/bold]")
        user_dn = "uid=mwhite,ou=people,dc=example,dc=com"

        # Show entry to be deleted
        console.print("[cyan]Entry to be deleted:[/cyan]")
        conn.search(user_dn, "(objectClass=*)", attributes=["*"])
        output.output_rich(conn.entries, console)

        # Perform deletion
        conn.delete(user_dn)
        console.print(f"[green]✓[/green] Deleted user: {user_dn}")

        # Verify deletion
        conn.search("ou=people,dc=example,dc=com", "(uid=mwhite)", attributes=["*"])
        if not conn.entries:
            console.print("[green]✓[/green] Entry no longer exists")

    elif choice == 3:  # Rename/Move an entry
        display_command(
            "ldapie rename ldap.example.com 'uid=jsmith,ou=people,dc=example,dc=com' 'uid=jsmith-renamed'"
        )

        # Show the rename operation
        console.print("\n[bold]Renaming an entry:[/bold]")
        old_dn = "uid=jsmith,ou=people,dc=example,dc=com"
        new_rdn = "uid=jsmith-renamed"

        # Show entry to be renamed
        console.print("[cyan]Entry to be renamed:[/cyan]")
        conn.search(old_dn, "(objectClass=*)", attributes=["*"])
        output.output_rich(conn.entries, console)

        # Perform rename
        conn.modify_dn(old_dn, new_rdn)
        console.print(
            f"[green]✓[/green] Renamed from {old_dn} to {new_rdn},ou=people,dc=example,dc=com"
        )

        # Show renamed entry
        conn.search(
            "ou=people,dc=example,dc=com", "(uid=jsmith-renamed)", attributes=["*"]
        )
        output.output_rich(conn.entries, console)

    pause_demo()


def batch_operations_demo(conn):
    """Demo batch operations like exporting/importing data"""
    section_header("Batch Operations")

    # Export all entries to JSON
    console.print("[bold]Exporting all entries to JSON:[/bold]")
    display_command(
        "ldapie search ldap.example.com 'dc=example,dc=com' --json --output all_entries.json"
    )

    conn.search("dc=example,dc=com", "(objectClass=*)", attributes=["*"])
    json_data = []
    for entry in conn.entries:
        entry_dict = {"dn": entry.entry_dn}
        for attr_name in entry.entry_attributes:
            if len(entry[attr_name].values) == 1:
                # Single value
                entry_dict[attr_name] = entry[attr_name].value
            else:
                # Multi-value
                entry_dict[attr_name] = list(entry[attr_name].values)
        json_data.append(entry_dict)

    console.print(
        Syntax(
            json.dumps(json_data[:2], indent=2, default=str),
            "json",
            theme="monokai",
            line_numbers=True,
        )
    )
    console.print(f"[green]✓[/green] Exported {len(json_data)} entries to JSON")

    # Import from LDIF demo
    console.print("\n[bold]Importing entries from LDIF:[/bold]")
    display_command("ldapie import ldap.example.com new_users.ldif")

    console.print("[cyan]Sample LDIF for import:[/cyan]")
    sample_ldif = "\n".join(
        [
            "version: 1",
            "",
            "dn: uid=newuser1,ou=people,dc=example,dc=com",
            "objectClass: inetOrgPerson",
            "cn: New User 1",
            "sn: User",
            "uid: newuser1",
            "mail: newuser1@example.com",
        ]
    )
    console.print(Syntax(sample_ldif, "text", theme="monokai", line_numbers=True))

    pause_demo()


def interactive_shell_demo(server, conn):
    """Demo interactive shell functionality"""
    section_header("Interactive Shell")
    display_command(
        "ldapie interactive --host ldap.example.com --base 'dc=example,dc=com'"
    )

    console.print("[bold]Interactive Mode Example:[/bold]")
    console.print(Panel("""
[cyan]ldapie>[/cyan] connect ldap.example.com 389 cn=admin,dc=example,dc=com --starttls
Enter password for cn=admin,dc=example,dc=com:
[green]Connected to ldap.example.com[/green]

[cyan]ldapie>[/cyan] base dc=example,dc=com
Base DN set to: dc=example,dc=com

[cyan]ldapie>[/cyan] search (uid=j*) cn mail title
[Displaying search results...]

[cyan]ldapie>[/cyan] schema inetOrgPerson
[Displaying the object class...]

[cyan]ldapie>[/cyan] search ?
[Context help for the search command...]

[cyan]ldapie>[/cyan] history
[Recent filters, base DNs and hosts...]
    """))

    console.print("\n[bold]Shell Completion:[/bold]")
    console.print(Panel("""
# Install completion for the current shell (bash, zsh or fish)
[cyan]$[/cyan] ldapie --install-completion

# Show the line to add to the shell config instead
[cyan]$[/cyan] ldapie --show-completion
    """))

    pause_demo()

    # In auto mode, we don't do the interactive session
    console.print("[cyan]Skipping interactive session in automated demo mode[/cyan]")

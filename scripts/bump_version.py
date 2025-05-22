#!/usr/bin/env python3
"""
Version bumping script for LDAPie.

This script updates the version number in the project files and manages the changelog.
"""

import argparse
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

def parse_args():
    parser = argparse.ArgumentParser(description="Bump version for LDAPie")
    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major"],
        help="The type of version bump to perform"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Automatically commit changes after version bump"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push changes to remote after commit (implies --auto-commit)"
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create git tag for the new version (implies --auto-commit)"
    )
    parser.add_argument(
        "--changelog-message",
        type=str,
        help="Message to add to changelog (optional)",
        default=""
    )
    return parser.parse_args()

def get_current_version() -> str:
    """
    Get the current version from __init__.py
    """
    init_file = Path("src/ldapie/__init__.py")
    if not init_file.exists():
        raise FileNotFoundError(f"Could not find {init_file}")
    
    content = init_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    
    if not match:
        raise ValueError("Could not find version string in __init__.py")
    
    return match.group(1)

def calculate_new_version(current_version: str, bump_type: str) -> str:
    """
    Calculate the new version based on bump type
    """
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

def update_version_in_file(file_path: str, current_version: str, new_version: str, dry_run: bool = False) -> bool:
    """
    Update version in a file.
    Returns True if changes were made, False otherwise.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Warning: {file_path} does not exist, skipping")
        return False
    
    content = path.read_text()
    updated_content = content.replace(current_version, new_version)
    
    if content == updated_content:
        print(f"No changes needed in {file_path}")
        return False
    
    if dry_run:
        print(f"Would update version in {file_path} from {current_version} to {new_version}")
    else:
        path.write_text(updated_content)
        print(f"Updated version in {file_path} from {current_version} to {new_version}")
    
    return True

def get_list_of_version_files(current_version: str) -> List[str]:
    """
    Get a list of files that potentially contain version information
    """
    # Basic list of files to check
    files_to_check = [
        "src/ldapie/__init__.py",
        "pyproject.toml",
        "setup.py",
        "README.md",
        "CONTAINER.md",
    ]
    
    # Filter to only existing files
    return [f for f in files_to_check if Path(f).exists()]

def update_changelog(new_version: str, message: str = "", dry_run: bool = False) -> bool:
    """
    Update the CHANGELOG.md file with a new version entry.
    Returns True if changes were made, False otherwise.
    """
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("Warning: CHANGELOG.md does not exist, creating it")
        if not dry_run:
            changelog_path.write_text("# Changelog\n\nAll notable changes to the LDAPie project will be documented in this file.\n\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\nand this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if message:
        # User provided a custom message
        new_entry = f"# {new_version} ({today})\n\n{message}\n\n"
    else:
        # Standard template
        new_entry = f"# {new_version} ({today})\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n\n"
    
    if dry_run:
        print(f"Would add new entry to CHANGELOG.md for version {new_version}")
        print("New entry would be:")
        print(new_entry)
        return True
    else:
        content = changelog_path.read_text()
        
        # Find position to insert (after header)
        if "# Changelog" in content:
            # Insert after the intro section
            pattern = r"(# Changelog.*?adheres to \[Semantic Versioning\].*?\n\n)"
            if re.search(pattern, content, re.DOTALL):
                updated_content = re.sub(pattern, r"\1" + new_entry, content, flags=re.DOTALL)
            else:
                # Fallback if pattern not found
                updated_content = content.splitlines()
                updated_content.insert(2, new_entry)
                updated_content = "\n".join(updated_content)
        else:
            # No existing changelog format, create new
            header = "# Changelog\n\nAll notable changes to the LDAPie project will be documented in this file.\n\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\nand this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
            updated_content = header + new_entry + content
        
        changelog_path.write_text(updated_content)
        print(f"Updated CHANGELOG.md with entry for version {new_version}")
        return True

def commit_changes(new_version: str, push: bool = False, create_tag: bool = False) -> bool:
    """
    Commit version changes and optionally push and tag
    """
    try:
        # Check if we're in a git repository
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], 
                      check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        
        # Add modified files
        subprocess.run(["git", "add", "src/ldapie/__init__.py", "CHANGELOG.md"], check=True)
        
        # Add optional files if they exist
        for file in ["pyproject.toml", "setup.py", "README.md", "CONTAINER.md"]:
            if Path(file).exists():
                subprocess.run(["git", "add", file], check=True)
        
        # Commit changes
        commit_message = f"Bump version to {new_version}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(f"Committed changes with message: '{commit_message}'")
        
        # Create tag if requested
        if create_tag:
            tag_name = f"v{new_version}"
            subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True)
            print(f"Created tag: {tag_name}")
        
        # Push if requested
        if push:
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("Pushed changes to origin/main")
            
            if create_tag:
                subprocess.run(["git", "push", "origin", f"v{new_version}"], check=True)
                print(f"Pushed tag v{new_version} to origin")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {e}")
        return False

def main():
    args = parse_args()
    
    # If push or tag is specified, enable auto-commit
    if args.push or args.tag:
        args.auto_commit = True
    
    try:
        current_version = get_current_version()
        new_version = calculate_new_version(current_version, args.bump_type)
        
        print(f"Current version: {current_version}")
        print(f"New version: {new_version}")
        
        # Get files to update
        files_to_update = get_list_of_version_files(current_version)
        
        # Update files
        changed_files = []
        for file_path in files_to_update:
            if update_version_in_file(file_path, current_version, new_version, args.dry_run):
                changed_files.append(file_path)
        
        # Update changelog
        changelog_updated = update_changelog(new_version, args.changelog_message, args.dry_run)
        
        if args.dry_run:
            print("\nDry run complete. No changes were made.")
            return 0
        
        if not changed_files and not changelog_updated:
            print("\nNo changes were needed.")
            return 0
        
        print("\nVersion bump complete!")
        
        # Handle git operations if requested
        if args.auto_commit:
            if commit_changes(new_version, args.push, args.tag):
                print("\nGit operations completed successfully.")
            else:
                print("\nGit operations failed. Manual intervention required.")
                return 1
        else:
            print("\nNext steps:")
            print(f"1. Edit CHANGELOG.md to document changes in version {new_version}")
            print(f"2. Commit changes: git commit -am 'Bump version to {new_version}'")
            print(f"3. Create tag: git tag -a v{new_version} -m 'Release v{new_version}'")
            print("4. Push changes: git push origin main && git push origin --tags")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

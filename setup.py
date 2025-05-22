#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
import re

# Read the version from the main module
version_file_paths = [
    os.path.join("src", "ldapie", "__init__.py"),  # Check if it's in a package
    os.path.join("src", "ldapie.py"),              # Check original path
    os.path.join("ldapie", "__init__.py"),         # Check another common location
    "ldapie.py"                                    # Check root directory
]

version = None
for path in version_file_paths:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
                if version_match:
                    version = version_match.group(1)
                    print(f"Found version {version} in {path}")
                    break
        except Exception as e:
            print(f"Error reading {path}: {e}")

if not version:
    # Default version if not found
    version = "dev"
    print(f"Warning: Unable to find version string, using default: {version}")

# Read long description from README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Define requirements directly to ensure they're installed
requirements = [
    "ldap3>=2.9,<3.0",
    "rich>=12.0.0",
    "click>=7.0",
    "pydantic>=1.9.0",
    "typer>=0.6.0",
    "pyyaml>=6.0",
    "cryptography>=38.0.0",
    "python-dotenv>=0.20.0",
    "python-Levenshtein>=0.20.0"
]

setup(
    name="ldapie",
    version=version,
    description="A modern LDAP client command-line interface tool inspired by HTTPie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LDAPie Team",
    author_email="ruslan.fialkovsky@gmail.com",
    url="https://github.com/ruslanfialkovskii/ldapie",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
        "Topic :: Utilities",
    ],
    keywords="ldap, cli, directory, admin, tool",
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "ldapie=ldapie.ldapie:cli",
        ],
    },
    # Using entry_points above instead of scripts
    project_urls={
        "Bug Reports": "https://github.com/ruslanfialkovskii/ldapie/issues",
        "Source": "https://github.com/ruslanfialkovskii/ldapie",
        "Documentation": "https://github.com/ruslanfialkovskii/ldapie#readme",
    },
)

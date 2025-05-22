#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
import re

# Read the version from the main module
with open(os.path.join("src", "ldapie.py"), "r") as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string")

# Read long description from README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ldapie",
    version=version,
    description="A modern LDAP client command-line interface tool inspired by HTTPie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LDAPie Team",
    author_email="author@example.com",
    url="https://github.com/username/ldapie",
    packages=find_packages(),
    package_dir={"": "src"},
    py_modules=["ldapie", "ldapie_utils", "rich_formatter"],
    scripts=["ldapie"],
    include_package_data=True,
    install_requires=[
        "ldap3>=2.9.0",
        "rich>=10.0.0",
        "click>=8.0.0",
        "pyperclip>=1.8.2",
    ],
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
            "ldapie=src.ldapie:cli",  # Updated from ldapcli to ldapie
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/username/ldapie/issues",
        "Source": "https://github.com/username/ldapie",
        "Documentation": "https://github.com/username/ldapie#readme",
    },
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file support for LDAPie.

Loads settings from ~/.config/ldapie/config.yaml (user-level)
and ./.ldapie.yaml (project-level, takes precedence).

Settings only provide defaults: options given on the command line always win.
The project file is read from the current directory, so it may come from a
cloned repository; it cannot turn off TLS certificate verification.
"""

import os
from typing import Any, Callable, Dict

import yaml

# Supported config keys and their types
CONFIG_KEYS: Dict[str, type] = {
    "default_host": str,
    "default_username": str,
    "use_ssl": bool,
    "port": int,
    "theme": str,
    "starttls": bool,
    "no_verify": bool,
}

# Keys the project-level file may not set (see module docstring)
PROJECT_FORBIDDEN_KEYS = {"no_verify"}

THEMES = ("dark", "light")

PROJECT_CONFIG_PATH = ".ldapie.yaml"


def user_config_path() -> str:
    """Path of the user-level config file (resolved at call time)."""
    return os.path.expanduser("~/.config/ldapie/config.yaml")


def load_config(warn: Callable[[str], None] = lambda message: None) -> Dict[str, Any]:
    """Load configuration from config files.

    Reads user-level config first, then project-level config (which
    overrides user-level values). Unknown keys, values of the wrong type and
    forbidden project-level keys are skipped and reported through ``warn``.

    Returns:
        Dict of configuration values.
    """
    config: Dict[str, Any] = {}
    sources = [
        (user_config_path(), set()),
        (PROJECT_CONFIG_PATH, PROJECT_FORBIDDEN_KEYS),
    ]
    for path, forbidden in sources:
        if os.path.exists(path):
            config.update(
                _validated(path, _load_yaml_file(path, warn), forbidden, warn)
            )
    return config


def _validated(
    path: str,
    data: Dict[str, Any],
    forbidden: set,
    warn: Callable[[str], None],
) -> Dict[str, Any]:
    valid: Dict[str, Any] = {}
    for key, value in data.items():
        expected = CONFIG_KEYS.get(key)
        if expected is None:
            warn(f"{path}: ignoring unknown setting '{key}'")
        elif key in forbidden:
            warn(
                f"{path}: ignoring '{key}'; set it in {user_config_path()} "
                "or pass it on the command line"
            )
        # bool is a subclass of int, so `port: true` must not pass as int
        elif not isinstance(value, expected) or (
            expected is int and isinstance(value, bool)
        ):
            warn(f"{path}: ignoring '{key}': expected {expected.__name__}")
        elif key == "theme" and value not in THEMES:
            warn(f"{path}: ignoring 'theme': expected one of {', '.join(THEMES)}")
        else:
            valid[key] = value
    return valid


def _load_yaml_file(path: str, warn: Callable[[str], None]) -> Dict[str, Any]:
    """Load and parse a YAML config file; problems are reported, not raised."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        warn(f"{path}: could not read config: {e}")
        return {}
    if data is None:
        return {}
    if not isinstance(data, dict):
        warn(f"{path}: expected a mapping of settings")
        return {}
    return data

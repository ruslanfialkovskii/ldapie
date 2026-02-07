#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file support for LDAPie.

Loads settings from ~/.config/ldapie/config.yaml (user-level)
and .ldapie.yaml (project-level, takes precedence).
"""

import os
from typing import Any, Dict

yaml: Any = None
YAML_AVAILABLE = False
try:
    import yaml  # type: ignore[no-redef]
    YAML_AVAILABLE = True
except ImportError:
    pass

# Supported config keys and their types
CONFIG_KEYS = {
    'default_host': str,
    'default_username': str,
    'use_ssl': bool,
    'port': int,
    'theme': str,
    'starttls': bool,
    'no_verify': bool,
}

USER_CONFIG_PATH = os.path.expanduser('~/.config/ldapie/config.yaml')
PROJECT_CONFIG_PATH = '.ldapie.yaml'


def load_config() -> Dict[str, Any]:
    """Load configuration from config files.

    Reads user-level config first, then project-level config (which
    overrides user-level values). Returns an empty dict if no config
    files exist or PyYAML is not installed.

    Returns:
        Dict of configuration values.
    """
    if not YAML_AVAILABLE:
        return {}

    config: Dict[str, Any] = {}

    # Load user config
    if os.path.exists(USER_CONFIG_PATH):
        config.update(_load_yaml_file(USER_CONFIG_PATH))

    # Load project config (overrides user config)
    if os.path.exists(PROJECT_CONFIG_PATH):
        config.update(_load_yaml_file(PROJECT_CONFIG_PATH))

    # Filter to only supported keys
    return {k: v for k, v in config.items() if k in CONFIG_KEYS}


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load and parse a YAML config file.

    Args:
        path: Path to the YAML file.

    Returns:
        Dict of parsed values, or empty dict on error.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data
        return {}
    except (OSError, yaml.YAMLError):
        return {}

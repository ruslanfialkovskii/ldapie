#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file support for LDAPie.

Loads settings from ~/.config/ldapie/config.yaml (user-level) and, with
restrictions, ./.ldapie.yaml (project-level).

Settings only provide defaults: options given on the command line always win.

The project file is read from the current directory, so it may come from a
cloned repository. It can therefore only set the theme and turn TLS on
(``use_ssl``/``starttls``: ``true``); it cannot choose the server, the bind
DN, the port, the CA bundle or the timeout, and it cannot turn TLS or
certificate verification off. Everything else is ignored with a warning.
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
    "ca_cert": str,
    "timeout": int,
}

# The only keys the project-level file may set (see module docstring)...
PROJECT_KEYS = {"theme", "use_ssl", "starttls"}
# ...and these it may only turn on, never off
PROJECT_TRUE_ONLY_KEYS = {"use_ssl", "starttls"}

THEMES = ("dark", "light")

PROJECT_CONFIG_PATH = ".ldapie.yaml"

Reporter = Callable[[str], None]


def user_config_path() -> str:
    """Path of the user-level config file (resolved at call time)."""
    return os.path.expanduser("~/.config/ldapie/config.yaml")


def load_config(
    warn: Reporter = lambda message: None, notice: Reporter = lambda message: None
) -> Dict[str, Any]:
    """Load configuration from config files.

    Reads user-level config first, then project-level config, which can only
    tighten it (theme, and TLS on). Unknown keys, values of the wrong type and
    keys the project-level file may not set are skipped and reported through
    ``warn``. When the project file contributes settings, ``notice`` is told
    which ones, so a file from a cloned repository never applies silently.

    Returns:
        Dict of configuration values.
    """
    config: Dict[str, Any] = {}
    sources = [(user_config_path(), False), (PROJECT_CONFIG_PATH, True)]
    for path, project in sources:
        if not os.path.exists(path):
            continue
        valid = _validated(path, _load_yaml_file(path, warn), project, warn)
        if project and valid:
            notice(f"{path}: using {', '.join(sorted(valid))}")
        config.update(valid)
    return config


def _validated(
    path: str, data: Dict[str, Any], project: bool, warn: Reporter
) -> Dict[str, Any]:
    valid: Dict[str, Any] = {}
    for key, value in data.items():
        expected = CONFIG_KEYS.get(key)
        if expected is None:
            warn(f"{path}: ignoring unknown setting '{key}'")
        elif project and key not in PROJECT_KEYS:
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
        elif key in ("port", "timeout") and isinstance(value, int) and value < 1:
            warn(f"{path}: ignoring '{key}': expected a positive number")
        elif project and key in PROJECT_TRUE_ONLY_KEYS and value is False:
            warn(
                f"{path}: ignoring '{key}: false'; a project file can only turn TLS on"
            )
        else:
            valid[key] = value
    return valid


def _load_yaml_file(path: str, warn: Reporter) -> Dict[str, Any]:
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

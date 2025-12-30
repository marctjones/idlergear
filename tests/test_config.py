"""Tests for configuration management."""

import os

import pytest

from idlergear.config import get_config_value, load_config, save_config, set_config_value


def test_load_config(temp_project):
    """Test loading configuration."""
    config = load_config()

    assert config is not None
    assert "project" in config
    assert config["project"]["name"] == "test-project"


def test_set_and_get_config_value(temp_project):
    """Test setting and getting config values."""
    set_config_value("github.repo", "user/repo")

    value = get_config_value("github.repo")
    assert value == "user/repo"


def test_get_nested_config_value(temp_project):
    """Test getting nested config values."""
    set_config_value("deeply.nested.key", "value")

    value = get_config_value("deeply.nested.key")
    assert value == "value"


def test_get_nonexistent_config_value(temp_project):
    """Test getting a config value that doesn't exist."""
    value = get_config_value("nonexistent.key")
    assert value is None


def test_config_env_fallback(temp_project):
    """Test that github.token falls back to GITHUB_TOKEN env var."""
    os.environ["GITHUB_TOKEN"] = "test-token-123"

    try:
        value = get_config_value("github.token")
        assert value == "test-token-123"
    finally:
        del os.environ["GITHUB_TOKEN"]

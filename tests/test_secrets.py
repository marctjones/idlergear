"""Tests for secrets management."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from idlergear.secrets.storage import (
    EncryptedStorage,
    SecretEntry,
    HAS_CRYPTO,
)
from idlergear.secrets.manager import SecretsManager


# Skip all tests if cryptography not installed
pytestmark = pytest.mark.skipif(not HAS_CRYPTO, reason="cryptography library required")


class TestSecretEntry:
    """Tests for SecretEntry dataclass."""

    def test_create_entry(self):
        """Create a basic secret entry."""
        now = datetime.now()
        entry = SecretEntry(
            name="API_KEY",
            value="secret123",
            created_at=now,
            updated_at=now,
        )
        assert entry.name == "API_KEY"
        assert entry.value == "secret123"

    def test_to_dict(self):
        """Entry can be serialized to dict."""
        now = datetime.now()
        entry = SecretEntry(
            name="TEST",
            value="value",
            created_at=now,
            updated_at=now,
            metadata={"source": "import"},
        )
        data = entry.to_dict()
        assert data["name"] == "TEST"
        assert data["value"] == "value"
        assert data["metadata"]["source"] == "import"

    def test_from_dict(self):
        """Entry can be created from dict."""
        data = {
            "name": "TEST",
            "value": "value",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00",
        }
        entry = SecretEntry.from_dict(data)
        assert entry.name == "TEST"
        assert entry.value == "value"

    def test_masked_preview_long(self):
        """Masked preview shows first and last chars."""
        now = datetime.now()
        entry = SecretEntry(
            name="KEY",
            value="sk-1234567890abcdef",
            created_at=now,
            updated_at=now,
        )
        preview = entry.masked_preview()
        assert preview == "sk-1...cdef"

    def test_masked_preview_short(self):
        """Short values are fully masked."""
        now = datetime.now()
        entry = SecretEntry(
            name="KEY",
            value="short",
            created_at=now,
            updated_at=now,
        )
        preview = entry.masked_preview()
        assert preview == "*****"


class TestEncryptedStorage:
    """Tests for EncryptedStorage backend."""

    def test_not_initialized(self, tmp_path):
        """New storage is not initialized."""
        storage = EncryptedStorage(tmp_path / "secrets")
        assert not storage.is_initialized()

    def test_initialize(self, tmp_path):
        """Initialize creates encrypted store."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        assert storage.is_initialized()
        assert storage.salt_file.exists()

    def test_unlock_correct_password(self, tmp_path):
        """Unlock with correct password succeeds."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        # Create new instance to simulate new session
        storage2 = EncryptedStorage(tmp_path / "secrets")
        assert storage2.unlock("test-password")

    def test_unlock_wrong_password(self, tmp_path):
        """Unlock with wrong password fails."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage2 = EncryptedStorage(tmp_path / "secrets")
        assert not storage2.unlock("wrong-password")

    def test_set_and_get(self, tmp_path):
        """Set and get a secret."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("API_KEY", "secret-value")
        assert storage.get("API_KEY") == "secret-value"

    def test_get_missing(self, tmp_path):
        """Get missing secret returns None."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        assert storage.get("MISSING") is None

    def test_set_updates_existing(self, tmp_path):
        """Set updates existing secret."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("KEY", "value1")
        storage.set("KEY", "value2")
        assert storage.get("KEY") == "value2"

    def test_list_secrets(self, tmp_path):
        """List returns all secret entries."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("KEY1", "val1")
        storage.set("KEY2", "val2")
        storage.set("KEY3", "val3")

        entries = storage.list()
        names = {e.name for e in entries}
        assert names == {"KEY1", "KEY2", "KEY3"}

    def test_delete(self, tmp_path):
        """Delete removes a secret."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("KEY", "value")
        assert storage.delete("KEY")
        assert storage.get("KEY") is None

    def test_delete_missing(self, tmp_path):
        """Delete missing secret returns False."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        assert not storage.delete("MISSING")

    def test_exists(self, tmp_path):
        """Exists checks secret presence."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("KEY", "value")
        assert storage.exists("KEY")
        assert not storage.exists("MISSING")

    def test_persistence(self, tmp_path):
        """Secrets persist across sessions."""
        storage1 = EncryptedStorage(tmp_path / "secrets")
        storage1.initialize("test-password")
        storage1.set("PERSISTENT", "data")

        # New instance with same path
        storage2 = EncryptedStorage(tmp_path / "secrets")
        storage2.unlock("test-password")

        assert storage2.get("PERSISTENT") == "data"

    def test_export_env(self, tmp_path):
        """Export returns all secrets as dict."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("test-password")

        storage.set("KEY1", "val1")
        storage.set("KEY2", "val2")

        env = storage.export_env()
        assert env == {"KEY1": "val1", "KEY2": "val2"}


class TestSecretsManager:
    """Tests for SecretsManager high-level interface."""

    def test_not_initialized(self, tmp_path):
        """Manager reports not initialized for new project."""
        manager = SecretsManager(tmp_path)
        assert not manager.is_initialized()

    def test_initialize(self, tmp_path):
        """Initialize creates secrets store."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        assert manager.is_initialized()

    def test_project_config_created(self, tmp_path):
        """Initialize creates project config."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        assert manager.config_file.exists()

    def test_set_and_get(self, tmp_path):
        """Set and get a secret."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")

        manager.set("API_KEY", "secret")
        assert manager.get("API_KEY") == "secret"

    def test_unlock_required(self, tmp_path):
        """Operations require unlock."""
        manager1 = SecretsManager(tmp_path)
        manager1.initialize("password")
        manager1.set("KEY", "value")

        # New manager instance
        manager2 = SecretsManager(tmp_path)
        with pytest.raises(RuntimeError, match="locked"):
            manager2.get("KEY")

        # After unlock
        manager2.unlock("password")
        assert manager2.get("KEY") == "value"

    def test_import_env_file(self, tmp_path):
        """Import from .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text('API_KEY="secret123"\nDB_HOST=localhost\n')

        manager = SecretsManager(tmp_path)
        manager.initialize("password")

        imported = manager.import_env_file(env_file)
        assert "API_KEY" in imported
        assert "DB_HOST" in imported

        assert manager.get("API_KEY") == "secret123"
        assert manager.get("DB_HOST") == "localhost"

    def test_import_skip_existing(self, tmp_path):
        """Import skips existing secrets without overwrite."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=new-value\n")

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.set("KEY", "original")

        imported = manager.import_env_file(env_file, overwrite=False)
        assert "KEY" not in imported
        assert manager.get("KEY") == "original"

    def test_import_overwrite(self, tmp_path):
        """Import overwrites with flag."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=new-value\n")

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.set("KEY", "original")

        imported = manager.import_env_file(env_file, overwrite=True)
        assert "KEY" in imported
        assert manager.get("KEY") == "new-value"

    def test_export_env_file(self, tmp_path):
        """Export to .env file."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.set("KEY1", "value1")
        manager.set("KEY2", "value2")

        export_path = tmp_path / "exported.env"
        manager.export_env_file(export_path)

        content = export_path.read_text()
        assert "KEY1" in content
        assert "KEY2" in content

    def test_run_preview(self, tmp_path):
        """Get preview of secrets for run."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.set("API_KEY", "sk-1234567890abcdef")

        preview = manager.get_run_preview()
        assert "API_KEY" in preview
        # Should be masked
        assert "1234567890" not in preview["API_KEY"]

    def test_run_with_secrets(self, tmp_path):
        """Run command with secrets injected."""
        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.set("TEST_VAR", "test-value")

        # Run a command that outputs env var
        exit_code = manager.run_with_secrets(
            ["python", "-c", "import os; print(os.environ.get('TEST_VAR', 'missing'))"]
        )
        assert exit_code == 0


class TestEnvFileParsing:
    """Tests for .env file parsing edge cases."""

    def test_import_comments_ignored(self, tmp_path):
        """Comments are ignored in .env files."""
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n")

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        imported = manager.import_env_file(env_file)

        assert len(imported) == 1
        assert "KEY" in imported

    def test_import_empty_lines_ignored(self, tmp_path):
        """Empty lines are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\n\n\nKEY2=value2\n")

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        imported = manager.import_env_file(env_file)

        assert len(imported) == 2

    def test_import_quoted_values(self, tmp_path):
        """Quoted values have quotes removed."""
        env_file = tmp_path / ".env"
        env_file.write_text('DOUBLE="double quoted"\nSINGLE=\'single quoted\'\n')

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.import_env_file(env_file)

        assert manager.get("DOUBLE") == "double quoted"
        assert manager.get("SINGLE") == "single quoted"

    def test_import_escaped_newlines(self, tmp_path):
        """Escaped newlines are unescaped."""
        env_file = tmp_path / ".env"
        env_file.write_text('MULTILINE="line1\\nline2"\n')

        manager = SecretsManager(tmp_path)
        manager.initialize("password")
        manager.import_env_file(env_file)

        assert manager.get("MULTILINE") == "line1\nline2"


class TestSecurityConsiderations:
    """Tests for security-related behavior."""

    def test_salt_file_permissions(self, tmp_path):
        """Salt file has restrictive permissions."""
        import os
        import stat

        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("password")

        mode = os.stat(storage.salt_file).st_mode
        # Check that file is not world or group readable
        assert not mode & stat.S_IRGRP
        assert not mode & stat.S_IROTH

    def test_secrets_file_permissions(self, tmp_path):
        """Secrets file has restrictive permissions."""
        import os
        import stat

        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("password")
        storage.set("KEY", "value")

        mode = os.stat(storage.secrets_file).st_mode
        assert not mode & stat.S_IRGRP
        assert not mode & stat.S_IROTH

    def test_encrypted_file_not_readable(self, tmp_path):
        """Encrypted file cannot be read as plain text."""
        storage = EncryptedStorage(tmp_path / "secrets")
        storage.initialize("password")
        storage.set("API_KEY", "super-secret-value")

        content = storage.secrets_file.read_bytes()
        assert b"super-secret-value" not in content
        assert b"API_KEY" not in content

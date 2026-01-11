"""Encrypted storage backend for secrets."""

from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Use cryptography library for secure encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


@dataclass
class SecretEntry:
    """A stored secret with metadata."""

    name: str
    value: str  # Encrypted value when in storage
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecretEntry":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )

    def masked_preview(self, show_chars: int = 4) -> str:
        """Get a masked preview of the secret value.

        SECURITY: This should only be used for display purposes.
        """
        if len(self.value) <= show_chars * 2:
            return "*" * len(self.value)
        return f"{self.value[:show_chars]}...{self.value[-show_chars:]}"


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2."""
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library required for encryption")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # OWASP recommended minimum
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class EncryptedStorage:
    """Encrypted file-based secrets storage."""

    def __init__(self, storage_path: Path, password: Optional[str] = None):
        """Initialize encrypted storage.

        Args:
            storage_path: Directory to store encrypted files
            password: Master password (will prompt if not provided and needed)
        """
        self.storage_path = storage_path
        self._password = password
        self._fernet: Optional["Fernet"] = None
        self._secrets: dict[str, SecretEntry] = {}
        self._loaded = False

    @property
    def secrets_file(self) -> Path:
        """Path to encrypted secrets file."""
        return self.storage_path / "secrets.enc"

    @property
    def salt_file(self) -> Path:
        """Path to salt file."""
        return self.storage_path / "secrets.salt"

    def is_initialized(self) -> bool:
        """Check if storage has been initialized."""
        return self.salt_file.exists()

    def initialize(self, password: str) -> None:
        """Initialize a new secrets store with password.

        Args:
            password: Master password for encryption
        """
        if not HAS_CRYPTO:
            raise RuntimeError(
                "cryptography library required. Install with: pip install cryptography"
            )

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Generate random salt
        salt = secrets.token_bytes(32)
        self.salt_file.write_bytes(salt)

        # Set restrictive permissions on salt file
        os.chmod(self.salt_file, 0o600)

        # Derive key and create Fernet instance
        key = derive_key(password, salt)
        self._fernet = Fernet(key)
        self._password = password
        self._secrets = {}
        self._loaded = True

        # Save empty secrets file
        self._save()

    def unlock(self, password: str) -> bool:
        """Unlock the secrets store with password.

        Returns:
            True if unlock succeeded, False if wrong password
        """
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography library required for encryption")

        if not self.is_initialized():
            raise RuntimeError("Secrets store not initialized. Run 'init' first.")

        salt = self.salt_file.read_bytes()
        key = derive_key(password, salt)
        self._fernet = Fernet(key)
        self._password = password

        # Try to load and decrypt - will fail if wrong password
        try:
            self._load()
            return True
        except Exception:
            self._fernet = None
            self._password = None
            return False

    def _ensure_unlocked(self) -> None:
        """Ensure storage is unlocked."""
        if self._fernet is None:
            raise RuntimeError("Secrets store is locked. Call unlock() first.")

    def _load(self) -> None:
        """Load secrets from encrypted file."""
        self._ensure_unlocked()

        if not self.secrets_file.exists():
            self._secrets = {}
            self._loaded = True
            return

        encrypted = self.secrets_file.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        data = json.loads(decrypted.decode())

        self._secrets = {}
        for entry_data in data.get("secrets", []):
            entry = SecretEntry.from_dict(entry_data)
            self._secrets[entry.name] = entry

        self._loaded = True

    def _save(self) -> None:
        """Save secrets to encrypted file."""
        self._ensure_unlocked()

        data = {"secrets": [entry.to_dict() for entry in self._secrets.values()]}
        plaintext = json.dumps(data, indent=2).encode()
        encrypted = self._fernet.encrypt(plaintext)

        self.secrets_file.write_bytes(encrypted)
        os.chmod(self.secrets_file, 0o600)

    def set(self, name: str, value: str, metadata: Optional[dict] = None) -> SecretEntry:
        """Set a secret value.

        Args:
            name: Secret name (e.g., API_KEY)
            value: Secret value
            metadata: Optional metadata

        Returns:
            The created/updated SecretEntry
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        now = datetime.now()
        if name in self._secrets:
            entry = self._secrets[name]
            entry.value = value
            entry.updated_at = now
            if metadata:
                entry.metadata.update(metadata)
        else:
            entry = SecretEntry(
                name=name,
                value=value,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._secrets[name] = entry

        self._save()
        return entry

    def get(self, name: str) -> Optional[str]:
        """Get a secret value.

        Args:
            name: Secret name

        Returns:
            The secret value, or None if not found
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        entry = self._secrets.get(name)
        return entry.value if entry else None

    def get_entry(self, name: str) -> Optional[SecretEntry]:
        """Get a secret entry with metadata.

        Args:
            name: Secret name

        Returns:
            The SecretEntry, or None if not found
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        return self._secrets.get(name)

    def list(self) -> list[SecretEntry]:
        """List all secrets (entries, not values).

        Returns:
            List of SecretEntry objects
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        return list(self._secrets.values())

    def delete(self, name: str) -> bool:
        """Delete a secret.

        Args:
            name: Secret name

        Returns:
            True if deleted, False if not found
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        if name not in self._secrets:
            return False

        del self._secrets[name]
        self._save()
        return True

    def exists(self, name: str) -> bool:
        """Check if a secret exists.

        Args:
            name: Secret name

        Returns:
            True if exists
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        return name in self._secrets

    def export_env(self) -> dict[str, str]:
        """Export all secrets as environment variables.

        Returns:
            Dict of name -> value
        """
        self._ensure_unlocked()
        if not self._loaded:
            self._load()

        return {name: entry.value for name, entry in self._secrets.items()}


class KeyringStorage:
    """Storage backend using system keyring (macOS Keychain, GNOME Keyring, etc.)."""

    SERVICE_NAME = "idlergear"

    def __init__(self, project_id: str):
        """Initialize keyring storage for a project.

        Args:
            project_id: Unique identifier for the project
        """
        self.project_id = project_id
        self._keyring: Any = None
        self._check_keyring()

    def _check_keyring(self) -> None:
        """Check if keyring is available."""
        try:
            import keyring

            self._keyring = keyring
        except ImportError:
            self._keyring = None

    def is_available(self) -> bool:
        """Check if system keyring is available."""
        if self._keyring is None:
            return False
        try:
            # Try to access keyring
            self._keyring.get_password(self.SERVICE_NAME, "__test__")
            return True
        except Exception:
            return False

    def _make_key(self, name: str) -> str:
        """Create keyring key from secret name."""
        return f"{self.project_id}:{name}"

    def set(self, name: str, value: str) -> None:
        """Store secret in system keyring."""
        if self._keyring is None:
            raise RuntimeError("keyring library not available")
        self._keyring.set_password(self.SERVICE_NAME, self._make_key(name), value)

    def get(self, name: str) -> Optional[str]:
        """Get secret from system keyring."""
        if self._keyring is None:
            raise RuntimeError("keyring library not available")
        return self._keyring.get_password(self.SERVICE_NAME, self._make_key(name))

    def delete(self, name: str) -> bool:
        """Delete secret from system keyring."""
        if self._keyring is None:
            raise RuntimeError("keyring library not available")
        try:
            self._keyring.delete_password(self.SERVICE_NAME, self._make_key(name))
            return True
        except Exception:
            return False

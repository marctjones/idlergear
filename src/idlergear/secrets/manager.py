"""High-level secrets management interface."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional
import uuid

from .storage import EncryptedStorage, SecretEntry


class SecretsManager:
    """High-level interface for secrets management.

    This is the main API for working with secrets. It handles:
    - Project-scoped secrets
    - Automatic backend selection (keyring vs encrypted file)
    - Password prompting
    - Environment variable injection
    """

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize secrets manager for a project.

        Args:
            project_path: Project directory (defaults to current directory)
        """
        self.project_path = project_path or Path.cwd()
        self._storage: Optional[EncryptedStorage] = None
        self._project_id: Optional[str] = None

    @property
    def config_file(self) -> Path:
        """Path to project secrets config."""
        return self.project_path / ".idlergear" / "secrets.json"

    @property
    def global_secrets_dir(self) -> Path:
        """Path to global secrets storage."""
        return Path.home() / ".idlergear" / "secrets"

    @property
    def project_secrets_dir(self) -> Path:
        """Path to this project's secrets storage."""
        project_id = self._get_or_create_project_id()
        return self.global_secrets_dir / "projects" / project_id

    def _get_or_create_project_id(self) -> str:
        """Get or create unique project ID."""
        if self._project_id is not None:
            return self._project_id

        import json

        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                self._project_id = data.get("project_id")
                if self._project_id:
                    return self._project_id
            except Exception:
                pass

        # Generate new project ID
        self._project_id = str(uuid.uuid4())[:8]
        return self._project_id

    def _save_config(self) -> None:
        """Save project config."""
        import json

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "project_id": self._get_or_create_project_id(),
            "project_name": self.project_path.name,
        }
        self.config_file.write_text(json.dumps(data, indent=2) + "\n")

    def is_initialized(self) -> bool:
        """Check if secrets store is initialized for this project."""
        storage = EncryptedStorage(self.project_secrets_dir)
        return storage.is_initialized()

    def initialize(self, password: str) -> None:
        """Initialize secrets store for this project.

        After initialization, the store is automatically unlocked.

        Args:
            password: Master password for encryption
        """
        # Create project config
        self._save_config()

        # Initialize encrypted storage
        storage = EncryptedStorage(self.project_secrets_dir)
        storage.initialize(password)

        # Store is now initialized and unlocked
        self._storage = storage

    def unlock(self, password: str) -> bool:
        """Unlock the secrets store.

        Args:
            password: Master password

        Returns:
            True if unlock succeeded
        """
        storage = EncryptedStorage(self.project_secrets_dir)
        if storage.unlock(password):
            self._storage = storage
            return True
        return False

    def _ensure_storage(self) -> EncryptedStorage:
        """Ensure storage is available and unlocked."""
        if self._storage is None:
            raise RuntimeError(
                "Secrets store is locked. Call unlock() or use 'idlergear secrets unlock'"
            )
        return self._storage

    def set(
        self, name: str, value: str, metadata: Optional[dict] = None
    ) -> SecretEntry:
        """Set a secret.

        Args:
            name: Secret name (e.g., API_KEY)
            value: Secret value
            metadata: Optional metadata

        Returns:
            Created/updated SecretEntry
        """
        storage = self._ensure_storage()
        return storage.set(name, value, metadata)

    def get(self, name: str) -> Optional[str]:
        """Get a secret value.

        Args:
            name: Secret name

        Returns:
            Secret value or None
        """
        storage = self._ensure_storage()
        return storage.get(name)

    def get_entry(self, name: str) -> Optional[SecretEntry]:
        """Get a secret entry with metadata.

        Args:
            name: Secret name

        Returns:
            SecretEntry or None
        """
        storage = self._ensure_storage()
        return storage.get_entry(name)

    def list(self) -> list[SecretEntry]:
        """List all secrets (metadata only, not values).

        Returns:
            List of SecretEntry objects
        """
        storage = self._ensure_storage()
        return storage.list()

    def delete(self, name: str) -> bool:
        """Delete a secret.

        Args:
            name: Secret name

        Returns:
            True if deleted
        """
        storage = self._ensure_storage()
        return storage.delete(name)

    def exists(self, name: str) -> bool:
        """Check if a secret exists.

        Args:
            name: Secret name

        Returns:
            True if exists
        """
        storage = self._ensure_storage()
        return storage.exists(name)

    def export_env_file(self, path: Path, comment_prefix: str = "# ") -> None:
        """Export secrets to .env format file.

        WARNING: Creates unencrypted file!

        Args:
            path: Output file path
            comment_prefix: Prefix for comment lines
        """
        storage = self._ensure_storage()
        secrets = storage.export_env()

        lines = [
            f"{comment_prefix}Generated by IdlerGear secrets export",
            f"{comment_prefix}WARNING: This file contains unencrypted secrets!",
            f"{comment_prefix}DO NOT commit to version control!",
            "",
        ]

        for name, value in sorted(secrets.items()):
            # Escape special characters in value
            escaped = (
                value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            )
            lines.append(f'{name}="{escaped}"')

        path.write_text("\n".join(lines) + "\n")

    def import_env_file(self, path: Path, overwrite: bool = False) -> list[str]:
        """Import secrets from .env format file.

        Args:
            path: Input file path
            overwrite: Whether to overwrite existing secrets

        Returns:
            List of imported secret names
        """
        storage = self._ensure_storage()
        imported = []

        content = path.read_text()
        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=value or KEY="value"
            if "=" not in line:
                continue

            name, value = line.split("=", 1)
            name = name.strip()

            # Remove quotes if present
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            # Unescape
            value = value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")

            # Check if exists
            if storage.exists(name) and not overwrite:
                continue

            storage.set(name, value)
            imported.append(name)

        return imported

    def run_with_secrets(
        self,
        command: list[str],
        additional_env: Optional[dict[str, str]] = None,
    ) -> int:
        """Run a command with secrets injected as environment variables.

        Args:
            command: Command and arguments to run
            additional_env: Additional environment variables

        Returns:
            Exit code from command
        """
        storage = self._ensure_storage()

        # Build environment
        env = os.environ.copy()
        env.update(storage.export_env())
        if additional_env:
            env.update(additional_env)

        # Run command
        result = subprocess.run(command, env=env)
        return result.returncode

    def get_run_preview(self) -> dict[str, str]:
        """Get preview of what secrets would be injected for a run.

        Returns:
            Dict of secret names to masked values
        """
        storage = self._ensure_storage()
        entries = storage.list()
        return {entry.name: entry.masked_preview() for entry in entries}

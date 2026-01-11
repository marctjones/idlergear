"""Secure local secrets management for IdlerGear."""

from .manager import SecretsManager
from .storage import EncryptedStorage, SecretEntry

__all__ = ["SecretsManager", "EncryptedStorage", "SecretEntry"]

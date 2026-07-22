"""
Secret encryption helpers for data stored at rest (e.g. model connection API keys).

Uses Fernet (symmetric AES) from the ``cryptography`` package. The master key is
resolved from the ``CLEARSWARM_SECRET_KEY`` environment variable; if that is not set,
a key is generated once and persisted to a file next to the SQLite database so the
application works out of the box and encrypted values survive restarts.
"""
import os
import stat
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

# Cached Fernet instance (built lazily on first use).
_fernet: Optional[Fernet] = None

# Default location for the auto-generated key file (same directory as agents.db).
_DEFAULT_KEY_FILE = Path(os.getenv("CLEARSWARM_SECRET_KEY_FILE", ".clearswarm_secret.key"))


def _load_or_create_key() -> bytes:
    """Return the raw Fernet key, from env or a persisted file (creating it if needed)."""
    env_key = os.getenv("CLEARSWARM_SECRET_KEY")
    if env_key:
        return env_key.encode("utf-8")

    key_file = _DEFAULT_KEY_FILE
    if key_file.exists():
        return key_file.read_bytes().strip()

    # Generate a new key and persist it with owner-only permissions.
    key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    try:
        key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        # Best effort on platforms that don't support chmod semantics.
        pass
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string, returning a urlsafe token. Empty input stays empty."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt_secret`. Empty input stays empty."""
    if not token:
        return ""
    return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")

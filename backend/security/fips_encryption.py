"""
FIPS-Compliant Encryption Service — AES-256-GCM + SHA-256 hashing.

Uses the ``cryptography`` library for FIPS-approved algorithms.
"""

import hashlib
import logging
import os
import secrets
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("security.fips_encryption")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _CRYPTO_AVAILABLE = True
except ImportError:
    AESGCM = None  # type: ignore[assignment,misc]
    _CRYPTO_AVAILABLE = False
    logger.warning("cryptography library not installed — FIPS encryption unavailable")


class FIPSEncryption:
    """
    AES-256-GCM encryption with FIPS-compliant hashing.

    Provides symmetric encryption, database field encryption helpers,
    and password hashing via SHA-256 + salt.
    """

    _NONCE_SIZE = 12   # 96-bit nonce for GCM
    _KEY_SIZE = 32     # 256-bit key
    _TAG_SIZE = 16     # 128-bit authentication tag

    def __init__(self):
        if not _CRYPTO_AVAILABLE:
            logger.warning("FIPSEncryption: cryptography library missing")

    # ── Key generation ──────────────────────────────────────────────

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically secure 32-byte AES-256 key."""
        return secrets.token_bytes(FIPSEncryption._KEY_SIZE)

    # ── Encrypt / Decrypt ───────────────────────────────────────────

    @staticmethod
    def encrypt(plaintext: str, key: bytes) -> Dict[str, bytes]:
        """
        Encrypt *plaintext* with AES-256-GCM.

        Returns dict with keys: ``ciphertext``, ``nonce``, ``tag``.
        """
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not installed")

        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        nonce = secrets.token_bytes(FIPSEncryption._NONCE_SIZE)
        aesgcm = AESGCM(key)
        # AESGCM.encrypt returns ciphertext || tag (16 bytes appended)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
        # Split: last 16 bytes are the tag
        ciphertext = ct_with_tag[:-FIPSEncryption._TAG_SIZE]
        tag = ct_with_tag[-FIPSEncryption._TAG_SIZE:]

        return {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "tag": tag,
        }

    @staticmethod
    def decrypt(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> str:
        """
        Decrypt data encrypted with AES-256-GCM.

        Returns the original plaintext string.
        """
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not installed")

        aesgcm = AESGCM(key)
        # AESGCM.decrypt expects ciphertext || tag concatenated
        ct_with_tag = ciphertext + tag
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, None)
        return plaintext.decode("utf-8")

    # ── Database field helpers ───────────────────────────────────────

    def encrypt_field(self, value: Any, field_name: str) -> Dict[str, str]:
        """
        Encrypt a database field value.

        Returns a JSON-serialisable dict with base64-encoded components.
        """
        import base64

        key = self._derive_field_key(field_name)
        plaintext = str(value) if value is not None else ""

        result = self.encrypt(plaintext, key)
        return {
            "ciphertext": base64.b64encode(result["ciphertext"]).decode("ascii"),
            "nonce": base64.b64encode(result["nonce"]).decode("ascii"),
            "tag": base64.b64encode(result["tag"]).decode("ascii"),
        }

    def decrypt_field(self, encrypted_value: Dict[str, str], field_name: str) -> str:
        """
        Decrypt a database field previously encrypted with ``encrypt_field``.
        """
        import base64

        key = self._derive_field_key(field_name)
        ciphertext = base64.b64decode(encrypted_value["ciphertext"])
        nonce = base64.b64decode(encrypted_value["nonce"])
        tag = base64.b64decode(encrypted_value["tag"])

        return self.decrypt(ciphertext, key, nonce, tag)

    # ── Password hashing ────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using SHA-256 with a random salt.

        Returns a string in the format ``salt_hex$hash_hex``.
        """
        salt = secrets.token_bytes(16)
        pw_hash = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return f"{salt.hex()}${pw_hash}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a hash produced by ``hash_password``.
        """
        try:
            salt_hex, expected_hash = hashed.split("$", 1)
            salt = bytes.fromhex(salt_hex)
            computed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
            return secrets.compare_digest(computed, expected_hash)
        except (ValueError, AttributeError):
            return False

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _derive_field_key(field_name: str) -> bytes:
        """
        Derive a deterministic 32-byte key from the field name.

        Uses SHA-256 so the same field_name always produces the same key,
        enabling decryption without storing the key per-field.
        """
        return hashlib.sha256(f"dutchkem-fips-v1-{field_name}".encode("utf-8")).digest()

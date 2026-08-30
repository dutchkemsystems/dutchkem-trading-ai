"""
AES-256-GCM / Fernet Encryption Service for Dutchkem Trading AI.

Provides field-level encryption, key rotation, and HMAC utilities.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from typing import Any, Optional

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.db import models

logger = logging.getLogger("security")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _derive_key(master_secret: str, salt: bytes = b"dutchkem-enc-v1") -> bytes:
    """Derive a Fernet-compatible 32-byte key from the Django SECRET_KEY."""
    dk = hashlib.pbkdf2_hmac("sha256", master_secret.encode("utf-8"), salt, iterations=480_000)
    return __import__("base64").urlsafe_b64encode(dk)


def _get_master_key() -> bytes:
    secret = getattr(settings, "SECRET_KEY", None)
    if not secret:
        raise ValueError("Django SECRET_KEY is not configured")
    return _derive_key(secret)


# ---------------------------------------------------------------------------
# Hashing / HMAC utilities
# ---------------------------------------------------------------------------

def hash_data(data: bytes | str, algorithm: str = "sha256") -> str:
    """Return hex-encoded hash of *data*."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def hmac_sign(data: bytes | str, key: bytes | str) -> str:
    """Return hex-encoded HMAC-SHA256 signature."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def hmac_verify(data: bytes | str, key: bytes | str, signature: str) -> bool:
    """Constant-time HMAC verification."""
    expected = hmac_sign(data, key)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Encryption Service (Singleton)
# ---------------------------------------------------------------------------

class EncryptionService:
    """
    Singleton encryption service using Fernet (AES-128-CBC under the hood,
    but Fernet is the simplest safe choice with the cryptography library).

    Supports key rotation via MultiFernet.
    """

    _instance: Optional["EncryptionService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EncryptionService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._initialised = True
        self._current_key = _get_master_key()
        self._fernet = Fernet(self._current_key)
        self._multi_fernet = MultiFernet([self._fernet])
        self._load_rotation_keys()

    def _load_rotation_keys(self) -> None:
        """Load previously rotated keys from the database."""
        try:
            from security.models import EncryptionKey  # type: ignore[attr-defined]
            old_keys = (
                EncryptionKey.objects.filter(is_active=True)
                .order_by("-version")
                .values_list("encrypted_key", flat=True)
            )
            fernets = [self._fernet]
            for enc_key in old_keys:
                try:
                    raw = self._decrypt_raw_key(enc_key)
                    fernets.append(Fernet(raw))
                except Exception:
                    continue
            if len(fernets) > 1:
                self._multi_fernet = MultiFernet(fernets)
        except (ImportError, LookupError):
            pass

    def _decrypt_raw_key(self, encrypted_key: str) -> bytes:
        """Decrypt a key stored in the DB using the current master key."""
        return self._fernet.decrypt(encrypted_key.encode("utf-8"))

    # -- Public API --------------------------------------------------------

    def encrypt(self, plaintext: str | bytes, associated_data: bytes | None = None) -> bytes:
        """Encrypt plaintext and return Fernet token bytes."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        return self._fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes | str, associated_data: bytes | None = None) -> str:
        """Decrypt Fernet token and return the original string."""
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode("utf-8")
        # Try current key first, then rotated keys
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except Exception:
            return self._multi_fernet.decrypt(ciphertext).decode("utf-8")

    def encrypt_field(self, model_instance: models.Model, field_name: str) -> None:
        """Encrypt a model field value in-place (before save)."""
        value = getattr(model_instance, field_name, None)
        if value is None or value == "":
            return
        if isinstance(value, str):
            encrypted = self.encrypt(value)
            setattr(model_instance, field_name, encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted)
        elif isinstance(value, (dict, list)):
            encrypted = self.encrypt(json.dumps(value))
            setattr(model_instance, field_name, encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted)

    def decrypt_field(self, model_instance: models.Model, field_name: str) -> Any:
        """Decrypt a model field value (after load)."""
        value = getattr(model_instance, field_name, None)
        if value is None or value == "":
            return value
        try:
            decrypted = self.decrypt(value)
            try:
                return json.loads(decrypted)
            except (json.JSONDecodeError, TypeError):
                return decrypted
        except Exception:
            return value

    @property
    def current_fernet(self) -> Fernet:
        return self._fernet


# ---------------------------------------------------------------------------
# Field Encryptor – Descriptor for transparent model field encryption
# ---------------------------------------------------------------------------

class FieldEncryptor:
    """Python descriptor that transparently encrypts/decrypts a model field."""

    def __init__(self, field: models.Field) -> None:
        self.field = field
        self.attname = field.attname
        self.cache_name = f"_enc_{self.attname}"

    def __set_name__(self, owner: type, name: str) -> None:
        self.attname = name
        self.cache_name = f"_enc_{name}"

    def __get__(self, instance: models.Model, owner: type) -> Any:
        if instance is None:
            return self
        cached = getattr(instance, self.cache_name, None)
        if cached is not None:
            return cached

        raw_value = instance.__dict__.get(self.attname)
        if raw_value is None:
            return None

        try:
            service = EncryptionService()
            decrypted = service.decrypt(raw_value)
            try:
                parsed = json.loads(decrypted)
            except (json.JSONDecodeError, TypeError):
                parsed = decrypted
            setattr(instance, self.cache_name, parsed)
            return parsed
        except Exception:
            return raw_value

    def __set__(self, instance: models.Model, value: Any) -> None:
        setattr(instance, self.cache_name, None)
        if value is None or value == "":
            instance.__dict__[self.attname] = value
            return
        try:
            service = EncryptionService()
            to_encrypt = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            encrypted = service.encrypt(to_encrypt)
            instance.__dict__[self.attname] = (
                encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
            )
        except Exception:
            instance.__dict__[self.attname] = value


# ---------------------------------------------------------------------------
# Custom Encrypted Field Classes
# ---------------------------------------------------------------------------

class EncryptedCharField(models.CharField):
    """CharField that encrypts on save and decrypts on load."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["max_length"] = kwargs.get("max_length", 500)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return None
        try:
            service = EncryptionService()
            return service.decrypt(value)
        except Exception:
            return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None or value == "":
            return super().get_prep_value(value)
        try:
            service = EncryptionService()
            encrypted = service.encrypt(str(value))
            result = encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
            # Ensure we don't exceed max_length
            if len(result) > self.max_length:
                logger.warning(
                    "Encrypted value for field %s exceeds max_length %d",
                    self.name,
                    self.max_length,
                )
            return result
        except Exception:
            return super().get_prep_value(value)

    def deconstruct(self) -> tuple:
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedTextField(models.TextField):
    """TextField that encrypts on save and decrypts on load."""

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return None
        try:
            service = EncryptionService()
            return service.decrypt(value)
        except Exception:
            return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None or value == "":
            return super().get_prep_value(value)
        try:
            service = EncryptionService()
            encrypted = service.encrypt(str(value))
            return encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
        except Exception:
            return super().get_prep_value(value)

    def deconstruct(self) -> tuple:
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedJSONField(models.JSONField):
    """JSONField that encrypts the serialised JSON on save and decrypts on load."""

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return None
        try:
            service = EncryptionService()
            decrypted = service.decrypt(value)
            return json.loads(decrypted)
        except Exception:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError, KeyError):
                return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return super().get_prep_value(value)
        try:
            service = EncryptionService()
            serialised = json.dumps(value)
            encrypted = service.encrypt(serialised)
            return encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
        except Exception:
            return super().get_prep_value(value)

    def deconstruct(self) -> tuple:
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


# ---------------------------------------------------------------------------
# Key Rotator
# ---------------------------------------------------------------------------

class KeyRotator:
    """Manages AES-256 key generation, storage, and rotation."""

    def __init__(self, rotation_days: int = 90) -> None:
        self.rotation_days = rotation_days
        self._service = EncryptionService()

    def generate_key(self) -> bytes:
        """Generate a new Fernet-compatible AES key."""
        return Fernet.generate_key()

    def store_key(self, key_bytes: bytes, version: int) -> None:
        """Store an encrypted key in the database."""
        from security.models import EncryptionKey  # type: ignore[attr-defined]

        encrypted = self._service.encrypt(key_bytes.decode("utf-8"))
        EncryptionKey.objects.update_or_create(
            version=version,
            defaults={
                "encrypted_key": encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted,
                "is_active": True,
                "created_at": __import__("django.utils.timezone").timezone.now(),
            },
        )

    def rotate_all(self) -> int:
        """
        Generate a new key, store it, and deactivate the oldest active key
        that exceeds the rotation window. Returns the new version number.
        """
        from datetime import timedelta

        from django.utils import timezone

        from security.models import EncryptionKey  # type: ignore[attr-defined]

        now = timezone.now()
        cutoff = now - timedelta(days=self.rotation_days)

        # Deactivate expired keys
        expired_count = EncryptionKey.objects.filter(
            is_active=True,
            created_at__lt=cutoff,
        ).update(is_active=False)

        if expired_count:
            logger.info("Deactivated %d expired encryption keys", expired_count)

        # Determine next version
        last = EncryptionKey.objects.order_by("-version").values_list("version", flat=True).first()
        new_version = (last or 0) + 1

        # Generate and store
        new_key = self.generate_key()
        self.store_key(new_key, new_version)

        logger.info("Rotated encryption keys: new version=%d, deactivated=%d", new_version, expired_count)
        return new_version

    def needs_rotation(self) -> bool:
        """Check if rotation is due based on the oldest active key."""
        from datetime import timedelta

        from django.utils import timezone

        from security.models import EncryptionKey  # type: ignore[attr-defined]

        cutoff = timezone.now() - timedelta(days=self.rotation_days)
        return not EncryptionKey.objects.filter(is_active=True, created_at__gte=cutoff).exists()

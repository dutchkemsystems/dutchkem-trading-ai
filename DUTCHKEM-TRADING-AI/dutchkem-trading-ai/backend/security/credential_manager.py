"""
V5 Centralized Credential & Secrets Management.

Stores, rotates, and injects secrets for MT5, API keys, and application-wide
credentials.  All values are encrypted at rest via the encryption module.
"""
import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .encryption import get_encryption
from .models import CredentialVault, ThreatLevel

logger = logging.getLogger('security.credentials')


# ---------------------------------------------------------------------------
# Credential Manager (core vault)
# ---------------------------------------------------------------------------

class CredentialManager:
    """Manages encrypted credential storage with versioning and rotation."""

    _instance: Optional['CredentialManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True
        self._encryption = get_encryption()
        logger.info('Credential manager initialised')

    def store_credential(
        self,
        name: str,
        value: str,
        credential_type: str = 'secret',
        description: str = '',
        expires_at: Optional[timezone.datetime] = None,
    ) -> CredentialVault:
        """Encrypt and store a credential."""
        encrypted = self._encryption.encrypt(value).encode()
        value_hash = self._encryption.hash_value(value)

        vault, created = CredentialVault.objects.update_or_create(
            name=name,
            defaults={
                'credential_type': credential_type,
                'encrypted_value': encrypted,
                'value_hash': value_hash,
                'description': description,
                'is_active': True,
                'rotated_at': timezone.now(),
                'expires_at': expires_at,
            },
        )
        logger.info('Credential stored: %s (created=%s)', name, created)
        return vault

    def get_credential(self, name: str) -> Optional[str]:
        """Retrieve and decrypt a credential by name."""
        try:
            vault = CredentialVault.objects.get(name=name, is_active=True)
        except CredentialVault.DoesNotExist:
            logger.warning('Credential not found: %s', name)
            return None

        if vault.expires_at and timezone.now() > vault.expires_at:
            logger.warning('Credential expired: %s', name)
            return None

        vault.last_accessed = timezone.now()
        vault.access_count += 1
        vault.save(update_fields=['last_accessed', 'access_count'])

        return self._encryption.decrypt(vault.encrypted_value.decode())

    def rotate_credential(self, name: str, new_value: str) -> Optional[CredentialVault]:
        """Rotate a credential to a new value (soft-deactivates old entry)."""
        try:
            old = CredentialVault.objects.get(name=name, is_active=True)
            old.is_active = False
            old.save(update_fields=['is_active'])
        except CredentialVault.DoesNotExist:
            pass

        return self.store_credential(name, new_value, description=f'Rotated from {name}')

    def delete_credential(self, name: str) -> bool:
        """Soft-delete a credential."""
        try:
            vault = CredentialVault.objects.get(name=name, is_active=True)
            vault.is_active = False
            vault.save(update_fields=['is_active'])
            logger.info('Credential soft-deleted: %s', name)
            return True
        except CredentialVault.DoesNotExist:
            return False

    def list_credentials(self) -> List[Dict[str, Any]]:
        """List all active credentials (values excluded)."""
        return [
            {
                'name': v.name,
                'credential_type': v.credential_type,
                'description': v.description,
                'created_at': v.created_at.isoformat() if v.created_at else None,
                'rotated_at': v.rotated_at.isoformat() if v.rotated_at else None,
                'expires_at': v.expires_at.isoformat() if v.expires_at else None,
                'last_accessed': v.last_accessed.isoformat() if v.last_accessed else None,
                'access_count': v.access_count,
            }
            for v in CredentialVault.objects.filter(is_active=True)
        ]

    def check_expiry(self) -> List[Dict[str, Any]]:
        """Return credentials that have expired or will expire within 7 days."""
        now = timezone.now()
        soon = now + timedelta(days=7)

        expired = CredentialVault.objects.filter(
            is_active=True,
            expires_at__lte=soon,
        )

        return [
            {
                'name': v.name,
                'credential_type': v.credential_type,
                'expires_at': v.expires_at.isoformat() if v.expires_at else None,
                'is_expired': v.expires_at < now if v.expires_at else False,
            }
            for v in expired
        ]

    def auto_rotate(self, name: str, rotate_days: int) -> bool:
        """Set up auto-rotation by updating expiry to trigger rotation."""
        try:
            vault = CredentialVault.objects.get(name=name, is_active=True)
            vault.expires_at = timezone.now() + timedelta(days=rotate_days)
            vault.save(update_fields=['expires_at'])
            logger.info('Auto-rotation scheduled for %s: %d days', name, rotate_days)
            return True
        except CredentialVault.DoesNotExist:
            return False


# ---------------------------------------------------------------------------
# MT5 Credential Store
# ---------------------------------------------------------------------------

class MT5CredentialStore:
    """Specialised store for MetaTrader 5 login credentials."""

    PREFIX = 'mt5_'

    def __init__(self):
        self._cm = CredentialManager()

    def store_mt5_credentials(
        self,
        account: str,
        server: str,
        password: str,
    ) -> None:
        """Store MT5 login credentials (all values encrypted)."""
        self._cm.store_credential(
            name=f'{self.PREFIX}account_{account}_server',
            value=server,
            credential_type='mt5_server',
            description=f'MT5 server for account {account}',
        )
        self._cm.store_credential(
            name=f'{self.PREFIX}account_{account}_password',
            value=password,
            credential_type='mt5_password',
            description=f'MT5 password for account {account}',
        )
        logger.info('MT5 credentials stored for account %s', account)

    def get_mt5_credentials(self, account: str) -> Optional[Dict[str, str]]:
        """Retrieve MT5 credentials for an account."""
        server = self._cm.get_credential(f'{self.PREFIX}account_{account}_server')
        password = self._cm.get_credential(f'{self.PREFIX}account_{account}_password')

        if server is None or password is None:
            return None

        return {
            'account': account,
            'server': server,
            'password': password,
        }

    def rotate_mt5_password(self, account: str, new_password: str) -> bool:
        """Rotate the MT5 password for an account."""
        result = self._cm.rotate_credential(
            f'{self.PREFIX}account_{account}_password',
            new_password,
        )
        return result is not None


# ---------------------------------------------------------------------------
# API Credential Manager
# ---------------------------------------------------------------------------

class APICredentialManager:
    """Manages third-party API key/secret pairs."""

    PREFIX = 'api_'

    def __init__(self):
        self._cm = CredentialManager()

    def store_api_key(self, service: str, key: str, secret: str) -> None:
        """Store an API key/secret pair for a service."""
        self._cm.store_credential(
            name=f'{self.PREFIX}{service}_key',
            value=key,
            credential_type='api_key',
            description=f'API key for {service}',
        )
        self._cm.store_credential(
            name=f'{self.PREFIX}{service}_secret',
            value=secret,
            credential_type='api_secret',
            description=f'API secret for {service}',
        )
        logger.info('API credentials stored for %s', service)

    def get_api_key(self, service: str) -> Optional[Dict[str, str]]:
        """Retrieve API key/secret for a service."""
        key = self._cm.get_credential(f'{self.PREFIX}{service}_key')
        secret = self._cm.get_credential(f'{self.PREFIX}{service}_secret')

        if key is None or secret is None:
            return None

        return {'key': key, 'secret': secret}

    def rotate_api_key(self, service: str, new_key: str, new_secret: str) -> bool:
        """Rotate API key and secret for a service."""
        r1 = self._cm.rotate_credential(f'{self.PREFIX}{service}_key', new_key)
        r2 = self._cm.rotate_credential(f'{self.PREFIX}{service}_secret', new_secret)
        return r1 is not None and r2 is not None

    def validate_api_key(self, service: str) -> bool:
        """Check if the stored API key exists and is not expired."""
        creds = self.get_api_key(service)
        if creds is None:
            return False

        # Additional validation can be added per service here
        return True


# ---------------------------------------------------------------------------
# Secret Injector
# ---------------------------------------------------------------------------

class SecretInjector:
    """Loads secrets from the vault into environment variables."""

    def __init__(self):
        self._cm = CredentialManager()

    def inject_secrets(self) -> int:
        """Load all active credentials into os.environ. Returns count injected."""
        count = 0
        for cred in CredentialVault.objects.filter(is_active=True):
            env_key = cred.name.upper().replace('.', '_').replace('-', '_')
            value = self._cm.get_credential(cred.name)
            if value:
                os.environ[env_key] = value
                count += 1
        logger.info('Injected %d secrets into environment', count)
        return count

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret from the vault, falling back to environment."""
        value = self._cm.get_credential(name)
        if value is not None:
            return value

        env_key = name.upper().replace('.', '_').replace('-', '_')
        return os.environ.get(env_key, default)

    @staticmethod
    def mask_secret(value: str, visible_chars: int = 4) -> str:
        """Return a masked version of a secret for safe logging."""
        if len(value) <= visible_chars:
            return '*' * len(value)
        return '*' * (len(value) - visible_chars) + value[-visible_chars:]


# ---------------------------------------------------------------------------
# Encryption Integration
# ---------------------------------------------------------------------------

class EncryptionIntegration:
    """Thin wrapper bridging CredentialManager with the encryption engine."""

    def __init__(self):
        self._engine = get_encryption()

    def encrypt_value(self, plaintext: str) -> str:
        return self._engine.encrypt(plaintext)

    def decrypt_value(self, ciphertext: str) -> str:
        return self._engine.decrypt(ciphertext)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_cm_instance: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    global _cm_instance
    if _cm_instance is None:
        _cm_instance = CredentialManager()
    return _cm_instance

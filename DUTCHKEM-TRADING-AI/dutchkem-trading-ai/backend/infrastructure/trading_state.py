"""
V4 Trading State Persistence — Save and recover trading state across restarts.
"""
import json
import logging
import os
import hashlib
import hmac
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('infrastructure.trading_state')

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import django
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False


class TradingStatePersistence:
    """
    Persist trading state for immediate recovery.
    - Saves to Redis (fast), PostgreSQL (persistent), local file (fallback)
    - Signs state for integrity verification
    - Recovers from most recent consistent snapshot
    """

    def __init__(self, redis_url: str = 'redis://localhost:6379/0',
                 state_dir: str = 'state_snapshots',
                 integrity_key: str = 'dutchkem-state-integrity-key'):
        self.redis_url = redis_url
        self.state_dir = state_dir
        self.integrity_key = integrity_key
        self._redis_client = None
        self._lock = threading.Lock()

        os.makedirs(self.state_dir, exist_ok=True)

    @property
    def redis_client(self):
        if self._redis_client is None and REDIS_AVAILABLE:
            try:
                self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
                self._redis_client.ping()
            except Exception as e:
                logger.warning("Redis unavailable for state persistence: %s", e)
                self._redis_client = None
        return self._redis_client

    def _sign_state(self, state: Dict) -> str:
        """Create HMAC signature for state integrity."""
        state_json = json.dumps(state, sort_keys=True, default=str)
        return hmac.new(
            self.integrity_key.encode(),
            state_json.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_state(self, state: Dict, signature: str) -> bool:
        """Verify state integrity using HMAC signature."""
        expected = self._sign_state(state)
        return hmac.compare_digest(expected, signature)

    def save_state(self, state_type: str, state: Dict) -> bool:
        """Save trading state to all available storage backends."""
        state_data = {
            'type': state_type,
            'data': state,
            'timestamp': time.time(),
            'iso_timestamp': datetime.utcnow().isoformat(),
        }
        state_data['signature'] = self._sign_state(state_data)

        saved_any = False

        if self._save_to_redis(state_type, state_data):
            saved_any = True

        if self._save_to_file(state_type, state_data):
            saved_any = True

        if DJANGO_AVAILABLE and self._save_to_db(state_type, state_data):
            saved_any = True

        if saved_any:
            logger.info("State saved: %s", state_type)
        else:
            logger.error("Failed to save state to any backend: %s", state_type)

        return saved_any

    def _save_to_redis(self, state_type: str, state_data: Dict) -> bool:
        """Save state to Redis for fast recovery."""
        client = self.redis_client
        if client is None:
            return False

        try:
            key = f"dutchkem:state:{state_type}"
            client.set(key, json.dumps(state_data, default=str), ex=86400)

            history_key = f"dutchkem:state:{state_type}:history"
            client.lpush(history_key, json.dumps(state_data, default=str))
            client.ltrim(history_key, 0, 99)

            return True
        except Exception as e:
            logger.error("Redis state save failed for %s: %s", state_type, e)
            return False

    def _save_to_file(self, state_type: str, state_data: Dict) -> bool:
        """Save state to local file as fallback."""
        try:
            filename = f"{state_type}_{int(time.time())}.json"
            filepath = os.path.join(self.state_dir, filename)

            with open(filepath, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)

            latest_link = os.path.join(self.state_dir, f"{state_type}_latest.json")
            with open(latest_link, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)

            self._cleanup_old_snapshots(state_type)
            return True
        except Exception as e:
            logger.error("File state save failed for %s: %s", state_type, e)
            return False

    def _save_to_db(self, state_type: str, state_data: Dict) -> bool:
        """Save state to PostgreSQL for persistent storage."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO infrastructure_tradingstatesnapshot 
                    (state_type, state_data, signature, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, [state_type, json.dumps(state_data, default=str),
                      state_data['signature']])
            return True
        except Exception as e:
            logger.debug("DB state save skipped (table may not exist): %s", e)
            return False

    def _cleanup_old_snapshots(self, state_type: str, max_keep: int = 50):
        """Remove old state snapshots to prevent disk fill."""
        try:
            files = sorted(
                [
                    f for f in os.listdir(self.state_dir)
                    if f.startswith(f"{state_type}_") and f != f"{state_type}_latest.json"
                ],
                reverse=True
            )
            for old_file in files[max_keep:]:
                os.remove(os.path.join(self.state_dir, old_file))
        except Exception as e:
            logger.debug("Snapshot cleanup error: %s", e)

    def load_state(self, state_type: str) -> Optional[Dict]:
        """Load the most recent valid state, trying Redis first, then file."""
        state = self._load_from_redis(state_type)
        if state and self._verify_state(state, state.get('signature', '')):
            return state

        state = self._load_from_file(state_type)
        if state and self._verify_state(state, state.get('signature', '')):
            return state

        logger.warning("No valid state found for %s", state_type)
        return None

    def _load_from_redis(self, state_type: str) -> Optional[Dict]:
        """Load state from Redis."""
        client = self.redis_client
        if client is None:
            return None

        try:
            key = f"dutchkem:state:{state_type}"
            data = client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error("Redis state load failed for %s: %s", state_type, e)
        return None

    def _load_from_file(self, state_type: str) -> Optional[Dict]:
        """Load state from local file."""
        try:
            filepath = os.path.join(self.state_dir, f"{state_type}_latest.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error("File state load failed for %s: %s", state_type, e)
        return None

    def save_positions(self, positions: List[Dict]) -> bool:
        """Save open positions state."""
        return self.save_state('positions', {'positions': positions, 'count': len(positions)})

    def load_positions(self) -> List[Dict]:
        """Load open positions state."""
        state = self.load_state('positions')
        return state['data']['positions'] if state else []

    def save_account(self, account: Dict) -> bool:
        """Save account state (balance, equity, margin)."""
        return self.save_state('account', account)

    def load_account(self) -> Optional[Dict]:
        """Load account state."""
        state = self.load_state('account')
        return state['data'] if state else None

    def save_orders(self, orders: List[Dict]) -> bool:
        """Save pending orders state."""
        return self.save_state('orders', {'orders': orders, 'count': len(orders)})

    def load_orders(self) -> List[Dict]:
        """Load pending orders state."""
        state = self.load_state('orders')
        return state['data']['orders'] if state else []

    def save_trading_config(self, config: Dict) -> bool:
        """Save trading configuration state."""
        return self.save_state('trading_config', config)

    def load_trading_config(self) -> Optional[Dict]:
        """Load trading configuration state."""
        state = self.load_state('trading_config')
        return state['data'] if state else None

    def get_state_history(self, state_type: str, limit: int = 10) -> List[Dict]:
        """Get recent state history from Redis."""
        client = self.redis_client
        if client is None:
            return []

        try:
            history_key = f"dutchkem:state:{state_type}:history"
            data = client.lrange(history_key, 0, limit - 1)
            return [json.loads(item) for item in data]
        except Exception as e:
            logger.error("State history load failed for %s: %s", state_type, e)
            return []

    def get_persistence_status(self) -> Dict[str, Any]:
        """Get the current persistence status."""
        redis_ok = False
        if self.redis_client:
            try:
                self.redis_client.ping()
                redis_ok = True
            except Exception:
                pass

        file_count = 0
        try:
            file_count = len([
                f for f in os.listdir(self.state_dir)
                if f.endswith('.json') and '_latest' not in f
            ])
        except Exception:
            pass

        return {
            'redis_available': redis_ok,
            'file_storage_available': os.path.isdir(self.state_dir),
            'snapshot_count': file_count,
            'state_dir': self.state_dir,
        }


_persistence: Optional[TradingStatePersistence] = None


def get_state_persistence() -> TradingStatePersistence:
    global _persistence
    if _persistence is None:
        _persistence = TradingStatePersistence()
    return _persistence

"""
V4 State Synchronization — Redis-backed distributed state sync with buffer queue and consistency.
"""
import json
import logging
import time
import hashlib
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque

logger = logging.getLogger('infrastructure.state_sync')

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class StateBuffer:
    """Thread-safe state buffer queue for pending sync operations."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def enqueue(self, key: str, state: Dict) -> bool:
        with self._lock:
            if len(self._buffer) >= self.max_size:
                self._buffer.popleft()
            self._buffer.append({
                'key': key,
                'state': state,
                'timestamp': time.time(),
            })
            return True

    def dequeue(self) -> Optional[Dict]:
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
            return None

    def peek_all(self) -> List[Dict]:
        with self._lock:
            return list(self._buffer)

    def clear(self):
        with self._lock:
            self._buffer.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)


class StateSynchronizer:
    """
    Real-time state synchronization across all nodes.
    - Maintains state buffer queue
    - Replicates state to all nodes
    - Verifies consistency across nodes
    - Resyncs nodes that fall behind
    """

    def __init__(self, redis_url: str = 'redis://localhost:6379/0',
                 buffer_max_size: int = 1000):
        self.redis_url = redis_url
        self._client = None
        self.sync_prefix = 'dutchkem:sync:'
        self.lock_prefix = 'dutchkem:lock:'
        self.history_prefix = 'dutchkem:history:'
        self.node_prefix = 'dutchkem:node:'
        self.buffer = StateBuffer(max_size=buffer_max_size)
        self._node_id = f"node-{int(time.time())}"
        self._consistency_log: deque = deque(maxlen=500)
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                self._client.ping()
            except Exception as e:
                logger.warning("Redis unavailable for state sync: %s", e)
                self._client = None
        return self._client

    def sync_state(self, key: str, state: Dict) -> bool:
        """Sync state with consistency hash and history."""
        client = self.client
        if client is None:
            self.buffer.enqueue(key, state)
            logger.debug("Redis unavailable, buffered sync for %s", key)
            return False

        try:
            state['_sync_timestamp'] = time.time()
            state['_sync_node'] = self._node_id
            state['_sync_hash'] = hashlib.md5(
                json.dumps(state, sort_keys=True, default=str).encode()
            ).hexdigest()

            client.set(
                f"{self.sync_prefix}{key}",
                json.dumps(state, default=str),
                ex=3600,
            )

            history_key = f"{self.history_prefix}{key}"
            client.lpush(history_key, json.dumps(state, default=str))
            client.ltrim(history_key, 0, 99)

            client.set(
                f"{self.node_prefix}{self._node_id}:last_sync",
                time.time(),
                ex=3600,
            )

            return True
        except Exception as e:
            logger.error("State sync failed for %s: %s", key, e)
            self.buffer.enqueue(key, state)
            return False

    def get_state(self, key: str) -> Optional[Dict]:
        """Get the latest synced state."""
        client = self.client
        if client is None:
            return None

        try:
            data = client.get(f"{self.sync_prefix}{key}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error("State get failed for %s: %s", key, e)
        return None

    def verify_consistency(self, key: str) -> Dict[str, Any]:
        """Verify state consistency by checking hash."""
        state = self.get_state(key)
        if not state:
            return {'consistent': False, 'reason': 'No state found'}

        stored_hash = state.pop('_sync_hash', None)
        current_hash = hashlib.md5(
            json.dumps(state, sort_keys=True, default=str).encode()
        ).hexdigest()

        consistent = stored_hash == current_hash if stored_hash else True

        result = {
            'key': key,
            'consistent': consistent,
            'stored_hash': stored_hash,
            'current_hash': current_hash,
            'verified_at': time.time(),
        }

        self._consistency_log.append(result)
        return result

    def get_state_history(self, key: str, limit: int = 10) -> List[Dict]:
        """Get sync history for a key."""
        client = self.client
        if client is None:
            return []

        try:
            history_key = f"{self.history_prefix}{key}"
            data = client.lrange(history_key, 0, limit - 1)
            return [json.loads(item) for item in data]
        except Exception as e:
            logger.error("State history failed for %s: %s", key, e)
            return []

    def resync_node(self, target_node_id: str) -> Dict[str, Any]:
        """Resync state to a specific node."""
        client = self.client
        if client is None:
            return {'success': False, 'reason': 'Redis not available'}

        try:
            synced_keys = []
            cursor = 0
            while True:
                cursor, keys = client.scan(
                    cursor, match=f"{self.sync_prefix}*", count=100
                )
                for key in keys:
                    data = client.get(key)
                    if data:
                        clean_key = key.replace(self.sync_prefix, '')
                        client.set(
                            f"{self.node_prefix}{target_node_id}:{clean_key}",
                            data,
                            ex=3600,
                        )
                        synced_keys.append(clean_key)

                if cursor == 0:
                    break

            client.set(
                f"{self.node_prefix}{target_node_id}:last_resync",
                time.time(),
                ex=3600,
            )

            return {
                'success': True,
                'target_node': target_node_id,
                'synced_keys': len(synced_keys),
                'keys': synced_keys,
            }
        except Exception as e:
            logger.error("Node resync failed for %s: %s", target_node_id, e)
            return {'success': False, 'error': str(e)}

    def process_buffered_syncs(self) -> int:
        """Process any buffered sync operations."""
        processed = 0
        while True:
            item = self.buffer.dequeue()
            if item is None:
                break
            if self.sync_state(item['key'], item['state']):
                processed += 1
        return processed

    def sync_positions(self, positions: List[Dict]) -> bool:
        return self.sync_state('positions', {'positions': positions, 'count': len(positions)})

    def get_positions(self) -> List[Dict]:
        state = self.get_state('positions')
        return state.get('positions', []) if state else []

    def sync_account(self, account: Dict) -> bool:
        return self.sync_state('account', account)

    def get_account(self) -> Optional[Dict]:
        return self.get_state('account')

    def acquire_lock(self, resource: str, timeout: float = 5.0) -> bool:
        client = self.client
        if client is None:
            return True

        try:
            return bool(client.set(
                f"{self.lock_prefix}{resource}",
                self._node_id,
                nx=True,
                ex=int(timeout),
            ))
        except Exception:
            return False

    def release_lock(self, resource: str) -> bool:
        client = self.client
        if client is None:
            return True

        try:
            client.delete(f"{self.lock_prefix}{resource}")
            return True
        except Exception:
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive sync status."""
        client = self.client
        if client is None:
            return {
                'available': False,
                'reason': 'Redis not connected',
                'buffered_items': self.buffer.size(),
            }

        try:
            keys = client.keys(f"{self.sync_prefix}*")
            node_keys = client.keys(f"{self.node_prefix}*")

            return {
                'available': True,
                'synced_keys': len(keys),
                'keys': [k.replace(self.sync_prefix, '') for k in keys[:20]],
                'node_id': self._node_id,
                'registered_nodes': len(set(
                    k.split(':')[2] for k in node_keys
                    if len(k.split(':')) >= 3
                )),
                'buffered_items': self.buffer.size(),
                'consistency_checks': len(self._consistency_log),
            }
        except Exception:
            return {'available': False, 'reason': 'Redis error'}


_synchronizer: Optional[StateSynchronizer] = None


def get_synchronizer() -> StateSynchronizer:
    global _synchronizer
    if _synchronizer is None:
        _synchronizer = StateSynchronizer()
    return _synchronizer

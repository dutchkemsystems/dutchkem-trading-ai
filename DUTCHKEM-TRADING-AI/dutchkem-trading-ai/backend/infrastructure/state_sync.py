"""
V4 State Synchronization — Redis-backed distributed state sync.
"""
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger('infrastructure.state_sync')

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class StateSynchronizer:
    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis_url = redis_url
        self._client = None
        self.sync_prefix = 'dutchkem:sync:'
        self.lock_prefix = 'dutchkem:lock:'
    
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
        client = self.client
        if client is None:
            logger.debug("Redis unavailable, skipping sync for %s", key)
            return False
        
        try:
            state['_sync_timestamp'] = time.time()
            state['_sync_hash'] = hashlib.md5(
                json.dumps(state, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            client.set(
                f"{self.sync_prefix}{key}",
                json.dumps(state, default=str),
                ex=3600,
            )
            return True
        except Exception as e:
            logger.error("State sync failed for %s: %s", key, e)
            return False
    
    def get_state(self, key: str) -> Optional[Dict]:
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
                self.node_id if hasattr(self, 'node_id') else 'unknown',
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
        client = self.client
        if client is None:
            return {'available': False, 'reason': 'Redis not connected'}
        
        try:
            keys = client.keys(f"{self.sync_prefix}*")
            return {
                'available': True,
                'synced_keys': len(keys),
                'keys': [k.replace(self.sync_prefix, '') for k in keys[:20]],
            }
        except Exception:
            return {'available': False, 'reason': 'Redis error'}


_synchronizer: Optional[StateSynchronizer] = None

def get_synchronizer() -> StateSynchronizer:
    global _synchronizer
    if _synchronizer is None:
        _synchronizer = StateSynchronizer()
    return _synchronizer

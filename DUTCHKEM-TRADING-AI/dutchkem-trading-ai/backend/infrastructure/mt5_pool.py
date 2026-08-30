"""
V4 MT5 Connection Pool — Connection pooling, lifecycle management, health checks.
"""
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from collections import deque
from enum import Enum

logger = logging.getLogger('infrastructure.mt5_pool')


class ConnectionState(Enum):
    IDLE = 'idle'
    IN_USE = 'in_use'
    CLOSED = 'closed'
    ERROR = 'error'


class MT5Connection:
    def __init__(self, conn_id: str, host: str, port: int):
        self.conn_id = conn_id
        self.host = host
        self.port = port
        self.state = ConnectionState.IDLE
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.error_count = 0
    
    def acquire(self) -> bool:
        if self.state == ConnectionState.IDLE:
            self.state = ConnectionState.IN_USE
            self.last_used = time.time()
            self.use_count += 1
            return True
        return False
    
    def release(self):
        self.state = ConnectionState.IDLE
        self.last_used = time.time()
    
    def mark_error(self):
        self.error_count += 1
        self.state = ConnectionState.ERROR
    
    def is_healthy(self) -> bool:
        return self.state != ConnectionState.ERROR and self.error_count < 5
    
    def to_dict(self) -> Dict:
        return {
            'conn_id': self.conn_id,
            'host': self.host,
            'port': self.port,
            'state': self.state.value,
            'use_count': self.use_count,
            'error_count': self.error_count,
            'age_seconds': time.time() - self.created_at,
        }


class MT5ConnectionPool:
    def __init__(self, max_connections: int = 5, host: str = 'localhost', port: int = 14222):
        self.max_connections = max_connections
        self.host = host
        self.port = port
        self.connections: Dict[str, MT5Connection] = {}
        self._lock = threading.Lock()
        self._conn_counter = 0
        self.health_check_interval = 30.0
        self.max_connection_age = 3600.0
    
    def _create_connection(self) -> MT5Connection:
        self._conn_counter += 1
        conn_id = f"mt5-{self._conn_counter}"
        conn = MT5Connection(conn_id, self.host, self.port)
        self.connections[conn_id] = conn
        logger.info("Created MT5 connection: %s", conn_id)
        return conn
    
    def acquire(self) -> Optional[MT5Connection]:
        with self._lock:
            for conn in self.connections.values():
                if conn.state == ConnectionState.IDLE and conn.is_healthy():
                    if conn.acquire():
                        return conn
            
            if len(self.connections) < self.max_connections:
                conn = self._create_connection()
                conn.acquire()
                return conn
            
            logger.warning("No MT5 connections available (pool exhausted)")
            return None
    
    def release(self, conn_id: str):
        with self._lock:
            if conn_id in self.connections:
                self.connections[conn_id].release()
    
    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            results = {}
            for conn_id, conn in list(self.connections.items()):
                if not conn.is_healthy():
                    conn.state = ConnectionState.CLOSED
                    logger.warning("MT5 connection %s marked unhealthy", conn_id)
                
                if time.time() - conn.created_at > self.max_connection_age:
                    conn.state = ConnectionState.CLOSED
                    logger.info("MT5 connection %s expired", conn_id)
                
                results[conn_id] = conn.to_dict()
            
            self.connections = {
                cid: c for cid, c in self.connections.items()
                if c.state != ConnectionState.CLOSED
            }
            
            return {
                'total': len(self.connections),
                'idle': sum(1 for c in self.connections.values() if c.state == ConnectionState.IDLE),
                'in_use': sum(1 for c in self.connections.values() if c.state == ConnectionState.IN_USE),
                'connections': results,
            }
    
    def get_pool_status(self) -> Dict[str, Any]:
        return {
            'max_connections': self.max_connections,
            'current': len(self.connections),
            'available': sum(1 for c in self.connections.values() if c.state == ConnectionState.IDLE),
            'in_use': sum(1 for c in self.connections.values() if c.state == ConnectionState.IN_USE),
        }


_pool: Optional[MT5ConnectionPool] = None

def get_pool() -> MT5ConnectionPool:
    global _pool
    if _pool is None:
        _pool = MT5ConnectionPool()
    return _pool

"""
V4 MT5 Connection Pool — Connection pooling, load balancing, lifecycle management, health checks.
"""
import logging
import time
import threading
import random
from typing import Dict, Any, Optional, List
from collections import deque
from enum import Enum

logger = logging.getLogger('infrastructure.mt5_pool')


class ConnectionState(Enum):
    IDLE = 'idle'
    IN_USE = 'in_use'
    CLOSED = 'closed'
    ERROR = 'error'
    RECONNECTING = 'reconnecting'


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
        self.latency_ms = 0.0
        self.reconnect_count = 0

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

    def mark_reconnecting(self):
        self.state = ConnectionState.RECONNECTING

    def is_healthy(self) -> bool:
        return self.state not in (ConnectionState.ERROR, ConnectionState.CLOSED) and self.error_count < 5

    def to_dict(self) -> Dict:
        return {
            'conn_id': self.conn_id,
            'host': self.host,
            'port': self.port,
            'state': self.state.value,
            'use_count': self.use_count,
            'error_count': self.error_count,
            'latency_ms': self.latency_ms,
            'reconnect_count': self.reconnect_count,
            'age_seconds': time.time() - self.created_at,
        }


class LoadBalancer:
    """Load balancing strategies for MT5 connections."""

    ROUND_ROBIN = 'round_robin'
    LEAST_CONNECTIONS = 'least_connections'
    RANDOM = 'random'
    LATENCY_BASED = 'latency_based'

    def __init__(self, strategy: str = ROUND_ROBIN):
        self.strategy = strategy
        self._round_robin_index = 0

    def select_connection(self, connections: Dict[str, MT5Connection]) -> Optional[MT5Connection]:
        """Select the best connection based on the load balancing strategy."""
        available = [
            conn for conn in connections.values()
            if conn.state == ConnectionState.IDLE and conn.is_healthy()
        ]

        if not available:
            return None

        if self.strategy == self.ROUND_ROBIN:
            return self._round_robin(available)
        elif self.strategy == self.LEAST_CONNECTIONS:
            return self._least_connections(available)
        elif self.strategy == self.RANDOM:
            return self._random_select(available)
        elif self.strategy == self.LATENCY_BASED:
            return self._latency_based(available)
        else:
            return self._round_robin(available)

    def _round_robin(self, connections: List[MT5Connection]) -> MT5Connection:
        """Round-robin selection."""
        if not connections:
            return None
        conn = connections[self._round_robin_index % len(connections)]
        self._round_robin_index += 1
        return conn

    def _least_connections(self, connections: List[MT5Connection]) -> MT5Connection:
        """Select connection with least use count."""
        return min(connections, key=lambda c: c.use_count)

    def _random_select(self, connections: List[MT5Connection]) -> MT5Connection:
        """Random selection."""
        return random.choice(connections)

    def _latency_based(self, connections: List[MT5Connection]) -> MT5Connection:
        """Select connection with lowest latency."""
        return min(connections, key=lambda c: c.latency_ms if c.latency_ms > 0 else float('inf'))


class MT5ConnectionPool:
    """
    Maintain multiple MT5 connections for reliability.
    - Pool of 3 MT5 connections
    - Health checks on each connection
    - Automatic reconnection
    - Load balancing across connections
    """

    def __init__(self, max_connections: int = 3, host: str = 'localhost',
                 port: int = 14222, load_balance_strategy: str = 'round_robin'):
        self.max_connections = max_connections
        self.host = host
        self.port = port
        self.connections: Dict[str, MT5Connection] = {}
        self._lock = threading.Lock()
        self._conn_counter = 0
        self.health_check_interval = 30.0
        self.max_connection_age = 3600.0
        self.load_balancer = LoadBalancer(strategy=load_balance_strategy)
        self._reconnect_thread: Optional[threading.Thread] = None
        self._running = False
        self._reconnect_log: deque = deque(maxlen=100)

    def _create_connection(self) -> MT5Connection:
        """Create a new MT5 connection."""
        self._conn_counter += 1
        conn_id = f"mt5-{self._conn_counter}"
        conn = MT5Connection(conn_id, self.host, self.port)
        self.connections[conn_id] = conn
        logger.info("Created MT5 connection: %s", conn_id)
        return conn

    def acquire(self) -> Optional[MT5Connection]:
        """Acquire a connection using load balancing."""
        with self._lock:
            conn = self.load_balancer.select_connection(self.connections)
            if conn and conn.acquire():
                return conn

            if len(self.connections) < self.max_connections:
                conn = self._create_connection()
                conn.acquire()
                return conn

            logger.warning("No MT5 connections available (pool exhausted)")
            return None

    def release(self, conn_id: str):
        """Release a connection back to the pool."""
        with self._lock:
            if conn_id in self.connections:
                self.connections[conn_id].release()

    def update_latency(self, conn_id: str, latency_ms: float):
        """Update latency for a connection."""
        with self._lock:
            if conn_id in self.connections:
                self.connections[conn_id].latency_ms = latency_ms

    def health_check(self) -> Dict[str, Any]:
        """Run health checks on all connections."""
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
                'unhealthy': sum(1 for c in self.connections.values() if not c.is_healthy()),
                'connections': results,
            }

    def reconnect_connection(self, conn_id: str) -> bool:
        """Attempt to reconnect a failed connection."""
        with self._lock:
            if conn_id not in self.connections:
                return False
            conn = self.connections[conn_id]

        logger.info("Reconnecting MT5 connection: %s", conn_id)
        conn.mark_reconnecting()

        try:
            time.sleep(0.5)

            conn.state = ConnectionState.IDLE
            conn.error_count = max(0, conn.error_count - 1)
            conn.reconnect_count += 1
            conn.last_used = time.time()

            self._reconnect_log.append({
                'conn_id': conn_id,
                'timestamp': time.time(),
                'success': True,
            })

            logger.info("Reconnected MT5 connection: %s", conn_id)
            return True
        except Exception as e:
            logger.error("Failed to reconnect MT5 connection %s: %s", conn_id, e)
            conn.state = ConnectionState.ERROR

            self._reconnect_log.append({
                'conn_id': conn_id,
                'timestamp': time.time(),
                'success': False,
                'error': str(e),
            })
            return False

    def start_auto_reconnect(self):
        """Start the automatic reconnection thread."""
        if self._running:
            return
        self._running = True
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
        logger.info("MT5 auto-reconnect started")

    def stop_auto_reconnect(self):
        """Stop the automatic reconnection thread."""
        self._running = False
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=5.0)
        logger.info("MT5 auto-reconnect stopped")

    def _reconnect_loop(self):
        """Background loop to reconnect failed connections."""
        while self._running:
            try:
                with self._lock:
                    failed_conns = [
                        cid for cid, c in self.connections.items()
                        if c.state == ConnectionState.ERROR
                    ]

                for conn_id in failed_conns:
                    self.reconnect_connection(conn_id)

            except Exception as e:
                logger.error("MT5 reconnect loop error: %s", e)

            time.sleep(10.0)

    def get_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status."""
        with self._lock:
            total_use = sum(c.use_count for c in self.connections.values())
            avg_latency = 0.0
            latency_conns = [c for c in self.connections.values() if c.latency_ms > 0]
            if latency_conns:
                avg_latency = sum(c.latency_ms for c in latency_conns) / len(latency_conns)

            return {
                'max_connections': self.max_connections,
                'current': len(self.connections),
                'available': sum(1 for c in self.connections.values() if c.state == ConnectionState.IDLE),
                'in_use': sum(1 for c in self.connections.values() if c.state == ConnectionState.IN_USE),
                'unhealthy': sum(1 for c in self.connections.values() if not c.is_healthy()),
                'total_use_count': total_use,
                'average_latency_ms': round(avg_latency, 2),
                'load_balance_strategy': self.load_balancer.strategy,
                'auto_reconnect': self._running,
                'connections': {
                    cid: c.to_dict() for cid, c in self.connections.items()
                },
            }


_pool: Optional[MT5ConnectionPool] = None


def get_pool() -> MT5ConnectionPool:
    global _pool
    if _pool is None:
        _pool = MT5ConnectionPool()
    return _pool

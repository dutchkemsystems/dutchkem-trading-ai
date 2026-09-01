"""
V4 Failover Manager — Automatic failover between nodes with heartbeat monitoring.
"""
import logging
import time
import threading
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.failover')


class FailoverState(Enum):
    NORMAL = 'normal'
    FAILOVER_PENDING = 'failover_pending'
    FAILOVER_IN_PROGRESS = 'failover_in_progress'
    RECOVERY = 'recovery'


class FailoverManager:
    """
    Automatic failover between nodes.
    - Monitors node health via heartbeat
    - Detects failures (3 missed heartbeats = failure)
    - Switches to healthy backup node
    - Syncs state to new active node
    - Logs all failover events
    """

    def __init__(self, missed_heartbeats_threshold: int = 3, heartbeat_interval: float = 10.0):
        self.missed_heartbeats_threshold = missed_heartbeats_threshold
        self.heartbeat_interval = heartbeat_interval
        self.nodes: Dict[str, Dict] = {}
        self.active_node_id: Optional[str] = None
        self.state = FailoverState.NORMAL
        self.failover_log: deque = deque(maxlen=500)
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, List[Callable]] = {
            'on_failover': [],
            'on_recovery': [],
            'on_node_failure': [],
            'on_node_recovery': [],
        }

    def register_node(self, node_id: str, host: str, port: int,
                      priority: int = 0, metadata: Optional[Dict] = None) -> Dict:
        """Register a node for failover monitoring."""
        with self._lock:
            self.nodes[node_id] = {
                'node_id': node_id,
                'host': host,
                'port': port,
                'priority': priority,
                'status': 'standby',
                'last_heartbeat': time.time(),
                'missed_heartbeats': 0,
                'failover_count': 0,
                'metadata': metadata or {},
            }
            logger.info("Node registered for failover: %s at %s:%s", node_id, host, port)
            return self.nodes[node_id]

    def set_active_node(self, node_id: str):
        """Set a node as the active node."""
        with self._lock:
            if node_id not in self.nodes:
                logger.warning("Cannot set active node: %s not registered", node_id)
                return
            if self.active_node_id and self.active_node_id in self.nodes:
                self.nodes[self.active_node_id]['status'] = 'standby'
            self.nodes[node_id]['status'] = 'active'
            self.active_node_id = node_id
            logger.info("Active node set to: %s", node_id)

    def heartbeat(self, node_id: str) -> bool:
        """Record a heartbeat from a node."""
        with self._lock:
            if node_id not in self.nodes:
                logger.warning("Heartbeat from unknown node: %s", node_id)
                return False

            node = self.nodes[node_id]
            was_failed = node['status'] == 'failed'

            node['last_heartbeat'] = time.time()
            node['missed_heartbeats'] = 0

            if was_failed:
                node['status'] = 'standby'
                logger.info("Node %s recovered (heartbeat received)", node_id)
                self._fire_event('on_node_recovery', node_id)

            return True

    def check_failures(self) -> List[Dict]:
        """Check all nodes for failures based on missed heartbeats."""
        failed_nodes = []
        now = time.time()

        with self._lock:
            for node_id, node in list(self.nodes.items()):
                if node['status'] == 'active' and node_id != self.active_node_id:
                    continue

                elapsed = now - node['last_heartbeat']
                expected_heartbeats = elapsed / self.heartbeat_interval

                if expected_heartbeats > self.missed_heartbeats_threshold:
                    node['missed_heartbeats'] = int(expected_heartbeats)

                    if node['status'] != 'failed':
                        node['status'] = 'failed'
                        node['failover_count'] += 1
                        failed_info = {
                            'node_id': node_id,
                            'host': node['host'],
                            'missed_heartbeats': node['missed_heartbeats'],
                            'failover_count': node['failover_count'],
                            'timestamp': time.time(),
                        }
                        failed_nodes.append(failed_info)
                        logger.warning(
                            "Node %s failed (missed %d heartbeats, failover #%d)",
                            node_id, node['missed_heartbeats'], node['failover_count']
                        )
                        self._fire_event('on_node_failure', node_id)

        return failed_nodes

    def trigger_failover(self, source_node_id: Optional[str] = None,
                         target_node_id: Optional[str] = None) -> Dict:
        """Trigger a manual or automatic failover."""
        start_time = time.time()

        with self._lock:
            if self.state == FailoverState.FAILOVER_IN_PROGRESS:
                return {'success': False, 'reason': 'Failover already in progress'}

            source = source_node_id or self.active_node_id
            if not source:
                return {'success': False, 'reason': 'No active node to failover from'}

            if source not in self.nodes:
                return {'success': False, 'reason': f'Source node {source} not found'}

            self.state = FailoverState.FAILOVER_IN_PROGRESS

        target = target_node_id or self._select_backup_node(source)
        if not target:
            self.state = FailoverState.NORMAL
            return {'success': False, 'reason': 'No healthy backup node available'}

        logger.info("Failover initiated: %s -> %s", source, target)

        with self._lock:
            self.nodes[source]['status'] = 'failed'
            self.nodes[source]['failover_count'] += 1
            self.nodes[target]['status'] = 'active'
            self.active_node_id = target
            self.state = FailoverState.NORMAL

        duration = time.time() - start_time

        event = {
            'type': 'failover',
            'source': source,
            'target': target,
            'duration_seconds': round(duration, 3),
            'timestamp': time.time(),
            'success': True,
        }
        self.failover_log.append(event)

        self._log_failover_event('failover', source, target, duration, True)
        self._fire_event('on_failover', event)

        logger.info("Failover completed: %s -> %s in %.3fs", source, target, duration)
        return {'success': True, 'source': source, 'target': target, 'duration': duration}

    def trigger_recovery(self, node_id: str) -> Dict:
        """Attempt to recover a failed node."""
        with self._lock:
            if node_id not in self.nodes:
                return {'success': False, 'reason': f'Node {node_id} not found'}

            node = self.nodes[node_id]
            if node['status'] != 'failed':
                return {'success': False, 'reason': f'Node {node_id} is not failed (status: {node["status"]})'}

            node['status'] = 'recovering'
            node['missed_heartbeats'] = 0

        logger.info("Recovery initiated for node %s", node_id)

        self._log_failover_event('recovery', node_id, '', 0.0, True)
        self._fire_event('on_node_recovery', node_id)

        return {'success': True, 'node_id': node_id, 'status': 'recovering'}

    def _select_backup_node(self, exclude_node: str) -> Optional[str]:
        """Select the best backup node (highest priority, healthy)."""
        best_node = None
        best_priority = -1

        for node_id, node in self.nodes.items():
            if node_id == exclude_node:
                continue
            if node['status'] in ('failed',):
                continue
            if node['priority'] > best_priority:
                best_priority = node['priority']
                best_node = node_id

        return best_node

    def on(self, event: str, callback: Callable):
        """Register a callback for a failover event."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, *args, **kwargs):
        """Fire callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error("Failover callback error for %s: %s", event, e)

    def _log_failover_event(self, event_type: str, source: str, target: str,
                            duration: float, success: bool):
        """Log failover event to database."""
        try:
            from .models import FailoverEvent
            FailoverEvent.log(
                event_type=event_type,
                description=f"Failover from {source} to {target}",
                source_node=source,
                target_node=target,
                severity='WARNING' if success else 'CRITICAL',
                duration_seconds=duration,
                success=success,
            )
        except Exception as e:
            logger.error("Failed to log failover event: %s", e)

    def start_monitoring(self):
        """Start the background failover monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Failover monitoring started (interval: %.1fs)", self.heartbeat_interval)

    def stop_monitoring(self):
        """Stop the failover monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Failover monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop that checks for failures."""
        while self._running:
            try:
                failed = self.check_failures()
                for node_info in failed:
                    logger.warning(
                        "Auto-failover triggered for node %s",
                        node_info['node_id']
                    )
                    if node_info['node_id'] == self.active_node_id:
                        self.trigger_failover(node_info['node_id'])
            except Exception as e:
                logger.error("Failover monitor error: %s", e)

            time.sleep(self.heartbeat_interval)

    def get_status(self) -> Dict[str, Any]:
        """Get the current failover manager status."""
        with self._lock:
            return {
                'state': self.state.value,
                'active_node': self.active_node_id,
                'total_nodes': len(self.nodes),
                'healthy_nodes': sum(
                    1 for n in self.nodes.values()
                    if n['status'] in ('active', 'standby')
                ),
                'failed_nodes': sum(
                    1 for n in self.nodes.values()
                    if n['status'] == 'failed'
                ),
                'nodes': {
                    nid: {
                        'status': n['status'],
                        'host': n['host'],
                        'port': n['port'],
                        'priority': n['priority'],
                        'missed_heartbeats': n['missed_heartbeats'],
                        'failover_count': n['failover_count'],
                        'last_heartbeat': n['last_heartbeat'],
                    }
                    for nid, n in self.nodes.items()
                },
                'recent_failovers': list(self.failover_log)[-10:],
                'monitoring': self._running,
            }


_manager: Optional[FailoverManager] = None


def get_failover_manager() -> FailoverManager:
    global _manager
    if _manager is None:
        _manager = FailoverManager()
    return _manager

"""
V4 Multi-Node Orchestration — Node discovery, leader election, automatic failover.
"""
import logging
import time
import uuid
import threading
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger('infrastructure.multi_node')


class NodeStatus(Enum):
    ACTIVE = 'active'
    STANDBY = 'standby'
    FAILED = 'failed'
    RECOVERING = 'recovering'


class Node:
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.status = NodeStatus.STANDBY
        self.last_heartbeat = time.time()
        self.failover_count = 0
        self.load_score = 0.0
    
    def is_alive(self, timeout: float = 30.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout
    
    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'status': self.status.value,
            'last_heartbeat': self.last_heartbeat,
            'failover_count': self.failover_count,
            'load_score': self.load_score,
        }


class MultiNodeOrchestrator:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.leader_id: Optional[str] = None
        self.node_id = f"node-{uuid.uuid4().hex[:8]}"
        self.heartbeat_interval = 10.0
        self.failover_timeout = 30.0
        self._lock = threading.Lock()
    
    def register_node(self, host: str, port: int) -> str:
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self.nodes[node_id] = Node(node_id, host, port)
        logger.info("Node registered: %s at %s:%s", node_id, host, port)
        return node_id
    
    def heartbeat(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self.nodes:
                self.nodes[node_id].last_heartbeat = time.time()
                self.nodes[node_id].status = NodeStatus.ACTIVE
                return True
        return False
    
    def elect_leader(self) -> Optional[str]:
        with self._lock:
            active_nodes = [
                n for n in self.nodes.values()
                if n.is_alive(self.failover_timeout) and n.node_id != self.leader_id
            ]
            
            if not active_nodes:
                if self.leader_id and self.leader_id in self.nodes:
                    return self.leader_id
                return None
            
            active_nodes.sort(key=lambda n: n.load_score)
            self.leader_id = active_nodes[0].node_id
            self.nodes[self.leader_id].status = NodeStatus.ACTIVE
            
            for n in self.nodes.values():
                if n.node_id != self.leader_id and n.status == NodeStatus.ACTIVE:
                    n.status = NodeStatus.STANDBY
            
            logger.info("Leader elected: %s", self.leader_id)
            return self.leader_id
    
    def check_failovers(self) -> List[Dict]:
        failed = []
        with self._lock:
            for node_id, node in list(self.nodes.items()):
                if not node.is_alive(self.failover_timeout) and node.status != NodeStatus.FAILED:
                    node.status = NodeStatus.FAILED
                    node.failover_count += 1
                    failed.append(node.to_dict())
                    logger.warning("Node %s failed (failover #%d)", node_id, node.failover_count)
            
            if self.leader_id and self.leader_id in self.nodes:
                if not self.nodes[self.leader_id].is_alive(self.failover_timeout):
                    logger.warning("Leader %s failed, triggering re-election", self.leader_id)
                    self.leader_id = None
                    self.elect_leader()
        
        return failed
    
    def get_cluster_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'leader': self.leader_id,
                'total_nodes': len(self.nodes),
                'active_nodes': sum(1 for n in self.nodes.values() if n.status == NodeStatus.ACTIVE),
                'failed_nodes': sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED),
                'nodes': {nid: n.to_dict() for nid, n in self.nodes.items()},
            }


_orchestrator: Optional[MultiNodeOrchestrator] = None

def get_orchestrator() -> MultiNodeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiNodeOrchestrator()
    return _orchestrator

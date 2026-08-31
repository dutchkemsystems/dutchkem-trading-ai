"""
V4 Infrastructure API Views — Cluster status, health checks, node management, resiliency.
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger('infrastructure.views')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cluster_status(request):
    """Get cluster/multi-node status."""
    from .multi_node import get_orchestrator

    orch = get_orchestrator()
    return Response(orch.get_cluster_status())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health_checks(request):
    """Run all health checks."""
    from .self_healing import get_self_healing

    sh = get_self_healing()
    results = sh.run_health_checks()
    return Response({
        'healthy': sh.is_system_healthy(),
        'checks': results,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mt5_pool_status(request):
    """Get MT5 connection pool status."""
    from .mt5_pool import get_pool

    pool = get_pool()
    return Response(pool.get_pool_status())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_status(request):
    """Get state synchronization status."""
    from .state_sync import get_synchronizer

    sync = get_synchronizer()
    return Response(sync.get_sync_status())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def force_health_check(request):
    """Force a health check on a specific service."""
    service = request.data.get('service')
    if not service:
        return Response({'error': 'service parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    from .self_healing import get_self_healing
    sh = get_self_healing()
    result = sh.attempt_recovery(service)
    return Response({
        'service': service,
        'recovery_attempted': result,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """Get comprehensive system health status."""
    from .health_monitor import get_health_monitor

    monitor = get_health_monitor()
    report = monitor.generate_report()
    return Response(report)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def node_status(request):
    """Get node status for all registered nodes."""
    from .failover_manager import get_failover_manager

    manager = get_failover_manager()
    status_data = manager.get_status()
    return Response(status_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_failover(request):
    """Trigger a manual failover."""
    source_node = request.data.get('source_node')
    target_node = request.data.get('target_node')

    from .failover_manager import get_failover_manager
    manager = get_failover_manager()

    if source_node:
        result = manager.trigger_failover(source_node, target_node)
    else:
        result = manager.trigger_failover(target_node_id=target_node)

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_alerts(request):
    """Get recent alerts from the alert system."""
    from .models import AlertLog

    limit = int(request.query_params.get('limit', 50))
    alerts = AlertLog.objects.all()[:limit]

    alert_data = []
    for alert in alerts:
        alert_data.append({
            'id': str(alert.id),
            'level': alert.level,
            'channel': alert.channel,
            'subject': alert.subject,
            'message': alert.message,
            'status': alert.status,
            'sent_at': alert.sent_at.isoformat(),
        })

    return Response({
        'alerts': alert_data,
        'total': AlertLog.objects.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overall_status(request):
    """Get overall system status from all resiliency components."""
    from .orchestrator import get_resiliency_orchestrator

    orchestrator = get_resiliency_orchestrator()
    status_data = orchestrator.get_system_status()
    return Response(status_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def failover_status(request):
    """Get failover manager status."""
    from .failover_manager import get_failover_manager

    manager = get_failover_manager()
    return Response(manager.get_status())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def broker_failover_status(request):
    """Get broker failover status."""
    from .broker_failover import get_broker_failover

    broker = get_broker_failover()
    return Response(broker.get_status())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_broker_failover(request):
    """Trigger a broker failover."""
    source_broker = request.data.get('source_broker')
    target_broker = request.data.get('target_broker')

    from .broker_failover import get_broker_failover
    broker = get_broker_failover()

    if source_broker:
        result = broker.trigger_failover(source_broker, target_broker)
    else:
        result = broker.trigger_failover(target_broker_id=target_broker)

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def power_status(request):
    """Get power protection status."""
    from .power_protection import get_power_protection

    protection = get_power_protection()
    return Response(protection.get_status())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def internet_status(request):
    """Get internet failover status."""
    from .internet_failover import get_internet_failover

    failover = get_internet_failover()
    return Response(failover.get_status())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trading_state_status(request):
    """Get trading state persistence status."""
    from .trading_state import get_state_persistence

    persistence = get_state_persistence()
    return Response(persistence.get_persistence_status())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_trading_state(request):
    """Save current trading state."""
    state_type = request.data.get('type', 'manual')
    state_data = request.data.get('state', {})

    from .trading_state import get_state_persistence
    persistence = get_state_persistence()

    success = persistence.save_state(state_type, state_data)
    return Response({
        'success': success,
        'state_type': state_type,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def failover_events(request):
    """Get recent failover events."""
    from .models import FailoverEvent

    limit = int(request.query_params.get('limit', 50))
    event_type = request.query_params.get('type')

    events = FailoverEvent.objects.all()
    if event_type:
        events = events.filter(event_type=event_type)
    events = events[:limit]

    event_data = []
    for event in events:
        event_data.append({
            'id': str(event.id),
            'event_type': event.event_type,
            'source_node': event.source_node,
            'target_node': event.target_node,
            'severity': event.severity,
            'description': event.description,
            'duration_seconds': event.duration_seconds,
            'success': event.success,
            'created_at': event.created_at.isoformat(),
        })

    return Response({
        'events': event_data,
        'total': FailoverEvent.objects.count(),
    })

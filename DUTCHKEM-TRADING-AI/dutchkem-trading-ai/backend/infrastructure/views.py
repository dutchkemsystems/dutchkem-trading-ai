"""
V4 Infrastructure API Views — Cluster status, health checks, node management.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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

"""
V5 Security API Views — Security status, events, credentials, threat intelligence.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def security_status(request):
    """Get overall security system status."""
    from .siem import get_siem
    from .rasp import get_rasp
    from .credential_manager import get_credential_manager
    
    siem = get_siem()
    rasp = get_rasp()
    cm = get_credential_manager()
    
    return Response({
        'security_status': 'active',
        'siem': {
            'active_rules': len(siem.rules) if hasattr(siem, 'rules') else 0,
            'recent_alerts': len(siem.get_recent_alerts() if hasattr(siem, 'get_recent_alerts') else []),
        },
        'rasp': {
            'integrity_ok': rasp.verify_integrity() if hasattr(rasp, 'verify_integrity') else False,
        },
        'credential_manager': {
            'credentials_stored': len(cm.list_credentials() if hasattr(cm, 'list_credentials') else []),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def security_events(request):
    """Get recent security events."""
    from .models import SecurityEvent
    
    limit = int(request.query_params.get('limit', 50))
    threat_level = request.query_params.get('threat_level')
    event_type = request.query_params.get('event_type')
    
    qs = SecurityEvent.objects.all()
    if threat_level:
        qs = qs.filter(threat_level=threat_level)
    if event_type:
        qs = qs.filter(event_type=event_type)
    
    events = qs[:limit]
    return Response({
        'events': [
            {
                'id': e.id,
                'timestamp': e.timestamp.isoformat(),
                'event_type': e.event_type,
                'threat_level': e.threat_level,
                'ip_address': e.ip_address,
                'user_id': e.user_id,
                'details': e.details,
                'action_taken': e.action_taken,
            }
            for e in events
        ],
        'count': qs.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def threat_summary(request):
    """Get threat intelligence summary."""
    from .siem import get_siem
    
    siem = get_siem()
    summary = siem.get_threat_summary() if hasattr(siem, 'get_threat_summary') else {}
    return Response(summary)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rotate_encryption_keys(request):
    """Trigger encryption key rotation."""
    from .encryption import get_key_rotator
    
    rotator = get_key_rotator()
    result = rotator.rotate_all() if hasattr(rotator, 'rotate_all') else False
    return Response({
        'success': result,
        'message': 'Key rotation completed' if result else 'Key rotation failed',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blocked_ips(request):
    """Get list of blocked IPs."""
    from .models import BlockedIP
    
    ips = BlockedIP.objects.filter(is_active=True)[:100]
    return Response({
        'blocked_ips': [
            {
                'ip': ip.ip_address,
                'reason': ip.reason,
                'blocked_at': ip.blocked_at.isoformat(),
                'threat_level': ip.threat_level,
            }
            for ip in ips
        ],
    })

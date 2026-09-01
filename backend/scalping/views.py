"""
V2 Scalping API Views — Scanner, spike detection, news detection.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scanner_status(request):
    """Get multi-asset scanner status."""
    from .multi_asset_scanner import scanner
    
    return Response(scanner.get_scan_stats())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_opportunities(request):
    """Get top trading opportunities from scanner."""
    from .multi_asset_scanner import scanner
    
    n = int(request.query_params.get('n', 5))
    return Response({
        'opportunities': scanner.get_top_opportunities(n),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def spike_history(request):
    """Get recent spike detections."""
    from .spike_detector import spike_detector
    
    symbol = request.query_params.get('symbol')
    limit = int(request.query_params.get('limit', 50))
    return Response({
        'spikes': spike_detector.get_spike_history(symbol, limit),
        'stats': spike_detector.get_spike_stats(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def news_events(request):
    """Get upcoming news events and trading pause status."""
    from .news_detector import news_detector
    
    hours = float(request.query_params.get('hours', 24))
    return Response({
        'upcoming_events': news_detector.get_upcoming_events(hours),
        'stats': news_detector.get_news_stats(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_pause(request):
    """Check if trading should be paused for a symbol."""
    from .news_detector import news_detector
    
    symbol = request.data.get('symbol')
    if not symbol:
        return Response({'error': 'symbol parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    result = news_detector.should_pause_trading(symbol)
    return Response(result)

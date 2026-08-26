from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MCPConnection, MCPServer, MCPTool
from .serializers import (
    MCPCallSerializer,
    MCPConnectionSerializer,
    MCPServerSerializer,
    MCPToolSerializer,
)


class MCPServerListView(generics.ListAPIView):
    queryset = MCPServer.objects.filter(is_active=True)
    serializer_class = MCPServerSerializer
    permission_classes = [permissions.AllowAny]


class MCPServerDetailView(generics.RetrieveAPIView):
    queryset = MCPServer.objects.all()
    serializer_class = MCPServerSerializer


class MCPToolListView(generics.ListAPIView):
    serializer_class = MCPToolSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = MCPTool.objects.filter(is_active=True)
        server = self.request.query_params.get("server")
        if server:
            queryset = queryset.filter(server__name=server)
        return queryset


class MCPConnectionListView(generics.ListAPIView):
    serializer_class = MCPConnectionSerializer

    def get_queryset(self):
        return MCPConnection.objects.all()[:20]


class MCPCallView(APIView):
    """Make a call to an MCP server tool"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MCPCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        server = MCPServer.objects.get(id=serializer.validated_data["server"])
        tool_name = serializer.validated_data["tool"]
        parameters = serializer.validated_data.get("parameters", {})

        # This would make the actual MCP call
        # For now, return placeholder
        return Response(
            {
                "status": "success",
                "server": server.display_name,
                "tool": tool_name,
                "result": {"message": f"MCP call to {tool_name} queued"},
            }
        )


class MCPHealthCheckView(APIView):
    """Check health of all MCP servers"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        servers = MCPServer.objects.filter(is_active=True)
        health = []
        for server in servers:
            health.append(
                {
                    "id": str(server.id),
                    "name": server.display_name,
                    "is_healthy": server.is_healthy,
                    "last_check": server.last_health_check,
                    "tools_count": server.tools_count,
                }
            )
        return Response(health)

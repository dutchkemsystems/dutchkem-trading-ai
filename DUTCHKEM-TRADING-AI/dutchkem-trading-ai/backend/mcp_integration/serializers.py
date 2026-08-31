from rest_framework import serializers

from .models import MCPConnection, MCPServer, MCPTool


class MCPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCPServer
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "endpoint_url",
            "is_active",
            "tools_count",
            "is_healthy",
            "last_health_check",
            "created_at",
        ]


class MCPToolSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source="server.display_name", read_only=True)

    class Meta:
        model = MCPTool
        fields = [
            "id",
            "server",
            "server_name",
            "name",
            "display_name",
            "description",
            "parameters_schema",
            "return_schema",
            "is_active",
            "category",
        ]


class MCPConnectionSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source="server.display_name", read_only=True)

    class Meta:
        model = MCPConnection
        fields = [
            "id",
            "server",
            "server_name",
            "session_id",
            "status",
            "requests_count",
            "errors_count",
            "avg_response_time",
            "connected_at",
            "disconnected_at",
        ]


class MCPCallSerializer(serializers.Serializer):
    server = serializers.UUIDField()
    tool = serializers.CharField()
    parameters = serializers.JSONField(default=dict)

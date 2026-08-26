import uuid

from django.db import models


class MCPServer(models.Model):
    SERVER_TYPES = [
        ("SYNX-MT5", "SYNX-MT5-MCP"),
        ("AKTOOLS", "AkTools Pro"),
        ("OPENALGO", "OpenAlgo"),
        ("CROSSTRADE", "CrossTrade"),
        ("OPENTRADING", "OpenTrading"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=SERVER_TYPES)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    endpoint_url = models.URLField()
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    tools_count = models.IntegerField(default=0)
    config = models.JSONField(default=dict)
    health_check_url = models.URLField(blank=True)
    last_health_check = models.DateTimeField(blank=True, null=True)
    is_healthy = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "MCP servers"

    def __str__(self):
        return self.display_name


class MCPTool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name="tools")
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    parameters_schema = models.JSONField(default=dict)
    return_schema = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ["server", "name"]
        ordering = ["server", "name"]

    def __str__(self):
        return f"{self.server.name} - {self.name}"


class MCPConnection(models.Model):
    """Track MCP server connections and usage"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name="connections")
    session_id = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[
            ("CONNECTED", "Connected"),
            ("DISCONNECTED", "Disconnected"),
            ("ERROR", "Error"),
        ],
    )
    requests_count = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    avg_response_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-connected_at"]

    def __str__(self):
        return f"{self.server.name} - {self.session_id}"

# Dutchkem Trading AI — MCP Integration Tests

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestMCPServerModel:
    def test_create_server(self):
        from mcp_integration.models import MCPServer

        server = MCPServer.objects.create(
            name="SYNX-MT5-MCP",
            display_name="SYNX MT5 MCP Server",
            description="MT5 integration server",
            is_active=True,
        )
        assert server.name == "SYNX-MT5-MCP"
        assert server.is_active is True

    def test_server_str(self):
        from mcp_integration.models import MCPServer

        server = MCPServer.objects.create(
            name="SYNX-MT5-MCP", display_name="SYNX MT5 MCP Server", description="MT5 integration server"
        )
        assert "SYNX" in str(server)

    def test_create_tool(self):
        from mcp_integration.models import MCPServer, MCPTool

        server = MCPServer.objects.create(
            name="SYNX-MT5-MCP", display_name="SYNX MT5 MCP Server", description="MT5 integration server"
        )
        tool = MCPTool.objects.create(
            server=server,
            name="get_market_data",
            display_name="Get Market Data",
            description="Get market data",
            parameters_schema={"type": "object"},
        )
        assert tool.name == "get_market_data"
        assert tool.server == server

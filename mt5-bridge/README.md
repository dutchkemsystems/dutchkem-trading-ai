# MT5 Bridge (SYNX-MT5-MCP)

Dockerized bridge between the Django backend and MetaTrader 5 terminal.

## Prerequisites

- **Docker Desktop** installed and running
- **MT5 terminal** running on the host machine
- MT5 must have "Allow WebRequest" enabled (see below)

## Setup

1. Copy the environment file and configure if needed:

```bash
cp .env.example .env
```

2. Start the bridge:

```bash
docker compose up -d
```

3. Verify it is running:

```bash
docker compose logs -f mt5-bridge
# Look for "MT5 MCP server listening on port 3000"
```

4. Check the health endpoint:

```bash
curl http://localhost:8082/health
```

## Ports

| Port  | Protocol  | Purpose                     |
|-------|-----------|-----------------------------|
| 8082  | REST      | MCP REST API (mapped to 3000) |
| 8081  | WebSocket | MCP WebSocket (mapped to 3001) |

## Configuring MT5

1. Open MT5 terminal
2. Go to **Tools → Options → Expert Advisors**
3. Enable **"Allow WebRequest for listed URL"**
4. Add `http://localhost:8082` to the allowed URLs
5. Restart MT5 (or reload EAs) for changes to take effect

## Troubleshooting

**Bridge can't connect to MT5:**
- Ensure MT5 is running on the host
- Verify MT5 has "Allow WebRequest" enabled
- Check that the MT5 port matches what the bridge expects (default: 443)

**Health check fails:**
- Wait 30 seconds after starting (container needs time to initialize)
- Check logs: `docker compose logs mt5-bridge`

**Port conflict on 8082/8081:**
- Change the host-side ports in `docker-compose.yml` if they conflict with other services

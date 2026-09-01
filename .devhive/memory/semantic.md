# Semantic Memories — DUTCHKEM-TRADING-AI

<!-- sem-001 -->
**[sem-001]** Django 4.2 + DRF backend with Python 3.12, using JWT auth, channels for WebSocket, and celery-beat for scheduling
Tags: backend, django, drf, celery

<!-- sem-002 -->
**[sem-002]** MT5 integration via SYNX-MT5-MCP Docker container exposing REST (8082) and WebSocket (8081) endpoints
Tags: mt5, docker, integration

<!-- sem-003 -->
**[sem-003]** Celery beat schedule uses DatabaseScheduler with dynamic symbol/timeframe tasks and static monitoring tasks
Tags: celery, scheduling, trading

<!-- sem-004 -->
**[sem-004]** Production deployment targets Render with Docker, PostgreSQL, and Redis services
Tags: deployment, render, docker

<!-- sem-005 -->
**[sem-005]** MT5 port inconsistency: settings_production.py defaults to 3000/3001 but Docker maps to 8082/8081
Tags: bug, mt5, ports, critical

<!-- sem-006 -->
**[sem-006]** render.yaml only defines web service - missing Celery worker and beat services for production
Tags: bug, render, celery, critical

<!-- sem-007 -->
**[sem-007]** Duplicate MT5 image references: mt5-bridge uses synx/mt5-mcp:latest but setup scripts use ghcr.io/synx-ai/synx-mt5-mcp:latest
Tags: bug, docker, mt5

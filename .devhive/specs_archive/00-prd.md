# Product Requirements Document — DUTCHKEM-TRADING-AI Deployment

## Overview
Deploy the DUTCHKEM-TRADING-AI trading platform for production in the cloud (Render) and locally (Docker Compose), with full MT5 terminal integration.

## Goals
1. Fix critical MT5 port inconsistency preventing production connections
2. Add missing Celery worker/beat services to Render deployment
3. Create comprehensive deployment documentation
4. Provide start/pause/stop procedures for all deployment modes

## Success Criteria
- MT5 bridge connects correctly in all environments (local Docker, cloud)
- Celery worker and beat run in production on Render
- Complete deployment guide covers local dev, local production, and cloud
- All services can be started/stopped via PowerShell scripts

## Constraints
- Must maintain backward compatibility with existing .env files
- Must work with free tier on Render
- MT5 terminal only runs on Windows

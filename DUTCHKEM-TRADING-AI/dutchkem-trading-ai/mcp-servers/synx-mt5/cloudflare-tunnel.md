# Cloudflare Tunnel Setup for MT5 Bridge

This guide explains how to use Cloudflare Tunnel (formerly Argo Tunnel) to securely expose your local MetaTrader 5 instance through the SYNX-MT5-MCP server.

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Fly.io Cloud  │────▶│  Cloudflare Edge │────▶│  Your Local PC  │
│   (Backend)     │     │  (Tunnel)        │     │  (MT5 + MCP)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Prerequisites

- Cloudflare account with a domain
- MetaTrader 5 installed locally
- Docker installed (for running SYNX-MT5-MCP)
- `cloudflared` CLI tool

## Step 1: Install Cloudflared

### Windows
```powershell
# Download from GitHub releases
# https://github.com/cloudflare/cloudflared/releases/latest

# Or use winget
winget install Cloudflare.cloudflared

# Or use chocolatey
choco install cloudflared
```

### macOS
```bash
brew install cloudflared
```

### Linux
```bash
# Debian/Ubuntu
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Or use the official repository
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
curl -L https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg
sudo apt update && sudo apt install cloudflared
```

## Step 2: Authenticate with Cloudflare

```bash
# This opens a browser for authentication
cloudflared tunnel login

# Select your domain (e.g., your-domain.com)
# A certificate will be saved to ~/.cloudflared/cert.pem
```

## Step 3: Create a Tunnel

```bash
# Create a named tunnel
cloudflared tunnel create dutchkem-mt5-bridge

# This outputs a tunnel ID, e.g.:
# Created tunnel dutchkem-mt5-bridge with id a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Save the tunnel ID
export TUNNEL_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

## Step 4: Configure Tunnel Routing

### Option A: Using Docker Compose (Recommended)

The `docker-compose.mt5.yml` file in this directory handles everything.

1. Create a `.env` file:
```bash
# Get your tunnel token from Cloudflare Dashboard
# Go to: Zero Trust → Networks → Tunnels → Configure → Token
CF_TUNNEL_TOKEN=your_tunnel_token_here
```

2. Start the services:
```bash
cd mcp-servers/synx-mt5
docker-compose -f docker-compose.mt5.yml up -d
```

### Option B: Manual Configuration

Create a configuration file at `~/.cloudflared/config.yml`:

```yaml
# Cloudflare Tunnel Configuration
tunnel: dutchkem-mt5-bridge
credentials-file: /root/.cloudflared/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json

# Ingress rules
ingress:
  # Route MT5 bridge traffic
  - hostname: mt5-bridge.your-domain.com
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      tcpKeepAlive: 30s

  # Catch-all rule (required)
  - service: http_status:404
```

## Step 5: Add DNS Route

```bash
# Route DNS to your tunnel
cloudflared tunnel route dns dutchkem-mt5-bridge mt5-bridge.your-domain.com

# This creates a CNAME record:
# mt5-bridge.your-domain.com → a1b2c3d4-e5f6-7890-abcd-ef1234567890.cfargotunnel.com
```

## Step 6: Run the Tunnel

### Using Docker Compose (Recommended)
```bash
docker-compose -f docker-compose.mt5.yml up -d
```

### Using cloudflared directly
```bash
# Run the tunnel
cloudflared tunnel run dutchkem-mt5-bridge

# Or run as a service (Windows)
cloudflared service install

# Or run as a service (Linux)
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

## Step 7: Update Backend Configuration

Update your Fly.io backend to use the tunnel URL:

```bash
# Set the MT5 MCP URL in Fly.io secrets
fly secrets set MT5_MCP_URL=https://mt5-bridge.your-domain.com
```

Or in your `settings_production.py`:

```python
MT5_MCP_URL = os.environ.get("MT5_MCP_URL", "https://mt5-bridge.your-domain.com")
```

## Step 8: Verify the Tunnel

```bash
# Check tunnel status
cloudflared tunnel info dutchkem-mt5-bridge

# Test the connection
curl https://mt5-bridge.your-domain.com/health
```

## Security Considerations

1. **Authentication**: Consider adding Cloudflare Access policies to protect the tunnel
2. **IP Whitelisting**: Restrict access to known IPs if needed
3. **Rate Limiting**: Configure rate limits in Cloudflare dashboard
4. **Encryption**: All traffic is encrypted end-to-end via Cloudflare

## Troubleshooting

### Tunnel won't connect
```bash
# Check logs
cloudflared tunnel run --loglevel debug dutchkem-mt5-bridge

# Verify credentials
ls -la ~/.cloudflared/
```

### MT5 not reachable
```bash
# Ensure MT5 is running and listening
netstat -an | findstr :3000

# Check Docker containers
docker ps
docker logs synx-mt5
```

### DNS not resolving
```bash
# Check DNS records
dig mt5-bridge.your-domain.com

# Verify tunnel route
cloudflared tunnel route dns list
```

## Cloudflare Zero Trust (Optional)

For production use, set up Cloudflare Access:

1. Go to Zero Trust Dashboard → Access → Applications
2. Create a new application
3. Set the domain to `mt5-bridge.your-domain.com`
4. Add authentication policies (e.g., email, One-Time Pin)
5. This adds an extra layer of security before reaching your MT5 instance

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [SYNX-MT5-MCP Documentation](https://github.com/synx-mt5/synx-mt5-mcp)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)

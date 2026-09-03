"""
DUTCHKEM — Render MT5_HOST Auto-Update
Reads the Cloudflare Tunnel URL and pushes it to Render via API.
Also triggers a deploy so changes take effect immediately.

Usage:
    python render_update_tunnel.py <tunnel_url>
    python render_update_tunnel.py  (interactive — prompts for URL)

Requires:
    RENDER_API_KEY  — set in environment or in .env file
    RENDER_SERVICE_ID — set in environment or in .env file
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────

RENDER_API = "https://api.render.com/v1"

def load_env():
    """Load from .env file if present."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    os.environ.setdefault(key, value)


def render_request(method, path, body=None):
    """Make authenticated request to Render API."""
    api_key = os.environ.get("RENDER_API_KEY", "")
    service_id = os.environ.get("RENDER_SERVICE_ID", "")

    if not api_key:
        print("ERROR: RENDER_API_KEY not set.")
        print("  Get it from: https://dashboard.render.com/u/settings#api-keys")
        print("  Set it in environment or in C:\\DUTCHKEM-TRADING-AI\\.env")
        return None

    if not service_id:
        print("ERROR: RENDER_SERVICE_ID not set.")
        print("  Find it in your Render dashboard URL:")
        print("  https://dashboard.render.com/web/srv-XXXXXXXX")
        print("  Set it in environment or in C:\\DUTCHKEM-TRADING-AI\\.env")
        return None

    url = f"{RENDER_API}{path}"
    data = json.dumps(body).encode() if body else None

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"API Error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def update_mt5_host(tunnel_url):
    """Update MT5_HOST env var on Render service."""
    service_id = os.environ.get("RENDER_SERVICE_ID", "")
    print(f"Updating MT5_HOST on service {service_id}...")
    print(f"  New URL: {tunnel_url}")

    result = render_request(
        "PUT",
        f"/services/{service_id}/env-vars/MT5_HOST",
        {"value": tunnel_url}
    )

    if result:
        print("  MT5_HOST updated successfully!")
        return True
    return False


def trigger_deploy():
    """Trigger a deploy to apply env var changes."""
    service_id = os.environ.get("RENDER_SERVICE_ID", "")
    print("Triggering deploy...")

    result = render_request(
        "POST",
        f"/services/{service_id}/deploys",
        {"clearCache": "do_not_clear"}
    )

    if result:
        deploy_id = result.get("id", "unknown")
        print(f"  Deploy triggered! ID: {deploy_id}")
        print("  Service will restart with new MT5_HOST in ~1-2 minutes.")
        return True
    return False


def read_tunnel_url_from_logs():
    """Try to read tunnel URL from tunnel.log."""
    log_path = Path(__file__).parent.parent / "logs" / "tunnel.log"
    if log_path.exists():
        content = log_path.read_text()
        for line in content.splitlines():
            if "trycloudflare.com" in line:
                # Extract URL
                for word in line.split():
                    if "https://" in word and "trycloudflare.com" in word:
                        return word.rstrip(".,;:)")
    return None


def main():
    load_env()

    # Get tunnel URL from args or logs or prompt
    tunnel_url = None
    if len(sys.argv) > 1:
        tunnel_url = sys.argv[1]
    else:
        tunnel_url = read_tunnel_url_from_logs()
        if tunnel_url:
            print(f"Found tunnel URL from logs: {tunnel_url}")
        else:
            tunnel_url = input("Enter Cloudflare Tunnel URL: ").strip()

    if not tunnel_url:
        print("ERROR: No tunnel URL provided.")
        sys.exit(1)

    # Validate URL
    if not tunnel_url.startswith("https://"):
        tunnel_url = f"https://{tunnel_url}"
    if "trycloudflare.com" not in tunnel_url:
        print(f"WARNING: URL doesn't look like a Cloudflare tunnel: {tunnel_url}")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != "y":
            sys.exit(1)

    print()
    print("=" * 50)
    print("  Render MT5_HOST Auto-Update")
    print("=" * 50)
    print()

    # Step 1: Update env var
    if not update_mt5_host(tunnel_url):
        print("FAILED to update MT5_HOST. Check your API key and service ID.")
        sys.exit(1)

    print()

    # Step 2: Trigger deploy
    confirm = input("Trigger deploy now? (y/n, default: y): ").strip().lower()
    if confirm in ("", "y", "yes"):
        if not trigger_deploy():
            print("WARNING: Deploy trigger failed. Update env var manually or redeploy from dashboard.")

    print()
    print("Done! Render will use the new tunnel URL.")
    print()


if __name__ == "__main__":
    main()

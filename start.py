"""Startup script — runs migrations, collectstatic, then launches supervisord."""
import os
import subprocess
import sys


def run(cmd, label):
    print(f"[{label}] Running: {cmd}", flush=True)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  WARNING: {label} exited with code {result.returncode}", flush=True)
    return result.returncode


def main():
    print("=" * 50, flush=True)
    print("  Dutchkem Trading AI — Starting (All-in-One)", flush=True)
    print("=" * 50, flush=True)
    sys.stdout.flush()

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Migrations
    run("python manage.py migrate --no-input", "migrate")

    # Static files
    run("python manage.py collectstatic --no-input", "collectstatic")

    # Launch supervisord (Django + Celery Worker + Celery Beat)
    print("[supervisord] Starting all services...", flush=True)
    os.execvp("supervisord", ["supervisord", "-c", "/app/supervisord.conf"])


if __name__ == "__main__":
    main()

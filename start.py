"""Startup script — avoids all shell/CRLF issues on Windows builds."""
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
    print("  Dutchkem Trading AI — Starting", flush=True)
    print("=" * 50, flush=True)
    sys.stdout.flush()

    # Migrations
    run("python manage.py migrate --no-input", "migrate")

    # Static files
    run("python manage.py collectstatic --no-input", "collectstatic")

    # Gunicorn — use os.execvp to replace this process
    port = os.environ.get("PORT", "8000")
    workers = os.environ.get("WEB_CONCURRENCY", "1")
    args = [
        "gunicorn", "config.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
        "--workers", workers,
        "--timeout", "180",
        "--preload",
        "--access-logfile", "-",
        "--error-logfile", "-",
    ]
    print(f"[gunicorn] {' '.join(args)}", flush=True)
    os.execvp("gunicorn", args)


if __name__ == "__main__":
    main()

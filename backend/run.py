#!/usr/bin/env python3
"""
Startup script for the Stellar backend server.

Usage:
    python run.py              # Run with default settings
    python run.py --port 8080  # Run on custom port
    python run.py --no-reload  # Disable auto-reload
"""
import sys
import argparse
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def main():
    parser = argparse.ArgumentParser(description="Run Stellar backend server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Log level")

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 Stellar Backend Server")
    print("=" * 60)
    print(f"Starting server at http://{args.host}:{args.port}")
    print(f"API docs: http://localhost:{args.port}/docs")
    print(f"Health check: http://localhost:{args.port}/health")
    print("=" * 60)
    print()

    import uvicorn

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()

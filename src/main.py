#!/usr/bin/env python3
"""
Virtual Test Engineer - Main Application
"""

import uvicorn
import argparse
from pathlib import Path


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="Virtual Test Engineer")
    parser.add_argument(
        "--config",
        type=str,
        default="config/testbench.yaml",
        help="Path to test bench configuration file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Ensure config directory exists
    config_dir = Path(args.config).parent
    config_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Starting Virtual Test Engineer...")
    print(f"📁 Config file: {args.config}")
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print(f"🔄 Auto-reload: {'enabled' if args.reload else 'disabled'}")

    # Start the server
    uvicorn.run(
        "src.api.endpoints:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=["src"] if args.reload else None
    )


if __name__ == "__main__":
    main()
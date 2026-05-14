import asyncio
from mcp_server.stdio import run_stdio_mcp

if __name__ == "__main__":
    try:
        asyncio.run(run_stdio_mcp())
    except KeyboardInterrupt:
        pass

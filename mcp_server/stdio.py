import asyncio
import logging
import sys
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions

from mcp_server.server import mcp_server
import importlib.metadata

async def run_stdio_mcp():
    """Entry point for stdio-based MCP communication."""
    # Reconfigure logging to stderr to avoid corrupting stdout
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    version = "0.1.0"
    try:
        version = importlib.metadata.version("sdtb")
    except:
        pass
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sdtb-commander",
                    server_version=version,
                    capabilities=mcp_server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logging.error(f"MCP server error: {e}")

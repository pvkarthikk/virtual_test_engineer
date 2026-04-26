import os
import sys
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

# Import the SDTB system singleton
# We need to ensure the path is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from routers.system import system as sdtb_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sdtb_mcp")

# Initialize MCP Server
server = Server("sdtb-commander")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available hardware control tools."""
    return [
        types.Tool(
            name="list_channels",
            description="Lists all configured hardware channels and their current status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_channel_info",
            description="Get detailed metadata about a specific channel (units, ranges, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "The ID of the channel to query."}
                },
                "required": ["channel_id"],
            },
        ),
        types.Tool(
            name="read_channel",
            description="Read the current value of a hardware channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "The ID of the channel to read."}
                },
                "required": ["channel_id"],
            },
        ),
        types.Tool(
            name="write_channel",
            description="Write a value to a hardware channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "The ID of the channel to write to."},
                    "value": {"type": "number", "description": "The value to set."}
                },
                "required": ["channel_id", "value"],
            },
        ),
        types.Tool(
            name="get_system_summary",
            description="Get an overview of the system status, including connected devices.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="connect_system",
            description="Connects all configured hardware devices. Must be called before reading or writing channels.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="disconnect_system",
            description="Safely disconnects all hardware devices. Call this when testing is finished.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List documentation resources."""
    return [
        types.Resource(
            uri="sdtb://docs/control-guide",
            name="SDTB Control Guide",
            description="Instructions on how to control the Software Defined Test Bench properly.",
            mimeType="text/markdown",
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a documentation resource."""
    if uri == "sdtb://docs/control-guide":
        return """# SDTB Control Guide

To interact with the Software Defined Test Bench (SDTB) successfully, you must follow this lifecycle:

1.  **Connect**: Call `connect_system` first. This establishes physical links to Arduinos, CAN interfaces, etc.
2.  **Discover**: Call `list_channels` to see which virtualized signals are available for the current bench setup.
3.  **Interact**: Use `read_channel` to monitor sensors and `write_channel` to drive actuators.
4.  **Monitor**: Use `get_system_summary` periodically to ensure all hardware remains online.
5.  **Disconnect**: When your task is complete, call `disconnect_system` to release hardware resources safely.

**Note**: All controls are abstracted. You do not need to know which pin is connected to which device; simply use the `channel_id` provided by `list_channels`.
"""
    raise ValueError(f"Resource not found: {uri}")

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    try:
        if name == "list_channels":
            channels = sdtb_system.channel_manager.get_all_channels()
            channel_list = [
                {
                    "id": c.channel_id,
                    "unit": c.properties.unit,
                    "range": [c.properties.min, c.properties.max]
                }
                for c in channels
            ]
            return [types.TextContent(type="text", text=json.dumps(channel_list, indent=2))]

        elif name == "get_channel_info":
            ch_id = arguments.get("channel_id")
            info = sdtb_system.channel_manager.get_channel_info(ch_id)
            if not info:
                return [types.TextContent(type="text", text=f"Error: Channel '{ch_id}' not found.")]
            
            return [types.TextContent(type="text", text=json.dumps(info.model_dump(), indent=2))]

        elif name == "read_channel":
            ch_id = arguments.get("channel_id")
            try:
                value = sdtb_system.channel_manager.read_channel(ch_id)
                info = sdtb_system.channel_manager.get_channel_info(ch_id)
                unit = info.properties.unit if info else ""
                return [types.TextContent(type="text", text=f"Channel '{ch_id}' current value: {value:.2f} {unit}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error reading channel '{ch_id}': {str(e)}")]

        elif name == "write_channel":
            ch_id = arguments.get("channel_id")
            value = arguments.get("value")
            try:
                sdtb_system.channel_manager.write_channel(ch_id, value)
                return [types.TextContent(type="text", text=f"Successfully set channel '{ch_id}' to {value}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error writing to channel '{ch_id}': {str(e)}")]

        elif name == "get_system_summary":
            devices = sdtb_system.device_manager.get_all_devices()
            channels = sdtb_system.channel_manager.get_all_channels()
            summary = {
                "status": "online" if any(d.is_connected for d in devices.values()) else "offline",
                "device_count": len(devices),
                "channel_count": len(channels),
                "connected_devices": [
                    f"{dev_id} ({d.vendor} {d.model})" 
                    for dev_id, d in devices.items() 
                    if d.is_connected
                ]
            }
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "connect_system":
            try:
                sdtb_system.device_manager.connect_all()
                return [types.TextContent(type="text", text="Hardware connection sequence completed successfully.")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error connecting system: {str(e)}")]

        elif name == "disconnect_system":
            try:
                sdtb_system.device_manager.disconnect_all()
                return [types.TextContent(type="text", text="Hardware disconnection sequence completed.")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error disconnecting system: {str(e)}")]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Internal Error: {str(e)}")]

async def main():
    # Ensure system is started inside the running event loop
    try:
        sdtb_system.startup()
        
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sdtb-commander",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    finally:
        # Graceful shutdown of hardware and background tasks
        await sdtb_system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

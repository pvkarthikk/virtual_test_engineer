import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Response
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server.sse import SseServerTransport

# Access the singleton system instance from the system router
from routers.system import system as sdtb_system

logger = logging.getLogger("sdtb_mcp")
router = APIRouter(prefix="/mcp", tags=["MCP"])

# Initialize MCP Server
mcp_server = Server("sdtb-commander")

# Define the SSE transport
sse = SseServerTransport("/mcp/messages")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available hardware control tools."""
    return [
        types.Tool(
            name="list_channels",
            description="Lists all configured hardware channels and their current status.",
            inputSchema={"type": "object", "properties": {}},
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
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="connect_system",
            description="Connects all configured hardware devices. Must be called before reading or writing channels.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="disconnect_system",
            description="Safely disconnects all hardware devices. Call this when testing is finished.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="read_channels",
            description="Read the current values of multiple hardware channels in batch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of channel IDs to read."
                    }
                },
                "required": ["channel_ids"],
            },
        ),
        types.Tool(
            name="write_channels",
            description="Write values to multiple hardware channels in batch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "writes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "channel_id": {"type": "string"},
                                "value": {"type": "number"}
                            },
                            "required": ["channel_id", "value"]
                        },
                        "description": "List of channel writes to perform."
                    }
                },
                "required": ["writes"],
            },
        )
    ]

@mcp_server.list_resources()
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

@mcp_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a documentation resource."""
    if uri == "sdtb://docs/control-guide":
        return """# SDTB Control Guide

To interact with the Software Defined Test Bench (SDTB) successfully, you must follow this lifecycle:

1.  **Connect**: Call `connect_system` first. This establishes physical links to Arduinos, CAN interfaces, etc.
2.  **Discover**: Call `list_channels` to see which virtualized signals are available.
3.  **Interact**: Use `read_channel` to monitor sensors and `write_channel` to drive actuators.
4.  **Monitor**: Use `get_system_summary` periodically to ensure all hardware remains online.
5.  **Disconnect**: When your task is complete, call `disconnect_system` to release hardware resources.

**Note**: All controls are abstracted. You do not need to know which pin is connected to which device.
"""
    raise ValueError(f"Resource not found: {uri}")

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
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
            value = await sdtb_system.channel_manager.read_channel(ch_id)
            info = sdtb_system.channel_manager.get_channel_info(ch_id)
            unit = info.properties.unit if info else ""
            return [types.TextContent(type="text", text=f"Channel '{ch_id}' current value: {value:.2f} {unit}")]

        elif name == "write_channel":
            if sdtb_system.test_engine.is_test_running:
                return [types.TextContent(type="text", text="Error: Cannot perform manual write: A test sequence is currently running.")]
            ch_id = arguments.get("channel_id")
            value = arguments.get("value")
            await sdtb_system.channel_manager.write_channel(ch_id, value)
            return [types.TextContent(type="text", text=f"Successfully set channel '{ch_id}' to {value}")]

        elif name == "get_system_summary":
            devices = sdtb_system.device_manager.get_all_devices()
            channels = sdtb_system.channel_manager.get_all_channels()
            summary = {
                "status": "online" if any(d.is_connected for d in devices.values()) else "offline",
                "device_count": len(devices),
                "channel_count": len(channels),
                "connected_devices": [f"{dev_id} ({d.vendor} {d.model})" for dev_id, d in devices.items() if d.is_connected]
            }
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "connect_system":
            await sdtb_system.device_manager.connect_all()
            return [types.TextContent(type="text", text="Hardware connection sequence completed successfully.")]

        elif name == "disconnect_system":
            await sdtb_system.device_manager.disconnect_all()
            return [types.TextContent(type="text", text="Hardware disconnection sequence completed.")]

        elif name == "read_channels":
            ch_ids = arguments.get("channel_ids", [])
            results = []
            for ch_id in ch_ids:
                try:
                    value = await sdtb_system.channel_manager.read_channel(ch_id)
                    info = sdtb_system.channel_manager.get_channel_info(ch_id)
                    results.append({
                        "id": ch_id,
                        "value": round(value, 2),
                        "unit": info.properties.unit if info else "",
                        "status": "success"
                    })
                except Exception as e:
                    results.append({"id": ch_id, "status": "error", "message": str(e)})
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "write_channels":
            if sdtb_system.test_engine.is_test_running:
                return [types.TextContent(type="text", text="Error: Cannot perform manual write: A test sequence is currently running.")]
            writes = arguments.get("writes", [])
            results = []
            for w in writes:
                ch_id = w.get("channel_id")
                val = w.get("value")
                try:
                    await sdtb_system.channel_manager.write_channel(ch_id, val)
                    results.append({"id": ch_id, "status": "success"})
                except Exception as e:
                    results.append({"id": ch_id, "status": "error", "message": str(e)})
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# To avoid "Unexpected ASGI message" and "NoneType is not callable" errors,
# we use a NoOpResponse that tells Starlette the response is already handled.
class NoOpResponse(Response):
    async def __call__(self, scope, receive, send):
        return

async def handle_sse(request: Request):
    """Handle the SSE connection for MCP."""
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sdtb-commander",
                server_version="0.1.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    return NoOpResponse()

async def handle_messages(request: Request):
    """Handle incoming MCP messages over the SSE transport."""
    await sse.handle_post_message(request.scope, request.receive, request._send)
    return NoOpResponse()

# We expose the sub-app or the routes to be mounted in main.py
from starlette.routing import Route
mcp_routes = [
    Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
    Route("/mcp/messages", endpoint=handle_messages, methods=["POST"]),
]

import asyncio
import json
import logging
from typing import List
from mcp.server import Server
import mcp.types as types

import httpx
from mcp_server.client import SDTBRestClient

logger = logging.getLogger("sdtb_mcp")

# Initialize MCP Server
mcp_server = Server("sdtb-commander")

# Initialize the REST client
# In a production environment, this URL could be configurable
client = SDTBRestClient("http://localhost:8000")

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
        ),
        types.Tool(
            name="run_test",
            description="Run a test script against the hardware. You can provide either a raw JSONL script string OR a saved script_id. Each line in a raw script is a test step (write, wait, assert). The test runs in the background; use get_test_status and get_test_history to monitor progress.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "Optional. The raw JSONL test script content. Each line is a JSON object with an 'action' field ('write','wait','assert')"},
                    "script_id": {"type": "string", "description": "Optional. The ID of a saved test script to execute."}
                },
            },
        ),
        types.Tool(
            name="list_test_scripts",
            description="List all saved test scripts and their descriptions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_test_script",
            description="Retrieve the full content (steps) of a specific test script by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {"type": "string", "description": "The unique ID of the test script."}
                },
                "required": ["script_id"],
            },
        ),
        types.Tool(
            name="save_test_script",
            description="Save a new test script for future use.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "A human-readable description of what the test does."},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["write", "wait", "assert", "fault"]},
                                "channel": {"type": "string"},
                                "value": {"type": "number"},
                                "duration_ms": {"type": "integer"},
                                "condition": {"type": "string", "enum": [">", ">=", "<", "<=", "==", "!="]},
                                "device": {"type": "string"},
                                "signal": {"type": "string"},
                                "fault_id": {"type": "string"}
                            },
                            "required": ["action"]
                        },
                        "description": "List of test steps."
                    }
                },
                "required": ["description", "steps"],
            },
        ),
        types.Tool(
            name="stop_test",
            description="Abort a currently running test sequence",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_test_status",
            description="Get the current status of the test engine (whether a test is running and if an abort was requested).",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_test_history",
            description="Get the results of executed test steps. Returns a list of step results with pass/fail/error status.",
            inputSchema={"type": "object", "properties": {
                "last_n":{
                    "type": "integer",
                    "description": "Optional. Return only the last N results. If omitted, returns all results.",
                }
            }},
        ),
        types.Tool(
            name="list_can_interfaces",
            description="Lists all active CAN bus interfaces and their buffer status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="read_can_log",
            description="Reads the most recent raw CAN frames from a specific bus.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "The ID of the device (e.g. 'mock')."},
                    "bus": {"type": "string", "description": "The CAN bus name (e.g. 'can0')."},
                    "count": {"type": "integer", "description": "Number of frames to retrieve (default 50)."},
                    "arb_id": {"type": "string", "description": "Optional hex filter for arbitration ID (e.g. '0x100')."}
                },
                "required": ["device_id", "bus"],
            },
        ),
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
        ),
        types.Resource(
            uri="sdtb://docs/test-script-guide",
            name="SDTB Test Script Guide",
            description="Instructions on how to write and run test scripts for the run_test tool.",
            mimeType="text/markdown",
        ),
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
    if uri == "sdtb://docs/test-script-guide":
        return """# SDTB Test Script Guide
The `run_test` tool accepts a **JSONL** (JSON Lines) string where each line is a test step.

## Step Types

### 1. Write - Set a channel value
```json
{"action": "write", "channel": "Throttle_Command", "value": 50.0}
```
- `channel`: The channel ID to write to (must match a channel from `list_channels`).
- `value`: Numeric value within the channel's valid range.

### 2. Wait - Pause the execution
```json
{"action": "wait", "duration_ms": 1000}
```
- `duration_ms`: Time to Wait in milliseconds.

### 3. Assert - Validate a channel reading
```json
{"action": "assert", "channel": "Engine_Speed", "condition": ">=", "value": 800.0}
```
- `channel`: The channel ID to assert.
- `condition`: The condition to assert ("==", "!=", ">", "<", ">=", "<=").
- `value`: The value to compare against.

### 4. Fault - Inject a hardware fault
```json
{"action": "fault", "device": "mock", "signal": "Throttle_Sensor", "fault_id": "short_to_ground", "duration_ms": 2000}
```
- `device`: The device ID (e.g. from `get_system_summary`).
- `signal`: The signal/channel to inject the fault on.
- `fault_id`: Fault type identifier (e.g. `short_to_ground`, `open_circuit`).
- `duration_ms`: Optional. Duration in ms before auto-clearing. If omitted, the fault persists until manually cleared.

## Example Script

A 3-step script that sets the throttle to 50%, waits for 1 second, and then asserts that the engine speed is greater than or equal to 800 RPM.

```json
{"action": "write", "channel": "Throttle_Command", "value": 50.0}
{"action": "wait", "duration_ms": 1000}
{"action": "assert", "channel": "Engine_Speed", "condition": ">=", "value": 800.0}
```

## Workflow

1. Call `run_test` with the script. It returns a token and runs in the background.
2. Poll `get_test_status` to check if the test is still running.
3. Call `get_test_history` to see per-step pass/fail/error results.
4. Use `stop_test` to abort the test sequence if needed.

## Notes

- Each step runs sequentially, If an assert fails, the test stops.
- While a test is running, manual `write_channel` calls are blocked.
- Only one test can run at a time.
"""
    raise ValueError(f"Resource not found: {uri}")

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool execution requests."""
    try:
        if name == "list_channels":
            channels = await client.list_channels()
            channel_list = [
                {
                    "id": c["channel_id"],
                    "unit": c["properties"]["unit"],
                    "range": [c["properties"]["min"], c["properties"]["max"]]
                }
                for c in channels
            ]
            return [types.TextContent(type="text", text=json.dumps(channel_list, indent=2))]

        elif name == "get_channel_info":
            ch_id = arguments.get("channel_id")
            info = await client.get_channel_info(ch_id)
            return [types.TextContent(type="text", text=json.dumps(info, indent=2))]

        elif name == "read_channel":
            ch_id = arguments.get("channel_id")
            data = await client.read_channel(ch_id)
            value = data["value"]
            # We don't easily have unit here without another call or refactoring REST
            return [types.TextContent(type="text", text=f"Channel '{ch_id}' current value: {value:.2f}")]

        elif name == "write_channel":
            ch_id = arguments.get("channel_id")
            value = arguments.get("value")
            result = await client.write_channel(ch_id, value)
            return [types.TextContent(type="text", text=result.get("message", "Success"))]

        elif name == "get_system_summary":
            summary = await client.get_system_summary()
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "connect_system":
            result = await client.connect_system()
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "disconnect_system":
            result = await client.disconnect_system()
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "read_channels":
            ch_ids = arguments.get("channel_ids", [])
            results = []
            for ch_id in ch_ids:
                try:
                    data = await client.read_channel(ch_id)
                    results.append({
                        "id": ch_id,
                        "value": round(data["value"], 2),
                        "status": "success"
                    })
                except Exception as e:
                    results.append({"id": ch_id, "status": "error", "message": str(e)})
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "write_channels":
            writes = arguments.get("writes", [])
            results = []
            for w in writes:
                ch_id = w.get("channel_id")
                val = w.get("value")
                try:
                    await client.write_channel(ch_id, val)
                    results.append({"id": ch_id, "status": "success"})
                except Exception as e:
                    results.append({"id": ch_id, "status": "error", "message": str(e)})
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "run_test":
            script = arguments.get("script", "")
            script_id = arguments.get("script_id", "")
            result = await client.run_test(script=script, script_id=script_id)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_test_scripts":
            scripts = await client.list_test_scripts()
            return [types.TextContent(type="text", text=json.dumps(scripts, indent=2))]

        elif name == "get_test_script":
            script_id = arguments.get("script_id")
            script = await client.get_test_script(script_id)
            return [types.TextContent(type="text", text=json.dumps(script, indent=2))]

        elif name == "save_test_script":
            description = arguments.get("description")
            steps = arguments.get("steps", [])
            result = await client.save_test_script(description, steps)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "stop_test":
            result = await client.stop_test()
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_test_status":
            status = await client.get_test_status()
            return [types.TextContent(type="text", text=json.dumps(status, indent=2))]
        
        elif name == "get_test_history":
            history = await client.get_test_history()
            return [types.TextContent(type="text", text=json.dumps(history, indent=2))]

        elif name == "list_can_interfaces":
            interfaces = await client.list_can_interfaces()
            return [types.TextContent(type="text", text=json.dumps(interfaces, indent=2))]

        elif name == "read_can_log":
            dev_id = arguments.get("device_id")
            bus = arguments.get("bus")
            count = arguments.get("count", 50)
            arb_id = arguments.get("arb_id")
            
            frames = await client.read_can_log(dev_id, bus, count, arb_id)
            return [types.TextContent(type="text", text=json.dumps(frames, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during tool {name}: {e.response.text}")
        return [types.TextContent(type="text", text=f"Error (HTTP {e.response.status_code}): {e.response.text}")]
    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

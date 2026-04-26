# SDTB API Reference

The Software Defined Test Bench (SDTB) exposes a REST API built with FastAPI. All endpoints are relative to the server root (default: `http://localhost:8000`).

## System Management

### GET `/system/status`
Returns the current operational status of the SDTB system.

### POST `/system/startup`
Initiates the system startup sequence (plugin discovery and channel mapping).

### POST `/system/shutdown`
Safely shuts down the system and disconnects all hardware.

### POST `/system/restart`
Performs a full system restart.

### GET `/system/logs/stream`
SSE endpoint for real-time system logs.

---

## Device Management

### GET `/device`
Lists all discovered hardware devices.

### GET `/device/{device_id}`
Retrieves detailed information about a specific device.

### POST `/device/{device_id}/toggle`
Enable or disable a specific device.
- **Body**: `{"enabled": boolean}`

### GET `/device/{device_id}/signal`
Lists all raw hardware signals exposed by the device.

---

## Channel Operations

Logical channels map to raw device signals with scaling and unit conversion.

### GET `/channel`
Lists all configured logical channels.

### GET `/channel/{channel_id}`
Reads the scaled value of a channel.

### PUT `/channel/{channel_id}`
Writes a scaled value to a channel.
- **Query Param**: `value: float`

### GET `/channel/{channel_id}/stream`
SSE endpoint for real-time updates of a channel's scaled value.

---

## Test Execution

### POST `/test/run`
Executes a test sequence in JSONL format.
- **Body**: Text/Plain (JSONL content)

### POST `/test/stop`
Aborts the currently running test sequence.

### GET `/test/status`
Returns the status of the test engine.

---

## Flashing Protocols

### GET `/flash/protocols`
Lists all discovered flash protocols.

### POST `/flash/connect`
Connects to a specific flash target.
- **Query Param**: `flash_id: string`

### POST `/flash`
Starts a flashing operation.
- **Form Data**:
  - `flash_id`: ID of the protocol to use.
  - `file`: The binary file to flash.
  - `params`: (Optional) JSON string of parameters.

### GET `/flash/status`
Gets the status of a flash operation.
- **Query Params**: `flash_id`, `execution_id`

### GET `/flash/log`
SSE endpoint to stream logs for a specific flash operation.

---

## MCP Integration

### GET `/mcp/sse`
Entry point for Model Context Protocol (MCP) clients using SSE transport.

### POST `/mcp/messages`
Endpoint for receiving MCP messages.

# SDTB API Reference

The Software Defined Test Bench (SDTB) exposes a REST API built with FastAPI. All endpoints are relative to the server root (default: `http://localhost:8000`).

## System Management

### GET `/system/config`
Get current system configuration.

### POST `/system/connect`
Initiates the system connection sequence (discovery and hardware mapping).

### POST `/system/disconnect`
Safely disconnects all hardware and stops background loops.

### POST `/system/restart`
Performs a full system restart.

### POST `/system/fault/clear`
Global safety mechanism to clear all faults on all devices.

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
- **Body**: `{"enabled": boolean}` (JSON)

### POST `/device/{device_id}/restart`
Re-initialize and restart a specific hardware device.

### GET `/device/{device_id}/signals`
Lists all raw hardware signals exposed by the device.

### GET `/device/{device_id}/signal/{signal_id}`
Read raw hardware signal value.

### PUT `/device/{device_id}/signal/{signal_id}`
Write raw hardware signal value.
- **Body**: `{"value": float}`

### GET `/device/{device_id}/signal/{signal_id}/stream`
SSE stream for real-time raw signal updates.

### GET `/device/{device_id}/signal/{signal_id}/fault`
List available fault injection types for the signal.

### POST `/device/{device_id}/signal/{signal_id}/fault`
Inject a hardware fault.
- **Body**: `{"fault_id": string}`

### DELETE `/device/{device_id}/signal/{signal_id}/fault`
Clear active hardware fault on the signal.

---

## Channel Operations

Logical channels map to raw device signals with scaling and unit conversion.

### GET `/channel`
Lists all configured logical channels.

### GET `/channel/{channel_id}`
Reads the scaled value of a channel.

### PUT `/channel/{channel_id}`
Writes a scaled value to a channel.
- **Body**: `{"value": float}`

### GET `/channel/{channel_id}/info`
Get detailed channel metadata and scaling info.

### GET `/channel/{channel_id}/status`
Get current operational status of the channel.

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

### POST `/flash/abort`
Aborts an ongoing flashing operation.
- **Query Params**: `flash_id`, `execution_id`

### GET `/flash/history`
Retrieve history of flashing operations.

---

## MCP Integration

### GET `/mcp/sse`
Entry point for Model Context Protocol (MCP) clients using SSE transport.

### POST `/mcp/messages`
Endpoint for receiving MCP messages.

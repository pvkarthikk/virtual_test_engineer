# 03_RestAPI.md - Complete REST API Endpoint Reference

## API Overview

- **Base URL**: `http://localhost:8080/api/v1`
- **Authentication**: None (local deployment)
- **Content-Type**: `application/json`
- **Framework**: FastAPI with automatic OpenAPI documentation
- **Real-time**: WebSocket support for streaming data

## 1. Health & Discovery Endpoints

### GET /health
Health check endpoint returning test bench status.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": 1704110400.0,
  "details": {
    "state": "idle",
    "plugins_loaded": 3,
    "channels_available": 3
  }
}
```

### GET /bench
Get test bench information and current state.

**Response (200):**
```json
{
  "id": "virtual_test_bench_001",
  "name": "Virtual Test Engineer",
  "version": "1.0.0",
  "status": "idle",
  "uptime_seconds": 1704110400.0,
  "active_dut_profile": null,
  "active_scenario": null,
  "capabilities": {
    "max_channels": 128,
    "supported_channel_types": ["digital", "analog", "pwm"],
    "supported_bus_types": ["can"],
    "plugins_loaded": ["gpio", "analog", "can"]
  }
}
```

### GET /capabilities
Get test bench capabilities and supported features.

**Response (200):**
```json
{
  "max_channels": 128,
  "supported_channel_types": ["digital", "analog", "pwm"],
  "supported_bus_types": ["can"],
  "plugins_loaded": ["gpio", "analog", "can"],
  "features": ["async_execution", "real_time_streaming", "artifact_generation"]
}
```

## 2. Channel Management Endpoints

### GET /channels
List all available channels.

**Response (200):**
```json
{
  "channels": [
    {
      "id": "throttle_position",
      "type": "analog",
      "status": "active"
    },
    {
      "id": "engine_speed",
      "type": "pwm",
      "status": "active"
    },
    {
      "id": "eco_mode",
      "type": "digital",
      "status": "active"
    }
  ]
}
```

### GET /channels/{channel_id}
Read the current value of a channel.

**Parameters:**
- `channel_id` (path): Channel identifier

**Response (200):**
```json
{
  "channel_id": "throttle_position",
  "value": 75.5,
  "timestamp": 1704110400.0,
  "quality": "good"
}
```

**Error Responses:**
- `404`: Channel not found
- `500`: Read error

### PUT /channels/{channel_id}
Write a value to a channel.

**Parameters:**
- `channel_id` (path): Channel identifier

**Request Body:**
```json
{
  "value": 50
}
```

**Response (200):**
```json
{
  "channel_id": "throttle_position",
  "value": 50,
  "timestamp": 1704110400.0,
  "status": "ok"
}
```

**Error Responses:**
- `400`: Missing value field
- `404`: Channel not found
- `500`: Write error

### GET /channels/{channel_id}/info
Get detailed information about a channel.

**Parameters:**
- `channel_id` (path): Channel identifier

**Response (200):**
```json
{
  "id": "throttle_position",
  "type": "analog",
  "instrument": "throttle_sensor",
  "scaling": {
    "input_range": [0, 1023],
    "output_range": [0, 100],
    "units": "%"
  },
  "config": {},
  "last_value": 75.5,
  "last_read_time": 1704110400.0
}
```

## 3. Test Execution Endpoints

### POST /runs
Start a new test run.

**Request Body:**
```json
{
  "scenario_id": "throttle_response_basic",
  "parameters": {},
  "async": true
}
```

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": "throttle_response_basic",
  "status": "queued",
  "created_at": 1704110400.0
}
```

**Error Responses:**
- `400`: Missing scenario_id
- `500`: Test execution error

### GET /runs/{run_id}
Get the status of a test run.

**Parameters:**
- `run_id` (path): Test run identifier

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": "throttle_response_basic",
  "status": "running",
  "start_time": 1704110400.0,
  "end_time": null,
  "progress": {
    "current_step": 2,
    "total_steps": 4,
    "percentage": 50.0
  },
  "parameters": {}
}
```

**Error Responses:**
- `404`: Test run not found

### DELETE /runs/{run_id}
Abort a running test run.

**Parameters:**
- `run_id` (path): Test run identifier

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "aborted",
  "aborted_at": 1704110400.0
}
```

**Error Responses:**
- `404`: Test run not found

### GET /runs/{run_id}/results
Get the complete results of a test run.

**Parameters:**
- `run_id` (path): Test run identifier

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": "throttle_response_basic",
  "status": "completed",
  "start_time": 1704110400.0,
  "end_time": 1704110430.0,
  "duration_ms": 30000.0,
  "parameters": {},
  "steps": [
    {
      "step_id": "set_throttle_50",
      "status": "passed",
      "start_time": 1704110400.0,
      "end_time": 1704110400.5,
      "readings": {
        "throttle_position": 50
      }
    },
    {
      "step_id": "wait_settle",
      "status": "passed",
      "start_time": 1704110400.5,
      "end_time": 1704110402.5,
      "readings": {}
    },
    {
      "step_id": "read_engine_speed",
      "status": "passed",
      "start_time": 1704110402.5,
      "end_time": 1704110402.6,
      "readings": {
        "engine_speed": 5.2
      }
    },
    {
      "step_id": "assert_response",
      "status": "passed",
      "start_time": 1704110402.6,
      "end_time": 1704110402.7,
      "readings": {}
    }
  ],
  "summary": {
    "total_steps": 4,
    "passed_steps": 4,
    "failed_steps": 0,
    "assertions": {
      "total": 1,
      "passed": 1,
      "failed": 0
    }
  }
}
```

**Error Responses:**
- `404`: Test run not found
- `409`: Test run not completed yet

## 4. Plugin Management Endpoints

### GET /plugins
List loaded and available plugins.

**Response (200):**
```json
{
  "loaded_plugins": [
    {
      "name": "arduino_gpio",
      "type": "gpio",
      "status": "initialized"
    },
    {
      "name": "arduino_analog",
      "type": "analog",
      "status": "initialized"
    },
    {
      "name": "arduino_can",
      "type": "can",
      "status": "initialized"
    }
  ],
  "available_plugins": ["gpio", "analog", "can"]
}
```

## 5. Configuration Endpoints

### POST /config/reload
Reload the test bench configuration from disk.

**Response (200):**
```json
{
  "status": "reloaded",
  "timestamp": 1704110400.0
}
```

**Error Responses:**
- `500`: Configuration reload failed

## 6. Firmware Flashing Endpoints

### POST /flash
Initiate a firmware flashing operation to a target device.

**Request Body:**
```json
{
  "target_device": "arduino_ecu",
  "firmware_file": "throttle_control_v1.2.hex",
  "protocol": "avrdude",
  "parameters": {
    "programmer": "arduino",
    "port": "/dev/ttyACM0",
    "baudrate": 115200,
    "chip": "atmega328p"
  },
  "verify_after_flash": true,
  "backup_current_firmware": false
}
```

**Response (202 Accepted):**
```json
{
  "flash_id": "flash_550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_duration": 30,
  "created_at": 1704110400.0
}
```

**Error Responses:**
- `400`: Missing required fields (target_device, firmware_file, protocol)
- `404`: Target device or firmware file not found
- `409`: Another flash operation already in progress

### GET /flash/status
Get status of flashing operations.

**Query Parameters:**
- `flash_id` (optional): Specific flash operation ID

**Response (200):**
```json
{
  "flash_id": "flash_550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": {
    "percentage": 45,
    "current_step": "writing_flash",
    "step_description": "Writing firmware to flash memory",
    "bytes_written": 14336,
    "total_bytes": 32768
  },
  "start_time": 1704110400.0,
  "estimated_completion": 1704110430.0,
  "target_device": "arduino_ecu",
  "firmware_file": "throttle_control_v1.2.hex"
}
```

**Error Responses:**
- `404`: Flash operation not found

### GET /flash/status/{flash_id}
Get detailed status and logs for a specific flash operation.

**Parameters:**
- `flash_id` (path): Flash operation identifier

**Response (200):**
```json
{
  "flash_id": "flash_550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "success": true,
    "verification_passed": true,
    "bytes_written": 32768,
    "flash_time_ms": 28500,
    "md5_checksum": "a1b2c3d4e5f6..."
  },
  "start_time": 1704110400.0,
  "end_time": 1704110428.5,
  "logs": [
    {
      "timestamp": 1704110400.0,
      "level": "info",
      "message": "Starting flash operation"
    },
    {
      "timestamp": 1704110405.0,
      "level": "info",
      "message": "Erasing flash memory"
    },
    {
      "timestamp": 1704110410.0,
      "level": "info",
      "message": "Writing firmware blocks"
    },
    {
      "timestamp": 1704110425.0,
      "level": "info",
      "message": "Verifying written data"
    },
    {
      "timestamp": 1704110428.5,
      "level": "info",
      "message": "Flash operation completed successfully"
    }
  ]
}
```

**Error Responses:**
- `404`: Flash operation not found

### DELETE /flash/{flash_id}
Cancel an ongoing flash operation.

**Parameters:**
- `flash_id` (path): Flash operation identifier

**Response (200):**
```json
{
  "flash_id": "flash_550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": 1704110415.0
}
```

**Error Responses:**
- `404`: Flash operation not found
- `409`: Flash operation cannot be cancelled (already completed/failed)

### POST /flash/upload
Upload a firmware file for flashing operations.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: Firmware binary/hex file (required)
- `filename`: Optional custom filename
- `description`: Optional description

**Response (201):**
```json
{
  "file_id": "fw_550e8400-e29b-41d4-a716-446655440001",
  "filename": "throttle_control_v1.2.hex",
  "size_bytes": 32768,
  "md5_checksum": "a1b2c3d4e5f6...",
  "uploaded_at": 1704110400.0,
  "description": "Throttle control firmware v1.2"
}
```

**Error Responses:**
- `400`: No file provided or invalid file format
- `413`: File too large
- `500`: File upload failed

### GET /flash/files
List uploaded firmware files.

**Response (200):**
```json
{
  "files": [
    {
      "file_id": "fw_550e8400-e29b-41d4-a716-446655440001",
      "filename": "throttle_control_v1.2.hex",
      "size_bytes": 32768,
      "md5_checksum": "a1b2c3d4e5f6...",
      "uploaded_at": 1704110400.0,
      "description": "Throttle control firmware v1.2"
    }
  ]
}
```

### DELETE /flash/files/{file_id}
Delete an uploaded firmware file.

**Parameters:**
- `file_id` (path): Firmware file identifier

**Response (200):**
```json
{
  "file_id": "fw_550e8400-e29b-41d4-a716-446655440001",
  "status": "deleted"
}
```

**Error Responses:**
- `404`: Firmware file not found
- `409`: File is currently being used in a flash operation

## 8. Error Response Format

All API errors return a standardized JSON response:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
      "field": "specific_field_name",
      "provided_value": "invalid_value",
      "expected_range": "[0, 100]"
    },
    "timestamp": 1704110400.0
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONFIG_INVALID` | 400 | Invalid configuration |
| `CHANNEL_NOT_FOUND` | 404 | Channel does not exist |
| `TEST_RUN_NOT_FOUND` | 404 | Test run does not exist |
| `TEST_NOT_COMPLETED` | 409 | Test run not finished yet |
| `FLASH_OPERATION_NOT_FOUND` | 404 | Flash operation does not exist |
| `FLASH_ALREADY_RUNNING` | 409 | Another flash operation is already in progress |
| `FIRMWARE_FILE_NOT_FOUND` | 404 | Firmware file not found |
| `FLASH_VERIFICATION_FAILED` | 500 | Firmware verification after flash failed |
| `FLASH_TIMEOUT` | 408 | Flash operation timed out |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## 9. WebSocket Streaming

### Channel Value Streaming
**Endpoint:** `ws://localhost:8080/api/v1/channels/{channel_id}/stream`

**Message Format:**
```json
{
  "type": "channel_update",
  "channel_id": "throttle_position",
  "value": 75.5,
  "timestamp": 1704110400.0,
  "quality": "good"
}
```

### CAN Bus Message Streaming
**Endpoint:** `ws://localhost:8080/api/v1/buses/{bus_id}/can/stream`

**Message Format:**
```json
{
  "type": "can_message",
  "bus_id": "can_bus",
  "message_id": 256,
  "data": [0, 0, 78, 32],
  "timestamp": 1704110400.0,
  "direction": "rx"
}
```

## 10. Rate Limiting

- **Channel Reads/Writes:** No explicit rate limiting (hardware-dependent)
- **Test Runs:** Maximum 5 concurrent test runs
- **Flash Operations:** Maximum 1 concurrent flash operation per target device
- **Firmware Uploads:** Maximum 10MB per file, 100MB total storage
- **API Requests:** No rate limiting for local deployment

## 11. OpenAPI Documentation

Complete API documentation is automatically available at:
- **Swagger UI:** `http://localhost:8080/docs`
- **ReDoc:** `http://localhost:8080/redoc`
- **OpenAPI JSON:** `http://localhost:8080/openapi.json`

**Response:**
```json
{
  "supported_io_types": ["digital", "analog", "can", "pwm"],
  "max_concurrent_scenarios": 1,
  "supported_protocols": ["can2.0a", "can2.0b"],
  "config_formats": ["yaml", "json"],
  "real_time_streaming": true,
  "async_execution": true
}
```

## 2. Instrument Management

### GET /instruments
List all configured instruments.

**Response:**
```json
{
  "instruments": [
    {
      "id": "throttle_sensor",
      "plugin": "analog_driver",
      "type": "adc",
      "status": "initialized",
      "capabilities": {
        "resolution": 12,
        "sample_rate": 1000,
        "voltage_range": [0, 5]
      }
    }
  ]
}
```

### GET /instruments/{instrumentId}
Get instrument details and current status.

**Response:**
```json
{
  "id": "throttle_sensor",
  "plugin": "analog_driver",
  "type": "adc",
  "status": "initialized",
  "config": {
    "channel": 0,
    "calibration": {
      "offset": 0.0,
      "scale": 1.0
    }
  },
  "last_reading": {
    "value": 2.5,
    "timestamp": "2024-01-01T10:00:00Z"
  }
}
```

## 3. Channel Control

### GET /channels
List all configured channels.

**Response:**
```json
{
  "channels": [
    {
      "id": "throttle_position",
      "instrument": "throttle_sensor",
      "type": "analog_input",
      "logical_name": "THROTTLE_POS",
      "units": "%",
      "status": "active"
    }
  ]
}
```

### GET /channels/{channelId}
Read channel value.

**Response:**
```json
{
  "channel_id": "throttle_position",
  "value": 75.5,
  "timestamp": "2024-01-01T10:00:00Z",
  "quality": "good",
  "units": "%"
}
```

### PUT /channels/{channelId}
Set channel value (for output channels).

**Request:**
```json
{
  "value": 50.0
}
```

**Response:**
```json
{
  "channel_id": "throttle_position",
  "value": 50.0,
  "timestamp": "2024-01-01T10:00:00Z",
  "status": "ok"
}
```

### WebSocket /channels/{channelId}/stream
Subscribe to channel value changes.

**Message Format:**
```json
{
  "type": "channel_update",
  "channel_id": "throttle_position",
  "value": 75.5,
  "timestamp": "2024-01-01T10:00:00Z"
}
```

## 4. DUT Profile Management

### GET /dutProfiles
List available DUT profiles.

**Response:**
```json
{
  "profiles": [
    {
      "id": "arduino_ecu",
      "name": "Arduino Throttle ECU",
      "description": "Simple ECU with analog throttle input",
      "channels": ["throttle_position", "engine_speed_output"],
      "buses": ["can_bus"]
    }
  ]
}
```

### GET /dutProfiles/{profileId}
Get DUT profile details.

**Response:**
```json
{
  "id": "arduino_ecu",
  "name": "Arduino Throttle ECU",
  "description": "Simple ECU with analog throttle input and PWM engine speed output",
  "channels": [
    {
      "id": "throttle_position",
      "required": true,
      "direction": "input"
    }
  ],
  "buses": ["can_bus"],
  "calibration": {
    "throttle_deadband": 5
  }
}
```

### PUT /dutProfiles/{profileId}/activate
Activate a DUT profile.

**Response:**
```json
{
  "profile_id": "arduino_ecu",
  "status": "activated",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

## 5. Bus Control

### GET /buses
List configured buses.

**Response:**
```json
{
  "buses": [
    {
      "id": "can_bus",
      "type": "can",
      "status": "connected",
      "bitrate": 500000,
      "statistics": {
        "messages_tx": 150,
        "messages_rx": 200,
        "errors": 0
      }
    }
  ]
}
```

### POST /buses/{busId}/can/transmit
Transmit CAN message.

**Request:**
```json
{
  "message_id": 256,
  "data": [0x12, 0x34, 0x56, 0x78],
  "extended_id": false
}
```

**Response:**
```json
{
  "bus_id": "can_bus",
  "message_id": 256,
  "timestamp": "2024-01-01T10:00:00Z",
  "status": "transmitted"
}
```

### WebSocket /buses/{busId}/can/stream
Stream received CAN messages.

**Message Format:**
```json
{
  "type": "can_message",
  "bus_id": "can_bus",
  "message_id": 256,
  "data": [0x12, 0x34, 0x56, 0x78],
  "timestamp": "2024-01-01T10:00:00Z",
  "direction": "rx"
}
```

## 6. Scenario Management

### GET /scenarios
List available test scenarios.

**Response:**
```json
{
  "scenarios": [
    {
      "id": "throttle_response_test",
      "name": "Throttle Response Validation",
      "description": "Test ECU throttle to engine speed response",
      "estimated_duration": "30s",
      "tags": ["throttle", "response"]
    }
  ]
}
```

### GET /scenarios/{scenarioId}
Get scenario details.

**Response:**
```json
{
  "id": "throttle_response_test",
  "name": "Throttle Response Validation",
  "description": "Test ECU throttle to engine speed response",
  "steps": [
    {
      "id": "set_throttle",
      "type": "set_channel",
      "channel": "throttle_position",
      "value": 50
    }
  ],
  "parameters": {
    "throttle_positions": [0, 25, 50, 75, 100]
  }
}
```

### POST /scenarios/{scenarioId}/validate
Validate scenario configuration.

**Response:**
```json
{
  "scenario_id": "throttle_response_test",
  "valid": true,
  "warnings": [],
  "errors": []
}
```

## 7. Test Execution

### POST /runs
Start a new test run.

**Request:**
```json
{
  "scenario_id": "throttle_response_test",
  "parameters": {
    "throttle_positions": [0, 25, 50, 75, 100]
  },
  "async": true
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": "throttle_response_test",
  "status": "queued",
  "created_at": "2024-01-01T10:00:00Z"
}
```

### GET /runs/{runId}
Get test run status and results.

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": {
    "current_step": 5,
    "total_steps": 25,
    "percentage": 20
  },
  "current_readings": {
    "throttle_position": 50,
    "engine_speed_output": 5.2
  }
}
```

### DELETE /runs/{runId}
Abort a running test.

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "aborted",
  "aborted_at": "2024-01-01T10:00:15Z"
}
```

### GET /runs/{runId}/results
Get completed test results.

**Response:** (See DataModels.md for full schema)

### GET /runs/{runId}/steps/{stepId}
Get specific step result.

**Response:**
```json
{
  "step_id": "set_throttle",
  "status": "passed",
  "start_time": "2024-01-01T10:00:05Z",
  "end_time": "2024-01-01T10:00:05Z",
  "readings": {
    "throttle_position": 50
  },
  "assertions": [
    {
      "condition": "value > 45",
      "result": true
    }
  ]
}
```

## 8. Artifact Management

### GET /artifacts/runs/{runId}
List artifacts for a test run.

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "artifacts": [
    {
      "type": "csv",
      "filename": "throttle_response.csv",
      "size_bytes": 2048,
      "created_at": "2024-01-01T10:00:30Z",
      "url": "/artifacts/runs/550e8400-e29b-41d4-a716-446655440000/throttle_response.csv"
    }
  ]
}
```

### GET /artifacts/runs/{runId}/{filename}
Download artifact file.

**Response:** Binary file content with appropriate Content-Type header.

## 9. Real-time Streaming

### WebSocket /stream
Main streaming endpoint for real-time updates.

**Supported Message Types:**
- `run_status`: Test execution progress
- `channel_update`: Channel value changes
- `can_message`: CAN bus traffic
- `log_entry`: Test log messages
- `artifact_ready`: New artifact available

**Example Messages:**
```json
{
  "type": "run_status",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 20
}

{
  "type": "channel_update",
  "channel_id": "throttle_position",
  "value": 75.5,
  "timestamp": "2024-01-01T10:00:00Z"
}
```
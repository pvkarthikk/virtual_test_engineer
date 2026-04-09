# 06_ErrorHandling.md - Error Handling and Recovery

## Overview

The Virtual Test Engineer implements comprehensive error handling and recovery mechanisms to ensure reliable test execution and graceful degradation under failure conditions. This document outlines the error handling strategies, recovery procedures, and logging mechanisms.

## Error Classification

### Error Types

1. **Configuration Errors**
   - Invalid YAML syntax
   - Missing required fields
   - Incompatible parameter values
   - Plugin configuration conflicts

2. **Plugin Errors**
   - Hardware initialization failures
   - Communication timeouts
   - Resource allocation failures
   - Unsupported operations

3. **Channel/Bus Errors**
   - I/O operation failures
   - Out-of-range values
   - Connection losses
   - Protocol violations

4. **Test Execution Errors**
   - Assertion failures
   - Timeout conditions
   - Resource exhaustion
   - Unexpected exceptions

5. **System Errors**
   - Memory exhaustion
   - Disk space issues
   - Network failures
   - Operating system errors

## Error Response Structure

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
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Codes

| Code | Category | Description |
|------|----------|-------------|
| `CONFIG_INVALID` | Configuration | Invalid configuration file or parameters |
| `CONFIG_MISSING` | Configuration | Required configuration field is missing |
| `PLUGIN_INIT_FAILED` | Plugin | Plugin initialization failed |
| `PLUGIN_NOT_FOUND` | Plugin | Requested plugin not found or not loaded |
| `CHANNEL_NOT_FOUND` | Channel | Requested channel does not exist |
| `CHANNEL_BUSY` | Channel | Channel is currently in use by another operation |
| `CHANNEL_RANGE_ERROR` | Channel | Channel value outside allowed range |
| `BUS_NOT_FOUND` | Bus | Requested bus does not exist |
| `BUS_DISCONNECTED` | Bus | Bus connection lost |
| `TEST_NOT_FOUND` | Test | Requested test scenario not found |
| `TEST_TIMEOUT` | Test | Test execution exceeded timeout |
| `ASSERTION_FAILED` | Test | Test assertion condition failed |
| `SYSTEM_RESOURCE` | System | System resource exhaustion |
| `INTERNAL_ERROR` | System | Unexpected internal error |

## Configuration Validation

### Schema Validation

Configuration files are validated against JSON schemas:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional

class ChannelConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    instrument: str = Field(..., min_length=1)
    scaling: Optional[Dict[str, Any]] = None

    @validator('id')
    def validate_channel_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Channel ID must be alphanumeric with underscores/hyphens')
        return v

class PluginConfig(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)

class TestBenchConfig(BaseModel):
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    name: str = Field(..., min_length=1, max_length=100)
    plugins: List[PluginConfig] = Field(default_factory=list)
    instruments: List[Dict[str, Any]] = Field(default_factory=list)
    channels: List[ChannelConfig] = Field(default_factory=list)
    buses: List[Dict[str, Any]] = Field(default_factory=list)
    dut_profiles: List[Dict[str, Any]] = Field(default_factory=list)
```

### Validation API

```bash
# Validate configuration
curl -X POST http://localhost:8080/api/v1/config/validate \
  -H "Content-Type: application/json" \
  -d @testbench_config.yaml

# Response for valid config
{
  "valid": true,
  "warnings": []
}

# Response for invalid config
{
  "valid": false,
  "errors": [
    {
      "field": "channels[0].scaling.output_range",
      "message": "Output range must be a list of two numbers",
      "code": "TYPE_ERROR"
    }
  ],
  "warnings": [
    {
      "field": "plugins[1].config",
      "message": "Plugin config missing optional field 'timeout'"
    }
  ]
}
```

## Plugin Error Handling

### Initialization Failures

```python
class PluginInitializationError(Exception):
    """Raised when plugin initialization fails."""

    def __init__(self, plugin_name: str, reason: str, details: Dict[str, Any] = None):
        self.plugin_name = plugin_name
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Plugin '{plugin_name}' initialization failed: {reason}")

# Usage in plugin manager
try:
    success = plugin.initialize(config)
    if not success:
        raise PluginInitializationError(
            plugin_name=plugin_name,
            reason="Plugin returned False from initialize()",
            details={"config": config}
        )
except Exception as e:
    logger.error(f"Plugin {plugin_name} failed to initialize: {e}")
    raise PluginInitializationError(
        plugin_name=plugin_name,
        reason=str(e),
        details={"exception_type": type(e).__name__}
    )
```

### Runtime Error Recovery

```python
class ChannelOperationError(Exception):
    """Raised when channel operations fail."""

    def __init__(self, channel_id: str, operation: str, reason: str):
        self.channel_id = channel_id
        self.operation = operation
        self.reason = reason
        super().__init__(f"Channel '{channel_id}' {operation} failed: {reason}")

async def safe_channel_read(channel: Channel, retries: int = 3) -> Any:
    """Safely read from a channel with retry logic."""

    for attempt in range(retries):
        try:
            value = await channel.read()
            return value
        except Exception as e:
            if attempt == retries - 1:
                raise ChannelOperationError(
                    channel_id=channel.channel_id,
                    operation="read",
                    reason=str(e)
                )
            await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

    raise ChannelOperationError(
        channel_id=channel.channel_id,
        operation="read",
        reason="Max retries exceeded"
    )
```

## Test Execution Error Handling

### Test Run States

```python
from enum import Enum

class TestRunStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TestRun:
    def __init__(self, scenario_id: str):
        self.run_id = str(uuid.uuid4())
        self.scenario_id = scenario_id
        self.status = TestRunStatus.QUEUED
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.errors: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {}

    def add_error(self, step_id: str, error: Exception, context: Dict[str, Any] = None):
        """Add an error to the test run."""
        self.errors.append({
            "step_id": step_id,
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        })

    def fail(self, reason: str):
        """Mark the test run as failed."""
        self.status = TestRunStatus.FAILED
        self.end_time = datetime.utcnow()
        self.add_error("system", Exception(reason))
```

### Assertion Failures

```python
class AssertionError(Exception):
    """Raised when test assertions fail."""

    def __init__(self, condition: str, actual_value: Any, expected: str, message: str = None):
        self.condition = condition
        self.actual_value = actual_value
        self.expected = expected
        self.message = message or f"Assertion failed: {condition}"
        super().__init__(self.message)

# Usage in test engine
async def execute_assertion(self, assertion_config: Dict[str, Any]) -> None:
    """Execute an assertion step."""

    condition = assertion_config.get('condition')
    message = assertion_config.get('message', f"Assertion failed: {condition}")

    try:
        # Evaluate the condition (simplified - would use a proper expression evaluator)
        if not self._evaluate_condition(condition):
            raise AssertionError(
                condition=condition,
                actual_value=self._get_variable_values(condition),
                expected=condition,
                message=message
            )
    except AssertionError:
        raise
    except Exception as e:
        raise AssertionError(
            condition=condition,
            actual_value="evaluation_error",
            expected=condition,
            message=f"Assertion evaluation failed: {e}"
        )
```

### Timeout Handling

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def test_timeout(timeout_seconds: float):
    """Context manager for test step timeouts."""

    try:
        yield await asyncio.wait_for(asyncio.sleep(0), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TestTimeoutError(f"Step timed out after {timeout_seconds} seconds")

async def execute_step_with_timeout(self, step: Dict[str, Any], timeout: float = 30.0):
    """Execute a test step with timeout protection."""

    step_id = step.get('id', 'unknown')
    step_type = step.get('type')

    try:
        async with test_timeout(timeout):
            if step_type == 'set_channel':
                await self._execute_set_channel(step)
            elif step_type == 'read_channel':
                await self._execute_read_channel(step)
            elif step_type == 'delay':
                await self._execute_delay(step)
            elif step_type == 'assert':
                await self._execute_assertion(step)
            else:
                raise ValueError(f"Unknown step type: {step_type}")

    except asyncio.TimeoutError:
        self.current_run.add_error(
            step_id=step_id,
            error=TestTimeoutError(f"Step timed out after {timeout} seconds"),
            context={"step": step, "timeout": timeout}
        )
        raise
    except Exception as e:
        self.current_run.add_error(
            step_id=step_id,
            error=e,
            context={"step": step}
        )
        raise
```

## Recovery Strategies

### Automatic Recovery

1. **Channel Recovery**
   - Retry failed operations with exponential backoff
   - Reinitialize channels on persistent failures
   - Switch to backup channels if available

2. **Bus Recovery**
   - Reconnect to buses on connection loss
   - Flush pending messages on recovery
   - Validate bus state after reconnection

3. **Plugin Recovery**
   - Restart plugins on failure
   - Reload plugin configurations
   - Switch to alternative plugins

### Manual Recovery

```bash
# Restart a failed plugin
curl -X POST http://localhost:8080/api/v1/plugins/gpio_plugin/restart

# Reset a channel
curl -X POST http://localhost:8080/api/v1/channels/throttle_position/reset

# Reconnect a bus
curl -X POST http://localhost:8080/api/v1/buses/can_bus/reconnect

# Cancel a running test
curl -X POST http://localhost:8080/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/cancel
```

## Logging and Monitoring

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information about system operation
- **WARNING**: Potential issues that don't stop operation
- **ERROR**: Errors that affect specific operations
- **CRITICAL**: System-wide failures

### Structured Logging

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_error(self, error_code: str, message: str, **kwargs):
        """Log structured error information."""

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "error_code": error_code,
            "message": message,
            **kwargs
        }

        self.logger.error(json.dumps(log_data))

# Usage
logger = StructuredLogger("test_engine")

try:
    await channel.write(value)
except Exception as e:
    logger.log_error(
        error_code="CHANNEL_WRITE_FAILED",
        message=f"Failed to write to channel {channel.channel_id}",
        channel_id=channel.channel_id,
        value=value,
        exception=str(e)
    )
```

### Health Monitoring

```bash
# Get system health status
curl http://localhost:8080/api/v1/health

# Response
{
  "status": "degraded",
  "components": {
    "plugins": {
      "gpio_plugin": "healthy",
      "can_plugin": "unhealthy",
      "analog_plugin": "healthy"
    },
    "channels": {
      "throttle_position": "healthy",
      "engine_speed": "healthy",
      "eco_mode": "unhealthy"
    },
    "buses": {
      "can_bus": "unhealthy"
    }
  },
  "last_check": "2024-01-15T10:30:00Z"
}
```

## Error Recovery Procedures

### Configuration Errors

1. Validate configuration syntax
2. Check for missing required fields
3. Verify parameter ranges and types
4. Test plugin compatibility
5. Validate channel and bus references

### Runtime Errors

1. Log error details with context
2. Attempt automatic recovery (retry, reconnect)
3. Notify monitoring systems
4. Degrade gracefully if recovery fails
5. Provide detailed error information to clients

### Test Failures

1. Capture failure context and state
2. Log all relevant data and conditions
3. Clean up test resources
4. Generate failure reports
5. Allow test continuation or termination based on configuration

## Best Practices

### Error Prevention

- Validate all inputs at API boundaries
- Use type hints and runtime type checking
- Implement comprehensive unit tests
- Use configuration validation before runtime
- Implement health checks and monitoring

### Error Communication

- Provide clear, actionable error messages
- Include context and suggestions for resolution
- Use consistent error codes and formats
- Log errors with sufficient detail for debugging
- Avoid exposing internal system details

### Recovery Design

- Implement graceful degradation
- Use circuit breaker patterns for external dependencies
- Provide manual recovery options
- Design for eventual consistency
- Test recovery procedures regularly
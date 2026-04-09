# Virtual Test Engineer Python Client

A comprehensive Python client library for interacting with the Virtual Test Engineer REST API, enabling automated testing of embedded systems and ECUs.

## Features

- **Async/Await Support**: Full async support for high-performance testing
- **Channel Operations**: Read/write analog and digital channels
- **Test Execution**: Start, monitor, and control automated test runs
- **Firmware Flashing**: Upload and flash firmware to target devices
- **Configuration Management**: Persistent client configuration
- **Error Handling**: Robust error handling and retry logic

## Installation

### From Source

```bash
cd client
pip install -e .
```

### Requirements

- Python 3.8+
- aiohttp
- pydantic

## Quick Start

```python
import asyncio
from vte_client import VirtualTestEngineerClient

async def main():
    async with VirtualTestEngineerClient("http://localhost:8080") as client:
        # Health check
        health = await client.health_check()
        print(f"Server status: {health['status']}")

        # List channels
        channels = await client.list_channels()
        print(f"Found {len(channels)} channels")

        # Read a channel
        if channels:
            channel_info = await client.read_channel(channels[0].id)
            print(f"Channel {channel_info.id}: {channel_info.value}")

asyncio.run(main())
```

## Configuration

Create a configuration file at `~/.vte_client/config.json`:

```json
{
  "server_url": "http://localhost:8080",
  "timeout": 30.0,
  "retry_attempts": 3,
  "log_level": "INFO",
  "default_test_timeout": 300.0,
  "default_flash_timeout": 300.0
}
```

Or configure programmatically:

```python
from config_manager import ConfigManager

config_manager = ConfigManager()
config = config_manager.load_config()
config.server_url = "http://your-server:8080"
config_manager.save_config()
```

## API Reference

### Client Class

#### `VirtualTestEngineerClient(base_url="http://localhost:8080")`

Main client class for interacting with the Virtual Test Engineer API.

#### Health & Status Methods

- `health_check()` - Check system health
- `get_bench_info()` - Get test bench information
- `get_capabilities()` - Get system capabilities

#### Channel Methods

- `list_channels()` - List all available channels
- `read_channel(channel_id)` - Read a specific channel
- `write_channel(channel_id, value)` - Write to a channel
- `read_multiple_channels(channel_ids)` - Read multiple channels

#### Test Methods

- `start_test(test_config)` - Start a test run
- `get_test_status(test_id)` - Get test status
- `stop_test(test_id)` - Stop a test run
- `list_tests()` - List all test runs

#### Flashing Methods

- `list_firmware_files()` - List uploaded firmware files
- `upload_firmware(file_path, description, version)` - Upload firmware
- `start_flash(file_id, protocol, target_device, parameters)` - Start flash operation
- `get_flash_status(flash_id)` - Get flash status
- `cancel_flash(flash_id)` - Cancel flash operation

#### Utility Methods

- `wait_for_flash_completion(flash_id, timeout, poll_interval)` - Wait for flash completion
- `wait_for_test_completion(test_id, timeout, poll_interval)` - Wait for test completion

## Example Applications

### Channel Monitoring

```python
async def monitor_channels():
    async with VirtualTestEngineerClient() as client:
        channels = await client.list_channels()

        while True:
            readings = await client.read_multiple_channels([ch.id for ch in channels])
            for reading in readings:
                print(f"{reading.id}: {reading.value} {reading.units}")
            await asyncio.sleep(1.0)
```

### Automated Test

```python
async def run_ecu_test():
    test_config = {
        "name": "ECU Functionality Test",
        "dut_profile": "arduino_ecu",
        "steps": [
            {
                "id": "set_throttle",
                "type": "channel_write",
                "parameters": {"channel_id": "throttle_position", "value": 75.0}
            },
            {
                "id": "read_response",
                "type": "channel_read",
                "parameters": {"channel_id": "engine_speed"}
            },
            {
                "id": "validate",
                "type": "assert",
                "parameters": {
                    "condition": "engine_speed > 2000",
                    "message": "Engine speed should exceed 2000 RPM"
                }
            }
        ]
    }

    async with VirtualTestEngineerClient() as client:
        test_id = await client.start_test(test_config)
        result = await client.wait_for_test_completion(test_id)
        print(f"Test result: {result['status']}")
```

### Firmware Flashing

```python
async def flash_firmware():
    async with VirtualTestEngineerClient() as client:
        # Upload firmware
        upload = await client.upload_firmware(
            "firmware.hex",
            description="Latest ECU firmware",
            version="2.1.0"
        )

        # Start flash operation
        flash_id = await client.start_flash(
            upload['file_id'],
            "avrdude",
            "atmega328p",
            {"port": "/dev/ttyUSB0"}
        )

        # Wait for completion
        result = await client.wait_for_flash_completion(flash_id)
        print(f"Flash result: {result['status']}")
```

## Command Line Usage

The client includes a command-line example application:

```bash
# Run all tests
python example_client.py

# Test only channels
python example_client.py --test channels

# Use different server
python example_client.py --server http://test-server:8080
```

## Error Handling

The client includes comprehensive error handling:

```python
try:
    async with VirtualTestEngineerClient() as client:
        result = await client.read_channel("nonexistent_channel")
except Exception as e:
    print(f"Error: {e}")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details
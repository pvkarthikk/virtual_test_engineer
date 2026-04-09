# Virtual Test Engineer - User Guide

## Overview

The Virtual Test Engineer is a modular test automation framework designed for testing embedded systems and ECUs (Electronic Control Units). This guide provides detailed instructions for extending the system by adding new simulators, DUT (Device Under Test) profiles, and creating client applications.

## Table of Contents

1. [Adding a New Simulator](#adding-a-new-simulator)
2. [Adding a New DUT Profile](#adding-a-new-dut-profile)
3. [Creating a Sample Client](#creating-a-sample-client)
4. [Configuration Reference](#configuration-reference)
5. [API Reference](#api-reference)

## Adding a New Simulator

Simulators in the Virtual Test Engineer are implemented as plugins that provide hardware interfaces such as GPIO, analog I/O, PWM, CAN bus, etc. Each plugin consists of a driver implementation and a manifest file.

### Step 1: Create Plugin Directory Structure

Create a new directory under `drivers/plugins/` for your simulator:

```bash
mkdir -p drivers/plugins/my_custom_plugin
cd drivers/plugins/my_custom_plugin
```

### Step 2: Create Plugin Manifest

Create `plugin.json` with the plugin metadata:

```json
{
  "name": "my_custom_plugin",
  "version": "1.0.0",
  "description": "Custom simulator plugin for specialized hardware",
  "author": "Your Name",
  "type": "device_driver",
  "supported_interfaces": ["gpio", "analog", "pwm"],
  "dependencies": {
    "python": ">=3.8",
    "packages": ["numpy", "scipy"]
  },
  "entry_point": "my_custom_driver.py",
  "capabilities": {
    "digital_inputs": 16,
    "digital_outputs": 16,
    "analog_inputs": 8,
    "analog_outputs": 4,
    "pwm_channels": 6,
    "supported_protocols": ["i2c", "spi"]
  }
}
```

### Step 3: Implement the Plugin Driver

Create the main driver file (e.g., `my_custom_driver.py`):

```python
#!/usr/bin/env python3
"""
My Custom Plugin - Hardware simulator implementation
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional, List

from ...core.types import (
    DevicePlugin, Channel, ChannelConfig, ChannelType, ChannelValue,
    DeviceCapabilities, PluginConfig, ValidationResult, BusPlugin, BusConfig
)


class CustomChannel(Channel):
    """Custom channel implementation"""

    def __init__(self, channel_id: str, config: ChannelConfig):
        super().__init__(channel_id, config)
        self.simulated_value = 0.0
        self.last_update = time.time()

    async def read(self) -> ChannelValue:
        """Read channel value"""
        # Simulate hardware reading
        if self.config.type == ChannelType.ANALOG_INPUT:
            # Generate simulated analog reading
            self.simulated_value = random.uniform(0.0, 5.0)
        elif self.config.type == ChannelType.DIGITAL_INPUT:
            # Generate simulated digital reading
            self.simulated_value = random.choice([0, 1])

        return ChannelValue(
            channel_id=self.channel_id,
            value=self.simulated_value,
            timestamp=time.time(),
            units=self.config.scaling.get('units') if self.config.scaling else None
        )

    async def write(self, value: Union[int, float, bool]) -> None:
        """Write channel value"""
        self.simulated_value = float(value)
        self.last_update = time.time()


class CustomBusPlugin(BusPlugin):
    """Custom bus plugin for CAN, serial, etc."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.receive_callback = None

    async def initialize(self, config: BusConfig) -> None:
        """Initialize bus plugin"""
        print(f"Initializing {config.type} bus: {config.id}")
        # Initialize hardware or simulator

    async def shutdown(self) -> None:
        """Shutdown bus plugin"""
        print("Shutting down custom bus plugin")

    async def transmit(self, message: CanMessage) -> None:
        """Transmit a message"""
        print(f"Transmitting message: {message.message_id}")
        # Simulate transmission
        self.messages.append({
            'id': message.message_id,
            'data': message.data,
            'timestamp': time.time()
        })

    def set_receive_callback(self, callback: callable) -> None:
        """Set callback for received messages"""
        self.receive_callback = callback


class MyCustomPlugin(DevicePlugin):
    """Main plugin class"""

    def __init__(self):
        self.channels: Dict[str, CustomChannel] = {}
        self.bus_plugins: Dict[str, CustomBusPlugin] = {}
        self.initialized = False

    async def initialize(self, config: PluginConfig) -> None:
        """Initialize the plugin"""
        print(f"Initializing {config.name} plugin")

        # Parse configuration
        self.adc_channels = config.config.get('adc_channels', [])
        self.dac_channels = config.config.get('dac_channels', [])
        self.gpio_pins = config.config.get('gpio_pins', [])

        self.initialized = True
        print(f"Plugin {config.name} initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the plugin"""
        print("Shutting down custom plugin")
        self.initialized = False

    def get_capabilities(self) -> DeviceCapabilities:
        """Get plugin capabilities"""
        return DeviceCapabilities(
            digital_inputs=len(self.gpio_pins),
            digital_outputs=len(self.gpio_pins),
            analog_inputs=len(self.adc_channels),
            analog_outputs=len(self.dac_channels),
            pwm_channels=6,  # Fixed number for this plugin
            supported_protocols=["i2c", "spi"]
        )

    def validate_config(self, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        errors = []
        warnings = []

        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return ValidationResult(valid=False, errors=errors)

        # Validate ADC channels
        adc_channels = config.get('adc_channels', [])
        if not isinstance(adc_channels, list):
            errors.append("adc_channels must be a list")
        else:
            for ch in adc_channels:
                if not isinstance(ch, int) or ch < 0:
                    errors.append(f"Invalid ADC channel: {ch}")

        # Validate GPIO pins
        gpio_pins = config.get('gpio_pins', [])
        if not isinstance(gpio_pins, list):
            errors.append("gpio_pins must be a list")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def create_channel(self, channel_id: str, config: ChannelConfig) -> Channel:
        """Create a channel instance"""
        channel = CustomChannel(channel_id, config)
        self.channels[channel_id] = channel
        return channel

    async def destroy_channel(self, channel_id: str) -> None:
        """Destroy a channel instance"""
        if channel_id in self.channels:
            del self.channels[channel_id]

    async def create_bus_plugin(self, bus_id: str, config: BusConfig) -> BusPlugin:
        """Create a bus plugin instance"""
        bus_plugin = CustomBusPlugin()
        await bus_plugin.initialize(config)
        self.bus_plugins[bus_id] = bus_plugin
        return bus_plugin

    async def destroy_bus_plugin(self, bus_id: str) -> None:
        """Destroy a bus plugin instance"""
        if bus_id in self.bus_plugins:
            await self.bus_plugins[bus_id].shutdown()
            del self.bus_plugins[bus_id]


# Factory function for plugin instantiation
def create_plugin():
    """Create plugin instance"""
    return MyCustomPlugin()
```

### Step 4: Update Configuration

Add the new plugin to your `config/testbench.yaml`:

```yaml
plugins:
  - name: "my_custom_plugin"
    type: "device_driver"
    config:
      adc_channels: [0, 1, 2, 3]
      dac_channels: [0, 1]
      gpio_pins: [2, 3, 4, 5, 6, 7, 8, 9]
```

### Step 5: Test the Plugin

Create a test script to verify your plugin:

```python
#!/usr/bin/env python3
"""
Test script for custom plugin
"""

import asyncio
from src.core.plugin_manager import PluginManager
from src.core.types import PluginConfig


async def test_plugin():
    """Test the custom plugin"""
    manager = PluginManager()

    # Discover plugins
    plugins = await manager.discover_plugins()
    print(f"Discovered plugins: {plugins}")

    # Load and test your plugin
    config = PluginConfig(
        name="my_custom_plugin",
        type="device_driver",
        config={
            "adc_channels": [0, 1],
            "gpio_pins": [2, 3, 4]
        }
    )

    plugin = await manager.load_plugin("my_custom_plugin", config)
    if plugin:
        print("✅ Plugin loaded successfully")

        # Test capabilities
        caps = plugin.get_capabilities()
        print(f"Capabilities: {caps}")

        # Test configuration validation
        result = plugin.validate_config(config.config)
        print(f"Config validation: {result.valid}")
        if result.errors:
            print(f"Errors: {result.errors}")

        await plugin.shutdown()
    else:
        print("❌ Failed to load plugin")


if __name__ == "__main__":
    asyncio.run(test_plugin())
```

## Adding a New DUT Profile

DUT (Device Under Test) profiles define the interface specifications for different types of devices you want to test. They specify which channels and buses are required for testing a particular device.

### Step 1: Understand DUT Profile Structure

A DUT profile consists of:
- **ID**: Unique identifier for the profile
- **Name**: Human-readable name
- **Description**: Detailed description
- **Channels**: Required channels with direction (input/output)
- **Buses**: Required communication buses

### Step 2: Add DUT Profile to Configuration

Edit `config/testbench.yaml` and add a new DUT profile:

```yaml
dut_profiles:
  - id: "arduino_ecu"
    name: "Arduino Throttle ECU"
    description: "Simple ECU with analog throttle input and PWM engine speed output"
    channels:
      - id: "throttle_position"
        required: true
        direction: "input"
      - id: "engine_speed"
        required: true
        direction: "output"
      - id: "eco_mode"
        required: false
        direction: "input"
    buses:
      - can_bus

  - id: "advanced_ecu"
    name: "Advanced Automotive ECU"
    description: "Complex ECU with multiple sensors and actuators"
    channels:
      - id: "throttle_position"
        required: true
        direction: "input"
      - id: "engine_speed"
        required: true
        direction: "output"
      - id: "vehicle_speed"
        required: true
        direction: "input"
      - id: "brake_pressure"
        required: true
        direction: "input"
      - id: "fuel_injection"
        required: true
        direction: "output"
      - id: "ignition_coil"
        required: true
        direction: "output"
      - id: "diagnostic_led"
        required: false
        direction: "output"
    buses:
      - can_bus
      - diagnostic_bus
```

### Step 3: Ensure Required Channels Exist

Make sure all channels referenced in the DUT profile are defined in the configuration:

```yaml
channels:
  - id: "throttle_position"
    instrument: "throttle_sensor"
    logical_name: "THROTTLE_POS"
    scaling:
      input_range: [0.0, 5.0]
      output_range: [0, 100]
      units: "%"

  - id: "engine_speed"
    instrument: "engine_speed_output"
    config:
      frequency: 1000
      duty_cycle_range: [0, 100]
    scaling:
      output_range: [0, 8000]
      units: "rpm"

  - id: "vehicle_speed"
    instrument: "vehicle_speed_sensor"
    logical_name: "VEHICLE_SPEED"
    scaling:
      input_range: [0.0, 12.0]
      output_range: [0, 200]
      units: "km/h"

  - id: "brake_pressure"
    instrument: "brake_sensor"
    logical_name: "BRAKE_PRESSURE"
    scaling:
      input_range: [0.5, 4.5]
      output_range: [0, 100]
      units: "bar"

  - id: "fuel_injection"
    instrument: "fuel_injector"
    config:
      frequency: 50
      duty_cycle_range: [0, 100]

  - id: "ignition_coil"
    instrument: "ignition_driver"
    config:
      frequency: 100
      duty_cycle_range: [0, 100]

  - id: "diagnostic_led"
    instrument: "status_led"
    active_high: true
```

### Step 4: Add Required Buses

Ensure all buses referenced in the DUT profile are configured:

```yaml
buses:
  - id: "can_bus"
    plugin: "can_plugin"
    type: "can"
    bitrate: 500000
    filters:
      - id: 0x100
        mask: 0x7FF

  - id: "diagnostic_bus"
    plugin: "diagnostic_plugin"
    type: "can"
    bitrate: 250000
    interface: "can1"
```

### Step 5: Test DUT Profile

Create a test script to validate the DUT profile:

```python
#!/usr/bin/env python3
"""
Test DUT profile configuration
"""

import asyncio
import yaml
from pathlib import Path


def validate_dut_profile(config: dict, dut_id: str):
    """Validate a DUT profile configuration"""
    if 'dut_profiles' not in config:
        print("❌ No DUT profiles found in configuration")
        return False

    dut_profile = None
    for profile in config['dut_profiles']:
        if profile['id'] == dut_id:
            dut_profile = profile
            break

    if not dut_profile:
        print(f"❌ DUT profile '{dut_id}' not found")
        return False

    print(f"✅ Found DUT profile: {dut_profile['name']}")
    print(f"   Description: {dut_profile['description']}")

    # Validate channels
    if 'channels' in dut_profile:
        print(f"   Required channels: {len(dut_profile['channels'])}")
        for ch in dut_profile['channels']:
            print(f"     - {ch['id']} ({ch['direction']}, required: {ch['required']})")

            # Check if channel exists in configuration
            channel_found = False
            if 'channels' in config:
                for cfg_ch in config['channels']:
                    if cfg_ch['id'] == ch['id']:
                        channel_found = True
                        break

            if not channel_found:
                print(f"       ⚠️  Channel '{ch['id']}' not found in configuration")

    # Validate buses
    if 'buses' in dut_profile:
        print(f"   Required buses: {len(dut_profile['buses'])}")
        for bus_id in dut_profile['buses']:
            print(f"     - {bus_id}")

            # Check if bus exists in configuration
            bus_found = False
            if 'buses' in config:
                for cfg_bus in config['buses']:
                    if cfg_bus['id'] == bus_id:
                        bus_found = True
                        break

            if not bus_found:
                print(f"       ⚠️  Bus '{bus_id}' not found in configuration")

    return True


async def test_dut_profile():
    """Test DUT profile validation"""
    config_file = Path("config/testbench.yaml")

    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    print("🔍 Validating DUT profiles...")
    print()

    # Test each DUT profile
    for profile in config.get('dut_profiles', []):
        print(f"Testing DUT profile: {profile['id']}")
        validate_dut_profile(config, profile['id'])
        print()


if __name__ == "__main__":
    asyncio.run(test_dut_profile())
```

## Creating a Sample Client

Clients interact with the Virtual Test Engineer via the REST API. Here's how to create a comprehensive client application.

### Step 1: Basic Client Structure

Create a Python client library:

```python
#!/usr/bin/env python3
"""
Virtual Test Engineer Python Client
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class ChannelInfo:
    """Channel information"""
    id: str
    type: str
    status: str
    value: Optional[float] = None
    units: Optional[str] = None


@dataclass
class TestBenchStatus:
    """Test bench status"""
    state: str
    config_file: str
    loaded_plugins: List[str]
    available_channels: int
    active_runs: int


class VirtualTestEngineerClient:
    """REST API client for Virtual Test Engineer"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{endpoint}"

        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")

            return await response.json()

    # Health and Status Methods

    async def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        return await self._request('GET', '/health')

    async def get_bench_info(self) -> Dict[str, Any]:
        """Get test bench information"""
        return await self._request('GET', '/bench')

    async def get_capabilities(self) -> Dict[str, Any]:
        """Get system capabilities"""
        return await self._request('GET', '/capabilities')

    # Channel Methods

    async def list_channels(self) -> List[ChannelInfo]:
        """List all available channels"""
        response = await self._request('GET', '/channels')
        channels = []
        for ch_data in response['channels']:
            channels.append(ChannelInfo(
                id=ch_data['id'],
                type=ch_data['type'],
                status=ch_data['status'],
                value=ch_data.get('value'),
                units=ch_data.get('units')
            ))
        return channels

    async def read_channel(self, channel_id: str) -> ChannelInfo:
        """Read channel value"""
        response = await self._request('GET', f'/channels/{channel_id}')
        return ChannelInfo(
            id=response['id'],
            type=response['type'],
            status=response['status'],
            value=response['value'],
            units=response.get('units')
        )

    async def write_channel(self, channel_id: str, value: Union[int, float, bool]) -> Dict[str, Any]:
        """Write channel value"""
        data = {'value': value}
        return await self._request('PUT', f'/channels/{channel_id}', json=data)

    async def read_multiple_channels(self, channel_ids: List[str]) -> List[ChannelInfo]:
        """Read multiple channels"""
        data = {'channel_ids': channel_ids}
        response = await self._request('POST', '/channels/read', json=data)

        channels = []
        for ch_data in response['channels']:
            channels.append(ChannelInfo(
                id=ch_data['id'],
                type=ch_data['type'],
                status=ch_data['status'],
                value=ch_data['value'],
                units=ch_data.get('units')
            ))
        return channels

    # Test Execution Methods

    async def start_test(self, test_config: Dict[str, Any]) -> str:
        """Start a test run"""
        response = await self._request('POST', '/tests', json=test_config)
        return response['test_id']

    async def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get test status"""
        return await self._request('GET', f'/tests/{test_id}')

    async def stop_test(self, test_id: str) -> Dict[str, Any]:
        """Stop a test run"""
        return await self._request('DELETE', f'/tests/{test_id}')

    async def list_tests(self) -> List[Dict[str, Any]]:
        """List all tests"""
        response = await self._request('GET', '/tests')
        return response['tests']

    # Flashing Methods

    async def list_firmware_files(self) -> List[Dict[str, Any]]:
        """List available firmware files"""
        response = await self._request('GET', '/flash/files')
        return response['files']

    async def upload_firmware(self, file_path: str, description: str = None,
                            version: str = None) -> Dict[str, Any]:
        """Upload firmware file"""
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path)
            if description:
                data.add_field('description', description)
            if version:
                data.add_field('version', version)

            return await self._request('POST', '/flash/upload', data=data)

    async def start_flash(self, file_id: str, protocol: str, target_device: str,
                         parameters: Dict[str, Any] = None) -> str:
        """Start firmware flashing"""
        data = {
            'file_id': file_id,
            'protocol': protocol,
            'target_device': target_device,
            'parameters': parameters or {}
        }
        response = await self._request('POST', '/flash', json=data)
        return response['flash_id']

    async def get_flash_status(self, flash_id: str = None) -> Dict[str, Any]:
        """Get flash operation status"""
        endpoint = f'/flash/status'
        if flash_id:
            endpoint += f'?flash_id={flash_id}'
        return await self._request('GET', endpoint)

    async def cancel_flash(self, flash_id: str) -> Dict[str, Any]:
        """Cancel flash operation"""
        return await self._request('DELETE', f'/flash/{flash_id}')

    # Utility Methods

    async def wait_for_flash_completion(self, flash_id: str, timeout: float = 300.0,
                                      poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for flash operation to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_flash_status(flash_id)

            if status['status'] in ['completed', 'failed', 'cancelled']:
                return status

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Flash operation {flash_id} did not complete within {timeout} seconds")

    async def wait_for_test_completion(self, test_id: str, timeout: float = 300.0,
                                     poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for test to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_test_status(test_id)

            if status['status'] in ['completed', 'failed', 'aborted']:
                return status

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Test {test_id} did not complete within {timeout} seconds")
```

### Step 2: Create Configuration Management

Create a configuration class for client settings:

```python
#!/usr/bin/env python3
"""
Client Configuration Management
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ClientConfig:
    """Client configuration"""
    server_url: str = "http://localhost:8080"
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    log_level: str = "INFO"
    auth_token: Optional[str] = None
    ssl_verify: bool = True

    # Test-specific settings
    default_test_timeout: float = 300.0
    default_poll_interval: float = 1.0

    # Flashing settings
    default_flash_timeout: float = 300.0
    default_flash_protocol: str = "avrdude"

    # DUT profiles
    default_dut_profile: Optional[str] = None


class ConfigManager:
    """Configuration manager for client"""

    def __init__(self, config_file: str = "~/.vte_client/config.json"):
        self.config_file = Path(config_file).expanduser()
        self.config = ClientConfig()

    def load_config(self) -> ClientConfig:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Update config with loaded data
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

        return self.config

    def save_config(self) -> None:
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)

    def update_config(self, **kwargs) -> None:
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                print(f"Warning: Unknown config key: {key}")

    def get_config(self) -> ClientConfig:
        """Get current configuration"""
        return self.config

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = ClientConfig()
```

### Step 3: Create Example Application

Create a comprehensive example application:

```python
#!/usr/bin/env python3
"""
Example Virtual Test Engineer Client Application
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from vte_client import VirtualTestEngineerClient, ConfigManager


async def example_channel_operations(client: VirtualTestEngineerClient):
    """Demonstrate channel operations"""
    print("🔌 Testing Channel Operations")
    print("-" * 40)

    # List all channels
    channels = await client.list_channels()
    print(f"Found {len(channels)} channels:")
    for ch in channels:
        print(f"  - {ch.id} ({ch.type})")

    # Read a channel (if available)
    if channels:
        channel_id = channels[0].id
        print(f"\nReading channel: {channel_id}")
        channel_info = await client.read_channel(channel_id)
        print(f"Value: {channel_info.value} {channel_info.units}")

        # Write to a channel (if it's an output)
        if 'output' in channel_info.type.lower():
            print(f"Writing to channel: {channel_id}")
            await client.write_channel(channel_id, 50.0)
            print("Write successful")

    print()


async def example_flashing_operations(client: VirtualTestEngineerClient):
    """Demonstrate flashing operations"""
    print("⚡ Testing Flashing Operations")
    print("-" * 40)

    # List firmware files
    files = await client.list_firmware_files()
    print(f"Found {len(files)} firmware files")

    # Upload a firmware file (if it exists)
    test_firmware = Path("test_firmware.hex")
    if test_firmware.exists():
        print(f"Uploading firmware: {test_firmware}")
        upload_result = await client.upload_firmware(
            str(test_firmware),
            description="Test firmware for demonstration",
            version="1.0.0"
        )
        print(f"Upload successful: {upload_result['file_id']}")

        # Start flash operation
        flash_id = await client.start_flash(
            file_id=upload_result['file_id'],
            protocol="avrdude",
            target_device="atmega328p",
            parameters={"port": "/dev/ttyUSB0"}
        )
        print(f"Flash started: {flash_id}")

        # Wait for completion
        try:
            final_status = await client.wait_for_flash_completion(flash_id, timeout=60.0)
            print(f"Flash completed: {final_status['status']}")
        except TimeoutError as e:
            print(f"Flash timeout: {e}")
    else:
        print("No test firmware file found, skipping upload/flash demo")

    print()


async def example_test_execution(client: VirtualTestEngineerClient):
    """Demonstrate test execution"""
    print("🧪 Testing Test Execution")
    print("-" * 40)

    # Example test configuration
    test_config = {
        "name": "Basic ECU Test",
        "description": "Test basic ECU functionality",
        "dut_profile": "arduino_ecu",
        "steps": [
            {
                "id": "setup",
                "type": "channel_write",
                "description": "Set throttle to 50%",
                "parameters": {
                    "channel_id": "throttle_position",
                    "value": 50.0
                }
            },
            {
                "id": "read_engine_speed",
                "type": "channel_read",
                "description": "Read engine speed",
                "parameters": {
                    "channel_id": "engine_speed"
                }
            },
            {
                "id": "validate",
                "type": "assert",
                "description": "Validate engine speed is reasonable",
                "parameters": {
                    "condition": "engine_speed > 1000",
                    "message": "Engine speed should be above 1000 RPM at 50% throttle"
                }
            }
        ]
    }

    # Start test
    test_id = await client.start_test(test_config)
    print(f"Test started: {test_id}")

    # Wait for completion
    try:
        final_status = await client.wait_for_test_completion(test_id, timeout=30.0)
        print(f"Test completed: {final_status['status']}")

        if final_status['status'] == 'completed':
            print("✅ Test passed!")
        else:
            print("❌ Test failed!")
            if 'results' in final_status:
                for result in final_status['results']:
                    if not result.get('passed', True):
                        print(f"  Failed step: {result.get('step_id', 'unknown')}")
    except TimeoutError as e:
        print(f"Test timeout: {e}")

    print()


async def main():
    """Main application"""
    parser = argparse.ArgumentParser(description="Virtual Test Engineer Client Example")
    parser.add_argument("--server", default="http://localhost:8080",
                       help="Server URL")
    parser.add_argument("--config", default="~/.vte_client/config.json",
                       help="Configuration file")
    parser.add_argument("--test", choices=['channels', 'flashing', 'test', 'all'],
                       default='all', help="Test to run")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    # Load configuration
    config_manager = ConfigManager(args.config)
    config = config_manager.load_config()
    config.server_url = args.server  # Override with command line

    print("🚀 Virtual Test Engineer Client Example")
    print(f"Server: {config.server_url}")
    print()

    # Test connection
    try:
        async with VirtualTestEngineerClient(config.server_url) as client:
            # Health check
            health = await client.health_check()
            print(f"✅ Server health: {health['status']}")
            print()

            # Run selected tests
            if args.test in ['channels', 'all']:
                await example_channel_operations(client)

            if args.test in ['flashing', 'all']:
                await example_flashing_operations(client)

            if args.test in ['test', 'all']:
                await example_test_execution(client)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Create Setup Script

Create a setup script for the client:

```python
#!/usr/bin/env python3
"""
Setup script for Virtual Test Engineer Client
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vte-client",
    version="1.0.0",
    author="Virtual Test Engineer Team",
    author_email="team@vte.example.com",
    description="Python client for Virtual Test Engineer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/virtual-test-engineer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=1.8.0",
        "dataclasses>=0.6; python_version < '3.7'",
    ],
    extras_require={
        "dev": ["pytest>=6.0", "pytest-asyncio>=0.15"],
    },
    entry_points={
        "console_scripts": [
            "vte-client=example_client:main",
        ],
    },
)
```

### Step 5: Create Configuration File

Create a sample configuration file:

```json
{
  "server_url": "http://localhost:8080",
  "timeout": 30.0,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "log_level": "INFO",
  "ssl_verify": true,
  "default_test_timeout": 300.0,
  "default_poll_interval": 1.0,
  "default_flash_timeout": 300.0,
  "default_flash_protocol": "avrdude",
  "default_dut_profile": "arduino_ecu"
}
```

## Configuration Reference

### Main Configuration Structure

```yaml
version: "1.0"
name: "My Test Bench"
description: "Description of your test setup"

plugins:
  - name: "plugin_name"
    type: "device_driver"
    config:
      # Plugin-specific configuration

instruments:
  - id: "instrument_id"
    plugin: "plugin_name"
    type: "adc|dac|pwm|digital_input|digital_output"
    channel: 0  # Physical channel number
    calibration:
      min: 0.0
      max: 5.0
      units: "volts"

channels:
  - id: "logical_channel_id"
    instrument: "instrument_id"
    logical_name: "LOGICAL_NAME"
    scaling:
      input_range: [0.0, 5.0]
      output_range: [0, 100]
      units: "%"

buses:
  - id: "bus_id"
    plugin: "bus_plugin"
    type: "can|serial|ethernet"
    bitrate: 500000
    interface: "can0"

dut_profiles:
  - id: "dut_profile_id"
    name: "DUT Profile Name"
    description: "Description"
    channels:
      - id: "channel_id"
        required: true
        direction: "input|output"
    buses:
      - bus_id

flashing:
  enabled: true
  firmware_directory: "./firmware"
  supported_protocols: ["avrdude", "openocd"]
  default_timeout: 300
  max_concurrent_operations: 1
  verification_enabled: true
```

## API Reference

### REST API Endpoints

#### Health & Status
- `GET /health` - System health check
- `GET /bench` - Test bench information
- `GET /capabilities` - System capabilities

#### Channels
- `GET /channels` - List all channels
- `GET /channels/{id}` - Read channel value
- `PUT /channels/{id}` - Write channel value
- `POST /channels/read` - Read multiple channels

#### Tests
- `GET /tests` - List test runs
- `POST /tests` - Start new test
- `GET /tests/{id}` - Get test status
- `DELETE /tests/{id}` - Stop test

#### Flashing
- `GET /flash/files` - List firmware files
- `POST /flash/upload` - Upload firmware
- `POST /flash` - Start flash operation
- `GET /flash/status` - Get flash status
- `DELETE /flash/{id}` - Cancel flash operation

### Response Codes
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Internal server error

This guide provides a comprehensive foundation for extending the Virtual Test Engineer system. Each section includes working examples and best practices for adding new simulators, DUT profiles, and client applications.</content>
<parameter name="filePath">/workspaces/virtual_test_engineer/USER_GUIDE.md
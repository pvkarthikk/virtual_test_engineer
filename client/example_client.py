#!/usr/bin/env python3
"""
Example Virtual Test Engineer Client Application
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from vte_client import VirtualTestEngineerClient
from config_manager import ConfigManager


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
    test_firmware = Path("../test_firmware.hex")
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
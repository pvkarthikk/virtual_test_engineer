#!/usr/bin/env python3
"""
Test script for Virtual Test Engineer Client
Demonstrates basic client functionality
"""

import asyncio
import sys
import os

# Add client directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'client'))

from vte_client import VirtualTestEngineerClient


async def test_basic_functionality():
    """Test basic client functionality"""
    print("🧪 Testing Virtual Test Engineer Client")
    print("=" * 50)

    try:
        async with VirtualTestEngineerClient("http://localhost:8080") as client:
            # Test health check
            print("🔍 Testing health check...")
            health = await client.health_check()
            print(f"✅ Server health: {health['status']}")
            print(f"   State: {health['details']['state']}")
            print(f"   Config: {health['details']['config_file']}")
            print()

            # Test bench info
            print("🏭 Testing bench info...")
            bench = await client.get_bench_info()
            print(f"✅ Bench: {bench['name']} v{bench['version']}")
            print(f"   Status: {bench['status']}")
            print()

            # Test channel operations
            print("📡 Testing channel operations...")
            channels = await client.list_channels()
            print(f"✅ Found {len(channels)} channels")

            if channels:
                # Test reading a channel
                channel_id = channels[0].id
                print(f"   Reading channel: {channel_id}")
                channel_info = await client.read_channel(channel_id)
                print(f"   ✅ Value: {channel_info.value} {channel_info.units}")

                # Test writing to a channel (if it's an output)
                if 'output' in channel_info.type.lower():
                    print(f"   Writing to channel: {channel_id}")
                    await client.write_channel(channel_id, 50.0)
                    print("   ✅ Write successful")
            print()

            # Test flashing operations
            print("⚡ Testing flashing operations...")
            firmware_files = await client.list_firmware_files()
            print(f"✅ Found {len(firmware_files)} firmware files")

            # Note: Actual flashing would require firmware files
            print("   (Upload and flash operations require firmware files)")
            print()

            print("🎉 All basic tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


async def test_advanced_functionality():
    """Test advanced client functionality"""
    print("\n🔬 Testing Advanced Client Features")
    print("=" * 50)

    try:
        async with VirtualTestEngineerClient("http://localhost:8080") as client:
            # Test multiple channel reading
            print("📊 Testing multiple channel reading...")
            channels = await client.list_channels()
            if len(channels) > 1:
                channel_ids = [ch.id for ch in channels[:3]]  # First 3 channels
                print(f"   Reading channels: {channel_ids}")
                readings = await client.read_multiple_channels(channel_ids)
                for reading in readings:
                    print(f"   ✅ {reading.id}: {reading.value} {reading.units}")
            else:
                print("   ⚠️  Not enough channels for multi-read test")
            print()

            # Test capabilities
            print("🔧 Testing capabilities...")
            caps = await client.get_capabilities()
            print(f"✅ System capabilities retrieved")
            print(f"   Channels: {caps.get('available_channels', 'N/A')}")
            print()

            print("🎉 Advanced tests completed successfully!")

    except Exception as e:
        print(f"❌ Advanced test failed: {e}")
        return False

    return True


async def main():
    """Main test function"""
    print("🚀 Virtual Test Engineer Client Test Suite")
    print("This test assumes the server is running on http://localhost:8080")
    print()

    # Test basic functionality
    basic_success = await test_basic_functionality()

    if basic_success:
        # Test advanced functionality
        advanced_success = await test_advanced_functionality()

        if advanced_success:
            print("\n🎊 All tests passed! Client is working correctly.")
            return 0
        else:
            print("\n⚠️  Basic tests passed, but advanced tests failed.")
            return 1
    else:
        print("\n❌ Basic tests failed. Check server connection and configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
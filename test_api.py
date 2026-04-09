#!/usr/bin/env python3
"""
Test script to demonstrate Virtual Test Engineer functionality
"""

import asyncio
import aiohttp
import json


async def test_api():
    """Test the REST API endpoints"""

    base_url = "http://localhost:8080"

    async with aiohttp.ClientSession() as session:
        try:
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Health check passed: {health['status']}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return

            # Test bench info
            print("\n🏭 Testing bench info...")
            async with session.get(f"{base_url}/bench") as response:
                if response.status == 200:
                    bench = await response.json()
                    print(f"✅ Bench info: {bench['name']} - {bench['status']}")
                else:
                    print(f"❌ Bench info failed: {response.status}")

            # Test channels
            print("\n📡 Testing channels...")
            async with session.get(f"{base_url}/channels") as response:
                if response.status == 200:
                    channels = await response.json()
                    print(f"✅ Found {len(channels['channels'])} channels")
                    for ch in channels['channels']:
                        print(f"  - {ch['id']} ({ch['type']})")
                else:
                    print(f"❌ Channels list failed: {response.status}")

            # Test channel read (if channels exist)
            channels_data = None
            async with session.get(f"{base_url}/channels") as response:
                if response.status == 200:
                    channels_data = await response.json()

            if channels_data and channels_data['channels']:
                channel_id = channels_data['channels'][0]['id']
                print(f"\n📖 Testing channel read: {channel_id}")
                async with session.get(f"{base_url}/channels/{channel_id}") as response:
                    if response.status == 200:
                        reading = await response.json()
                        print(f"✅ Channel read: {reading['value']} {reading.get('units', '')}")
                    else:
                        print(f"❌ Channel read failed: {response.status}")

            # Test test run
            print("\n🧪 Testing test scenario execution...")
            test_request = {
                "scenario_id": "throttle_response_test",
                "parameters": {"throttle_positions": [25, 50, 75]},
                "async": True
            }

            async with session.post(f"{base_url}/runs",
                                  json=test_request,
                                  headers={'Content-Type': 'application/json'}) as response:
                if response.status == 200:
                    run_result = await response.json()
                    run_id = run_result['run_id']
                    print(f"✅ Test run started: {run_id}")

                    # Wait a bit then check status
                    await asyncio.sleep(2)

                    async with session.get(f"{base_url}/runs/{run_id}") as status_response:
                        if status_response.status == 200:
                            status = await status_response.json()
                            print(f"✅ Test run status: {status['status']}")

                            if status['status'] in ['completed', 'failed']:
                                # Get results
                                async with session.get(f"{base_url}/runs/{run_id}/results") as results_response:
                                    if results_response.status == 200:
                                        results = await results_response.json()
                                        print(f"✅ Test results: {results['summary']}")
                        else:
                            print(f"❌ Status check failed: {status_response.status}")
                else:
                    error_text = await response.text()
                    print(f"❌ Test run failed: {response.status} - {error_text}")

        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
            print("💡 Make sure the server is running: python -m src.main")


async def main():
    """Main test function"""
    print("🚀 Virtual Test Engineer API Test")
    print("=" * 40)

    # Give the server time to start if running in parallel
    await asyncio.sleep(1)

    await test_api()

    print("\n" + "=" * 40)
    print("✨ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
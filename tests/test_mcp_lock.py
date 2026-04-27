import sys
import os
import asyncio
import json

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem
from routers.mcp import handle_call_tool
import mcp.types as types

async def test_mcp_lock():
    print("Testing MCP Lock...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    await system.startup()
    await system.device_manager.connect_all()

    # 1. Start a long running test step
    script = '{"action": "wait", "duration_ms": 2000}\n'
    task = asyncio.create_task(system.test_engine.run_jsonl_script(script))
    
    await asyncio.sleep(0.5)
    assert system.test_engine.is_test_running == True
    print("Test is running...")

    # 2. Attempt MCP write_channel
    print("Attempting MCP write_channel...")
    result = await handle_call_tool("write_channel", {"channel_id": "test", "value": 10.0})
    print(f"Result: {result[0].text}")
    assert "Error: Cannot perform manual write" in result[0].text

    # 3. Attempt MCP write_channels
    print("Attempting MCP write_channels...")
    result = await handle_call_tool("write_channels", {"writes": [{"channel_id": "test", "value": 10.0}]})
    print(f"Result: {result[0].text}")
    assert "Error: Cannot perform manual write" in result[0].text

    # 4. Wait for test to finish
    await task
    assert system.test_engine.is_test_running == False
    print("Test finished.")

    # 5. Attempt MCP write after test finished (should work)
    print("Attempting MCP write_channel after test...")
    # Inject a valid channel for write (same as we did before to avoid errors)
    from models.config import ChannelConfig, ChannelProperties
    test_ch = ChannelConfig(
        channel_id="test_channel",
        device_id="mock_1",
        signal_id="DO0",
        properties=ChannelProperties(unit="V", min=0, max=100, resolution=1, offset=0)
    )
    system.channel_manager.channels["test_channel"] = test_ch

    result = await handle_call_tool("write_channel", {"channel_id": "test_channel", "value": 10.0})
    print(f"Result: {result[0].text}")
    assert "Successfully set channel" in result[0].text

    print("MCP Lock Test Passed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_lock())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

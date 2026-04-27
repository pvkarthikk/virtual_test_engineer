import sys
import os
import asyncio
import json

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem
from core.base_device import BaseDeviceException

async def test_safety_bounds():
    print("Testing Dual-Layer Safety Bounds...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    await system.startup()
    await system.device_manager.connect_all()

    # 1. Setup a channel with broad logical bounds but narrow physical bounds
    # AI0 has physical bounds [0, 5]
    from models.config import ChannelConfig, ChannelProperties
    ch_cfg = ChannelConfig(
        channel_id="ch_safety",
        device_id="mock_1",
        signal_id="AI0",
        properties=ChannelProperties(unit="C", min=-100, max=1000, resolution=0.1, offset=0)
    )
    system.channel_manager.channels["ch_safety"] = ch_cfg

    # 2. Attempt a write that is logically OK but physically out of bounds
    # Value 10.0 -> Raw 100.0 (since offset=0, res=0.1)
    # Physical max is 5.0
    print("Attempting write (Logical: OK, Physical: OUT)...")
    try:
        await system.channel_manager.write_channel("ch_safety", 10.0)
        assert False, "Should have raised BaseDeviceException"
    except BaseDeviceException as e:
        print(f"Caught expected hardware exception: {e}")
        assert e.code == "SIGNAL_OUT_OF_BOUNDS"
    except Exception as e:
        print(f"Caught unexpected exception: {type(e).__name__}: {e}")
        assert False

    # 3. Attempt a write that is logically OUT (should fail at ChannelManager)
    print("Attempting write (Logical: OUT)...")
    try:
        await system.channel_manager.write_channel("ch_safety", 2000.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"Caught expected logical exception: {e}")
        assert "out of bounds for channel" in str(e)

    # 4. Attempt a write that is both OK
    print("Attempting write (Logical: OK, Physical: OK)...")
    await system.channel_manager.write_channel("ch_safety", 0.4) # Raw 4.0
    print("Write successful!")

    print("Safety Bounds Test Passed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_safety_bounds())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

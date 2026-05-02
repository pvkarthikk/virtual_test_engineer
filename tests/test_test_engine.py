import sys
import os
import asyncio
import json

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

async def test_test_engine():
    print("Testing Test Engine...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    await system.startup()
    await system.device_manager.connect_all()

    # 3. Inject a valid channel for testing
    from models.config import ChannelConfig, ChannelProperties
    test_ch = ChannelConfig(
        channel_id="test_channel",
        device_id="mock_1",
        signal_id="DO0",
        properties=ChannelProperties(unit="V", min=0, max=100, resolution=1, offset=0)
    )
    system.channel_manager.channels["test_channel"] = test_ch

    # Create a simple JSONL script
    script = (
        '{"action": "write", "channel": "test_channel", "value": 25.0}\n'
        '{"action": "wait", "duration_ms": 500}\n'
        '{"action": "assert", "channel": "test_channel", "condition": "==", "value": 25.0}\n'
    )

    print("Running script...")
    await system.test_engine.run_jsonl_script(script)
    print("Script finished OK")

async def test_concurrency_lock():
    print("\nTesting Concurrency Lock...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    
    # 1. Start a long running test step
    script = '{"action": "wait", "duration_ms": 2000}\n'
    
    # Run in background
    task = asyncio.create_task(system.test_engine.run_jsonl_script(script))
    
    # Wait a bit for it to start
    await asyncio.sleep(0.5)
    assert system.test_engine.is_test_running == True
    assert system.test_engine._lock.locked() == True
    print("Test is running in background...")

    # 2. Attempt manual write
    print(f"is_test_running: {system.test_engine.is_test_running}")
    
    # 3. Attempt to run another test script concurrently
    try:
        await system.test_engine.run_jsonl_script('{"action": "wait", "duration_ms": 100}')
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        print("Concurrency lock verified (RuntimeError raised correctly).")
    
    # 4. Wait for test to finish
    await task
    assert system.test_engine.is_test_running == False
    print("Concurrency test passed (flag logic verified)")

if __name__ == "__main__":
    try:
        asyncio.run(test_test_engine())
        asyncio.run(test_concurrency_lock())
        print("\nAll test engine tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

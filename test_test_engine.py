import sys
import os
import asyncio
import json

# Add source directory to path
source_path = os.path.join(os.getcwd(), "sdtb", "source")
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

async def test_test_engine():
    print("Testing Test Engine...")
    config_dir = os.path.join(os.getcwd(), "sdtb", "source", "config")
    system = SDTBSystem(config_dir)
    system.startup()
    system.device_manager.connect_all()

    # Create a simple JSONL script
    # 1. Write ch_temp to 25
    # 2. Wait 500ms
    # 3. Assert ch_temp == 25
    script = (
        '{"action": "write", "channel": "ch_temp", "value": 25.0}\n'
        '{"action": "wait", "duration_ms": 500}\n'
        '{"action": "assert", "channel": "ch_temp", "condition": "==", "value": 25.0}\n'
    )

    print("Running script...")
    await system.test_engine.run_jsonl_script(script)
    print("Script finished OK")

async def test_concurrency_lock():
    print("\nTesting Concurrency Lock...")
    config_dir = os.path.join(os.getcwd(), "sdtb", "source", "config")
    system = SDTBSystem(config_dir)
    
    # 1. Start a long running test step
    script = '{"action": "wait", "duration_ms": 2000}\n'
    
    # Run in background
    task = asyncio.create_task(system.test_engine.run_jsonl_script(script))
    
    # Wait a bit for it to start
    await asyncio.sleep(0.5)
    assert system.test_engine.is_test_running == True
    print("Test is running in background...")

    # 2. Attempt manual write (via ChannelManager directly - in real app via API)
    # The API router checks is_test_running.
    # Let's verify our is_test_running flag is correct.
    print(f"is_test_running: {system.test_engine.is_test_running}")
    
    # 3. Wait for test to finish
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

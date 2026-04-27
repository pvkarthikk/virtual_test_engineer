import sys
import os
import asyncio
import time

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

async def test_flash_non_blocking():
    print("Testing Non-Blocking Flashing...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    await system.startup()
    
    # We'll use the 'mock_target' protocol which uses FlashMock
    # FlashMock.connect() has a 0.5s sleep.
    
    start_time = time.time()
    
    # Run a "fast" task in parallel with the "slow" connect
    async def fast_task():
        await asyncio.sleep(0.1)
        print("Fast task finished during blocking connection!")
        return time.time() - start_time

    print("Starting concurrent connect and fast task...")
    results = await asyncio.gather(
        system.flash_manager.connect_target("mock_target"),
        fast_task()
    )
    
    total_time = time.time() - start_time
    fast_task_time = results[1]
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Fast task took: {fast_task_time:.2f}s")
    
    # Verification
    assert fast_task_time < 0.4, "Fast task should have finished immediately despite slow connection"
    assert total_time >= 0.5, "Slow connection should have taken at least 0.5s"
    print("SUCCESS: Flash connection did NOT block the event loop!")

async def test_flash_sse_logic():
    print("\nTesting Flash SSE Logic...")
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    
    # Mocking a Request object for the router
    class MockRequest:
        async def is_disconnected(self): return False

    from routers.flash import stream_flash_log
    
    # Start a mock flash
    execution_id = await system.flash_manager.start_flash("mock_target", b"hello", {})
    
    # Get the response from the router
    response = await stream_flash_log("mock_target", execution_id, MockRequest())
    
    print(f"SSE Response Type: {type(response).__name__}")
    assert type(response).__name__ == "EventSourceResponse"
    
    # Consume a few logs from the generator
    count = 0
    async for event in response.body_iterator:
        print(f"Received Event: {event}")
        count += 1
        if count > 3: break
        if "TERMINATED" in str(event): break

    print("SSE Logic Verification OK")

if __name__ == "__main__":
    try:
        asyncio.run(test_flash_non_blocking())
        asyncio.run(test_flash_sse_logic())
        print("\nAll flash async tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

import sys
import os
import asyncio

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

async def test_integration():
    print("Testing System Integration...")
    config_dir = os.path.join(source_path, "config")
    
    # Initialize system with the specific test config directory
    system = SDTBSystem(config_dir)
    
    # 1. Startup: Discover and Initialize
    system.startup()
    
    assert "mock_1" in system.device_manager.devices, "mock_1 device should be discovered"
    assert "ch_temp" in system.channel_manager.channels, "ch_temp channel should be initialized"
    print("Discovery & Initialization OK")
    
    # 2. Connect
    system.device_manager.connect_all()
    print("Connection OK")
    
    # 3. Read Channel
    val = system.channel_manager.read_channel("ch_temp")
    print(f"Read ch_temp (scaled): {val}")
    assert val == -19.75, f"Expected -19.75, got {val}"
    
    # 4. Write Channel
    print("Writing 20.0 to ch_temp...")
    system.channel_manager.write_channel("ch_temp", 20.0)
    
    # Verify write reached mock device correctly
    mock_dev = system.device_manager.get_device("mock_1")
    raw_val = mock_dev.read_signal("AI0")
    print(f"Mock device raw signal AI0: {raw_val}")
    assert raw_val == 400.0, f"Expected 400.0, got {raw_val}"
    
    # 5. Out of bounds check
    print("Testing out of bounds write (expecting ValueError)...")
    try:
        system.channel_manager.write_channel("ch_temp", 200.0) # max is 150.0
        assert False, "Should have raised ValueError for out of bounds"
    except ValueError as e:
        print(f"Caught expected error: {e}")

    # 6. Shutdown
    await system.shutdown()
    print("Shutdown OK")

if __name__ == "__main__":
    try:
        asyncio.run(test_integration())
        print("\nFull system integration test passed!")
    except Exception as e:
        print(f"\nIntegration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

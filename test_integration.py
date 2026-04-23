import sys
import os

# Add source directory to path
source_path = os.path.join(os.getcwd(), "sdtb", "source")
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

def test_integration():
    print("Testing System Integration...")
    config_dir = os.path.join(os.getcwd(), "sdtb", "source", "config")
    
    # Initialize system with the specific test config directory
    # (The singleton instance might already be initialized if we were in the same process)
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
    # Mock AI0 defaults to 2.5
    # ch_temp mapping: Value = (Raw * 0.1) - 20.0
    # Value = (2.5 * 0.1) - 20.0 = 0.25 - 20.0 = -19.75
    val = system.channel_manager.read_channel("ch_temp")
    print(f"Read ch_temp (scaled): {val}")
    assert val == -19.75, f"Expected -19.75, got {val}"
    
    # 4. Write Channel
    # target = 20.0
    # Raw = (Target - Offset) / Resolution
    # Raw = (20.0 - (-20.0)) / 0.1 = 40.0 / 0.1 = 400.0
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
    system.shutdown()
    print("Shutdown OK")

if __name__ == "__main__":
    try:
        test_integration()
        print("\nFull system integration test passed!")
    except Exception as e:
        print(f"\nIntegration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

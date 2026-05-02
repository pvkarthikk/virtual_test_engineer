import sys
import os
import asyncio
import time
from typing import List, Any, Optional

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem
from core.base_device import BaseDevice, SignalDefinition

class SlowMockDevice(BaseDevice):
    def __init__(self):
        self._connected = False
        self._enabled = True
    
    @property
    def is_connected(self) -> bool: return self._connected
    @property
    def vendor(self) -> str: return "Mock"
    @property
    def model(self) -> str: return "SlowDevice"
    @property
    def firmware_version(self) -> str: return "1.0"
    @property
    def enabled(self) -> bool: return self._enabled
    @enabled.setter
    def enabled(self, value: bool): self._enabled = value

    def connect(self, params: dict): self._connected = True
    def disconnect(self): self._connected = False
    def restart(self): pass

    def inject_fault(self, signal_id: str, fault_id: str): pass
    def clear_fault(self, signal_id: Optional[str] = None): pass
    def get_available_faults(self, signal_id: str): return []
    
    def get_signals(self) -> List[SignalDefinition]:
        return [
            SignalDefinition("S1", "Slow Signal", "analog", "input", 1.0, "V", 0, 0, 10, 5.0, "Slow")
        ]

    def read_signal(self, signal_id: str) -> Any:
        print(f"DEBUG: Starting slow read for {signal_id}...")
        time.sleep(2) # SIMULATE BLOCKING HARDWARE
        print(f"DEBUG: Finished slow read for {signal_id}.")
        return 5.0

    def write_signal(self, signal_id: str, value: Any): pass
    def restart(self): pass

async def test_non_blocking():
    print("Testing Non-Blocking Hardware I/O...")
    
    # Manually setup a system with our slow mock device
    SDTBSystem._reset_instance()
    system = SDTBSystem()
    
    try:
        # Inject our mock device
        dev = SlowMockDevice()
        system.device_manager.devices["slow_dev"] = dev
        system.device_manager._system_connected = True
        dev.connect({})
        
        # Setup a channel for it
        from models.config import ChannelConfig, ChannelProperties, LinearConversion
        ch_cfg = ChannelConfig(
            channel_id="ch_slow",
            device_id="slow_dev",
            signal_id="S1",
            properties=ChannelProperties(
                unit="V", 
                min=0, 
                max=10, 
                conversion=LinearConversion(resolution=1.0, offset=0.0)
            )
        )
        system.channel_manager.channels["ch_slow"] = ch_cfg
        
        # Measure time for a concurrent task
        start_time = time.time()
        
        # Run the slow read and a "fast" task concurrently
        async def fast_task():
            await asyncio.sleep(0.1)
            print("Fast task finished while hardware is blocking!")
            return time.time() - start_time

        print("Starting concurrent tasks...")
        # These should run concurrently. If blocking, fast_task will wait 2s.
        results = await asyncio.gather(
            system.channel_manager.read_channel("ch_slow"),
            fast_task()
        )
        
        total_time = time.time() - start_time
        fast_task_time = results[1]
        
        print(f"Total time: {total_time:.2f}s")
        print(f"Fast task took: {fast_task_time:.2f}s")
        
        # Verification
        assert fast_task_time < 0.5, "Fast task should have finished immediately despite slow hardware"
        assert total_time >= 2.0, "Slow hardware should have taken at least 2s"
        print("SUCCESS: Hardware read did NOT block the event loop!")
    finally:
        await system.shutdown()
        SDTBSystem._reset_instance()

if __name__ == "__main__":
    try:
        asyncio.run(test_non_blocking())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

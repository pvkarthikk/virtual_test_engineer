from core.base_device import BaseDevice, SignalDefinition
from typing import List, Any, Dict, Optional
import logging
import random
import time

logger = logging.getLogger(__name__)
def generate_mock_value(signal: SignalDefinition):
    val = random.uniform(signal.min, signal.max)
    return round(val / signal.resolution) * signal.resolution


class EngineMock:
    def __init__(self):
        self._throttle_pwm = 0 # 0 - 255 PWM
        self._engine_speed = 0 # 0 - 4095 volt
        self._throttle_percent = 0 # 0 - 100 %
        self._engine_speed_rpm = 0 # 0 - 5000 rpm
        self._idle_rpm = 800
        self._max_rpm = 5000
    
    @property
    def throttle_pwm(self) -> int:
        return self._throttle_pwm

    @throttle_pwm.setter
    def throttle_pwm(self, value: int):
        self._throttle_pwm = max(0, min(255, value))
        self._throttle_percent = self._throttle_pwm / 255.0 * 100.0

    @property
    def engine_speed(self) -> int:
        return self._engine_speed

    def update(self):
        # calculate engine rpm based on the throttle percent
        target_rpm = self._idle_rpm + (self._max_rpm - self._idle_rpm) * (self._throttle_percent / 100.0)
        
        # Add some jitter/noise
        noise = random.uniform(-50, 50)
        self._engine_speed_rpm = target_rpm + noise
        
        # Clamp RPM to physical limits
        self._engine_speed_rpm = max(0, min(self._max_rpm + 500, self._engine_speed_rpm))
        
        # convert engine rpm to the engine speed (0-4095 range for 0-5000 RPM)
        # We allow it to go slightly above 4095 if RPM exceeds 5000 due to momentum/noise
        raw_val = self._engine_speed_rpm * 4095.0 / 5000.0
        self._engine_speed = max(0, min(4095, round(raw_val)))

class MockDevice(BaseDevice):
    def __init__(self):
        self._engine = EngineMock()
        self._connected = False
        self._enabled = True
        self._signals = [
            SignalDefinition(
                signal_id="J1_01",
                name="Engine Speed Feedback", 
                value=0, 
                direction="input",
                type="uint16", 
                min=0, 
                max=4095, 
                resolution=1, 
                unit="mV"),
            SignalDefinition(
                signal_id="J1_02",
                name="Throttle Command",
                direction="output",
                value=0, 
                type="uint8", 
                min=0, 
                max=255, 
                resolution=1, 
                unit="PWM"),
        ]

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def vendor(self) -> str:
        return "SDTB"

    @property
    def model(self) -> str:
        return "Mock-v1"

    @property
    def firmware_version(self) -> str:
        return "1.0.0"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def connect(self, connection_params: dict) -> None:
        logger.info(f"MockDevice connecting with {connection_params}")
        self._connected = True

    def disconnect(self) -> None:
        logger.info("MockDevice disconnected")
        self._connected = False

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    def restart(self) -> None:
        logger.info("MockDevice restarting...")
        self.disconnect()
        # Simulated delay
        time.sleep(0.5)
        self._connected = True
        logger.info("MockDevice restarted")
    
    def get_signal(self, signal_id: str) -> SignalDefinition:
        for s in self._signals:
            if s.signal_id == signal_id:
                return s
        raise ValueError(f"Signal {signal_id} not found in {self.vendor} {self.model}")

    def read_signal(self, signal_id: str) -> Any:
        if not self._connected:
            raise RuntimeError("Device not connected")
        sig = self.get_signal(signal_id)
        logger.info(f"MockDevice reading {signal_id} {sig.value}")
        return sig.value

    def write_signal(self, signal_id: str, value: Any) -> None:
        if not self._connected:
            raise RuntimeError("Device not connected")
        sig = self.get_signal(signal_id)
        sig.value = value
        logger.info(f"MockDevice writing {value} to {signal_id}")

    def update(self) -> None:
        if not self._connected:
            return
        
        # 1. Read commands from system
        self._engine.throttle_pwm = self.get_signal("J1_02").value
        
        # 2. Update engine state
        self._engine.update()
        
        # 3. Push feedback to system
        self.get_signal("J1_01").value = self._engine.engine_speed
        
        
    def inject_fault(self, signal_id: str, fault_id: str) -> None:
        """Mock implementation of fault injection."""
        logger.info(f"Mock Injecting fault '{fault_id}' on signal '{signal_id}'")
        pass

    def clear_fault(self, signal_id: Optional[str] = None) -> None:
        """Mock implementation of clearing faults."""
        if signal_id:
            logger.info(f"Mock Clearing fault on signal '{signal_id}'")
        else:
            logger.info("Mock Clearing all faults on device")
        pass

    def get_available_faults(self, signal_id: str) -> List[Dict[str, str]]:
        """Returns standard fault types for mock."""
        return [
        ]
    

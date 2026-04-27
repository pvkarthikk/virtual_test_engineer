from core.base_device import BaseDevice, SignalDefinition
from typing import List, Any, Dict
import logging
import random

logger = logging.getLogger(__name__)
def generate_mock_value(signal: SignalDefinition):
    val = random.uniform(signal.min, signal.max)
    return round(val / signal.resolution) * signal.resolution

class MockDevice(BaseDevice):
    def __init__(self):
        self._connected = False
        self._enabled = True
        self._signals = [
            SignalDefinition(
                signal_id="AI0",
                name="Analog Input 0",
                type="analog",
                direction="input",
                resolution=0.01,
                unit="V",
                offset=0,
                min=0,
                max=5,
                value=2.5,
                description="Mock AI 0"
            ),
            SignalDefinition(
                signal_id="DO0",
                name="Digital Output 0",
                type="digital",
                direction="output",
                resolution=1,
                unit="bool",
                offset=0,
                min=0,
                max=1,
                value=0,
                description="Mock DO 0"
            )
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
        import time
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
        self.validate_signal_value(sig, value)
        sig.value = value
        logger.info(f"MockDevice writing {value} to {signal_id}")
    def update(self) -> None:
        if not self._connected:
            return
        #generate 2 new values
        for sig in self._signals:
            if sig.direction == "input":
                sig.value = generate_mock_value(sig)
    

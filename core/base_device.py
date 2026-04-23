from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any

@dataclass
class SignalDefinition:
    signal_id: str
    name: str
    type: str        # e.g., "analog", "digital", "pwm", "can"
    direction: str   # "input", "output", or "bidirectional"
    resolution: float
    unit: str        # Measurement unit
    offset: float    # Calibration offset
    min: float       # Minimum valid range value
    max: float       # Maximum valid range value
    value: float     # Initial or last known value
    description: str # Physical connection info

class BaseDevice(ABC):
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the device is currently connected to hardware."""
        pass

    @property
    @abstractmethod
    def vendor(self) -> str:
        """Returns the vendor of the device."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Returns the model of the device."""
        pass

    @property
    @abstractmethod
    def firmware_version(self) -> str:
        """Returns the firmware version of the device."""
        pass

    @abstractmethod
    def connect(self, connection_params: dict) -> None:
        """Establishes connection to the hardware device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully closes the connection to the hardware device."""
        pass

    @abstractmethod
    def get_signals(self) -> List[SignalDefinition]:
        """Returns a list of signals supported by this device."""
        pass

    @abstractmethod
    def read_signal(self, signal_id: str) -> Any:
        """Reads a value from the specified signal."""
        pass

    @abstractmethod
    def write_signal(self, signal_id: str, value: Any) -> None:
        """Writes a value to the specified signal."""
        pass

class BaseDeviceException(Exception):
    """Base exception class for device-related errors."""
    pass

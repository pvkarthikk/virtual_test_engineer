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
        raise NotImplementedError("Subclasses must implement the connect method.")

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully closes the connection to the hardware device."""
        raise NotImplementedError("Subclasses must implement the disconnect method.")

    @abstractmethod
    def get_signals(self) -> List[SignalDefinition]:
        """Returns a list of signals supported by this device."""
        raise NotImplementedError("Subclasses must implement the get_signals method.")

    @abstractmethod
    def read_signal(self, signal_id: str) -> Any:
        """Reads a value from the specified signal."""
        raise NotImplementedError("Subclasses must implement the read_signal method.")

    @abstractmethod
    def write_signal(self, signal_id: str, value: Any) -> None:
        """Writes a value to the specified signal."""
        raise NotImplementedError("Subclasses must implement the write_signal method.")

    @abstractmethod
    def restart(self) -> None:
        """Restarts the hardware device."""
        raise NotImplementedError("Subclasses must implement the restart method.")

    def update(self) -> None:
        """Called periodically by the system for background tasks."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Returns True if the device is enabled."""
        pass

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool):
        """Sets the enabled state of the device."""
        pass

class BaseDeviceException(Exception):
    """Base exception class for device-related errors."""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.message = message
        self.code = code

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any, Optional, Dict

# ---------------------------------------------------------------------------
# Type aliases (documentation anchors — not runtime-enforced)
# ---------------------------------------------------------------------------

# Hardware signal category key — must match a key in config/signal_types.json.
# Examples: "pwm_duty", "battery_voltage", "engine_speed", "binary_switch"
SignalTypeKey = str

# AUTOSAR implementation type for the raw integer/boolean representation.
# One of: "uint8", "uint16", "sint16", "sint32", "float32", "boolean"
ImplType = str

# Physical hardware interface type.
# One of: "analog", "digital", "pwm", "can"
HardwareType = str


# ---------------------------------------------------------------------------
# Signal definition — one signal per physical hardware pin/channel
# ---------------------------------------------------------------------------

@dataclass
class SignalDefinition:
    """
    Describes a single hardware signal exposed by a device plugin.

    Typed fields (signal_type, impl_type, bit_width, signed) are validated at
    startup against ``config/signal_types.json`` via ``core.signal_registry``.
    Validation is non-fatal: mismatches produce log warnings, not exceptions.
    """
    # --- Identity ---
    signal_id: str                   # Unique ID within the device (e.g. "J1_01")
    name: str                        # Human-readable name
    type: HardwareType               # Hardware interface: "analog", "digital", "pwm", "can"
    direction: str                   # "input", "output", or "bidirectional"

    # --- Scaling ---
    resolution: float                # Physical units per raw count (e.g. 0.25 rpm/count)

    # --- AUTOSAR / Signal Taxonomy ---
    signal_type: SignalTypeKey = ""  # Registry key in signal_types.json (e.g. "engine_speed")
    impl_type: ImplType        = ""  # AUTOSAR impl type: "uint8", "uint16", "sint16", etc.
    bit_width: int             = 0   # Hardware ADC/DAC bit width (e.g. 12, 16)
    signed: bool               = False  # True if the raw integer is two's-complement signed

    # --- Physical Range & Calibration ---
    unit: str        = ""            # SI unit string (e.g. "rpm", "V", "degC", "%")
    offset: float    = 0.0           # Calibration offset applied during scaling
    min: float       = 0.0           # Minimum valid *physical* value
    max: float       = 0.0           # Maximum valid *physical* value

    # --- Runtime State ---
    value: float     = 0.0           # Most recent raw hardware count
    description: str = ""            # Optional physical connection note
@dataclass(frozen=True)
class CANFrame:
    """
    Represents a single raw CAN frame captured from a hardware interface.
    Immutable value object for safe transport through the system.
    """
    timestamp: float        # Capture timestamp (seconds since epoch)
    bus: str                # Interface ID (e.g., "can0")
    arbitration_id: int     # CAN ID (standard or extended)
    dlc: int                # Data Length Code (0-8 for standard CAN)
    data: bytes             # Raw payload
    is_extended: bool = False
    is_error: bool = False
    is_remote: bool = False

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

    @abstractmethod
    def inject_fault(self, signal_id: str, fault_id: str) -> None:
        """Simulates a hardware fault on a specific signal."""
        raise NotImplementedError("Subclasses must implement the inject_fault method.")

    @abstractmethod
    def clear_fault(self, signal_id: Optional[str] = None) -> None:
        """
        Clears the active fault on a specific signal.
        If signal_id is None, clears all faults on the device.
        """
        raise NotImplementedError("Subclasses must implement the clear_fault method.")

    @abstractmethod
    def get_available_faults(self, signal_id: str) -> List[Dict[str, str]]:
        """Returns a list of supported faults for the specified signal."""
        raise NotImplementedError("Subclasses must implement the get_available_faults method.")

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

    def get_can_interfaces(self) -> List[str]:
        """Returns a list of CAN bus interfaces advertised by this device (e.g. ['can0'])."""
        return []

    def pop_can_frames(self) -> List[CANFrame]:
        """Returns and clears all CAN frames captured since the last call."""
        return []

    def validate_signal_value(self, signal: SignalDefinition, value: Any):
        """Validates that a value is within the physical signal's min/max range."""
        if not (signal.min <= value <= signal.max):
            raise BaseDeviceException(
                f"Hardware value {value} is out of physical bounds for signal '{signal.signal_id}' "
                f"(Range: {signal.min} to {signal.max})",
                code="SIGNAL_OUT_OF_BOUNDS"
            )

class BaseDeviceException(Exception):
    """Base exception class for device-related errors."""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.message = message
        self.code = code

# ---------------------------------------------------------------------------
# Signal Helper Classes for Plugin Developers
# ---------------------------------------------------------------------------

class SignalAnalog(SignalDefinition):
    """Pre-configured SignalDefinition for a standard Analog Voltage input/output."""
    def __init__(self, signal_id: str, name: str, direction: str, **kwargs):
        kwargs.setdefault("type", "analog")
        kwargs.setdefault("signal_type", "sensor_voltage")
        kwargs.setdefault("impl_type", "uint16")
        kwargs.setdefault("bit_width", 12)
        kwargs.setdefault("signed", False)
        kwargs.setdefault("resolution", 0.001)
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("min", 0.0)
        kwargs.setdefault("max", 5.0)
        super().__init__(signal_id=signal_id, name=name, direction=direction, **kwargs)

class SignalPWM(SignalDefinition):
    """Pre-configured SignalDefinition for a PWM duty cycle signal."""
    def __init__(self, signal_id: str, name: str, direction: str, **kwargs):
        kwargs.setdefault("type", "pwm")
        kwargs.setdefault("signal_type", "pwm_duty")
        kwargs.setdefault("impl_type", "uint16")
        kwargs.setdefault("bit_width", 16)
        kwargs.setdefault("signed", False)
        kwargs.setdefault("resolution", 0.00305)
        kwargs.setdefault("unit", "%")
        kwargs.setdefault("min", 0.0)
        kwargs.setdefault("max", 100.0)
        super().__init__(signal_id=signal_id, name=name, direction=direction, **kwargs)

class SignalSwitch(SignalDefinition):
    """Pre-configured SignalDefinition for a binary digital switch."""
    def __init__(self, signal_id: str, name: str, direction: str, **kwargs):
        kwargs.setdefault("type", "digital")
        kwargs.setdefault("signal_type", "binary_switch")
        kwargs.setdefault("impl_type", "boolean")
        kwargs.setdefault("bit_width", 1)
        kwargs.setdefault("signed", False)
        kwargs.setdefault("resolution", 1.0)
        kwargs.setdefault("unit", "")
        kwargs.setdefault("min", 0.0)
        kwargs.setdefault("max", 1.0)
        super().__init__(signal_id=signal_id, name=name, direction=direction, **kwargs)

class SignalCurrent(SignalDefinition):
    """Pre-configured SignalDefinition for a signed current shunt measurement."""
    def __init__(self, signal_id: str, name: str, direction: str, **kwargs):
        kwargs.setdefault("type", "analog")
        kwargs.setdefault("signal_type", "current_shunt")
        kwargs.setdefault("impl_type", "sint16")
        kwargs.setdefault("bit_width", 16)
        kwargs.setdefault("signed", True)
        kwargs.setdefault("resolution", 0.001)
        kwargs.setdefault("unit", "A")
        kwargs.setdefault("min", -32.768)
        kwargs.setdefault("max", 32.767)
        super().__init__(signal_id=signal_id, name=name, direction=direction, **kwargs)

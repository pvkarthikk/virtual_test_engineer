#!/usr/bin/env python3
"""
Virtual Test Engineer - Core Types and Interfaces
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time


class ChannelType(Enum):
    DIGITAL_INPUT = "digital_input"
    DIGITAL_OUTPUT = "digital_output"
    ANALOG_INPUT = "analog_input"
    ANALOG_OUTPUT = "analog_output"
    PWM = "pwm"


class BusType(Enum):
    CAN = "can"
    SERIAL = "serial"
    ETHERNET = "ethernet"


class TestBenchState(Enum):
    IDLE = "idle"
    CONFIGURING = "configuring"
    RUNNING = "running"
    ERROR = "error"


class TestRunStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ChannelValue:
    """Represents a channel reading or setting"""
    channel_id: str
    value: Union[int, float, bool]
    timestamp: str
    quality: str = "good"
    units: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CanMessage:
    """Represents a CAN message"""
    bus_id: str
    message_id: int
    data: List[int]
    timestamp: str
    direction: str  # "tx" or "rx"
    extended_id: bool = False
    dlc: int = 8


@dataclass
class PluginConfig:
    """Plugin configuration"""
    name: str
    type: str
    config: Dict[str, Any]


@dataclass
class ChannelConfig:
    """Channel configuration"""
    id: str
    type: ChannelType
    pin: Optional[int] = None
    scaling: Optional[Dict[str, Any]] = None
    calibration: Optional[Dict[str, Any]] = None


@dataclass
class BusConfig:
    """Bus configuration"""
    id: str
    type: BusType
    bitrate: Optional[int] = None
    interface: Optional[str] = None


@dataclass
class DeviceCapabilities:
    """Device capabilities"""
    digital_inputs: int = 0
    digital_outputs: int = 0
    analog_inputs: int = 0
    analog_outputs: int = 0
    pwm_channels: int = 0
    supported_protocols: List[str] = None

    def __post_init__(self):
        if self.supported_protocols is None:
            self.supported_protocols = []


@dataclass
class ValidationResult:
    """Configuration validation result"""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class DevicePlugin(ABC):
    """Abstract base class for device plugins"""

    @abstractmethod
    async def initialize(self, config: PluginConfig) -> None:
        """Initialize the plugin"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the plugin"""
        pass

    @abstractmethod
    def get_capabilities(self) -> DeviceCapabilities:
        """Get plugin capabilities"""
        pass

    @abstractmethod
    def validate_config(self, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        pass

    @abstractmethod
    async def create_channel(self, channel_id: str, config: ChannelConfig) -> 'Channel':
        """Create a channel instance"""
        pass

    @abstractmethod
    async def destroy_channel(self, channel_id: str) -> None:
        """Destroy a channel instance"""
        pass


class Channel(ABC):
    """Abstract base class for channels"""

    def __init__(self, channel_id: str, config: ChannelConfig):
        self.channel_id = channel_id
        self.config = config

    @abstractmethod
    async def read(self) -> ChannelValue:
        """Read channel value"""
        pass

    @abstractmethod
    async def write(self, value: Union[int, float, bool]) -> None:
        """Write channel value"""
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get channel state"""
        pass


class BusPlugin(ABC):
    """Abstract base class for bus plugins"""

    @abstractmethod
    async def initialize(self, config: BusConfig) -> None:
        """Initialize the bus plugin"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the bus plugin"""
        pass

    @abstractmethod
    async def transmit(self, message: CanMessage) -> None:
        """Transmit a message"""
        pass

    @abstractmethod
    def set_receive_callback(self, callback: callable) -> None:
        """Set callback for received messages"""
        pass


@dataclass
class TestStep:
    """Represents a test step"""
    id: str
    type: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class TestStepResult:
    """Result of executing a test step"""
    step_id: str
    status: str  # "passed", "failed", "skipped"
    start_time: str
    end_time: str
    readings: Dict[str, Any] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.readings is None:
            self.readings = {}


@dataclass
class TestRun:
    """Represents a test run"""
    run_id: str
    scenario_id: str
    status: TestRunStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    parameters: Dict[str, Any] = None
    results: List[TestStepResult] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.results is None:
            self.results = []


def create_timestamp() -> str:
    """Create an ISO timestamp"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
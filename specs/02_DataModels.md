# 02_DataModels.md - Configuration Schema and Data Formats

## Configuration Schema

### Test Bench Configuration (YAML)

```yaml
version: "1.0"
name: "Arduino_ECU_TestBench"

plugins:
  - name: "arduino_gpio"
    type: "gpio"
    config:
      pins: [2, 3, 4, 5, 6, 7, 8, 9]

  - name: "arduino_analog"
    type: "analog"
    config:
      adc_channels: [0, 1, 2, 3]
      dac_channels: []

  - name: "arduino_can"
    type: "can"
    config:
      interface: "can0"
      bitrate: 500000

instruments:
  - id: "throttle_sensor"
    plugin: "arduino_analog"
    type: "adc"
    channel: 0

  - id: "engine_speed_output"
    plugin: "arduino_gpio"
    type: "pwm"
    pin: 9

  - id: "mode_switch"
    plugin: "arduino_gpio"
    type: "digital_input"
    pin: 2

channels:
  - id: "throttle_position"
    instrument: "throttle_sensor"
    scaling:
      input_range: [0, 1023]
      output_range: [0, 100]
      units: "%"

  - id: "engine_speed"
    instrument: "engine_speed_output"
    config:
      frequency: 1000
      duty_cycle_range: [0, 100]
    scaling:
      output_range: [0, 8000]
      units: "rpm"

  - id: "eco_mode"
    instrument: "mode_switch"
    active_high: true

buses:
  - id: "can_bus"
    plugin: "arduino_can"
    bitrate: 500000

dut_profiles:
  - id: "arduino_throttle_ecu"
    channels: ["throttle_position", "engine_speed", "eco_mode"]
    buses: ["can_bus"]
```

## Test Scenario Schema

```yaml
version: "1.0"
id: "throttle_response_basic"
name: "Basic Throttle Response Test"

steps:
  - id: "set_throttle_50"
    type: "set_channel"
    channel: "throttle_position"
    value: 50

  - id: "wait_settle"
    type: "delay"
    duration: 2000

  - id: "read_engine_speed"
    type: "read_channel"
    channel: "engine_speed"
    variable: "engine_speed"

  - id: "assert_response"
    type: "assert"
    condition: "${engine_speed} > 4.5 && ${engine_speed} < 5.5"
    message: "Engine speed not within expected range"

artifacts:
  - type: "csv"
    filename: "throttle_test.csv"
    channels: ["throttle_position", "engine_speed"]
    sample_rate: 10
```

## Pydantic Data Models

### Core Types

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class ChannelType(str, Enum):
    DIGITAL = "digital"
    ANALOG = "analog"
    PWM = "pwm"

class BusType(str, Enum):
    CAN = "can"
    LIN = "lin"
    ETHERNET = "ethernet"

class TestRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
```

### Configuration Models

```python
class PluginConfig(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)

class InstrumentConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    plugin: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    channel: Optional[Union[int, str]] = None
    pin: Optional[int] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class ScalingConfig(BaseModel):
    input_range: Optional[List[float]] = None
    output_range: Optional[List[float]] = None
    units: Optional[str] = None

class ChannelConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    instrument: str = Field(..., min_length=1)
    scaling: Optional[ScalingConfig] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    active_high: bool = True

class BusConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    plugin: str = Field(..., min_length=1)
    bitrate: Optional[int] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class DUTProfile(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = None
    description: Optional[str] = None
    channels: List[str] = Field(default_factory=list)
    buses: List[str] = Field(default_factory=list)

class TestBenchConfig(BaseModel):
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    name: str = Field(..., min_length=1, max_length=100)
    plugins: List[PluginConfig] = Field(default_factory=list)
    instruments: List[InstrumentConfig] = Field(default_factory=list)
    channels: List[ChannelConfig] = Field(default_factory=list)
    buses: List[BusConfig] = Field(default_factory=list)
    dut_profiles: List[DUTProfile] = Field(default_factory=list)
```

### Test Scenario Models

```python
class TestStep(BaseModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    channel: Optional[str] = None
    value: Optional[Any] = None
    variable: Optional[str] = None
    duration: Optional[float] = None
    condition: Optional[str] = None
    message: Optional[str] = None
    steps: Optional[List['TestStep']] = None
    values: Optional[List[Any]] = None

class ArtifactConfig(BaseModel):
    type: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    channels: List[str] = Field(default_factory=list)
    sample_rate: Optional[float] = None

class TestScenario(BaseModel):
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    steps: List[TestStep] = Field(default_factory=list)
    artifacts: List[ArtifactConfig] = Field(default_factory=list)
```

### API Response Models

```python
class ChannelInfo(BaseModel):
    id: str
    type: str
    instrument: str
    last_value: Optional[Any] = None
    last_read_time: Optional[datetime] = None
    scaling: Optional[ScalingConfig] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class BusInfo(BaseModel):
    id: str
    type: str
    plugin: str
    is_connected: bool = False
    bitrate: Optional[int] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class PluginInfo(BaseModel):
    name: str
    type: str
    status: str  # "loaded", "initialized", "error"
    supported_channel_types: List[str]
    supported_bus_types: List[str]
    config: Dict[str, Any]

class StepResult(BaseModel):
    step_id: str
    status: str  # "passed", "failed", "skipped"
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    readings: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class TestRun(BaseModel):
    run_id: str
    scenario_id: str
    status: TestRunStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    steps: List[StepResult] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    error: Dict[str, Any]

class ValidationResult(BaseModel):
    valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
```
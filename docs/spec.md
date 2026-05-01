

# Software Defined Test Bench - Requirements Document

## 1. Project Overview

### 1.1 Project Identification
- **Project Name**: Software Defined Test Bench (SDTB)
- **Project Type**: Test automation/validation framework
- **Core Functionality**: A flexible, software-defined approach to test bench automation for hardware validation
- **Target Users**: 
  - Test Engineers
  - Hardware Developers
  - QA Teams
  - Validation Engineers
  - System Integrators

### 1.2 Vision Statement
To provide a unified, programmable interface for hardware validation that abstracts hardware complexity through software-defined interfaces, enabling rapid test development and execution.

### 1.3 Key Benefits
- Reduced test development time through reusable components
- Hardware abstraction layer for technology independence
- Scalable architecture supporting multiple device types
- Standardized interfaces for consistent test execution
- Real-time monitoring and control capabilities

## 2. System Architecture

### 2.1 Design Considerations

#### 2.1.1 Why REST API?

| Consideration | Rationale |
|---------------|-----------|
| **Ubiquitous Standard** | REST APIs are widely adopted across the industry, making integration with existing tools, CI/CD pipelines, and third-party systems straightforward |
| **Stateless Operations** | Each request is independent, enabling easier scaling, debugging, and load balancing |
| **Tooling Ecosystem** | Extensive off-the-shelf tooling available (Postman, curl, API clients) reduces custom client development effort |
| **HTTP Semantics** | Leverages standard HTTP methods (GET, POST, PUT, DELETE) for intuitive interface design |
| **Platform Independence** | Works across all platforms and programming languages without client-side dependencies |
| **Firewall Friendliness** | Uses standard ports (80/443) that typically pass through firewalls without special configuration |
| **Monitoring & Caching** | Benefits from existing HTTP infrastructure for monitoring, caching, and load balancing |

#### 2.1.2 Why MCP (Model Context Protocol)?

| Consideration | Rationale |
|---------------|-----------|
| **Contextual Awareness** | MCP provides rich context management that goes beyond simple request-response, enabling smarter test orchestration |
| **AI/ML Integration** | Designed to work with AI/ML systems for intelligent test automation and optimization |
| **Tool Abstraction** | MCP can wrap multiple backend systems (REST, gRPC, custom) under a unified interface |
| **Enhanced Capabilities** | Supports features like streaming responses, subscriptions, and bidirectional communication |
| **Standardized Interface** | Provides a standardized way for AI assistants to interact with test infrastructure |
| **Future Proofing** | Positions the system for integration with emerging AI-driven development workflows |

#### 2.1.3 Why Python?

| Consideration | Rationale |
|---------------|-----------|
| **Extensive Libraries** | Rich ecosystem of libraries for hardware communication (pySerial, pyUSB, GPIO libraries), test frameworks (pytest), and data analysis |
| **Hardware Integration** | Excellent support for various hardware interfaces including GPIO, I2C, SPI, UART, USB, and SCPI protocols |
| **FastAPI/Flask Support** | Mature web frameworks (FastAPI, Flask) with excellent async support for high-performance APIs |
| **Community & Support** | Large community in test automation and hardware programming spaces |
| **Learning Curve** | Simple, readable syntax that reduces onboarding time for new team members |
| **Cross-Platform** | Runs natively on Windows, Linux, macOS without code changes |
| **Async Support** | Native asyncio support for handling concurrent operations efficiently |
| **MCP Compatibility** | Good ecosystem support for MCP protocol implementation in Python |
| **Scripting Flexibility** | Ideal for rapid prototyping and automation scripts alongside the API |

#### 2.1.4 Alternative Technologies Considered

| Technology | Considered And Rejected | Reason for Rejection |
|------------|------------------------|---------------------|
| Node.js/Express | Yes | Less hardware library support compared to Python; team expertise preference |
| gRPC | No (complementary) | Binary format not as accessible for manual testing; better suited for internal service communication |
| GraphQL | No | Overkill for test automation use cases; adds unnecessary complexity for our read-heavy patterns |
| C/C++ | No | Slower development cycle; less productive for web/API layer; hardware-specific code can be added later |

#### 2.1.5 Extensibility Model

SDTB supports user-defined devices through an extensible plugin architecture:

| Component | Description | Location |
|-----------|------------|----------|
| BaseDevice | Base Python class that users extend to create custom devices | Built-in |
| BaseFlash | Base Python class that users extend to create custom flashing protocols | Built-in |
| BaseDeviceException | Exception class for device plugin errors | Built-in |
| Device Plugins | User-created device implementations (device_*.py) | User's SDTB device directory |
| Flash Plugins | User-created flashing protocols (flash_*.py) | User's SDTB device directory |
| system.json | System-level configuration (server settings, device directory path) | User's AppData/SDTB directory |
| device_<name>.json | Per-device configuration file (connection params, settings) co-located with plugin | User's SDTB device directory |
| flash_<name>.json | Per-protocol configuration file (timeouts, retry logic) co-located with plugin | User's SDTB device directory |
| channels.json | Channel-to-signal mappings with independent properties | User's AppData/SDTB directory |
| ui.json | UI dashboard layout and widget-to-channel mappings | User's AppData/SDTB directory |

**Plugin Discovery Mechanism**

- System scans device directory for files matching pattern `device_*.py` and `flash_*.py`
- Each plugin file must have a corresponding `.json` configuration file (`device_*.json` or `flash_*.json`)
- Device files must contain a class extending `BaseDevice`
- Flash files must contain a class extending `BaseFlash`
- Each plugin class auto-loads its own configuration at startup
- **Singleton Guard**: The core `SDTBSystem` uses a dedicated `initialized` flag to prevent partial or duplicate re-initialization during rapid restart cycles
- Components are auto-detected and registered at system startup
- Available via `/device` and `/flash` endpoints without any configuration changes

**BaseDevice Class Interface**

The BaseDevice abstract class defines the contract for all device plugins:

```python
class BaseDevice(ABC):
    @property
    @abstractmethod
    def vendor(self) -> str: pass

    @property
    @abstractmethod
    def model(self) -> str: pass

    @property
    @abstractmethod
    def firmware_version(self) -> str: pass

    @abstractmethod
    def connect(self, connection_params: dict) -> None: pass

    @abstractmethod
    def disconnect(self) -> None: pass

    @abstractmethod
    def get_signals(self) -> List[SignalDefinition]: pass

    @abstractmethod
    def read_signal(self, signal_id: str) -> Any: pass

    @abstractmethod
    def write_signal(self, signal_id: str, value: Any) -> None: pass

    @abstractmethod
    def restart(self) -> None:
        """Restarts the hardware device."""
        pass

    def update(self) -> None:
        """Called periodically based on system device_update_rate. Override to implement background tasks."""
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
```

**BaseFlash Class Interface**

The BaseFlash abstract class defines the contract for all flashing protocol plugins:

```python
class BaseFlash(ABC):
    @property
    @abstractmethod
    def vendor(self) -> str: pass

    @property
    @abstractmethod
    def model(self) -> str: pass

    @abstractmethod
    def connect(self, connection_params: dict) -> None: pass

    @abstractmethod
    def disconnect(self) -> None: pass

    @abstractmethod
    def flash(self, data: bytes, params: dict) -> str:
        """Initiates flash and returns execution_id."""
        pass

    @abstractmethod
    def get_status(self, execution_id: str) -> dict:
        """Returns current status and progress (0-100)."""
        pass

    @abstractmethod
    def abort(self, execution_id: str) -> None:
        """Aborts the ongoing flash operation."""
        pass

    @abstractmethod
    def get_log(self, execution_id: str) -> List[str]:
        """Returns the log messages for a specific flash execution."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Returns True if the flashing protocol is enabled."""
        pass

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool):
        """Sets the enabled state of the flashing protocol."""
        pass
```

**SignalDefinition**

Describes the metadata and physical characteristics of a device signal:

```python
@dataclass
class SignalDefinition:
    signal_id: str        # Unique identifier within the device
    name: str             # Human-readable signal name
    type: str             # Signal type (validated against config/signal_types.json)
    direction: str        # "input", "output", or "bidirectional"
    resolution: int       # Number of bits or smallest increment
    unit: str             # Measurement unit (e.g., "V", "mA", "%")
    offset: float         # Calibration offset
    min: float            # Minimum valid range value
    max: float            # Maximum valid range value
    value: float          # Initial or last known value
    description: str      # Physical connection info (e.g., "J1-Pin3", "ECU Connector A, Pin 12")

# Helper classes for rapid plugin development
class SignalAnalog(SignalDefinition): pass
class SignalPWM(SignalDefinition): pass
class SignalSwitch(SignalDefinition): pass
class SignalCurrent(SignalDefinition): pass
```

**BaseDeviceException**

Custom exception for device plugin errors. Raised by plugin developers and captured by REST layer to report meaningful errors to API consumers.

```python
class BaseDeviceException(Exception):
    def __init__(self, message: str, code: str = None): pass
```

**BaseFlashException**

Custom exception for flashing protocol errors. Raised by protocol developers during connection or flashing operations to report specific failures (e.g., "Handshake Timeout", "CRC Mismatch").

```python
class BaseFlashException(Exception):
    def __init__(self, message: str, code: str = None): pass
```

**Configuration Files**

SDTB uses independent configuration files for fault isolation. Each file is backed up (`.bak`) before every write. On startup, if a file is corrupted, the system falls back to its `.bak` copy. If both are corrupted, a fresh default is created and a warning is logged.

**system.json** — System-level settings:

```json
{
  "device_directory": "C:\\Users\\<user>\\SDTB\\devices",
  "device_update_rate": 100, // Valid range: 10ms to 5000ms. Guards against CPU exhaustion and division-by-zero.
  "server": {
    "host": "127.0.0.1",
    "port": 8080
  }
}
```

**device_<name>.json** — Per-device configuration (co-located with device_<name>.py in device directory):

```json
{
  "id": "device_keysight_dmm",
  "plugin": "KeysightDMMPlugin",
  "enabled": true,
  "connection_params": { "ip_address": "192.168.1.10" },
  "settings": {}
}
```

Note: Each device plugin (`device_<name>.py`) has a corresponding `device_<name>.json` in the same directory. The device class auto-loads its own configuration file at startup. If the JSON file is missing, a default is created.

**channels.json** — Channel-to-signal mappings:

```json
[
  {
    "channel_id": "ch_temperature_1",
    "device_id": "device_1",
    "signal_id": "AI0",
    "properties": {
      "unit": "\u00b0C",
      "min": -40.0,
      "max": 150.0,
      "conversion": {
        "type": "lut",
        "table": [ [100.0, 150.0], [4000.0, -40.0] ]
      },
      "value": 0.0
    }
  }
]
```

**ui.json** — UI dashboard layout and widget-to-channel mappings:

```json
{
  "layout": "dashboard",
  "widgets": [
    {
      "id": "w1",
      "type": "gauge",
      "channel": "ch_temperature_1",
      "label": "Engine Temperature",
      "position": { "row": 0, "col": 0 }
    },
    {
      "id": "w2",
      "type": "slider",
      "channel": "ch_voltage_1",
      "label": "Supply Voltage",
      "min": 0,
      "max": 5.0,
      "position": { "row": 0, "col": 1 }
    }
  ]
}
```

### 2.2 High-Level Architecture
```
+----------------------+
|   MCP Server Layer   |  ← Wrapper Layer (Python)
+----------------------+
|   REST API Layer     |  ← Base Layer (Python)
+----------------------+
|   Hardware Abstraction Layer |
+----------------------+
|   Device Drivers     |
+----------------------+
|   Physical Hardware  |
+----------------------+
```

### 2.3 Architectural Components

#### 2.3.1 Base Layer: REST API Endpoint
- **Technology**: Python-based REST API (FastAPI/Flask)
- **Purpose**: Core functionality exposure through standardized HTTP endpoints
- **Responsibilities**:
  - Device management and discovery
  - Test execution control
  - Signal I/O operations
  - Flashing operations
  - System status reporting

#### 2.3.2 Wrapper Layer: MCP Server
- **Technology**: Model Context Protocol server implementation
- **Purpose**: Enhanced interface layer providing contextual awareness and advanced capabilities
- **Responsibilities**:
  - Context-aware test orchestration
  - Advanced parameter validation
  - Test result interpretation
  - Integration with AI/ML test optimization
  - Enhanced error handling and diagnostics

#### 2.3.3 Technology Stack
- **Primary Language**: Python 3.8+
- **REST Framework**: FastAPI (Recommended) or Flask
- **MCP Implementation**: Custom or standard MCP library
- **Async Support**: AsyncIO for concurrent operations
- **Documentation**: OpenAPI/Swagger for API docs

## 3. Feature Requirements

### 3.1 Feature Map

| Feature ID | Feature Name | Priority | Status |
|------------|--------------|----------|--------|
| F01 | System Management | High | Implemented |
| F02 | Device Management | High | Implemented |
| F03 | Signal Management | High | Implemented |
| F04 | Channel Management | High | Implemented |
| F05 | Software Flashing | Low | Defined |
| F06 | Test Execution & Control | High | Implemented |
| F07 | User Interface (UI) | Medium | Implemented |
| F08 | Agentic Control (MCP) | Medium | Implemented |
| F09 | Fault Injection | Low | Defined |

### 3.1.1 Feature Descriptions

- **System**: The core SDTB infrastructure handles the global configuration, hardware connection lifecycles, health status, and logging. It acts as the backbone that loads configuration files (`system.json`, `channels.json`, and per-device `device_<name>.json`), instantiates device drivers, and manages role-based access. Through the `/system` endpoints, administrators can cleanly connect or disconnect the entire test bench in one go.

- **Device**: Physical hardware instruments (e.g., multimeters, power supplies, CAN sniffers) are represented as software "Devices" in the system. The Device Management feature is responsible for discovering these plugin drivers dynamically on startup, tracking their health, and managing their configurations.

- **Signal**: The raw electrical or data communication capabilities owned by a specific Device. The Signal Management feature provides the read/write capabilities across various domains (e.g., analog voltage, digital high/low, PWM duty cycle, or CAN bus messages) directly on the physical hardware.

- **Channel**: A logical abstraction of physical signals. The Channel Management feature abstracts distinct vendor-specific device signals into a unified pool of logical pathways (Channels) so tests remain technology-agnostic.

- **Flashing**: The critical process of uploading and programming large firmware or software binaries onto a target Electronic Control Unit (ECU). The Software Flashing feature ensures that these large files can be safely uploaded via `multipart/form-data`. To prevent Out-Of-Memory (OOM) errors, the system enforces a **10MB file size cap** and performs a dual-layer size check (HTTP `file.size` and raw `len(data)`).

- **Tests**: Programmable scripts (e.g., JSONL) executed by the framework to automatically orchestrate channels and flashing.

- **UI**: A browser-based dashboard served directly by the SDTB server. The User Interface feature provides a visual control panel where users can map widgets (gauges, sliders, buttons, LEDs, etc.) to channels, control system lifecycle (connect/disconnect/restart), monitor live signal activity in a debug window, and edit/execute test scripts — all without writing any API calls manually. The Test Execution & Control feature manages the complete lifecycle of these automated sequences—allowing users to discover available tests, pass dynamic parameters, run them asynchronously, and retrieve detailed pass/fail measurement logs upon completion.

- **MCP**: A built-in Model Context Protocol server that enables AI agents to autonomously discover, monitor, and control the test bench. By exposing hardware as a set of standardized "Tools" (like `read_channels` and `write_channels`), agents can execute complex test scenarios, interpret sensor data, and drive actuators using natural language reasoning.

- **Fault Injection**: Simulates hardware or communication failures (e.g., shorts, opens, signal corruption) to validate the target system's diagnostic and safety mechanisms.

### 3.2 Domain Concepts

#### 3.2.1 Device and Signal Relationship

Each device has its own signal capabilities (e.g., an NI device may have different signals than a Keysight device). Devices and signals are bundled together - signals are defined as part of device capabilities.

#### 3.2.2 Channel Abstraction Layer

Channels are user-facing abstractions that represent logical I/O points on the test bench, decoupled from the underlying physical devices. Users interact with channels, not directly with devices/signals.

#### 3.2.3 Signal-to-Channel Mapping

Users can map a channel to any available signal on any connected device. This provides maximum flexibility for test setup and hardware adaptation:
- Channel A on the test bench can map to "PWM Output" on Device 1
- Channel B on the test bench can map to "CAN" on Device 2
- Channel configuration is independent of the underlying device

#### 3.2.4 Value Validation

The system shall validate values against the min/max range defined by the target before any write operation. This applies at both the raw signal level (F03) and the channel abstraction level (F04). Each layer may define its own valid range independently — a channel may expose a narrower or shifted range compared to the underlying device signal.

### 3.3 Feature Details

#### F01: System Management

**Description**: Provide system-level control and monitoring capabilities for the SDTB infrastructure itself.

**API Endpoints**

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/system` | GET | Retrieve overall system health, status, and version information | 200 OK |
| `/system/connect` | POST | Connect all configured hardware devices | 200 OK, 503 Service Unavailable |
| `/system/disconnect` | POST | Gracefully disconnect all hardware devices | 200 OK, 503 Service Unavailable |
| `/system/config` | GET | Retrieve current system configuration (system.json) | 200 OK |
| `/system/config` | PUT | Update system configuration file (system.json) | 200 OK, 400 Bad Request |
| `/system/config/channels` | GET | Retrieve channel-to-signal mapping configuration | 200 OK |
| `/system/config/channels` | PUT | Configure which channel maps to which device signal | 200 OK, 400 Bad Request |
| `/system/diagnostics` | GET | Run system diagnostics and return health report | 200 OK, 503 Service Unavailable |
| `/system/metrics` | GET | Retrieve system performance metrics | 200 OK |
| `/system/restart` | POST | Restart the system (auto-disconnect, re-initialize, re-discover) | 200 OK, 503 Service Unavailable |
| `/system/stream` | GET | Multiplexed SSE stream for real-time logs, channel values, and device signal updates over a single connection | 200 OK |

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F01.01 | System shall provide a base endpoint (/system) indicating overall operational readiness and version information | High | Integration Test |
| F01.02 | User shall be able to connect/disconnect hardware devices gracefully | High | Integration Test |
| F01.03 | System shall maintain configuration persistence across restarts using independent config files (system.json, channels.json, and per-device device_<name>.json) | High | Integration Test |
| F01.04 | System shall provide diagnostic capabilities for troubleshooting | Medium | Integration Test |
| F01.05 | System shall expose performance metrics (throughput, latency, resource utilization) | Low | Integration Test |
| F01.06 | System shall handle graceful degradation when subsystems fail | Medium | Integration Test |
| F01.07 | System shall provide connect/disconnect sequencing to ensure proper hardware initialization | High | Integration Test |
| F01.08 | User shall be able to configure channel-to-device-signal mappings via /system/config/channels endpoint | High | Integration Test |
| F01.09 | Channel configuration shall persist across system restarts | High | Integration Test |
| F01.10 | System shall expose a `/system/diagnostics` endpoint for internal health checks. | Low (Planned) | Unit Test |
| F01.11 | System shall expose a `/system/metrics` endpoint for Prometheus-style monitoring. | Low (Planned) | Integration Test |
| F01.12 | System shall implement Role-Based Access Control (RBAC) for API endpoints. | Medium (Planned) | Security Audit |
| F01.13 | System shall maintain an audit log of all hardware-mutating operations. | Medium (Planned) | Security Audit |
| F01.14 | User shall be able to restart the system via /system/restart (auto-disconnect, re-initialize, re-discover) | High | Integration Test |
| F01.15 | System shall provide live log streaming via SSE for real-time command and event monitoring | Medium | Integration Test |

#### F02: Device Management

**Description**: Manage physical hardware instruments, their auto-discovery, and operational status.

**API Endpoints**

| Endpoint | Method | Description | Response Object | Status Codes |
|----------|--------|-------------|-----------------|--------------|
| `/device` | GET | Retrieve list of all available devices | List[DeviceStatus] | 200 OK |
| `/device/{device_id}/toggle` | POST | Enable or disable a device and save state to config | Message | 200 OK, 404 Not Found |
| `/device/{device_id}` | GET | Retrieve detailed information for specific device | DeviceDetail | 200 OK, 404 Not Found |
| `/device/{device_id}/status` | GET | Retrieve current operational status of device | DeviceStatus | 200 OK, 404 Not Found |
| `/device/{device_id}/restart` | POST | Restart the hardware device | Message | 200 OK, 500 Internal Error |

**DeviceStatus / DeviceDetail Properties**

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique device identifier specified in config |
| `vendor` | String | Device manufacturer (from plugin) |
| `model` | String | Device model (from plugin) |
| `firmware_version`| String | Current firmware version of the hardware |
| `status` | String | Connection state: `online`, `connected`, or `offline` |
| `enabled` | Boolean | Whether the device is software-enabled |
| `plugin` | String | Internal module name of the device driver |

Note: Devices are auto-detected from device directory at startup. POST /device is removed - device registration happens automatically via plugin discovery.

Note: Each device's configuration is stored in its own `device_<name>.json` file co-located with the plugin file. The device class auto-loads its own configuration at startup.

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F02.01 | System shall provide device discovery mechanism to enumerate available devices | High | Integration Test |
| F02.02 | Each device shall expose unique identifier and human-readable name | High | Unit Test |
| F02.03 | System shall maintain device metadata including vendor, model, capabilities, firmware version | Medium | Integration Test |
| F02.04 | Devices shall be grouped by type/functionality for easier management | Medium | Integration Test |
| F02.05 | System shall support hot-plugging of devices where hardware permits | Low | Integration Test |
| F02.06 | Device status shall include operational state (idle, busy, error, offline) | High | Integration Test |
| F02.07 | System shall provide health monitoring for connected devices | Medium | Integration Test |
| F02.08 | System shall provide BaseDevice Python class for user to extend | High | Unit Test |
| F02.09 | User devices shall use naming pattern device_*.py in device directory | High | Integration Test |
| F02.10 | User devices shall be auto-detected at system startup | High | Integration Test |
| F02.11 | Each device plugin (device_<name>.py) shall have a corresponding device_<name>.json in the device directory | High | Integration Test |
| F02.12 | device_<name>.json shall contain device instance configuration (connection params, settings) | High | Integration Test |
| F02.13 | If device_<name>.json not found, system shall create one with default values | High | Integration Test |
| F02.14 | Each device shall expose its own signal types as part of device capabilities | High | Integration Test |
| F02.15 | BaseDeviceException shall be used by plugin developers for error handling | High | Unit Test |
| F02.16 | System shall allow enabling/disabling devices individually via API, persisting state in device config | High | Integration Test |
| F02.17 | Hardware drivers shall use the standard `logging` module to ensure internal driver events are visible in the global SSE stream | Medium | Integration Test |

#### F03: Signal Management

**Description**: Provide comprehensive control and monitoring capabilities for various signal types originating from or targeting connected devices.

**Supported Signal Types**

| Signal Type | Description | Typical Use Cases |
|-------------|-------------|-------------------|
| Passive Analog | Passive analog signal input (voltage sensing without excitation) | Voltage monitoring, sensor reading without excitation |
| Active Analog | Active analog signal input/output (with excitation) | Thermistor, RTD sensors, load simulation |
| Switch to Ground | Digital input that switches to ground reference | Button inputs, ground-referenced switches |
| Switch to Battery | Digital input that switches to battery/reference voltage | Battery-referenced switches, high-side sensing |
| PWM Input | Pulse Width Modulation signal input | Reading PWM output from external devices |
| PWM Output | Pulse Width Modulation signal output generation | Motor control, LED dimming, actuator control |
| Frequency/Speed Signal (VR) | Variable Reluctor signal input (sine wave from VR sensor) | Wheel speed, crank position, speed sensing |
| Frequency/Speed Signal (Hall) | Hall effect sensor signal input (digital square wave) | Wheel speed, RPM sensing, position detection |
| Low Side Driver | Low-side switching driver (ground switching) | Relay control, solenoid drive, load switching |
| High Side Driver | High-side switching driver (positive voltage switching) | Battery-connected loads, fused outputs |
| CAN | Controller Area Network communication | Vehicle network, ECU communication, diagnostics |
| LIN | Local Interconnect Network communication (TBD - future support) | Simple vehicle sensors, body electronics |
| SENT | Single Edge Nibble Transmission (TBD - future support) | High-resolution sensor communication |

**Signal Properties**

Each raw signal shall expose the following properties to define its physical characteristics:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `resolution` | Integer | Number of bits or smallest increment | 12 (bits), 0.001 (V) |
| `unit` | String | Measurement unit | "V", "mA", "%", "Hz" |
| `offset` | Float | Calibration offset applied to raw value | 0.0, -0.05 |
| `min` | Float | Minimum valid range value | 0.0, -10.0 |
| `max` | Float | Maximum valid range value | 3.3, 10.0, 100.0 |
| `value` | Float | Initial or last known value | 0.0, 2.5 |
| `description` | String | Physical connection info (pin, connector, wiring notes) | "J1-Pin3", "ECU Connector A, Pin 12" |

**API Endpoints**

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/device/{device_id}/signal` | GET | Retrieve a list of all available signals for the device | 200 OK, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}` | PUT | Write to a raw device signal using a `WriteValue` request body (Pydantic validated) | 200 OK, 400 Bad Request, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}` | GET | Read a raw device signal | 200 OK, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}/info` | GET | Retrieve signal metadata and properties (resolution, unit, min, max, offset) | 200 OK, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}/fault` | GET | Retrieve a list of available fault simulation capabilities for this specific signal | 200 OK, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}/fault` | POST | Activate a specific fault simulation on the signal (requires `fault_id` in JSON payload) | 200 OK, 400 Bad Request, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}/fault` | DELETE | Clear any active fault on the signal and restore normal operation | 200 OK, 404 Not Found |

> **TODO**: Streaming endpoints for LIN and SENT are placeholders for future support. Will be reviewed later.

> **TODO**: Signal streaming implementation details (keepalive, reconnection, termination) are pending review.

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F03.01 | User shall be able to configure analog signal output parameters (voltage/current range, precision) | High | Integration Test |
| F03.02 | User shall be able to read analog signal input with configurable sampling rates | High | Integration Test |
| F03.03 | System shall support both single-ended and differential analog signal modes where hardware permits | Medium | Integration Test |
| F03.04 | User shall be able to set digital signal output states (high/low) | High | Integration Test |
| F03.05 | User shall be able to read digital signal input states with debouncing configuration | High | Integration Test |
| F03.06 | User shall be able to configure PWM signal parameters (frequency, duty cycle, polarity) | High | Integration Test |
| F03.07 | User shall be able to read PWM signal input measurements (frequency, duty cycle) | High | Integration Test |
| F03.08 | System shall support real-time signal streaming via the multiplexed `/system/stream` endpoint | Medium | Integration Test |
| F03.09 | Signal configuration shall validate against the Signal Registry (`config/signal_types.json`) | High | Unit Test |
| F03.10 | System shall provide signal buffering capabilities for oscilloscope generation/capture where supported | Low | Integration Test |
| F03.11 | All signal operations shall be timestamped for synchronization purposes | Medium | Integration Test |
| F03.12 | System shall support signal triggering capabilities (external trigger sources) | Low | Integration Test |
| F03.13 | LIN streaming endpoint to be implemented (TBD) | TBD | TBD |
| F03.14 | SENT signal support (TBD - placeholder for future) | TBD | TBD |
| F03.15 | Users typically interact with channels (logical), but can optionally use raw device signals via `signal_id` for advanced scenarios or debugging | High | Contract Test |

#### F04: Channel Management

**Description**: Abstract specific hardware device signals into logical pathways (Channels) so tests remain technology-agnostic.

**Core Principle**: No breaking API changes required for device channel additions, modifications, or removals.

**API Endpoints**

Note: Channel endpoints are for reading and writing logical signal values. Channel configuration (mapping channel to device signal) is handled via `/system/config/channels`.

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/channel` | GET | List all available channels across all devices | 200 OK |
| `/channel/{channel_id}` | GET | Read signal value from channel | 200 OK, 404 Not Found |
| `/channel/{channel_id}` | PUT | Write signal value to channel using a `WriteValue` request body (Pydantic validated) | 200 OK, 400 Bad Request, 404 Not Found |
| `/channel/{channel_id}/info` | GET | Retrieve detailed meta information about channel | 200 OK, 404 Not Found |
| `/channel/{channel_id}/status` | GET | Retrieve current status of channel | 200 OK, 404 Not Found |

**Channel Properties**

Each channel shall expose the following properties for proper signal handling:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `conversion` | Object | The conversion strategy (linear, polynomial, lut) | `{"type": "linear", "resolution": 1.0}` |
| `unit` | String | Measurement unit | "V", "mA", "%", "Hz" |
| `min` | Float | Minimum valid range value | 0.0, -10.0 |
| `max` | Float | Maximum valid range value | 3.3, 10.0, 100.0 |
| `value` | Float | Initial or last known value | 0.0, 2.5 |


**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F04.01 | Adding new device channels shall require zero changes to existing REST API consumers | High | Contract Test |
| F04.02 | Modifying existing device channels shall require zero changes to existing REST API consumers for compatible changes | High | Contract Test |
| F04.03 | Removing device channels shall require zero changes to existing REST API consumers (graceful degradation - channel returns offline/error status) | High | Contract Test |
| F04.04 | Each channel shall expose resolution property indicating measurement precision | High | Unit Test |
| F04.05 | Each channel shall expose unit property indicating measurement unit | High | Unit Test |
| F04.06 | Each channel shall expose offset property for calibration | Medium | Unit Test |
| F04.07 | Each channel shall expose min property indicating minimum valid range | High | Unit Test |
| F04.08 | Each channel shall expose max property indicating maximum valid range | High | Unit Test |
| F04.09 | Users shall be able to dynamically map any available device signal to any channel through software configuration | High | Integration Test |
| F04.10 | Users shall see channels (user-facing) not raw device signals | High | Unit Test |

#### F05: Software Flashing

**Description**: Enable users to flash firmware/software to target devices through programmable endpoints with full lifecycle management capabilities.

**API Endpoints**

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/flash/connect` | POST | Connect to the flash target device/ECU (independent of system connect) | 200 OK, 400 Bad Request, 503 Service Unavailable |
| `/flash/disconnect` | POST | Disconnect from the flash target device/ECU | 200 OK, 503 Service Unavailable |
| `/flash` | POST | Initiate software flashing process (supports multipart/form-data for ≤10MB files) | 202 Accepted, 400 Bad Request, 500 Internal Error |
| `/flash/status` | GET | Retrieve current flashing operation status | 200 OK, 404 Not Found |
| `/flash/log` | GET | Stream live flash operation logs via SSE | 200 OK, 404 Not Found |
| `/flash/abort` | POST | Abort ongoing flashing operation | 200 OK, 409 Conflict, 404 Not Found |
| `/flash/history` | GET | Retrieve flashing operation history | 200 OK |

Note: Flash connection is independent of `/system/connect`. The flash target must be connected via `/flash/connect` before any flashing operation can be initiated.

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F05.01 | User shall be able to connect/disconnect to flash target independently of system device connections | High | Integration Test |
| F05.02 | User shall be able to initiate software flashing via REST API endpoint | High | Integration Test |
| F05.03 | System shall return unique flash operation ID upon initiation | High | Unit Test |
| F05.04 | User shall be able to query real-time flashing progress/status | High | Integration Test |
| F05.05 | System shall support pausing/resuming flashing operations where hardware permits | Medium | Integration Test |
| F05.06 | User shall be able to abort ongoing flashing operations safely | High | Integration Test |
| F05.07 | System shall validate flashing parameters before initiation | High | Unit Test |
| F05.08 | System shall provide detailed flash completion reports including success/failure reasons | Medium | Integration Test |
| F05.09 | User shall be able to retrieve meta information of currently/last flashed software | High | Integration Test |
| F05.10 | System shall maintain flash operation history for audit trails | Low | Integration Test |
| F05.11 | Flashing operations shall be device-specific with proper device validation | High | Integration Test |
| F05.12 | System shall provide live flash operation logs via SSE streaming | Medium | Integration Test |
| F05.13 | System shall provide BaseFlash Python class for user to extend custom protocols | High | Unit Test |
| F05.14 | Flashing protocol plugins (flash_*.py) shall be auto-detected at startup | High | Integration Test |

**Non-Functional Requirements**
- Flash operations shall support progress reporting (percentage complete)
- System shall enforce a **10MB maximum file size** for firmware uploads to ensure server stability
- Flash timeout configuration shall be configurable per device type
- System shall verify firmware integrity post-flash when supported by hardware

#### F06: Test Execution & Control

**Description**: Manage the complete lifecycle of test execution from initiation through completion with result retrieval and test abortion capabilities.

**API Endpoints**

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/test` | GET | Retrieve list of available test definitions | 200 OK |
| `/test` | POST | Upload or create a new test definition | 201 Created, 400 Bad Request |
| `/test/{test_id}` | GET | Retrieve details of a specific test definition | 200 OK, 404 Not Found |
| `/run` | POST | Initiate new test execution (accepts test script as JSONL) and return execution ID | 202 Accepted, 400 Bad Request, 409 Conflict |
| `/run/test/{test_id}` | POST | Initiate execution of an existing test definition and return execution ID | 202 Accepted, 400 Bad Request, 404 Not Found |
| `/run/{execution_id}` | GET | Retrieve status and progress of specific test execution | 200 OK, 404 Not Found |
| `/run/{execution_id}/results` | GET | Retrieve results of completed test execution | 200 OK, 404 Not Found, 202 Accepted (if still running) |
| `/run/{execution_id}/abort` | POST | Abort ongoing test execution | 200 OK, 409 Conflict, 404 Not Found |
| `/run/{execution_id}/pause` | POST | Pause test execution (if supported) | 200 OK, 409 Conflict, 404 Not Found |
| `/run/{execution_id}/resume` | POST | Resume paused test execution (if supported) | 200 OK, 409 Conflict, 404 Not Found |
| `/run` | GET | List test execution history with filtering options | 200 OK |
| `/run/{execution_id}/logs` | GET | Retrieve execution logs for specific test | 200 OK, 404 Not Found |

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F06.01 | User shall be able to initiate test execution via REST API and receive unique test identifier | High | Integration Test |
| F06.02 | System shall maintain test execution queue; only one test runs at a time, additional requests are queued | High | Integration Test |
| F06.03 | User shall be able to monitor real-time test execution status and progress | High | Integration Test |
| F06.04 | System shall provide detailed test execution results including pass/fail status, measurements, and timing | High | Integration Test |
| F06.05 | User shall be able to abort ongoing test executions safely and cleanly | High | Integration Test |
| F06.06 | System shall support test pausing and resuming where test design permits | Medium | Integration Test |
| F06.07 | Only one active session permitted at any time; multiple run requests within a session shall be queued | High | Integration Test |
| F06.08 | System shall maintain a test execution history, capped at the **last 1000 results** to prevent memory leaks during long-running automation | Medium | Integration Test |
| F06.09 | System shall capture and store execution logs for debugging purposes | Medium | Integration Test |
| F06.10 | Test definitions shall be referenced by ID or name, allowing for version management | High | Integration Test |
| F06.11 | System shall support parameterized test execution with runtime variable substitution | Medium | Integration Test |
| F06.12 | Test timeout values shall be configurable per test definition | High | Integration Test |

> **TODO**: Assert pass/fail behavior in test execution - to be reviewed later. Currently test steps execute sequentially but assertion failure handling is not specified.

#### F07: User Interface (UI)

**Description**: Provide a browser-based dashboard served by the SDTB server that enables visual system control, channel-widget mapping, live monitoring, and test script editing without direct API interaction.

**API Endpoints**

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/ui` | GET | Serve the browser-based dashboard application | 200 OK |
| `/ui/config` | GET | Retrieve UI layout configuration (ui.json) | 200 OK |
| `/ui/config` | PUT | Update UI layout configuration (ui.json) | 200 OK, 400 Bad Request |

The UI uses **GoldenLayout v1.5.9**, a sophisticated dockable panel manager that allows users to fully customize their workspace by dragging, resizing, and stacking views. The layout state is persisted in the browser's `localStorage` (`sdtb-layout-v1`), ensuring the workspace remains exactly as the user left it across page refreshes.

```
+----------------------------------------------------------+
|  Toolbar / Menubar                                       |
|  [Connect] [Disconnect] [Reset Layout] [About]           |
+----------------------------------------------------------+
|                                                          |
|       GoldenLayout Workspace (Dockable Panels)           |
|                                                          |
|  +-------------------+  +-----------------------------+  |
|  | Device Explorer   |  |       Dashboard             |  |
|  | (Side Panel)      |  |       (Center View)         |  |
|  +-------------------+  +-----------------------------+  |
|                                                          |
|  +----------------------------------------------------+  |
|  |           Debug Window / Test Editor               |  |
|  |           (Bottom Stacks)                          |  |
|  +----------------------------------------------------+  |
|                                                          |
+----------------------------------------------------------+
```

**Toolbar / Menubar**

| Menu Item | Description |
|-----------|-------------|
| File | Import/export test scripts, save/load UI layouts |
| About | System information, SDTB version, API version |
| Preference | Opens system configuration (system.json) as a form overlay dialog |

**Sidebar Views**

The sidebar displays icon buttons (VS Code-style). Clicking an icon switches the center content area.

| View Name | Description |
|-----------|-------------|
| Dashboard | Ultra-Compact v3 grid displaying mapped channel widgets. Supports **Quick Look** (click widget to open high-res modal oscilloscope). |
| Widget Mapper | Configuration interface to assign widget types to channels. |
| Channel Mapper | Interface to create/edit channel-to-signal mappings visually. |
| Device Explorer | Multi-tab view of discovered hardware with **LED Status Indicators** and per-device **Restart** buttons. |
| Oscilloscope Viewer | Multi-channel graphing with collapsible "Active Plots" panel for maximized visualization space. |
| Debug Window | Live scrolling log of command flow via SSE. |
| Test Editor | JSONL test script editor with integrated execution controls. |

**Supported Widget Types**

| Widget Type | Description | Typical Channel Mapping |
|-------------|-------------|------------------------|
| Button | Toggle ON/OFF control | Digital output channels (relay, switch) |
| LED | Status indicator (ON/OFF/color) | Digital input channels (status signals) |
| Slider | Continuous value control with range | Analog output channels (voltage, current) |
| Gauge | Circular dial displaying a measured value | Analog input channels (temperature, pressure) |
| Bar Graph | Vertical/horizontal bar for value visualization | Analog input channels (level, percentage) |
| Numeric Display | Real-time numeric value readout | Any readable channel |

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F07.01 | System shall serve a browser-based UI dashboard via /ui endpoint | Medium | Integration Test |
| F07.02 | UI shall follow a three-region layout: toolbar/menubar (top), sidebar (left), and center content area | Medium | Integration Test |
| F07.03 | Toolbar shall provide File, About, and Preference menu items | Medium | Integration Test |
| F07.04 | Preference menu shall open system configuration (system.json) as a form overlay dialog | Medium | Integration Test |
| F07.05 | Sidebar shall provide icon-based navigation with six views: Dashboard, Widget Mapper, Channel Mapper, Device Explorer, Oscilloscope Viewer, and Debug Window | Medium | Integration Test |
| F07.06 | Center content area shall dynamically switch based on the active sidebar view | Medium | Integration Test |
| F07.07 | Dashboard view shall display live channel widgets and include Connect, Disconnect, and Restart buttons | Medium | Integration Test |
| F07.08 | Widget Mapper view shall allow users to assign widget types to channels and configure widget properties | Medium | Integration Test |
| F07.09 | UI shall provide pre-configured widget types (button, LED, slider, gauge, bar graph, numeric display) | Medium | Integration Test |
| F07.10 | Channel Mapper view shall allow users to create and edit channel-to-signal mappings visually | Medium | Integration Test |
| F07.11 | Debug Window view shall display live channel/signal command flow via SSE | Medium | Integration Test |
| F07.12 | Test Editor view shall support JSONL format editing with Play, Pause, and Stop controls | Medium | Integration Test |
| F07.13 | Widget-to-channel mappings and layout shall be persisted in ui.json | Medium | Integration Test |
| F07.14 | UI configuration (ui.json) shall be managed exclusively via /ui/config endpoints | Medium | Unit Test |
| F07.15 | Widgets shall update in real-time using channel streaming (SSE) | Medium | Integration Test |
| F07.16 | UI shall be self-contained; no external dependencies or separate build step required to serve | Medium | Integration Test |
| F07.17 | Oscilloscope viewer shall support simultaneous display of multiple channels | High | Integration Test |
| F07.18 | User shall be able to assign unique colors to each channel in the viewer | High | UI Test |
| F07.19 | User shall be able to select different line styles (solid, dashed, dotted, points) per channel | High | UI Test |
| F07.20 | Viewer shall support real-time zoom (X and Y axis) and panning | High | UI Test |
| F07.21 | User shall be able to pause and resume the live data stream without losing buffered history | High | UI Test |
| F07.22 | User shall be able to select the data refresh rate for the oscilloscope (e.g., 250ms, 500ms, 1000ms) | High | UI Test |
| F07.23 | Viewer shall display a legend with channel names and current values | High | UI Test |
| F07.24 | User shall be able to export the current oscilloscope data to CSV/JSON (future) | Low | Integration Test |

#### F08: Agentic Control (MCP)

**Description**: Expose the test bench capabilities to AI agents using the Model Context Protocol (MCP), providing an abstracted, tool-based interface for autonomous hardware interaction.

**Architecture Integration**: The MCP server is integrated directly into the FastAPI application as a sub-app, sharing the same hardware connection lifecycle and system state as the REST API and Web UI.

**MCP Resources**

| URI | Name | Description |
|-----|------|-------------|
| `sdtb://docs/control-guide` | SDTB Control Guide | Markdown documentation explaining the hardware lifecycle (Connect -> Discover -> Interact -> Disconnect). |

**MCP Tools**

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `list_channels` | Lists all logical channels available on the bench. | None |
| `read_channel` | Reads the current value of a single channel. | `channel_id` |
| `read_channels` | Batch read multiple channels in a single request. | `channel_ids: List[str]` |
| `write_channel` | Sets the value of a single channel. | `channel_id`, `value` |
| `write_channels` | Batch write multiple channels for synchronized control. | `writes: List[WriteOp]` |
| `inject_fault` | Simulates a hardware fault on a channel (Short to Ground, Open, etc.). | `channel_id`, `fault_id` |
| `clear_fault` | Restores a channel to normal operation. | `channel_id` |
| `get_channel_info` | Retrieves metadata (units, range) for a channel. | `channel_id` |
| `get_system_summary` | Returns a high-level overview of hardware health. | None |
| `connect_system` | Connects all physical hardware (Arduinos, etc.). | None |
| `disconnect_system` | Safely closes all hardware connections. | None |

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F08.01 | System shall expose an MCP interface over SSE (Server-Sent Events) transport. | High | Integration Test |
| F08.02 | MCP interface shall share the same system state as the REST API. | High | Contract Test |
| F08.03 | Agents shall be able to discover all channels via `list_channels`. | High | Agent Test |
| F08.04 | System shall provide batch read/write tools for optimized agent performance. | Medium | Performance Test |
| F08.05 | MCP interface shall provide human-readable documentation as a Resource. | Medium | Agent Test |
| F08.06 | Tool execution shall include proper error reporting for individual channel failures in batches. | High | Error Handling Test |

#### F09: Fault Injection

**Description**: Enable users to simulate hardware failures and signal anomalies to validate the diagnostic capabilities and fail-safe logic of the target system (ECU).

**API Integration**: Faults are managed directly through the signal endpoints. Users do not call a separate fault service; instead, they apply faults to specific hardware signals.

| Endpoint | Method | Description | Status Codes |
|----------|--------|-------------|--------------|
| `/device/{device_id}/signal/{signal_id}/fault` | GET | Retrieve list of available faults for the signal | 200 OK, 404 Not Found |
| `/device/{device_id}/signal/{signal_id}/fault` | POST | Trigger a specific fault on the signal (accepts `fault_id`) | 200 OK, 400 Bad Request |
| `/device/{device_id}/signal/{signal_id}/fault` | DELETE | Clear the active fault on the signal | 200 OK |
| `/system/fault/clear` | POST | Global safety mechanism to clear all faults across all devices | 200 OK |

**Fault Types**

| Fault Type | Description |
|------------|-------------|
| Short to Ground | Forces a signal to 0V/Ground |
| Short to Battery | Forces a signal to Battery voltage (Vbatt) |
| Open Circuit | Disconnects the signal path (High Impedance) |
| Stuck at Value | Forces a signal to a specific static value |
| Signal Noise | Injects random noise into an analog signal |
| Packet Loss | Simulates intermittent communication failure (CAN/LIN) |

**Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| F09.01 | User shall be able to trigger faults on specific channels or raw signals | Low | Integration Test |
| F09.02 | System shall support timed faults (automatic clearing after a duration) | Low | Integration Test |
| F09.03 | System shall provide a global "Clear All Faults" safety mechanism | Low | Integration Test |
| F09.04 | Fault states shall be reported in the system health status | Low | Integration Test |
| F09.05 | Fault injection shall be supported in automated test scripts (JSONL) | Low | Integration Test |
| F09.06 | System shall prevent conflicting faults on the same signal (e.g., Short to Ground and Short to Battery) | Low | Unit Test |


### 3.4 Workflow Requirements

#### W01: System Startup & Initialization

1. Server process starts and loads `system.json` and `channels.json` from `AppData/SDTB`
2. If any config file is not found, system creates it with default values
3. System reads device directory path from `system.json` and scans for `device_*.py` plugin files and their corresponding `device_*.json` config files
4. Discovered plugins are registered and visible via `GET /device`, but remain in `offline` state
5. Each discovered plugin auto-loads its own `device_<name>.json` configuration
6. REST API becomes available; `GET /system` returns system status with discovered device summary
7. Devices are **not connected** until the user explicitly calls `POST /system/connect`

#### W02: Device Connection Lifecycle

1. User calls `POST /system/connect`
2. System iterates through **all** discovered and configured device instances
3. For each device, calls `BaseDevice.connect(connection_params)`
   - On success: device state transitions to `idle`
   - On failure: device state transitions to `error`; system continues with remaining devices (graceful degradation)
4. Response includes summary of connected and failed devices
5. User calls `POST /system/disconnect` to gracefully disconnect all devices
6. On server restart, system auto-disconnects any connected devices before re-initializing

**Device State Transitions:**

```
offline → idle → busy → idle
                ↘ error → idle (on recovery)
```

| State | Description |
|-------|-------------|
| `offline` | Discovered but not connected |
| `idle` | Connected and ready for operations |
| `busy` | Currently executing an operation |
| `error` | Connection or operation failure |

#### W03: Channel Configuration

1. User discovers available signals via `GET /device/{device_id}/signal`
2. User retrieves signal metadata via `GET /device/{device_id}/signal/{signal_id}/info`
3. User configures channel mappings via `PUT /system/config/channels`
4. Each channel mapping specifies: channel ID, target device ID, target signal ID, and **independent** channel properties (min, max, unit, resolution, offset)
5. Channel properties are **not inherited** from the underlying signal — they represent the logical range and unit exposed to the user (e.g., a voltage signal mapped to a temperature channel with different unit and range)
6. Channels can be reconfigured (remapped to a different signal) while devices are connected
7. Channel configuration is persisted to `channels.json`

#### W04: Signal & Channel Read/Write

**Raw Signal Access (Advanced/Debugging):**

1. User calls `GET /device/{device_id}/signal/{signal_id}` to read a raw value
2. User calls `PUT /device/{device_id}/signal/{signal_id}` with value in payload
3. System validates the value against the **signal's** min/max range before writing

**Channel Access (Standard User):**

1. User calls `GET /channel/{channel_id}` to read a logical value
2. System resolves channel → device + signal, reads raw value, applies channel offset/calibration
3. User calls `PUT /channel/{channel_id}` with value in payload
4. System validates the value against the **channel's** min/max range
5. System converts channel value to raw signal value (reverse offset/calibration)
   - **Resolution Guard**: Scaling logic includes a zero-check for `resolution` to prevent division-by-zero errors.
6. System validates the converted value against the **signal's** min/max range
7. System writes the raw value to the device

**Dual-Layer Validation:** Both channel and signal layers independently validate values against their own defined ranges. A write can fail at either layer.

#### W05: Live Streaming

1. User calls `GET /channel/{channel_id}/stream` or `GET /device/{device_id}/signal/{signal_id}/stream`
2. System opens an **SSE (Server-Sent Events)** connection
3. System continuously reads the signal value and pushes data frames to the client
4. **Change Detection**: System implements a delta filter using `math.isclose` (rel_tol=1e-5) to only push data frames when values change significantly, reducing bandwidth and client load.
5. Each data frame includes: value, timestamp, and unit
5. Client disconnects to terminate the stream
6. System stops reading when the client disconnects

#### W06: Test Execution Lifecycle

1. **Define**: User uploads a test definition via `POST /test` or references an existing one
2. **Execute**: User calls `POST /run` (inline JSONL) or `POST /run/test/{test_id}`
3. System validates the test script and enqueues the execution
4. System returns `202 Accepted` with a unique `execution_id`
5. **Run**: System dequeues and executes test steps sequentially
   - Test steps reference **channels** (not raw signals)
   - Each step result (value, pass/fail, timestamp) is logged
6. **Monitor**: User polls `GET /run/{execution_id}` for progress
7. **Complete**: Results available via `GET /run/{execution_id}/results`
8. **Abort**: User can call `POST /run/{execution_id}/abort` at any time

**JSONL Test Script Format:**

```jsonl
{"step": 1, "action": "write", "channel": "ch_voltage_1", "value": 3.3}
{"step": 2, "action": "wait", "duration_ms": 500}
{"step": 3, "action": "read", "channel": "ch_current_1", "assert": {"min": 0.9, "max": 1.1}}
{"step": 4, "action": "read", "channel": "ch_temperature_1", "assert": {"operator": "==", "target": 25.0, "tolerance": 0.1}}
{"step": 5, "action": "fault", "channel": "ch_throttle_sensor", "type": "short_to_ground", "duration_ms": 1000}
```

#### W07: Session & Concurrency Rules

1. Only **one test execution** can be actively running at any time
2. If a test is running and the user submits another `POST /run`, the new request is **queued**
3. The currently running test is considered the active "session"
4. While a test is running, **no user write operations** are permitted via the API (both channel and signal writes are blocked) — this prevents interference with the active test
5. **Read operations** remain available during test execution for monitoring purposes
6. Queued runs execute in order once the active run completes or is aborted

**Workflow Requirements:**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| W01.01 | System shall discover device plugins at startup without connecting to hardware | High | Integration Test |
| W01.02 | Each device plugin shall auto-load its own device_<name>.json; if missing, a default shall be created | High | Integration Test |
| W01.03 | System shall create a backup (.bak) of each config file before every write operation | High | Integration Test |
| W01.04 | On startup, if a config file is corrupted, system shall fall back to its .bak copy | High | Integration Test |
| W01.05 | If both primary and backup config files are corrupted, system shall create fresh defaults and log a warning | High | Integration Test |
| W01.06 | Corruption of one config file shall not affect the other two | High | Integration Test |
| W02.01 | POST /system/connect shall connect all configured devices; individual device connection is not supported | High | Integration Test |
| W02.02 | Failed device connections shall not block connection of remaining devices | High | Integration Test |
| W02.03 | Server restart shall auto-disconnect devices before re-initialization | High | Integration Test |
| W03.01 | Channel properties (min, max, unit, offset, resolution) shall be independently defined, not inherited from the mapped signal | High | Unit Test |
| W03.02 | Channel remapping shall be allowed while devices are connected | High | Integration Test |
| W04.01 | Write operations shall validate at both channel and signal layers independently | High | Unit Test |
| W05.01 | Live streaming shall use Server-Sent Events (SSE) protocol | High | Integration Test |
| W06.01 | Test scripts shall reference channels, not raw device signals | High | Unit Test |
| W06.02 | Test execution shall follow JSONL format with step, action, channel, and assertions supporting **6 comparison operators** (`>`, `>=`, `==`, `!=`, `<`, `<=`) and floating-point tolerance via `math.isclose` | High | Integration Test |
| W07.01 | Only one test execution shall be actively running at any time | High | Integration Test |
| W07.02 | Additional run requests during active execution shall be queued | High | Integration Test |
| W07.03 | User write operations (channel and signal) shall be blocked during active test execution | High | Integration Test |
| W07.04 | User read operations shall remain available during active test execution | High | Integration Test |

## 4. Non-Functional Requirements

### 4.1 Performance Requirements
- **Response Time**: API endpoints shall respond within 100ms for 95% of requests under normal load
- **Throughput**: System shall support minimum 100 concurrent API connections
- **Latency**: Signal I/O operations shall have deterministic latency where hardware permits
- **Scalability**: Architecture shall support horizontal scaling for API layer

### 4.2 Reliability Requirements
- **Availability**: System shall target 99.9% uptime excluding maintenance windows
- **Fault Tolerance**: System shall handle individual device failures without complete system failure
- **Recovery**: System shall automatically recover from transient failures where possible
- **Data Integrity**: All critical operations shall include validation and error detection

### 4.3 Security Requirements
- **Authentication**: System shall support API key-based authentication (Low priority)
- **Authorization**: Role-based access control for administrative operations (Low priority)
- **Communication**: API communications shall support TLS encryption (configurable)
- **Input Validation**: All API inputs shall be validated to prevent injection attacks
- **Audit Trail**: Significant operations shall be logged for security monitoring

### 4.4 Usability Requirements
- **API Consistency**: All endpoints shall follow RESTful conventions and consistent naming
- **Documentation**: Complete OpenAPI/Swagger documentation shall be provided
- **Error Responses**: Standardized error response format with meaningful messages
- **Versioning**: API shall support versioning to enable backward compatibility

### 4.5 Maintainability Requirements
- **Modularity**: Code shall be organized into loosely coupled, highly cohesive modules
- **Testability**: System shall be designed for unit and integration testing (>80% code coverage target)
- **Logging**: Comprehensive structured logging shall be implemented
- **Configuration**: System behavior shall be configurable without code changes
- **Extensibility**: Architecture shall support adding new device types and signal types

## 5. Out of Scope

The following items are explicitly excluded from the initial release:

- **Timing Performance Validation**: Validation of timing performance in millisecond or microsecond ranges requires specialized equipment and is out of scope
- **Wireless Communication Protocols**: Native support for Wi-Fi, Bluetooth, Zigbee, etc. requires additional hardware
- **High-Speed Serial Interfaces**: PCIe, SATA, USB 3.0+ testing requires specialized equipment
- **Environmental Testing**: Temperature, humidity, vibration testing chambers integration
- **Machine Learning Test Optimization**: AI-driven test generation and optimization (future extension)
- **Cloud Integration**: Native cloud service integrations (AWS/Azure/GCP) for test data storage
- **Advanced Triggering Systems**: Complex multi-channel triggering with precise nanosecond synchronization
- **Real-Time Operating System (RTOS) Support**: Deterministic real-time guarantees require specialized kernels

## 6. Glossary

- **Software Defined Test Bench (SDTB)**: A test automation framework that defines test instrumentation and control through software interfaces rather than hardware-specific implementations.

- **REST API**: Representational State Transfer Application Programming Interface - an architectural style for designing networked applications using HTTP methods.

- **MCP Server**: Model Context Protocol Server - an enhanced interface layer that provides contextual awareness and advanced capabilities beyond basic REST APIs.

- **Device**: A physical hardware instrument (e.g., multimeter, power supply, CAN sniffer) represented as a software plugin in the SDTB system. Devices are auto-discovered from plugin files and expose their raw signal capabilities.

- **Channel**: A logical abstraction that maps to a raw device signal, providing a technology-agnostic interface for test engineers. Channels decouple tests from specific hardware, enabling hardware swaps without test changes.

- **Flash Operation**: The process of writing firmware or software to a target device's memory.

- **Test Run**: A single execution of a test procedure identified by a unique test ID.

- **Signal**: A raw electrical or data communication capability owned by a specific device, defined by properties such as type, resolution, unit, and valid range. Signals are the physical-layer building blocks that channels abstract over.

- **Signal I/O**: Input/Output operations involving electrical signals of various types (analog, digital, PWM).

- **Health Status**: Indicates the operational readiness and condition of the SDTB system and its subsystems.

- **Concurrency**: The ability to handle multiple operations simultaneously, such as running multiple tests or controlling multiple devices.

- **Deterministic Latency**: Predictable and consistent response time for operations, critical for timing-sensitive applications.

- **Hot-Plugging**: The ability to add or remove devices while the system is running without requiring a reboot.

- **Debouncing**: Technique used to eliminate noise or false triggers in digital signal readings.

- **Duty Cycle**: The percentage of time a PWM signal is in the high state during each period.

- **Sampling Rate**: The frequency at which analog signals are measured or digital signals are read.

- **Isolation**: Ensuring that operations on one device or test do not affect operations on another.

- **Graceful Degradation**: The ability of a system to continue operating at a reduced level when some components fail.

- **Role-Based Access Control (RBAC)**: Security approach that restricts system access based on user roles and permissions.

- **Audit Trail**: Chronological record of system activities that allows for reconstruction and examination of events.

- **OpenAPI/Swagger**: Specification for defining RESTful APIs that enables automatic documentation generation.

- **Structured Logging**: Logging approach that uses a consistent format (typically JSON) to enable machine processing and analysis.

- **Widget**: A visual UI component (button, gauge, slider, LED, etc.) that is mapped to a channel for real-time display or control.

- **Server-Sent Events (SSE)**: A standard HTTP-based protocol for pushing real-time updates from server to client over a single long-lived connection.
# Software Defined Test Bench (SDTB)

A flexible, software-defined test automation framework for hardware validation. SDTB provides a programmable interface that abstracts hardware complexity through REST API and MCP server interfaces, enabling rapid test development and execution.

## High-Level Concept

SDTB acts as a middle layer between your test scripts and the physical hardware. It allows you to:
1.  **Abstract Hardware**: Define logical "Channels" (e.g., `Battery_Voltage`) that map to raw hardware signals (e.g., `Arduino_Pin_A0`).
2.  **Plugin Architecture**: Add support for new devices or flashing protocols by simply dropping a Python script into the `devices/` directory.
3.  **Universal Control**: Control your entire test bench via a standardized REST API or using AI-assisted tools through the Model Context Protocol (MCP).

## System Architecture

```mermaid
graph TD
    UI[Web UI Dashboard] --> API[FastAPI REST API Layer]
    MCP[MCP Server Wrapper] --> API
    
    subgraph SDTB Core System
        API --> SystemMgr[System Manager]
        API --> DeviceMgr[Device Manager]
        API --> ChannelMgr[Channel Manager]
        API --> TestEngine[Test Execution Engine]
        API --> FlashMgr[Flash Manager]
        
        SystemMgr --> Config[Configuration Manager]
        DeviceMgr --> PluginLoader[Plugin Loader]
        FlashMgr --> PluginLoader
        ChannelMgr --> Config
        ChannelMgr --> DeviceMgr
        TestEngine --> ChannelMgr
    end
    
    PluginLoader --> Device1[device_ni_daq.py]
    PluginLoader --> Device2[device_arduino.py]
    PluginLoader --> Flash1[flash_uds.py]
    
    Device1 --> Hardware1[NI Hardware]
    Device2 --> Hardware2[Arduino Hardware]
    Flash1 --> Target[ECU Target]
```

## Tool Snapshots

### Live Dashboard
![SDTB Dashboard](docs/image/dashboard.png)

### Waveform Viewer
![SDTB Waveform](docs/image/waveform.png)

### Software Flasher
![SDTB Flasher](docs/image/flash.png)

### System Logs & Debug
![SDTB Logs](docs/image/system_log.png)

## Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. How to Run
Start the main application, which hosts both the REST API and the MCP server (via SSE):
```bash
python main.py
```
The server will start on `http://localhost:8000`. You can access the UI at `http://localhost:8000/ui`.

## Documentation Map

| Document | Description |
|----------|-------------|
| [api.md](docs/api.md) | Detailed REST API reference and input definitions |
| [spec.md](docs/spec.md) | System specifications and protocol definitions |
| [design.md](docs/design.md) | Architectural design and implementation details |

## Extending the Bench

### How to Add a Device
1.  **Create Plugin**: Create a new file `devices/device_<name>.py`.
2.  **Implement Class**: Create a class inheriting from `core.base_device.BaseDevice`.
3.  **Define Config**: Create a corresponding `config/device_<name>.json` to enable it in the system.

### How to Add a Flash Protocol
1.  **Create Plugin**: Create a new file `devices/flash_<name>.py`.
2.  **Implement Class**: Create a class inheriting from `core.base_flash.BaseFlash`.
3.  **Define Config**: Create a JSON file `devices/flash_<name>.json` specifying the plugin class and connection parameters.

## License

[License Information]
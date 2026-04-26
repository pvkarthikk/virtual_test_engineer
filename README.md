# Software Defined Test Bench (SDTB)

A flexible, software-defined test automation framework for hardware validation. SDTB provides a programmable interface that abstracts hardware complexity through REST API and MCP server interfaces, enabling rapid test development and execution.

## Features

- **Software Flashing**: Programmatic firmware/software deployment to target devices
- **Device Channel Management**: Flexible device discovery and management with no API changes for additions
- **Signal Control & Monitoring**: Support for analog, digital, and PWM signals
- **Test Execution**: Complete test lifecycle management with status tracking and abort capabilities
- **System Control**: Start, shutdown, and health monitoring

## Architecture

```
MCP Server (Wrapper) → REST API (Base) → Hardware Abstraction → Devices
```

## Documentation Map

| Document | Description |
|----------|-------------|
| [requirement.md](requirement.md) | Feature requirements, specifications, and API definitions |
| [design.md](design.md) | System design, architecture details, and implementation decisions |
| [test.md](test.md) | Test plans, test cases, and verification procedures |
| [results.md](results.md) | Test execution results, reports, and traceability |

## Quick Start

```bash
# Installation
pip install -r requirements.txt

# Run API server
python -m sdtb.api

# Run MCP server
python -m sdtb.mcp
```

## API Documentation

API documentation is available via Swagger UI at `/docs` endpoint when the server is running.

## License

[License Information]
#!/usr/bin/env python3
"""
Virtual Test Engineer - Main Test Bench
"""

import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

from .types import TestBenchState, TestRun
from .plugin_manager import PluginManager
from .device_manager import DeviceManager
from .test_engine import TestExecutionEngine
from .flashing_manager import FlashingManager


class VirtualTestBench:
    """Main test bench class"""

    def __init__(self, config_file: Optional[str] = None):
        self.state = TestBenchState.IDLE
        self.config_file = config_file
        self.config: Dict[str, Any] = {}

        # Core components
        self.plugin_manager = PluginManager()
        self.device_manager = DeviceManager(self.plugin_manager)
        self.test_engine = TestExecutionEngine(self.device_manager)
        self.flashing_manager: Optional[FlashingManager] = None

    async def initialize(self, config_file: Optional[str] = None) -> bool:
        """Initialize the test bench"""
        try:
            self.state = TestBenchState.CONFIGURING

            if config_file:
                self.config_file = config_file

            if self.config_file and Path(self.config_file).exists():
                await self.load_config(self.config_file)

            # Discover and load plugins
            await self.plugin_manager.discover_plugins()

            # Initialize devices from config
            if self.config:
                success = await self.device_manager.initialize_from_config(self.config)
                if not success:
                    self.state = TestBenchState.ERROR
                    return False

            # Initialize flashing manager if enabled
            flashing_config = self.config.get('flashing', {})
            if flashing_config.get('enabled', False):
                self.flashing_manager = FlashingManager(self.plugin_manager, flashing_config)
                await self.flashing_manager.initialize()

            self.state = TestBenchState.IDLE
            return True

        except Exception as e:
            print(f"Error initializing test bench: {e}")
            self.state = TestBenchState.ERROR
            return False

    async def load_config(self, config_file: str) -> None:
        """Load configuration from file"""
        config_path = Path(config_file)

        if config_path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

        print(f"Loaded configuration from {config_file}")

    async def reload_config(self) -> bool:
        """Reload configuration"""
        if not self.config_file:
            return False

        try:
            await self.shutdown()
            return await self.initialize(self.config_file)
        except Exception as e:
            print(f"Error reloading config: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the test bench"""
        try:
            await self.test_engine.cleanup_completed_runs()
            await self.device_manager.shutdown()
            await self.plugin_manager.shutdown_all()
            self.state = TestBenchState.IDLE
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.state = TestBenchState.ERROR

    # Device operations
    async def read_channel(self, channel_id: str) -> Optional[Any]:
        """Read a channel value"""
        reading = await self.device_manager.read_channel(channel_id)
        return reading.value if reading else None

    async def write_channel(self, channel_id: str, value: Any) -> bool:
        """Write a channel value"""
        return await self.device_manager.write_channel(channel_id, value)

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        return self.device_manager.get_channel_info(channel_id)

    def get_available_channels(self) -> List[str]:
        """Get list of available channels"""
        return self.device_manager.get_available_channels()

    # Test execution
    async def start_test_scenario(self, scenario_id: str, parameters: Dict[str, Any] = None,
                                async_mode: bool = True) -> str:
        """Start a test scenario"""
        if self.state != TestBenchState.IDLE:
            raise RuntimeError(f"Cannot start test while in state: {self.state.value}")

        self.state = TestBenchState.RUNNING
        run_id = await self.test_engine.start_scenario(scenario_id, parameters, async_mode)

        # If not async, reset state after completion
        if not async_mode:
            self.state = TestBenchState.IDLE

        return run_id

    def get_test_run_status(self, run_id: str) -> Optional[TestRun]:
        """Get test run status"""
        return self.test_engine.get_run_status(run_id)

    def abort_test_run(self, run_id: str) -> bool:
        """Abort a test run"""
        success = self.test_engine.abort_run(run_id)
        if success:
            self.state = TestBenchState.IDLE
        return success

    # Flashing operations
    async def start_flash(self, target_device: str, firmware_file: str,
                         protocol: str, parameters: Dict[str, Any]) -> str:
        """Start a firmware flash operation"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return await self.flashing_manager.start_flash(
            target_device, firmware_file, protocol, parameters
        )

    def get_flash_status(self, flash_id: Optional[str] = None) -> Dict[str, Any]:
        """Get flash operation status"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return self.flashing_manager.get_flash_status(flash_id)

    async def cancel_flash(self, flash_id: str) -> bool:
        """Cancel a flash operation"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return await self.flashing_manager.cancel_flash(flash_id)

    async def upload_firmware(self, filename: str, content: bytes,
                            description: Optional[str] = None):
        """Upload firmware file"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return await self.flashing_manager.upload_firmware(filename, content, description)

    async def delete_firmware(self, file_id: str) -> bool:
        """Delete firmware file"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return await self.flashing_manager.delete_firmware(file_id)

    def list_firmware_files(self):
        """List firmware files"""
        if not self.flashing_manager:
            raise RuntimeError("Flashing not enabled in configuration")

        return self.flashing_manager.list_firmware_files()

    def get_active_test_runs(self) -> List[str]:
        """Get active test run IDs"""
        return self.test_engine.get_active_runs()

    # Plugin management
    def get_loaded_plugins(self) -> List[str]:
        """Get loaded plugin names"""
        return self.plugin_manager.get_loaded_plugins()

    def get_available_plugins(self) -> List[str]:
        """Get available plugin names"""
        return self.plugin_manager.get_available_plugins()

    # System information
    def get_status(self) -> Dict[str, Any]:
        """Get test bench status"""
        return {
            "state": self.state.value,
            "config_file": self.config_file,
            "loaded_plugins": self.get_loaded_plugins(),
            "available_channels": len(self.get_available_channels()),
            "active_runs": len(self.get_active_test_runs())
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get test bench capabilities"""
        return {
            "supported_io_types": ["digital", "analog", "pwm", "can"],
            "max_concurrent_scenarios": 1,
            "supported_protocols": ["can2.0a", "can2.0b"],
            "config_formats": ["yaml", "json"],
            "real_time_streaming": False,  # Not implemented yet
            "async_execution": True
        }
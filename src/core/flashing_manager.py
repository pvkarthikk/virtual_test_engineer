#!/usr/bin/env python3
"""
Virtual Test Engineer - Flashing Manager
"""

import asyncio
import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from .types import (
    FlashOperation, FlashStatus, FlashProtocol, FirmwareFile,
    FlashingPlugin
)
from .plugin_manager import PluginManager


class FlashingManager:
    """Manages firmware flashing operations"""

    def __init__(self, plugin_manager: PluginManager, config: Dict[str, Any]):
        self.plugin_manager = plugin_manager
        self.config = config
        self.firmware_directory = Path(config.get('firmware_directory', './firmware'))
        self.supported_protocols = config.get('supported_protocols', ['avrdude'])
        self.default_timeout = config.get('default_timeout', 300)
        self.max_concurrent_operations = config.get('max_concurrent_operations', 1)

        # Ensure firmware directory exists
        self.firmware_directory.mkdir(exist_ok=True)

        # Active operations and files
        self.active_operations: Dict[str, FlashOperation] = {}
        self.firmware_files: Dict[str, FirmwareFile] = {}
        self.flash_plugins: Dict[str, FlashingPlugin] = {}

        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_operations)

    async def initialize(self) -> None:
        """Initialize the flashing manager"""
        # Load existing firmware files
        await self._load_existing_firmware_files()

        # Initialize flashing plugins
        await self._initialize_flash_plugins()

    async def shutdown(self) -> None:
        """Shutdown the flashing manager"""
        # Cancel all active operations
        for flash_id in list(self.active_operations.keys()):
            await self.cancel_flash(flash_id)

        # Shutdown plugins
        for plugin in self.flash_plugins.values():
            await plugin.shutdown()

        # Shutdown executor
        self.executor.shutdown(wait=True)

    async def start_flash(self, target_device: str, firmware_file: str,
                         protocol: str, parameters: Dict[str, Any]) -> str:
        """Start a flash operation"""

        # Validate inputs
        if protocol not in self.supported_protocols:
            raise ValueError(f"Unsupported protocol: {protocol}")

        if firmware_file not in [f.filename for f in self.firmware_files.values()]:
            raise ValueError(f"Firmware file not found: {firmware_file}")

        # Check concurrent operation limit
        running_ops = [op for op in self.active_operations.values()
                      if op.status == FlashStatus.RUNNING]
        if len(running_ops) >= self.max_concurrent_operations:
            raise ValueError("Maximum concurrent flash operations reached")

        # Create flash operation
        flash_id = f"flash_{uuid.uuid4()}"
        operation = FlashOperation(
            flash_id=flash_id,
            target_device=target_device,
            firmware_file=firmware_file,
            protocol=FlashProtocol(protocol),
            parameters=parameters,
            status=FlashStatus.QUEUED
        )

        self.active_operations[flash_id] = operation

        # Start async flashing task
        asyncio.create_task(self._execute_flash(operation))

        return flash_id

    async def _execute_flash(self, operation: FlashOperation) -> None:
        """Execute flash operation asynchronously"""
        try:
            operation.status = FlashStatus.RUNNING
            operation.start_time = time.time()

            # Get appropriate flashing plugin
            plugin = self._get_flash_plugin(operation.protocol)
            if not plugin:
                raise ValueError(f"No plugin available for protocol: {operation.protocol}")

            # Execute flash with progress callback
            success = await plugin.flash_firmware(operation, self._progress_callback)

            operation.status = FlashStatus.COMPLETED if success else FlashStatus.FAILED
            operation.end_time = time.time()

            # Log completion
            operation.logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": f"Flash operation {'completed successfully' if success else 'failed'}"
            })

        except Exception as e:
            operation.status = FlashStatus.FAILED
            operation.end_time = time.time()
            operation.logs.append({
                "timestamp": time.time(),
                "level": "error",
                "message": f"Flash failed: {str(e)}"
            })

    def _progress_callback(self, flash_id: str, progress: Dict[str, Any]) -> None:
        """Update flash progress"""
        if flash_id in self.active_operations:
            operation = self.active_operations[flash_id]
            operation.progress.update(progress)

            # Add progress log
            operation.logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": f"Progress: {progress.get('percentage', 0)}% - {progress.get('step_description', '')}"
            })

    async def cancel_flash(self, flash_id: str) -> bool:
        """Cancel a flash operation"""
        if flash_id not in self.active_operations:
            return False

        operation = self.active_operations[flash_id]
        if operation.status not in [FlashStatus.QUEUED, FlashStatus.RUNNING]:
            return False

        # Cancel with plugin
        plugin = self._get_flash_plugin(operation.protocol)
        if plugin:
            await plugin.cancel_flash(flash_id)

        operation.status = FlashStatus.CANCELLED
        operation.end_time = time.time()
        operation.logs.append({
            "timestamp": time.time(),
            "level": "info",
            "message": "Flash operation cancelled by user"
        })

        return True

    def get_flash_status(self, flash_id: Optional[str] = None) -> Dict[str, Any]:
        """Get flash operation status"""
        if flash_id:
            operation = self.active_operations.get(flash_id)
            if not operation:
                return None
            return self._operation_to_dict(operation)
        else:
            return {
                "operations": [self._operation_to_dict(op) for op in self.active_operations.values()]
            }

    def _operation_to_dict(self, operation: FlashOperation) -> Dict[str, Any]:
        """Convert operation to dictionary"""
        result = {
            "flash_id": operation.flash_id,
            "status": operation.status.value,
            "progress": operation.progress,
            "start_time": operation.start_time,
            "end_time": operation.end_time,
            "target_device": operation.target_device,
            "firmware_file": operation.firmware_file,
            "logs": operation.logs
        }

        # Add estimated completion for running operations
        if operation.status == FlashStatus.RUNNING and operation.start_time:
            elapsed = time.time() - operation.start_time
            if elapsed > 0 and operation.progress.get("percentage", 0) > 0:
                total_estimated = elapsed / (operation.progress["percentage"] / 100)
                remaining = total_estimated - elapsed
                result["estimated_completion"] = time.time() + remaining

        return result

    async def upload_firmware(self, filename: str, content: bytes,
                            description: Optional[str] = None) -> FirmwareFile:
        """Upload a firmware file"""
        # Generate file ID and checksum
        file_id = f"fw_{uuid.uuid4()}"
        md5_hash = hashlib.md5(content).hexdigest()

        # Create firmware file record
        firmware_file = FirmwareFile(
            file_id=file_id,
            filename=filename,
            size_bytes=len(content),
            md5_checksum=md5_hash,
            uploaded_at=time.time(),
            description=description
        )

        # Save file to disk
        file_path = self.firmware_directory / filename
        with open(file_path, 'wb') as f:
            f.write(content)

        # Store in memory
        self.firmware_files[file_id] = firmware_file

        return firmware_file

    async def delete_firmware(self, file_id: str) -> bool:
        """Delete a firmware file"""
        if file_id not in self.firmware_files:
            return False

        firmware_file = self.firmware_files[file_id]

        # Check if file is being used in active operations
        for operation in self.active_operations.values():
            if (operation.firmware_file == firmware_file.filename and
                operation.status in [FlashStatus.QUEUED, FlashStatus.RUNNING]):
                return False

        # Delete file from disk
        file_path = self.firmware_directory / firmware_file.filename
        if file_path.exists():
            file_path.unlink()

        # Remove from memory
        del self.firmware_files[file_id]

        return True

    def list_firmware_files(self) -> List[FirmwareFile]:
        """List all firmware files"""
        return list(self.firmware_files.values())

    def _get_flash_plugin(self, protocol: FlashProtocol) -> Optional[FlashingPlugin]:
        """Get flashing plugin for protocol"""
        return self.flash_plugins.get(protocol.value)

    async def _initialize_flash_plugins(self) -> None:
        """Initialize flashing plugins"""
        # For now, create a mock plugin for avrdude
        # In a real implementation, plugins would be loaded from the plugin system
        if 'avrdude' in self.supported_protocols:
            plugin = MockAvrdudePlugin()
            await plugin.initialize({})
            self.flash_plugins['avrdude'] = plugin

    async def _load_existing_firmware_files(self) -> None:
        """Load existing firmware files from disk"""
        if not self.firmware_directory.exists():
            return

        for file_path in self.firmware_directory.iterdir():
            if file_path.is_file():
                try:
                    # Calculate checksum
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        md5_hash = hashlib.md5(content).hexdigest()

                    # Create firmware file record
                    firmware_file = FirmwareFile(
                        file_id=f"fw_{uuid.uuid4()}",
                        filename=file_path.name,
                        size_bytes=len(content),
                        md5_checksum=md5_hash,
                        uploaded_at=file_path.stat().st_mtime
                    )

                    self.firmware_files[firmware_file.file_id] = firmware_file

                except Exception as e:
                    print(f"Error loading firmware file {file_path}: {e}")


class MockAvrdudePlugin(FlashingPlugin):
    """Mock AVRDUDE flashing plugin for demonstration"""

    def __init__(self):
        self.active_operations: Dict[str, asyncio.Task] = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass

    async def shutdown(self) -> None:
        """Shutdown the plugin"""
        for task in self.active_operations.values():
            task.cancel()

    async def flash_firmware(self, operation: FlashOperation, progress_callback: callable) -> bool:
        """Execute firmware flashing (mock implementation)"""
        try:
            # Simulate flash process
            steps = [
                ("Erasing flash memory", 10),
                ("Writing firmware blocks", 60),
                ("Verifying written data", 30)
            ]

            for step_desc, step_duration in steps:
                # Update progress
                progress_callback(operation.flash_id, {
                    "current_step": step_desc.lower().replace(" ", "_"),
                    "step_description": step_desc,
                    "percentage": operation.progress.get("percentage", 0) + step_duration
                })

                # Simulate work
                await asyncio.sleep(step_duration / 10)  # Convert to seconds

            # Final verification
            progress_callback(operation.flash_id, {
                "current_step": "completed",
                "step_description": "Flash operation completed",
                "percentage": 100
            })

            return True

        except Exception as e:
            progress_callback(operation.flash_id, {
                "current_step": "failed",
                "step_description": f"Flash failed: {str(e)}",
                "percentage": operation.progress.get("percentage", 0)
            })
            return False

    async def cancel_flash(self, flash_id: str) -> bool:
        """Cancel ongoing flash operation"""
        task = self.active_operations.get(flash_id)
        if task:
            task.cancel()
            return True
        return False

    def get_supported_protocols(self) -> List[FlashProtocol]:
        """Get supported protocols"""
        return [FlashProtocol.AVRDUDE]
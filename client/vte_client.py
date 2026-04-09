#!/usr/bin/env python3
"""
Virtual Test Engineer Python Client
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class ChannelInfo:
    """Channel information"""
    id: str
    type: str
    status: str
    value: Optional[float] = None
    units: Optional[str] = None


@dataclass
class TestBenchStatus:
    """Test bench status"""
    state: str
    config_file: str
    loaded_plugins: List[str]
    available_channels: int
    active_runs: int


class VirtualTestEngineerClient:
    """REST API client for Virtual Test Engineer"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{endpoint}"

        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")

            return await response.json()

    # Health and Status Methods

    async def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        return await self._request('GET', '/health')

    async def get_bench_info(self) -> Dict[str, Any]:
        """Get test bench information"""
        return await self._request('GET', '/bench')

    async def get_capabilities(self) -> Dict[str, Any]:
        """Get system capabilities"""
        return await self._request('GET', '/capabilities')

    # Channel Methods

    async def list_channels(self) -> List[ChannelInfo]:
        """List all available channels"""
        response = await self._request('GET', '/channels')
        channels = []
        for ch_data in response['channels']:
            channels.append(ChannelInfo(
                id=ch_data['id'],
                type=ch_data['type'],
                status=ch_data['status'],
                value=ch_data.get('value'),
                units=ch_data.get('units')
            ))
        return channels

    async def read_channel(self, channel_id: str) -> ChannelInfo:
        """Read channel value"""
        response = await self._request('GET', f'/channels/{channel_id}')
        return ChannelInfo(
            id=response['id'],
            type=response['type'],
            status=response['status'],
            value=response['value'],
            units=response.get('units')
        )

    async def write_channel(self, channel_id: str, value: Union[int, float, bool]) -> Dict[str, Any]:
        """Write channel value"""
        data = {'value': value}
        return await self._request('PUT', f'/channels/{channel_id}', json=data)

    async def read_multiple_channels(self, channel_ids: List[str]) -> List[ChannelInfo]:
        """Read multiple channels"""
        data = {'channel_ids': channel_ids}
        response = await self._request('POST', '/channels/read', json=data)

        channels = []
        for ch_data in response['channels']:
            channels.append(ChannelInfo(
                id=ch_data['id'],
                type=ch_data['type'],
                status=ch_data['status'],
                value=ch_data['value'],
                units=ch_data.get('units')
            ))
        return channels

    # Test Execution Methods

    async def start_test(self, test_config: Dict[str, Any]) -> str:
        """Start a test run"""
        response = await self._request('POST', '/tests', json=test_config)
        return response['test_id']

    async def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get test status"""
        return await self._request('GET', f'/tests/{test_id}')

    async def stop_test(self, test_id: str) -> Dict[str, Any]:
        """Stop a test run"""
        return await self._request('DELETE', f'/tests/{test_id}')

    async def list_tests(self) -> List[Dict[str, Any]]:
        """List all tests"""
        response = await self._request('GET', '/tests')
        return response['tests']

    # Flashing Methods

    async def list_firmware_files(self) -> List[Dict[str, Any]]:
        """List available firmware files"""
        response = await self._request('GET', '/flash/files')
        return response['files']

    async def upload_firmware(self, file_path: str, description: str = None,
                            version: str = None) -> Dict[str, Any]:
        """Upload firmware file"""
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path)
            if description:
                data.add_field('description', description)
            if version:
                data.add_field('version', version)

            return await self._request('POST', '/flash/upload', data=data)

    async def start_flash(self, file_id: str, protocol: str, target_device: str,
                         parameters: Dict[str, Any] = None) -> str:
        """Start firmware flashing"""
        data = {
            'file_id': file_id,
            'protocol': protocol,
            'target_device': target_device,
            'parameters': parameters or {}
        }
        response = await self._request('POST', '/flash', json=data)
        return response['flash_id']

    async def get_flash_status(self, flash_id: str = None) -> Dict[str, Any]:
        """Get flash operation status"""
        endpoint = f'/flash/status'
        if flash_id:
            endpoint += f'?flash_id={flash_id}'
        return await self._request('GET', endpoint)

    async def cancel_flash(self, flash_id: str) -> Dict[str, Any]:
        """Cancel flash operation"""
        return await self._request('DELETE', f'/flash/{flash_id}')

    # Utility Methods

    async def wait_for_flash_completion(self, flash_id: str, timeout: float = 300.0,
                                      poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for flash operation to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_flash_status(flash_id)

            if status['status'] in ['completed', 'failed', 'cancelled']:
                return status

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Flash operation {flash_id} did not complete within {timeout} seconds")

    async def wait_for_test_completion(self, test_id: str, timeout: float = 300.0,
                                     poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for test to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_test_status(test_id)

            if status['status'] in ['completed', 'failed', 'aborted']:
                return status

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Test {test_id} did not complete within {timeout} seconds")
#!/usr/bin/env python3
"""
Virtual Test Engineer - Device Manager
"""

import asyncio
from typing import Dict, List, Any, Optional
from .types import (
    Channel, ChannelConfig, ChannelType, ChannelValue,
    BusPlugin, BusConfig, BusType, CanMessage,
    DeviceCapabilities, PluginConfig
)
from .plugin_manager import PluginManager


class DeviceManager:
    """Manages devices, channels, and buses"""

    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.channels: Dict[str, Channel] = {}
        self.channel_configs: Dict[str, ChannelConfig] = {}
        self.bus_plugins: Dict[str, BusPlugin] = {}
        self.bus_configs: Dict[str, BusConfig] = {}

    async def initialize_from_config(self, config: Dict[str, Any]) -> bool:
        """Initialize devices from configuration"""
        try:
            # Load plugins
            if 'plugins' in config:
                for plugin_config in config['plugins']:
                    plugin_name = plugin_config['name']
                    plugin_type = plugin_config['type']
                    plugin_cfg = PluginConfig(
                        name=plugin_name,
                        type=plugin_type,
                        config=plugin_config.get('config', {})
                    )

                    await self.plugin_manager.load_plugin(plugin_name, plugin_cfg)

            # Configure buses
            if 'buses' in config:
                for bus_config in config['buses']:
                    await self.configure_bus(bus_config)

            # Configure channels
            if 'channels' in config:
                for channel_config in config['channels']:
                    await self.configure_channel(channel_config)

            return True

        except Exception as e:
            print(f"Error initializing from config: {e}")
            return False

    async def configure_channel(self, config: Dict[str, Any]) -> bool:
        """Configure a channel"""
        try:
            channel_id = config['id']
            instrument_id = config.get('instrument')
            channel_type = ChannelType(config.get('type', 'analog_input'))

            # Find the plugin for this instrument
            plugin_name = None
            if 'instruments' in config:
                # This is a direct instrument config
                plugin_name = config.get('plugin')
            else:
                # Need to look up instrument config
                # For now, assume plugin is specified directly
                plugin_name = config.get('plugin')

            if not plugin_name:
                print(f"No plugin specified for channel {channel_id}")
                return False

            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                print(f"Plugin {plugin_name} not loaded for channel {channel_id}")
                return False

            # Create channel configuration
            channel_config = ChannelConfig(
                id=channel_id,
                type=channel_type,
                pin=config.get('pin'),
                scaling=config.get('scaling'),
                calibration=config.get('calibration')
            )

            # Create the channel
            channel = await plugin.create_channel(channel_id, channel_config)
            self.channels[channel_id] = channel
            self.channel_configs[channel_id] = channel_config

            print(f"Configured channel {channel_id}")
            return True

        except Exception as e:
            print(f"Error configuring channel {config.get('id', 'unknown')}: {e}")
            return False

    async def configure_bus(self, config: Dict[str, Any]) -> bool:
        """Configure a bus"""
        try:
            bus_id = config['id']
            bus_type = BusType(config.get('type', 'can'))
            plugin_name = config.get('plugin')

            if not plugin_name:
                print(f"No plugin specified for bus {bus_id}")
                return False

            # For now, we'll handle bus plugins differently
            # This would need to be extended based on actual bus plugin implementation
            print(f"Configured bus {bus_id} (plugin: {plugin_name})")
            return True

        except Exception as e:
            print(f"Error configuring bus {config.get('id', 'unknown')}: {e}")
            return False

    async def read_channel(self, channel_id: str) -> Optional[ChannelValue]:
        """Read a channel value"""
        if channel_id not in self.channels:
            print(f"Channel {channel_id} not found")
            return None

        try:
            channel = self.channels[channel_id]
            return await channel.read()
        except Exception as e:
            print(f"Error reading channel {channel_id}: {e}")
            return None

    async def write_channel(self, channel_id: str, value: Any) -> bool:
        """Write a channel value"""
        if channel_id not in self.channels:
            print(f"Channel {channel_id} not found")
            return False

        try:
            channel = self.channels[channel_id]
            await channel.write(value)
            return True
        except Exception as e:
            print(f"Error writing channel {channel_id}: {e}")
            return False

    def get_channel_config(self, channel_id: str) -> Optional[ChannelConfig]:
        """Get channel configuration"""
        return self.channel_configs.get(channel_id)

    def get_available_channels(self) -> List[str]:
        """Get list of available channel IDs"""
        return list(self.channels.keys())

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        if channel_id not in self.channels:
            return None

        config = self.channel_configs.get(channel_id)
        if not config:
            return None

        return {
            'id': channel_id,
            'type': config.type.value,
            'pin': config.pin,
            'scaling': config.scaling,
            'calibration': config.calibration
        }

    async def shutdown(self) -> None:
        """Shutdown all devices"""
        # Shutdown channels
        for channel_id, channel in self.channels.items():
            try:
                # Note: This assumes channels have a destroy method
                # In a real implementation, this would be handled by the plugin
                pass
            except Exception as e:
                print(f"Error shutting down channel {channel_id}: {e}")

        self.channels.clear()
        self.channel_configs.clear()

        # Shutdown bus plugins
        for bus_id, bus_plugin in self.bus_plugins.items():
            try:
                await bus_plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down bus {bus_id}: {e}")

        self.bus_plugins.clear()
        self.bus_configs.clear()
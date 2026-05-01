import logging
import os
from typing import Dict, Optional, Type, List
from core.base_device import BaseDevice
from core.plugin_loader import PluginLoader
from core.config_manager import ConfigManager
from models.config import DeviceConfig

logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self, device_dir: str, config_manager: ConfigManager):
        self.device_dir = device_dir
        self.config_manager = config_manager
        self.devices: Dict[str, BaseDevice] = {}
        self.device_configs: Dict[str, DeviceConfig] = {}
        self.device_config_files: Dict[str, str] = {} # device_id -> config_name
        self._system_connected = False

    def discover_and_initialize(self):
        """
        Discovers device plugins and initializes them with their respective configs.
        Creates default JSON configs for discovered plugins if none exist.
        """
        plugin_classes = PluginLoader.discover_plugins(self.device_dir)
        plugin_map: Dict[str, Type[BaseDevice]] = {cls.__name__: cls for cls in plugin_classes}
        
        # Temporary ConfigManager pointed at device directory for per-device configs
        device_config_manager = ConfigManager(self.device_dir)

        # 1. Check for plugins without any config and create defaults
        existing_json_files = [f for f in os.listdir(self.device_dir) if f.endswith(".json") and f.startswith("device_")]
        
        # We also need to know which plugins are ALREADY referenced in existing JSONs
        referenced_plugins = set()
        for filename in existing_json_files:
            try:
                with open(os.path.join(self.device_dir, filename), 'r') as f:
                    data = json.load(f)
                    if "plugin" in data:
                        referenced_plugins.add(data["plugin"])
            except:
                pass

        # For plugins not referenced anywhere, create a default JSON
        for plugin_name in plugin_map:
            if plugin_name not in referenced_plugins:
                default_config_name = f"device_{plugin_name.lower()}"
                if not os.path.exists(os.path.join(self.device_dir, f"{default_config_name}.json")):
                    config = DeviceConfig(
                        id=f"{plugin_name.lower()}_1",
                        plugin=plugin_name,
                        enabled=False,
                        connection_params={},
                        settings={}
                    )
                    device_config_manager.save_config(default_config_name, config)
                    logger.info(f"Created default config for new plugin: {default_config_name}.json")
                    existing_json_files.append(f"{default_config_name}.json")

        # 2. Load all device-specific configurations
        for filename in existing_json_files:
            config_name = filename[:-5]
            try:
                config = device_config_manager.load_config(config_name, DeviceConfig)
                
                plugin_class = plugin_map.get(config.plugin)
                if not plugin_class:
                    logger.error(f"Plugin class '{config.plugin}' not found for device '{config.id}'")
                    continue

                # Instantiate the device
                device_instance = plugin_class()
                device_instance.enabled = config.enabled
                
                # Store by the ID specified in the config
                device_id = config.id
                self.devices[device_id] = device_instance
                self.device_configs[device_id] = config
                self.device_config_files[device_id] = config_name
                
                logger.info(f"Initialized device: {device_id} using {config.plugin} plugin ({config_name}.json)")
            except Exception as e:
                logger.error(f"Failed to initialize device config {filename}: {e}")

    async def connect_all(self) -> Dict[str, Dict[str, str]]:
        """
        Attempts to connect all initialized devices.
        Returns a dictionary of results per device.
        """
        import asyncio
        results = {}
        for device_id, device in self.devices.items():
            config = self.device_configs[device_id]
            if not config.enabled:
                results[device_id] = {"status": "skipped", "message": "Device disabled"}
                continue
                
            try:
                logger.info(f"Connecting to device {device_id}...")
                # Offload to thread to avoid blocking event loop
                await asyncio.to_thread(device.connect, config.connection_params)
                logger.info(f"Successfully connected device: {device_id}")
                results[device_id] = {"status": "success", "message": "Connected"}
            except Exception as e:
                logger.error(f"Failed to connect device {device_id}: {e}")
                results[device_id] = {"status": "error", "message": str(e)}
                
        self._system_connected = True
        return results

    async def disconnect_all(self):
        """
        Gracefully disconnects all devices.
        """
        import asyncio
        for device_id, device in self.devices.items():
            try:
                # Offload to thread to avoid blocking event loop
                await asyncio.to_thread(device.disconnect)
                logger.info(f"Disconnected device: {device_id}")
            except Exception as e:
                logger.error(f"Error disconnecting device {device_id}: {e}")
        self._system_connected = False

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        return self.devices.get(device_id)

    def get_all_devices(self) -> Dict[str, BaseDevice]:
        return self.devices

    async def toggle_device(self, device_id: str, enabled: bool):
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        device.enabled = enabled
        
        # Update config
        config = self.device_configs[device_id]
        config.enabled = enabled
        
        # Save to file
        config_name = self.device_config_files[device_id]
        device_config_manager = ConfigManager(self.device_dir)
        device_config_manager.save_config(config_name, config)
        
        logger.info(f"Device {device_id} is now {'enabled' if enabled else 'disabled'}")
        
        # Connection management based on toggle
        # Only auto-connect if the system is globally in the 'connected' state
        import asyncio
        if enabled:
            if not device.is_connected and self._system_connected:
                try:
                    logger.info(f"Auto-connecting enabled device: {device_id}")
                    # Offload to thread to avoid blocking event loop
                    await asyncio.to_thread(device.connect, config.connection_params)
                except Exception as e:
                    logger.error(f"Auto-connect failed for {device_id}: {e}")
        else:
            if device.is_connected:
                try:
                    # Offload to thread to avoid blocking event loop
                    await asyncio.to_thread(device.disconnect)
                except Exception as e:
                    logger.error(f"Disconnect failed for {device_id}: {e}")

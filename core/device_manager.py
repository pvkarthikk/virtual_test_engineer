import logging
import os
from typing import Dict, Optional, Type
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

    def discover_and_initialize(self):
        """
        Discovers device plugins and initializes them with their respective configs.
        """
        plugin_classes = PluginLoader.discover_plugins(self.device_dir)
        
        # Temporary ConfigManager pointed at device directory for per-device configs
        device_config_manager = ConfigManager(self.device_dir)

        for cls in plugin_classes:
            # convention: device_name.py has device_name.json
            # PluginLoader currently gives us classes. 
            # We might need the filename or a way to derive the config name.
            # Let's assume the class name or a property can help, 
            # but for now we'll look for device_<classname_lower>.json
            config_name = f"device_{cls.__name__.lower()}"
            
            try:
                # Load device-specific configuration
                config = device_config_manager.load_config(config_name, DeviceConfig)
                
                # Instantiate the device
                device_instance = cls()
                
                # Store by the ID specified in the config
                device_id = config.id
                self.devices[device_id] = device_instance
                self.device_configs[device_id] = config
                
                logger.info(f"Initialized device: {device_id} using {config_name}.json")
            except Exception as e:
                logger.error(f"Failed to initialize device class {cls.__name__}: {e}")

    def connect_all(self):
        """
        Attempts to connect all initialized devices.
        Failed connections are logged but don't stop the process.
        """
        for device_id, device in self.devices.items():
            config = self.device_configs[device_id]
            try:
                logger.info(f"Connecting to device {device_id}...")
                device.connect(config.connection_params)
                logger.info(f"Successfully connected device: {device_id}")
            except Exception as e:
                logger.error(f"Failed to connect device {device_id}: {e}")

    def disconnect_all(self):
        """
        Gracefully disconnects all devices.
        """
        for device_id, device in self.devices.items():
            try:
                device.disconnect()
                logger.info(f"Disconnected device: {device_id}")
            except Exception as e:
                logger.error(f"Error disconnecting device {device_id}: {e}")

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        return self.devices.get(device_id)

    def get_all_devices(self) -> Dict[str, BaseDevice]:
        return self.devices

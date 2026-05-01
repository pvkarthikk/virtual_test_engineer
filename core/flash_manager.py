import logging
import os
import asyncio
from typing import Dict, Optional, Type, List, Any
from core.base_flash import BaseFlash
from core.plugin_loader import PluginLoader
from core.config_manager import ConfigManager
from models.config import FlashConfig

logger = logging.getLogger(__name__)

class FlashManager:
    def __init__(self, device_dir: str, config_manager: ConfigManager):
        self.device_dir = device_dir
        self.config_manager = config_manager
        self.flash_protocols: Dict[str, BaseFlash] = {}
        self.flash_configs: Dict[str, FlashConfig] = {}
        self.flash_config_files: Dict[str, str] = {} # flash_id -> config_name

    def discover_and_initialize(self):
        """
        Discovers flash plugins and initializes them with their respective configs.
        Creates default JSON configs for discovered flash plugins if none exist.
        """
        plugin_classes = PluginLoader.discover_plugins(
            self.device_dir, 
            pattern="flash_", 
            base_class=BaseFlash
        )
        plugin_map: Dict[str, Type[BaseFlash]] = {cls.__name__: cls for cls in plugin_classes}
        
        # Temporary ConfigManager pointed at device directory for per-protocol configs
        flash_config_manager = ConfigManager(self.device_dir)

        # 1. Check for plugins without any config and create defaults
        existing_json_files = []
        if os.path.exists(self.device_dir):
            existing_json_files = [f for f in os.listdir(self.device_dir) if f.endswith(".json") and f.startswith("flash_")]
        
        # Track which plugins are referenced in existing JSONs
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
                default_config_name = f"flash_{plugin_name.lower()}"
                if not os.path.exists(os.path.join(self.device_dir, f"{default_config_name}.json")):
                    config = FlashConfig(
                        id=f"{plugin_name.lower()}_1",
                        plugin=plugin_name,
                        enabled=False,
                        connection_params={},
                        settings={}
                    )
                    flash_config_manager.save_config(default_config_name, config)
                    logger.info(f"Created default config for new flash plugin: {default_config_name}.json")
                    existing_json_files.append(f"{default_config_name}.json")

        # 2. Load all flash-specific configurations
        for filename in existing_json_files:
            config_name = filename[:-5]
            try:
                # Load flash-specific configuration
                config = flash_config_manager.load_config(config_name, FlashConfig)
                
                plugin_class = plugin_map.get(config.plugin)
                if not plugin_class:
                    logger.error(f"Flash plugin class '{config.plugin}' not found for protocol '{config.id}'")
                    continue

                # Instantiate the protocol
                flash_instance = plugin_class()
                flash_instance.enabled = config.enabled
                
                # Store by the ID specified in the config
                flash_id = config.id
                self.flash_protocols[flash_id] = flash_instance
                self.flash_configs[flash_id] = config
                self.flash_config_files[flash_id] = config_name
                
                logger.info(f"Initialized flash protocol: {flash_id} using {config.plugin} plugin ({config_name}.json)")
            except Exception as e:
                logger.error(f"Failed to initialize flash config {filename}: {e}")

    def get_protocol(self, flash_id: str) -> Optional[BaseFlash]:
        return self.flash_protocols.get(flash_id)

    def get_all_protocols(self) -> Dict[str, BaseFlash]:
        return self.flash_protocols

    def get_all_configs(self) -> Dict[str, FlashConfig]:
        return self.flash_configs

    async def connect_target(self, flash_id: str):
        """Connects to a specific flash target."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        config = self.flash_configs[flash_id]
        await asyncio.to_thread(protocol.connect, config.connection_params)

    async def disconnect_target(self, flash_id: str):
        """Disconnects from a specific flash target."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        await asyncio.to_thread(protocol.disconnect)

    async def start_flash(self, flash_id: str, data: bytes, params: dict) -> str:
        """Starts a flash operation."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        return await asyncio.to_thread(protocol.flash, data, params)

    def get_flash_status(self, flash_id: str, execution_id: str) -> dict:
        """Gets the status of a flash operation."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        return protocol.get_status(execution_id)

    def get_flash_log(self, flash_id: str, execution_id: str) -> List[str]:
        """Gets the logs of a flash operation."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        return protocol.get_log(execution_id)

    async def abort_flash(self, flash_id: str, execution_id: str):
        """Aborts a flash operation."""
        protocol = self.get_protocol(flash_id)
        if not protocol:
            raise ValueError(f"Flash protocol {flash_id} not found")
        
        await asyncio.to_thread(protocol.abort, execution_id)

    async def connect_all(self):
        """Connects all configured flash targets."""
        for flash_id in list(self.flash_protocols.keys()):
            try:
                await self.connect_target(flash_id)
            except Exception as e:
                logger.error(f"Error connecting flash target {flash_id}: {e}")

    async def disconnect_all(self):
        """Disconnects all active flash targets."""
        for flash_id in list(self.flash_protocols.keys()):
            try:
                await self.disconnect_target(flash_id)
            except Exception as e:
                logger.error(f"Error disconnecting flash target {flash_id}: {e}")

#!/usr/bin/env python3
"""
Virtual Test Engineer - Plugin Manager
"""

import asyncio
import importlib
import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from .types import DevicePlugin, BusPlugin, PluginConfig, ValidationResult


class PluginManager:
    """Manages plugin loading and lifecycle"""

    def __init__(self, plugins_dir: str = "drivers/plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, DevicePlugin] = {}
        self.bus_plugins: Dict[str, BusPlugin] = {}
        self.plugin_manifests: Dict[str, Dict[str, Any]] = {}

    async def discover_plugins(self) -> List[str]:
        """Discover available plugins"""
        if not self.plugins_dir.exists():
            return []

        plugins = []
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "plugin.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            plugin_name = manifest.get('name')
                            if plugin_name:
                                self.plugin_manifests[plugin_name] = manifest
                                plugins.append(plugin_name)
                    except Exception as e:
                        print(f"Error loading plugin manifest {manifest_path}: {e}")

        return plugins

    async def load_plugin(self, plugin_name: str, config: PluginConfig) -> Optional[DevicePlugin]:
        """Load a plugin by name"""
        if plugin_name not in self.plugin_manifests:
            print(f"Plugin {plugin_name} not found in manifests")
            return None

        manifest = self.plugin_manifests[plugin_name]
        entry_point = manifest.get('entry_point')

        if not entry_point:
            print(f"No entry point defined for plugin {plugin_name}")
            return None

        plugin_dir = self.plugins_dir / plugin_name
        plugin_path = plugin_dir / entry_point

        if not plugin_path.exists():
            print(f"Plugin entry point {plugin_path} not found")
            return None

        try:
            # Add plugin directory to Python path
            import sys
            sys.path.insert(0, str(plugin_dir))

            # Import the plugin module
            module_name = entry_point.replace('.py', '')
            module = importlib.import_module(module_name)

            # Find the plugin class (assuming it's the only class that inherits from DevicePlugin)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, DevicePlugin) and
                    attr != DevicePlugin):
                    plugin_class = attr
                    break

            if not plugin_class:
                print(f"No DevicePlugin subclass found in {module_name}")
                return None

            # Instantiate and initialize the plugin
            plugin_instance = plugin_class()
            await plugin_instance.initialize(config)

            self.loaded_plugins[plugin_name] = plugin_instance
            print(f"Successfully loaded plugin {plugin_name}")

            return plugin_instance

        except Exception as e:
            print(f"Error loading plugin {plugin_name}: {e}")
            return None

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self.loaded_plugins:
            return False

        try:
            plugin = self.loaded_plugins[plugin_name]
            await plugin.shutdown()
            del self.loaded_plugins[plugin_name]
            print(f"Successfully unloaded plugin {plugin_name}")
            return True
        except Exception as e:
            print(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[DevicePlugin]:
        """Get a loaded plugin instance"""
        return self.loaded_plugins.get(plugin_name)

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self.loaded_plugins.keys())

    def get_available_plugins(self) -> List[str]:
        """Get list of available plugin names"""
        return list(self.plugin_manifests.keys())

    async def validate_plugin_config(self, plugin_name: str, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return ValidationResult(valid=False, errors=[f"Plugin {plugin_name} not loaded"])

        return plugin.validate_config(config)

    async def shutdown_all(self) -> None:
        """Shutdown all loaded plugins"""
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)
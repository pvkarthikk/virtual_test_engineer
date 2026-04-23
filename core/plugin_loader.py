import importlib.util
import inspect
import os
import logging
from typing import List, Type
from core.base_device import BaseDevice

logger = logging.getLogger(__name__)

class PluginLoader:
    @staticmethod
    def discover_plugins(directory: str) -> List[Type[BaseDevice]]:
        """
        Scans the specified directory for 'device_*.py' files and returns
        a list of classes that implement BaseDevice.
        """
        plugins = []
        if not os.path.exists(directory):
            logger.error(f"Plugin directory {directory} does not exist.")
            return plugins

        for filename in os.listdir(directory):
            if filename.startswith("device_") and filename.endswith(".py"):
                file_path = os.path.join(directory, filename)
                module_name = filename[:-3]
                
                try:
                    # Dynamic import of the plugin module
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Inspect the module for classes inheriting from BaseDevice
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseDevice) and 
                            obj is not BaseDevice):
                            plugins.append(obj)
                            logger.info(f"Discovered plugin: {name} in {filename}")
                except Exception as e:
                    logger.error(f"Failed to load plugin module {filename}: {e}")
        
        return plugins

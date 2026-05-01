import json
import os
import shutil
import logging
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def get_file_path(self, config_type: str) -> str:
        # For per-device config, config_type might be 'device_<name>'
        return os.path.join(self.config_dir, f"{config_type}.json")

    def load_config(self, config_type: str, model_class: Type[T]) -> T:
        """
        Loads a configuration file, with fallback to .bak if primary is corrupted.
        If both fail, returns a default instance of the model if possible.
        """
        file_path = self.get_file_path(config_type)
        bak_path = file_path + ".bak"

        # Try primary file
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return model_class.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to load primary config {file_path}: {e}. Trying backup...")

        # Try backup file
        if os.path.exists(bak_path):
            try:
                with open(bak_path, "r") as f:
                    data = json.load(f)
                return model_class.model_validate(data)
            except Exception as e:
                logger.error(f"Failed to load backup config {bak_path}: {e}.")

        # If both fail, create a fresh default or raise if no defaults
        logger.warning(f"No valid config found for {config_type}. Attempting to return default and persist it.")
        try:
            # This will only work if all fields in model_class are optional or have defaults
            config = model_class()
            self.save_config(config_type, config)
            return config
        except Exception as e:
            logger.error(f"Could not create default config for {config_type}: {e}")
            raise

    def save_config(self, config_type: str, config: BaseModel):
        """
        Saves a configuration file, creating a .bak copy of the existing file first.
        """
        file_path = self.get_file_path(config_type)
        bak_path = file_path + ".bak"

        # Create backup before write
        if os.path.exists(file_path):
            try:
                shutil.copy2(file_path, bak_path)
                logger.info(f"Created backup for {config_type}")
            except Exception as e:
                logger.error(f"Failed to create backup for {config_type}: {e}")

        # Save new content
        try:
            with open(file_path, "w") as f:
                f.write(config.model_dump_json(indent=2))
            logger.info(f"Saved config {config_type}")
        except Exception as e:
            logger.error(f"Failed to save config {config_type}: {e}")
            raise

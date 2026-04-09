#!/usr/bin/env python3
"""
Client Configuration Management
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ClientConfig:
    """Client configuration"""
    server_url: str = "http://localhost:8080"
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    log_level: str = "INFO"
    auth_token: Optional[str] = None
    ssl_verify: bool = True

    # Test-specific settings
    default_test_timeout: float = 300.0
    default_poll_interval: float = 1.0

    # Flashing settings
    default_flash_timeout: float = 300.0
    default_flash_protocol: str = "avrdude"

    # DUT profiles
    default_dut_profile: Optional[str] = None


class ConfigManager:
    """Configuration manager for client"""

    def __init__(self, config_file: str = "~/.vte_client/config.json"):
        self.config_file = Path(config_file).expanduser()
        self.config = ClientConfig()

    def load_config(self) -> ClientConfig:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Update config with loaded data
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

        return self.config

    def save_config(self) -> None:
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)

    def update_config(self, **kwargs) -> None:
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                print(f"Warning: Unknown config key: {key}")

    def get_config(self) -> ClientConfig:
        """Get current configuration"""
        return self.config

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = ClientConfig()
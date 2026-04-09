"""
Virtual Test Engineer Python Client

A comprehensive client library for interacting with the Virtual Test Engineer
REST API for automated testing of embedded systems and ECUs.
"""

from .vte_client import VirtualTestEngineerClient, ChannelInfo, TestBenchStatus
from .config_manager import ConfigManager, ClientConfig

__version__ = "1.0.0"
__all__ = [
    "VirtualTestEngineerClient",
    "ChannelInfo",
    "TestBenchStatus",
    "ConfigManager",
    "ClientConfig"
]
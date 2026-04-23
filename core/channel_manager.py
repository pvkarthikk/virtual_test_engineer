import logging
from typing import Dict, List, Any, Optional
from core.device_manager import DeviceManager
from models.config import ChannelConfig
from core.stream_manager import StreamManager

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self, device_manager: DeviceManager, stream_manager: Optional[StreamManager] = None):
        self.device_manager = device_manager
        self.stream_manager = stream_manager
        self.channels: Dict[str, ChannelConfig] = {}

    def initialize_channels(self, channel_configs: List[ChannelConfig]):
        """
        Loads channel configurations and validates their mappings to devices and signals.
        """
        self.channels = {cfg.channel_id: cfg for cfg in channel_configs}
        self.validate_mappings()
        logger.info(f"Initialized {len(self.channels)} channels.")

    def validate_mappings(self):
        """
        Verifies that all channels map to existing devices and signals.
        """
        for ch_id, cfg in self.channels.items():
            device = self.device_manager.get_device(cfg.device_id)
            if not device:
                logger.error(f"Channel '{ch_id}' maps to unknown device '{cfg.device_id}'")
                continue
            
            try:
                signals = device.get_signals()
                signal_ids = [s.signal_id for s in signals]
                if cfg.signal_id not in signal_ids:
                    logger.error(f"Channel '{ch_id}' maps to unknown signal '{cfg.signal_id}' on device '{cfg.device_id}'")
            except Exception as e:
                logger.warning(f"Could not verify signals for device '{cfg.device_id}': {e}")

    def read_channel(self, channel_id: str) -> Any:
        """
        Reads a value from a channel, applying scaling (Raw -> Value).
        Equation: Value = (Raw * Resolution) + Offset
        """
        cfg = self.channels.get(channel_id)
        if not cfg:
            raise ValueError(f"Channel '{channel_id}' not found")

        device = self.device_manager.get_device(cfg.device_id)
        if not device:
            raise RuntimeError(f"Device '{cfg.device_id}' for channel '{channel_id}' is not initialized or connected")

        # Read raw value from device plugin
        raw_value = device.read_signal(cfg.signal_id)
        
        # Apply scaling
        scaled_value = (raw_value * cfg.properties.resolution) + cfg.properties.offset
        
        if self.stream_manager:
            self.stream_manager.push_channel_update(channel_id, scaled_value)
            logger.info(f"Channel READ: {channel_id} = {scaled_value:.2f} {cfg.properties.unit}")
            
        return scaled_value

    def write_channel(self, channel_id: str, value: float):
        """
        Writes a value to a channel after validation and scaling (Value -> Raw).
        Equation: Raw = (Value - Offset) / Resolution
        """
        cfg = self.channels.get(channel_id)
        if not cfg:
            raise ValueError(f"Channel '{channel_id}' not found")

        # 1. Logical Bounds Check (Channel Level)
        if not (cfg.properties.min <= value <= cfg.properties.max):
            raise ValueError(
                f"Value {value} is out of bounds for channel '{channel_id}' "
                f"(Valid range: {cfg.properties.min} to {cfg.properties.max} {cfg.properties.unit})"
            )

        device = self.device_manager.get_device(cfg.device_id)
        if not device:
            raise RuntimeError(f"Device '{cfg.device_id}' for channel '{channel_id}' is not initialized or connected")

        # 2. Scaling to Raw value
        # Handle potential division by zero if resolution is 0 (though it shouldn't be)
        if cfg.properties.resolution == 0:
            raw_value = value - cfg.properties.offset
        else:
            raw_value = (value - cfg.properties.offset) / cfg.properties.resolution
        
        # 3. Hardware Write (Device plugin performs physical signal-level bounds checking)
        device.write_signal(cfg.signal_id, raw_value)
        
        # 4. Push update to stream subscribers
        if self.stream_manager:
            self.stream_manager.push_channel_update(channel_id, value)
            logger.info(f"Channel WRITE: {channel_id} = {value} {cfg.properties.unit} (Raw: {raw_value:.2f})")

    def get_channel_info(self, channel_id: str) -> Optional[ChannelConfig]:
        return self.channels.get(channel_id)

    def get_all_channels(self) -> List[ChannelConfig]:
        return list(self.channels.values())

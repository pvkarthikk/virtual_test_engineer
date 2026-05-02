import logging
import asyncio
import math
from typing import Dict, List, Any, Optional
from core.device_manager import DeviceManager
from core.signal_registry import SignalRegistry
from models.config import ChannelConfig, LinearConversion, PolynomialConversion, LutConversion
from core.stream_manager import StreamManager
from core.converters import Converter, LinearConverter, PolynomialConverter, LutConverter

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self, device_manager: DeviceManager, stream_manager: Optional[StreamManager] = None):
        self.device_manager = device_manager
        self.stream_manager = stream_manager
        self.channels: Dict[str, ChannelConfig] = {}
        self.converters: Dict[str, Converter] = {}

    def initialize_channels(self, channel_configs: List[ChannelConfig]):
        """
        Loads channel configurations and validates their mappings to devices and signals.
        """
        self.channels = {cfg.channel_id: cfg for cfg in channel_configs}
        self.converters = {}
        
        for ch_id, cfg in self.channels.items():
            conv_cfg = cfg.properties.conversion
            if isinstance(conv_cfg, LinearConversion):
                self.converters[ch_id] = LinearConverter(conv_cfg.resolution, conv_cfg.offset)
            elif isinstance(conv_cfg, PolynomialConversion):
                # Use a wide default range for raw bounds; device plugin clamps it physically
                self.converters[ch_id] = PolynomialConverter(conv_cfg.coefficients, -1e6, 1e6)
            elif isinstance(conv_cfg, LutConversion):
                self.converters[ch_id] = LutConverter(conv_cfg.table)

        self.validate_mappings()
        logger.info(f"Initialized {len(self.channels)} channels.")

    def validate_mappings(self):
        """
        Verifies that all channels map to existing devices and signals, and
        cross-validates signal definitions and channel properties against the
        signal type registry (``config/signal_types.json``).

        All registry mismatches are reported as warnings — they do not prevent
        startup but indicate potential misconfiguration.
        """
        registry = SignalRegistry()

        for ch_id, cfg in self.channels.items():
            device = self.device_manager.get_device(cfg.device_id)
            if not device:
                logger.error(f"Channel '{ch_id}' maps to unknown device '{cfg.device_id}'")
                continue

            try:
                signals = device.get_signals()
                signal_map = {s.signal_id: s for s in signals}

                if cfg.signal_id not in signal_map:
                    logger.error(
                        f"Channel '{ch_id}' maps to unknown signal '{cfg.signal_id}' "
                        f"on device '{cfg.device_id}'"
                    )
                    continue

                # --- Validate signal definition against the registry ---
                signal = signal_map[cfg.signal_id]
                sig_warnings = registry.validate_signal(signal)
                for w in sig_warnings:
                    logger.warning(f"[SignalRegistry] Channel '{ch_id}' / Signal '{cfg.signal_id}': {w}")

                # --- Validate channel properties against the registry ---
                ch_sig_type = cfg.properties.signal_type
                if ch_sig_type:
                    typedef = registry.get(ch_sig_type)
                    if typedef is None:
                        logger.warning(
                            f"[SignalRegistry] Channel '{ch_id}' references unknown "
                            f"signal_type '{ch_sig_type}' in its properties."
                        )
                    else:
                        if typedef.unit and cfg.properties.unit and cfg.properties.unit != typedef.unit:
                            logger.warning(
                                f"[SignalRegistry] Channel '{ch_id}': unit '{cfg.properties.unit}' "
                                f"does not match registry unit '{typedef.unit}' for type '{ch_sig_type}'."
                            )
                        if cfg.properties.min < typedef.min_physical:
                            logger.warning(
                                f"[SignalRegistry] Channel '{ch_id}': min {cfg.properties.min} is below "
                                f"registry min_physical {typedef.min_physical} for type '{ch_sig_type}'."
                            )
                        if cfg.properties.max > typedef.max_physical:
                            logger.warning(
                                f"[SignalRegistry] Channel '{ch_id}': max {cfg.properties.max} exceeds "
                                f"registry max_physical {typedef.max_physical} for type '{ch_sig_type}'."
                            )

            except Exception as e:
                logger.warning(f"Could not verify signals for device '{cfg.device_id}': {e}")

    def _get_converter(self, channel_id: str, cfg: ChannelConfig) -> Converter:
        if channel_id not in self.converters:
            conv_cfg = cfg.properties.conversion
            if isinstance(conv_cfg, LinearConversion):
                self.converters[channel_id] = LinearConverter(conv_cfg.resolution, conv_cfg.offset)
            elif isinstance(conv_cfg, PolynomialConversion):
                self.converters[channel_id] = PolynomialConverter(conv_cfg.coefficients, -1e6, 1e6)
            elif isinstance(conv_cfg, LutConversion):
                self.converters[channel_id] = LutConverter(conv_cfg.table)
        return self.converters[channel_id]

    def get_scaled_value(self, cfg: ChannelConfig, raw_value: float) -> float:
        """
        Applies scaling (Raw -> Value) using the channel's configured converter.
        """
        converter = self._get_converter(cfg.channel_id, cfg)
        return converter.to_physical(raw_value)

    async def read_channel(self, channel_id: str) -> Any:
        """
        Reads a value from a channel, applying scaling (Raw -> Value).
        Equation: Value = (Raw * Resolution) + Offset
        """
        cfg = self.channels.get(channel_id)
        if not cfg:
            raise ValueError(f"Channel '{channel_id}' not found")

        device = self.device_manager.get_device(cfg.device_id)
        if not device or not device.is_connected:
            raise RuntimeError(f"Device '{cfg.device_id}' for channel '{channel_id}' is not connected")

        # Read raw value from device plugin - Offload to thread to avoid blocking event loop
        raw_value = await asyncio.to_thread(device.read_signal, cfg.signal_id)
        
        # Apply scaling
        scaled_value = self.get_scaled_value(cfg, raw_value)
        logger.debug(f"Channel READ: {channel_id} = {scaled_value:.2f} {cfg.properties.unit}")
        return scaled_value

    async def write_channel(self, channel_id: str, value: float):
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
        if not device or not device.is_connected:
            raise RuntimeError(f"Device '{cfg.device_id}' for channel '{channel_id}' is not connected")

        # 2. Scaling to Raw value
        converter = self._get_converter(channel_id, cfg)
        raw_value = converter.to_raw(value)
        
        # 3. Hardware Write (Device plugin performs physical signal-level bounds checking)
        # Offload to thread to avoid blocking event loop
        await asyncio.to_thread(device.write_signal, cfg.signal_id, raw_value)
        
        # 4. Push update to stream subscribers
        if self.stream_manager:
            self.stream_manager.push_channel_update(channel_id, value)
            cfg.properties.value = value  # Update memory cache
            logger.info(f"Channel WRITE: {channel_id} = {value} {cfg.properties.unit} (Raw: {raw_value:.2f})")

    def get_channel_info(self, channel_id: str) -> Optional[ChannelConfig]:
        return self.channels.get(channel_id)

    def get_all_channels(self) -> List[ChannelConfig]:
        return list(self.channels.values())

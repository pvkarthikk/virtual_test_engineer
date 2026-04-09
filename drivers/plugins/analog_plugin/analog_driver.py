#!/usr/bin/env python3
"""
Analog Plugin - Simulated ADC/DAC operations for testing
"""

import asyncio
import random
from typing import Dict, Any, Optional

from ...core.types import (
    DevicePlugin, Channel, ChannelConfig, ChannelType, ChannelValue,
    DeviceCapabilities, PluginConfig, ValidationResult, create_timestamp
)


class AnalogChannel:
    """Simulated analog channel"""

    def __init__(self, channel_number: int, channel_type: ChannelType):
        self.channel_number = channel_number
        self.channel_type = channel_type
        self.value = 0.0
        self.resolution = 12  # 12-bit ADC

    def read_voltage(self) -> float:
        """Read analog voltage (0-5V)"""
        if self.channel_type == ChannelType.ANALOG_INPUT:
            # Simulate ADC reading
            raw_value = random.randint(0, 2**self.resolution - 1)
            voltage = (raw_value / (2**self.resolution - 1)) * 5.0
            return voltage
        else:
            return self.value

    def write_voltage(self, voltage: float) -> None:
        """Write analog voltage"""
        self.value = max(0.0, min(5.0, voltage))


class AnalogPlugin(DevicePlugin):
    """Analog plugin implementation"""

    def __init__(self):
        self.adc_channels: Dict[int, AnalogChannel] = {}
        self.dac_channels: Dict[int, AnalogChannel] = {}
        self.channels: Dict[str, AnalogChannelWrapper] = {}
        self.initialized = False

    async def initialize(self, config: PluginConfig) -> None:
        """Initialize the analog plugin"""
        print(f"Initializing Analog plugin with config: {config.config}")

        # Initialize ADC channels
        adc_channels = config.config.get('adc_channels', [])
        for ch_num in adc_channels:
            self.adc_channels[ch_num] = AnalogChannel(ch_num, ChannelType.ANALOG_INPUT)

        # Initialize DAC channels
        dac_channels = config.config.get('dac_channels', [])
        for ch_num in dac_channels:
            self.dac_channels[ch_num] = AnalogChannel(ch_num, ChannelType.ANALOG_OUTPUT)

        self.initialized = True
        print(f"Analog plugin initialized with {len(adc_channels)} ADC and {len(dac_channels)} DAC channels")

    async def shutdown(self) -> None:
        """Shutdown the analog plugin"""
        print("Shutting down Analog plugin")
        self.adc_channels.clear()
        self.dac_channels.clear()
        self.channels.clear()
        self.initialized = False

    def get_capabilities(self) -> DeviceCapabilities:
        """Get plugin capabilities"""
        return DeviceCapabilities(
            analog_inputs=len(self.adc_channels),
            analog_outputs=len(self.dac_channels)
        )

    def validate_config(self, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        errors = []

        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return ValidationResult(valid=False, errors=errors)

        adc_channels = config.get('adc_channels', [])
        dac_channels = config.get('dac_channels', [])

        if not isinstance(adc_channels, list):
            errors.append("'adc_channels' must be a list")
        else:
            for ch in adc_channels:
                if not isinstance(ch, int) or ch < 0:
                    errors.append(f"Invalid ADC channel number: {ch}")

        if not isinstance(dac_channels, list):
            errors.append("'dac_channels' must be a list")
        else:
            for ch in dac_channels:
                if not isinstance(ch, int) or ch < 0:
                    errors.append(f"Invalid DAC channel number: {ch}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def create_channel(self, channel_id: str, config: ChannelConfig) -> Channel:
        """Create an analog channel"""
        if not self.initialized:
            raise RuntimeError("Plugin not initialized")

        channel_number = config.pin
        if channel_number is None:
            raise ValueError(f"No channel number specified for channel {channel_id}")

        # Find the appropriate channel
        analog_channel = None
        if config.type == ChannelType.ANALOG_INPUT and channel_number in self.adc_channels:
            analog_channel = self.adc_channels[channel_number]
        elif config.type == ChannelType.ANALOG_OUTPUT and channel_number in self.dac_channels:
            analog_channel = self.dac_channels[channel_number]

        if not analog_channel:
            raise ValueError(f"Analog channel {channel_number} not configured in plugin")

        channel = AnalogChannelWrapper(channel_id, config, analog_channel)
        self.channels[channel_id] = channel

        print(f"Created analog channel {channel_id} (type: {config.type.value}, ch: {channel_number})")
        return channel

    async def destroy_channel(self, channel_id: str) -> None:
        """Destroy an analog channel"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            print(f"Destroyed analog channel {channel_id}")


class AnalogChannelWrapper(Channel):
    """Analog channel wrapper"""

    def __init__(self, channel_id: str, config: ChannelConfig, analog_channel: AnalogChannel):
        super().__init__(channel_id, config)
        self.analog_channel = analog_channel

    async def read(self) -> ChannelValue:
        """Read channel value"""
        voltage = self.analog_channel.read_voltage()

        # Apply scaling if configured
        value = voltage
        if self.config.scaling:
            input_range = self.config.scaling.get('input_range')
            output_range = self.config.scaling.get('output_range')
            if input_range and output_range:
                # Simple linear scaling
                input_min, input_max = input_range
                output_min, output_max = output_range
                if input_max != input_min:
                    value = output_min + (voltage - input_min) * (output_max - output_min) / (input_max - input_min)

        return ChannelValue(
            channel_id=self.channel_id,
            value=value,
            timestamp=create_timestamp(),
            quality="good",
            units=self.config.scaling.get('units') if self.config.scaling else "V",
            metadata={"raw_voltage": voltage}
        )

    async def write(self, value: Any) -> None:
        """Write channel value"""
        if isinstance(value, (int, float)):
            # Convert back to voltage if scaling was applied
            voltage = value
            if self.config.scaling:
                output_range = self.config.scaling.get('output_range')
                input_range = self.config.scaling.get('input_range')
                if output_range and input_range:
                    # Reverse scaling
                    output_min, output_max = output_range
                    input_min, input_max = input_range
                    if output_max != output_min:
                        voltage = input_min + (value - output_min) * (input_max - input_min) / (output_max - output_min)

            self.analog_channel.write_voltage(voltage)

    def get_state(self) -> Dict[str, Any]:
        """Get channel state"""
        return {
            "channel": self.config.pin,
            "type": self.config.type.value,
            "value": self.analog_channel.value,
            "resolution": self.analog_channel.resolution
        }
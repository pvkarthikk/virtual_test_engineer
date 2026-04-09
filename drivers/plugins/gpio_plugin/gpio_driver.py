#!/usr/bin/env python3
"""
GPIO Plugin - Simulated GPIO operations for testing
"""

import asyncio
import random
from typing import Dict, Any, Optional

from ...core.types import (
    DevicePlugin, Channel, ChannelConfig, ChannelType, ChannelValue,
    DeviceCapabilities, PluginConfig, ValidationResult, create_timestamp
)


class GPIOPin:
    """Simulated GPIO pin"""

    def __init__(self, pin_number: int, pin_type: ChannelType):
        self.pin_number = pin_number
        self.pin_type = pin_type
        self.value = 0
        self.pwm_duty_cycle = 0
        self.frequency = 1000

    def read(self) -> int:
        """Read pin value"""
        if self.pin_type == ChannelType.ANALOG_INPUT:
            # Simulate analog reading (0-1023)
            return random.randint(0, 1023)
        elif self.pin_type == ChannelType.DIGITAL_INPUT:
            # Simulate digital reading
            return random.choice([0, 1])
        else:
            return self.value

    def write(self, value: int) -> None:
        """Write pin value"""
        self.value = value
        if self.pin_type.name == "pwm":
            self.pwm_duty_cycle = value

    def set_pwm(self, duty_cycle: int, frequency: int = 1000) -> None:
        """Set PWM parameters"""
        self.pwm_duty_cycle = duty_cycle
        self.frequency = frequency


class GPIOPlugin(DevicePlugin):
    """GPIO plugin implementation"""

    def __init__(self):
        self.pins: Dict[int, GPIOPin] = {}
        self.channels: Dict[str, GPIOChannel] = {}
        self.initialized = False

    async def initialize(self, config: PluginConfig) -> None:
        """Initialize the GPIO plugin"""
        print(f"Initializing GPIO plugin with config: {config.config}")

        # Initialize pins from config
        pins = config.config.get('pins', [])
        for pin_num in pins:
            # Default to digital output, will be configured by channels
            self.pins[pin_num] = GPIOPin(pin_num, ChannelType.DIGITAL_OUTPUT)

        self.initialized = True
        print(f"GPIO plugin initialized with {len(pins)} pins")

    async def shutdown(self) -> None:
        """Shutdown the GPIO plugin"""
        print("Shutting down GPIO plugin")
        self.pins.clear()
        self.channels.clear()
        self.initialized = False

    def get_capabilities(self) -> DeviceCapabilities:
        """Get plugin capabilities"""
        return DeviceCapabilities(
            digital_inputs=16,
            digital_outputs=16,
            pwm_channels=6,
            interrupt_capable=True
        )

    def validate_config(self, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        errors = []

        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return ValidationResult(valid=False, errors=errors)

        pins = config.get('pins', [])
        if not isinstance(pins, list):
            errors.append("'pins' must be a list")
        else:
            for pin in pins:
                if not isinstance(pin, int) or pin < 0 or pin > 255:
                    errors.append(f"Invalid pin number: {pin}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def create_channel(self, channel_id: str, config: ChannelConfig) -> Channel:
        """Create a GPIO channel"""
        if not self.initialized:
            raise RuntimeError("Plugin not initialized")

        pin_number = config.pin
        if pin_number is None:
            raise ValueError(f"No pin number specified for channel {channel_id}")

        if pin_number not in self.pins:
            raise ValueError(f"Pin {pin_number} not configured in plugin")

        # Update pin type based on channel config
        pin = self.pins[pin_number]
        pin.pin_type = config.type

        channel = GPIOChannel(channel_id, config, pin)
        self.channels[channel_id] = channel

        print(f"Created GPIO channel {channel_id} on pin {pin_number}")
        return channel

    async def destroy_channel(self, channel_id: str) -> None:
        """Destroy a GPIO channel"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            print(f"Destroyed GPIO channel {channel_id}")


class GPIOChannel(Channel):
    """GPIO channel implementation"""

    def __init__(self, channel_id: str, config: ChannelConfig, pin: GPIOPin):
        super().__init__(channel_id, config)
        self.pin = pin

    async def read(self) -> ChannelValue:
        """Read channel value"""
        raw_value = self.pin.read()

        # Apply scaling if configured
        value = raw_value
        if self.config.scaling:
            input_range = self.config.scaling.get('input_range')
            output_range = self.config.scaling.get('output_range')
            if input_range and output_range:
                # Simple linear scaling
                input_min, input_max = input_range
                output_min, output_max = output_range
                if input_max != input_min:
                    value = output_min + (raw_value - input_min) * (output_max - output_min) / (input_max - input_min)

        return ChannelValue(
            channel_id=self.channel_id,
            value=value,
            timestamp=create_timestamp(),
            quality="good",
            units=self.config.scaling.get('units') if self.config.scaling else None,
            metadata={"raw_value": raw_value}
        )

    async def write(self, value: Any) -> None:
        """Write channel value"""
        if self.config.type.name == "pwm":
            # For PWM, value is duty cycle (0-100)
            duty_cycle = int(value)
            frequency = self.config.config.get('frequency', 1000) if self.config.config else 1000
            self.pin.set_pwm(duty_cycle, frequency)
        else:
            # Digital output
            self.pin.write(1 if value else 0)

    def get_state(self) -> Dict[str, Any]:
        """Get channel state"""
        return {
            "pin": self.config.pin,
            "type": self.config.type.value,
            "value": self.pin.value,
            "pwm_duty_cycle": getattr(self.pin, 'pwm_duty_cycle', None),
            "frequency": getattr(self.pin, 'frequency', None)
        }
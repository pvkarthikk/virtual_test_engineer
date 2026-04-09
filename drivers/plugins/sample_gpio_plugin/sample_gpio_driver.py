#!/usr/bin/env python3
"""
Sample GPIO Plugin - Demonstrates plugin development for Virtual Test Engineer
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional, List

from ...core.types import (
    DevicePlugin, Channel, ChannelConfig, ChannelType, ChannelValue,
    DeviceCapabilities, PluginConfig, ValidationResult
)


class SampleGPIOChannel(Channel):
    """Sample GPIO channel implementation"""

    def __init__(self, channel_id: str, config: ChannelConfig):
        super().__init__(channel_id, config)
        self.pin_number = config.pin or 0
        self.simulated_value = False
        self.pullup_enabled = config.config.get('pullup', False) if config.config else False
        self.interrupt_enabled = config.config.get('interrupt', False) if config.config else False
        self.last_change = time.time()

    async def read(self) -> ChannelValue:
        """Read GPIO channel value"""
        # Simulate GPIO reading
        if self.config.type == ChannelType.DIGITAL_INPUT:
            # Generate random input changes occasionally
            if random.random() < 0.1:  # 10% chance of change
                self.simulated_value = not self.simulated_value
                self.last_change = time.time()

        return ChannelValue(
            channel_id=self.channel_id,
            value=self.simulated_value,
            timestamp=time.time(),
            quality="good"
        )

    async def write(self, value: bool) -> None:
        """Write GPIO channel value"""
        if self.config.type == ChannelType.DIGITAL_OUTPUT:
            self.simulated_value = bool(value)
            self.last_change = time.time()


class SampleGPIOPlugin(DevicePlugin):
    """Sample GPIO plugin implementation"""

    def __init__(self):
        self.channels: Dict[str, SampleGPIOChannel] = {}
        self.pin_states: Dict[int, bool] = {}
        self.interrupt_callbacks: Dict[int, callable] = {}
        self.initialized = False

    async def initialize(self, config: PluginConfig) -> None:
        """Initialize the GPIO plugin"""
        print(f"Initializing Sample GPIO Plugin: {config.name}")

        # Parse configuration
        self.digital_inputs = config.config.get('digital_inputs', [])
        self.digital_outputs = config.config.get('digital_outputs', [])
        self.pwm_channels = config.config.get('pwm_channels', [])

        # Initialize pin states
        all_pins = set(self.digital_inputs + self.digital_outputs + self.pwm_channels)
        for pin in all_pins:
            self.pin_states[pin] = False

        print(f"Configured {len(self.digital_inputs)} inputs, {len(self.digital_outputs)} outputs")
        self.initialized = True

    async def shutdown(self) -> None:
        """Shutdown the GPIO plugin"""
        print("Shutting down Sample GPIO Plugin")
        self.channels.clear()
        self.pin_states.clear()
        self.interrupt_callbacks.clear()
        self.initialized = False

    def get_capabilities(self) -> DeviceCapabilities:
        """Get plugin capabilities"""
        return DeviceCapabilities(
            digital_inputs=len(self.digital_inputs),
            digital_outputs=len(self.digital_outputs),
            analog_inputs=0,  # This plugin doesn't support analog
            analog_outputs=0,
            pwm_channels=len(self.pwm_channels)
        )

    def validate_config(self, config: Any) -> ValidationResult:
        """Validate plugin configuration"""
        errors = []
        warnings = []

        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return ValidationResult(valid=False, errors=errors)

        # Validate digital inputs
        digital_inputs = config.get('digital_inputs', [])
        if not isinstance(digital_inputs, list):
            errors.append("digital_inputs must be a list")
        else:
            for pin in digital_inputs:
                if not isinstance(pin, int) or pin < 0 or pin > 40:
                    errors.append(f"Invalid digital input pin: {pin}")

        # Validate digital outputs
        digital_outputs = config.get('digital_outputs', [])
        if not isinstance(digital_outputs, list):
            errors.append("digital_outputs must be a list")
        else:
            for pin in digital_outputs:
                if not isinstance(pin, int) or pin < 0 or pin > 40:
                    errors.append(f"Invalid digital output pin: {pin}")

        # Check for pin conflicts
        all_pins = set(digital_inputs + digital_outputs)
        if len(all_pins) != len(digital_inputs) + len(digital_outputs):
            warnings.append("Some pins are configured for both input and output")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def create_channel(self, channel_id: str, config: ChannelConfig) -> Channel:
        """Create a GPIO channel instance"""
        if config.pin is None:
            raise ValueError(f"GPIO channel {channel_id} requires a pin number")

        # Validate pin is configured for this plugin
        if config.type == ChannelType.DIGITAL_INPUT and config.pin not in self.digital_inputs:
            raise ValueError(f"Pin {config.pin} not configured as digital input")
        elif config.type == ChannelType.DIGITAL_OUTPUT and config.pin not in self.digital_outputs:
            raise ValueError(f"Pin {config.pin} not configured as digital output")

        channel = SampleGPIOChannel(channel_id, config)
        self.channels[channel_id] = channel
        return channel

    async def destroy_channel(self, channel_id: str) -> None:
        """Destroy a GPIO channel instance"""
        if channel_id in self.channels:
            del self.channels[channel_id]

    # Plugin-specific methods

    async def set_pin_mode(self, pin: int, mode: str) -> None:
        """Set pin mode (input/output)"""
        if mode not in ['input', 'output']:
            raise ValueError(f"Invalid pin mode: {mode}")

        print(f"Setting pin {pin} to {mode} mode")

    async def enable_pullup(self, pin: int, enable: bool = True) -> None:
        """Enable/disable pullup resistor on pin"""
        if pin not in self.pin_states:
            raise ValueError(f"Pin {pin} not configured")

        print(f"{'Enabling' if enable else 'Disabling'} pullup on pin {pin}")

    async def set_interrupt_callback(self, pin: int, callback: callable) -> None:
        """Set interrupt callback for pin"""
        if pin not in self.digital_inputs:
            raise ValueError(f"Pin {pin} not configured as digital input")

        self.interrupt_callbacks[pin] = callback
        print(f"Interrupt callback set for pin {pin}")

    async def get_pin_state(self, pin: int) -> bool:
        """Get current pin state"""
        return self.pin_states.get(pin, False)

    async def simulate_pin_change(self, pin: int, new_state: bool) -> None:
        """Simulate a pin state change (for testing)"""
        if pin not in self.pin_states:
            raise ValueError(f"Pin {pin} not configured")

        old_state = self.pin_states[pin]
        self.pin_states[pin] = new_state

        # Trigger interrupt callback if set
        if pin in self.interrupt_callbacks and old_state != new_state:
            try:
                await self.interrupt_callbacks[pin](pin, old_state, new_state)
            except Exception as e:
                print(f"Error in interrupt callback for pin {pin}: {e}")


# Factory function for plugin instantiation
def create_plugin():
    """Create plugin instance"""
    return SampleGPIOPlugin()
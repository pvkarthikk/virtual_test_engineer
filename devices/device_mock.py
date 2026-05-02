from core.base_device import BaseDevice, SignalDefinition, SignalAnalog, SignalPWM
from typing import List, Any, Dict, Optional
import logging
import random
import time

logger = logging.getLogger(__name__)
def generate_mock_value(signal: SignalDefinition):
    val = random.uniform(signal.min, signal.max)
    return round(val / signal.resolution) * signal.resolution


class EngineMock:
    def __init__(self):
        self._throttle_pwm = 0 # 0 - 255 PWM
        self._engine_speed = 0 # 0 - 4095 volt
        self._throttle_percent = 0 # 0 - 100 %
        self._engine_speed_rpm = 0 # 0 - 5000 rpm
        self._idle_rpm = 800
        self._max_rpm = 5000
        
        # New non-linear sensor simulations
        self._temperature_c = 20.0  # Starts at 20C
        self._temperature_raw = 2500
        self._map_raw = 500
    
    @property
    def throttle_pwm(self) -> int:
        return self._throttle_pwm

    @throttle_pwm.setter
    def throttle_pwm(self, value: int):
        # 16-bit PWM where 32768 = 100% (0.00305 resolution)
        self._throttle_pwm = max(0, min(32768, value))
        self._throttle_percent = self._throttle_pwm * 0.00305

    @property
    def engine_speed(self) -> int:
        return self._engine_speed

    @property
    def temperature_raw(self) -> int:
        return self._temperature_raw

    @property
    def map_raw(self) -> int:
        return self._map_raw

    def update(self):
        # calculate engine rpm based on the throttle percent
        target_rpm = self._idle_rpm + (self._max_rpm - self._idle_rpm) * (self._throttle_percent / 100.0)
        
        # Add some jitter/noise
        noise = random.uniform(-50, 50)
        self._engine_speed_rpm = target_rpm + noise
        
        # Clamp RPM to physical limits
        self._engine_speed_rpm = max(0, min(self._max_rpm + 500, self._engine_speed_rpm))
        
        # convert engine rpm to 12-bit ADC counts (0-5V range where 4095 = 5000 RPM)
        raw_val = (self._engine_speed_rpm / 5000.0) * 4095.0
        self._engine_speed = max(0, min(4095, round(raw_val)))

        # ----------------------------------------------------
        # Simulate Coolant Temperature (Warms up as engine runs)
        # ----------------------------------------------------
        if self._engine_speed_rpm > 1000:
            self._temperature_c += (90.0 - self._temperature_c) * 0.05
        else:
            self._temperature_c += (90.0 - self._temperature_c) * 0.01

        # Add slight thermal noise so it visibly updates in the UI
        temp_with_noise = self._temperature_c + random.uniform(-0.5, 0.5)

        # NTC Inverse relation mapping to 12-bit ADC:
        if temp_with_noise <= -40: self._temperature_raw = 4000
        elif temp_with_noise <= 20: 
            self._temperature_raw = 4000 - ((temp_with_noise - -40) / 60.0) * 1500
        elif temp_with_noise <= 90:
            self._temperature_raw = 2500 - ((temp_with_noise - 20) / 70.0) * 1700
        elif temp_with_noise <= 150:
            self._temperature_raw = 800 - ((temp_with_noise - 90) / 60.0) * 700
        else:
            self._temperature_raw = 100
        self._temperature_raw = max(0, min(4095, round(self._temperature_raw)))

        # ----------------------------------------------------
        # Simulate MAP Sensor (Manifold Absolute Pressure)
        # ----------------------------------------------------
        # Higher throttle = less vacuum = higher pressure
        pressure_kpa = 30.0 + (self._throttle_percent * 0.7) - ((self._engine_speed_rpm - 800) * 0.005)
        # Add slight pressure fluctuations
        pressure_kpa += random.uniform(-1.0, 1.0)
        pressure_kpa = max(10.0, min(105.0, pressure_kpa))
        
        # Sensor curve: P(kPa) = 10.0 + 0.015*raw + 0.000002*(raw^2)
        import math
        a, b, c = 0.000002, 0.015, 10.0 - pressure_kpa
        discriminant = b**2 - 4*a*c
        if discriminant >= 0:
            r = (-b + math.sqrt(discriminant)) / (2*a)
            self._map_raw = max(0, min(4095, round(r)))
        else:
            self._map_raw = 0

class MockDevice(BaseDevice):
    def __init__(self):
        self._engine = EngineMock()
        self._connected = False
        self._enabled = True
        self._signals = [
            SignalAnalog(
                signal_id="J1_01",
                name="Engine Speed Feedback",
                direction="input",
                description="12-bit analog tachometer feedback (0-5V = 0-5000 RPM)."
            ),
            SignalPWM(
                signal_id="J1_02",
                name="Throttle Command",
                direction="output",
                description="16-bit PWM output to throttle actuator. J1 pin 02."
            ),
            SignalAnalog(
                signal_id="J1_03",
                name="Coolant Temperature ADC",
                direction="input",
                description="12-bit ADC reading from NTC thermistor. Scaled by LUT channel."
            ),
            SignalAnalog(
                signal_id="J1_04",
                name="MAP Sensor ADC",
                direction="input",
                description="12-bit ADC for MAP sensor. Scaled by Polynomial channel."
            ),
        ]

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def vendor(self) -> str:
        return "SDTB"

    @property
    def model(self) -> str:
        return "Mock-v1"

    @property
    def firmware_version(self) -> str:
        return "1.0.0"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def connect(self, connection_params: dict) -> None:
        logger.info(f"MockDevice connecting with {connection_params}")
        self._connected = True

    def disconnect(self) -> None:
        logger.info("MockDevice disconnected")
        self._connected = False

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    def restart(self) -> None:
        logger.info("MockDevice restarting...")
        self.disconnect()
        # Simulated delay
        time.sleep(0.5)
        self._connected = True
        logger.info("MockDevice restarted")
    
    def get_signal(self, signal_id: str) -> SignalDefinition:
        for s in self._signals:
            if s.signal_id == signal_id:
                return s
        raise ValueError(f"Signal {signal_id} not found in {self.vendor} {self.model}")

    def read_signal(self, signal_id: str) -> Any:
        if not self._connected:
            raise RuntimeError("Device not connected")
        sig = self.get_signal(signal_id)
        logger.info(f"MockDevice reading {signal_id} {sig.value}")
        return sig.value

    def write_signal(self, signal_id: str, value: Any) -> None:
        if not self._connected:
            raise RuntimeError("Device not connected")
        sig = self.get_signal(signal_id)
        sig.value = value
        logger.info(f"MockDevice writing {value} to {signal_id}")

    def update(self) -> None:
        if not self._connected:
            return
        
        # 1. Read commands from system
        self._engine.throttle_pwm = self.get_signal("J1_02").value
        
        # 2. Update engine state
        self._engine.update()
        
        # 3. Push feedback to system
        self.get_signal("J1_01").value = self._engine.engine_speed
        self.get_signal("J1_03").value = self._engine.temperature_raw
        self.get_signal("J1_04").value = self._engine.map_raw
        
        
    def inject_fault(self, signal_id: str, fault_id: str) -> None:
        """Mock implementation of fault injection."""
        logger.info(f"Mock Injecting fault '{fault_id}' on signal '{signal_id}'")
        pass

    def clear_fault(self, signal_id: Optional[str] = None) -> None:
        """Mock implementation of clearing faults."""
        if signal_id:
            logger.info(f"Mock Clearing fault on signal '{signal_id}'")
        else:
            logger.info("Mock Clearing all faults on device")
        pass

    def get_available_faults(self, signal_id: str) -> List[Dict[str, str]]:
        """Returns standard fault types for mock."""
        return [
        ]
    

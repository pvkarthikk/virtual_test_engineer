from core.base_device import BaseDevice, SignalDefinition, SignalAnalog, SignalPWM, SignalSwitch, CANFrame
from typing import List, Any, Dict, Optional
import logging
import random
import time
import struct
import collections

logger = logging.getLogger(__name__)
def generate_mock_value(signal: SignalDefinition):
    val = random.uniform(signal.min, signal.max)
    return round(val / signal.resolution) * signal.resolution


class EngineMock:
    def __init__(self):
        self._ignition_switch = False # 0 - 12V
        self._throttle_pwm = 0 # 0 - 255 PWM
        self._engine_speed = 0 # 0 - 4095 volt
        self._engine_speed_pwm = 0 # 0 - 255 PWM
        self._throttle_percent = 0 # 0 - 100 %
        self._engine_speed_rpm = 0 # 0 - 5000 rpm
        self._idle_rpm = 800
        self._max_rpm = 5000
        
        # New non-linear sensor simulations
        self._temperature_c = 20.0  # Starts at 20C
        self._temperature_raw = 2500
        self._map_raw = 500
        self._last_update = time.time()
        self._eco_mode = False
    
    @property
    def eco_mode(self) -> bool:
        return self._eco_mode

    @eco_mode.setter
    def eco_mode(self, value: bool):
        self._eco_mode = value

    @property
    def ignition_switch(self) -> bool:
        return self._ignition_switch
    
    @ignition_switch.setter
    def ignition_switch(self, value: bool):
        self._ignition_switch = value

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
    def engine_speed_pwm(self) -> int:
        return self._engine_speed_pwm

    @property
    def temperature_raw(self) -> int:
        return self._temperature_raw

    @property
    def map_raw(self) -> int:
        return self._map_raw

    def update(self):
        # Calculate delta time for natural physics simulation
        now = time.time()
        dt = now - self._last_update
        self._last_update = now
        
        # calculate engine rpm based on the throttle percent
        # Eco Mode reduces available power by 20%
        power_multiplier = 0.8 if self._eco_mode else 1.0
        dynamic_range = (self._max_rpm - self._idle_rpm) * power_multiplier
        target_rpm = self._idle_rpm + dynamic_range * (self._throttle_percent / 100.0)
        
        # Add some jitter/noise
        noise = random.uniform(-50, 50)
        self._engine_speed_rpm = target_rpm + noise
        
        # Clamp RPM to physical limits
        self._engine_speed_rpm = max(0, min(self._max_rpm + 500, self._engine_speed_rpm))
        
        # convert engine rpm to 12-bit ADC counts (0-5V range where 4095 = 5000 RPM)
        raw_val = (self._engine_speed_rpm / 5000.0) * 4095.0
        self._engine_speed = max(0, min(4095, round(raw_val)))

        # Convert RPM to 8-bit PWM (0-255)
        self._engine_speed_pwm = round((self._engine_speed_rpm / 5000.0) * 255)
        self._engine_speed_pwm = max(0, min(255, self._engine_speed_pwm))
        
        # ----------------------------------------------------
        # Simulate MAP Sensor (Manifold Absolute Pressure)
        # ----------------------------------------------------
        if not self._ignition_switch:
            self._engine_speed = 0
            self._engine_speed_pwm = 0
            self._engine_speed_rpm = 0
            # Engine off = Atmospheric pressure
            pressure_kpa = 101.3
        else:
            # Engine running: Higher throttle = less vacuum, Higher RPM = more vacuum
            pressure_kpa = 30.0 + (self._throttle_percent * 0.7) - ((self._engine_speed_rpm - 800) * 0.005)
            # Add slight pressure fluctuations
            pressure_kpa += random.uniform(-1.0, 1.0)
            
        pressure_kpa = max(10.0, min(105.0, pressure_kpa))
        
        # Real-world 1-bar GM MAP Sensor is linear: P(kPa) = 10.0 + 0.023199 * raw
        # Inverse mapping to get 12-bit ADC raw value (0-4095)
        raw_val = (pressure_kpa - 10.0) / 0.023199
        self._map_raw = max(0, min(4095, round(raw_val)))
        # ----------------------------------------------------
        # Simulate Coolant Temperature (Warms up as engine runs)
        # ----------------------------------------------------
        # Calculate an RPM-based load factor (0.0 at idle, 1.0 at max RPM)
        load_factor = max(0.0, (self._engine_speed_rpm - self._idle_rpm) / (self._max_rpm - self._idle_rpm))
        
        # Dynamic heating rate: ~0.5 C/sec at idle, scaling up to ~3.0 C/sec at redline
        heating_rate = (0.5 + (2.5 * load_factor)) * random.uniform(1.9, 2.1)
        
        if self._engine_speed_rpm > 400: # Engine is running
            # Heating: Targets 90.0 C
            if self._temperature_c < 90.0:
                self._temperature_c += heating_rate * dt
        else:
            # Cooling: Engine is off, drops toward ambient 20.0 C
            if self._temperature_c > 20.0:
                cooling_rate = 0.3 * random.uniform(1.9, 2.1)
                self._temperature_c -= cooling_rate * dt

        # Add slight thermal noise so it visibly updates in the UI
        temp_with_noise = self._temperature_c + random.uniform(-0.1, 0.1)

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



class MockDevice(BaseDevice):
    def __init__(self):
        self._engine = None
        self._connected = False
        self._enabled = True
        self._can_buffer = collections.deque(maxlen=100)
        self._obd_counter = 0
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
            SignalSwitch(
                signal_id="J1_05",
                name="Eco Mode Switch",
                direction="output",
                description="Binary switch to toggle Engine Eco Mode (1=On, 0=Off)."
            ),
            SignalPWM(
                signal_id="J1_06",
                name="Engine Speed Feedback 2",
                direction="input",
                description="8-bit PWM feedback from engine speed sensor. J1 pin 06."
            ),
            SignalSwitch(
                signal_id="J1_07",
                name="Ignition Switch",
                direction="output",
                description="Binary switch to toggle Engine Ignition (1=On, 0=Off). J1 pin 07."
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
        self._engine = EngineMock()

    def disconnect(self) -> None:
        logger.info("MockDevice disconnected")
        self._connected = False
        self._engine = None

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    def get_can_interfaces(self) -> List[str]:
        return ["can0"]

    def pop_can_frames(self) -> List[CANFrame]:
        # Atomic swap to prevent race conditions with the background update thread
        temp = self._can_buffer
        self._can_buffer = collections.deque(maxlen=100) 
        return list(temp)

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
        self._engine.eco_mode = bool(self.get_signal("J1_05").value)
        self._engine.ignition_switch = bool(self.get_signal("J1_07").value)
        
        # 2. Update engine state
        self._engine.update()
        
        # 3. Push feedback to system
        self.get_signal("J1_01").value = self._engine.engine_speed
        self.get_signal("J1_03").value = self._engine.temperature_raw
        self.get_signal("J1_04").value = self._engine.map_raw
        self.get_signal("J1_06").value = self._engine.engine_speed_pwm
        
        # 4. Generate CAN frames (Simulated background traffic)
        # 0x100: Engine telemetry
        self._can_buffer.append(CANFrame(
            timestamp=time.time(),
            bus="can0",
            arbitration_id=0x100,
            dlc=4,
            data=struct.pack(">HH", int(self._engine._engine_speed_rpm), int(self._engine._temperature_raw))
        ))
        
        # 0x200: Throttle status
        self._can_buffer.append(CANFrame(
            timestamp=time.time(),
            bus="can0",
            arbitration_id=0x200,
            dlc=3,
            data=struct.pack(">HB", int(self._engine.throttle_pwm), 1 if self._engine.eco_mode else 0)
        ))
        
        # 0x7DF: Periodic OBD-II request (Every ~10 updates)
        self._obd_counter += 1
        if self._obd_counter >= 10:
            self._obd_counter = 0
            self._can_buffer.append(CANFrame(
                timestamp=time.time(),
                bus="can0",
                arbitration_id=0x7DF,
                dlc=8,
                data=bytes([0x02, 0x01, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]) # Get Coolant Temp
            ))

        # 5. J1939 Traffic (29-bit Extended IDs)
        # EEC1 (Electronic Engine Controller 1): PGN 61444 (0xF004)
        # Priority 3, Source Address 0x00
        # ID = (3 << 26) | (0xF004 << 8) | 0x00 = 0x0CF00400
        # Speed is 2 bytes, 0.125 RPM/bit. Max 8031 RPM (64255)
        engine_speed_j1939 = min(64255, int(self._engine._engine_speed_rpm * 8))
        self._can_buffer.append(CANFrame(
            timestamp=time.time(),
            bus="can0",
            arbitration_id=0x0CF00400,
            dlc=8,
            data=struct.pack("<HHBBBB", 0xFFFF, engine_speed_j1939, 0xFF, 0xFF, 0xFF, 0xFF),
            is_extended=True
        ))

        # ET1 (Engine Temperature 1): PGN 65262 (0xFEEE)
        # Priority 6, Source Address 0x00
        # ID = (6 << 26) | (0xFEEE << 8) | 0x00 = 0x18FEEE00
        # Temp is 1 byte, -40 offset. Range -40 to 210. 
        # Map 0-4095 raw to 0-250 J1939 range
        temp_j1939 = min(250, int(self._engine._temperature_raw / 16))
        self._can_buffer.append(CANFrame(
            timestamp=time.time(),
            bus="can0",
            arbitration_id=0x18FEEE00,
            dlc=8,
            data=struct.pack("<BBBBBBBB", temp_j1939, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
            is_extended=True
        ))

        # TSC1 (Torque/Speed Control 1): PGN 0 (0x0000) - PDU1 format
        # Priority 3, SA 0x03, Destination 0x00
        # ID = (3 << 26) | (0x00 << 8) | 0x03 = 0x0C000003
        self._can_buffer.append(CANFrame(
            timestamp=time.time(),
            bus="can0",
            arbitration_id=0x0C000003,
            dlc=8,
            data=struct.pack("<BBBBBBBB", 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
            is_extended=True
        ))
        
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
    

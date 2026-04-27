import logging
from typing import List, Any, Dict
from core.base_device import BaseDevice, SignalDefinition
from devices.sim_r4_driver import ArduinoR4Controller

logger = logging.getLogger(__name__)

class ArduinoR4SimDevice(BaseDevice):
    def __init__(self):
        self._controller: ArduinoR4Controller = None
        self._connected = False
        self._enabled = True
        self._signals: List[SignalDefinition] = []
        self._signal_map: Dict[str, SignalDefinition] = {}
        self._connection_params: dict = {}
        self._create_signals()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def vendor(self) -> str:
        return "Arduino"

    @property
    def model(self) -> str:
        return "Custom R4 Firmware"

    @property
    def firmware_version(self) -> str:
        return "2.1 (LBP)"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def _create_signals(self):
        self._signals = [
            # Generic Outputs (Mapped to Simulator Controls)
            SignalDefinition("DO1", "Digital Output 1", "digital", "output", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "Simulator: Ignition Switch"),
            SignalDefinition("AO1", "Analog Output 1", "analog", "output", 1.0, "V", 0.0, 0.0, 4095.0, 0.0, "Simulator: Engine RPM (DAC)"),
            SignalDefinition("AO2", "Analog Output 2", "analog", "output", 1.0, "%", 0.0, 0.0, 4095.0, 0.0, "Simulator: Pedal Position (PWM)"),
            SignalDefinition("AO3", "Analog Output 3", "analog", "output", 1.0, "%", 0.0, 0.0, 4095.0, 0.0, "Simulator: Battery Voltage (PWM)"),
            SignalDefinition("AO4", "Analog Output 4", "analog", "output", 1.0, "%", 0.0, 0.0, 4095.0, 0.0, "Simulator: Oil Pressure (PWM)"),
            
            # Generic Inputs (Mapped to Simulator Monitoring)
            SignalDefinition("IN1", "Input 1", "digital", "input", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "Simulator: Check Engine Light"),
            SignalDefinition("IN2", "Input 2", "pwm", "input", 1.0, "%", 0.0, 0.0, 20000.0, 0.0, "Simulator: Throttle Position")
        ]
        self._signal_map = {s.signal_id: s for s in self._signals}

    def connect(self, connection_params: dict) -> None:
        self._connection_params = connection_params
        port = connection_params.get("port", "COM3")
        baud = connection_params.get("baud", 115200)
        try:
            self._controller = ArduinoR4Controller(port=port, baudrate=baud)
            if self._controller.ser:
                self._connected = True
                logger.info(f"Custom Arduino Firmware connected on {port}")
            else:
                self._connected = False
                raise RuntimeError(f"Failed to open serial port {port}")
        except Exception as e:
            self._connected = False
            logger.error(f"Connection error: {e}")
            raise

    def disconnect(self) -> None:
        if self._controller:
            self._controller.close()
        self._connected = False
        logger.info("Custom Arduino Firmware disconnected")

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    def restart(self) -> None:
        logger.info(f"Restarting device {self.model}...")
        self.disconnect()
        import time
        time.sleep(1) # Grace period
        if self._connection_params:
            self.connect(self._connection_params)
        else:
            logger.warn("Cannot restart: No connection parameters stored")

    def read_signal(self, signal_id: str) -> Any:
        if signal_id not in self._signal_map:
            raise ValueError(f"Signal {signal_id} not found")
        return self._signal_map[signal_id].value

    def write_signal(self, signal_id: str, value: Any) -> None:
        if not self._connected:
            raise RuntimeError("Device not connected")
        
        if signal_id not in self._signal_map:
            raise ValueError(f"Signal {signal_id} not found")

        sig = self._signal_map[signal_id]
        self.validate_signal_value(sig, value)
        logger.info(f"Writing {signal_id} = {value}")
        
        # In a generic driver, the signal_id (DO1, AO1, etc.) is the command key
        if signal_id.startswith("DO"):
            self._controller.set_digital_out(signal_id, bool(value))
        elif signal_id.startswith("AO"):
            self._controller.set_analog_out(signal_id, int(value))
        
        sig.value = value

    def update(self) -> None:
        if not self._connected or not self._controller:
            return

        # Fetch latest data from background thread (list of values)
        data_list = self._controller.get_latest_data()
        
        # Map indexed data to generic input signals
        # sim.ino sends: [VAL1 (CEL), VAL2 (THROTTLE)]
        if len(data_list) >= 2:
            if "IN1" in self._signal_map:
                self._signal_map["IN1"].value = float(data_list[0])
            if "IN2" in self._signal_map:
                self._signal_map["IN2"].value = float(data_list[1])

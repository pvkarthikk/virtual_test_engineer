import logging
from typing import List, Any, Dict
from core.base_device import BaseDevice, SignalDefinition
from devices.arduino_custom_firmware_driver import ArduinoR4Controller

logger = logging.getLogger(__name__)

class ArduinoCustomFirmwareDevice(BaseDevice):
    def __init__(self):
        self._controller: ArduinoR4Controller = None
        self._connected = False
        self._enabled = True
        self._signals: List[SignalDefinition] = []
        self._signal_map: Dict[str, SignalDefinition] = {}
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
            # Outputs
            SignalDefinition("DO1", "Digital Out 1", "digital", "output", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "D2 Output"),
            SignalDefinition("DO2", "Digital Out 2", "digital", "output", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "D12 Output"),
            SignalDefinition("DO3", "Digital Out 3", "digital", "output", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "D13 Output"),
            SignalDefinition("AO1", "Analog Out 1 (DAC)", "analog", "output", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "A0 True DAC"),
            SignalDefinition("AO2", "Analog Out 2", "analog", "output", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "D3 PWM-Analog"),
            SignalDefinition("AO3", "Analog Out 3", "analog", "output", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "D6 PWM-Analog"),
            SignalDefinition("AO4", "Analog Out 4", "analog", "output", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "D9 PWM-Analog"),
            SignalDefinition("PWMO", "PWM Output", "pwm", "output", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "D10 PWM Output"),
            
            # Inputs
            SignalDefinition("DI1", "Digital In 1", "digital", "input", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "D7 Input"),
            SignalDefinition("DI2", "Digital In 2", "digital", "input", 1.0, "bool", 0.0, 0.0, 1.0, 0.0, "D11 Input"),
            SignalDefinition("AI1", "Analog In 1", "analog", "input", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "A1 Input"),
            SignalDefinition("AI2", "Analog In 2", "analog", "input", 1.0, "raw", 0.0, 0.0, 4095.0, 0.0, "A2 Input"),
            SignalDefinition("PWM_IN", "PWM Input", "pwm", "input", 1.0, "us", 0.0, 0.0, 20000.0, 0.0, "D8 Pulse Width")
        ]
        self._signal_map = {s.signal_id: s for s in self._signals}

    def connect(self, connection_params: dict) -> None:
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
        logger.info(f"Writing {signal_id} = {value}")
        if signal_id.startswith("DO"):
            idx = int(signal_id[2:])
            self._controller.set_digital_out(idx, bool(value))
        elif signal_id.startswith("AO"):
            idx = int(signal_id[2:])
            self._controller.set_analog_out(idx, int(value))
        elif signal_id == "PWMO":
            self._controller.set_analog_out(5, int(value))
        
        sig.value = value

    def update(self) -> None:
        if not self._connected or not self._controller:
            return

        # Fetch latest data from background thread
        data = self._controller.get_inputs()
        
        for key, val in data.items():
            if key in self._signal_map:
                self._signal_map[key].value = float(val)

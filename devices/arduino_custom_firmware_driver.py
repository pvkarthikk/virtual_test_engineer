import serial
import time
import threading

class ArduinoR4Controller:
    def __init__(self, port, baudrate=115200, timeout=1):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to Arduino on {port}")
        except Exception as e:
            print(f"Error connecting to serial port: {e}")
            self.ser = None

        self.latest_data = {
            "DI1": 0, "DI2": 0, 
            "AI1": 0, "AI2": 0, 
            "PWM_IN": 0
        }
        self.running = True
        
        # Start background thread to listen for data
        if self.ser:
            self.listener_thread = threading.Thread(target=self._listen, daemon=True)
            self.listener_thread.start()

    def _listen(self):
        """Internal method to continuously parse data from Arduino."""
        while self.running:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line.startswith("DATA:"):
                        # Split string: DATA:di1,di2,ai1,ai2,pwmPulse
                        raw_values = line.replace("DATA:", "").split(',')
                        if len(raw_values) == 5:
                            self.latest_data["DI1"] = int(raw_values[0])
                            self.latest_data["DI2"] = int(raw_values[1])
                            self.latest_data["AI1"] = int(raw_values[2])
                            self.latest_data["AI2"] = int(raw_values[3])
                            self.latest_data["PWM_IN"] = int(raw_values[4])
                except Exception as e:
                    pass # Ignore partial/corrupt frames

    def _send_command(self, cmd, val):
        """Sends command in format CMD:VAL\n"""
        if self.ser:
            # Ensure 12-bit range for analog/pwm (0-4095)
            if "AO" in cmd or "PWM" in cmd:
                val = max(0, min(4095, int(val)))
            
            message = f"{cmd}:{val}\n"
            self.ser.write(message.encode('utf-8'))
            print(f"Sent command: {message}")

    # --- CONTROL METHODS ---
    def set_digital_out(self, index, state):
        """Set D2 (index 1) or D12 (index 2) to True/False"""
        cmd = f"DO{index}"
        self._send_command(cmd, 1 if state else 0)

    def set_analog_out(self, index, value):
        """Set Analog Outs (1-4) or PWM Out (index 5) 0-4095"""
        if index == 5:
            self._send_command("PWMO", value)
        else:
            self._send_command(f"AO{index}", value)

    def get_inputs(self):
        """Returns the latest readings from the board"""
        return self.latest_data

    def close(self):
        self.running = False
        if self.ser:
            self.ser.close()

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Update 'COM3' or '/dev/ttyACM0' to match your board's port
    board = ArduinoR4Controller(port='COM3') 

    try:
        print("Testing Digital Output 1 (D2)...")
        board.set_digital_out(3, True)
        time.sleep(1)
        
        print("Testing Analog Output 1 (A0 DAC) at 50%...")
        board.set_analog_out(1, 2048) # 12-bit mid-point
        
        while True:
            data = board.get_inputs()
            print(f"\rInputs -> AI1: {data['AI1']} | PWM_IN: {data['PWM_IN']}us | DI1: {data['DI1']}", end="")
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        board.close()
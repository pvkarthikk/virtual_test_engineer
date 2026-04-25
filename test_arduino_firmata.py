import sys
import os
import time
import logging

# Add source directory to path if needed
# source_path = os.path.dirname(os.path.abspath(__file__))
# if source_path not in sys.path:
#     sys.path.append(source_path)

from devices.device_arduino_firmata import ArduinoFirmataDevice

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(name)s: %(message)s')

def run_arduino_test():
    """
    Tests the Arduino Firmata device directly by blinking D13 and reading A0.
    """
    print("=== Direct Arduino Firmata Device Test script ===")
    
    # 1. Instantiate the device directly
    device = ArduinoFirmataDevice()
    
    # Define connection parameters (Update 'port' if needed)
    connection_params = {
        "port": "COM3",
        "baud": 57600,
        "arduino_wait": 2
    }
    
    try:
        # 2. Connect
        print(f"\n[1/4] Connecting to Arduino on {connection_params['port']}...")
        device.connect(connection_params)
        
        if not device.is_connected:
            print("FAILED: Device could not connect.")
            return
            
        print(f"SUCCESS: Connected. Firmware: {device.firmware_version}")
        
        # 3. Test Digital Write (Blink LED on D13)
        print("\n[2/4] Testing Digital Write: Blinking Onboard LED (D13)...")
        for i in range(1, 4):
            print(f"  Cycle {i}: LED ON")
            device.write_signal("D13", 1)
            time.sleep(0.5)
            print(f"  Cycle {i}: LED OFF")
            device.write_signal("D13", 0)
            time.sleep(0.5)
            
        print("SUCCESS: Digital write test complete.")
        
        # # 4. Test Analog Read (A0)
        # print("\n[3/4] Testing Analog Read: Reading A0...")
        # for i in range(15):
        #     # We must call update() manually to fetch latest values from hardware
        #     device.update()
        #     val = device.read_signal("A0")
        #     print(f"  Read {i+1}: A0 = {val:.2f}V")
        #     wait_for_user = input()
        #     time.sleep(0.5)
        
        # 5. Test Blink D13 and Analog Read (A0)
        print("\n[4/4] Testing Digital Write D13 and Analog Read: A0...")
        d13_val = 0
        for i in range(15):
            # We must call update() manually to fetch latest values from hardware
            device.update()
            device.write_signal("D13", d13_val)
            d13_val = not d13_val
            val = device.read_signal("A0")
            print(f"  Read {i+1}: A0 = {val:.2f}V")
            wait_for_user = input()
            time.sleep(0.5)
            
        print("SUCCESS: Analog read test complete.")
        
        # 5. Shutdown
        print("\n[4/4] Disconnecting from Arduino...")
        device.disconnect()
        print("SUCCESS: Test Sequence Finished Successfully.")

    except Exception as e:
        print(f"\nFATAL ERROR during test: {e}")
        if device.is_connected:
            device.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    run_arduino_test()

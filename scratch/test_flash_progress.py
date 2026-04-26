import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_flash_progress():
    # 1. Connect to flash target
    print("Connecting to flash target...")
    resp = requests.post(f"{BASE_URL}/flash/connect?flash_id=mock_target")
    print(resp.json())

    # 2. Start flashing
    print("Starting flash...")
    files = {'file': ('test.bin', b'\x00' * 1024)}
    data = {'flash_id': 'mock_target', 'params': '{}'}
    resp = requests.post(f"{BASE_URL}/flash", data=data, files=files)
    flash_data = resp.json()
    print(f"Flash initiated: {flash_data}")
    exec_id = flash_data['execution_id']

    # 3. Poll status
    print("Polling status...")
    for _ in range(20):
        resp = requests.get(f"{BASE_URL}/flash/status?flash_id=mock_target&execution_id={exec_id}")
        status = resp.json()
        print(f"Status: {status}")
        if status['status'] in ["Success", "Failed", "Aborted", "Error"]:
            break
        time.sleep(1)

if __name__ == "__main__":
    # Ensure server is running or start it
    test_flash_progress()

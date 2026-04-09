#!/usr/bin/env python3
"""
Test script for flashing endpoints
"""

import asyncio
import requests
import time
import os

# Test the flashing API endpoints
BASE_URL = "http://localhost:8080"

def test_flash_endpoints():
    """Test flashing endpoints"""

    print("Testing flashing endpoints...")

    # Test 1: Check if flashing is available
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test 2: List firmware files
    try:
        response = requests.get(f"{BASE_URL}/flash/files")
        print(f"List firmware files: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Firmware files: {len(data['files'])}")
    except Exception as e:
        print(f"List firmware files failed: {e}")

    # Test 3: Upload a test firmware file
    try:
        # Create a dummy firmware file
        test_firmware = b"dummy firmware content for testing"
        files = {'file': ('test_firmware.hex', test_firmware)}
        data = {'description': 'Test firmware file'}

        response = requests.post(f"{BASE_URL}/flash/upload", files=files, data=data)
        print(f"Upload firmware: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Uploaded file: {data['filename']}")
            firmware_file = data['filename']
        else:
            print(f"Upload failed: {response.text}")
            return
    except Exception as e:
        print(f"Upload firmware failed: {e}")
        return

    # Test 4: Start flash operation
    try:
        flash_request = {
            "target_device": "arduino_ecu",
            "firmware_file": firmware_file,
            "protocol": "avrdude",
            "parameters": {
                "programmer": "arduino",
                "port": "/dev/ttyACM0"
            }
        }

        response = requests.post(f"{BASE_URL}/flash", json=flash_request)
        print(f"Start flash: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Flash started: {data['flash_id']}")
            flash_id = data['flash_id']
        else:
            print(f"Start flash failed: {response.text}")
            return
    except Exception as e:
        print(f"Start flash failed: {e}")
        return

    # Test 5: Monitor flash progress
    try:
        for i in range(10):
            response = requests.get(f"{BASE_URL}/flash/status/{flash_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"Flash status: {data['status']} - {data['progress']['percentage']}%")
                if data['status'] in ['completed', 'failed']:
                    print(f"Flash finished: {data['status']}")
                    break
            else:
                print(f"Status check failed: {response.text}")
            time.sleep(1)
    except Exception as e:
        print(f"Monitor flash failed: {e}")

    # Test 6: List firmware files again
    try:
        response = requests.get(f"{BASE_URL}/flash/files")
        if response.status_code == 200:
            data = response.json()
            print(f"Final firmware files: {len(data['files'])}")
    except Exception as e:
        print(f"Final list failed: {e}")

    print("Flashing endpoint tests completed!")

if __name__ == "__main__":
    test_flash_endpoints()
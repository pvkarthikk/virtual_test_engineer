import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from main import app

@pytest.fixture
def client():
    """Provides a TestClient with lifespan support to ensure startup/shutdown logic runs."""
    with TestClient(app) as c:
        yield c

def test_system_status(client):
    response = client.get("/system")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "devices_discovered" in data

def test_system_config(client):
    response = client.get("/system/config")
    assert response.status_code == 200
    data = response.json()
    assert "device_directory" in data

def test_list_devices(client):
    response = client.get("/device")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_channels(client):
    response = client.get("/channel")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_flash_protocols(client):
    response = client.get("/flash/protocols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_device_toggle_contract(client):
    # This test verifies the contract (JSON body)
    # We use a mock-like approach or just check the 404/422 behavior
    response = client.post("/device/non_existent/toggle", json={"enabled": True})
    # Should be 404 if not found, NOT 422 (validation error) or 500 (undefined var)
    assert response.status_code == 404
    assert response.json()["detail"] == "Device non_existent not found"

def test_fault_clear_contract(client):
    response = client.post("/system/fault/clear")
    # Should return 200 if asyncio is correctly imported and to_thread works
    assert response.status_code == 200
    assert "message" in response.json()

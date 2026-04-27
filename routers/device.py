from fastapi import APIRouter, HTTPException, Body
import asyncio
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from core.system import SDTBSystem

router = APIRouter(prefix="/device", tags=["Device Management"])

# Access the singleton system instance
system = SDTBSystem()

class WriteValue(BaseModel):
    value: float

@router.get("")
async def list_devices():
    """
    Lists all available devices across all configured instruments.
    """
    devices = system.device_manager.get_all_devices()
    result = []
    for dev_id, dev in devices.items():
        try:
            result.append({
                "id": dev_id,
                "vendor": dev.vendor,
                "model": dev.model,
                "firmware_version": dev.firmware_version,
                "status": "connected" if dev.is_connected else "offline",
                "enabled": dev.enabled,
                "plugin": dev.__class__.__module__
            })
        except Exception as e:
            result.append({
                "id": dev_id,
                "error": str(e)
            })
    return result

@router.get("/{device_id}")
async def get_device_details(device_id: str):
    """
    Retrieves detailed information about a specific device.
    """
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
        
    return {
        "id": device_id,
        "vendor": device.vendor,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "status": "online" if device.is_connected else "offline",
        "enabled": device.enabled
    }

@router.get("/{device_id}/signal")
async def list_device_signals(device_id: str):
    """
    Lists all raw signals exposed by a specific hardware device.
    """
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
        
    try:
        return device.get_signals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving signals: {e}")

@router.post("/{device_id}/toggle")
async def toggle_device(device_id: str, enabled: bool):
    try:
        await system.device_manager.toggle_device(device_id, enabled)
        return {"message": f"Device {device_id} is now {'enabled' if enabled else 'disabled'}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}/signal/{signal_id}")
async def read_device_signal(device_id: str, signal_id: str):
    """
    Reads a single signal value from hardware.
    """
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    try:
        val = await asyncio.to_thread(device.read_signal, signal_id)
        return {"device_id": device_id, "signal_id": signal_id, "value": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{device_id}/signal/{signal_id}")
async def write_device_signal(device_id: str, signal_id: str, data: WriteValue = Body(...)):
    """
    Writes a value to a single hardware signal.
    """
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    try:
        await asyncio.to_thread(device.write_signal, signal_id, data.value)
        return {"message": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}/signal/{signal_id}/stream")
async def stream_device_signal(device_id: str, signal_id: str):
    """
    Server-Sent Events (SSE) stream for a raw hardware signal.
    """
    return EventSourceResponse(system.stream_manager.subscribe_device_signal(device_id, signal_id))

@router.post("/{device_id}/restart")
async def restart_device(device_id: str):
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    try:
        await asyncio.to_thread(device.restart)
        return {"message": f"Device {device_id} restart initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
from core.system import SDTBSystem

router = APIRouter(prefix="/device", tags=["Device Management"])

# Access the singleton system instance
system = SDTBSystem()

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
                "status": "connected" if dev.is_connected else "offline"
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
        "firmware_version": device.firmware_version
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

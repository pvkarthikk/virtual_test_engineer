from fastapi import APIRouter, HTTPException
import asyncio
from typing import List
import os
from core.system import SDTBSystem
from models.config import SystemConfig, ChannelConfig
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/system", tags=["System Management"])

# Access the singleton system instance via call to ensure we always have the current instance
def get_system():
    return SDTBSystem()

@router.get("")
async def get_system_status():
    """
    Returns overall system health, status, and version information.
    """
    system = get_system()
    devices = system.device_manager.get_all_devices()
    is_connected = any(dev.is_connected for dev in devices.values()) if devices else False
    
    return {
        "name": "SDTB Server",
        "version": "0.1.0",
        "status": "online" if is_connected else "offline",
        "is_connected": is_connected,
        "devices_discovered": len(devices),
        "channels_configured": len(system.channel_manager.get_all_channels())
    }

@router.post("/connect")
async def connect_system():
    """
    Connects all configured hardware devices.
    Returns a summary of connection results.
    """
    try:
        system = get_system()
        results = await system.device_manager.connect_all()
        # Check if any device failed
        has_errors = any(r["status"] == "error" for r in results.values())
        
        return {
            "message": "Hardware connection sequence completed",
            "has_errors": has_errors,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect")
async def disconnect_system():
    """
    Gracefully disconnects all hardware devices.
    """
    try:
        await get_system().device_manager.disconnect_all()
        return {"message": "Hardware disconnection sequence completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart")
async def restart_system():
    """
    Restarts the system: auto-disconnect, re-initialize, and re-discover.
    """
    try:
        await get_system().restart()
        return {"message": "System restart completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_system_config():
    """
    Retrieves current system configuration (system.json).
    """
    return get_system().system_config

@router.put("/config")
async def update_system_config(config: SystemConfig):
    """
    Updates the system configuration file.
    """
    try:
        system = get_system()
        system.config_manager.save_config("system", config)
        system.system_config = config
        return {"message": "System configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config/channels")
async def get_channel_configs():
    """
    Retrieves channel-to-signal mapping configuration.
    """
    return get_system().channel_manager.get_all_channels()

@router.put("/config/channels")
async def update_channel_configs(channels: List[ChannelConfig]):
    """
    Configures channel-to-device-signal mappings.
    """
    try:
        system = get_system()
        # Save to file
        # We need a way to save a list in ConfigManager or handle it here
        # For now, let's assume we can save it as 'channels'
        # Since ConfigManager.save_config expects a BaseModel, 
        # we might need a wrapper or handle it directly
        import json
        file_path = system.config_manager.get_file_path("channels")
        
        # Create backup
        import shutil
        if os.path.exists(file_path):
            shutil.copy2(file_path, file_path + ".bak")
            
        with open(file_path, "w") as f:
            # Pydantic v2 dump
            json.dump([c.model_dump() for c in channels], f, indent=2)
            
        system.channel_manager.initialize_channels(channels)
        return {"message": "Channel configurations updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/logs/stream")
async def stream_logs():
    """
    Server-Sent Events (SSE) stream for real-time system logs and test progress.
    """
    return EventSourceResponse(get_system().stream_manager.subscribe_logs())

@router.get("/stream")
async def stream_all():
    """
    Unified Server-Sent Events (SSE) stream multiplexing logs, channels, and device signals.
    """
    return EventSourceResponse(get_system().stream_manager.subscribe_all())

@router.post("/fault/clear")
async def clear_all_faults():
    """
    Global safety mechanism to clear all faults across all devices.
    """
    try:
        system = get_system()
        devices = system.device_manager.get_all_devices()
        for device_id, device in devices.items():
            # BaseDevice now has clear_all_faults or we loop signals
            await asyncio.to_thread(device.clear_fault, None) # None means all
        return {"message": "Global fault clear sequence completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

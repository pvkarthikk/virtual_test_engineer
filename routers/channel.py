from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from core.system import SDTBSystem
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/channel", tags=["Channel Management"])

# Access the singleton system instance via call to ensure we always have the current instance
def get_system():
    return SDTBSystem()

class WriteValue(BaseModel):
    value: float

@router.get("")
async def list_channels():
    """
    Lists all available channels across all devices.
    """
    return get_system().channel_manager.get_all_channels()

@router.get("/{channel_id}")
async def read_channel(channel_id: str):
    """
    Reads a scaled signal value from a logical channel.
    """
    try:
        value = await get_system().channel_manager.read_channel(channel_id)
        return {"channel_id": channel_id, "value": value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{channel_id}")
async def write_channel(channel_id: str, data: WriteValue = Body(...)):
    """
    Writes a scaled signal value to a logical channel.
    Blocks if a test sequence is currently running.
    """
    system = get_system()
    if system.test_engine.is_test_running:
        raise HTTPException(
            status_code=409, 
            detail="Cannot perform manual write: A test sequence is currently running."
        )
        
    try:
        await system.channel_manager.write_channel(channel_id, data.value)
        return {"message": f"Successfully wrote {data.value} to {channel_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{channel_id}/info")
async def get_channel_info(channel_id: str):
    """
    Retrieves detailed meta information about a specific channel.
    """
    info = get_system().channel_manager.get_channel_info(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    return info

@router.get("/{channel_id}/stream")
async def stream_channel(channel_id: str):
    """
    Server-Sent Events (SSE) stream for real-time updates of a specific channel's value.
    """
    system = get_system()
    if not system.channel_manager.get_channel_info(channel_id):
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    return EventSourceResponse(system.stream_manager.subscribe_channel(channel_id))

@router.get("/{channel_id}/status")
async def get_channel_status(channel_id: str):
    """
    Retrieves current status of a channel.
    """
    system = get_system()
    info = system.channel_manager.get_channel_info(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    device = system.device_manager.get_device(info.device_id)
    is_operational = device.is_connected if device else False
    return {"status": "operational" if is_operational else "offline"}

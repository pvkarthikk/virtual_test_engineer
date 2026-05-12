from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional
from core.system import SDTBSystem
from models.config import CANFrameResponse, CANInterfaceInfo

router = APIRouter(prefix="/can", tags=["CAN"])

def get_system():
    return SDTBSystem()

@router.get("/interfaces", response_model=List[CANInterfaceInfo])
async def list_interfaces(system: SDTBSystem = Depends(get_system)):
    """
    Returns a list of all available CAN interfaces and their current buffer status.
    """
    return system.can_manager.get_interfaces()

@router.get("/log/{device_id}/{bus}", response_model=List[CANFrameResponse])
async def get_can_log(
    device_id: str, 
    bus: str, 
    count: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    arb_id: Optional[str] = None,
    system: SDTBSystem = Depends(get_system)
):
    """
    Retrieves recent CAN frames from a specific interface.
    Optional 'arb_id' filter accepts hex strings like '0x100'.
    """
    # Validation (Point 2)
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    
    if bus not in device.get_can_interfaces():
        raise HTTPException(status_code=404, detail=f"CAN bus '{bus}' not found on device '{device_id}'")

    arb_id_filter = None
    if arb_id:
        try:
            arb_id_filter = int(arb_id, 16)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid arbitration ID format. Use hex (e.g., 0x100)")

    frames = system.can_manager.get_frames(device_id, bus, count, offset, arb_id_filter)
    
    # Map to response model (hex encode ID and data)
    return [
        CANFrameResponse(
            timestamp=f.timestamp,
            bus=f.bus,
            arbitration_id=f"0x{f.arbitration_id:X}",
            dlc=f.dlc,
            data=f.data.hex(),
            is_extended=f.is_extended,
            is_error=f.is_error,
            is_remote=f.is_remote
        ) for f in frames
    ]

@router.get("/log/{device_id}/{bus}/stream")
async def stream_can_log(device_id: str, bus: str, system: SDTBSystem = Depends(get_system)):
    """
    SSE endpoint for real-time CAN frame monitoring.
    """
    # Validation (Point 2)
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    
    if bus not in device.get_can_interfaces():
        raise HTTPException(status_code=404, detail=f"CAN bus '{bus}' not found on device '{device_id}'")

    return EventSourceResponse(system.stream_manager.subscribe_can(device_id, bus))

@router.delete("/log/{device_id}/{bus}")
async def clear_can_log(device_id: str, bus: str, system: SDTBSystem = Depends(get_system)):
    """
    Clears the in-memory ring buffer for a specific CAN interface.
    """
    # Validation (Point 2)
    device = system.device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    
    if bus not in device.get_can_interfaces():
        raise HTTPException(status_code=404, detail=f"CAN bus '{bus}' not found on device '{device_id}'")

    system.can_manager.clear(device_id, bus)
    return {"status": "cleared"}

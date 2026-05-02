import logging
import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from sse_starlette.sse import EventSourceResponse
from core.system import SDTBSystem
from core.base_flash import BaseFlashException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flash", tags=["Flash"])

# Access the singleton system instance via call to ensure we always have the current instance
def get_system():
    return SDTBSystem()

@router.get("/protocols")
async def get_flash_protocols():
    """List all discovered flash protocols and their configurations."""
    try:
        configs = get_system().flash_manager.get_all_configs()
        return [cfg.model_dump() for cfg in configs.values()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_flash(flash_id: str):
    """Connect to a specific flash target."""
    try:
        await get_system().flash_manager.connect_target(flash_id)
        return {"message": f"Successfully connected to flash target: {flash_id}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BaseFlashException as e:
        raise HTTPException(status_code=503, detail=f"Flash target error: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/disconnect")
async def disconnect_flash(flash_id: str):
    """Disconnect from a specific flash target."""
    try:
        await get_system().flash_manager.disconnect_target(flash_id)
        return {"message": f"Successfully disconnected from flash target: {flash_id}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def start_flash(
    flash_id: str = Form(...),
    file: UploadFile = File(...),
    params: str = Form("{}")
):
    """
    Initiate a flashing process.
    Supports multipart/form-data for large binary files.
    """
    try:
        # Check file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Firmware binary too large (max 10MB)")

        # Read the binary data
        data = await file.read()
        
        # Double check size
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Firmware binary too large (max 10MB)")
        
        # Parse params JSON
        try:
            param_dict = json.loads(params)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in 'params' field")

        execution_id = await get_system().flash_manager.start_flash(flash_id, data, param_dict)
        return {
            "execution_id": execution_id,
            "status": "initiated",
            "flash_id": flash_id,
            "file_name": file.filename,
            "file_size": len(data)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_flash_status(flash_id: str, execution_id: str):
    """Retrieve current flashing operation status."""
    try:
        status = get_system().flash_manager.get_flash_status(flash_id, execution_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/log")
async def stream_flash_log(flash_id: str, execution_id: str, request: Request):
    """
    Stream live flash operation logs via SSE.
    """
    async def log_generator():
        last_index = 0
        system = get_system()
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
                
            try:
                logs = system.flash_manager.get_flash_log(flash_id, execution_id)
                
                # Only send new logs
                if len(logs) > last_index:
                    for i in range(last_index, len(logs)):
                        yield {"data": logs[i]}
                    last_index = len(logs)
                
                # Check if flashing is finished to stop streaming
                status = system.flash_manager.get_flash_status(flash_id, execution_id)
                current_state = status.get("status", "").lower()
                if current_state in ["success", "failed", "aborted", "error"]:
                    yield {"data": f"FLASH_PROCESS_TERMINATED: {current_state}"}
                    break
                    
            except Exception as e:
                yield {"data": f"Error retrieving logs: {str(e)}"}
                break
                
            await asyncio.sleep(0.5)

    return EventSourceResponse(log_generator())

@router.post("/abort")
async def abort_flash(flash_id: str, execution_id: str):
    """Abort an ongoing flashing operation."""
    try:
        await get_system().flash_manager.abort_flash(flash_id, execution_id)
        return {"message": f"Abort command sent for execution: {execution_id}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/history")
async def get_flash_history():
    """Retrieve flashing operation history (placeholder)."""
    # In a real implementation, this would query a database
    return {"history": []}

#!/usr/bin/env python3
"""
Virtual Test Engineer - REST API
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import asyncio
import uuid

from ..core.test_bench import VirtualTestBench
from ..core.types import TestRunStatus

app = FastAPI(title="Virtual Test Engineer API", version="1.0.0")

# Global test bench instance
test_bench: Optional[VirtualTestBench] = None


async def get_test_bench() -> VirtualTestBench:
    """Get the global test bench instance"""
    global test_bench
    if test_bench is None:
        test_bench = VirtualTestBench('config/testbench.yaml')
        success = await test_bench.initialize()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to initialize test bench")
    return test_bench


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    global test_bench
    if test_bench:
        await test_bench.shutdown()


# Health and Status Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        tb = await get_test_bench()
        status = tb.get_status()
        return {
            "status": "healthy" if status["state"] != "error" else "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "details": status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }


@app.get("/bench")
async def get_bench_info():
    """Get test bench information"""
    tb = await get_test_bench()
    status = tb.get_status()

    return {
        "id": "virtual_test_bench_001",
        "name": "Virtual Test Engineer",
        "version": "1.0.0",
        "status": status["state"],
        "uptime_seconds": asyncio.get_event_loop().time(),
        "active_dut_profile": None,  # Not implemented yet
        "active_scenario": None,     # Not implemented yet
        "capabilities": tb.get_capabilities()
    }


@app.get("/capabilities")
async def get_capabilities():
    """Get test bench capabilities"""
    tb = await get_test_bench()
    return tb.get_capabilities()


# Channel Endpoints

@app.get("/channels")
async def list_channels():
    """List all available channels"""
    tb = await get_test_bench()
    channels = []

    for channel_id in tb.get_available_channels():
        info = tb.get_channel_info(channel_id)
        if info:
            channels.append({
                "id": channel_id,
                "type": info["type"],
                "status": "active"
            })

    return {"channels": channels}


@app.get("/channels/{channel_id}")
async def read_channel(channel_id: str):
    """Read a channel value"""
    tb = await get_test_bench()

    try:
        value = await tb.read_channel(channel_id)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")

        return {
            "channel_id": channel_id,
            "value": value,
            "timestamp": asyncio.get_event_loop().time(),
            "quality": "good"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading channel: {str(e)}")


@app.put("/channels/{channel_id}")
async def write_channel(channel_id: str, request: Dict[str, Any]):
    """Write a channel value"""
    tb = await get_test_bench()

    if "value" not in request:
        raise HTTPException(status_code=400, detail="Missing 'value' field")

    try:
        success = await tb.write_channel(channel_id, request["value"])
        if not success:
            raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")

        return {
            "channel_id": channel_id,
            "value": request["value"],
            "timestamp": asyncio.get_event_loop().time(),
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing channel: {str(e)}")


@app.get("/channels/{channel_id}/info")
async def get_channel_info(channel_id: str):
    """Get channel information"""
    tb = await get_test_bench()
    info = tb.get_channel_info(channel_id)

    if not info:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")

    return info


# Test Execution Endpoints

@app.post("/runs")
async def start_test_run(request: Dict[str, Any], background_tasks: BackgroundTasks):
    """Start a new test run"""
    tb = await get_test_bench()

    scenario_id = request.get("scenario_id")
    if not scenario_id:
        raise HTTPException(status_code=400, detail="Missing 'scenario_id' field")

    parameters = request.get("parameters", {})
    async_mode = request.get("async", True)

    try:
        run_id = await tb.start_test_scenario(scenario_id, parameters, async_mode)

        if async_mode:
            # Set up completion callback
            def on_complete(test_run):
                print(f"Test run {run_id} completed with status: {test_run.status.value}")

            tb.test_engine.set_run_callback(run_id, on_complete)

        return {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "status": "queued" if async_mode else "running",
            "created_at": asyncio.get_event_loop().time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting test run: {str(e)}")


@app.get("/runs/{run_id}")
async def get_test_run_status(run_id: str):
    """Get test run status"""
    tb = await get_test_bench()
    test_run = tb.get_test_run_status(run_id)

    if not test_run:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")

    return {
        "run_id": test_run.run_id,
        "scenario_id": test_run.scenario_id,
        "status": test_run.status.value,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "progress": {
            "current_step": len(test_run.results) if test_run.results else 0,
            "total_steps": 4,  # Hardcoded for now
            "percentage": (len(test_run.results) / 4 * 100) if test_run.results else 0
        },
        "parameters": test_run.parameters
    }


@app.delete("/runs/{run_id}")
async def abort_test_run(run_id: str):
    """Abort a test run"""
    tb = await get_test_bench()

    success = tb.abort_test_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")

    return {
        "run_id": run_id,
        "status": "aborted",
        "aborted_at": asyncio.get_event_loop().time()
    }


@app.get("/runs/{run_id}/results")
async def get_test_run_results(run_id: str):
    """Get test run results"""
    tb = await get_test_bench()
    test_run = tb.get_test_run_status(run_id)

    if not test_run:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")

    if test_run.status not in [TestRunStatus.COMPLETED, TestRunStatus.FAILED, TestRunStatus.ABORTED]:
        raise HTTPException(status_code=409, detail="Test run not completed yet")

    return {
        "run_id": test_run.run_id,
        "scenario_id": test_run.scenario_id,
        "status": test_run.status.value,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "duration_ms": (asyncio.get_event_loop().time() * 1000) if test_run.end_time else None,
        "parameters": test_run.parameters,
        "steps": [
            {
                "step_id": result.step_id,
                "status": result.status,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "readings": result.readings
            }
            for result in test_run.results
        ],
        "summary": {
            "total_steps": len(test_run.results),
            "passed_steps": len([r for r in test_run.results if r.status == "passed"]),
            "failed_steps": len([r for r in test_run.results if r.status == "failed"]),
            "assertions": {
                "total": len([r for r in test_run.results if r.step_id.startswith("assert")]),
                "passed": len([r for r in test_run.results if r.step_id.startswith("assert") and r.status == "passed"]),
                "failed": len([r for r in test_run.results if r.step_id.startswith("assert") and r.status == "failed"])
            }
        }
    }


# Plugin Management Endpoints

@app.get("/plugins")
async def list_plugins():
    """List loaded plugins"""
    tb = await get_test_bench()

    return {
        "loaded_plugins": tb.get_loaded_plugins(),
        "available_plugins": tb.get_available_plugins()
    }


# Configuration Endpoints

@app.post("/config/reload")
async def reload_configuration():
    """Reload test bench configuration"""
    tb = await get_test_bench()

    try:
        success = await tb.reload_config()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reload configuration")

        return {"status": "reloaded", "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading config: {str(e)}")


# Firmware Flashing Endpoints

@app.post("/flash")
async def start_flash(request: Dict[str, Any]):
    """Start firmware flashing"""
    tb = await get_test_bench()

    required_fields = ["target_device", "firmware_file", "protocol"]
    for field in required_fields:
        if field not in request:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    try:
        flash_id = await tb.start_flash(
            target_device=request["target_device"],
            firmware_file=request["firmware_file"],
            protocol=request["protocol"],
            parameters=request.get("parameters", {})
        )

        return {
            "flash_id": flash_id,
            "status": "queued",
            "created_at": asyncio.get_event_loop().time()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting flash: {str(e)}")


@app.get("/flash/status")
async def get_flash_status(flash_id: Optional[str] = None):
    """Get flash status"""
    tb = await get_test_bench()

    try:
        status = tb.get_flash_status(flash_id)
        if flash_id and status is None:
            raise HTTPException(status_code=404, detail="Flash operation not found")
        return status
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/flash/status/{flash_id}")
async def get_flash_status_detail(flash_id: str):
    """Get detailed flash status"""
    tb = await get_test_bench()

    try:
        status = tb.get_flash_status(flash_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Flash operation not found")
        return status
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/flash/{flash_id}")
async def cancel_flash(flash_id: str):
    """Cancel flash operation"""
    tb = await get_test_bench()

    try:
        success = await tb.cancel_flash(flash_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flash operation not found")

        return {
            "flash_id": flash_id,
            "status": "cancelled",
            "cancelled_at": asyncio.get_event_loop().time()
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/flash/upload")
async def upload_firmware(
    file: UploadFile = File(...),
    description: Optional[str] = None
):
    """Upload firmware file"""
    tb = await get_test_bench()

    try:
        # Read file content
        content = await file.read()

        # Upload firmware
        firmware_file = await tb.upload_firmware(
            filename=file.filename,
            content=content,
            description=description
        )

        return firmware_file
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/flash/files")
async def list_firmware_files():
    """List firmware files"""
    tb = await get_test_bench()

    try:
        files = tb.list_firmware_files()
        return {"files": files}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/flash/files/{file_id}")
async def delete_firmware_file(file_id: str):
    """Delete firmware file"""
    tb = await get_test_bench()

    try:
        success = await tb.delete_firmware(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Firmware file not found or in use")

        return {
            "file_id": file_id,
            "status": "deleted"
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc),
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    )
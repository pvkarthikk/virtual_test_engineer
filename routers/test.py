from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from core.system import SDTBSystem
from models.test import TestScriptSaveRequest, TestScript, TestScriptMetadata
from typing import List

router = APIRouter(prefix="/test", tags=["Test Execution"])

# Access the singleton system instance via call to ensure we always have the current instance
def get_system():
    return SDTBSystem()

@router.post("/run")
async def run_test(background_tasks: BackgroundTasks, script: str = Body(..., media_type="text/plain")):
    """
    Executes a test sequence provided in JSONL format.
    Runs asynchronously in the background.
    """
    try:
        system = get_system()
        # Synchronously claim the engine and get a one-time token.
        # This prevents race conditions from concurrent HTTP requests.
        token = system.test_engine.claim_engine()
        
        # Pass the token to the background task to prove authorization
        background_tasks.add_task(system.test_engine.run_jsonl_script, script, token=token)
        return {"message": "Test sequence accepted and started in the background"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=f"Test sequence rejected: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to initiate test: {e}")

@router.post("/stop")
async def stop_test():
    """
    Aborts the currently running test sequence.
    """
    system = get_system()
    if not system.test_engine.is_test_running:
        return {"message": "No test is currently running"}
        
    system.test_engine.stop()
    return {"message": "Abort signal sent to test engine"}

@router.get("/status")
async def get_test_status():
    """
    Returns the current operational status of the test engine.
    """
    system = get_system()
    engine = system.test_engine
    last_run_status = None
    if not engine.is_test_running and engine.history:
        last_run = engine.history[-1]
        if any(r.status in ["fail", "error"] for r in last_run.results):
            last_run_status = "fail"
        elif last_run.results:
            last_run_status = "pass"

    return {
        "is_running": engine.is_test_running,
        "abort_requested": engine._stop_requested,
        "current_step": engine.current_step,
        "total_steps": engine.total_steps,
        "progress": engine.progress,
        "last_run_status": last_run_status
    }

@router.get("/history")
async def get_test_history():
    """
    Returns the history of all executed test steps.
    """
    return get_system().test_engine.history

@router.delete("/history")
async def clear_test_history():
    """
    Clears the history of executed test steps.
    """
    get_system().test_engine.history.clear()
    return {"message": "Test history cleared"}

@router.post("/save", response_model=dict)
async def save_test_script(request: TestScriptSaveRequest):
    """
    Stores a JSONL test script and returns its unique ID.
    """
    system = get_system()
    script_id = system.script_manager.save_script(request.description, request.steps)
    return {"id": script_id}

@router.get("/retrieve", response_model=List[TestScriptMetadata])
async def retrieve_test_scripts():
    """
    Returns a list of all saved test scripts and their descriptions.
    """
    system = get_system()
    return system.script_manager.list_scripts()

@router.get("/retrieve/{script_id}", response_model=TestScript)
async def retrieve_test_script(script_id: str):
    """
    Returns the full content and metadata for a specific test script.
    """
    system = get_system()
    script = system.script_manager.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script with ID {script_id} not found")
    return script

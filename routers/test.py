from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from core.system import SDTBSystem

router = APIRouter(prefix="/test", tags=["Test Execution"])

# Access the singleton system instance
system = SDTBSystem()

@router.post("/run")
async def run_test(background_tasks: BackgroundTasks, script: str = Body(..., media_type="text/plain")):
    """
    Executes a test sequence provided in JSONL format.
    Runs asynchronously in the background.
    """
    if system.test_engine.is_test_running:
        raise HTTPException(status_code=409, detail="A test is already running. Please wait or stop the current test.")
    
    try:
        # Pass the task to background
        background_tasks.add_task(system.test_engine.run_jsonl_script, script)
        return {"message": "Test sequence accepted and started in the background"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to initiate test: {e}")

@router.post("/stop")
async def stop_test():
    """
    Aborts the currently running test sequence.
    """
    if not system.test_engine.is_test_running:
        return {"message": "No test is currently running"}
        
    system.test_engine.stop()
    return {"message": "Abort signal sent to test engine"}

@router.get("/status")
async def get_test_status():
    """
    Returns the current operational status of the test engine.
    """
    return {
        "is_running": system.test_engine.is_test_running,
        "abort_requested": system.test_engine._stop_requested
    }

@router.get("/history")
async def get_test_history():
    """
    Returns the history of all executed test steps.
    """
    return system.test_engine.history

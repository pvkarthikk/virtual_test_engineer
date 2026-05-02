from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from core.system import SDTBSystem

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
    return {
        "is_running": system.test_engine.is_test_running,
        "abort_requested": system.test_engine._stop_requested
    }

@router.get("/history")
async def get_test_history():
    """
    Returns the history of all executed test steps.
    """
    return get_system().test_engine.history

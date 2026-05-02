from fastapi import APIRouter, HTTPException
from core.system import SDTBSystem
from models.config import UIConfig

router = APIRouter(prefix="/ui", tags=["UI Configuration"])

# Access the singleton system instance via call to ensure we always have the current instance
def get_system():
    return SDTBSystem()

@router.get("/config")
async def get_ui_config():
    """
    Retrieves the current UI dashboard configuration (ui.json).
    """
    try:
        return get_system().config_manager.load_config("ui", UIConfig)
    except Exception as e:
        # Return a blank dashboard config if it doesn't exist
        return {"layout": "default", "widgets": []}

@router.put("/config")
async def update_ui_config(config: UIConfig):
    """
    Updates the UI dashboard layout and widget mappings.
    """
    try:
        get_system().config_manager.save_config("ui", config)
        return {"message": "UI configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

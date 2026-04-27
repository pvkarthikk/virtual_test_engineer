import pytest
import asyncio
from core.system import SDTBSystem

@pytest.mark.asyncio
async def test_test_history_persistence(sdtb_system):
    """
    Verifies that test results are stored in history.
    """
    engine = sdtb_system.test_engine
    engine.history.clear()
    
    script = """
    {"action": "wait", "duration_ms": 100}
    {"action": "wait", "duration_ms": 100}
    """
    
    await engine.run_jsonl_script(script)
    
    assert len(engine.history) == 2
    assert engine.history[0].action == "wait"
    assert engine.history[1].step_index == 1

from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, Optional

class WriteStep(BaseModel):
    action: Literal["write"]
    channel: str
    value: float

class WaitStep(BaseModel):
    action: Literal["wait"]
    duration_ms: int

class AssertStep(BaseModel):
    action: Literal["assert"]
    channel: str
    condition: Literal[">", ">=", "<", "<=", "==", "!="]
    value: float

class FaultStep(BaseModel):
    action: Literal["fault"]
    device: str
    signal: str
    fault_id: str # 'short_to_ground', 'open_circuit', etc.
    duration_ms: Optional[int] = None # If None, it stays injected

# Discriminated union for test steps
TestStep = Annotated[
    Union[WriteStep, WaitStep, AssertStep, FaultStep], 
    Field(discriminator='action')
]

class TestResult(BaseModel):
    __test__ = False
    step_index: int
    action: str
    status: Literal["pass", "fail", "error"]
    message: str
    timestamp: float

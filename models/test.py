from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated

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

# Discriminated union for test steps
TestStep = Annotated[
    Union[WriteStep, WaitStep, AssertStep], 
    Field(discriminator='action')
]

class TestResult(BaseModel):
    step_index: int
    action: str
    status: Literal["pass", "fail", "error"]
    message: str
    timestamp: float

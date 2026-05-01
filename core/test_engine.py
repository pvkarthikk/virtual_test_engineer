import json
import asyncio
import time
import logging
import math
from typing import List, Optional, Callable, Any
from models.test import TestStep, WriteStep, WaitStep, AssertStep, FaultStep, TestResult
from core.channel_manager import ChannelManager

logger = logging.getLogger(__name__)

class TestEngine:
    __test__ = False
    def __init__(self, channel_manager: ChannelManager, device_manager: Optional[Any] = None):
        self.channel_manager = channel_manager
        self.device_manager = device_manager
        self.is_test_running = False
        self._stop_requested = False
        self._current_task: Optional[asyncio.Task] = None
        
        # Callback for real-time progress reporting (e.g., via SSE)
        self.on_step_complete: Optional[Callable[[TestResult], None]] = None
        self.history: List[TestResult] = []

    async def run_jsonl_script(self, jsonl_content: str):
        """
        Parses and executes a JSONL test script.
        """
        if self.is_test_running:
            raise RuntimeError("A test is already running. Concurrency is not allowed.")

        self.is_test_running = True
        self._stop_requested = False
        
        try:
            # 1. Parse JSONL
            steps = []
            for i, line in enumerate(jsonl_content.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    # Uses Pydantic's discriminated union to parse correctly
                    from pydantic import TypeAdapter
                    adapter = TypeAdapter(TestStep)
                    step = adapter.validate_json(line)
                    steps.append(step)
                except Exception as e:
                    logger.error(f"Syntax error in JSONL line {i+1}: {e}")
                    raise ValueError(f"Line {i+1}: Invalid step format: {e}")

            # 2. Sequential Execution
            logger.info(f"Starting execution of {len(steps)} test steps...")
            for i, step in enumerate(steps):
                if self._stop_requested:
                    logger.warning("Test execution aborted by user.")
                    break
                
                result = await self._execute_step(i, step)
                
                # Report result via callback
                if self.on_step_complete:
                    self.on_step_complete(result)
                
                if result.status != "pass":
                    logger.error(f"Test aborted at step {i+1} due to {result.status}: {result.message}")
                    break
                    
            logger.info("Test execution finished.")

        finally:
            self.is_test_running = False

    async def _execute_step(self, index: int, step: TestStep) -> TestResult:
        """
        Executes a single test step and returns the result.
        """
        start_time = time.time()
        status = "pass"
        message = "Step completed successfully"

        try:
            if isinstance(step, WriteStep):
                logger.info(f"Step {index}: Writing {step.value} to {step.channel}")
                await self.channel_manager.write_channel(step.channel, step.value)
                
            elif isinstance(step, WaitStep):
                logger.info(f"Step {index}: Waiting for {step.duration_ms}ms")
                await asyncio.sleep(step.duration_ms / 1000.0)
                
            elif isinstance(step, AssertStep):
                logger.info(f"Step {index}: Asserting {step.channel} {step.condition} {step.value}")
                actual_value = await self.channel_manager.read_channel(step.channel)
                
                if not self._evaluate_assertion(actual_value, step.condition, step.value):
                    status = "fail"
                    message = f"Assertion failed: Expected {step.condition} {step.value}, got {actual_value}"
                    
            elif isinstance(step, FaultStep):
                if not self.device_manager:
                    raise RuntimeError("DeviceManager not available in TestEngine")
                
                logger.info(f"Step {index}: Injecting fault '{step.fault_id}' on {step.device}/{step.signal}")
                device = self.device_manager.get_device(step.device)
                if not device:
                    raise ValueError(f"Device {step.device} not found")
                
                await asyncio.to_thread(device.inject_fault, step.signal, step.fault_id)
                
                if step.duration_ms:
                    logger.info(f"Step {index}: Keeping fault for {step.duration_ms}ms")
                    await asyncio.sleep(step.duration_ms / 1000.0)
                    logger.info(f"Step {index}: Clearing fault '{step.fault_id}'")
                    await asyncio.to_thread(device.clear_fault, step.signal)
        except Exception as e:
            status = "error"
            message = f"Unexpected error: {str(e)}"
            logger.exception(f"Step {index} failed with error")

        result = TestResult(
            step_index=index,
            action=step.action,
            status=status,
            message=message,
            timestamp=start_time
        )
        self.history.append(result)
        # Prevent memory leak by limiting history size
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        return result

    def _evaluate_assertion(self, actual: float, condition: str, target: float) -> bool:
        """
        Evaluates the assertion logic with floating-point tolerance for equality.
        """
        if condition == "==": return math.isclose(actual, target, rel_tol=1e-6, abs_tol=1e-9)
        if condition == "!=": return not math.isclose(actual, target, rel_tol=1e-6, abs_tol=1e-9)
        if condition == ">":  return actual > target
        if condition == ">=": return actual >= target
        if condition == "<":  return actual < target
        if condition == "<=": return actual <= target
        return False

    def stop(self):
        """
        Sets the stop flag to abort test execution.
        """
        self._stop_requested = True

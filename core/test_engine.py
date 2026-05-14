import asyncio
import time
import uuid
import logging
import math
from typing import List, Optional, Callable, Any
from models.test import TestStep, WriteStep, WaitStep, AssertStep, FaultStep, TestResult, TestRun
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
        self.history: List[TestRun] = []
        self._current_run: Optional[TestRun] = None
        self._active_token: Optional[str] = None
        self.current_step = 0
        self.total_steps = 0

    @property
    def progress(self) -> float:
        """
        Returns the percentage of completion for the current test.
        """
        if self.total_steps == 0:
            return 0.0
        return round((self.current_step / self.total_steps) * 100, 2)

    def get_test_history(self, last_n: Optional[int] = None) -> List[dict]:
        """
        Returns the history of test step results.
        """
        results = self.history
        if last_n:
            results = results[-last_n:]
        return [r.model_dump() for r in results]

    def claim_engine(self) -> str:
        """
        Synchronously claims the test engine and returns a one-time execution token.
        This prevents race conditions between API acceptance and background task start.
        """
        if self.is_test_running:
            raise RuntimeError("A test is already running.")
        
        self.is_test_running = True
        token = str(uuid.uuid4())
        self._active_token = token
        return token

    async def run_jsonl_script(self, jsonl_content: str, token: Optional[str] = None):
        """
        Parses and executes a JSONL test script.
        """
        try:
            # If a token is provided, verify it matches the active reservation.
            # If no token is provided, attempt a fresh lock.
            if token is not None:
                if token != self._active_token:
                    raise RuntimeError("Invalid or expired execution token.")
                # Token validated, engine already marked as running by claim_engine()
                self._active_token = None # Consume token
            else:
                if self.is_test_running:
                    raise RuntimeError("A test is already running. Concurrency is not allowed.")
                self.is_test_running = True
            
            self._stop_requested = False

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
            await self.run_test_steps(steps, internal_lock=True)

        except Exception as e:
            self._log(f"Test execution FAILED: {str(e)}", "error")
            raise
        finally:
            if token is None: # Only clear if we didn't use a token (if we did, run_test_steps handled it or we failed before)
                 self.is_test_running = False
            self.current_step = 0
            self.total_steps = 0
            self._active_token = None

    async def run_test_steps(self, steps: List[TestStep], token: Optional[str] = None, internal_lock: bool = False):
        """
        Executes a list of test steps.
        """
        try:
            if not internal_lock:
                if token is not None:
                    if token != self._active_token:
                        raise RuntimeError("Invalid or expired execution token.")
                    self._active_token = None 
                else:
                    if self.is_test_running:
                        raise RuntimeError("A test is already running. Concurrency is not allowed.")
                    self.is_test_running = True
                
                self._stop_requested = False

            self.total_steps = len(steps)
            self.current_step = 0
            logger.info(f"Starting execution of {self.total_steps} test steps...")
            
            self._current_run = TestRun(id=str(uuid.uuid4()), timestamp=time.time(), results=[], logs=[])
            self.history.append(self._current_run)
            if len(self.history) > 100:
                self.history.pop(0)

            for i, step in enumerate(steps):
                if self._stop_requested:
                    break
                
                self.current_step = i + 1
                result = await self._execute_step(i, step)
                
                # Append to current run history
                if self._current_run:
                    self._current_run.results.append(result)

                # Report result via callback
                if self.on_step_complete:
                    self.on_step_complete(result)
                
                if result.status != "pass":
                    break
            
            if self._stop_requested:
                self._log("Test execution ABORTED by user.", "warning")
            elif self.current_step == self.total_steps and self.total_steps > 0:
                self._log(f"Test execution FINISHED: {self.total_steps}/{self.total_steps} steps passed.", "info")
            else:
                self._log(f"Test execution STOPPED at step {self.current_step}/{self.total_steps}.", "error")

        except Exception as e:
            self._log(f"Test execution FAILED: {str(e)}", "error")
            raise
        finally:
            self.is_test_running = False
            self.current_step = 0
            self.total_steps = 0
            self._active_token = None 

    async def _execute_step(self, index: int, step: TestStep) -> TestResult:
        """
        Executes a single test step and returns the result.
        """
        start_time = time.time()
        status = "pass"
        message = "Step completed successfully"

        try:
            if isinstance(step, WriteStep):
                self._log(f"Step {index}: Writing {step.value} to {step.channel}")
                await self.channel_manager.write_channel(step.channel, step.value)
                
            elif isinstance(step, WaitStep):
                self._log(f"Step {index}: Waiting for {step.duration_ms}ms")
                await asyncio.sleep(step.duration_ms / 1000.0)
                
            elif isinstance(step, AssertStep):
                self._log(f"Step {index}: Asserting {step.channel} {step.condition} {step.value}")
                actual_value = await self.channel_manager.read_channel(step.channel)
                
                if not self._evaluate_assertion(actual_value, step.condition, step.value):
                    status = "fail"
                    message = f"Assertion failed: Expected {step.condition} {step.value}, got {actual_value}"
                    
            elif isinstance(step, FaultStep):
                if not self.device_manager:
                    raise RuntimeError("DeviceManager not available in TestEngine")
                
                self._log(f"Step {index}: Injecting fault '{step.fault_id}' on {step.device}/{step.signal}")
                device = self.device_manager.get_device(step.device)
                if not device:
                    raise ValueError(f"Device {step.device} not found")
                
                await asyncio.to_thread(device.inject_fault, step.signal, step.fault_id)
                
                if step.duration_ms:
                    self._log(f"Step {index}: Keeping fault for {step.duration_ms}ms")
                    await asyncio.sleep(step.duration_ms / 1000.0)
                    self._log(f"Step {index}: Clearing fault '{step.fault_id}'")
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

    def _log(self, message: str, level: str = "info"):
        """
        Logs a message to the system logger and also to the current run's log history.
        """
        if level == "info": logger.info(message)
        elif level == "error": logger.error(message)
        elif level == "warning": logger.warning(message)
        
        if self._current_run:
            self._current_run.logs.append(f"{level.upper()} | {message}")

    def stop(self):
        """
        Sets the stop flag to abort test execution.
        """
        self._stop_requested = True

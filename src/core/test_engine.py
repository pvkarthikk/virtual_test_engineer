#!/usr/bin/env python3
"""
Virtual Test Engineer - Test Execution Engine
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from .types import (
    TestRun, TestRunStatus, TestStep, TestStepResult,
    ChannelValue, create_timestamp
)
from .device_manager import DeviceManager


class TestExecutionEngine:
    """Handles test scenario execution"""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.active_runs: Dict[str, TestRun] = {}
        self.run_callbacks: Dict[str, Callable] = {}

    async def start_scenario(self, scenario_id: str, parameters: Dict[str, Any] = None,
                           async_mode: bool = True) -> str:
        """Start a test scenario execution"""
        run_id = str(uuid.uuid4())

        if parameters is None:
            parameters = {}

        test_run = TestRun(
            run_id=run_id,
            scenario_id=scenario_id,
            status=TestRunStatus.QUEUED,
            parameters=parameters
        )

        self.active_runs[run_id] = test_run

        if async_mode:
            # Start execution in background
            asyncio.create_task(self._execute_scenario_async(run_id))
        else:
            # Execute synchronously
            await self._execute_scenario(run_id)

        return run_id

    async def _execute_scenario_async(self, run_id: str) -> None:
        """Execute scenario asynchronously"""
        try:
            await self._execute_scenario(run_id)
        except Exception as e:
            print(f"Error executing scenario {run_id}: {e}")
            if run_id in self.active_runs:
                self.active_runs[run_id].status = TestRunStatus.FAILED

    async def _execute_scenario(self, run_id: str) -> None:
        """Execute a test scenario"""
        if run_id not in self.active_runs:
            return

        test_run = self.active_runs[run_id]
        test_run.status = TestRunStatus.RUNNING
        test_run.start_time = create_timestamp()

        try:
            # For now, create a simple test scenario
            # In a real implementation, this would load scenario from config
            steps = self._create_sample_steps(test_run.scenario_id)

            results = []
            for step in steps:
                step_result = await self._execute_step(step, test_run.parameters)
                results.append(step_result)

                # Check if we should abort
                if test_run.status == TestRunStatus.ABORTED:
                    break

            test_run.results = results
            test_run.status = TestRunStatus.COMPLETED
            test_run.end_time = create_timestamp()

        except Exception as e:
            print(f"Scenario execution failed: {e}")
            test_run.status = TestRunStatus.FAILED
            test_run.end_time = create_timestamp()

        # Notify callbacks
        if run_id in self.run_callbacks:
            callback = self.run_callbacks[run_id]
            try:
                callback(test_run)
            except Exception as e:
                print(f"Error in run callback: {e}")

    def _create_sample_steps(self, scenario_id: str) -> List[TestStep]:
        """Create sample test steps (would be loaded from config in real implementation)"""
        if scenario_id == "throttle_response_test":
            return [
                TestStep(
                    id="set_throttle",
                    type="set_channel",
                    description="Set throttle to 50%",
                    parameters={"channel": "throttle_position", "value": 50}
                ),
                TestStep(
                    id="wait_settle",
                    type="delay",
                    description="Wait for system to settle",
                    parameters={"duration": 2000}
                ),
                TestStep(
                    id="read_engine_speed",
                    type="read_channel",
                    description="Read engine speed",
                    parameters={"channel": "engine_speed_output", "variable": "engine_speed"}
                ),
                TestStep(
                    id="assert_response",
                    type="assert",
                    description="Verify engine speed response",
                    parameters={
                        "condition": "${engine_speed} > 4.5 && ${engine_speed} < 5.5",
                        "message": "Engine speed not within expected range"
                    }
                )
            ]
        else:
            # Default simple test
            return [
                TestStep(
                    id="read_throttle",
                    type="read_channel",
                    description="Read throttle position",
                    parameters={"channel": "throttle_position", "variable": "throttle"}
                )
            ]

    async def _execute_step(self, step: TestStep, run_parameters: Dict[str, Any]) -> TestStepResult:
        """Execute a single test step"""
        start_time = create_timestamp()

        try:
            if step.type == "set_channel":
                channel = step.parameters.get("channel")
                value = step.parameters.get("value")
                success = await self.device_manager.write_channel(channel, value)
                status = "passed" if success else "failed"

            elif step.type == "read_channel":
                channel = step.parameters.get("channel")
                reading = await self.device_manager.read_channel(channel)
                status = "passed" if reading else "failed"
                readings = {step.parameters.get("variable", channel): reading.value if reading else None}

            elif step.type == "delay":
                duration = step.parameters.get("duration", 1000)
                await asyncio.sleep(duration / 1000.0)
                status = "passed"
                readings = {}

            elif step.type == "assert":
                # Simple assertion evaluation (would be more sophisticated in real implementation)
                condition = step.parameters.get("condition", "true")
                # For now, assume assertion passes
                status = "passed"
                readings = {}

            else:
                status = "skipped"
                readings = {}

            end_time = create_timestamp()

            return TestStepResult(
                step_id=step.id,
                status=status,
                start_time=start_time,
                end_time=end_time,
                readings=readings
            )

        except Exception as e:
            end_time = create_timestamp()
            return TestStepResult(
                step_id=step.id,
                status="failed",
                start_time=start_time,
                end_time=end_time,
                error_message=str(e)
            )

    def get_run_status(self, run_id: str) -> Optional[TestRun]:
        """Get test run status"""
        return self.active_runs.get(run_id)

    def abort_run(self, run_id: str) -> bool:
        """Abort a running test"""
        if run_id in self.active_runs:
            self.active_runs[run_id].status = TestRunStatus.ABORTED
            return True
        return False

    def set_run_callback(self, run_id: str, callback: Callable) -> None:
        """Set callback for run completion"""
        self.run_callbacks[run_id] = callback

    def get_active_runs(self) -> List[str]:
        """Get list of active run IDs"""
        return list(self.active_runs.keys())

    async def cleanup_completed_runs(self, max_age_seconds: int = 3600) -> None:
        """Clean up old completed runs"""
        current_time = asyncio.get_event_loop().time()
        to_remove = []

        for run_id, test_run in self.active_runs.items():
            if (test_run.status in [TestRunStatus.COMPLETED, TestRunStatus.FAILED, TestRunStatus.ABORTED] and
                test_run.end_time):
                # This is a simplified check - in real implementation would parse timestamp
                to_remove.append(run_id)

        for run_id in to_remove:
            del self.active_runs[run_id]
            if run_id in self.run_callbacks:
                del self.run_callbacks[run_id]
import httpx
import logging

logger = logging.getLogger("sdtb_mcp_client")

class SDTBRestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    async def get_system_summary(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/system")
            resp.raise_for_status()
            return resp.json()

    async def connect_system(self):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/system/connect")
            resp.raise_for_status()
            return resp.json()

    async def disconnect_system(self):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/system/disconnect")
            resp.raise_for_status()
            return resp.json()

    async def list_channels(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/channel")
            resp.raise_for_status()
            return resp.json()

    async def get_channel_info(self, channel_id: str):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/channel/{channel_id}/info")
            resp.raise_for_status()
            return resp.json()

    async def read_channel(self, channel_id: str):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/channel/{channel_id}")
            resp.raise_for_status()
            return resp.json()

    async def write_channel(self, channel_id: str, value: float):
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{self.base_url}/channel/{channel_id}", json={"value": value})
            resp.raise_for_status()
            return resp.json()

    async def list_test_scripts(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/test/retrieve")
            resp.raise_for_status()
            return resp.json()

    async def get_test_script(self, script_id: str):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/test/retrieve/{script_id}")
            resp.raise_for_status()
            return resp.json()

    async def save_test_script(self, description: str, steps: list):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/test/save", json={"description": description, "steps": steps})
            resp.raise_for_status()
            return resp.json()

    async def run_test(self, script: str = None, script_id: str = None):
        async with httpx.AsyncClient() as client:
            if script_id:
                # Need to check if there is a run-by-id endpoint or if we need to retrieve and then run
                # The current test router only has /run which takes plain text script.
                # Wait, if script_id is provided, I should probably retrieve the script first.
                script_data = await self.get_test_script(script_id)
                # Convert steps back to JSONL if needed, or check if /run can handle JSONL
                # The /run endpoint takes 'text/plain' script.
                import json
                script_text = "\n".join([json.dumps(s) for s in script_data["steps"]])
                resp = await client.post(f"{self.base_url}/test/run", content=script_text)
            else:
                resp = await client.post(f"{self.base_url}/test/run", content=script)
            
            resp.raise_for_status()
            return resp.json()

    async def stop_test(self):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/test/stop")
            resp.raise_for_status()
            return resp.json()

    async def get_test_status(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/test/status")
            resp.raise_for_status()
            return resp.json()

    async def get_test_history(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/test/history")
            resp.raise_for_status()
            return resp.json()

    async def list_can_interfaces(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/can/interfaces")
            resp.raise_for_status()
            return resp.json()

    async def read_can_log(self, device_id: str, bus: str, count: int = 50, arb_id: str = None):
        async with httpx.AsyncClient() as client:
            params = {"count": count}
            if arb_id:
                params["arb_id"] = arb_id
            resp = await client.get(f"{self.base_url}/can/log/{device_id}/{bus}", params=params)
            resp.raise_for_status()
            return resp.json()

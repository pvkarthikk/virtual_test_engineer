import asyncio
import json
import logging
from typing import Dict, List, Any, AsyncGenerator

class SSELogHandler(logging.Handler):
    def __init__(self, stream_manager):
        super().__init__()
        self.stream_manager = stream_manager

    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream_manager.push_log(msg)
        except Exception:
            self.handleError(record)

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self):
        # List of queues for global system logs
        self.log_queues: List[asyncio.Queue] = []
        
        # Dict mapping channel_id to list of subscriber queues
        self.channel_queues: Dict[str, List[asyncio.Queue]] = {}
        
        # Dict mapping "device_id:signal_id" to list of subscriber queues
        self.device_queues: Dict[str, List[asyncio.Queue]] = {}

    async def subscribe_logs(self) -> AsyncGenerator[Dict[str, str], None]:
        """
        Subscribes to global system logs. Yields SSE-formatted dicts.
        """
        queue = asyncio.Queue()
        self.log_queues.append(queue)
        try:
            while True:
                message = await queue.get()
                yield {"data": message}
        finally:
            self.log_queues.remove(queue)

    async def subscribe_channel(self, channel_id: str) -> AsyncGenerator[Dict[str, str], None]:
        """
        Subscribes to updates for a specific channel. Yields SSE-formatted dicts.
        """
        if channel_id not in self.channel_queues:
            self.channel_queues[channel_id] = []
            
        queue = asyncio.Queue()
        self.channel_queues[channel_id].append(queue)
        try:
            while True:
                data = await queue.get()
                yield {"data": json.dumps(data)}
        finally:
            self.channel_queues[channel_id].remove(queue)

    async def subscribe_device_signal(self, device_id: str, signal_id: str) -> AsyncGenerator[Dict[str, str], None]:
        """
        Subscribes to updates for a raw device signal.
        """
        key = f"{device_id}:{signal_id}"
        if key not in self.device_queues:
            self.device_queues[key] = []
            
        queue = asyncio.Queue()
        self.device_queues[key].append(queue)
        try:
            while True:
                data = await queue.get()
                yield {"data": json.dumps(data)}
        finally:
            self.device_queues[key].remove(queue)

    def push_log(self, message: str):
        """
        Pushes a log message to all active subscribers.
        """
        for queue in self.log_queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Global log queue is full, dropping message.")

    def push_channel_update(self, channel_id: str, value: Any):
        """
        Pushes a channel value update to all active subscribers for that channel.
        """
        if channel_id in self.channel_queues:
            update = {
                "channel_id": channel_id, 
                "value": value, 
                "timestamp": asyncio.get_event_loop().time()
            }
            for queue in self.channel_queues[channel_id]:
                try:
                    queue.put_nowait(update)
                except asyncio.QueueFull:
                    logger.warning(f"Channel queue for '{channel_id}' is full, dropping update.")

    def push_device_signal_update(self, device_id: str, signal_id: str, value: Any):
        """
        Pushes a raw device signal update to all active subscribers.
        """
        key = f"{device_id}:{signal_id}"
        if key in self.device_queues:
            update = {
                "device_id": device_id,
                "signal_id": signal_id,
                "value": value,
                "timestamp": asyncio.get_event_loop().time()
            }
            for queue in self.device_queues[key]:
                try:
                    queue.put_nowait(update)
                except asyncio.QueueFull:
                    logger.warning(f"Device signal queue for '{key}' is full, dropping update.")

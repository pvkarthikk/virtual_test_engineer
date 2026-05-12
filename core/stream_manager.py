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
        
        # List of queues for unified global stream (multiplexing)
        self.global_queues: List[asyncio.Queue] = []

        # Dict mapping "device_id:bus" to list of subscriber queues
        self.can_queues: Dict[str, List[asyncio.Queue]] = {}

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

    async def subscribe_all(self) -> AsyncGenerator[Dict[str, str], None]:
        """
        Subscribes to all events multiplexed into a single stream.
        """
        queue = asyncio.Queue()
        self.global_queues.append(queue)
        try:
            while True:
                data = await queue.get()
                yield {"data": json.dumps(data)}
        finally:
            self.global_queues.remove(queue)

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
                
        # Also push to unified stream
        global_msg = {"type": "log", "message": message}
        for queue in self.global_queues:
            try:
                queue.put_nowait(global_msg)
            except asyncio.QueueFull:
                pass

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
                    
        # Also push to unified stream
        global_update = {
            "type": "channel",
            "channel_id": channel_id,
            "value": value,
            "timestamp": asyncio.get_event_loop().time()
        }
        for queue in self.global_queues:
            try:
                queue.put_nowait(global_update)
            except asyncio.QueueFull:
                pass

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
                    
        # Also push to unified stream
        global_update = {
            "type": "device_signal",
            "device_id": device_id,
            "signal_id": signal_id,
            "value": value,
            "timestamp": asyncio.get_event_loop().time()
        }
        for queue in self.global_queues:
            try:
                queue.put_nowait(global_update)
            except asyncio.QueueFull:
                pass

    async def subscribe_can(self, device_id: str, bus: str) -> AsyncGenerator[Dict[str, str], None]:
        """
        Subscribes to updates for a specific CAN bus.
        """
        key = f"{device_id}:{bus}"
        if key not in self.can_queues:
            self.can_queues[key] = []
            
        queue = asyncio.Queue()
        self.can_queues[key].append(queue)
        try:
            while True:
                data = await queue.get()
                yield {"data": json.dumps(data)}
        finally:
            self.can_queues[key].remove(queue)

    def push_can_frame(self, device_id: str, bus: str, frame: Any):
        """
        Pushes a CAN frame update to all active subscribers.
        """
        key = f"{device_id}:{bus}"
        
        # Serialize for JSON transport
        frame_data = {
            "timestamp": frame.timestamp,
            "bus": frame.bus,
            "arbitration_id": f"0x{frame.arbitration_id:X}",
            "dlc": frame.dlc,
            "data": frame.data.hex(),
            "is_extended": frame.is_extended,
            "is_error": frame.is_error,
            "is_remote": frame.is_remote
        }

        if key in self.can_queues:
            for queue in self.can_queues[key]:
                try:
                    queue.put_nowait(frame_data)
                except asyncio.QueueFull:
                    pass
                    
        # Also push to unified stream
        global_update = {
            "type": "can_frame",
            "device_id": device_id,
            "bus": bus,
            **frame_data
        }
        for queue in self.global_queues:
            try:
                queue.put_nowait(global_update)
            except asyncio.QueueFull:
                pass

import collections
from typing import List, Dict, Optional, Any
from .base_device import CANFrame, BaseDevice

class CANLogBuffer:
    """
    In-memory ring buffer for CAN frames with filtering and retrieval capabilities.
    """
    def __init__(self, maxlen: int = 10000):
        self._buffer = collections.deque(maxlen=maxlen)
        self._frame_count = 0

    def append(self, frame: CANFrame):
        self._buffer.append(frame)
        self._frame_count += 1

    def get_frames(self, count: int = 100, offset: int = 0, arb_id_filter: Optional[int] = None) -> List[CANFrame]:
        """
        Retrieves frames from the buffer with optional filtering and pagination.
        Frames are returned in reverse chronological order (newest first).
        """
        all_frames = list(self._buffer)
        all_frames.reverse() # Newest first

        # Apply arbitration ID filter if specified
        if arb_id_filter is not None:
            all_frames = [f for f in all_frames if f.arbitration_id == arb_id_filter]

        # Apply offset and count
        start = offset
        end = offset + count
        return all_frames[start:end]

    def clear(self):
        self._buffer.clear()

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def total_count(self) -> int:
        return self._frame_count

class CANManager:
    """
    Singleton-style manager for draining CAN frames from devices and managing buffers.
    """
    def __init__(self, stream_manager: Any):
        self.stream_manager = stream_manager
        self.buffers: Dict[str, CANLogBuffer] = {}

    def drain_device(self, device_id: str, device: BaseDevice):
        """
        Pulls pending CAN frames from a device and distributes them to buffers and streams.
        """
        frames = device.pop_can_frames()
        if not frames:
            return

        for frame in frames:
            key = f"{device_id}:{frame.bus}"
            if key not in self.buffers:
                self.buffers[key] = CANLogBuffer()
            
            self.buffers[key].append(frame)
            self.stream_manager.push_can_frame(device_id, frame.bus, frame)

    def get_frames(self, device_id: str, bus: str, count: int = 100, offset: int = 0, arb_id_filter: Optional[int] = None) -> List[CANFrame]:
        key = f"{device_id}:{bus}"
        if key in self.buffers:
            return self.buffers[key].get_frames(count, offset, arb_id_filter)
        return []

    def get_interfaces(self) -> List[Dict[str, Any]]:
        """
        Returns a summary of all active CAN interfaces and their buffer status.
        """
        interfaces = []
        for key, buffer in self.buffers.items():
            device_id, bus = key.split(':')
            interfaces.append({
                "device_id": device_id,
                "bus": bus,
                "buffer_size": buffer.size,
                "frame_count": buffer.total_count
            })
        return interfaces

    def clear(self, device_id: str, bus: str):
        key = f"{device_id}:{bus}"
        if key in self.buffers:
            self.buffers[key].clear()

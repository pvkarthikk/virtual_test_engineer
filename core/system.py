import logging
import os
import asyncio
import math
import json
from typing import List, Optional, Dict
from pydantic import TypeAdapter
from core.config_manager import ConfigManager
from core.device_manager import DeviceManager
from core.channel_manager import ChannelManager
from core.test_engine import TestEngine
from core.stream_manager import StreamManager, SSELogHandler
from core.flash_manager import FlashManager
from models.config import SystemConfig, ChannelConfig, UIConfig

logger = logging.getLogger(__name__)

class SDTBSystem:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SDTBSystem, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_dir: Optional[str] = None):
        # Prevent re-initialization if already initialized
        if hasattr(self, 'initialized') and self.initialized:
            return
        self.initialized = True
            
        if config_dir is None:
            # Default to current directory if not specified
            config_dir = os.path.join(os.getcwd(), "config")
            
        self.config_dir = config_dir
        self.config_manager = ConfigManager(self.config_dir)
        
        # Load System Configuration
        try:
            self.system_config = self.config_manager.load_config("system", SystemConfig)
        except Exception as e:
            logger.error(f"Critical failure loading system config: {e}")
            # In a real app, we might provide defaults here
            self.system_config = SystemConfig(
                device_directory=os.path.join(os.getcwd(), "devices"),
                server={"host": "0.0.0.0", "port": 8000}
            )

        # Initialize core managers
        self.device_manager = DeviceManager(self.system_config.device_directory, self.config_manager)
        self.stream_manager = StreamManager()
        self.flash_manager = FlashManager(self.system_config.device_directory, self.config_manager)
        self.channel_manager = ChannelManager(self.device_manager, self.stream_manager)
        self.test_engine = TestEngine(self.channel_manager)
        
        # Redirect all standard logging to the SSE stream
        root_logger = logging.getLogger()
        has_sse_handler = any(isinstance(h, SSELogHandler) for h in root_logger.handlers)
        
        if not has_sse_handler:
            sse_handler = SSELogHandler(self.stream_manager)
            sse_handler.setFormatter(logging.Formatter('%(levelname)s | %(name)s: %(message)s'))
            root_logger.addHandler(sse_handler)
        
        # Connect test engine results to log stream
        self.test_engine.on_step_complete = self._handle_test_step_result
        
        self.update_task: Optional[asyncio.Task] = None
        self._last_pushed_values: Dict[str, float] = {} # Key: "dev:sig" or "ch:id"
        logger.info("SDTB System Initialized")

    async def startup(self):
        """
        Performs the system startup sequence: discovery and channel mapping.
        """
        logger.info("Starting up SDTB System...")
        
        # 1. Discover and initialize devices and flash protocols
        self.device_manager.discover_and_initialize()
        self.flash_manager.discover_and_initialize()
        
        # 2. Load and initialize channels
        try:
            file_path = self.config_manager.get_file_path("channels")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                adapter = TypeAdapter(List[ChannelConfig])
                channels = adapter.validate_python(data)
                self.channel_manager.initialize_channels(channels)
            else:
                logger.warning(f"Channels config file not found: {file_path}")
        except Exception as e:
            logger.error(f"Could not load channels during startup: {e}")
            
        # 3. Start background update loop
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())
            logger.info(f"Started device update loop (rate: {self.system_config.device_update_rate}ms)")

    async def shutdown(self):
        """
        Performs system shutdown: disconnects devices and stops update loop.
        """
        logger.info("Shutting down SDTB System...")
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
        await self.device_manager.disconnect_all()
        await self.flash_manager.disconnect_all()

    async def restart(self):
        """
        Restarts the system: disconnects, re-initializes, and re-discovers.
        """
        logger.info("Restarting SDTB System...")
        await self.shutdown()
        self.initialized = False
        self.__init__(self.config_dir)
        await self.startup()

    def _handle_test_step_result(self, result):
        """
        Callback from TestEngine. Pushes result to log stream.
        """
        log_msg = f"Step {result.step_index} [{result.action}]: {result.status} - {result.message}"
        self.stream_manager.push_log(log_msg)

    async def _update_loop(self):
        """
        Periodic task that calls update() on all connected devices.
        """
        while True:
            try:
                rate_sec = self.system_config.device_update_rate / 1000.0
                await asyncio.sleep(rate_sec)
                
                devices = self.device_manager.get_all_devices()
                for dev_id, device in devices.items():
                    if device.is_connected:
                        try:
                            # Offload to thread to avoid blocking loop
                            await asyncio.to_thread(device.update)
                            
                            # Push raw signal updates to stream
                            signals = device.get_signals()
                            for sig in signals:
                                cache_key = f"dev:{dev_id}:{sig.signal_id}"
                                last_val = self._last_pushed_values.get(cache_key)
                                if last_val is None or not math.isclose(last_val, sig.value, rel_tol=1e-5):
                                    self.stream_manager.push_device_signal_update(dev_id, sig.signal_id, sig.value)
                                    self._last_pushed_values[cache_key] = sig.value
                                
                            # Push scaled channel updates to stream
                            for ch in self.channel_manager.get_all_channels():
                                if ch.device_id == dev_id:
                                    for sig in signals:
                                        if sig.signal_id == ch.signal_id:
                                            scaled_value = self.channel_manager.get_scaled_value(ch, sig.value)
                                            cache_key = f"ch:{ch.channel_id}"
                                            last_val = self._last_pushed_values.get(cache_key)
                                            if last_val is None or not math.isclose(last_val, scaled_value, rel_tol=1e-5):
                                                self.stream_manager.push_channel_update(ch.channel_id, scaled_value)
                                                self._last_pushed_values[cache_key] = scaled_value
                                            break
                        except Exception as e:
                            logger.error(f"Error updating device {dev_id}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in update loop: {e}")
                await asyncio.sleep(1.0)

import logging
import os
from typing import List, Optional
from core.config_manager import ConfigManager
from core.device_manager import DeviceManager
from core.channel_manager import ChannelManager
from core.test_engine import TestEngine
from core.stream_manager import StreamManager
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
        self.channel_manager = ChannelManager(self.device_manager, self.stream_manager)
        self.test_engine = TestEngine(self.channel_manager)
        
        # Redirect all standard logging to the SSE stream
        from core.stream_manager import SSELogHandler
        sse_handler = SSELogHandler(self.stream_manager)
        # Simple format: Module: Message
        sse_handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
        logging.getLogger().addHandler(sse_handler)
        
        # Connect test engine results to log stream
        self.test_engine.on_step_complete = self._handle_test_step_result
        
        self.initialized = True
        logger.info("SDTB System Initialized")

    def startup(self):
        """
        Performs the system startup sequence: discovery and channel mapping.
        """
        logger.info("Starting up SDTB System...")
        
        # 1. Discover and initialize devices
        self.device_manager.discover_and_initialize()
        
        # 2. Load and initialize channels
        try:
            from pydantic import TypeAdapter
            import json
            
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

    def shutdown(self):
        """
        Performs system shutdown: disconnects devices.
        """
        logger.info("Shutting down SDTB System...")
        self.device_manager.disconnect_all()

    def restart(self):
        """
        Restarts the system: disconnects, re-initializes, and re-discovers.
        """
        logger.info("Restarting SDTB System...")
        self.shutdown()
        self.initialized = False
        self.__init__(self.config_dir)
        self.startup()

    def _handle_test_step_result(self, result):
        """
        Callback from TestEngine. Pushes result to log stream.
        """
        log_msg = f"Step {result.step_index} [{result.action}]: {result.status} - {result.message}"
        self.stream_manager.push_log(log_msg)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChannelProperties(BaseModel):
    unit: str
    min: float
    max: float
    resolution: float
    offset: float
    value: float = 0.0

class ChannelConfig(BaseModel):
    channel_id: str
    device_id: str
    signal_id: str
    properties: ChannelProperties

class SystemServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000

class SystemConfig(BaseModel):
    device_directory: str = "devices"
    device_update_rate: int = Field(default=100, ge=10, le=5000)
    server: SystemServerConfig = Field(default_factory=SystemServerConfig)

class DeviceConfig(BaseModel):
    id: str
    plugin: str
    enabled: bool = True
    connection_params: Dict[str, Any]
    settings: Dict[str, Any] = {}

class WidgetPosition(BaseModel):
    row: int
    col: int

class WidgetConfig(BaseModel):
    id: str
    type: str
    channel: str
    label: str
    position: WidgetPosition
    min: Optional[float] = None
    max: Optional[float] = None

class UIConfig(BaseModel):
    layout: str = "dashboard"
    widgets: List[WidgetConfig] = []

class FlashConfig(BaseModel):
    id: str
    plugin: str
    enabled: bool = True
    connection_params: Dict[str, Any]
    settings: Dict[str, Any] = {}

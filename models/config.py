from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Literal, Union, Annotated

class BaseConversion(BaseModel):
    type: str

class LinearConversion(BaseConversion):
    type: Literal["linear"] = "linear"
    resolution: float
    offset: float

class PolynomialConversion(BaseConversion):
    type: Literal["polynomial"] = "polynomial"
    coefficients: List[float]

class LutConversion(BaseConversion):
    type: Literal["lut"] = "lut"
    table: List[List[float]]

ConversionStrategy = Annotated[
    Union[LinearConversion, PolynomialConversion, LutConversion],
    Field(discriminator="type")
]

class ChannelProperties(BaseModel):
    """
    Physical scaling and range properties for a logical channel.

    ``signal_type`` is optional. When supplied, it must match a key in
    ``config/signal_types.json`` and is used for startup validation of the
    channel's min/max/unit against the registry.
    """
    signal_type: Optional[str] = None  # e.g. "engine_speed", "pwm_duty"
    unit: str
    min: float
    max: float
    conversion: ConversionStrategy = Field(
        default_factory=lambda: LinearConversion(resolution=1.0, offset=0.0)
    )
    value: float = 0.0

    # Legacy fields excluded from serialization
    resolution: Optional[float] = Field(default=None, exclude=True)
    offset: Optional[float] = Field(default=None, exclude=True)

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_conversion(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If conversion is missing but legacy resolution/offset are present
            if "conversion" not in data and "resolution" in data and "offset" in data:
                data["conversion"] = {
                    "type": "linear",
                    "resolution": data.pop("resolution"),
                    "offset": data.pop("offset")
                }
        return data

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

class CANFrameResponse(BaseModel):
    timestamp: float
    bus: str
    arbitration_id: str  # Hex string like "0x100"
    dlc: int
    data: str           # Hex string
    is_extended: bool
    is_error: bool
    is_remote: bool

class CANInterfaceInfo(BaseModel):
    device_id: str
    bus: str
    buffer_size: int
    frame_count: int

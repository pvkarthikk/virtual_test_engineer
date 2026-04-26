import sys
import os

# Add source directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.config import SystemConfig, ChannelConfig, ChannelProperties
from core.config_manager import ConfigManager
import json

def test_pydantic_models():
    print("Testing Pydantic Models...")
    sys_json = '{"device_directory": "C:/devices", "server": {"host": "127.0.0.1", "port": 8080}}'
    config = SystemConfig.model_validate_json(sys_json)
    assert config.device_directory == "C:/devices"
    assert config.server.port == 8080
    print("SystemConfig OK")

    ch_json = '{"channel_id": "ch1", "device_id": "dev1", "signal_id": "sig1", "properties": {"unit": "V", "min": 0, "max": 5, "resolution": 0.001, "offset": 0}}'
    config = ChannelConfig.model_validate_json(ch_json)
    assert config.channel_id == "ch1"
    assert config.properties.unit == "V"
    print("ChannelConfig OK")

def test_config_manager():
    print("\nTesting Config Manager...")
    cm = ConfigManager("temp_config")
    sys_cfg = SystemConfig(device_directory="C:/test", server={"host": "0.0.0.0", "port": 8000})
    
    # Test Save
    cm.save_config("system", sys_cfg)
    assert os.path.exists("temp_config/system.json")
    
    # Test Load
    loaded = cm.load_config("system", SystemConfig)
    assert loaded.device_directory == "C:/test"
    
    # Test Backup
    with open("temp_config/system.json", "w") as f:
        f.write("modified content")
    
    sys_cfg.device_directory = "C:/updated"
    cm.save_config("system", sys_cfg)
    assert os.path.exists("temp_config/system.json.bak")
    with open("temp_config/system.json.bak", "r") as f:
        assert "modified content" in f.read()
    
    print("ConfigManager OK")

if __name__ == "__main__":
    try:
        test_pydantic_models()
        test_config_manager()
        print("\nAll basic tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        import shutil
        if os.path.exists("temp_config"):
            shutil.rmtree("temp_config")

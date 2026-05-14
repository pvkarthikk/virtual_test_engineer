import os
import json
import uuid
import logging
from typing import List, Optional
from models.test import TestScript, TestScriptMetadata, TestStep

logger = logging.getLogger(__name__)

class ScriptManager:
    def __init__(self, scripts_dir: str):
        self.scripts_dir = scripts_dir
        if not os.path.exists(self.scripts_dir):
            os.makedirs(self.scripts_dir)
            logger.info(f"Created scripts directory: {self.scripts_dir}")

    def _get_file_path(self, script_id: str) -> str:
        return os.path.join(self.scripts_dir, f"{script_id}.json")

    def save_script(self, description: str, steps: List[TestStep]) -> str:
        """
        Saves a test script and returns its unique ID.
        """
        script_id = str(uuid.uuid4())
        script = TestScript(id=script_id, description=description, steps=steps)
        
        file_path = self._get_file_path(script_id)
        with open(file_path, "w") as f:
            f.write(script.model_dump_json(indent=2))
        
        logger.info(f"Saved test script {script_id}: {description}")
        return script_id

    def list_scripts(self) -> List[TestScriptMetadata]:
        """
        Lists all saved test scripts.
        """
        scripts = []
        for filename in os.listdir(self.scripts_dir):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.scripts_dir, filename)
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        scripts.append(TestScriptMetadata(id=data["id"], description=data["description"]))
                except Exception as e:
                    logger.error(f"Failed to load script metadata from {filename}: {e}")
        return scripts

    def get_script(self, script_id: str) -> Optional[TestScript]:
        """
        Retrieves a specific test script by ID.
        """
        file_path = self._get_file_path(script_id)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return TestScript.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load script {script_id}: {e}")
            return None

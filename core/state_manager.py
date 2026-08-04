import os
import json
import time
import shutil

class State_Manager:
    def __init__(self, workspace_dir: str):
        if not workspace_dir:
            raise ValueError("[State_Manager] CRITICAL: workspace_dir cannot be empty.")
        if not os.path.isdir(workspace_dir):
            raise ValueError(f"[State_Manager] CRITICAL: Directory does not exist -> {workspace_dir}")
        
        self.workspace_dir = workspace_dir
        self.state_file_path = os.path.join(self.workspace_dir, "project_state.json")
        self.tmp_file_path = os.path.join(self.workspace_dir, "project_state.tmp")
        self.backup_file_path = os.path.join(self.workspace_dir, "project_state.backup")
        self.lock_file_path = os.path.join(self.workspace_dir, "project_state.lock")

    def _acquire_lock(self, timeout: int = 10) -> bool:
        start_time = time.time()
        while True:
            if not os.path.exists(self.lock_file_path):
                with open(self.lock_file_path, 'w') as f:
                    f.write("LOCKED")
                return True
            if time.time() - start_time > timeout:
                raise TimeoutError("[State_Manager] CRITICAL: Lock acquisition timeout. Another agent holds the state.")
            time.sleep(0.1)

    def _release_lock(self):
        if os.path.exists(self.lock_file_path):
            os.remove(self.lock_file_path)

    def load_state(self) -> dict:
        if not os.path.exists(self.state_file_path):
            if os.path.exists(self.backup_file_path):
                print("[State_Manager] Main state missing. Auto-recovering from backup...", flush=True)
                shutil.copy2(self.backup_file_path, self.state_file_path)
            else:
                return {"schema_version": "3.0"}
        
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            if os.path.exists(self.backup_file_path):
                print("[State_Manager] FATAL: State corrupted. Auto-recovering from backup...", flush=True)
                shutil.copy2(self.backup_file_path, self.state_file_path)
                with open(self.state_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            raise RuntimeError(f"[State_Manager] FATAL: State file is corrupted and no backup exists -> {self.state_file_path}")

    def validate_schema(self, data: dict, required_keys: list = None) -> bool:
        if not isinstance(data, dict):
            return False
        if required_keys:
            for key in required_keys:
                if key not in data:
                    print(f"[State_Manager] Validation Warning: Missing key '{key}'", flush=True)
                    return False
                if data[key] in ["", [], {}]:
                    print(f"[State_Manager] Validation Warning: Key '{key}' is empty.", flush=True)
                    return False
        return True

    def save_state(self, state_data: dict, required_keys: list = None) -> bool:
        if not self.validate_schema(state_data, required_keys):
            raise ValueError("[State_Manager] Schema validation failed. Atomic save aborted to prevent corruption.")

        state_data["schema_version"] = "3.0"

        self._acquire_lock()
        try:
            with open(self.tmp_file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4)
            
            os.replace(self.tmp_file_path, self.state_file_path)
            shutil.copy2(self.state_file_path, self.backup_file_path)
            return True
        except Exception as e:
            if os.path.exists(self.tmp_file_path):
                os.remove(self.tmp_file_path)
            raise RuntimeError(f"[State_Manager] Atomic save failed: {str(e)}")
        finally:
            self._release_lock()

import os
import secrets
from datetime import datetime
from core.state_manager import State_Manager

class Agent_00_Workspace_Initializer:
    def __init__(self):
        self.agent_name = "Agent_00_Workspace_Initializer"

    def _generate_project_id(self) -> str:
        """Pure Procedural Mathematical ID Generation (No LLM)."""
        date_str = datetime.now().strftime('%Y%m%d')
        random_hex = secrets.token_hex(4).upper()
        return f"Project_{date_str}_{random_hex}"

    def execute(self, state: dict) -> dict:
        print(f"[{self.agent_name}] INFO: Initializing OmniMatrix Environment (Procedural Mode)...", flush=True)

        # 1. Project ID Generation (Non-AI)
        project_id = state.get("project_id")
        if not project_id:
            project_id = self._generate_project_id()
            state["project_id"] = project_id
            
        state["schema_version"] = "3.0"

        # 2. Complete Path Calculations
        base_workspace = state.get("paths", {}).get("workspace_root", "OmniMatrix_Workspace")
        project_dir = os.path.join(base_workspace, "projects", project_id)

        directories = {
            "workspace_dir": project_dir,
            "outputs_dir": os.path.join(project_dir, "outputs"),
            "logs_dir": os.path.join(project_dir, "logs"),
            "temp_dir": os.path.join(project_dir, "temp"),
            "backups_dir": os.path.join(project_dir, "backups"),
            "prompts_dir": state.get("paths", {}).get("prompts_dir", "prompts")
        }

        # 3. Dynamic Workspace Creation
        for key, path in directories.items():
            if path:
                os.makedirs(path, exist_ok=True)

        state["paths"] = directories
        state["workspace_dir"] = project_dir

        # 4. State Initialization (Skeleton)
        state.setdefault("user_prompt", "")
        state.setdefault("runtime_data", {})
        state.setdefault("metrics", {})

        # 5. Global Configuration Setup
        global_config = state.setdefault("global_config", {})
        global_config.setdefault("medium", "Dynamic/Unbound")
        global_config.setdefault("rendering_engine", "Dynamic/Unbound")
        global_config.setdefault("color_lighting", "Dynamic/Unbound")
        global_config.setdefault("kinetic_framing", "Dynamic/Unbound")
        global_config.setdefault("target_duration_sec", 60)
        global_config.setdefault("resolution", "1080x1920")
        global_config.setdefault("fps", 30)

        # 6. Control Handoff to Orchestrator
        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status["next_agent"] = "Ai_Agent_65_Supreme_Creative_Script_Conductor"
        pipeline_status[self.agent_name] = "COMPLETED"

        # 7. First Atomic Save via State Manager
        sm = State_Manager(project_dir)
        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Workspace Locked! ID: {project_id}. Routing matrix to Agent 65.", flush=True)

        return state

import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_03_Visual_Sync_Storyboarder:
    def __init__(self):
        self.agent_name = "Ai_Agent_03_Visual_Sync_Storyboarder"
        self.required_panel_keys = [
            "scene_id",
            "frame_composition",
            "subject_action",
            "micro_camera_cuts",
            "lighting_atmosphere",
            "vfx_assets_needed"
        ]

    def _validate_storyboard_deep(self, storyboard_panels: list, expected_scene_count: int) -> bool:
        if not isinstance(storyboard_panels, list):
            print(f"[{self.agent_name}] Validation Failed: Output is not a list.", flush=True)
            return False
            
        if len(storyboard_panels) != expected_scene_count:
            print(f"[{self.agent_name}] Validation Failed: Length mismatch. Expected {expected_scene_count} panels, got {len(storyboard_panels)}.", flush=True)
            return False

        for panel in storyboard_panels:
            if not isinstance(panel, dict):
                return False
            for key in self.required_panel_keys:
                if key not in panel:
                    print(f"[{self.agent_name}] Validation Failed: Missing key '{key}' in panel.", flush=True)
                    return False
                
                val = panel[key]
                if key == "micro_camera_cuts":
                    if not isinstance(val, list) or len(val) == 0:
                        print(f"[{self.agent_name}] Validation Failed: 'micro_camera_cuts' must be a non-empty list.", flush=True)
                        return False
                    for cut in val:
                        if not isinstance(cut, str) or len(cut.strip()) == 0:
                            return False
                else:
                    if isinstance(val, str) and len(val.strip()) == 0:
                        print(f"[{self.agent_name}] Validation Failed: Key '{key}' has an empty string.", flush=True)
                        return False
        return True

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
             print(f"[{self.agent_name}] Warning: State schema version '{schema_version}' may not be fully compatible.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        if "agent_03_storyboard" in module_scripting:
            del module_scripting["agent_03_storyboard"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        script_scenes = module_scripting.get("agent_02_script", [])
        if not script_scenes or len(script_scenes) == 0:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing 'agent_02_script'. Agent 02 must run first.")

        expected_scene_count = len(script_scenes)
        script_json = json.dumps(script_scenes, indent=2)

        core_topic = runtime_data.get("core_topic", state.get("user_prompt", ""))
        global_config = state.get("global_config", {})
        medium = global_config.get("medium", "Dynamic/Unbound")
        rendering_engine = global_config.get("rendering_engine", "Dynamic/Unbound")
        color_lighting = global_config.get("color_lighting", "Dynamic/Unbound")
        kinetic_framing = global_config.get("kinetic_framing", "Dynamic/Unbound")
        master_theme = runtime_data.get("master_theme_blueprint", f"{medium} - {rendering_engine}")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "core_topic": core_topic,
            "master_theme": master_theme,
            "medium": medium,
            "rendering_engine": rendering_engine,
            "color_lighting": color_lighting,
            "kinetic_framing": kinetic_framing,
            "script_json": script_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_03_storyboard.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Visual Sync Storyboarder. Generate raw structured JSON only.",
            temperature=0.7,
            required_keys=["agent_03_storyboard"],
            project_id=project_id
        )

        storyboard_panels = response["data"]["agent_03_storyboard"]
        
        if not self._validate_storyboard_deep(storyboard_panels, expected_scene_count):
            raise ValueError(f"[{self.agent_name}] [AG003] Deep Schema Validation Failed. Panel count or structure mismatch.")

        module_scripting["agent_03_storyboard"] = storyboard_panels
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] INFO: Executed successfully! Mapped {len(storyboard_panels)} storyboard panels to script scenes. (Time: {exec_time}s via {provider})", flush=True)

        return state

import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_02_Core_Script_Engine:
    def __init__(self):
        self.agent_name = "Ai_Agent_02_Core_Script_Engine"
        self.required_scene_keys = [
            "scene_id",
            "narration_text",
            "visual_directive",
            "audio_foley_directive",
            "pacing_tempo",
            "estimated_duration_sec",
            "required_assets"
        ]
        self.asset_sub_keys = [
            "asset_priority",
            "characters",
            "voice_speaker",
            "props",
            "environment",
            "animals_creatures",
            "vehicles",
            "fx_requirements"
        ]

    def _validate_script_deep(self, script_scenes: list) -> bool:
        if not isinstance(script_scenes, list) or len(script_scenes) == 0:
            return False

        for scene in script_scenes:
            if not isinstance(scene, dict):
                return False
            for key in self.required_scene_keys:
                if key not in scene:
                    print(f"[{self.agent_name}] Validation Failed: Missing key '{key}'.", flush=True)
                    return False
                val = scene[key]
                
                if isinstance(val, str) and len(val.strip()) == 0:
                    return False
                
                if key == "estimated_duration_sec":
                    if not isinstance(val, (int, float)) or val <= 0 or val > 60:
                        print(f"[{self.agent_name}] Validation Failed: Duration {val}s is out of bounds (0-60s).", flush=True)
                        return False

                if key == "required_assets":
                    if not isinstance(val, dict):
                        print(f"[{self.agent_name}] Validation Failed: 'required_assets' must be a dictionary.", flush=True)
                        return False
                    
                    for sub_key in self.asset_sub_keys:
                        if sub_key not in val:
                            print(f"[{self.agent_name}] Validation Failed: Missing '{sub_key}' in required_assets.", flush=True)
                            return False
                    
                    if val.get("asset_priority") not in ["Critical", "Important", "Optional"]:
                        print(f"[{self.agent_name}] Validation Failed: Invalid asset_priority '{val.get('asset_priority')}'.", flush=True)
                        return False

                    chars = val.get("characters", [])
                    if not isinstance(chars, list):
                        print(f"[{self.agent_name}] Validation Failed: 'characters' must be a list.", flush=True)
                        return False
                    
                    for char in chars:
                        if not isinstance(char, dict):
                            return False
                        char_keys = ["name", "gender", "age", "outfit"]
                        if not all(k in char for k in char_keys):
                            print(f"[{self.agent_name}] Validation Failed: Character dict missing required detailed keys (name, gender, age, outfit).", flush=True)
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

        if "agent_02_script" in module_scripting:
            del module_scripting["agent_02_script"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        hooks = module_scripting.get("agent_01_hooks", [])
        selected_index = module_scripting.get("selected_hook_index", 0)

        if not hooks or selected_index >= len(hooks) or selected_index < 0:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Invalid hook index ({selected_index}) or hooks array is empty.")

        selected_hook = hooks[selected_index]
        selected_hook_json = json.dumps(selected_hook)

        core_topic = runtime_data.get("core_topic", state.get("user_prompt", ""))
        if not core_topic:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'core_topic' missing in state.")

        global_config = state.get("global_config", {})
        medium = global_config.get("medium", "Dynamic/Unbound")
        rendering_engine = global_config.get("rendering_engine", "Dynamic/Unbound")
        color_lighting = global_config.get("color_lighting", "Dynamic/Unbound")
        kinetic_framing = global_config.get("kinetic_framing", "Dynamic/Unbound")
        
        target_duration_sec = global_config.get("target_duration_sec", 30)
        
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
            "target_duration_sec": target_duration_sec,
            "selected_hook_json": selected_hook_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_02_script.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Core Script Engine. Generate raw structured JSON.",
            temperature=0.7,
            required_keys=["agent_02_script"],
            project_id=project_id
        )

        script_scenes = response["data"]["agent_02_script"]
        if not self._validate_script_deep(script_scenes):
            raise ValueError(f"[{self.agent_name}] [AG003] Deep Schema Validation Failed for scene directives.")

        module_scripting["agent_02_script"] = script_scenes
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] INFO: Executed successfully! Generated {len(script_scenes)} scenes. (Time: {exec_time}s via {provider})", flush=True)

        return state

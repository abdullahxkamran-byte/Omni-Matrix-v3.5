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
            "estimated_duration_sec"
        ]

    def _validate_script_deep(self, script_scenes: list) -> bool:
        """Validates nested structure including 'None' handling and strict duration limits."""
        if not isinstance(script_scenes, list) or len(script_scenes) == 0:
            return False

        for scene in script_scenes:
            if not isinstance(scene, dict):
                return False
            for key in self.required_scene_keys:
                if key not in scene:
                    return False
                val = scene[key]
                
                # Check for empty strings
                if isinstance(val, str) and len(val.strip()) == 0:
                    return False
                
                # ChatGPT FIX 2: Strict Duration Limit (Max 60 seconds per scene)
                if key == "estimated_duration_sec":
                    if not isinstance(val, (int, float)) or val <= 0 or val > 60:
                        print(f"[{self.agent_name}] Validation Failed: Duration {val}s is out of bounds (0-60s).", flush=True)
                        return False
        return True

    def execute(self, state: dict) -> dict:
        # ChatGPT FIX 3: State Schema Version Check
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
             print(f"[{self.agent_name}] Warning: State schema version '{schema_version}' may not be fully compatible.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        # Idempotency Scrubbing
        if "agent_02_script" in module_scripting:
            del module_scripting["agent_02_script"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        hooks = module_scripting.get("agent_01_hooks", [])
        selected_index = module_scripting.get("selected_hook_index", 0)

        # ChatGPT FIX 1: Negative Index Protection
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
        master_theme = runtime_data.get("master_theme_blueprint", f"{medium} - {rendering_engine}")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        # Load Prompt
        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "core_topic": core_topic,
            "master_theme": master_theme,
            "medium": medium,
            "rendering_engine": rendering_engine,
            "color_lighting": color_lighting,
            "kinetic_framing": kinetic_framing,
            "selected_hook_json": selected_hook_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_02_script.txt", variables)

        # AI Generation
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

        # Update State
        module_scripting["agent_02_script"] = script_scenes
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        # Atomic Safe Save
        sm.save_state(state)

        # ChatGPT FIX 4: Ready for Logger transition
        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] INFO: Executed successfully! Generated {len(script_scenes)} scenes. (Time: {exec_time}s via {provider})", flush=True)

        return state

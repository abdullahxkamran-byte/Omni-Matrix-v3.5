import json
import re
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_07_Vibe_Enhancer:
    def __init__(self):
        self.agent_name = "Ai_Agent_07_Vibe_Enhancer"
        self.required_keys = [
            "global_aesthetic_keywords",
            "primary_color_hex",
            "secondary_color_hex",
            "target_bpm_range",
            "musical_genre_directive",
            "vibe_shift_timestamp_percent"
        ]

    def _validate_hex(self, hex_string: str) -> bool:
        if not isinstance(hex_string, str):
            return False
        return bool(re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", hex_string))

    def _validate_vibe_deep(self, vibe_data: dict) -> bool:
        if not isinstance(vibe_data, dict):
            return False

        for key in self.required_keys:
            if key not in vibe_data:
                print(f"[{self.agent_name}] Validation Failed: Missing key '{key}'.", flush=True)
                return False

            val = vibe_data[key]

            if key == "global_aesthetic_keywords":
                if not isinstance(val, list) or len(val) != 3:
                    return False
                for kw in val:
                    if not isinstance(kw, str) or len(kw.strip()) == 0:
                        return False

            if key in ["primary_color_hex", "secondary_color_hex"]:
                if not self._validate_hex(val):
                    print(f"[{self.agent_name}] Validation Failed: Invalid HEX format '{val}'.", flush=True)
                    return False

            if key == "vibe_shift_timestamp_percent":
                if not isinstance(val, int) or val < 0 or val > 100:
                    print(f"[{self.agent_name}] Validation Failed: Percentage '{val}' out of 0-100 bounds.", flush=True)
                    return False

        return True

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
            print(f"[{self.agent_name}] Warning: Schema mismatch.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        if "agent_07_vibe" in module_scripting:
            del module_scripting["agent_07_vibe"]

        tension_data = module_scripting.get("agent_04_tension_analysis", [])
        arc_data = module_scripting.get("agent_05_story_arc", {})

        if not tension_data or not arc_data:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Tension or Story Arc dependencies.")

        core_topic = runtime_data.get("core_topic", state.get("user_prompt", ""))
        global_config = state.get("global_config", {})
        medium = global_config.get("medium", "Dynamic/Unbound")
        rendering_engine = global_config.get("rendering_engine", "Dynamic/Unbound")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        tension_json = json.dumps(tension_data, indent=2)
        arc_json = json.dumps(arc_data, indent=2)

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "core_topic": core_topic,
            "medium": medium,
            "rendering_engine": rendering_engine,
            "tension_json": tension_json,
            "arc_json": arc_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_07_vibe.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Vibe & Aesthetic Enhancer. Output strictly valid JSON.",
            temperature=0.6,
            required_keys=["agent_07_vibe"],
            project_id=project_id
        )

        vibe_data = response["data"]["agent_07_vibe"]
        
        if not self._validate_vibe_deep(vibe_data):
            raise ValueError(f"[{self.agent_name}] [AG003] Validation Failed: HEX code, BPM, or percentage corruption detected.")

        module_scripting["agent_07_vibe"] = vibe_data
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] INFO: Vibe locked! Primary Color: {vibe_data['primary_color_hex']} | BPM Target: {vibe_data['target_bpm_range']} (Time: {exec_time}s via {provider})", flush=True)

        return state

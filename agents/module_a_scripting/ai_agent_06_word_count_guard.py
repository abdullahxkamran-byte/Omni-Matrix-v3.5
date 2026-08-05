import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_06_Word_Count_Guard:
    def __init__(self):
        self.agent_name = "Ai_Agent_06_Word_Count_Guard"
        self.required_guard_keys = [
            "scene_id",
            "original_duration_sec",
            "phonetic_narration_text",
            "calculated_word_count",
            "speech_rate_wpm",
            "status_flag"
        ]

    def _validate_guard_deep(self, guard_data: list, expected_scene_count: int) -> bool:
        if not isinstance(guard_data, list):
            return False
            
        if len(guard_data) != expected_scene_count:
            print(f"[{self.agent_name}] Validation Failed: Expected {expected_scene_count} blocks, got {len(guard_data)}.", flush=True)
            return False

        for block in guard_data:
            if not isinstance(block, dict):
                return False
            for key in self.required_guard_keys:
                if key not in block:
                    return False
                
                val = block[key]
                
                if key == "phonetic_narration_text":
                    if isinstance(val, str) and "$" in val or "%" in val:
                        print(f"[{self.agent_name}] Validation Failed: Unpronounceable symbols ($ or %) found in text.", flush=True)
                        return False
                        
                if key == "speech_rate_wpm":
                    if not isinstance(val, (int, float)):
                        return False
                    if val > 220:
                        print(f"[{self.agent_name}] Validation Failed: WPM {val} is impossibly fast for TTS.", flush=True)
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

        if "agent_06_word_guard" in module_scripting:
            del module_scripting["agent_06_word_guard"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        script_scenes = module_scripting.get("agent_02_script", [])
        if not script_scenes:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 02 Script.")

        expected_scene_count = len(script_scenes)
        script_json = json.dumps(script_scenes, indent=2)
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "script_json": script_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_06_word_guard.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Word Count & Phonetic Guard. Generate strict JSON.",
            temperature=0.2, 
            required_keys=["agent_06_word_guard"],
            project_id=project_id
        )

        guard_data = response["data"]["agent_06_word_guard"]
        
        if not self._validate_guard_deep(guard_data, expected_scene_count):
            raise ValueError(f"[{self.agent_name}] [AG003] Validation Failed: Pronunciation/WPM math limit breached.")

        module_scripting["agent_06_word_guard"] = guard_data
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] INFO: Executed! Audited {len(guard_data)} scenes for TTS safety. (Time: {exec_time}s via {provider})", flush=True)

        return state

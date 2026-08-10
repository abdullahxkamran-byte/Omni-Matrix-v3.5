import time
import json
import hashlib
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_18_Adaptive_BGM_Vibe_Matcher:
    def __init__(self):
        self.agent_name = "Ai_Agent_18_Adaptive_BGM_Vibe_Matcher"
        self.required_root_keys = [
            "global_musical_properties",
            "leitmotifs",
            "bgm_cues",
            "agent_18b_generative_prompt"
        ]
        self.required_cue_keys = [
            "cue_id",
            "start_sec",
            "end_sec",
            "active_stems",
            "intensity_level",
            "transition_in",
            "transition_out"
        ]

    def _generate_state_hash(self, vibe: dict, tension: list, timeline: dict) -> str:
        """Deterministic hashing for Caching & Idempotency."""
        raw_string = f"{json.dumps(vibe, sort_keys=True)}|{json.dumps(tension, sort_keys=True)}|{json.dumps(timeline, sort_keys=True)}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16]

    def _validate_blueprint_deep(self, blueprint: dict) -> bool:
        if not isinstance(blueprint, dict):
            return False

        for key in self.required_root_keys:
            if key not in blueprint:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        cues = blueprint.get("bgm_cues", [])
        if not isinstance(cues, list) or len(cues) == 0:
            print(f"[{self.agent_name}] Validation Failed: BGM cues list is empty or invalid.", flush=True)
            return False

        for cue in cues:
            for ck in self.required_cue_keys:
                if ck not in cue:
                    print(f"[{self.agent_name}] Validation Failed: Missing cue key '{ck}'.", flush=True)
                    return False

            start_sec = cue.get("start_sec", -1.0)
            end_sec = cue.get("end_sec", -1.0)

            if not isinstance(start_sec, (int, float)) or start_sec < 0:
                print(f"[{self.agent_name}] Validation Failed: Invalid negative start timestamp.", flush=True)
                return False
                
            if not isinstance(end_sec, (int, float)) or end_sec <= start_sec:
                print(f"[{self.agent_name}] Validation Failed: Impossible cue duration (end <= start).", flush=True)
                return False
                
            stems = cue.get("active_stems", [])
            if not isinstance(stems, list):
                print(f"[{self.agent_name}] Validation Failed: 'active_stems' must be a list of strings.", flush=True)
                return False

        return True

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        
        module_scripting = runtime_data.get("module_a_scripting", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # Fetch Dependencies
        vibe_data = module_scripting.get("agent_07_vibe", {})
        tension_data = module_scripting.get("agent_04_tension_analysis", [])
        global_timestamps = module_audio.get("agent_12_global_timestamps", {})

        if not global_timestamps or not vibe_data or not tension_data:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Vibe, Tension, or Global Timestamps.")

        # Caching & Idempotency Check
        current_hash = self._generate_state_hash(vibe_data, tension_data, global_timestamps)
        existing_blueprint = module_audio.get("agent_18_bgm_blueprint", {})
        
        if existing_blueprint and existing_blueprint.get("_blueprint_hash") == current_hash:
            print(f"[{self.agent_name}] INFO: Deterministic cache hit. Skipping re-analysis.", flush=True)
            return state

        if "agent_18_bgm_blueprint" in module_audio:
            del module_audio["agent_18_bgm_blueprint"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "vibe_json": json.dumps(vibe_data, indent=2),
            "tension_json": json.dumps(tension_data, indent=2),
            "timeline_json": json.dumps(global_timestamps, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_18_adaptive_bgm.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Adaptive BGM Architect. Strict adherence to agent boundaries. Output valid JSON only.",
            temperature=0.6,  # Balanced for creativity in leitmotifs and logic in timestamps
            required_keys=["agent_18_bgm_blueprint"],
            project_id=project_id
        )

        blueprint = response["data"]["agent_18_bgm_blueprint"]
        
        if not self._validate_blueprint_deep(blueprint):
            raise ValueError(f"[{self.agent_name}] [LLM003] Validation Failed: BGM Blueprint schema or timeline logic is corrupt.")

        # Lock Hash for future Caching
        blueprint["_blueprint_hash"] = current_hash

        module_audio["agent_18_bgm_blueprint"] = blueprint
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        total_cues = len(blueprint.get("bgm_cues", []))
        master_key = blueprint.get("global_musical_properties", {}).get("master_key", "Unknown")
        
        print(f"[{self.agent_name}] INFO: Musical Orchestration Locked! Key: {master_key}. Designed {total_cues} stems/cues. Generative prompt ready for Agent 18B. (Time: {exec_time}s via {provider})", flush=True)

        return state

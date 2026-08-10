import json
import hashlib
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_15_Low_Frequency_Impact_Sub_Designer:
    def __init__(self):
        self.agent_name = "Ai_Agent_15_Low_Frequency_Impact_Sub_Designer"
        self.required_root_keys = [
            "global_low_end_policy",
            "impact_designs"
        ]
        self.required_impact_keys = [
            "impact_id",
            "timestamp_sec",
            "duration_sec",
            "layering_blueprint",
            "pitch_drop_intent",
            "adsr_profile",
            "dialogue_protection_flag",
            "handoff_agent_16_sidechain",
            "handoff_agent_17_sfx",
            "handoff_agent_19_mastering",
            "confidence"
        ]

    def _generate_state_hash(self, beat_map: dict, timeline: dict) -> str:
        """Deterministic hashing for Caching & Idempotency."""
        raw_string = f"{json.dumps(beat_map, sort_keys=True)}|{json.dumps(timeline, sort_keys=True)}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16]

    def _validate_blueprint_deep(self, blueprint: dict) -> bool:
        if not isinstance(blueprint, dict):
            return False

        for key in self.required_root_keys:
            if key not in blueprint:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        impacts = blueprint.get("impact_designs", [])
        if not isinstance(impacts, list):
            return False

        for impact in impacts:
            for ik in self.required_impact_keys:
                if ik not in impact:
                    print(f"[{self.agent_name}] Validation Failed: Missing impact key '{ik}'.", flush=True)
                    return False

            # Timeline Safety Checks
            start_sec = impact.get("timestamp_sec", -1)
            duration = impact.get("duration_sec", -1)

            if not isinstance(start_sec, (int, float)) or start_sec < 0:
                print(f"[{self.agent_name}] Validation Failed: Invalid negative timestamp '{start_sec}'.", flush=True)
                return False
                
            if not isinstance(duration, (int, float)) or duration <= 0:
                print(f"[{self.agent_name}] Validation Failed: Impossible duration '{duration}'.", flush=True)
                return False

            confidence = impact.get("confidence", "").lower()
            if confidence not in ["high", "medium", "low"]:
                print(f"[{self.agent_name}] Validation Failed: Invalid confidence score '{confidence}'.", flush=True)
                return False

        return True

    def execute(self, state: dict) -> dict:
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        
        module_scripting = runtime_data.get("module_a_scripting", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        beat_drop_map = module_audio.get("agent_14_beat_drop_map", {})
        global_timestamps = module_audio.get("agent_12_global_timestamps", {})
        vibe_data = module_scripting.get("agent_07_vibe", {})

        if not beat_drop_map or not global_timestamps:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 14 Beat Map or Agent 12 Timeline.")

        # Caching & Idempotency Check
        current_hash = self._generate_state_hash(beat_drop_map, global_timestamps)
        existing_blueprint = module_audio.get("agent_15_sub_impact_blueprint", {})
        
        if existing_blueprint and existing_blueprint.get("_blueprint_hash") == current_hash:
            print(f"[{self.agent_name}] INFO: Deterministic cache hit. Skipping re-analysis.", flush=True)
            return state

        if "agent_15_sub_impact_blueprint" in module_audio:
            del module_audio["agent_15_sub_impact_blueprint"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "beat_drop_json": json.dumps(beat_drop_map, indent=2),
            "timeline_json": json.dumps(global_timestamps, indent=2),
            "vibe_json": json.dumps(vibe_data, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_15_sub_designer.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Low-Frequency Sub Designer. Adhere strictly to handoff boundaries and timeline safety. Output valid JSON only.",
            temperature=0.4, # Keep it strictly logical and mathematical
            required_keys=["agent_15_sub_impact_blueprint"],
            project_id=project_id
        )

        blueprint = response["data"]["agent_15_sub_impact_blueprint"]
        
        if not self._validate_blueprint_deep(blueprint):
            raise ValueError(f"[{self.agent_name}] [LLM003] Validation Failed: Corrupted DSP Blueprint or unsafe timelines detected.")

        # Lock Hash for future Caching
        blueprint["_blueprint_hash"] = current_hash

        module_audio["agent_15_sub_impact_blueprint"] = blueprint
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        total_impacts = len(blueprint.get("impact_designs", []))
        
        print(f"[{self.agent_name}] INFO: Sub-Bass Blueprint locked! Orchestrated {total_impacts} impact points. Handoff prepared for Agents 16, 17 & 19. (Time: {exec_time}s via {provider})", flush=True)

        return state

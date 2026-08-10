import json
import hashlib
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_14_Phonk_Beat_Drop_Analyzer:
    def __init__(self):
        self.agent_name = "Ai_Agent_14_Phonk_Beat_Drop_Analyzer"
        self.required_root_keys = [
            "global_track_metadata",
            "energy_curve_map",
            "drop_hierarchy_and_candidates",
            "impact_opportunity_map",
            "scene_synchronization",
            "analysis_health_report"
        ]

    def _generate_state_hash(self, vibe_data: dict, timeline_data: dict) -> str:
        """Generates a deterministic hash to prevent unnecessary re-analysis (Caching Protocol)."""
        raw_string = f"{json.dumps(vibe_data, sort_keys=True)}|{json.dumps(timeline_data, sort_keys=True)}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16]

    def _validate_beat_map_deep(self, beat_map: dict) -> bool:
        if not isinstance(beat_map, dict):
            return False

        for key in self.required_root_keys:
            if key not in beat_map:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        drops = beat_map.get("drop_hierarchy_and_candidates", [])
        if not isinstance(drops, list):
            return False
            
        valid_drop_types = ["PRIMARY_DROP", "SECONDARY_DROP", "MINOR_IMPACT", "TRANSITION_HIT", "FILL"]
        for drop in drops:
            if drop.get("drop_type") not in valid_drop_types:
                print(f"[{self.agent_name}] Validation Failed: Invalid drop_type '{drop.get('drop_type')}'.", flush=True)
                return False
            if not isinstance(drop.get("confidence"), (int, float)) or drop.get("confidence") < 0.0 or drop.get("confidence") > 1.0:
                print(f"[{self.agent_name}] Validation Failed: Confidence score out of bounds.", flush=True)
                return False

        impacts = beat_map.get("impact_opportunity_map", [])
        if not isinstance(impacts, list):
            return False
            
        for impact in impacts:
            tolerance = impact.get("tolerance_window", {})
            if "early_sec" not in tolerance or "late_sec" not in tolerance:
                print(f"[{self.agent_name}] Validation Failed: Missing strict tolerance window.", flush=True)
                return False

        health = beat_map.get("analysis_health_report", {})
        if "bpm_confidence" not in health:
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

        vibe_data = module_scripting.get("agent_07_vibe", {})
        tension_data = module_scripting.get("agent_04_tension_analysis", [])
        global_timestamps = module_audio.get("agent_12_global_timestamps", {})

        if not global_timestamps or not vibe_data:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 12 Timeline or Agent 07 Vibe Data.")

        # Caching & Idempotency Check
        current_hash = self._generate_state_hash(vibe_data, global_timestamps)
        existing_map = module_audio.get("agent_14_beat_drop_map", {})
        
        if existing_map and existing_map.get("_blueprint_hash") == current_hash:
            print(f"[{self.agent_name}] INFO: Deterministic cache hit. Skipping re-analysis.", flush=True)
            return state

        if "agent_14_beat_drop_map" in module_audio:
            del module_audio["agent_14_beat_drop_map"]

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "vibe_json": json.dumps(vibe_data, indent=2),
            "timeline_json": json.dumps(global_timestamps, indent=2),
            "tension_json": json.dumps(tension_data, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_14_phonk_beat_drop.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Musical Intelligence Layer. Strict adherence to agent boundaries. Output valid JSON only.",
            temperature=0.4,  # Low temperature for mathematical consistency
            required_keys=["agent_14_beat_drop_map"],
            project_id=project_id
        )

        beat_map = response["data"]["agent_14_beat_drop_map"]
        
        if not self._validate_beat_map_deep(beat_map):
            raise ValueError(f"[{self.agent_name}] [LLM003] Validation Failed: Drop hierarchy or tolerance corruption detected.")

        # Save Hash for future Caching
        beat_map["_blueprint_hash"] = current_hash

        module_audio["agent_14_beat_drop_map"] = beat_map
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        total_drops = len(beat_map.get("drop_hierarchy_and_candidates", []))
        
        print(f"[{self.agent_name}] INFO: Phonk Architecture locked! Mapped {total_drops} drops securely. Handoff ready for Sub-Bass & SFX. (Time: {exec_time}s via {provider})", flush=True)

        return state

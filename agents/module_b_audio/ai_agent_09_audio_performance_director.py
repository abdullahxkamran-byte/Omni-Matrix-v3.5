import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_09_Audio_Performance_Director:
    def __init__(self):
        self.agent_name = "Ai_Agent_09_Audio_Performance_Director"
        self.required_root_keys = [
            "global_audio_directives",
            "character_voice_profiles",
            "scene_performances"
        ]

    def _validate_performance_deep(self, performance_map: dict, expected_scene_count: int) -> bool:
        if not isinstance(performance_map, dict):
            return False

        for key in self.required_root_keys:
            if key not in performance_map:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        profiles = performance_map.get("character_voice_profiles", [])
        if not isinstance(profiles, list):
            return False
            
        valid_speaker_ids = []
        for p in profiles:
            if isinstance(p, dict) and "speaker_id" in p:
                valid_speaker_ids.append(p["speaker_id"])
                
                profile_keys = ["gender_presentation", "vocal_age", "voice_personality", "pitch_tendency", "speaking_style", "emotional_baseline"]
                if not all(k in p for k in profile_keys):
                    print(f"[{self.agent_name}] Validation Failed: Character profile missing deep trait keys.", flush=True)
                    return False

        valid_speaker_ids.append("None")

        scenes = performance_map.get("scene_performances", [])
        if not isinstance(scenes, list) or len(scenes) != expected_scene_count:
            print(f"[{self.agent_name}] Validation Failed: Expected {expected_scene_count} scene performances.", flush=True)
            return False

        for scene in scenes:
            if not isinstance(scene, dict):
                return False
                
            speaker_id = scene.get("speaker_id")
            if speaker_id not in valid_speaker_ids:
                print(f"[{self.agent_name}] Validation Failed: Speaker ID '{speaker_id}' not found.", flush=True)
                return False

            duration_target = scene.get("line_duration_target", {})
            if not isinstance(duration_target, dict) or "total_target_sec" not in duration_target:
                print(f"[{self.agent_name}] Validation Failed: Missing 'total_target_sec'.", flush=True)
                return False

            word_map = scene.get("word_level_timing_map", [])
            if not isinstance(word_map, list):
                print(f"[{self.agent_name}] Validation Failed: 'word_level_timing_map' must be a list.", flush=True)
                return False

            for word_obj in word_map:
                if not isinstance(word_obj, dict):
                    return False
                word_keys = ["word", "target_duration_sec", "stretch_compress_intent", "emphasis_level", "pause_before_sec", "pause_after_sec"]
                if not all(wk in word_obj for wk in word_keys):
                    print(f"[{self.agent_name}] Validation Failed: Incomplete word-level intent in mapping.", flush=True)
                    return False

            handoff = scene.get("module_c_handoff_package", {})
            if not isinstance(handoff, dict) or "post_process_required" not in handoff:
                print(f"[{self.agent_name}] Validation Failed: Missing 'module_c_handoff_package' structure.", flush=True)
                return False

            if handoff.get("post_process_required") is True:
                adjustments = handoff.get("word_adjustments", [])
                if not isinstance(adjustments, list):
                    return False
                for adj in adjustments:
                    if not isinstance(adj, dict) or "action" not in adj or "target_duration_sec" not in adj:
                        print(f"[{self.agent_name}] Validation Failed: Invalid word adjustment block.", flush=True)
                        return False

        return True

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
            print(f"[{self.agent_name}] Warning: Schema mismatch.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        
        module_scripting = runtime_data.get("module_a_scripting", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        if "agent_09_audio_performance_map" in module_audio:
            del module_audio["agent_09_audio_performance_map"]

        master_blueprint = module_scripting.get("agent_08_master_blueprint", {})
        if not master_blueprint or "master_scenes" not in master_blueprint:
            raise ValueError(f"[{self.agent_name}] CRITICAL: Missing Agent 08 Master Blueprint.")

        master_scenes = master_blueprint.get("master_scenes", [])
        expected_scene_count = len(master_scenes)
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "master_blueprint_json": json.dumps(master_blueprint, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_09_audio_performance.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Audio Performance Director. Output strictly valid JSON.",
            temperature=0.4,
            required_keys=["agent_09_audio_performance_map"],
            project_id=project_id
        )

        performance_map = response["data"]["agent_09_audio_performance_map"]
        
        if not self._validate_performance_deep(performance_map, expected_scene_count):
            raise ValueError(f"[{self.agent_name}] Validation Failed: Performance map corruption or missing data.")

        module_audio["agent_09_audio_performance_map"] = performance_map
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        total_speakers = len(performance_map.get("character_voice_profiles", []))
        
        print(f"[{self.agent_name}] INFO: Audio Performance Blueprint generated successfully! Extracted {total_speakers} speaker profiles. (Time: {exec_time}s via {provider})", flush=True)

        return state

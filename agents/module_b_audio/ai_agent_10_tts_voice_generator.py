import json
import hashlib
from datetime import datetime, timezone
from core.voice_research_gateway import Voice_Research_Gateway
from core.tts_provider_gateway import TTS_Provider_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_10_TTS_Voice_Generator:
    def __init__(self):
        self.agent_name = "Ai_Agent_10_TTS_Voice_Generator"
        self.required_audio_result_keys = [
            "status",
            "output_path",
            "actual_duration_sec",
            "generation_settings",
            "provider",
            "voice_id"
        ]

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _discover_voice(self, profile: dict, state: dict) -> dict:
        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        variables = {"character_profile_json": json.dumps(profile, indent=2)}
        prompt = Prompt_Manager.load(prompts_dir, "agent_10_voice_discovery.txt", variables)
        
        gateway = Voice_Research_Gateway()
        response = gateway.generate_research(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Voice Research Gateway. Use search to find exact voice IDs. Return strict JSON.",
            required_keys=["voice_discovery_result"],
            project_id=project_id
        )
        return response["data"]["voice_discovery_result"]

    def execute(self, state: dict) -> dict:
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.get("module_a_scripting", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        if "agent_10_tts_metadata" in module_audio:
            del module_audio["agent_10_tts_metadata"]

        global_registry = runtime_data.setdefault("global_voice_registry", {})
        project_voice_registry = global_registry.setdefault(project_id, {})
        
        performance_map = module_audio.get("agent_09_audio_performance_map", {})
        if not performance_map or "scene_performances" not in performance_map:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 09 Performance Map.")

        master_blueprint = module_scripting.get("agent_08_master_blueprint", {})
        
        master_scenes = {}
        for s in master_blueprint.get("master_scenes", []):
            if isinstance(s, dict) and "scene_id" in s:
                master_scenes[s["scene_id"]] = s

        profiles = performance_map.get("character_voice_profiles", [])
        for profile in profiles:
            speaker_id = profile.get("speaker_id")
            if not speaker_id or speaker_id == "None":
                continue
                
            if speaker_id not in project_voice_registry:
                discovery = self._discover_voice(profile, state)
                
                status = discovery.get("verification_status", "DISCOVERED")
                final_status = "VERIFIED_LOCKED" if status == "VERIFIED" else "DISCOVERED"
                
                project_voice_registry[speaker_id] = {
                    "character_id": speaker_id,
                    "provider": discovery.get("provider", "UNKNOWN"),
                    "voice_id": discovery.get("voice_id", "UNKNOWN"),
                    "voice_name": discovery.get("voice_name", "UNKNOWN"),
                    "language": discovery.get("language", "en-US"),
                    "accent": discovery.get("accent", "Unknown"),
                    "voice_characteristics": discovery.get("voice_characteristics", []),
                    "provider_model": discovery.get("provider_model", "UNKNOWN"),
                    "verification_evidence": discovery.get("verification_evidence", "None"),
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "verification_status": final_status
                }

        tts_gateway = TTS_Provider_Gateway(workspace_dir)
        tts_metadata_log = []

        scene_performances = performance_map.get("scene_performances", [])
        for perf in scene_performances:
            scene_id = perf.get("scene_id")
            speaker_id = perf.get("speaker_id")
            
            if not scene_id or speaker_id == "None" or speaker_id not in project_voice_registry:
                continue

            master_scene = master_scenes.get(scene_id, {})
            source_text = master_scene.get("narration_block", {}).get("phonetic_text", "")
            
            if not source_text or source_text == "None":
                continue

            word_timing_map = perf.get("word_level_timing_map", [])
            if not word_timing_map:
                raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing word_level_timing_map for scene {scene_id}.")

            text_hash = self._hash_text(source_text)
            registry_entry = project_voice_registry[speaker_id]
            target_duration = perf.get("line_duration_target", {}).get("total_target_sec", 0.0)

            audio_result = tts_gateway.generate_voice(source_text, registry_entry, perf, scene_id)
            
            if not all(k in audio_result for k in self.required_audio_result_keys):
                raise ValueError(f"[{self.agent_name}] [AG003] CRITICAL: Malformed response from TTS_Provider_Gateway.")

            if audio_result["status"] != "SUCCESS":
                raise RuntimeError(f"[{self.agent_name}] [LLM005] TTS Generation Failed for {scene_id}")

            actual_duration = audio_result["actual_duration_sec"]
            timing_tolerance = perf.get("line_duration_target", {}).get("timing_tolerance", "Strict")
            
            module_c_handoff = False
            if timing_tolerance == "Strict" and abs(actual_duration - target_duration) > 0.2:
                module_c_handoff = True
                
            if perf.get("module_c_handoff_package", {}).get("post_process_required") is True:
                module_c_handoff = True

            metadata_entry = {
                "scene_id": scene_id,
                "speaker_id": speaker_id,
                "provider": audio_result["provider"],
                "voice_id": audio_result["voice_id"],
                "generation_settings": audio_result["generation_settings"],
                "source_text_hash": text_hash,
                "target_duration_sec": target_duration,
                "actual_duration_sec": actual_duration,
                "output_path": audio_result["output_path"],
                "word_level_timing_intent_passed": word_timing_map,
                "module_c_handoff_required": module_c_handoff,
                "validation_status": "PASSED"
            }
            tts_metadata_log.append(metadata_entry)

        module_audio["agent_10_tts_metadata"] = tts_metadata_log

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Generated {len(tts_metadata_log)} audio assets. Verification flow strict. Handoff prepared.", flush=True)

        return state

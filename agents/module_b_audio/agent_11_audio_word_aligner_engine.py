import time
from core.state_manager import State_Manager

class Agent_11_Audio_Word_Aligner_Engine:
    def __init__(self):
        self.agent_name = "Agent_11_Audio_Word_Aligner_Engine"
        # FFmpeg atempo hard limits (Hardware Safety Cap - Rule 9)
        self.min_atempo = 0.5
        self.max_atempo = 2.0

    def _calculate_advanced_alignment(self, actual_total_duration: float, target_intents: list) -> dict:
        total_target = sum(
            w.get("target_duration_sec", 0.0) + w.get("pause_before_sec", 0.0) + w.get("pause_after_sec", 0.0)
            for w in target_intents
        )

        # Scale factor tells us how much the actual TTS deviated from Agent 9's intent
        scale_factor = actual_total_duration / total_target if total_target > 0 else 1.0

        aligned_words = []
        current_actual_time = 0.0
        word_count = 0

        for intent in target_intents:
            word = intent.get("word", "")
            if word.strip():
                word_count += 1

            # Proportional mapping based on TTS generation reality
            mapped_pause_before = intent.get("pause_before_sec", 0.0) * scale_factor
            mapped_duration = intent.get("target_duration_sec", 0.0) * scale_factor
            mapped_pause_after = intent.get("pause_after_sec", 0.0) * scale_factor

            start_time = current_actual_time + mapped_pause_before
            end_time = start_time + mapped_duration

            # ADVANCED: Pre-calculate FFmpeg atempo for Module C
            # If actual duration is 1.5s but target was 1.0s, atempo needs to be 1.5x to force it back.
            desired_target = intent.get("target_duration_sec", 0.0)
            if desired_target > 0:
                raw_atempo = mapped_duration / desired_target
            else:
                raw_atempo = 1.0
            
            # Clamp to safe limits to prevent FFmpeg crashes
            safe_atempo = max(self.min_atempo, min(self.max_atempo, raw_atempo))

            aligned_words.append({
                "word": word,
                "estimated_start_sec": round(start_time, 3),
                "estimated_end_sec": round(end_time, 3),
                "mapped_duration_sec": round(mapped_duration, 3),
                "target_duration_sec": desired_target,
                "stretch_compress_intent": intent.get("stretch_compress_intent", "normal"),
                "emphasis_level": intent.get("emphasis_level", "low"),
                "sync_marker": intent.get("sync_marker", "None"),
                "ffmpeg_atempo_correction": round(safe_atempo, 3)
            })

            current_actual_time = end_time + mapped_pause_after

        # Pacing Analytics
        duration_minutes = actual_total_duration / 60.0 if actual_total_duration > 0 else 1.0
        wpm = round(word_count / duration_minutes)

        return {
            "aligned_words": aligned_words,
            "scale_factor_applied": round(scale_factor, 4),
            "actual_wpm": wpm
        }

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # Idempotency Scrubbing
        if "agent_11_word_alignment_map" in module_audio:
            del module_audio["agent_11_word_alignment_map"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        tts_metadata = module_audio.get("agent_10_tts_metadata", [])
        if not tts_metadata:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 10 TTS Metadata.")

        master_alignment_log = []

        for audio_asset in tts_metadata:
            scene_id = audio_asset.get("scene_id")
            speaker_id = audio_asset.get("speaker_id")
            actual_duration = audio_asset.get("actual_duration_sec", 0.0)
            word_intents = audio_asset.get("word_level_timing_intent_passed", [])

            if not word_intents or speaker_id == "None":
                continue

            # Run Advanced Mathematical Alignment
            alignment_data = self._calculate_advanced_alignment(actual_duration, word_intents)

            master_alignment_log.append({
                "scene_id": scene_id,
                "speaker_id": speaker_id,
                "output_path": audio_asset.get("output_path"),
                "actual_duration_sec": actual_duration,
                "scale_factor_applied": alignment_data["scale_factor_applied"],
                "scene_wpm": alignment_data["actual_wpm"],
                "aligned_words": alignment_data["aligned_words"]
            })

        module_audio["agent_11_word_alignment_map"] = master_alignment_log

        exec_time = round(time.time() - start_time, 2)
        state.setdefault("metrics", {})[self.agent_name] = {
            "provider": "Procedural DSP Math",
            "execution_time_sec": exec_time,
            "aligned_scenes": len(master_alignment_log)
        }

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Procedural alignment complete! Pre-calculated FFmpeg parameters for {len(master_alignment_log)} scenes. (Time: {exec_time}s)", flush=True)

        return state

import time
import math
from core.state_manager import State_Manager

class Agent_12_Precision_Timestamp_Generator:
    def __init__(self):
        self.agent_name = "Agent_12_Precision_Timestamp_Generator"

    def _sec_to_frame(self, time_sec: float, fps: int) -> int:
        """Converts absolute seconds to exact frame numbers based on project FPS."""
        return math.floor(time_sec * fps)

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # Idempotency Scrubbing
        if "agent_12_global_timestamps" in module_audio:
            del module_audio["agent_12_global_timestamps"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        alignment_map = module_audio.get("agent_11_word_alignment_map", [])
        if not alignment_map:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 11 Alignment Map.")

        global_config = state.get("global_config", {})
        fps = int(global_config.get("fps", 30))

        global_current_sec = 0.0
        master_timeline = []
        global_sync_markers = []

        for scene_data in alignment_map:
            scene_id = scene_data.get("scene_id")
            actual_duration = scene_data.get("actual_duration_sec", 0.0)
            words = scene_data.get("aligned_words", [])
            
            scene_start_sec = global_current_sec
            scene_end_sec = global_current_sec + actual_duration
            
            global_words = []
            
            for word_data in words:
                local_start = word_data.get("estimated_start_sec", 0.0)
                local_end = word_data.get("estimated_end_sec", 0.0)
                
                global_start = round(scene_start_sec + local_start, 3)
                global_end = round(scene_start_sec + local_end, 3)
                
                start_frame = self._sec_to_frame(global_start, fps)
                end_frame = self._sec_to_frame(global_end, fps)
                
                sync_marker = word_data.get("sync_marker", "None")
                if sync_marker != "None":
                    global_sync_markers.append({
                        "scene_id": scene_id,
                        "marker_type": sync_marker,
                        "word": word_data.get("word", ""),
                        "global_sec": global_start,
                        "global_frame": start_frame
                    })
                
                global_words.append({
                    "word": word_data.get("word", ""),
                    "global_start_sec": global_start,
                    "global_end_sec": global_end,
                    "global_start_frame": start_frame,
                    "global_end_frame": end_frame,
                    "ffmpeg_atempo_correction": word_data.get("ffmpeg_atempo_correction", 1.0)
                })

            master_timeline.append({
                "scene_id": scene_id,
                "global_scene_start_sec": round(scene_start_sec, 3),
                "global_scene_end_sec": round(scene_end_sec, 3),
                "global_scene_start_frame": self._sec_to_frame(scene_start_sec, fps),
                "global_scene_end_frame": self._sec_to_frame(scene_end_sec, fps),
                "global_words": global_words
            })
            
            global_current_sec = scene_end_sec

        module_audio["agent_12_global_timestamps"] = {
            "fps_reference": fps,
            "total_calculated_duration_sec": round(global_current_sec, 3),
            "total_calculated_frames": self._sec_to_frame(global_current_sec, fps),
            "master_timeline": master_timeline,
            "global_sync_markers": global_sync_markers
        }

        exec_time = round(time.time() - start_time, 4)
        state.setdefault("metrics", {})[self.agent_name] = {
            "provider": "Procedural Timestamp Math",
            "execution_time_sec": exec_time,
            "total_frames_calculated": self._sec_to_frame(global_current_sec, fps)
        }

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Global timeline generated. Total Duration: {round(global_current_sec, 2)}s | FPS: {fps}. (Time: {exec_time}s)", flush=True)

        return state

import math
import time
from core.state_manager import State_Manager


class Agent_12_Precision_Timestamp_Generator:
    def __init__(self):
        self.agent_name = "Agent_12_Precision_Timestamp_Generator"
        self.default_fps = 30
        self.timestamp_precision = 3

    def _safe_float(self, value, field_name: str, default=None) -> float:
        if value is None:
            if default is not None:
                return float(default)
            raise ValueError(
                f"[{self.agent_name}] [AG012] Invalid numeric value for '{field_name}'."
            )

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"[{self.agent_name}] [AG012] Invalid numeric value for '{field_name}': {value}"
            )

        if not math.isfinite(number):
            raise ValueError(
                f"[{self.agent_name}] [AG012] Non-finite numeric value for '{field_name}'."
            )

        return number

    def _sec_to_frame(self, time_sec: float, fps: int) -> int:
        time_sec = self._safe_float(time_sec, "time_sec")

        if fps <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG013] FPS must be greater than zero."
            )

        if time_sec < 0:
            raise ValueError(
                f"[{self.agent_name}] [AG014] Timestamp cannot be negative."
            )

        return int(math.floor((time_sec * fps) + 1e-9))

    def _round_time(self, value: float) -> float:
        return round(
            self._safe_float(value, "timestamp"),
            self.timestamp_precision
        )

    def _validate_fps(self, global_config: dict) -> int:
        raw_fps = global_config.get("fps", self.default_fps)

        try:
            fps = int(raw_fps)
        except (TypeError, ValueError):
            raise ValueError(
                f"[{self.agent_name}] [AG003] Invalid project FPS: {raw_fps}"
            )

        if fps <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG003] Project FPS must be greater than zero."
            )

        return fps

    def _validate_scene_data(self, scene_data: dict, scene_index: int):
        if not isinstance(scene_data, dict):
            raise ValueError(
                f"[{self.agent_name}] [AG004] Scene index {scene_index} is not a valid object."
            )

        scene_id = scene_data.get("scene_id")

        if not scene_id:
            raise ValueError(
                f"[{self.agent_name}] [AG004] Scene index {scene_index} has no scene_id."
            )

        actual_duration = self._safe_float(
            scene_data.get("actual_duration_sec", 0.0),
            f"{scene_id}.actual_duration_sec"
        )

        if actual_duration <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG005] Scene '{scene_id}' has invalid duration: {actual_duration}"
            )

        words = scene_data.get("aligned_words", [])

        if not isinstance(words, list):
            raise ValueError(
                f"[{self.agent_name}] [AG006] Scene '{scene_id}' aligned_words must be a list."
            )

        return scene_id, actual_duration, words

    def _validate_word_timing(
        self,
        word_data: dict,
        scene_id: str,
        scene_duration: float,
        word_index: int
    ):
        if not isinstance(word_data, dict):
            raise ValueError(
                f"[{self.agent_name}] [AG007] Invalid word object in scene '{scene_id}' at index {word_index}."
            )

        word = str(word_data.get("word", "")).strip()

        if not word:
            raise ValueError(
                f"[{self.agent_name}] [AG008] Empty word in scene '{scene_id}' at index {word_index}."
            )

        local_start = self._safe_float(
            word_data.get("estimated_start_sec", 0.0),
            f"{scene_id}.{word}.start"
        )

        local_end = self._safe_float(
            word_data.get("estimated_end_sec", 0.0),
            f"{scene_id}.{word}.end"
        )

        if local_start < 0:
            raise ValueError(
                f"[{self.agent_name}] [AG009] Negative word start in scene '{scene_id}': {local_start}"
            )

        if local_end < local_start:
            raise ValueError(
                f"[{self.agent_name}] [AG010] Word end precedes start in scene '{scene_id}': '{word}'"
            )

        if local_end > scene_duration + 0.001:
            raise ValueError(
                f"[{self.agent_name}] [AG011] Word '{word}' exceeds scene duration in '{scene_id}'."
            )

        return word, local_start, local_end

    def _validate_word_sequence(
        self,
        validated_words: list,
        scene_id: str
    ):
        previous_end = 0.0

        for index, word_data in enumerate(validated_words):
            current_start = word_data["local_start_sec"]
            current_end = word_data["local_end_sec"]

            if current_start < previous_end - 0.001:
                raise ValueError(
                    f"[{self.agent_name}] [AG015] Overlapping word timing detected "
                    f"in scene '{scene_id}' at word index {index}."
                )

            previous_end = max(previous_end, current_end)

    def execute(self, state: dict) -> dict:
        start_time = time.time()

        workspace_dir = state.get("workspace_dir", "")

        if not workspace_dir:
            raise ValueError(
                f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state."
            )

        sm = State_Manager(workspace_dir)

        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        alignment_map = module_audio.get(
            "agent_11_word_alignment_map",
            []
        )

        if not isinstance(alignment_map, list) or not alignment_map:
            raise ValueError(
                f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 11 Alignment Map."
            )

        global_config = state.get("global_config", {})
        fps = self._validate_fps(global_config)

        module_audio.pop("agent_12_global_timestamps", None)

        global_current_sec = 0.0
        master_timeline = []
        global_sync_markers = []

        seen_scene_ids = set()

        for scene_index, scene_data in enumerate(alignment_map):
            scene_id, actual_duration, words = self._validate_scene_data(
                scene_data,
                scene_index
            )

            if scene_id in seen_scene_ids:
                raise ValueError(
                    f"[{self.agent_name}] [AG016] Duplicate scene_id detected: '{scene_id}'."
                )

            seen_scene_ids.add(scene_id)

            scene_start_sec = self._round_time(global_current_sec)
            scene_end_sec = self._round_time(
                global_current_sec + actual_duration
            )

            validated_words = []

            for word_index, word_data in enumerate(words):
                word, local_start, local_end = self._validate_word_timing(
                    word_data,
                    scene_id,
                    actual_duration,
                    word_index
                )

                validated_words.append({
                    "word": word,
                    "local_start_sec": local_start,
                    "local_end_sec": local_end,
                    "source_data": word_data
                })

            self._validate_word_sequence(
                validated_words,
                scene_id
            )

            global_words = []

            for word_data in validated_words:
                source_data = word_data["source_data"]

                global_start = self._round_time(
                    scene_start_sec + word_data["local_start_sec"]
                )

                global_end = self._round_time(
                    scene_start_sec + word_data["local_end_sec"]
                )

                start_frame = self._sec_to_frame(
                    global_start,
                    fps
                )

                end_frame = self._sec_to_frame(
                    global_end,
                    fps
                )

                if end_frame < start_frame:
                    raise ValueError(
                        f"[{self.agent_name}] [AG017] Invalid frame ordering "
                        f"for word '{word_data['word']}' in scene '{scene_id}'."
                    )

                sync_marker = source_data.get(
                    "sync_marker",
                    "None"
                )

                if sync_marker != "None":
                    global_sync_markers.append({
                        "scene_id": scene_id,
                        "marker_type": sync_marker,
                        "word": word_data["word"],
                        "global_sec": global_start,
                        "global_frame": start_frame
                    })

                global_words.append({
                    "word": word_data["word"],
                    "global_start_sec": global_start,
                    "global_end_sec": global_end,
                    "global_start_frame": start_frame,
                    "global_end_frame": end_frame,
                    "ffmpeg_atempo_correction": source_data.get(
                        "ffmpeg_atempo_correction",
                        1.0
                    )
                })

            scene_start_frame = self._sec_to_frame(
                scene_start_sec,
                fps
            )

            scene_end_frame = self._sec_to_frame(
                scene_end_sec,
                fps
            )

            master_timeline.append({
                "scene_id": scene_id,
                "global_scene_start_sec": scene_start_sec,
                "global_scene_end_sec": scene_end_sec,
                "global_scene_start_frame": scene_start_frame,
                "global_scene_end_frame": scene_end_frame,
                "duration_sec": self._round_time(actual_duration),
                "global_words": global_words
            })

            global_current_sec = scene_end_sec

        total_duration = self._round_time(global_current_sec)
        total_frames = self._sec_to_frame(
            total_duration,
            fps
        )

        global_timestamp_package = {
            "fps_reference": fps,
            "timestamp_precision_sec": self.timestamp_precision,
            "frame_conversion_policy": "floor",
            "total_calculated_duration_sec": total_duration,
            "total_calculated_frames": total_frames,
            "scene_count": len(master_timeline),
            "master_timeline": master_timeline,
            "global_sync_markers": global_sync_markers
        }

        module_audio["agent_12_global_timestamps"] = (
            global_timestamp_package
        )

        exec_time = round(
            time.time() - start_time,
            4
        )

        state.setdefault("metrics", {})[
            self.agent_name
        ] = {
            "provider": "Procedural Timestamp Math",
            "execution_time_sec": exec_time,
            "total_frames_calculated": total_frames,
            "scene_count": len(master_timeline),
            "sync_marker_count": len(global_sync_markers),
            "fps": fps
        }

        pipeline_status = state.setdefault(
            "pipeline_status",
            {}
        )

        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(
            f"[{self.agent_name}] INFO: Global timeline generated. "
            f"Scenes: {len(master_timeline)} | "
            f"Duration: {total_duration}s | "
            f"Frames: {total_frames} | "
            f"FPS: {fps} | "
            f"Sync Markers: {len(global_sync_markers)} | "
            f"Time: {exec_time}s",
            flush=True
        )

        return state
import math
import time
from core.state_manager import State_Manager


class Agent_11_Audio_Word_Aligner_Engine:
    def __init__(self):
        self.agent_name = "Agent_11_Audio_Word_Aligner_Engine"

        self.min_atempo = 0.5
        self.max_atempo = 2.0

        self.micro_correction_threshold = 0.03
        self.major_correction_threshold = 0.15
        self.timestamp_precision = 3

    def _safe_float(self, value, field_name: str, default=0.0) -> float:
        if value is None:
            return float(default)

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"[{self.agent_name}] [AG003] Invalid numeric field '{field_name}': {value}"
            )

        if not math.isfinite(number):
            raise ValueError(
                f"[{self.agent_name}] [AG004] Non-finite numeric field '{field_name}'."
            )

        return number

    def _round(self, value: float) -> float:
        return round(
            self._safe_float(value, "timestamp"),
            self.timestamp_precision
        )

    def _clamp_atempo(self, value: float) -> float:
        return round(
            max(self.min_atempo, min(self.max_atempo, value)),
            3
        )

    def _validate_intent(self, intent: dict, index: int, scene_id: str) -> dict:
        if not isinstance(intent, dict):
            raise ValueError(
                f"[{self.agent_name}] [AG005] Invalid word intent at index {index} in scene '{scene_id}'."
            )

        word = str(intent.get("word", "")).strip()

        if not word:
            raise ValueError(
                f"[{self.agent_name}] [AG006] Empty word at index {index} in scene '{scene_id}'."
            )

        target_duration = self._safe_float(
            intent.get("target_duration_sec", 0.0),
            f"{scene_id}.{word}.target_duration_sec"
        )

        pause_before = self._safe_float(
            intent.get("pause_before_sec", 0.0),
            f"{scene_id}.{word}.pause_before_sec"
        )

        pause_after = self._safe_float(
            intent.get("pause_after_sec", 0.0),
            f"{scene_id}.{word}.pause_after_sec"
        )

        if target_duration < 0:
            raise ValueError(
                f"[{self.agent_name}] [AG007] Negative target duration for '{word}' in '{scene_id}'."
            )

        if pause_before < 0 or pause_after < 0:
            raise ValueError(
                f"[{self.agent_name}] [AG008] Negative pause value for '{word}' in '{scene_id}'."
            )

        return {
            "word": word,
            "target_duration_sec": target_duration,
            "pause_before_sec": pause_before,
            "pause_after_sec": pause_after,
            "stretch_compress_intent": intent.get(
                "stretch_compress_intent",
                "normal"
            ),
            "emphasis_level": intent.get(
                "emphasis_level",
                "low"
            ),
            "sync_marker": intent.get(
                "sync_marker",
                "None"
            )
        }

    def _classify_correction(
        self,
        target_duration: float,
        mapped_duration: float
    ) -> dict:
        if target_duration <= 0:
            return {
                "correction_required": False,
                "correction_type": "NO_CORRECTION",
                "correction_direction": "NONE",
                "duration_delta_sec": 0.0,
                "duration_ratio": 1.0,
                "atempo": 1.0,
                "clamped": False
            }

        duration_delta = mapped_duration - target_duration
        ratio = mapped_duration / target_duration

        if abs(duration_delta) <= self.micro_correction_threshold:
            correction_type = "NO_CORRECTION"
        elif abs(duration_delta) <= self.major_correction_threshold:
            correction_type = "MICRO_CORRECTION"
        else:
            correction_type = "MAJOR_CORRECTION"

        if duration_delta > self.micro_correction_threshold:
            direction = "COMPRESS"
        elif duration_delta < -self.micro_correction_threshold:
            direction = "STRETCH"
        else:
            direction = "NONE"

        raw_atempo = ratio
        safe_atempo = self._clamp_atempo(raw_atempo)

        return {
            "correction_required": correction_type != "NO_CORRECTION",
            "correction_type": correction_type,
            "correction_direction": direction,
            "duration_delta_sec": self._round(duration_delta),
            "duration_ratio": round(ratio, 4),
            "atempo": safe_atempo,
            "clamped": abs(raw_atempo - safe_atempo) > 0.0001
        }

    def _calculate_alignment(
        self,
        actual_total_duration: float,
        target_intents: list
    ) -> dict:
        actual_total_duration = self._safe_float(
            actual_total_duration,
            "actual_total_duration"
        )

        if actual_total_duration <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG009] Actual audio duration must be greater than zero."
            )

        validated_intents = []

        for index, intent in enumerate(target_intents):
            validated_intents.append(
                self._validate_intent(
                    intent,
                    index,
                    "CURRENT_SCENE"
                )
            )

        total_target = sum(
            item["target_duration_sec"]
            + item["pause_before_sec"]
            + item["pause_after_sec"]
            for item in validated_intents
        )

        if total_target <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG010] Total Agent 9 timing intent is zero."
            )

        scale_factor = actual_total_duration / total_target

        aligned_words = []
        correction_package = []

        current_actual_time = 0.0
        word_count = 0

        previous_end = 0.0

        for intent in validated_intents:
            word = intent["word"]

            if word:
                word_count += 1

            mapped_pause_before = (
                intent["pause_before_sec"] * scale_factor
            )

            mapped_duration = (
                intent["target_duration_sec"] * scale_factor
            )

            mapped_pause_after = (
                intent["pause_after_sec"] * scale_factor
            )

            start_time = (
                current_actual_time
                + mapped_pause_before
            )

            end_time = (
                start_time
                + mapped_duration
            )

            correction = self._classify_correction(
                intent["target_duration_sec"],
                mapped_duration
            )

            if start_time < previous_end - 0.001:
                raise ValueError(
                    f"[{self.agent_name}] [AG011] Timing overlap detected around '{word}'."
                )

            aligned_word = {
                "word": word,
                "estimated_start_sec": self._round(start_time),
                "estimated_end_sec": self._round(end_time),
                "mapped_duration_sec": self._round(mapped_duration),
                "target_duration_sec": self._round(
                    intent["target_duration_sec"]
                ),
                "mapped_pause_before_sec": self._round(
                    mapped_pause_before
                ),
                "mapped_pause_after_sec": self._round(
                    mapped_pause_after
                ),
                "target_pause_before_sec": self._round(
                    intent["pause_before_sec"]
                ),
                "target_pause_after_sec": self._round(
                    intent["pause_after_sec"]
                ),
                "stretch_compress_intent": intent[
                    "stretch_compress_intent"
                ],
                "emphasis_level": intent[
                    "emphasis_level"
                ],
                "sync_marker": intent[
                    "sync_marker"
                ],
                "correction_required": correction[
                    "correction_required"
                ],
                "correction_type": correction[
                    "correction_type"
                ],
                "correction_direction": correction[
                    "correction_direction"
                ],
                "duration_delta_sec": correction[
                    "duration_delta_sec"
                ],
                "duration_ratio": correction[
                    "duration_ratio"
                ],
                "ffmpeg_atempo_correction": correction[
                    "atempo"
                ],
                "atempo_was_clamped": correction[
                    "clamped"
                ]
            }

            aligned_words.append(aligned_word)

            if correction["correction_required"]:
                correction_package.append({
                    "word_index": len(aligned_words) - 1,
                    "word": word,
                    "direction": correction[
                        "correction_direction"
                    ],
                    "correction_type": correction[
                        "correction_type"
                    ],
                    "target_duration_sec": self._round(
                        intent["target_duration_sec"]
                    ),
                    "estimated_duration_sec": self._round(
                        mapped_duration
                    ),
                    "duration_delta_sec": correction[
                        "duration_delta_sec"
                    ],
                    "atempo": correction["atempo"],
                    "atempo_clamped": correction["clamped"],
                    "emphasis_level": intent[
                        "emphasis_level"
                    ],
                    "stretch_compress_intent": intent[
                        "stretch_compress_intent"
                    ]
                })

            current_actual_time = (
                end_time
                + mapped_pause_after
            )

            previous_end = end_time

        duration_minutes = actual_total_duration / 60.0

        actual_wpm = (
            round(word_count / duration_minutes)
            if duration_minutes > 0
            else 0
        )

        correction_count = len(correction_package)

        confidence = max(
            0.0,
            min(
                1.0,
                1.0 - (
                    abs(scale_factor - 1.0) * 0.75
                )
            )
        )

        if scale_factor < self.min_atempo:
            confidence *= 0.8

        if scale_factor > self.max_atempo:
            confidence *= 0.8

        return {
            "aligned_words": aligned_words,
            "correction_package": correction_package,
            "scale_factor_applied": round(
                scale_factor,
                4
            ),
            "alignment_method": "PROPORTIONAL_INTENT_MAPPING",
            "alignment_confidence": round(
                confidence,
                4
            ),
            "actual_wpm": actual_wpm,
            "word_count": word_count,
            "correction_count": correction_count,
            "total_mapped_duration_sec": self._round(
                current_actual_time
            )
        }

    def _validate_audio_asset(self, audio_asset: dict) -> tuple:
        scene_id = audio_asset.get("scene_id")
        speaker_id = audio_asset.get("speaker_id")
        actual_duration = audio_asset.get(
            "actual_duration_sec",
            0.0
        )
        word_intents = audio_asset.get(
            "word_level_timing_intent_passed",
            []
        )

        if not scene_id:
            raise ValueError(
                f"[{self.agent_name}] [AG012] Audio asset missing scene_id."
            )

        if not speaker_id:
            raise ValueError(
                f"[{self.agent_name}] [AG013] Audio asset '{scene_id}' missing speaker_id."
            )

        actual_duration = self._safe_float(
            actual_duration,
            f"{scene_id}.actual_duration_sec"
        )

        if actual_duration <= 0:
            raise ValueError(
                f"[{self.agent_name}] [AG014] Invalid audio duration for scene '{scene_id}'."
            )

        if not isinstance(word_intents, list):
            raise ValueError(
                f"[{self.agent_name}] [AG015] word_level_timing_intent_passed must be a list for '{scene_id}'."
            )

        if not word_intents:
            raise ValueError(
                f"[{self.agent_name}] [AG016] Missing Agent 9 word-level intent for '{scene_id}'."
            )

        return (
            scene_id,
            speaker_id,
            actual_duration,
            word_intents
        )

    def execute(self, state: dict) -> dict:
        start_time = time.time()

        workspace_dir = state.get(
            "workspace_dir",
            ""
        )

        if not workspace_dir:
            raise ValueError(
                f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state."
            )

        sm = State_Manager(workspace_dir)

        runtime_data = state.setdefault(
            "runtime_data",
            {}
        )

        module_audio = runtime_data.setdefault(
            "module_b_audio",
            {}
        )

        module_audio.pop(
            "agent_11_word_alignment_map",
            None
        )

        tts_metadata = module_audio.get(
            "agent_10_tts_metadata",
            []
        )

        if not isinstance(tts_metadata, list) or not tts_metadata:
            raise ValueError(
                f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 10 TTS Metadata."
            )

        master_alignment_log = []
        processed_scene_ids = set()

        total_corrections = 0
        total_words = 0
        skipped_assets = 0

        for audio_asset in tts_metadata:
            (
                scene_id,
                speaker_id,
                actual_duration,
                word_intents
            ) = self._validate_audio_asset(
                audio_asset
            )

            if speaker_id == "None":
                skipped_assets += 1
                continue

            if scene_id in processed_scene_ids:
                raise ValueError(
                    f"[{self.agent_name}] [AG017] Duplicate scene_id '{scene_id}' in Agent 10 metadata."
                )

            processed_scene_ids.add(scene_id)

            alignment_data = self._calculate_alignment(
                actual_duration,
                word_intents
            )

            aligned_words = alignment_data[
                "aligned_words"
            ]

            total_corrections += alignment_data[
                "correction_count"
            ]

            total_words += alignment_data[
                "word_count"
            ]

            master_alignment_log.append({
                "scene_id": scene_id,
                "speaker_id": speaker_id,
                "output_path": audio_asset.get(
                    "output_path"
                ),
                "provider": audio_asset.get(
                    "provider"
                ),
                "voice_id": audio_asset.get(
                    "voice_id"
                ),
                "actual_duration_sec": self._round(
                    actual_duration
                ),
                "scale_factor_applied": alignment_data[
                    "scale_factor_applied"
                ],
                "alignment_method": alignment_data[
                    "alignment_method"
                ],
                "alignment_confidence": alignment_data[
                    "alignment_confidence"
                ],
                "scene_wpm": alignment_data[
                    "actual_wpm"
                ],
                "word_count": alignment_data[
                    "word_count"
                ],
                "correction_count": alignment_data[
                    "correction_count"
                ],
                "aligned_words": aligned_words,
                "module_c_handoff_package": {
                    "post_process_required": (
                        alignment_data[
                            "correction_count"
                        ] > 0
                    ),
                    "correction_count": alignment_data[
                        "correction_count"
                    ],
                    "corrections": alignment_data[
                        "correction_package"
                    ],
                    "alignment_confidence": alignment_data[
                        "alignment_confidence"
                    ],
                    "source_alignment_method": alignment_data[
                        "alignment_method"
                    ]
                }
            })

        if not master_alignment_log:
            raise ValueError(
                f"[{self.agent_name}] [AG018] No valid scenes were aligned."
            )

        module_audio[
            "agent_11_word_alignment_map"
        ] = master_alignment_log

        exec_time = round(
            time.time() - start_time,
            4
        )

        state.setdefault(
            "metrics",
            {}
        )[self.agent_name] = {
            "provider": "Procedural DSP Intent Alignment",
            "execution_time_sec": exec_time,
            "aligned_scenes": len(
                master_alignment_log
            ),
            "aligned_words": total_words,
            "corrections_required": total_corrections,
            "skipped_assets": skipped_assets,
            "alignment_method": "PROPORTIONAL_INTENT_MAPPING"
        }

        pipeline_status = state.setdefault(
            "pipeline_status",
            {}
        )

        pipeline_status[
            "last_active_agent"
        ] = self.agent_name

        pipeline_status[
            self.agent_name
        ] = "COMPLETED"

        sm.save_state(state)

        print(
            f"[{self.agent_name}] INFO: "
            f"Alignment complete | "
            f"Scenes: {len(master_alignment_log)} | "
            f"Words: {total_words} | "
            f"Corrections: {total_corrections} | "
            f"Time: {exec_time}s",
            flush=True
        )

        return state
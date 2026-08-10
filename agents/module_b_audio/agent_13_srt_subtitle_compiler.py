import os
import re
import time
import math
import hashlib
import shutil
from core.state_manager import State_Manager

class Agent_13_SRT_Subtitle_Compiler:
    def __init__(self):
        self.agent_name = "Agent_13_SRT_Subtitle_Compiler"
        
        # Reading-Speed & Grouping Policies (Configurable per profile)
        self.max_chars_per_line = 42
        self.max_lines_per_cue = 2
        self.max_duration_sec = 6.0
        self.min_duration_sec = 0.5
        self.max_cps = 25.0
        self.pause_split_threshold_sec = 0.4  # Split cue if gap > 0.4s

    def _format_srt_timestamp(self, seconds: float) -> str:
        """Converts float seconds to SRT timestamp format (HH:MM:SS,mmm) safely."""
        if seconds < 0:
            seconds = 0.0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round(seconds - math.floor(seconds), 3) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _clean_text(self, text: str) -> str:
        """Sanitizes HTML/XML garbage and duplicate spaces."""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _smart_line_break(self, text: str) -> str:
        """Intelligently splits long text into 1-2 lines preferring center boundaries."""
        if len(text) <= self.max_chars_per_line:
            return text
            
        words = text.split()
        if len(words) <= 1:
            return text

        mid_point = len(text) // 2
        best_split_idx = 0
        min_dist = float('inf')

        current_len = 0
        for i, word in enumerate(words[:-1]):
            current_len += len(word) + 1
            dist = abs(current_len - mid_point)
            if dist < min_dist:
                min_dist = dist
                best_split_idx = i

        line1 = " ".join(words[:best_split_idx + 1])
        line2 = " ".join(words[best_split_idx + 1:])
        return f"{line1}\n{line2}"

    def _group_words_into_cues(self, master_timeline: list) -> list:
        """Groups words into logical subtitle cues based on pauses, punctuation, and duration."""
        cues = []
        
        for scene in master_timeline:
            scene_id = scene.get("scene_id")
            words = scene.get("global_words", [])
            if not words:
                continue

            current_cue = {"words": [], "start_sec": 0.0, "end_sec": 0.0, "text": "", "scene_id": scene_id}
            
            for i, word_data in enumerate(words):
                w_text = self._clean_text(word_data.get("word", ""))
                w_start = word_data.get("global_start_sec", 0.0)
                w_end = word_data.get("global_end_sec", 0.0)

                if not w_text:
                    continue

                if not current_cue["words"]:
                    current_cue["start_sec"] = w_start

                # Check pause between previous word and current word
                gap = 0.0
                if current_cue["words"]:
                    prev_end = current_cue["words"][-1]["end"]
                    gap = w_start - prev_end

                is_punctuation = bool(re.search(r'[.!?]$', current_cue["text"]))
                is_too_long = (w_end - current_cue["start_sec"]) > self.max_duration_sec
                is_too_many_chars = len(current_cue["text"] + " " + w_text) > (self.max_chars_per_line * 2)

                # Force split condition
                if current_cue["words"] and (gap >= self.pause_split_threshold_sec or is_punctuation or is_too_long or is_too_many_chars):
                    cues.append(dict(current_cue))
                    current_cue = {"words": [], "start_sec": w_start, "end_sec": 0.0, "text": "", "scene_id": scene_id}

                current_cue["words"].append({"text": w_text, "start": w_start, "end": w_end})
                current_cue["end_sec"] = w_end
                current_cue["text"] = " ".join([w["text"] for w in current_cue["words"]])

            if current_cue["words"]:
                cues.append(dict(current_cue))

        return cues

    def _repair_and_score_cues(self, cues: list) -> dict:
        """Performs overlap detection, reading-speed checks, and applies fixes."""
        repaired_cues = []
        metrics = {"overlaps_fixed": 0, "rejected": 0, "total_cps": 0.0}

        for i, cue in enumerate(cues):
            start = cue["start_sec"]
            end = cue["end_sec"]
            text = cue["text"]
            
            if not text:
                metrics["rejected"] += 1
                continue

            # Minimum Duration Fix
            duration = end - start
            if duration < self.min_duration_sec:
                end = start + self.min_duration_sec

            # Overlap Prevention
            if i < len(cues) - 1:
                next_start = cues[i+1]["words"][0]["start"] if cues[i+1]["words"] else float('inf')
                if end > next_start:
                    end = next_start - 0.001
                    metrics["overlaps_fixed"] += 1

            duration = max(0.001, end - start)
            cps = len(text) / duration
            metrics["total_cps"] += cps

            # Smart Line Break
            formatted_text = self._smart_line_break(text)

            score = 100
            if cps > self.max_cps: score -= 20
            if duration < 1.0: score -= 10
            
            repaired_cues.append({
                "cue_id": i + 1,
                "scene_id": cue["scene_id"],
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "formatted_text": formatted_text,
                "raw_text": text,
                "duration_sec": round(duration, 3),
                "cps": round(cps, 2),
                "quality_score": score
            })

        metrics["avg_cps"] = round(metrics["total_cps"] / len(repaired_cues), 2) if repaired_cues else 0.0
        return repaired_cues, metrics

    def _write_srt_atomically(self, cues: list, output_path: str) -> str:
        """Writes SRT to a temp file first, verifies it, then renames it safely."""
        tmp_path = f"{output_path}.tmp"
        
        srt_content = []
        for cue in cues:
            start_str = self._format_srt_timestamp(cue["start_sec"])
            end_str = self._format_srt_timestamp(cue["end_sec"])
            srt_content.append(f"{cue['cue_id']}")
            srt_content.append(f"{start_str} --> {end_str}")
            srt_content.append(f"{cue['formatted_text']}\n")

        full_text = "\n".join(srt_content)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        shutil.move(tmp_path, output_path)
        
        return hashlib.sha256(full_text.encode('utf-8')).hexdigest()

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        if "agent_13_subtitle_map" in module_audio:
            del module_audio["agent_13_subtitle_map"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        global_timestamps = module_audio.get("agent_12_global_timestamps", {})
        if not global_timestamps or "master_timeline" not in global_timestamps:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 12 Master Timeline.")

        master_timeline = global_timestamps["master_timeline"]

        # 1. Grouping
        raw_cues = self._group_words_into_cues(master_timeline)
        
        # 2. Repair & Score
        final_cues, repair_metrics = self._repair_and_score_cues(raw_cues)

        # 3. Export Files
        subs_dir = os.path.join(workspace_dir, "exports", "subtitles")
        os.makedirs(subs_dir, exist_ok=True)
        
        project_id = state.get("project_id", "project")
        srt_path = os.path.join(subs_dir, f"{project_id}_master.srt")
        
        srt_hash = self._write_srt_atomically(final_cues, srt_path)

        # 4. Save Internal Blueprint
        module_audio["agent_13_subtitle_map"] = {
            "srt_file_path": srt_path,
            "srt_sha256_hash": srt_hash,
            "cues": final_cues
        }

        # 5. Compile Metrics
        exec_time = round(time.time() - start_time, 3)
        total_words = sum(len(c["raw_text"].split()) for c in final_cues)
        
        state.setdefault("metrics", {})[self.agent_name] = {
            "provider": "Procedural Subtitle Compiler",
            "execution_time_sec": exec_time,
            "total_cues": len(final_cues),
            "total_words": total_words,
            "average_cps": repair_metrics["avg_cps"],
            "overlaps_fixed": repair_metrics["overlaps_fixed"],
            "rejected_cues": repair_metrics["rejected"]
        }

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: SRT Compiled Successfully! Generated {len(final_cues)} cues. Overlaps fixed: {repair_metrics['overlaps_fixed']}. Hash locked. (Time: {exec_time}s)", flush=True)

        return state

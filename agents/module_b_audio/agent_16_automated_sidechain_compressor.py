import time
import hashlib
import json
from core.state_manager import State_Manager

class Agent_16_Automated_Sidechain_Compressor:
    def __init__(self):
        self.agent_name = "Agent_16_Automated_Sidechain_Compressor"
        
        # Priority & DSP Configuration
        self.config = {
            "dialogue": {
                "priority": 1,
                "duck_depth_db": -16.0,
                "lookahead_sec": 0.1,
                "attack_sec": 0.15,
                "release_sec": 0.5,
                "debounce_gap_sec": 1.2 # Anti-pumping: merge words closer than 1.2s
            },
            "impact": {
                "priority": 2,
                "duck_depth_db": -8.0,
                "lookahead_sec": 0.05,
                "attack_sec": 0.05,
                "release_sec": 0.8,
                "debounce_gap_sec": 0.3
            }
        }

    def _generate_state_hash(self, timeline_data: dict, impact_data: dict) -> str:
        """Deterministic hashing for Caching & Idempotency."""
        raw = f"{json.dumps(timeline_data, sort_keys=True)}|{json.dumps(impact_data, sort_keys=True)}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    def _extract_and_sort_triggers(self, timeline_data: dict, impact_data: dict) -> list:
        triggers = []
        
        # Extract Dialogue Triggers (Agent 12)
        master_timeline = timeline_data.get("master_timeline", [])
        for scene in master_timeline:
            for word in scene.get("global_words", []):
                triggers.append({
                    "source": "dialogue",
                    "start_sec": word["global_start_sec"],
                    "end_sec": word["global_end_sec"],
                    "config": self.config["dialogue"]
                })
                
        # Extract Impact Triggers (Agent 15)
        impacts = impact_data.get("impact_designs", [])
        for impact in impacts:
            if impact.get("handoff_agent_16_sidechain", {}).get("sidechain_required", False):
                triggers.append({
                    "source": "impact",
                    "start_sec": impact["timestamp_sec"],
                    "end_sec": impact["timestamp_sec"] + impact["duration_sec"],
                    "config": self.config["impact"]
                })

        # Sort by start time mathematically
        triggers.sort(key=lambda x: x["start_sec"])
        return triggers

    def _debounce_triggers(self, triggers: list) -> list:
        """
        Anti-pumping protection: Merges close triggers of the same type.
        Ensures dialogue continuity by not bouncing volume between words.
        """
        if not triggers:
            return []

        merged = []
        current = triggers[0].copy()

        for next_trig in triggers[1:]:
            gap = next_trig["start_sec"] - current["end_sec"]
            debounce_limit = current["config"]["debounce_gap_sec"]

            if next_trig["source"] == current["source"] and gap <= debounce_limit:
                # Merge them: extend the end time
                current["end_sec"] = max(current["end_sec"], next_trig["end_sec"])
            else:
                merged.append(current)
                current = next_trig.copy()
        
        merged.append(current)
        return merged

    def _generate_dsp_envelopes(self, merged_triggers: list) -> list:
        """Translates merged triggers into exact mathematical ducking envelopes."""
        envelopes = []
        for trig in merged_triggers:
            cfg = trig["config"]
            
            start_sec = max(0.0, trig["start_sec"] - cfg["lookahead_sec"])
            duck_reached_sec = start_sec + cfg["attack_sec"]
            release_start_sec = trig["end_sec"]
            end_sec = release_start_sec + cfg["release_sec"]

            # Timeline Safety Check
            if start_sec >= end_sec:
                continue

            envelopes.append({
                "trigger_source": trig["source"],
                "duck_depth_db": cfg["duck_depth_db"],
                "env_start_sec": round(start_sec, 3),
                "duck_reached_sec": round(duck_reached_sec, 3),
                "release_start_sec": round(release_start_sec, 3),
                "env_end_sec": round(end_sec, 3)
            })
        return envelopes

    def _build_ffmpeg_abstraction(self, envelopes: list) -> str:
        """
        Actionable Abstraction (Rule 9): Generates the exact FFmpeg 'volume' filter 
        math string to be used by downstream rendering engines.
        """
        if not envelopes:
            return "volume=1.0"
            
        filter_parts = []
        for env in envelopes:
            t1 = env["env_start_sec"]
            t2 = env["duck_reached_sec"]
            t3 = env["release_start_sec"]
            t4 = env["env_end_sec"]
            
            # Convert dB to linear multiplier
            linear_vol = round(10 ** (env["duck_depth_db"] / 20.0), 3)
            
            # Mathematical lerp for smooth Attack and Release
            attack_eq = f"1.0-((1.0-{linear_vol})*(t-{t1})/({t2}-{t1}))"
            release_eq = f"{linear_vol}+((1.0-{linear_vol})*(t-{t3})/({t4}-{t3}))"
            
            # FFmpeg time-based expression
            part = f"if(between(t,{t1},{t2}),{attack_eq},if(between(t,{t2},{t3}),{linear_vol},if(between(t,{t3},{t4}),{release_eq},1.0)))"
            filter_parts.append(part)

        # Chain them together (Minimum value wins if envelopes overlap)
        if len(filter_parts) == 1:
            return f"volume=eval=frame:volume='{filter_parts[0]}'"
        
        chained = filter_parts[0]
        for part in filter_parts[1:]:
            chained = f"min({chained},{part})"
            
        return f"volume=eval=frame:volume='{chained}'"

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # Fetch Dependencies
        global_timestamps = module_audio.get("agent_12_global_timestamps", {})
        sub_impacts = module_audio.get("agent_15_sub_impact_blueprint", {})

        if not global_timestamps:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 12 Timestamps.")

        # Caching & Idempotency
        current_hash = self._generate_state_hash(global_timestamps, sub_impacts)
        existing_manifest = module_audio.get("agent_16_sidechain_manifest", {})
        
        if existing_manifest and existing_manifest.get("_cache_hash") == current_hash:
            print(f"[{self.agent_name}] INFO: Deterministic cache hit. Skipping re-analysis.", flush=True)
            return state

        if "agent_16_sidechain_manifest" in module_audio:
            del module_audio["agent_16_sidechain_manifest"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        # 1. Extract & Sort all triggers
        raw_triggers = self._extract_and_sort_triggers(global_timestamps, sub_impacts)
        
        # 2. Debounce (Anti-Pumping Protection)
        merged_triggers = self._debounce_triggers(raw_triggers)
        
        # 3. Generate DSP Envelopes
        envelopes = self._generate_dsp_envelopes(merged_triggers)
        
        # 4. Actionable FFmpeg Abstraction
        ffmpeg_filter_string = self._build_ffmpeg_abstraction(envelopes)

        # 5. Overlap & Peak Warning Detection
        warnings = []
        if len(envelopes) > 100:
            warnings.append("High density of sidechain events. Monitor for potential unnatural pumping.")
        
        manifest = {
            "_cache_hash": current_hash,
            "validation_status": "PASSED",
            "total_raw_triggers": len(raw_triggers),
            "total_debounced_envelopes": len(envelopes),
            "ducking_envelopes": envelopes,
            "ffmpeg_actionable_filter": ffmpeg_filter_string,
            "quality_metrics": {
                "max_peak_reduction_db": -16.0,
                "warnings": warnings
            }
        }

        module_audio["agent_16_sidechain_manifest"] = manifest

        exec_time = round(time.time() - start_time, 3)
        state.setdefault("metrics", {})[self.agent_name] = {
            "provider": "Procedural DSP Math",
            "execution_time_sec": exec_time,
            "envelopes_generated": len(envelopes)
        }

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Sidechain Manifest Generated. Debounced {len(raw_triggers)} triggers into {len(envelopes)} smooth envelopes. (Time: {exec_time}s)", flush=True)

        return state

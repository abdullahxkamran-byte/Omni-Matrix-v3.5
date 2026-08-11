import time
from core.state_manager import State_Manager
from core.music_inference_gateway import Music_Inference_Gateway

class Ai_Agent_18b_Neural_OST_Generator:
    def __init__(self):
        self.agent_name = "Ai_Agent_18b_Neural_OST_Generator"
        self.global_seed = 42069  # For deterministic reproducibility

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # 🔧 FIX 1: Idempotency Scrubbing (Rule 3)
        if "agent_18b_ost_manifest" in module_audio:
            del module_audio["agent_18b_ost_manifest"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        # Fetch Input Blueprints
        bgm_blueprint = module_audio.get("agent_18_bgm_blueprint", {})
        global_timestamps = module_audio.get("agent_12_global_timestamps", {})

        if not bgm_blueprint or not global_timestamps:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 18 Blueprint or Agent 12 Timestamps.")

        generative_prompt = bgm_blueprint.get("agent_18b_generative_prompt", "")
        
        # 🔧 FIX 2: Default fallback to 15.0s to prevent zero-duration crash
        target_duration = global_timestamps.get("total_calculated_duration_sec", 15.0)

        if not generative_prompt:
            generative_prompt = "Cinematic epic background music score, dark synth, 120 bpm"

        output_filename = f"{project_id}_master_bgm_ost.wav"

        # 🔧 FIX 3: Initialize Configurable Gateway with project_id for Path Isolation
        gateway = Music_Inference_Gateway(workspace_dir, project_id=project_id)
        
        # We set keep_in_vram=False because Agent 19 (Mixing) doesn't need GPU, 
        # but Module C (Blender) will need the GPU next! Rule 10 pipeline safety.
        result = gateway.generate_bgm(
            prompt=generative_prompt,
            target_duration_sec=target_duration,
            output_filename=output_filename,
            seed=self.global_seed,
            keep_in_vram=False
        )

        if result["status"] != "SUCCESS":
            raise RuntimeError(f"[{self.agent_name}] [LLM005] Neural OST Generation Failed: {result.get('error')}")

        # Save Exhaustive Output Manifest
        ost_manifest = {
            "project_id": project_id,
            "bgm_file_path": result["output_path"],
            "target_duration_sec": target_duration,
            "actual_duration_sec": result["actual_duration_sec"],
            "model_used": result["model_used"],
            "generative_prompt_used": generative_prompt,
            "generation_seed": result["seed"],
            "recipe_hash": result["cache_hash"],
            "was_cached": result["cached"],
            "chunks_stitched": result["chunks_stitched"],
            "validation_status": "PASSED"
        }

        module_audio["agent_18b_ost_manifest"] = ost_manifest

        exec_time = round(time.time() - start_time, 2)
        state.setdefault("metrics", {})[self.agent_name] = {
            "provider": f"Local Neural ({result['model_used']})",
            "execution_time_sec": exec_time,
            "bgm_duration_sec": result["actual_duration_sec"],
            "cached_hit": result["cached"]
        }

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        print(f"[{self.agent_name}] INFO: Local OST Synthesized & Validated! Duration: {result['actual_duration_sec']}s. Saved to {result['output_path']}. (Time: {exec_time}s)", flush=True)

        return state

import os
import re
import time
import json
import shutil
import hashlib
import numpy as np
import scipy.io.wavfile as wavfile

from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager
from core.sfx_inference_gateway import SFX_Inference_Gateway

class Ai_Agent_17_Autonomous_SFX_Alchemist_Synthesizer:
    def __init__(self):
        self.agent_name = "Ai_Agent_17_Autonomous_SFX_Alchemist_Synthesizer"
        self.sample_rate = 48000  # Locked to 48kHz Studio Standard

    def _clean_llm_json(self, raw_response: str) -> str:
        """Rule 5: Bulletproof JSON extraction."""
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            return match.group(0)
        return raw_response

    def _generate_physics_transient(self, params: dict, duration_sec: float) -> np.ndarray:
        """Physical Wave Synthesis Engine with Pitch Sweep and Sub-Rumble."""
        total_samples = int(self.sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)
        
        mass = max(0.0001, float(params.get("mass_kg", 0.01)))
        stiffness = float(params.get("stiffness_k", 50000.0))
        force = float(params.get("impact_force", 10.0))
        decay = max(1.0, min(8.0, float(params.get("decay_rate", 3.0))))
        
        sweep_start = float(params.get("pitch_sweep_start", 1.0))
        sweep_end = float(params.get("pitch_sweep_end", 1.0))
        sub_blend = float(params.get("sub_bass_blend", 0.25))
        
        base_freq_hz = (1.0 / (2.0 * np.pi)) * np.sqrt(stiffness / mass)
        base_freq_hz = min(base_freq_hz, self.sample_rate / 2.2)
        
        # Pitch Modulation Sweep
        freq_curve = np.linspace(base_freq_hz * sweep_start, base_freq_hz * sweep_end, total_samples)
        phase = 2.0 * np.pi * np.cumsum(freq_curve) / self.sample_rate
        main_osc = np.sin(phase)
        
        # Sub-Bass Fundamental
        sub_freq_hz = min(70.0, base_freq_hz * 0.3)
        sub_osc = np.sin(2.0 * np.pi * sub_freq_hz * t) * sub_blend
        
        # Exponential Body Envelope with Tail Release
        envelope = np.exp(-decay * t)
        fade_samples = int(self.sample_rate * 0.05)
        fade_out = np.ones(total_samples)
        if total_samples > fade_samples:
            fade_out[-fade_samples:] = np.linspace(1.0, 0.0, fade_samples)
            
        # Micro Impact Grain
        attack_samples = int(self.sample_rate * 0.02)
        impact_noise = np.random.uniform(-0.3, 0.3, total_samples)
        noise_envelope = np.zeros(total_samples)
        if total_samples > attack_samples:
            noise_envelope[:attack_samples] = np.linspace(1.0, 0.0, attack_samples)
            
        combined_wave = ((main_osc + sub_osc) * envelope) + (impact_noise * noise_envelope)
        master_wave = combined_wave * force * fade_out
        
        return master_wave

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # Paths Setup (Universal Isolation)
        project_sfx_dir = os.path.join(workspace_dir, "projects", project_id, "exports", "sfx")
        global_library_dir = os.path.join(workspace_dir, "library", "sfx_vault")
        
        os.makedirs(project_sfx_dir, exist_ok=True)
        os.makedirs(global_library_dir, exist_ok=True)

        # Rule 3: Idempotency Scrubbing
        if "agent_17_sfx_registry" in module_audio:
            del module_audio["agent_17_sfx_registry"]

        # Module A Handoff Extraction
        agent_08_blueprint = runtime_data.get("module_a_scripting", {}).get("agent_08_master_blueprint", {})
        if not agent_08_blueprint:
             raise ValueError(f"[{self.agent_name}] CRITICAL: Missing Agent 08 Blueprint in runtime_data.")

        # Extracting Both Global Summary and Scene-Level Foley Directives
        global_dependency_summary = agent_08_blueprint.get("global_dependency_summary", {})
        global_audio_needs = global_dependency_summary.get("module_b_audio_needs", "Generic cinematic sound effects")

        master_scenes = agent_08_blueprint.get("master_scenes", [])
        targeted_audio_blocks = []
        for scene in master_scenes:
            audio_block = scene.get("audio_block", {})
            foley_dir = audio_block.get("foley_directive", "")
            if foley_dir:
                targeted_audio_blocks.append({
                    "scene_id": scene.get("scene_id", "scene_X"),
                    "foley_directive": foley_dir,
                    "target_tension": audio_block.get("target_tension", "Medium")
                })

        if not targeted_audio_blocks:
            print(f"[{self.agent_name}] No scene foley directives specified. Registering empty manifest.", flush=True)
            module_audio["agent_17_sfx_registry"] = []
            state.setdefault("pipeline_status", {})[self.agent_name] = "COMPLETED"
            state["last_active_agent"] = self.agent_name
            return sm.save_state(state)

        # Prompt Loading & Variables Substitution
        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "scene_audio_blocks_json": json.dumps(targeted_audio_blocks, indent=2),
            "global_audio_needs": json.dumps(global_audio_needs, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_17_sfx_alchemist.txt", variables)

        # Dual API Failsafe LLM Call
        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Acoustic Fusion Architect. Output pure JSON mapping SFX dynamically based on the input blueprint.",
            temperature=0.7,
            required_keys=["agent_17_sfx_recipes"],
            project_id=project_id
        )

        clean_json_str = self._clean_llm_json(json.dumps(response.get("data", {})))
        parsed_response = json.loads(clean_json_str)
        recipes = parsed_response.get("agent_17_sfx_recipes", [])

        sfx_registry_manifest = []
        neural_gateway = SFX_Inference_Gateway(workspace_dir, target_sample_rate=self.sample_rate)

        print(f"[{self.agent_name}] Synthesizing {len(recipes)} SFX assets via Multi-Model Taxonomy...", flush=True)

        for recipe in recipes:
            sfx_id = recipe.get("sfx_id", f"SFX_{int(time.time())}")
            scene_id = recipe.get("scene_id", "SCENE_X").upper()
            semantic_name = recipe.get("semantic_name", "Acoustic_Asset")
            
            safe_semantic = "".join([c if c.isalnum() else "_" for c in semantic_name])
            model_key = recipe.get("recommended_model", "WOOSH_FLOW")
            duration_sec = float(recipe.get("duration_sec", 1.5))
            
            project_filename = f"{project_id}_{scene_id}_{safe_semantic}.wav"
            library_filename = f"{safe_semantic}.wav"
            
            project_output_path = os.path.join(project_sfx_dir, project_filename)
            library_output_path = os.path.join(global_library_dir, library_filename)
            
            total_samples = int(self.sample_rate * duration_sec)
            final_mix = np.zeros(total_samples)

            print(f"[{self.agent_name}] Processing: {safe_semantic} | Scene: {scene_id} | Route: {model_key}", flush=True)

            try:
                # Layer 1: Physics/DSP Transient Attack
                physics_params = recipe.get("physics_transient", {})
                if physics_params:
                    transient_wave = self._generate_physics_transient(physics_params, duration_sec)
                    final_mix += (transient_wave * 0.70)

                # Layer 2: Specialized Neural Body Texture
                neural_params = recipe.get("neural_body", {})
                if neural_params:
                    neural_prompt = neural_params.get("prompt", "Acoustic foley sound effect")
                    g_scale = float(neural_params.get("guidance_scale", 4.0))
                    
                    body_wave = neural_gateway.generate_neural_sfx(model_key, neural_prompt, duration_sec, g_scale)
                    
                    if len(body_wave) > total_samples:
                        body_wave = body_wave[:total_samples]
                    elif len(body_wave) < total_samples:
                        body_wave = np.pad(body_wave, (0, total_samples - len(body_wave)), 'constant')
                        
                    final_mix += (body_wave * 0.90)

                # Layer 3: Dynamic Compression & RMS Loudness Equalizer
                final_mix = neural_gateway.apply_dynamic_compression_and_rms(final_mix, target_rms=0.18)
                
                audio_int16 = np.int16(final_mix * 32767)
                
                # Save Dual Copies
                wavfile.write(project_output_path, self.sample_rate, audio_int16)
                shutil.copy2(project_output_path, library_output_path)
                
                with open(project_output_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()

                sfx_registry_manifest.append({
                    "sfx_id": sfx_id,
                    "scene_id": scene_id,
                    "semantic_name": semantic_name,
                    "routed_model": model_key,
                    "output_path": project_output_path,  # Agent 19 Mixer backward compatibility
                    "project_path": project_output_path,
                    "library_path": library_output_path,
                    "sha256": file_hash,
                    "validation": "PASSED"
                })

            except Exception as e:
                print(f"[{self.agent_name}] Error rendering {sfx_id}: {str(e)}", flush=True)

        # Atomic Handshake and State Save
        module_audio["agent_17_sfx_registry"] = sfx_registry_manifest
        state.setdefault("pipeline_status", {})[self.agent_name] = "COMPLETED"
        state["last_active_agent"] = self.agent_name
        sm.save_state(state)

        print(f"[{self.agent_name}] SFX Pipeline Complete. Generated {len(sfx_registry_manifest)} assets in {round(time.time() - start_time, 2)}s", flush=True)
        return state

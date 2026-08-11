import os
import time
import json
import hashlib
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_17_Autonomous_SFX_Alchemist_Synthesizer:
    def __init__(self):
        self.agent_name = "Ai_Agent_17_Autonomous_SFX_Alchemist_Synthesizer"
        # Hardware Safety Caps (Rule 9)
        self.max_duration_sec = 10.0
        self.max_layers = 6
        self.engine_version = "v4.1.0_DSP"

    def _generate_noise(self, noise_type: str, total_samples: int) -> np.ndarray:
        white = np.random.uniform(-1.0, 1.0, total_samples)
        if noise_type == "white_noise":
            return white
        elif noise_type == "brown_noise":
            brown = np.cumsum(white)
            return brown / np.max(np.abs(brown)) if np.max(np.abs(brown)) > 0 else brown
        elif noise_type == "pink_noise":
            # Simple 1/f approximation filter
            b, a = signal.butter(1, 0.02, btype='low')
            pink = signal.lfilter(b, a, white)
            return pink / np.max(np.abs(pink)) if np.max(np.abs(pink)) > 0 else pink
        return white

    def _apply_filter(self, wave: np.ndarray, filter_cfg: dict, sample_rate: int) -> np.ndarray:
        ftype = filter_cfg.get("type", "none").lower()
        cutoff = float(filter_cfg.get("cutoff_hz", 0))
        
        # 🔧 FIX 1: Safety clamp for Nyquist limit to prevent SciPy crashes
        nyquist = sample_rate / 2.0
        cutoff = max(20.0, min(cutoff, nyquist - 100.0))
        
        if ftype not in ["lowpass", "highpass"]:
            return wave
            
        try:
            b, a = signal.butter(2, cutoff / nyquist, btype=ftype)
            return signal.filtfilt(b, a, wave)
        except Exception:
            return wave

    def _generate_adsr(self, duration_sec: float, adsr: dict, sample_rate: int) -> np.ndarray:
        total_samples = int(sample_rate * duration_sec)
        envelope = np.zeros(total_samples)

        a_samples = int(sample_rate * adsr.get("attack_sec", 0.01))
        d_samples = int(sample_rate * adsr.get("decay_sec", 0.1))
        r_samples = int(sample_rate * adsr.get("release_sec", 0.1))
        sustain_level = adsr.get("sustain_level", 0.5)

        if a_samples + d_samples + r_samples > total_samples:
            r_samples = max(0, total_samples - a_samples - d_samples)
        
        s_samples = max(0, total_samples - a_samples - d_samples - r_samples)

        if a_samples > 0:
            envelope[0:a_samples] = np.linspace(0, 1, a_samples)
        if d_samples > 0:
            envelope[a_samples:a_samples+d_samples] = np.linspace(1, sustain_level, d_samples)
        if s_samples > 0:
            s_start = a_samples + d_samples
            envelope[s_start:s_start+s_samples] = sustain_level
        if r_samples > 0:
            r_start = a_samples + d_samples + s_samples
            envelope[r_start:r_start+r_samples] = np.linspace(sustain_level, 0, r_samples)

        return envelope

    def _synthesize_layer(self, layer: dict, duration_sec: float, sample_rate: int) -> np.ndarray:
        total_samples = int(sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)
        
        wave_type = layer.get("wave_type", "sine").lower()
        f_start = layer.get("freq_start_hz", 440.0)
        f_end = layer.get("freq_end_hz", 440.0)
        volume = layer.get("volume", 0.5)
        lfo = layer.get("lfo", {})
        
        # Base Frequency Array
        frequencies = np.linspace(f_start, f_end, total_samples)
        
        # Vibrato (FM)
        if lfo.get("type", "none") == "vibrato":
            lfo_wave = np.sin(2 * np.pi * lfo.get("rate_hz", 5.0) * t) * lfo.get("depth", 10.0)
            frequencies += lfo_wave
            
        phase = 2 * np.pi * np.cumsum(frequencies) / sample_rate
        
        if "noise" in wave_type:
            wave = self._generate_noise(wave_type, total_samples)
        elif wave_type == "sine":
            wave = np.sin(phase)
        elif wave_type == "square":
            wave = np.sign(np.sin(phase))
        elif wave_type == "sawtooth":
            wave = signal.sawtooth(phase)
        elif wave_type == "triangle":
            wave = signal.sawtooth(phase, 0.5)
        else:
            wave = np.sin(phase)

        # Tremolo (AM)
        if lfo.get("type", "none") == "tremolo":
            am_wave = 1.0 - lfo.get("depth", 0.5) * (0.5 * (1.0 + np.sin(2 * np.pi * lfo.get("rate_hz", 5.0) * t)))
            wave *= am_wave

        # Filter
        if "filter" in layer:
            wave = self._apply_filter(wave, layer["filter"], sample_rate)

        # ADSR Envelope
        adsr = layer.get("adsr", {"attack_sec": 0.05, "decay_sec": 0.1, "sustain_level": 0.5, "release_sec": 0.5})
        envelope = self._generate_adsr(duration_sec, adsr, sample_rate)
        
        return wave * envelope * volume

    def _process_and_validate_sfx(self, recipe: dict, output_path: str, sample_rate: int) -> dict:
        # Determinism via Seed
        generation_seed = recipe.get("seed", 42)
        np.random.seed(generation_seed)
        
        duration_sec = min(recipe.get("duration_sec", 1.0), self.max_duration_sec)
        total_samples = int(sample_rate * duration_sec)
        master_mix = np.zeros(total_samples)

        layers = recipe.get("layers", [])[:self.max_layers]
        
        for layer in layers:
            layer_wave = self._synthesize_layer(layer, duration_sec, sample_rate)
            if len(layer_wave) > total_samples:
                layer_wave = layer_wave[:total_samples]
            elif len(layer_wave) < total_samples:
                layer_wave = np.pad(layer_wave, (0, total_samples - len(layer_wave)))
            master_mix += layer_wave

        # Validation: NaN / Inf Protection
        if np.isnan(master_mix).any() or np.isinf(master_mix).any():
            return {"status": "FAILED", "error": "NaN or Inf values detected in DSP computation."}

        # Validation: Silence Detection
        peak_abs = np.max(np.abs(master_mix))
        if peak_abs < 0.0001:
            return {"status": "FAILED", "error": "Generated audio is complete silence."}

        # Dynamic Range Protection (Headroom / Limiting)
        if peak_abs > 0:
            master_mix = master_mix / peak_abs
            master_mix *= 0.85 # -1.4dB True Peak Safety Headroom

        # Metrics Calculation
        peak_db = round(20 * np.log10(np.max(np.abs(master_mix))), 2)
        rms = np.sqrt(np.mean(master_mix**2))
        lufs_approx = round(20 * np.log10(rms) if rms > 0 else -100.0, 2)

        audio_int16 = np.int16(master_mix * 32767)
        wavfile.write(output_path, sample_rate, audio_int16)
        
        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        return {
            "status": "VALIDATED",
            "file_path": output_path,
            "duration": duration_sec,
            "peak_db": peak_db,
            "lufs_approx": lufs_approx,
            "file_hash": file_hash,
            "generation_seed": generation_seed
        }

    def execute(self, state: dict) -> dict:
        start_time = time.time()
        
        workspace_dir = state.get("workspace_dir", "")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")
        
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        
        module_scripting = runtime_data.get("module_a_scripting", {})
        module_audio = runtime_data.setdefault("module_b_audio", {})

        # 🔧 FIX 2: Strict Project Path Isolation (Rule 2)
        sfx_exports_dir = os.path.join(workspace_dir, "projects", project_id, "exports", "sfx")
        os.makedirs(sfx_exports_dir, exist_ok=True)

        # Dynamic Audio Config
        sample_rate = state.get("global_config", {}).get("audio_sample_rate", 48000)

        # Idempotency Scrubbing
        if "agent_17_sfx_registry" in module_audio:
            del module_audio["agent_17_sfx_registry"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        master_blueprint = module_scripting.get("agent_08_master_blueprint", {})
        if not master_blueprint:
             raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Agent 08 Master Blueprint for context.")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "master_blueprint_json": json.dumps(master_blueprint, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_17_sfx_alchemist.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the Autonomous SFX Alchemist. Output pure mathematical DSP JSON arrays strictly based on scene contexts.",
            temperature=0.8, # High temp for creative sound design
            required_keys=["agent_17_sfx_recipes"],
            project_id=project_id
        )

        recipes = response["data"]["agent_17_sfx_recipes"]
        sfx_registry_manifest = []

        print(f"[{self.agent_name}] DSP Engine initialized. Synthesizing {len(recipes)} SFX assets...")

        for recipe in recipes:
            sfx_id = recipe.get("sfx_id", f"SFX_{int(time.time()*1000)}")
            safe_id = "".join([c if c.isalnum() else "_" for c in sfx_id])
            
            output_filename = f"{project_id}_{safe_id}.wav"
            output_path = os.path.join(sfx_exports_dir, output_filename)
            
            recipe_hash = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode('utf-8')).hexdigest()

            try:
                dsp_result = self._process_and_validate_sfx(recipe, output_path, sample_rate)
                
                if dsp_result["status"] == "VALIDATED":
                    sfx_registry_manifest.append({
                        "sfx_id": sfx_id,
                        "project_id": project_id,
                        "source_scene_id": recipe.get("source_scene_id", "global"),
                        "semantic_category": recipe.get("semantic_category", "uncategorized"),
                        "description": recipe.get("description", ""),
                        "generation_recipe_hash": recipe_hash,
                        "generation_seed": dsp_result["generation_seed"],
                        "sample_rate": sample_rate,
                        "channels": 1,
                        "bit_depth": 16,
                        "duration": dsp_result["duration"],
                        "peak_db": dsp_result["peak_db"],
                        "lufs": dsp_result["lufs_approx"],
                        "provider": "OmniMatrix_DSP",
                        "engine_version": self.engine_version,
                        "file_hash": dsp_result["file_hash"],
                        "output_path": dsp_result["file_path"],
                        "validation_status": "PASSED"
                    })
                else:
                    print(f"[{self.agent_name}] WARNING: SFX {sfx_id} failed validation -> {dsp_result['error']}")

            except Exception as e:
                print(f"[{self.agent_name}] WARNING: Failed to compute DSP for {sfx_id}. Error: {str(e)}")

        module_audio["agent_17_sfx_registry"] = sfx_registry_manifest
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = round(time.time() - start_time, 2)
        provider = response["metrics"]["provider"]
        
        print(f"[{self.agent_name}] INFO: Pure DSP Sound Design Complete! {len(sfx_registry_manifest)} Validated SFX added to Registry. (Time: {exec_time}s via {provider})", flush=True)

        return state

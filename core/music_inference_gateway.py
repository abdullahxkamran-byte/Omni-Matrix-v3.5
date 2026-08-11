import os
import time
import math
import hashlib
import json
import torch
import numpy as np
import scipy.io.wavfile as wavfile

class Music_Inference_Gateway:
    # 🔧 FIX 1: Added project_id for strict path isolation
    def __init__(self, workspace_dir: str, project_id: str = "DEFAULT_PROJECT"):
        self.workspace_dir = workspace_dir
        self.project_id = project_id
        
        # 🔧 FIX 1: Path isolated exactly to the project
        self.bgm_exports_dir = os.path.join(self.workspace_dir, "projects", self.project_id, "exports", "audio")
        os.makedirs(self.bgm_exports_dir, exist_ok=True)
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.model_name = "facebook/musicgen-medium"
        self.fallback_model_name = "facebook/musicgen-small"
        self.sample_rate = 32000 # Native MusicGen sample rate
        
        # 🔧 FIX 2: Exact tokens per second for MusicGen (50 instead of 256)
        self.frame_rate = 50 

    def _generate_cache_hash(self, prompt: str, duration: float, seed: int) -> str:
        """Generates deterministic cache key to prevent redundant heavy VRAM usage."""
        raw = f"{prompt}|{duration}|{seed}|{self.model_name}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    def _load_model(self):
        """Loads model safely with OutOfMemory detection and proper fallbacks."""
        if self.model is not None:
            return

        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        print(f"[Music_Inference_Gateway] Loading {self.model_name} on {self.device}...", flush=True)
        try:
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = MusicgenForConditionalGeneration.from_pretrained(self.model_name).to(self.device)
            # Optimize for inference
            self.model.eval()
        except Exception as e: # 🔧 FIX 3: Catch all exceptions to guarantee fallback trigger
            print(f"[Music_Inference_Gateway] VRAM/Load Error on {self.model_name}: {str(e)}. Falling back to small model...", flush=True)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.model_name = self.fallback_model_name
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = MusicgenForConditionalGeneration.from_pretrained(self.model_name).to(self.device)
            self.model.eval()

    def unload_model(self, force: bool = False):
        """Configurable model unloading. Keeps model in RAM for batch processing if force=False."""
        if force and self.model is not None:
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[Music_Inference_Gateway] VRAM Force Cleared.", flush=True)

    def _crossfade_chunks(self, chunks: list, overlap_sec: float = 3.0) -> np.ndarray:
        """Mathematically safe stitching with overlap limits."""
        if not chunks:
            return np.array([])
        if len(chunks) == 1:
            return chunks[0]

        overlap_samples = int(self.sample_rate * overlap_sec)
        combined = chunks[0]

        for next_chunk in chunks[1:]:
            # Safety: If chunk is smaller than expected overlap, adjust overlap
            safe_overlap = min(overlap_samples, len(combined), len(next_chunk))
            if safe_overlap <= 0:
                combined = np.concatenate([combined, next_chunk])
                continue

            fade_in = np.linspace(0, 1, safe_overlap)
            fade_out = np.linspace(1, 0, safe_overlap)

            tail = combined[-safe_overlap:] * fade_out
            head = next_chunk[:safe_overlap] * fade_in
            blended = tail + head

            combined = np.concatenate([combined[:-safe_overlap], blended, next_chunk[safe_overlap:]])

        return combined

    def generate_bgm(self, prompt: str, target_duration_sec: float, output_filename: str, seed: int = 42, keep_in_vram: bool = False) -> dict:
        start_time = time.time()
        
        # 1. Target Duration Validation
        if not isinstance(target_duration_sec, (int, float)) or math.isnan(target_duration_sec) or target_duration_sec <= 0:
            return {"status": "FAILED", "error": "Invalid target duration."}

        output_path = os.path.join(self.bgm_exports_dir, output_filename)
        cache_hash = self._generate_cache_hash(prompt, target_duration_sec, seed)

        # 2. Caching Verification
        if os.path.exists(output_path):
            try:
                sr, existing_audio = wavfile.read(output_path)
                existing_dur = len(existing_audio) / sr
                if abs(existing_dur - target_duration_sec) < 1.0 and sr == self.sample_rate:
                    print("[Music_Inference_Gateway] Valid cached audio found. Skipping inference.", flush=True)
                    return {
                        "status": "SUCCESS", "output_path": output_path, "actual_duration_sec": existing_dur,
                        "model_used": self.model_name, "execution_time_sec": 0.0, "seed": seed, "cache_hash": cache_hash, "cached": True
                    }
            except Exception:
                pass # Invalid file, regenerate

        # 3. Resource Planning & Initialization
        # 🔧 FIX 4: Clamp max_chunk_sec to 20s to ensure tokens NEVER hit 1500 CUDA limit
        max_chunk_sec = min(20.0, target_duration_sec)
        audio_prompt_overlap_sec = 3.0 # Use 3s of previous chunk to maintain musical continuity
        
        effective_chunk = max_chunk_sec - audio_prompt_overlap_sec
        if effective_chunk <= 0: effective_chunk = max_chunk_sec
        
        if target_duration_sec <= max_chunk_sec:
            num_chunks = 1
        else:
            num_chunks = max(1, math.ceil((target_duration_sec - max_chunk_sec) / effective_chunk) + 1)
        
        self._load_model()
        torch.manual_seed(seed)
        np.random.seed(seed)

        audio_chunks = []
        last_audio_tensor = None

        try:
            with torch.inference_mode(): # Faster, less memory than no_grad
                for c in range(num_chunks):
                    print(f"[Music_Inference_Gateway] Generating Chunk {c+1}/{num_chunks} (Musical Continuity Active)...", flush=True)
                    
                    # Musical Continuity: Pass the last 3s of previous chunk as audio_prompt
                    if c == 0 or last_audio_tensor is None:
                        inputs = self.processor(text=[prompt], padding=True, return_tensors="pt").to(self.device)
                        chunk_len = min(max_chunk_sec, target_duration_sec)
                    else:
                        overlap_samples = int(self.sample_rate * audio_prompt_overlap_sec)
                        prompt_audio = last_audio_tensor[-overlap_samples:]
                        inputs = self.processor(text=[prompt], audio=prompt_audio, sampling_rate=self.sample_rate, padding=True, return_tensors="pt").to(self.device)
                        
                        remaining_sec = target_duration_sec - (c * effective_chunk)
                        chunk_len = min(max_chunk_sec, remaining_sec + audio_prompt_overlap_sec)

                    # 🔧 FIX 5: Exact token math + Safety Clamp (Max 1200 tokens guaranteed)
                    new_tokens = int(self.frame_rate * chunk_len)
                    max_new_tokens = min(1200, max(50, new_tokens))
                    
                    audio_tokens = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, guidance_scale=3.0)
                    chunk_audio_np = audio_tokens[0, 0].cpu().numpy()
                    
                    audio_chunks.append(chunk_audio_np)
                    last_audio_tensor = torch.tensor(chunk_audio_np, dtype=torch.float32)

            # 4. Assembly & Stitching
            full_audio = self._crossfade_chunks(audio_chunks, overlap_sec=audio_prompt_overlap_sec)

            # 5. Trim to Exact Target Duration
            target_samples = int(self.sample_rate * target_duration_sec)
            if len(full_audio) > target_samples:
                full_audio = full_audio[:target_samples]
            elif len(full_audio) < target_samples:
                # Pad with silence if slightly short (rare edge case)
                full_audio = np.pad(full_audio, (0, target_samples - len(full_audio)))

            # 6. Safety & Normalization (-1.5dB Headroom)
            if np.isnan(full_audio).any() or np.isinf(full_audio).any():
                raise ValueError("Corrupt audio generated (NaN/Inf detected).")

            peak = np.max(np.abs(full_audio))
            if peak > 0:
                full_audio = (full_audio / peak) * 0.84

            # 7. Write to Disk
            audio_int16 = np.int16(full_audio * 32767)
            wavfile.write(output_path, self.sample_rate, audio_int16)

            # 8. Output Validation
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise IOError("Audio file failed to write properly.")

            exec_time = round(time.time() - start_time, 2)

            return {
                "status": "SUCCESS",
                "output_path": output_path,
                "actual_duration_sec": target_duration_sec,
                "model_used": self.model_name,
                "execution_time_sec": exec_time,
                "chunks_stitched": num_chunks,
                "seed": seed,
                "cache_hash": cache_hash,
                "cached": False
            }

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

        finally:
            if not keep_in_vram:
                self.unload_model(force=True)

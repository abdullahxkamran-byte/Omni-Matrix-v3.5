import os
import torch
import numpy as np
import warnings
import diffusers.utils.logging as diffusers_logging

# Suppress HuggingFace verbose logs and deprecations
warnings.filterwarnings("ignore")
diffusers_logging.set_verbosity_error()

class SFX_Inference_Gateway:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = None
        self.model_id = "cvssp/audioldm-s-full-v2"

    def _load_model(self):
        if self.pipe is not None:
            return
        
        try:
            from diffusers import AudioLDMPipeline
            print(f"[SFX_Gateway] Loading Stable AudioLDM Pipeline ({self.model_id}) on {self.device}...", flush=True)
            
            self.pipe = AudioLDMPipeline.from_pretrained(
                self.model_id, 
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            
        except Exception as e:
            print(f"[SFX_Gateway] FAILED to load neural model: {str(e)}", flush=True)
            raise e

    def _unload_model(self):
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[SFX_Gateway] VRAM Cleared successfully.", flush=True)

    def generate_neural_sfx(self, prompt: str, duration_sec: float, guidance_scale: float = 3.5, seed: int = 42) -> np.ndarray:
        self._load_model()
        generator = torch.Generator(device=self.device).manual_seed(seed)
        
        print(f"[SFX_Gateway] Synthesizing Neural Body Texture: '{prompt}'", flush=True)
        
        try:
            with torch.inference_mode():
                audio = self.pipe(
                    prompt=prompt,
                    audio_length_in_s=duration_sec,
                    num_inference_steps=35,
                    guidance_scale=guidance_scale,
                    generator=generator
                ).audios[0]
            
            return audio
            
        except Exception as e:
            print(f"[SFX_Gateway] Generation FAILED: {str(e)}", flush=True)
            return np.zeros(int(16000 * duration_sec))
            
        finally:
            self._unload_model()

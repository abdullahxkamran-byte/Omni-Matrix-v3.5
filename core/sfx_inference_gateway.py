import os
import gc
import torch
import warnings
import numpy as np
import scipy.io.wavfile as wavfile
import diffusers.utils.logging as diffusers_logging

warnings.filterwarnings("ignore")
diffusers_logging.set_verbosity_error()

class SFX_Inference_Gateway:
    def __init__(self, workspace_dir: str, target_sample_rate: int = 48000):
        self.workspace_dir = workspace_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.target_sample_rate = target_sample_rate
        self.active_model_id = None
        self.pipe = None
        
        # Model Model Registry Mapping
        self.model_registry = {
            "MOSS_V2": "hexgrad/MOSS-SoundEffect-v2",
            "WOOSH_FLOW": "cvssp/audioldm-s-full-v2",
            "STABLE_AUDIO": "stabilityai/stable-audio-open-1.0",
            "FALLBACK": "cvssp/audioldm-s-full-v2"
        }

    def _load_model(self, model_key: str):
        selected_model_id = self.model_registry.get(model_key, self.model_registry["FALLBACK"])
        
        if self.pipe is not None and self.active_model_id == selected_model_id:
            return
        
        # If another model is currently in VRAM, unload it first
        if self.pipe is not None:
            self._unload_model()

        try:
            print(f"[SFX_Gateway] Loading Neural Model ({model_key} -> {selected_model_id}) on {self.device}...", flush=True)
            
            if "stable-audio" in selected_model_id:
                from diffusers import StableAudioPipeline
                self.pipe = StableAudioPipeline.from_pretrained(
                    selected_model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                ).to(self.device)
            else:
                from diffusers import AudioLDMPipeline
                self.pipe = AudioLDMPipeline.from_pretrained(
                    selected_model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                ).to(self.device)
                
            self.active_model_id = selected_model_id
            
        except Exception as e:
            print(f"[SFX_Gateway] Primary model load failed for {model_key}: {str(e)}. Falling back to AudioLDM.", flush=True)
            try:
                from diffusers import AudioLDMPipeline
                fallback_id = self.model_registry["FALLBACK"]
                self.pipe = AudioLDMPipeline.from_pretrained(
                    fallback_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                ).to(self.device)
                self.active_model_id = fallback_id
            except Exception as fallback_err:
                print(f"[SFX_Gateway] CRITICAL: Fallback model load failed: {str(fallback_err)}", flush=True)
                raise fallback_err

    def _unload_model(self):
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.active_model_id = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[SFX_Gateway] VRAM Scrubbed successfully.", flush=True)

    def _resample_audio(self, audio: np.ndarray, native_sr: int) -> np.ndarray:
        if native_sr == self.target_sample_rate or len(audio) == 0:
            return audio
        
        duration = len(audio) / float(native_sr)
        target_length = int(duration * self.target_sample_rate)
        x_old = np.linspace(0, duration, len(audio), endpoint=False)
        x_new = np.linspace(0, duration, target_length, endpoint=False)
        resampled_audio = np.interp(x_new, x_old, audio)
        return resampled_audio

    def apply_dynamic_compression_and_rms(self, audio: np.ndarray, target_rms: float = 0.18) -> np.ndarray:
        if len(audio) == 0:
            return audio

        # Soft-knee peak compression via hyperbolic tangent
        threshold = 0.4
        abs_audio = np.abs(audio)
        compressed = np.where(
            abs_audio > threshold,
            np.sign(audio) * (threshold + (1.0 - threshold) * np.tanh((abs_audio - threshold) / (1.0 - threshold))),
            audio
        )

        # RMS Normalization
        current_rms = np.sqrt(np.mean(compressed ** 2))
        if current_rms > 0.0001:
            gain = target_rms / current_rms
            audio_boosted = compressed * gain
        else:
            audio_boosted = compressed

        # Peak ceiling guard (-0.9 dBFS)
        peak = np.max(np.abs(audio_boosted))
        if peak > 0.9:
            audio_boosted = (audio_boosted / peak) * 0.90

        return audio_boosted

    def generate_neural_sfx(self, model_key: str, prompt: str, duration_sec: float, guidance_scale: float = 4.0, seed: int = 42) -> np.ndarray:
        self._load_model(model_key)
        generator = torch.Generator(device=self.device).manual_seed(seed)
        native_sr = 16000
        
        print(f"[SFX_Gateway] Synthesizing Neural Texture via [{model_key}]: '{prompt}'", flush=True)
        
        try:
            with torch.inference_mode():
                if "stable-audio" in str(self.active_model_id):
                    native_sr = 44100
                    audio = self.pipe(
                        prompt=prompt,
                        audio_end_in_s=duration_sec,
                        num_inference_steps=50,
                        guidance_scale=guidance_scale,
                        generator=generator
                    ).audios[0].cpu().numpy().squeeze()
                else:
                    native_sr = 16000
                    audio = self.pipe(
                        prompt=prompt,
                        audio_length_in_s=duration_sec,
                        num_inference_steps=35,
                        guidance_scale=guidance_scale,
                        generator=generator
                    ).audios[0]

            # Unify sample rate to 48kHz for Agent 19 Mixer compatibility
            resampled_audio = self._resample_audio(audio, native_sr)
            return resampled_audio

        except Exception as e:
            print(f"[SFX_Gateway] Generation FAILED on {model_key}: {str(e)}", flush=True)
            return np.zeros(int(self.target_sample_rate * duration_sec))
            
        finally:
            self._unload_model()

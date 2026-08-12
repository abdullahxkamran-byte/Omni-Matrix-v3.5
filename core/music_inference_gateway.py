import os
import time
import math
import torch
import numpy as np
import scipy.io.wavfile as wavfile

class Music_Inference_Gateway:
def init(self, workspace_dir: str):
self.workspace_dir = workspace_dir
self.bgm_exports_dir = os.path.join(self.workspace_dir, "exports", "audio")
os.makedirs(self.bgm_exports_dir, exist_ok=True)

self.device = "cuda" if torch.cuda.is_available() else "cpu"  
    self.model = None  
    self.model_name = "facebook/musicgen-medium"  
    self.fallback_model_name = "facebook/musicgen-small"  
    self.sample_rate = 32000 # MusicGen native sample rate  

def _load_model(self):  
    """Lazy loads the MusicGen model onto GPU/CPU on demand."""  
    if self.model is not None:  
        return  

    from transformers import AutoProcessor, MusicgenForConditionalGeneration  

    print(f"[Music_Inference_Gateway] Loading {self.model_name} on {self.device}...", flush=True)  
    try:  
        self.processor = AutoProcessor.from_pretrained(self.model_name)  
        self.model = MusicgenForConditionalGeneration.from_pretrained(self.model_name).to(self.device)  
    except Exception as e:  
        print(f"[Music_Inference_Gateway] VRAM/Load Error on {self.model_name}: {str(e)}. Falling back to small model...", flush=True)  
        self.model_name = self.fallback_model_name  
        self.processor = AutoProcessor.from_pretrained(self.model_name)  
        self.model = MusicgenForConditionalGeneration.from_pretrained(self.model_name).to(self.device)  

def _unload_model(self):  
    """Cleans up GPU VRAM memory after generation to prevent crashes in downstream agents."""  
    if self.model is not None:  
        del self.model  
        del self.processor  
        self.model = None  
        if torch.cuda.is_available():  
            torch.cuda.empty_cache()  
        print("[Music_Inference_Gateway] VRAM Cleared successfully.", flush=True)  

def _crossfade_chunks(self, chunks: list, overlap_sec: float = 2.0) -> np.ndarray:  
    """Stitches multiple 30s audio tensors seamlessly using equal-power crossfading."""  
    if len(chunks) == 1:  
        return chunks[0]  

    overlap_samples = int(self.sample_rate * overlap_sec)  
    fade_in = np.linspace(0, 1, overlap_samples)  
    fade_out = np.linspace(1, 0, overlap_samples)  

    combined = chunks[0]  

    for i in range(1, len(chunks)):  
        next_chunk = chunks[i]  
          
        # Extract overlap regions  
        tail = combined[-overlap_samples:] * fade_out  
        head = next_chunk[:overlap_samples] * fade_in  
        blended = tail + head  

        # Stitch  
        combined = np.concatenate([combined[:-overlap_samples], blended, next_chunk[overlap_samples:]])  

    return combined  

def generate_bgm(self, prompt: str, target_duration_sec: float, output_filename: str) -> dict:  
    start_time = time.time()  
    output_path = os.path.join(self.bgm_exports_dir, output_filename)  

    # 1. Calculate how many 30s chunks are needed  
    chunk_duration = 30.0  
    overlap_sec = 2.0  
    effective_chunk_duration = chunk_duration - overlap_sec  
      
    num_chunks = max(1, math.ceil((target_duration_sec - overlap_sec) / effective_chunk_duration))  

    # 2. Load Model  
    self._load_model()  

    audio_chunks = []  
      
    try:  
        inputs = self.processor(  
            text=[prompt],  
            padding=True,  
            return_tensors="pt"  
        ).to(self.device)  

        max_new_tokens = int(chunk_duration * 50) # ~50 tokens per second for MusicGen  

        for c in range(num_chunks):  
            print(f"[Music_Inference_Gateway] Generating Chunk {c+1}/{num_chunks}...", flush=True)  
              
            with torch.no_grad():  
                audio_tokens = self.model.generate(**inputs, max_new_tokens=max_new_tokens)  
              
            # Extract 1D numpy array  
            audio_data = audio_tokens[0, 0].cpu().numpy()  
            audio_chunks.append(audio_data)  

        # 3. Stitch Chunks Together  
        full_audio = self._crossfade_chunks(audio_chunks, overlap_sec=overlap_sec)  

        # 4. Trim to Exact Target Duration  
        target_samples = int(self.sample_rate * target_duration_sec)  
        if len(full_audio) > target_samples:  
            full_audio = full_audio[:target_samples]  

        # 5. Peak Normalization (-1.5dB Headroom)  
        peak = np.max(np.abs(full_audio))  
        if peak > 0:  
            full_audio = (full_audio / peak) * 0.84  

        # Convert to int16 PCM WAV  
        audio_int16 = np.int16(full_audio * 32767)  
        wavfile.write(output_path, self.sample_rate, audio_int16)  

        exec_time = round(time.time() - start_time, 2)  

        return {  
            "status": "SUCCESS",  
            "output_path": output_path,  
            "actual_duration_sec": round(len(full_audio) / self.sample_rate, 2),  
            "model_used": self.model_name,  
            "execution_time_sec": exec_time,  
            "chunks_stitched": num_chunks  
        }  

    except Exception as e:  
        return {  
            "status": "FAILED",  
            "error": f"MusicGen Inference Failed: {str(e)}"  
        }  

    finally:  
        self._unload_model()
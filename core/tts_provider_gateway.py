import os
import hashlib
import time
import re
import json

from core.tts_providers.elevenlabs_adapter import ElevenLabs_Adapter
from core.tts_providers.google_tts_adapter import Google_TTS_Adapter
from core.tts_providers.azure_tts_adapter import Azure_TTS_Adapter

class TTS_Provider_Gateway:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.audio_exports_dir = os.path.join(self.workspace_dir, "exports", "audio")
        os.makedirs(self.audio_exports_dir, exist_ok=True)
        
        self.adapters = {
            "ElevenLabs": ElevenLabs_Adapter(),
            "Google_TTS": Google_TTS_Adapter(),
            "Azure_TTS": Azure_TTS_Adapter()
        }
        
        self.retry_delays = [2, 4, 8]

    def _sanitize_filename(self, text: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]', '_', text)

    def _generate_cache_hash(self, text: str, provider: str, voice_id: str, provider_model: str, performance_data: dict) -> str:
        raw_string = f"{text}|{provider}|{voice_id}|{provider_model}|{json.dumps(performance_data, sort_keys=True)}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16]

    def generate_voice(self, text: str, registry_entry: dict, performance_data: dict, scene_id: str) -> dict:
        provider = registry_entry.get("provider")
        voice_id = registry_entry.get("voice_id")
        provider_model = registry_entry.get("provider_model", "UNKNOWN")
        
        if provider not in self.adapters:
            return {"status": "FAILED", "error": f"Provider {provider} not registered in gateway."}

        adapter = self.adapters[provider]
        
        safe_scene_id = self._sanitize_filename(scene_id)
        safe_voice_id = self._sanitize_filename(voice_id)
        
        state_hash = self._generate_cache_hash(text, provider, voice_id, provider_model, performance_data)
        filename = f"{safe_scene_id}_{provider}_{safe_voice_id}_{state_hash}.wav"
        output_path = os.path.join(self.audio_exports_dir, filename)

        if os.path.exists(output_path) and adapter.validate_audio_file(output_path):
            actual_duration = adapter.get_actual_duration(output_path)
            return {
                "status": "SUCCESS",
                "provider": provider,
                "voice_id": voice_id,
                "output_path": output_path,
                "actual_duration_sec": actual_duration,
                "generation_settings": {"cached": True, "cache_hash": state_hash}
            }

        retry_count = 0
        max_retries = len(self.retry_delays)
        
        while retry_count < max_retries:
            try:
                actual_duration, gen_settings = adapter.generate(text, registry_entry, output_path, performance_data)
                
                return {
                    "status": "SUCCESS",
                    "provider": provider,
                    "voice_id": voice_id,
                    "output_path": output_path,
                    "actual_duration_sec": actual_duration,
                    "generation_settings": gen_settings,
                    "cache_hash": state_hash
                }
                
            except PermissionError as e:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return {"status": "FAILED", "error": f"Auth Error (No Retry): {str(e)}"}
                
            except ValueError as e:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return {"status": "FAILED", "error": f"Config Error (No Retry): {str(e)}"}
                
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
                time.sleep(self.retry_delays[retry_count])
                retry_count += 1
                
                if retry_count == max_retries:
                    return {"status": "FAILED", "error": f"Max retries reached. Last Error: {str(e)}"}

        return {"status": "FAILED", "error": "Unknown fatal error occurred during orchestration."}

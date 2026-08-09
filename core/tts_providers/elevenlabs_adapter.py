import os
import requests
from core.tts_providers.base_tts_adapter import Base_TTS_Adapter

class ElevenLabs_Adapter(Base_TTS_Adapter):
    def __init__(self):
        super().__init__()
        self.provider_name = "ElevenLabs"
        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

    def get_capabilities(self) -> dict:
        return {
            "languages": ["en", "es", "fr", "de", "hi"],
            "emotion_support": True,
            "speaking_rate_support": False, 
            "ssml_support": False,
            "supported_formats": ["pcm_16000", "mp3_44100_128"]
        }

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def _map_performance_intent(self, performance_data: dict) -> dict:
        emotion_intensity = performance_data.get("line_emotion", {}).get("intensity", "Medium")
        
        stability = 0.5
        similarity = 0.75
        style = 0.0

        if emotion_intensity.lower() == "high":
            stability = 0.3
            style = 0.5
        elif emotion_intensity.lower() == "low":
            stability = 0.8
            similarity = 0.9

        return {
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "use_speaker_boost": True
        }

    def generate(self, text: str, voice_id: str, output_path: str, performance_data: dict) -> tuple:
        if not self.validate_config():
            raise ValueError(f"[{self.provider_name}] API Key missing in environment.")

        url = f"{self.base_url}/{voice_id}?output_format=pcm_16000"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        voice_settings = self._map_performance_intent(performance_data)
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 401:
            raise PermissionError(f"[{self.provider_name}] Authentication failed.")
        elif response.status_code == 429:
            raise ConnectionError(f"[{self.provider_name}] Rate limit exceeded.")
        elif response.status_code != 200:
            raise RuntimeError(f"[{self.provider_name}] API Error: {response.text}")

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        if not self.validate_audio_file(output_path):
            raise RuntimeError(f"[{self.provider_name}] Generated audio is invalid or empty.")

        actual_duration = self.get_actual_duration(output_path)
        
        metadata = {
            "model": "eleven_v3",
            "voice_settings": voice_settings,
            "request_id": response.headers.get("request-id", "unknown")
        }

        return actual_duration, metadata

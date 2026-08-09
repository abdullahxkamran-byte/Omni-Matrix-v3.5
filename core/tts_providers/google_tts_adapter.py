import os
import requests
import base64
from core.tts_providers.base_tts_adapter import Base_TTS_Adapter

class Google_TTS_Adapter(Base_TTS_Adapter):
    def __init__(self):
        super().__init__()
        self.provider_name = "Google_TTS"
        self.api_key = os.environ.get("GOOGLE_TTS_API_KEY", "")
        self.credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def get_capabilities(self) -> dict:
        return {
            "languages": ["dynamic_registry"],
            "emotion_support": False,
            "speaking_rate_support": True, 
            "ssml_support": True,
            "supported_formats": ["LINEAR16", "MP3"]
        }

    def validate_config(self) -> bool:
        return bool(self.api_key or self.credentials_path)

    def _construct_ssml(self, text: str, performance_data: dict) -> str:
        speed = performance_data.get("line_emotion", {}).get("delivery_speed", "Normal").lower()
        rate_map = {"slow": "slow", "normal": "medium", "fast": "fast"}
        prosody_rate = rate_map.get(speed, "medium")
        
        return f"<speak><prosody rate='{prosody_rate}'>{text}</prosody></speak>"

    def generate(self, text: str, registry_entry: dict, output_path: str, performance_data: dict) -> tuple:
        if not self.validate_config():
            raise ValueError(f"[{self.provider_name}] Config missing (Key or OAuth Credentials).")

        voice_id = registry_entry.get("voice_id", "")
        language = registry_entry.get("language", "en-US")
        
        url = self.base_url
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        if self.api_key:
            url = f"{self.base_url}?key={self.api_key}"

        ssml_text = self._construct_ssml(text, performance_data)
        
        payload = {
            "input": {"ssml": ssml_text},
            "voice": {"name": voice_id, "languageCode": language},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 16000}
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code in [401, 403]:
            raise PermissionError(f"[{self.provider_name}] Authentication failed. Check credentials.")
        elif response.status_code != 200:
            raise RuntimeError(f"[{self.provider_name}] API Error: {response.text}")

        audio_content = response.json().get("audioContent", "")
        if not audio_content:
            raise RuntimeError(f"[{self.provider_name}] No audio content returned in payload.")

        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(audio_content))

        if not self.validate_audio_file(output_path):
            raise RuntimeError(f"[{self.provider_name}] Generated audio is invalid or empty.")

        actual_duration = self.get_actual_duration(output_path)
        
        metadata = {
            "ssml_used": True,
            "delivery_speed_mapped": True,
            "format": "LINEAR16_16000Hz"
        }

        return actual_duration, metadata
